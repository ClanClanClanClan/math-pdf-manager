"""Library-health snapshot collector."""
from __future__ import annotations

from pathlib import Path

from maintenance.health import collect_library_health


def test_empty_library_all_fields_present(tmp_path):
    h = collect_library_health(tmp_path)
    for key in ["pdfs", "sidecars", "sidecar_coverage", "vocab_pending",
                "vocab_ruled", "model_trained_on", "undo_transactions",
                "last_tx_age_days", "trash_pdfs", "corpus_stats_age_days"]:
        assert key in h
    assert h["pdfs"] == 0 and h["sidecar_coverage"] == 0.0


def test_populated_library_counts(tmp_path):
    from processing.identity import PaperIdentity, enable_sidecar_mirror
    from processing.title_vocab import decide, record_pending
    from processing.undo_log import UndoLog
    enable_sidecar_mirror(tmp_path)
    d = tmp_path / "01 - Published papers" / "S"
    d.mkdir(parents=True)
    for i in range(4):
        p = d / f"Smith, J. - Paper {i}.pdf"
        p.write_bytes(b"%PDF")
        if i < 3:                       # sidecars for 3 of 4
            PaperIdentity().save(p, recompute_hash=False)
    record_pending(tmp_path, ["Zorglub"], example="x")
    decide(tmp_path, "Gadget", "common")
    log = UndoLog(log_dir=tmp_path / ".operation_log")
    log.begin_transaction("t")
    log.record_move(tmp_path / "a", tmp_path / "b")
    log.commit()
    trash = tmp_path / ".trash" / "duplicates"
    trash.mkdir(parents=True)
    (trash / "old.pdf").write_bytes(b"%PDF")

    h = collect_library_health(tmp_path)
    assert h["pdfs"] == 4
    assert h["sidecars"] == 3
    assert h["sidecar_coverage"] == 0.75
    assert h["vocab_pending"] == 1
    assert h["vocab_ruled"] == 1
    assert h["undo_transactions"] == 1
    assert h["trash_pdfs"] == 1
