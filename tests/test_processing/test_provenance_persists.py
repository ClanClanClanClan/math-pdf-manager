"""Where a filename came from, recorded where it survives.

title_source was computed on four branches of ingest and read at exactly
one place, so not one of the 29,509 sidecars could say whether its name
came from the PDF's own metadata, from arXiv, from a local model, or
from the filename it arrived with. A name derived from an unverified
/Author field and one confirmed against arXiv looked identical
afterwards — which is how "Schnur, R. - Random matrices" sat in the
library indistinguishable from a correct filing.

I then reproduced the same defect: the first version of this work put
the fields in the result dict and nowhere else, so they died with the
function call.
"""
from __future__ import annotations

import json

import pytest

from processing.identity import PaperIdentity
from tests.test_processing.test_corroboration_and_registry import pdf_with_body


@pytest.fixture
def lib(tmp_path):
    for d in ("01 - Published papers", "03 - Working papers",
              "12 - To be sorted"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


def sidecar_of(lib, pdf):
    ident = PaperIdentity.load(pdf)
    return ident


class TestTheFieldsSurviveARoundTrip:

    def test_they_exist_and_persist(self, tmp_path):
        pdf = tmp_path / "Smith, J. - A paper.pdf"
        pdf.write_bytes(b"%PDF-")
        ident = PaperIdentity.load(pdf)
        ident.title_source = "arxiv"
        ident.author_source = "arxiv"
        ident.identification_state = "identified"
        ident.identification_note = ""
        ident.save(pdf)

        back = PaperIdentity.load(pdf)
        assert back.title_source == "arxiv"
        assert back.author_source == "arxiv"
        assert back.identification_state == "identified"

    def test_an_older_sidecar_without_them_still_loads(self, tmp_path):
        """29,509 sidecars predate these fields. Adding a field must not
        make the existing library unreadable."""
        pdf = tmp_path / "Smith, J. - A paper.pdf"
        pdf.write_bytes(b"%PDF-")
        ident = PaperIdentity.load(pdf)
        ident.save(pdf)
        path = next(tmp_path.rglob("*.meta.json"))
        payload = json.loads(path.read_text(encoding="utf-8"))
        for f in ("title_source", "author_source", "identification_state",
                  "identification_note"):
            payload.pop(f, None)
        path.write_text(json.dumps(payload), encoding="utf-8")

        back = PaperIdentity.load(pdf)
        assert back.title_source == ""
        assert back.identification_state == ""


class TestIngestWritesThem:

    def _body(self, who):
        return "\n".join([f"{who} studies free probability and matrices."] * 14)

    def test_a_filed_paper_records_where_its_name_came_from(self, lib):
        from processing.ingest import ingest_paper
        src = pdf_with_body(lib / "12 - To be sorted" / "drop.pdf",
                            title="Random matrix theory and free probability",
                            author="Roland Speicher",
                            body=self._body("Roland Speicher"))
        res = ingest_paper(src, library_root=lib, status="working",
                           dry_run=False)
        assert res["success"], res.get("error")

        filed = [p for p in lib.rglob("*.pdf")
                 if "12 - To be sorted" not in p.parts][0]
        ident = PaperIdentity.load(filed)
        assert ident.title_source == "embedded", (
            "the sidecar cannot say where the name came from")
        assert ident.author_source == "embedded"
        assert ident.identification_state == "identified"

    def test_the_reason_for_a_doubt_is_recorded_too(self, lib):
        """A held-back paper must carry WHY, or the review queue shows a
        list of filenames and no argument."""
        from processing.ingest import ingest_paper
        src = pdf_with_body(lib / "12 - To be sorted" / "drop2.pdf",
                            title="Random matrix theory and free probability",
                            author="Ricardo Schnur",
                            page_author="Roland Speicher",
                            body=self._body("Roland Speicher"))
        res = ingest_paper(src, library_root=lib, status="working",
                           dry_run=False)
        assert res["success"] is False
        assert res["identification_state"] == "needs_review"
        assert "Schnur" in res["identification_note"]
