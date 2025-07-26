#!/usr/bin/env python3
"""
Walks your huge PDF tree, skips the odd folders you listed, pulls the
first 3 pages (OCR when needed), and writes a *raw* jsonl file.

Usage:
    python scripts/extract_text.py <pdf_root> <out_file>
"""
from pathlib import Path
import json
import sys
import multiprocessing as mp
import warnings
import pymupdf as fitz                # PyMuPDF
import pikepdf
from PIL import Image
import pytesseract
import tqdm

# -------- FOLDERS TO IGNORE --------
SKIP_PATHS = {
    "01 - Astérisque",
    "04 - Séminaires de probabilités de Strasbourg",
    "05 - Séminaire Bourbaki",
    "14 - Math slides",
    "13 - Math books and lecture notes/00 - Histoire de l'académie royale des sciences",
    "13 - Math books and lecture notes/01 - Comptes rendus hebdomadaires de l'académie des sciences",
    "13 - Math books and lecture notes/02 - Mémoires présentés par divers savants à l'académie royale des sciences de l'institut de France",
    "13 - Math books and lecture notes/03 - Proceedings of the ICM",
    "13 - Math books and lecture notes/04 - Saint-Flour",
    "13 - Math books and lecture notes/05 - Lviv Scottish book",
    "13 - Math books and lecture notes/06 - Messenger of mathematics",
    "13 - Math books and lecture notes/07 - Cours spécialisés société mathématique de France",
    "13 - Math books and lecture notes/08 - Mémoires de la société mathématique de France",
    "13 - Math books and lecture notes/09 - The science reports of the Tōhoku imperial university",
}
HOME_ROOT = Path.home() / "Dropbox/Work/Maths"

def skip_this(path: Path) -> bool:
    try:
        rel = path.relative_to(HOME_ROOT)
    except ValueError:
        return False
    return any(str(rel).startswith(p) for p in SKIP_PATHS)

# -------- util helpers --------
def embedded_info(pdf: Path):
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
    pix = page.get_pixmap(matrix=fitz.Matrix(2,2))   # 300 dpi
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(img, lang="eng")

def page_text(page):
    txt = page.get_text("text")
    return txt if len(txt.strip()) > 200 else ocr_page(page)

def extract_text(pdf: Path, n_pages: int = 3) -> str:   # <- rename here
    try:
        with fitz.open(pdf) as doc:
            return "\n".join(page_text(doc.load_page(i))
                             for i in range(min(n_pages, doc.page_count)))
    except (fitz.fitz.EmptyFileError, RuntimeError):
        return ""   # unreadable / empty

# optional alias so old code keeps working
extract = extract_text

def process(pdf: Path):
    title, author = embedded_info(pdf)
    if not title:
        body = extract(pdf)
        if not body:
            return None          # drop unreadable file
        prompt = body[:6000]
    else:
        prompt = f"{title}\n{author}\n"
    return json.dumps({
        "prompt": prompt,
        "title":  title,
        "author": author,
        "path":   str(pdf)
    })

# -------- main routine --------
def main():
    root, outfile = map(Path, sys.argv[1:3])
    pdfs = [p for p in root.rglob("*.pdf") if not skip_this(p)]
    print(f"🔍  Scanning {len(pdfs):,} PDFs …")

    with mp.Pool() as pool, open(outfile, "w") as out:
        for row in tqdm.tqdm(pool.imap_unordered(process, pdfs, chunksize=8),
                             total=len(pdfs)):
            if row:
                out.write(row + "\n")

    print(f"✅  Wrote raw dataset → {outfile}")

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    mp.freeze_support()          # windows safety, harmless on mac/linux
    main()