"""Identifier-named PDF resolution (arXiv / DOI / SSRN / HAL from filename)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


class TestDetectFilenameIds:

    def test_arxiv_new(self):
        from processing.id_resolution import detect_filename_ids
        assert detect_filename_ids("2103.04185.pdf")["arxiv_id"] == "2103.04185"
        assert detect_filename_ids("2401.00001v2.pdf")["arxiv_id"] == "2401.00001v2"

    def test_arxiv_old(self):
        # On disk the old-scheme "/" is escaped to "_".
        from processing.id_resolution import detect_filename_ids
        assert detect_filename_ids("math.PR_0501001.pdf").get("arxiv_id") == "math.PR/0501001"
        assert detect_filename_ids("math_0501001.pdf").get("arxiv_id") == "math/0501001"

    def test_ssrn(self):
        from processing.id_resolution import detect_filename_ids
        assert detect_filename_ids("SSRN-id1234567.pdf")["ssrn_id"] == "1234567"
        assert detect_filename_ids("ssrn_7654321.pdf")["ssrn_id"] == "7654321"

    def test_hal_and_tel(self):
        from processing.id_resolution import detect_filename_ids
        assert detect_filename_ids("hal-01234567.pdf")["hal_id"] == "hal-01234567"
        assert detect_filename_ids("tel-09876543.pdf")["hal_id"] == "tel-09876543"

    def test_doi_escaped(self):
        from processing.id_resolution import detect_filename_ids
        # filesystem-safe DOI: "/" -> "_"
        got = detect_filename_ids("10.1214_aop.2023.1234.pdf")
        assert got.get("doi") == "10.1214/aop.2023.1234"

    def test_canonical_named_file_with_digit_pattern_is_not_an_id(self):
        # Real false positive caught on the live library: a hand-named
        # file whose TITLE contains a "dddd.ddddd"-looking substring must
        # not be read as an arXiv id.  The "Author - Title" form is the
        # tell that it's already named.
        from processing.id_resolution import detect_filename_ids
        assert detect_filename_ids(
            "Krylov, N.V. - Remarks on 2024.12345 strong solutions.pdf") == {}

    def test_normal_title_has_no_ids(self):
        # CRITICAL: a hand-named paper must NOT be mistaken for an id.
        from processing.id_resolution import detect_filename_ids
        for name in [
            "Karoui, N. - Backward SDEs and 10 applications.pdf",
            "Touzi, N. - A note on 2BSDEs (2021).pdf",
            "Smith, J. - Reflected BSDEs and optimal stopping.pdf",
            "Peng, S. - G-expectation and G-Brownian motion.pdf",
        ]:
            assert detect_filename_ids(name) == {}, name


class TestSsrnAndHal:

    def test_ssrn_doi_mapping(self):
        from processing.id_resolution import ssrn_doi
        assert ssrn_doi("1234567") == "10.2139/ssrn.1234567"

    def test_resolve_hal_success(self, monkeypatch):
        import processing.id_resolution as idr

        class FakeResp:
            status_code = 200
            def json(self):
                return {"response": {"docs": [{
                    "title_s": ["Reflected BSDEs under G-expectation"],
                    "authFullName_s": ["Jane Doe", "Pierre Martin"],
                }]}}

        monkeypatch.setattr(idr, "requests", type("R", (), {
            "get": staticmethod(lambda *a, **k: FakeResp())}), raising=False)
        # requests is imported inside the function, so patch sys.modules.
        import types
        fake = types.ModuleType("requests")
        fake.get = lambda *a, **k: FakeResp()
        monkeypatch.setitem(sys.modules, "requests", fake)
        out = idr.resolve_hal("hal-01234567")
        assert out["title"].startswith("Reflected BSDEs")
        assert out["authors"] == ["Jane Doe", "Pierre Martin"]

    def test_resolve_hal_no_record(self, monkeypatch):
        import processing.id_resolution as idr
        import types

        class FakeResp:
            status_code = 200
            def json(self):
                return {"response": {"docs": []}}
        fake = types.ModuleType("requests")
        fake.get = lambda *a, **k: FakeResp()
        monkeypatch.setitem(sys.modules, "requests", fake)
        assert idr.resolve_hal("hal-00000000") is None

    def test_resolve_hal_network_error_returns_none(self, monkeypatch):
        import processing.id_resolution as idr
        import types
        fake = types.ModuleType("requests")
        def boom(*a, **k):
            raise RuntimeError("network down")
        fake.get = boom
        monkeypatch.setitem(sys.modules, "requests", fake)
        assert idr.resolve_hal("hal-01234567") is None


class TestAugment:

    def test_fills_gaps_only(self):
        from processing.id_resolution import augment_metadata_with_filename_ids
        meta = {"title": "", "authors": [], "doi": None, "arxiv_id": None}
        augment_metadata_with_filename_ids("2103.04185.pdf", meta)
        assert meta["arxiv_id"] == "2103.04185"

    def test_does_not_override_text_detected(self):
        from processing.id_resolution import augment_metadata_with_filename_ids
        meta = {"title": "", "authors": [], "doi": None, "arxiv_id": "9999.99999"}
        augment_metadata_with_filename_ids("2103.04185.pdf", meta)
        assert meta["arxiv_id"] == "9999.99999"  # text-detected wins

    def test_ssrn_routes_to_crossref_doi(self):
        from processing.id_resolution import augment_metadata_with_filename_ids
        meta = {"title": "", "authors": [], "doi": None, "arxiv_id": None}
        augment_metadata_with_filename_ids("SSRN-id1234567.pdf", meta)
        assert meta["doi"] == "10.2139/ssrn.1234567"

    def test_hal_id_set_for_resolver(self):
        from processing.id_resolution import augment_metadata_with_filename_ids
        meta = {"title": "", "authors": [], "doi": None, "arxiv_id": None}
        augment_metadata_with_filename_ids("hal-01234567.pdf", meta)
        assert meta["hal_id"] == "hal-01234567"
