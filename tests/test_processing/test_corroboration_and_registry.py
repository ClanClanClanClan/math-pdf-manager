"""Ask the paper, and ask the registry.

Both sources of truth were sitting unused. The first 4,000 characters of
every PDF are extracted at ingest and were read by nothing but the LLM
prompt. And 1,758 of 2,073 inbox papers carry an arXiv id in the
filename, for 1,688 of which the API lookup was SKIPPED because the PDF
happened to carry an embedded /Title.
"""
from __future__ import annotations

import pytest

from processing.ingest import (
    _is_bare_identifier,
    _NON_ARTICLE_DOI_PREFIXES,
    corroborate,
)


BODY = ("Lecture Notes on Random Matrices. Saarland University. "
        "Prof. Dr. Roland Speicher. We study free probability. ") * 8


class TestTheePaperIsAsked:

    def test_an_author_who_is_not_in_his_own_paper_is_flagged(self):
        """The real case: 2009.05157 embeds /Title "Random matrices" and
        /Author "Ricardo Schnur". arXiv and the paper's own first page
        both say Roland Speicher. It filed as `Schnur, R.` and the gate
        and the watcher both called it a success."""
        doubts = corroborate("Random matrices", ["Schnur"], BODY)
        assert doubts and "Schnur" in doubts[0]

    def test_a_scanner_default_title_is_flagged(self):
        assert corroborate("Scannable Document", [], BODY)

    def test_a_true_claim_passes(self):
        assert corroborate("Lecture notes on random matrices",
                           ["Speicher"], BODY) == []

    @pytest.mark.parametrize("author,in_text", [
        ("Obłój", "Obloj"),            # PDF text is often ASCII-ised
        ("Øksendal", "Oksendal"),
        ("Bołbotowski", "Bolbotowski"),
        ("Schützenberger", "Schutzenberger"),
        ("Itô", "Ito"),
        # …and the form a LaTeX-produced PDF actually extracts as: the
        # accent arrives as a FREE-STANDING spacing character sitting
        # BEFORE its letter. Measured on the real inbox, this alone
        # accounted for 10 of 12 corroboration flags, every one false.
        ("Röckner", "R¨ockner"),
        ("Grüne", "Gr¨une"),
        ("Bañuelos", "Ban˜uelos"),
        ("Bréhier", "Br´ehier"),
        ("Laurière", "Lauri`ere"),
        ("Figueroa-López", "Figueroa-L´opez"),
    ])
    def test_accented_surnames_are_not_false_positives(self, author, in_text):
        """The trap an earlier attempt fell into, and the version of it
        that actually bites.

        The two spellings must DIFFER, or the test cannot tell a correct
        fold from no fold at all: folding both sides identically matches
        either way. In the wild the metadata carries "Obłój" while the
        extracted page text carries "Obloj" — and NFKD leaves "ł" and "ø"
        untouched, so a naive ASCII encode deletes them and "Obłój"
        becomes "Obj", which matches nothing.
        """
        text = (f"A paper by {in_text} on Skorokhod embeddings in "
                f"continuous time and related problems. ") * 8
        assert corroborate("A paper on Skorokhod embeddings", [author],
                           text) == []

    def test_a_paper_with_no_text_layer_produces_no_complaints(self):
        """Silence is not evidence. A scanned paper has no text at all,
        and complaining about everything would bury the real findings."""
        assert corroborate("Anything", ["Nobody"], "") == []
        assert corroborate("Anything", ["Nobody"], "short") == []

    def test_a_partly_matching_title_passes_and_a_mostly_absent_one_does_not(self):
        """Pins the threshold from BOTH sides. Requiring every word would
        flag any title a publisher reordered or truncated; requiring none
        would catch nothing."""
        # 3 of 5 content words present -> tolerated. The absent two have
        # to be genuinely absent: my first version used five words that
        # were ALL in the body, so it could not tell the threshold from
        # any other threshold and the mutant lived.
        assert corroborate(
            "Random matrices probability wireless scheduling", ["Speicher"],
            BODY) == []
        # 2 of 5 -> flagged. Chosen to sit BETWEEN a third and a half, so
        # it pins the bar from below as well: at a third this would pass.
        doubts = corroborate(
            "Ergodic capacity scheduling random matrices",
            ["Speicher"], BODY)
        assert doubts and "mostly absent" in doubts[0]


class TestBareIdentifierDetection:

    @pytest.mark.parametrize("stem", [
        "2105.10623v1", "10.3934_puqr.2025024", "s00245-025-10319-6",
        "1-s2.0-S0022247X26001174-main", "Download222", "90019751",
        "25m1755084", "main", "paper",
    ])
    def test_an_identifier_is_recognised(self, stem):
        assert _is_bare_identifier(stem)

    @pytest.mark.parametrize("stem", [
        "Yor, M. - Some aspects of Brownian motion",
        "Mathematical Finance - 2026 - Fan - One-Dimensional Nonlinear",
        "Reflected BSDEs and optimal stopping",
    ])
    def test_a_real_title_is_not(self, stem):
        assert not _is_bare_identifier(stem)


