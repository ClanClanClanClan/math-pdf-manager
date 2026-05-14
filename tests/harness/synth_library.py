"""Synthetic-library generator for end-to-end harness tests.

Creates a realistic-looking library tree under tmp_path with seeded PDFs
that exercise every code path the real pipeline hits. Tests built on top
of this never touch the user's real Dropbox.

The synthesized PDFs are minimally valid (PyMuPDF can open them) and have
metadata that triggers specific extraction code paths:

  - normal: title + author both present
  - latex_title: title contains raw LaTeX (\\^o, \\'e, \\v{S})
  - no_title: author present but no title (the "SoWise" case)
  - no_metadata: nothing extractable at all (raw filename)
  - cyrillic_author: tests Cyrillic alpha-subdir routing
  - greek_author: tests Greek alpha-subdir routing
  - particle_author: tests nobiliary-particle stripping (el Karoui → K)
  - already_canonical: source name already in canonical form
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SynthPdfSpec:
    """One synthesized PDF in the synthetic library."""
    filename: str
    subfolder: str        # e.g. "12 - To be sorted/03 - Working papers"
    pdf_title: Optional[str] = None
    pdf_author: Optional[str] = None
    pdf_keywords: Optional[str] = None
    # Expected outcome of running bulk_sort.sort_one on this paper:
    expect_ok: bool = True
    expect_destination_letter: Optional[str] = None  # e.g. "A"
    expect_destination_folder: Optional[str] = None  # e.g. "03 - Working papers"
    expect_filename_contains: list[str] = field(default_factory=list)
    notes: str = ""


def _write_minimal_pdf(path: Path, *, title: str = "", author: str = "", keywords: str = "") -> None:
    """Write a minimal valid PDF with an Info dictionary so PyMuPDF can
    extract title/author. Hand-crafted because pypdf is overkill for tests."""
    info_parts = []
    if title:
        info_parts.append(f"/Title ({_escape_pdf(title)})")
    if author:
        info_parts.append(f"/Author ({_escape_pdf(author)})")
    if keywords:
        info_parts.append(f"/Keywords ({_escape_pdf(keywords)})")
    info_obj = " ".join(info_parts) if info_parts else ""

    pdf = (
        "%PDF-1.4\n"
        "1 0 obj\n"
        "<< /Type /Catalog /Pages 2 0 R >>\n"
        "endobj\n"
        "2 0 obj\n"
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        "endobj\n"
        "3 0 obj\n"
        "<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] >>\n"
        "endobj\n"
        "4 0 obj\n"
        f"<< {info_obj} >>\n"
        "endobj\n"
        "xref\n"
        "0 5\n"
        "0000000000 65535 f \n"
        "0000000009 00000 n \n"
        "0000000058 00000 n \n"
        "0000000111 00000 n \n"
        "0000000195 00000 n \n"
        "trailer\n"
        "<< /Size 5 /Root 1 0 R /Info 4 0 R >>\n"
        "startxref\n"
        "250\n"
        "%%EOF\n"
    ).encode("utf-8", errors="replace")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf)


def _escape_pdf(s: str) -> str:
    """Escape a string for use inside a PDF (X) literal."""
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


# ---------------------------------------------------------------------------
# Canonical spec set — exercises every code path
# ---------------------------------------------------------------------------

STANDARD_SPECS: list[SynthPdfSpec] = [
    # 1. normal published paper
    SynthPdfSpec(
        filename="paper001.pdf",
        subfolder="12 - To be sorted/01 - Published papers",
        pdf_title="A theorem on stochastic differential equations",
        pdf_author="Smith, J.",
        expect_destination_letter="S",
        expect_destination_folder="01 - Published papers",
        expect_filename_contains=["Smith"],
        notes="normal published with comma-style author",
    ),
    # 2. full-name authors (PDF-embedded format)
    SynthPdfSpec(
        filename="paper002.pdf",
        subfolder="12 - To be sorted/01 - Published papers",
        pdf_title="Probability graphons",
        pdf_author="Romain Abraham, Jean-François Delmas & Julien Weibel",
        expect_destination_letter="A",
        expect_destination_folder="01 - Published papers",
        expect_filename_contains=["Abraham", "Delmas", "Weibel"],
        notes="full-name PDF-embedded format (was the original regression)",
    ),
    # 3. LaTeX accent in title
    SynthPdfSpec(
        filename="paper003.pdf",
        subfolder="12 - To be sorted/05 - Books and lecture notes",
        pdf_title="Stochastic It\\^o equations",
        pdf_author="N. V. Krylov",
        expect_destination_folder="05 - Books and lecture notes",
        expect_filename_contains=["Krylov", "Itô"],
        notes="LaTeX command \\^o decoded to Itô",
    ),
    # 4. nobiliary particle in author
    SynthPdfSpec(
        filename="paper004.pdf",
        subfolder="12 - To be sorted/03 - Working papers",
        pdf_title="Stochastic control under model uncertainty",
        pdf_author="Nicole el Karoui",
        expect_destination_letter="K",
        expect_destination_folder="03 - Working papers",
        expect_filename_contains=["el Karoui"],
        notes="el Karoui files under K, not E",
    ),
    # 5. fake author + no title (the SoWise case)
    SynthPdfSpec(
        filename="paper005.pdf",
        subfolder="12 - To be sorted/01 - Published papers",
        pdf_title=None,             # no title at all
        pdf_author="SoWise",        # PDF-creation software, NOT a real author
        expect_ok=False,            # quality gate should flag this
        notes="quality gate refuses to file: fake author + missing title",
    ),
    # 6. completely empty metadata (raw filename like Wiley)
    SynthPdfSpec(
        filename="148536_1_art_file_638720_t2qdrr_sc.pdf",
        subfolder="12 - To be sorted/03 - Working papers",
        pdf_title=None,
        pdf_author=None,
        expect_ok=False,
        notes="quality gate refuses: no metadata at all",
    ),
    # 7. already-canonical name in 12/
    SynthPdfSpec(
        filename="Smith, J. - Already canonical paper title.pdf",
        subfolder="12 - To be sorted/03 - Working papers",
        pdf_title=None,             # no metadata, but filename already canonical
        pdf_author=None,
        expect_ok=True,             # source-name matches canonical, accept
        expect_destination_letter="S",
        expect_destination_folder="03 - Working papers",
        expect_filename_contains=["Smith"],
        notes="already-canonical files pass through cleanly",
    ),
    # 8. Cyrillic author (alpha-subdir test)
    SynthPdfSpec(
        filename="paper008.pdf",
        subfolder="12 - To be sorted/01 - Published papers",
        pdf_title="On Markov chains",
        pdf_author="Иванов, А.",
        expect_destination_letter="I",
        expect_destination_folder="01 - Published papers",
        notes="Cyrillic Иванов files under I",
    ),
    # 9. Polish stroke letter
    SynthPdfSpec(
        filename="paper009.pdf",
        subfolder="12 - To be sorted/03 - Working papers",
        pdf_title="Regular and singular analytic functions",
        pdf_author="Łojasiewicz, S.",
        expect_destination_letter="L",
        expect_destination_folder="03 - Working papers",
        notes="Polish Ł decomposes to L",
    ),
    # 10. unicode emoji in title (filesystem-safety filter)
    SynthPdfSpec(
        filename="paper010.pdf",
        subfolder="12 - To be sorted/03 - Working papers",
        pdf_title="A 🎓 paper about 🔬 research",
        pdf_author="Brown, A.",
        expect_destination_letter="B",
        expect_destination_folder="03 - Working papers",
        expect_filename_contains=["Brown"],
        notes="emoji are filesystem-safe but should not crash",
    ),
    # 11. very long title (truncation test)
    SynthPdfSpec(
        filename="paper011.pdf",
        subfolder="12 - To be sorted/01 - Published papers",
        pdf_title=("A very long title that should trigger the filesystem byte-limit "
                   "truncation logic in the canonical filename generator " * 5),
        pdf_author="Wilson, K., Carter, B., Brown, A., Davis, E., Evans, F.",
        expect_destination_letter="W",
        expect_destination_folder="01 - Published papers",
        notes="long title gets truncated, et al. fallback may kick in",
    ),
    # 12. published with DOI in title field (we ignore this, doesn't break anything)
    SynthPdfSpec(
        filename="paper012.pdf",
        subfolder="12 - To be sorted/01 - Published papers",
        pdf_title="Optimal control of stochastic processes",
        pdf_author="Pham, H.",
        pdf_keywords="optimal control, stochastic, HJB",
        expect_destination_letter="P",
        expect_destination_folder="01 - Published papers",
        notes="standard published paper",
    ),
]


def build_synth_library(root: Path, specs: list[SynthPdfSpec] = STANDARD_SPECS) -> Path:
    """Construct a synthetic library tree at ``root`` and write the spec'd
    PDFs into ``12 - To be sorted/`` subfolders.

    Returns the root path for convenience.
    """
    # Top-level folders
    folders = [
        "01 - Published papers",
        "02 - Unpublished papers",
        "03 - Working papers",
        "04 - Papers to be downloaded",
        "05 - Books and lecture notes",
        "06 - Theses",
        "07a - BSDEs",
        "12 - To be sorted/01 - Published papers",
        "12 - To be sorted/02 - Unpublished papers",
        "12 - To be sorted/03 - Working papers",
        "12 - To be sorted/05 - Books and lecture notes",
        "12 - To be sorted/06 - Theses",
    ]
    for f in folders:
        (root / f).mkdir(parents=True, exist_ok=True)

    # Write each spec's PDF
    for spec in specs:
        target = root / spec.subfolder / spec.filename
        _write_minimal_pdf(
            target,
            title=spec.pdf_title or "",
            author=spec.pdf_author or "",
            keywords=spec.pdf_keywords or "",
        )

    return root
