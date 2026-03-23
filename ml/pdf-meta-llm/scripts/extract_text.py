#!/usr/bin/env python3
"""
Training data extraction for LLM-based metadata extraction.

Walks the PDF library, parsing filenames of the form
``Author1, Author2 - Title.pdf`` to derive ground-truth labels, then
extracts the first 3 pages of text from each PDF and writes two output
formats:

1. **Raw JSONL** (``--format raw``): One JSON object per line with
   ``prompt``, ``title``, ``author``, ``path`` keys.  Good for inspection
   and debugging.

2. **Chat JSONL** (``--format chat``, default): OpenAI-compatible chat
   messages format for fine-tuning with tools like ``mlx-lm``, ``axolotl``,
   or ``llama.cpp``::

       {"messages": [
         {"role": "system", "content": "..."},
         {"role": "user",   "content": "<PDF text>\\n...\\n</PDF text>\\n..."},
         {"role": "assistant", "content": "{\"title\": \"...\", \"authors\": [...]}"}
       ]}

Usage::

    python scripts/extract_text.py <pdf_root> <out_file> [--format chat|raw]
"""
from pathlib import Path
import argparse
import json
import re
import sys
import unicodedata
import multiprocessing as mp
import warnings

import pymupdf as fitz                # PyMuPDF

try:
    import pikepdf
except ImportError:
    pikepdf = None

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import tqdm as _tqdm
    tqdm_iter = _tqdm.tqdm
except ImportError:
    def tqdm_iter(it, **kw):
        return it

# -------- FOLDERS TO IGNORE --------
SKIP_PATHS = {
    # Slides — not papers, different structure
    "10 - Math slides",
    # Historical collections without Author - Title naming
    "05 - Books and lecture notes/00 - Histoire de l'académie royale des sciences",
    "05 - Books and lecture notes/02 - Mémoires présentés par divers savants à l'académie royale des sciences de l'institut de France",
    "05 - Books and lecture notes/07 - Séminaire Bourbaki",
    "05 - Books and lecture notes/10 - The science reports of the Tōhoku imperial university",
    # Scripts and non-PDF content
    "Scripts",
}
HOME_ROOT = Path.home() / "Dropbox/Work/Maths"

# -------- Chat-format system prompt (matches llm_extractor.py) --------
_SYSTEM_PROMPT = (
    "You are a metadata extraction assistant for academic mathematics papers.\n"
    "Given the first pages of a PDF, extract the paper's title and all author names.\n"
    "Return a JSON object with exactly two keys:\n"
    '  "title" — the full paper title (string)\n'
    '  "authors" — all author names (array of strings, each "Firstname Lastname")\n'
    "Rules:\n"
    "- Use the title exactly as it appears in the text (preserve the original language).\n"
    "- Do NOT include affiliations, emails, or other data.\n"
    '- If the text is too short or unclear to determine the title, return {"title": "", "authors": []}.'
)

_USER_TEMPLATE = (
    "<PDF text>\n{text}\n</PDF text>\n\n"
    "Extract the title and authors from the above academic paper text."
)


def skip_this(path: Path) -> bool:
    try:
        rel = path.relative_to(HOME_ROOT)
    except ValueError:
        return False
    return any(str(rel).startswith(p) for p in SKIP_PATHS)


# -------- filename parsing --------
def _is_initials_or_suffix(part: str) -> bool:
    """Check if a comma-separated part is initials or a name suffix.

    Matches patterns like: ``A.``, ``P. P.``, ``É.``, ``K. T. H.``,
    ``Yu.M.``, ``J.-P.``, ``P.-É.``, ``Jr.``, ``III``.

    Handles accented uppercase (É, Ł, Á, etc.) and Cyrillic-convention
    multi-letter initials (Yu., Sh., Ch.).
    """
    p = part.strip()
    # Uppercase letter class: ASCII + accented Latin uppercase
    _U = r"[A-ZÀ-ÖØ-Þ\u0100-\u024EŁ]"
    # An "initial unit": one or two uppercase letters followed by a period
    # Handles: A., É., Yu., Sh., Ch.
    _INIT = _U + r"{1,2}\."

    # Single uppercase letter without period: "A", "N", "É"
    if re.fullmatch(_U, p):
        return True
    # Single initial: "A.", "É.", "Ł.", "Yu."
    if re.fullmatch(_INIT, p):
        return True
    # Spaced initials: "P. P.", "E. A.", "K. T. H.", "S. C. P."
    if re.fullmatch(_INIT + r"(?:\s+" + _INIT + r")*", p):
        return True
    # Compact initials: "R.A.", "J.P.", "Yu.M.", "A.Yu."
    if re.fullmatch(_INIT + r"(?:" + _INIT + r")*", p):
        return True
    # Hyphenated initials: "J.-P.", "A.-L.", "P.-É.", "C.-É."
    if re.fullmatch(_INIT + r"\s*-\s*" + _INIT, p):
        return True
    # Cyrillic-convention with hyphen: "Y.R.-Y.", "J.Z.-G.", "T.-K.L."
    if re.fullmatch(r"(?:" + _INIT + r")+\s*-\s*(?:" + _INIT + r")+", p):
        return True
    # Suffixes: Jr, Jr., Sr, Sr., II, III, IV
    if re.fullmatch(r"(?:Jr|Sr|II|III|IV|V)\.?", p.rstrip("."), re.IGNORECASE):
        return True
    return False