class TestTheRegistryIsConsultedWhenTheFilenameIsJunk:

    @pytest.fixture
    def fake_arxiv(self, monkeypatch):
        """No network in tests. Returns a fixed Atom document."""
        calls = []

        _ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
 <entry>
  <title>Lecture Notes on Random Matrices</title>
  <author><name>Roland Speicher</name></author>
 </entry>
</feed>"""

        class Resp:
            status_code = 200
            text = _ATOM
            # The caller parses .content, not .text. A fake that carries
            # only one of them fails in a way that looks like the feature
            # is broken — which is exactly what it did on the first run.
            content = _ATOM.encode("utf-8")

        def fake_get(url, *a, **k):
            calls.append(url)
            return Resp()

        import requests
        monkeypatch.setattr(requests, "get", fake_get)
        return calls

    def test_an_embedded_title_no_longer_blocks_the_lookup(
            self, tmp_path, fake_arxiv):
        """The inversion. 96% of arXiv-named arrivals were skipping the
        registry purely because the PDF carried some /Title."""
        from tests.test_processing.test_stage0_fixes import write_pdf
        from processing.ingest import extract_metadata_from_pdf
        pdf = write_pdf(tmp_path / "2009.05157v1.pdf",
                        title="Random matrices", author="Ricardo Schnur")
        meta = extract_metadata_from_pdf(pdf)
        assert fake_arxiv, "the arXiv API was not consulted"
        assert meta["title_source"] == "arxiv"
        assert meta["title"] == "Lecture Notes on Random Matrices"
        # Assert the authoritative field directly. Falling back with
        # "or [authors_raw]" would let the embedded value satisfy a test
        # about the registry replacing it.
        assert meta["authors"] == ["Roland Speicher"]
        assert meta["author_source"] == "arxiv"

    def test_a_human_named_file_is_left_alone(self, tmp_path, fake_arxiv):
        """If someone already named it properly, their name wins and we
        do not spend a request second-guessing them."""
        from tests.test_processing.test_stage0_fixes import write_pdf
        from processing.ingest import extract_metadata_from_pdf
        pdf = write_pdf(
            tmp_path / "Speicher, R. - Lecture notes on random matrices.pdf",
            title="Lecture notes on random matrices", author="Speicher, R.")
        extract_metadata_from_pdf(pdf)
        assert not fake_arxiv, "a properly named paper triggered a lookup"


class TestFunderDoisAreRefused:
    """The extractor takes the FIRST "10.xxxx/" in three pages, and 9 of
    219 (4.1%) are a Zenodo deposit or a grant acknowledgement rather
    than the article."""

    @pytest.mark.parametrize("doi", ["10.5281/zenodo.1234567",
                                     "10.54499/UIDB/00297/2020",
                                     "10.69777/12345"])
    def test_a_non_article_prefix_is_listed(self, doi):
        assert doi.startswith(_NON_ARTICLE_DOI_PREFIXES)

    @pytest.mark.parametrize("doi", ["10.1007/s00780-023-00504-2",
                                     "10.1016/j.spa.2024.104321",
                                     "10.3934/naco.2025023"])
    def test_a_real_article_doi_is_not(self, doi):
        assert not doi.startswith(_NON_ARTICLE_DOI_PREFIXES)


def pdf_with_body(path, *, title, author, body, page_author=None) -> "Path":
    """A PDF with a real text layer, so fulltext_sample is populated.

    The hand-rolled builders elsewhere in the suite write no content
    stream, so extraction returns "" and corroboration correctly declines
    to judge — which means they cannot exercise this path at all.
    """
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), title, fontsize=14)
    # page_author defaults to author; passing a DIFFERENT one is the whole
    # point of the Schnur/Speicher case — the metadata claims one person
    # and the paper's own front matter names another.
    page.insert_text((72, 130), author if page_author is None else page_author,
                     fontsize=11)
    y = 170
    for line in body.split("\n"):
        page.insert_text((72, y), line, fontsize=9)
        y += 12
    doc.set_metadata({"title": title, "author": author})
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


class TestCorroborationReachesTheGate:
    """The unit tests above prove the predicate works. This proves the
    pipeline asks it — a mutation that disabled the call at the gate
    survived every one of them."""

    @pytest.fixture
    def lib(self, tmp_path):
        for d in ("01 - Published papers", "03 - Working papers",
                  "12 - To be sorted"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        return tmp_path

    def _body(self):
        return ("\n".join(
            ["We study free probability and random matrix theory."] * 14))

    def test_an_author_absent_from_the_paper_is_held_back(self, lib):
        """The Schnur/Speicher shape: plausible metadata, wrong person."""
        from processing.ingest import ingest_paper
        src = pdf_with_body(lib / "12 - To be sorted" / "whatever.pdf",
                            title="Random matrix theory and free probability",
                            author="Ricardo Schnur",
                            page_author="Roland Speicher",
                            body=self._body())
        result = ingest_paper(src, library_root=lib, status="working",
                              dry_run=False)
        assert result["success"] is False
        assert result["identification_state"] == "needs_review"
        assert "Schnur" in result["error"]
        assert not [p for p in lib.rglob("*.pdf")
                    if "12 - To be sorted" not in p.parts]

    def test_an_author_present_in_the_paper_files_normally(self, lib):
        from processing.ingest import ingest_paper
        body = "\n".join(
            ["Roland Speicher studies free probability and random matrices."]
            * 14)
        src = pdf_with_body(lib / "12 - To be sorted" / "whatever2.pdf",
                            title="Random matrix theory and free probability",
                            author="Roland Speicher", body=body)
        result = ingest_paper(src, library_root=lib, status="working",
                              dry_run=False)
        assert result["success"] is True, result.get("error")
        assert result["identification_state"] == "identified"

    def test_the_provenance_of_the_name_is_recorded(self, lib):
        """title_source was computed on four branches and read at one
        place, so no sidecar in the library says where its name came
        from."""
        from processing.ingest import ingest_paper
        body = "\n".join(
            ["Roland Speicher studies free probability and random matrices."]
            * 14)
        src = pdf_with_body(lib / "12 - To be sorted" / "whatever3.pdf",
                            title="Random matrix theory and free probability",
                            author="Roland Speicher", body=body)
        result = ingest_paper(src, library_root=lib, status="working",
                              dry_run=False)
        assert result["title_source"] == "embedded"
        assert result["author_source"] == "embedded"


class TestTheLookupIsBatched:
    """Inverting the gate widened the lookup from 70 papers to 1,758.
    Measured cost: 7.0 s per single-id call and 6.2 s per 25-id call, so
    the inbox is 205 minutes one at a time and 7.3 minutes batched. The
    inversion without the batching would have handed back the exact cost
    objection it was meant to refute.
    """

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        from processing.ingest import _ARXIV_CACHE
        _ARXIV_CACHE.clear()
        yield
        _ARXIV_CACHE.clear()

    def _feed(self, ids):
        entries = "".join(
            f"<entry><title>Paper {i}</title>"
            f"<author><name>Author {i}</name></author></entry>"
            for i in ids)
        return ('<?xml version="1.0"?><feed '
                f'xmlns="http://www.w3.org/2005/Atom">{entries}</feed>')

    @pytest.fixture
    def counting_api(self, monkeypatch):
        calls = []

        def fake_get(url, *a, **k):
            ids = url.split("id_list=")[1].split("&")[0].split(",")
            calls.append(ids)

            class R:
                status_code = 200
            R.content = self._feed(ids).encode()
            return R

        import requests
        monkeypatch.setattr(requests, "get", fake_get)
        return calls

    def test_sixty_ids_take_three_requests_not_sixty(self, counting_api):
        from processing.ingest import prefetch_arxiv
        ids = [f"24{i:02d}.{i:05d}" for i in range(60)]
        assert prefetch_arxiv(ids) == 60
        assert len(counting_api) == 3, (
            f"expected ceil(60/25)=3 requests, made {len(counting_api)}")

    def test_a_prefetched_id_costs_no_further_request(self, counting_api):
        from processing.ingest import lookup_arxiv, prefetch_arxiv
        prefetch_arxiv(["2401.00001"])
        before = len(counting_api)
        assert lookup_arxiv("2401.00001")["title"] == "Paper 2401.00001"
        assert len(counting_api) == before, "the cache was not consulted"

    def test_the_version_suffix_does_not_defeat_the_cache(self, counting_api):
        """Filenames carry "v1"/"v2"; the API is keyed on the bare id, and
        missing this would double every request."""
        from processing.ingest import lookup_arxiv, prefetch_arxiv
        prefetch_arxiv(["2401.00001v3"])
        before = len(counting_api)
        lookup_arxiv("2401.00001")
        lookup_arxiv("2401.00001v7")
        assert len(counting_api) == before

    def test_duplicate_ids_are_requested_once(self, counting_api):
        from processing.ingest import prefetch_arxiv
        prefetch_arxiv(["2401.00001"] * 40)
        assert len(counting_api) == 1
        assert counting_api[0] == ["2401.00001"]

    def test_a_failing_batch_does_not_raise(self, monkeypatch):
        """Offline must degrade, not stop a 2,000-paper run."""
        import requests

        def boom(*a, **k):
            raise requests.exceptions.ConnectionError("offline")
        monkeypatch.setattr(requests, "get", boom)
        from processing.ingest import prefetch_arxiv
        assert prefetch_arxiv(["2401.00001", "2401.00002"]) == 0
