"""Preprint ↔ published variant detection (synthetic library only)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402

from processing.preprint_variants import (
    VariantPair,
    arxiv_id_from_filename,
    backfill_identifiers,
    compare_pair,
    dismiss_pair,
    extract_identifiers,
    find_variant_pairs,
    is_collection_doi,
    load_dismissals,
    retire_preprint,
)


class TestExtraction:

    def test_arxiv_new_style_with_context(self):
        t = "arXiv:2201.03562v1  [math.OC]  10 Jan 2022"
        assert extract_identifiers(t)["arxiv_id"] == "2201.03562"

    def test_arxiv_old_style(self):
        t = "arXiv:math.PR/0605274v2 30 May 2006"
        assert extract_identifiers(t)["arxiv_id"] == "math.PR/0605274"

    def test_doi_with_trailing_punctuation(self):
        t = "Electron. J. Probab. 23 (2018), https://doi.org/10.1214/18-EJP259."
        assert extract_identifiers(t)["doi"] == "10.1214/18-ejp259"

    def test_doi_url_fragment_stripped(self):
        t = "available at https://link.springer.com/10.1007/s00780-008-0085-5/pdf here"
        assert extract_identifiers(t)["doi"] == "10.1007/s00780-008-0085-5"

    def test_bare_digits_not_mistaken_for_arxiv(self):
        # A year+page like "2018.1234" must not match without arXiv context.
        assert extract_identifiers("published in 2018.12345 pages")["arxiv_id"] == ""

    def test_filename_arxiv(self):
        assert arxiv_id_from_filename("2301.03756v1.pdf") == "2301.03756"
        assert arxiv_id_from_filename("Smith, J. - Paper.pdf") == ""


@pytest.fixture
def lib(tmp_path):
    from processing.identity import enable_sidecar_mirror
    for d in ["01 - Published papers", "02 - Unpublished papers",
              "03 - Working papers", "04 - Papers to be downloaded"]:
        (tmp_path / d).mkdir(parents=True)
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _paper(lib, rel, *, text="", doi="", arxiv=""):
    from processing.identity import PaperIdentity
    p = lib / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(p, title="t", author="A")
    ident = PaperIdentity()
    ident.classifier_text = text
    ident.doi = doi
    ident.arxiv_id = arxiv
    ident.save(p, recompute_hash=False)
    return p


class TestBackfill:

    def test_mines_ids_from_cached_text(self, lib):
        from processing.identity import PaperIdentity
        p = _paper(lib, "03 - Working papers/S/2022/Smith, J. - X.pdf",
                   text="arXiv:2201.03562v1 [math.OC] ... doi:10.1214/18-EJP259.")
        stats = backfill_identifiers(lib)
        assert stats["doi_added"] == 1 and stats["arxiv_added"] == 1
        ident = PaperIdentity.load(p)
        assert ident.doi == "10.1214/18-ejp259"
        assert ident.arxiv_id == "2201.03562"

    def test_existing_fields_never_overwritten(self, lib):
        from processing.identity import PaperIdentity
        p = _paper(lib, "01 - Published papers/S/Smith, J. - X.pdf",
                   text="doi:10.9999/other", doi="10.1/original")
        backfill_identifiers(lib)
        assert PaperIdentity.load(p).doi == "10.1/original"


class TestDetection:

    def test_doi_pair_across_status(self, lib):
        _paper(lib, "03 - Working papers/B/2017/Bauer, M. - Old title.pdf",
               doi="10.1214/18-ejp259")
        _paper(lib, "01 - Published papers/B/Bauer, M. - New title.pdf",
               doi="10.1214/18-EJP259")
        pairs = find_variant_pairs(lib)
        assert len(pairs) == 1
        p = pairs[0]
        assert p.tier == "doi"
        assert "03 - Working papers" in p.preprint
        assert "01 - Published papers" in p.published

    def test_arxiv_pair_from_filename_only(self, lib):
        # A bare arXiv leftover in 04/ pairs with the filed copy whose
        # sidecar knows its arXiv id — no fuzzy matching needed.
        _paper(lib, "04 - Papers to be downloaded/2301.03756v1.pdf")
        _paper(lib, "01 - Published papers/H/Hamana, Y. - Brownian hitting.pdf",
               arxiv="2301.03756")
        pairs = find_variant_pairs(lib)
        assert len(pairs) == 1 and pairs[0].tier == "arxiv"

    def test_fuzzy_bauer_case(self, lib):
        # The real trigger: same authors (one ADDED on publication),
        # meaningfully different titles, shared abstract.
        abstract = ("We prove existence and uniqueness of strong solutions "
                    "of mean field stochastic differential equations with "
                    "irregular drift coefficients using Malliavin calculus " * 3)
        _paper(lib, "02 - Unpublished papers/B/Bauer, M., Meyer-Brandis, T. - "
                    "Strong solutions of mean-field SDEs with irregular "
                    "expectation functionals in the drift.pdf",
               text=abstract)
        _paper(lib, "01 - Published papers/B/Bauer, M., Meyer-Brandis, T., "
                    "Proske, F. - Strong solutions of mean-field stochastic "
                    "differential equations with irregular drift.pdf",
               text=abstract + " journal version")
        pairs = find_variant_pairs(lib)
        assert len(pairs) == 1
        assert pairs[0].tier == "fuzzy"

    def test_book_doi_never_pairs_chapters(self, lib):
        # Real-library defect: a World Scientific volume DOI is printed on
        # every chapter, so it was mined into many distinct chapters and
        # cross-paired them.  Two guards must kill this: ISBN book-DOI skip
        # AND author-overlap.  Chapters here have DIFFERENT authors.
        book = "10.1142/9789811259142"
        assert is_collection_doi(book)
        _paper(lib, "01 - Published papers/G/Guyon, J. - The smile of stochastic "
                    "volatility models.pdf", doi=book)
        _paper(lib, "01 - Published papers/B/Brigo, D. - Probability-free models "
                    "in option pricing.pdf", doi=book)
        _paper(lib, "01 - Published papers/D/Dupire, B. - 25 years of local "
                    "volatility.pdf", doi=book)
        assert find_variant_pairs(lib) == []

    def test_shared_doi_different_authors_not_paired(self, lib):
        # Even a NON-book DOI shared by two DIFFERENT-author papers (a
        # proceedings-DOI coincidence) must not pair — a variant shares
        # authors.
        doi = "10.1016/j.na.2023.999999"
        _paper(lib, "02 - Unpublished papers/A/Alpha, A. - First topic.pdf", doi=doi)
        _paper(lib, "01 - Published papers/B/Beta, B. - Different topic.pdf", doi=doi)
        assert find_variant_pairs(lib) == []

    def test_backfill_skips_book_doi(self, lib):
        from processing.identity import PaperIdentity
        p = _paper(lib, "01 - Published papers/G/Guyon, J. - Chapter.pdf",
                   text="World Scientific 2023 https://doi.org/10.1142/9789811259142")
        backfill_identifiers(lib)
        assert PaperIdentity.load(p).doi == ""      # book DOI not stored

    def test_clear_collection_dois_cleans_pollution(self, lib):
        from processing.identity import PaperIdentity
        from processing.preprint_variants import clear_collection_dois
        # A sidecar polluted with a book DOI (as an earlier backfill would);
        # and a legit per-article DOI that must be LEFT alone.
        bad = _paper(lib, "01 - Published papers/G/Guyon, J. - Chapter.pdf",
                     doi="10.1142/9789811259142")
        good = _paper(lib, "01 - Published papers/C/Ciosmak, K.J. - Article.pdf",
                      doi="10.1016/j.na.2023.113267")
        # A real book in 05 legitimately keeps its ISBN DOI.
        book = _paper(lib, "05 - Books and lecture notes/S/Shreve, S. - Stochastic "
                           "calculus for finance.pdf", doi="10.1007/978-0-387-40101-0")
        dry = clear_collection_dois(lib, dry_run=True)
        assert len(dry["found"]) == 1 and dry["cleared"] == 0
        assert PaperIdentity.load(bad).doi == "10.1142/9789811259142"   # untouched
        res = clear_collection_dois(lib, dry_run=False)
        assert res["cleared"] == 1
        assert PaperIdentity.load(bad).doi == ""                        # chapter cleared
        assert PaperIdentity.load(good).doi == "10.1016/j.na.2023.113267"  # per-article kept
        assert PaperIdentity.load(book).doi == "10.1007/978-0-387-40101-0"  # real book kept

    def test_different_papers_same_author_not_paired(self, lib):
        _paper(lib, "02 - Unpublished papers/S/Smith, J. - Optimal stopping "
                    "under model uncertainty.pdf",
               text="abstract about optimal stopping problems and ambiguity " * 5)
        _paper(lib, "01 - Published papers/S/Smith, J. - Ergodic properties "
                    "of interacting particle systems.pdf",
               text="abstract about hydrodynamic limits and particle systems " * 5)
        assert find_variant_pairs(lib) == []


class TestResolution:

    def _pair(self, lib):
        from processing.identity import PaperIdentity
        pre = _paper(lib, "03 - Working papers/B/2017/Bauer, M. - Old.pdf",
                     doi="10.1/x")
        ident = PaperIdentity.load(pre)
        ident.topic_codes = ["07a"]
        ident.save(pre, recompute_hash=False)
        _paper(lib, "01 - Published papers/B/Bauer, M. - New.pdf", doi="10.1/x")
        (pairs,) = (find_variant_pairs(lib),)
        return pairs[0]

    def test_retire_preprint_reversible_and_merges_sidecar(self, lib):
        from processing.identity import PaperIdentity
        from processing.undo_log import UndoLog
        pair = self._pair(lib)
        log = UndoLog(log_dir=lib / ".operation_log")
        tx = log.begin_transaction("retire preprint")
        ok, msg = retire_preprint(pair, lib, undo_log=log)
        log.commit()
        assert ok, msg
        pre = lib / pair.preprint
        pub = lib / pair.published
        assert not pre.exists()
        assert (lib / ".trash" / "upgraded_preprints" / "Bauer, M. - Old.pdf").exists()
        # Published side inherited the preprint's topic knowledge.
        assert "07a" in PaperIdentity.load(pub).topic_codes
        # One-click reversible.
        log.undo_transaction(tx)
        assert pre.exists()

    def test_retire_variant_drops_chosen_side(self, lib):
        # Same-status near-duplicate: the owner keeps one, retires the other
        # (a dropped 01 copy lands in .trash/duplicates, not upgraded_preprints).
        from processing.preprint_variants import VariantPair, retire_variant
        from processing.undo_log import UndoLog
        a = _paper(lib, "01 - Published papers/D/Duembgen, M. - Estimate nothing.pdf",
                   doi="10.1/x")
        b = _paper(lib, "01 - Published papers/D/Dümbgen, M. - Estimate nothing.pdf",
                   doi="10.1/x")
        pair = VariantPair(preprint="01 - Published papers/D/Duembgen, M. - Estimate nothing.pdf",
                           published="01 - Published papers/D/Dümbgen, M. - Estimate nothing.pdf",
                           tier="doi")
        log = UndoLog(log_dir=lib / ".operation_log")
        log.begin_transaction("retire")
        ok, msg = retire_variant(pair, lib, drop=pair.preprint, undo_log=log)
        log.commit()
        assert ok, msg
        assert not a.exists() and b.exists()
        assert (lib / ".trash" / "duplicates" / a.name).exists()

    def test_compare_pair_reports_both_sides(self, lib):
        pair = self._pair(lib)
        cmp = compare_pair(pair, lib)
        assert cmp["preprint"]["exists"] and cmp["published"]["exists"]
        assert cmp["preprint"]["bytes"] > 0


class TestDismissals:

    def test_dismiss_persists(self, lib):
        pair = VariantPair(preprint="a.pdf", published="b.pdf", tier="fuzzy")
        assert pair.key() not in load_dismissals(lib)
        dismiss_pair(lib, pair)
        assert pair.key() in load_dismissals(lib)


class TestIdentifierTwin:

    def test_finds_twin_by_doi(self, lib):
        from processing.preprint_variants import find_identifier_twin
        filed = _paper(lib, "01 - Published papers/B/Bauer, M. - X.pdf",
                       doi="10.1/x")
        arrival = lib / "12" / "new.pdf"
        assert find_identifier_twin(lib, doi="10.1/X", exclude=arrival) == str(filed)

    def test_arxiv_version_suffix_ignored(self, lib):
        from processing.preprint_variants import find_identifier_twin
        filed = _paper(lib, "01 - Published papers/H/Hamana, Y. - X.pdf",
                       arxiv="2301.03756")
        # Arrival carries a v2 suffix; must still match the stored v-less id.
        assert find_identifier_twin(lib, arxiv_id="2301.03756v2",
                                    exclude=lib / "z.pdf") == str(filed)

    def test_no_twin_returns_none(self, lib):
        from processing.preprint_variants import find_identifier_twin
        _paper(lib, "01 - Published papers/B/Bauer, M. - X.pdf", doi="10.1/x")
        assert find_identifier_twin(lib, doi="10.9/other") is None
        assert find_identifier_twin(lib) is None      # no ids given


class TestIngestVariantFlag:

    def test_ingest_flags_variant_of(self, lib, monkeypatch):
        # A filed paper carries a DOI; a new arrival with the same DOI is
        # filed AND flagged variant_of (never blocked).
        from processing import ingest as ing
        _paper(lib, "01 - Published papers/B/Bauer, M. - Published.pdf",
               doi="10.1214/18-ejp259")
        arrival = lib / "12 - To be sorted" / "drop.pdf"
        arrival.parent.mkdir(parents=True, exist_ok=True)
        _write_minimal_pdf(arrival, title="t", author="Bauer, M.")

        def fake_meta(path):
            return {"title": "Strong solutions", "authors": [{"family": "Bauer", "given": "M."}],
                    "doi": "10.1214/18-EJP259"}
        monkeypatch.setattr(ing, "extract_metadata_from_pdf", fake_meta)
        res = ing.ingest_paper(arrival, library_root=lib, status="published",
                               dry_run=False, auto_topic=False, variant_check=True)
        assert res["success"]
        assert res.get("variant_of", "").endswith("Bauer, M. - Published.pdf")