def _group_author_parts(parts: list) -> list:
    """Group comma-split parts into complete author names.

    Filenames use ``Lastname, Initials`` with commas separating both parts
    of a name *and* different authors.  This function pairs each initial/suffix
    with its preceding lastname.

    Example::

        ["Bank", "P.", "Bayer", "C.", "Hager", "P. P."]
        → ["Bank, P.", "Bayer, C.", "Hager, P. P."]
    """
    if not parts:
        return []

    grouped = []
    current = parts[0].strip()

    for part in parts[1:]:
        part = part.strip()
        if not part:
            continue
        if _is_initials_or_suffix(part):
            # Attach to current name
            current = f"{current}, {part}"
        else:
            # Current name is complete, start a new one
            grouped.append(current)
            current = part

    if current:
        grouped.append(current)

    return grouped


def _to_firstname_lastname(name: str) -> str:
    """Convert ``Lastname, Initials`` → ``Initials Lastname``.

    If the name has no comma (already "Firstname Lastname" or a single name),
    return it as-is.

    Examples::

        "Dupont, F."       → "F. Dupont"
        "el Karoui, N."    → "N. el Karoui"
        "Hager, P. P."     → "P. P. Hager"
        "Clancy, Jr., D."  → "D. Clancy Jr."
        "Touzi"            → "Touzi"
    """
    if ", " not in name:
        return name

    parts = [p.strip() for p in name.split(", ")]

    if len(parts) == 2:
        lastname, initials = parts
        if _is_initials_or_suffix(initials):
            return f"{initials} {lastname}"
        else:
            # Two lastnames? e.g. "de Angelis, T." already handled above
            # but "Firstname, Lastname" would land here
            return name

    if len(parts) == 3:
        # "Clancy, Jr., D." → ["Clancy", "Jr.", "D."]
        # or "Chu, K. T. H., etc" — suffix in middle
        lastname, mid, last = parts
        if _is_initials_or_suffix(mid) and _is_initials_or_suffix(last):
            # "Lastname, Jr., D." → "D. Lastname Jr."
            return f"{last} {lastname} {mid}"
        elif _is_initials_or_suffix(last):
            return f"{last} {lastname}, {mid}"
        else:
            return name

    # 4+ parts: rare, return as-is
    return name


def parse_filename(pdf: Path):
    """Parse ``Author1, Author2 - Title.pdf`` → (title, [authors]).

    Returns ``(None, [])`` if the filename doesn't match the expected pattern.

    Authors are returned in ``"Firstname Lastname"`` format, matching the
    system prompt.  Handles the filename convention where commas separate
    both parts of a name and different authors.

    All output strings are NFC-normalised.  macOS stores filenames in NFD
    (decomposed) form, so ``é`` is stored as ``e`` + combining accent.
    NFC normalisation ensures training data uses the canonical composed form
    that the tokenizer and model expect.
    """
    # NFC-normalise the stem — critical on macOS where filenames use NFD
    stem = unicodedata.normalize("NFC", pdf.stem)

    # Strip leading article/page numbers from Séminaire papers: "218-Maitra" → "Maitra"
    stem = re.sub(r"^\d+\s*[-–]\s*", "", stem)

    # Strip trailing arXiv IDs, years, etc.
    stem = re.sub(r"\s*\(\d{4}\)\s*$", "", stem)          # trailing (2023)
    stem = re.sub(r"\s*\d{4}\.\d{4,5}(?:v\d+)?\s*$", "", stem)  # trailing arXiv ID

    if " - " not in stem:
        return None, []

    authors_part, title = stem.split(" - ", 1)
    title = title.strip()

    if not title or len(title) < 5:
        return None, []

    # Handle "and" separators first: "Author1 and Author2" or "Author1, Author2 and Author3"
    # Split on " and " but not on ", and " (which is handled by comma splitting)
    authors_part = re.sub(r"\s+and\s+", ", ", authors_part)

    # Split on commas, then group "Lastname, Initials" pairs together
    raw_parts = [p.strip() for p in authors_part.split(",") if p.strip()]
    grouped = _group_author_parts(raw_parts)

    # Convert each "Lastname, Initials" → "Initials Lastname"
    authors = [_to_firstname_lastname(name) for name in grouped]
    authors = [a for a in authors if a and len(a) >= 2]

    if not authors:
        return None, []

    return title, authors


