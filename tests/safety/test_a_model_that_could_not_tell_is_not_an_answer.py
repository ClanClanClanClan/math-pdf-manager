"""The local model's "could not tell" must never look like a name.

MEASURED 2026-10-15 on the real "12 - To be sorted": five different
scans behind JSTOR's cover sheet were each handed the same 152
characters, and the model named all five "The Annals of probability" by
"000-00" -- five papers proposed under one journal's name. The fix
(``processing.model_input``) leaves such a page out and refuses an
answer whose authors are not names, every time it is used, so an answer
remembered before the fix cannot come back. Details and the measured
populations: ``tests/test_processing/test_model_input.py``.
"""
from __future__ import annotations

from tests.test_processing.test_model_input import (  # noqa: F401  (fixture)
    JSTOR_SHEET, extract, fitz_text, model, pages_pdf)


def test_scans_behind_a_cover_sheet_are_never_named_by_the_model(model, tmp_path):
    for i in range(5):
        meta = extract(pages_pdf(tmp_path / f"Download{i}.pdf", [JSTOR_SHEET] + [""] * (i + 1)))
        assert meta["title"] == "" and meta.get("title_source") != "llm"
        assert meta["lookups"]["model"]["state"] == "unknown"
        assert "JSTOR's cover sheet" in meta["lookups"]["model"]["reason"]
    assert model.texts == []


def test_a_remembered_non_name_is_refused(model, tmp_path):
    from processing import ingest, lookup_cache as lc

    pdf = pages_pdf(tmp_path / "x.pdf", ["Front matter the model once misread. " * 5])
    key = ingest._llm_key(model.model_file, "".join(fitz_text(pdf))[:4000])
    lc.put("llm", key, lc.Answer(lc.FOUND, {"title": "The Annals of probability",
                                            "authors": ["000-00"]}))
    meta = extract(pdf)
    assert meta["title"] == "" and meta.get("title_source") != "llm"
    assert meta["lookups"]["model"]["state"] == "unknown"
    assert model.texts == []          # refused from memory, not re-read
