"""What the local model is given to read, and which of its answers count.

The local model is the last resort: it reads the first pages of a paper
that has no title in its own metadata and none from arXiv, Crossref or
HAL. MEASURED 2026-10-15, read-only, on the real ``12 - To be sorted``
(2,414 PDFs; 216 reach the model while arXiv is unreachable, 70 always):

* five different scans (``Download (1).pdf``, ``Download2/4/6/8.pdf``,
  129-698 KB) have ONE page of text, the sheet JSTOR put in front of its
  early scans -- "Institute of Mathematical Statistics is collaborating
  with JSTOR to digitize, preserve, and extend access to The Annals of
  Probability." -- and nothing else: the paper's own pages are images.
  The model was handed those 152 characters and named all five "The
  Annals of probability" by "000-00";
* a book whose only text is the Modern Birkhäuser Classics series
  description was named "Modern Birkhäuser classics" by "Birkhäuser".

Every other cover sheet met there -- ResearchGate, HAL, Taylor & Francis,
DML-CZ, a university repository -- names the paper (title, authors,
source), and the model read each of them correctly. JSTOR's later sheets
name the paper too: each of the 330 in the library whose filename has a
title carries it. So the rule is not "drop a cover page"; it is:

* **A page that says only who digitised, hosts or publishes the paper is
  not given to the model** (``furniture``). Any other page is given
  verbatim, so a paper without such a page is read from exactly the text
  it always was -- and its remembered answer (keyed by that text) still
  applies, while one that had such a page is read from new text, under a
  new key, and its old answer is never looked up again.
* **An answer is believed only if it names a paper** (``answer_problem``):
  a title with letters in it, and authors that are names. "000-00" is
  not a name. This is judged every time an answer is used, remembered or
  fresh, so a wrong answer remembered before this rule existed is refused
  too.

Either way the outcome is three-valued -- an answer, or "could not tell"
with the reason -- never a guess dressed as a name.
"""
from __future__ import annotations

import re
import unicodedata
from typing import List, Optional, Sequence, Tuple

#: The model is given the first 4,000 characters of the first three pages
#: (``processing.ingest.extract_metadata_from_pdf``), as it always was.
LIMIT = 4000

#: Pages of furniture: what each is, in the owner's words, and the text
#: that marks it. Each block is matched with its own line breaks and
#: spacing free, on an NFC-folded copy with words broken over lines
#: joined (macOS hands back NFD; "Birkhäuser" also arrives as
#: "Birkh¨auser" from TeX-made PDFs and as "Birkhauser" from scans).
_FURNITURE: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    # JSTOR's sheet in front of its early scans: the publisher and the
    # JOURNAL, nothing about the paper. Its later sheets carry the same
    # sentence below the paper's own title, authors and source, and are
    # therefore not furniture: the title lines are left over.
    ("JSTOR's cover sheet, which names only the journal",
     re.compile(
         r"(?:^|(?<=\n))[^\n]*?\bis\s+collaborating\s+with\s+JSTOR\s+to\s+"
         r"digiti[sz]e\s*,?\s+preserve\s*,?\s+and\s+extend\s+access\s+to\s+"
         r"[^\n]*(?:\n[^\n]*?\.(?=\s*(?:\n|$)))?",
         re.I)),
    # A series description printed before a book's title page.
    ("the Modern Birkhäuser Classics series description",
     re.compile(
         r"Modern\s+Birkh(?:ä|a¨|¨a|a)user\s+Classics\s+Many\s+of\s+the\s+"
         r"original\s+research\s+and\s+survey\s+monographs\b.*?"
         r"\b(?:students|scholars|researchers)\s*\.",
         re.I | re.S)),
)

#: Left on every such page and about nothing: links and the odd symbol.
_LINK = re.compile(r"(?:https?://|www\.)\S+", re.I)

#: A page with any word of three letters or more left, once its furniture
#: and links are taken away, may be about the paper and is kept. Measured
#: on the library's first pages that carry JSTOR's sentence: those left
#: out (96) keep 0 such words and never the owner's title (from the
#: filename); those kept (331) keep 10 or more, and carry it whenever the
#: filename has one (330). Three letters, so a
#: stray "R" from an ASCII "(R)" or a "p." does not count.
_PAPER_WORDS = 1
_WORD = re.compile(r"[^\W\d_]{3,}")


#: A word broken over a line: "resear-\nchers" in the library's Triebel.
_BROKEN_WORD = re.compile(r"-[ \t]*\n[ \t]*")


def _fold(text: str) -> str:
    """The copy a page is MATCHED on; the model still reads the original."""
    return _BROKEN_WORD.sub("", unicodedata.normalize("NFC", text or ""))


def furniture(page: str) -> Optional[str]:
    """Why this page tells the model nothing about the paper, or None.

    None for any page that keeps a real word once its furniture and
    links are removed -- and for a page with no furniture at all, however
    short or empty (an empty page gives the model nothing either way;
    dropping it changes nothing).
    """
    text = _fold(page)
    what = None
    for name, pattern in _FURNITURE:
        text, n = pattern.subn(" ", text)
        if n and what is None:
            what = name
    left = _WORD.findall(_LINK.sub(" ", text))
    return what if len(left) < _PAPER_WORDS else None


def text_for_model(pages: Sequence[str]) -> Tuple[str, List[str]]:
    """The text the model reads, and what was left out of it and why.

    ``pages`` are the first pages as PyMuPDF extracted them. The result
    is those pages joined, minus furniture pages, cut at ``LIMIT``. With
    no furniture it is exactly ``"".join(pages)[:LIMIT]``, byte for byte.
    """
    kept, left_out = [], []
    for number, page in enumerate(pages, start=1):
        why = furniture(page)
        if why is None:
            kept.append(page)
        else:
            left_out.append(f"page {number} is {why}")
    return "".join(kept)[:LIMIT], left_out


#: The model's own guard: below this it does not read at all
#: (``LLMMetadataExtractor.extract``), so it is not asked.
MIN_CHARS = 100


def nothing_to_read(text: str, left_out: Sequence[str]) -> Optional[str]:
    """Why the model is not even asked, or None to ask it."""
    if len(text.strip()) >= MIN_CHARS:
        return None
    if left_out:
        rest = ("and the other pages have no text to read (a scan without "
                "a text layer)" if not text.strip()
                else "and the other pages have almost no text")
        return f"{'; '.join(left_out)}, {rest}"
    if not text.strip():
        return "the first pages have no text to read (a scan without a text layer)"
    return "the first pages have almost no text"


def _has_letter(s: str) -> bool:
    return any(unicodedata.category(c).startswith("L") for c in s)


def answer_problem(result) -> Optional[str]:
    """Why the model's answer is not a paper's name, or None to use it.

    The fine-tuned model writes authors as surname and initials in turn
    (``["Gaunt", "R.E."]``), which the filename builder joins correctly,
    so an author is judged only on being a name at all: it has a letter.
    """
    if not isinstance(result, dict):
        return "it gave no answer"
    title = result.get("title")
    if not isinstance(title, str) or not title.strip():
        return "it read the first pages and found no title"
    if not _has_letter(title):
        return f"it gave {title.strip()!r} as the title, which has no words"
    authors = result.get("authors") or []
    if isinstance(authors, str):
        authors = [authors]
    for a in authors:
        if not isinstance(a, str) or not _has_letter(a):
            return (f"it gave {str(a).strip()!r} as an author, which is not "
                    f"a name, so its title {title.strip()!r} is not trusted "
                    f"either")
    return None
