"""Search + export helpers behind the cockpit Search page."""
from __future__ import annotations

from pathlib import Path

from ui.search_page import (
    build_index,
    row_details,
    search_index,
    to_bibtex,
    to_csv,
)


def _mk(lib: Path, rel: str) -> None:
    p = lib / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF")


class TestSearch:

    def test_accent_and_case_insensitive(self, tmp_path):
        _mk(tmp_path, "01 - Published papers/P/Possamaï, D. - Stochastic control.pdf")
        index = build_index(tmp_path)
        assert search_index(index, "possamai")           # ï matches i
        assert search_index(index, "POSSAMAI CONTROL")   # AND + case

    def test_and_semantics(self, tmp_path):
        _mk(tmp_path, "01 - Published papers/A/Alpha, A. - BSDE methods.pdf")
        _mk(tmp_path, "01 - Published papers/B/Beta, B. - Control methods.pdf")
        index = build_index(tmp_path)
        assert len(search_index(index, "methods")) == 2
        assert len(search_index(index, "alpha methods")) == 1
        assert search_index(index, "alpha control") == []

    def test_limit(self, tmp_path):
        for i in range(25):
            _mk(tmp_path, f"01 - Published papers/X/Xu, X. - Paper {i} on limits.pdf")
        index = build_index(tmp_path)
        assert len(search_index(index, "limits", limit=10)) == 10

    def test_trash_excluded(self, tmp_path):
        _mk(tmp_path, ".trash/duplicates/Gone, G. - Removed paper.pdf")
        _mk(tmp_path, "01 - Published papers/K/Kept, K. - Live paper.pdf")
        index = build_index(tmp_path)
        assert search_index(index, "removed") == []
        assert search_index(index, "live")


class TestRowDetails:

    def test_parses_authors_title_status_year(self):
        r = row_details(
            "Dalang, R. C. - Stochastic analysis.pdf",
            "03 - Working papers/D/2021/Dalang, R. C. - Stochastic analysis.pdf")
        assert r["authors"] == "Dalang, R. C."
        assert r["title"] == "Stochastic analysis"
        assert r["status"].startswith("03")
        assert r["year"] == "2021"

    def test_topic_folder_keeps_status_subbucket(self):
        r = row_details(
            "Smith, J. - BSDEs.pdf",
            "07a - BSDEs/01 - Published papers/S/Smith, J. - BSDEs.pdf")
        assert r["status"].startswith("01")

    def test_doi_from_sidecar(self, tmp_path):
        from processing.identity import PaperIdentity, enable_sidecar_mirror
        enable_sidecar_mirror(tmp_path)
        rel = "01 - Published papers/S/Smith, J. - X.pdf"
        _mk(tmp_path, rel)
        ident = PaperIdentity()
        ident.doi = "10.1/xyz"
        ident.save(tmp_path / rel)
        r = row_details("Smith, J. - X.pdf", rel, tmp_path)
        assert r["doi"] == "10.1/xyz"


class TestExport:

    ROWS = [
        {"authors": "Dalang, R. C., Possamai, D.", "title": "Control & games",
         "status": "01 - Published papers", "year": "2020",
         "doi": "10.1/x", "path": "01 - Published papers/D/x.pdf"},
        {"authors": "Körber, L. C.", "title": "Optimal trading",
         "status": "06 - Theses", "year": "",
         "doi": "", "path": "06 - Theses/K/y.pdf"},
    ]

    def test_csv_columns_and_rows(self):
        out = to_csv(self.ROWS)
        lines = out.strip().splitlines()
        assert lines[0] == "authors,title,status,year,doi,path"
        assert len(lines) == 3

    def test_bibtex_types_and_escaping(self):
        bib = to_bibtex(self.ROWS)
        assert "@article{dalang2020," in bib
        assert "@phdthesis{korber," in bib          # accent folded in key
        assert r"Control \& games" in bib           # & escaped
        assert "doi = {10.1/x}" in bib
        assert "author = {Dalang, R. C. and Possamai, D.}" in bib

    def test_bibtex_key_collision_suffixes(self):
        rows = [dict(self.ROWS[0]), dict(self.ROWS[0]), dict(self.ROWS[0])]
        bib = to_bibtex(rows)
        assert "@article{dalang2020," in bib
        assert "@article{dalang2020a," in bib
        assert "@article{dalang2020b," in bib

    def test_unpublished_and_working_map_to_unpublished(self):
        r = dict(self.ROWS[0], status="03 - Working papers")
        assert "@unpublished{" in to_bibtex([r])