# -------- text extraction helpers --------
def embedded_info(pdf: Path):
    """Extract embedded title/author from PDF metadata (legacy helper)."""
    if pikepdf is None:
        return None, None
    try:
        with pikepdf.open(pdf) as doc:
            info = doc.docinfo
            t = str(info.get("/Title",  ""))[:300]
            a = str(info.get("/Author", ""))[:300]
            if len(t) > 3 and len(a) > 3:
                return t, a
    except Exception:
        pass
    return None, None


def ocr_page(page):
    """OCR a page using Tesseract (fallback when text extraction is poor)."""
    if not OCR_AVAILABLE:
        return ""
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))   # 300 dpi
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(img, lang="eng")


def page_text(page):
    txt = page.get_text("text")
    return txt if len(txt.strip()) > 200 else ocr_page(page)


def extract_text(pdf: Path, n_pages: int = 3) -> str:
    """Extract text from the first *n_pages* of a PDF.

    Output is NFC-normalised so that accented characters use composed form.
    """
    try:
        with fitz.open(pdf) as doc:
            raw = "\n".join(
                page_text(doc.load_page(i))
                for i in range(min(n_pages, doc.page_count))
            )
            return unicodedata.normalize("NFC", raw)
    except Exception:
        return ""   # unreadable / empty


# optional alias so old code keeps working
extract = extract_text


# -------- processing functions --------
def _process_chat(pdf: Path):
    """Process a single PDF into chat-format JSONL for fine-tuning."""
    title, authors = parse_filename(pdf)
    if not title or not authors:
        return None

    body = extract_text(pdf)
    if not body or len(body.strip()) < 100:
        return None

    # Truncate to match what the LLM will see at inference time
    text = body[:6000]

    # Build the ground-truth JSON response
    ground_truth = json.dumps({"title": title, "authors": authors}, ensure_ascii=False)

    # Build chat messages
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _USER_TEMPLATE.format(text=text)},
        {"role": "assistant", "content": ground_truth},
    ]

    return json.dumps({"messages": messages}, ensure_ascii=False)


def _process_raw(pdf: Path):
    """Process a single PDF into raw JSONL (legacy format)."""
    title, authors = parse_filename(pdf)

    if not title:
        # Fall back to embedded metadata
        t, a = embedded_info(pdf)
        if t:
            title = t
            authors = [a] if a else []

    body = extract_text(pdf)
    if not body and not title:
        return None

    prompt = body[:6000] if body else f"{title}\n{', '.join(authors)}\n"

    return json.dumps({
        "prompt": prompt,
        "title": title,
        "author": ", ".join(authors) if authors else None,
        "path": str(pdf),
    })


# Legacy compatibility
def process(pdf: Path):
    """Legacy entry point — delegates to _process_raw."""
    return _process_raw(pdf)


# -------- main routine --------
def main():
    parser = argparse.ArgumentParser(
        description="Extract training data from PDF library for LLM fine-tuning"
    )
    parser.add_argument("pdf_root", type=Path, help="Root directory of PDF library")
    parser.add_argument("out_file", type=Path, help="Output JSONL file")
    parser.add_argument(
        "--format",
        choices=["chat", "raw"],
        default="chat",
        dest="output_format",
        help="Output format: 'chat' (OpenAI messages, default) or 'raw' (legacy)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes (default: CPU count)",
    )
    args = parser.parse_args()

    root = args.pdf_root
    outfile = args.out_file
    process_fn = _process_chat if args.output_format == "chat" else _process_raw

    pdfs = [p for p in root.rglob("*.pdf") if not skip_this(p)]
    print(f"🔍  Scanning {len(pdfs):,} PDFs ({args.output_format} format) …")

    written = 0
    with mp.Pool(args.workers) as pool, open(outfile, "w", encoding="utf-8") as out:
        for row in tqdm_iter(
            pool.imap_unordered(process_fn, pdfs, chunksize=8),
            total=len(pdfs),
        ):
            if row:
                out.write(row + "\n")
                written += 1

    print(f"✅  Wrote {written:,} examples → {outfile}")
    if args.output_format == "chat":
        print("   Format: OpenAI chat messages (ready for fine-tuning)")


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    mp.freeze_support()          # windows safety, harmless on mac/linux
    main()
