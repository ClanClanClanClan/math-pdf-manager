"""The spelling check, as conformance sees it.

Every file carrying a suspected typo was CANONICAL before this — 143 of
them, in the bucket the owner reads as settled. So the point of these
tests is less "does it detect" (that is test_typos.py) than "can a typo
ever again reach a verdict that reads as fine".
"""
from __future__ import annotations

import pytest

from maintenance import conformance as C
from maintenance.typos import build_corpus_stats


@pytest.fixture
def corpus():
    names = [f"A. - stochastic processes and control {i}" for i in range(30)]
    names += ["B. - stochstic control theory"]
    return build_corpus_stats(names)


class TestTheBucket:

    def test_a_typo_is_owner_work_not_a_code_fault(self):
        """In RED it would flip is_all_clear() permanently and file the
        spelling backlog under "the code is wrong"."""
        assert C.TYPO not in C.RED

    def test_a_typo_does_not_make_the_report_unclean(self):
        rep = C.ConformanceReport()
        rep.scanned = 10
        rep.counts = {C.CANONICAL: 9, C.TYPO: 1, C.NOT_EXAMINED: 0,
                      C.VIOLATION: 0, C.OWNER_QUEUE: 0, C.MECHANICAL: 0}
        assert rep.is_all_clear()

    def test_a_full_run_counts_a_typo_without_dying(self, tmp_path):
        """Two failures in one test, both real.

        counts[bucket] += 1 has no try/except around it, so a bucket
        missing from the initialiser raises KeyError on its first hit and
        takes the whole Conformance page down with it.

        And run() is the ONLY production caller of examine(); if it
        forgets to build and pass the corpus, the spelling check silently
        never happens anywhere. Nothing else would notice.
        """
        for i in range(30):
            (tmp_path / f"A. - stochastic processes and control {i}.pdf").write_bytes(b"%PDF-")
        (tmp_path / "B. - stochstic control theory.pdf").write_bytes(b"%PDF-")

        rep = C.run(tmp_path)
        assert C.TYPO in rep.counts, "bucket missing from the initialiser"
        assert rep.counts[C.TYPO] == 1, rep.counts
        assert rep.scanned == 31
        assert [f for f in rep.findings if f.bucket == C.TYPO], \
            "the finding must reach the report, not just the counter"

    def test_a_run_records_which_oracle_produced_it(self, tmp_path):
        """macOS's dictionaries are mutable — words the owner taught it,
        plus a counts file the OS rewrites as it goes. Two sweeps of an
        unchanged library gave 143 and then 147 during development. The
        fingerprint is what makes that visible instead of mysterious."""
        (tmp_path / "A. - a perfectly ordinary title.pdf").write_bytes(b"%PDF-")
        rep = C.run(tmp_path)
        assert rep.globals_.get("typo_oracle")


class TestExamine:

    def test_a_misspelling_is_reported_as_one(self, corpus, tmp_path):
        bucket, reason, detail = C.examine(
            "B. - stochstic control theory.pdf", tmp_path, corpus)
        assert bucket == C.TYPO
        assert reason == "suspected-typo"
        assert "stochstic" in detail and "stochastic" in detail

    def test_the_detail_carries_the_evidence_not_a_verdict(self, corpus,
                                                           tmp_path):
        _b, _r, detail = C.examine("B. - stochstic control theory.pdf",
                                   tmp_path, corpus)
        assert "→" in detail, "the owner needs to see what it would become"

    def test_without_a_corpus_the_check_is_SKIPPED_not_faked(self, tmp_path):
        """A corpus built from one filename has no frequent words, so
        every file would come back clean. Skipping is honest; guessing
        from a corpus of one is not."""
        bucket, _r, _d = C.examine("B. - stochstic control theory.pdf",
                                   tmp_path)
        assert bucket != C.TYPO

    def test_an_unusable_oracle_is_NOT_EXAMINED_never_canonical(
            self, tmp_path, monkeypatch):
        """The whole point of the third verdict. "I could not look" must
        not be spelled the same way as "I looked and it was fine"."""
        from maintenance import typos as T

        def dead(_name, _stats):
            return T.TypoReport(T.Verdict.UNKNOWN,
                                unknown_reason="no dictionary")
        monkeypatch.setattr(T, "examine_title", dead)
        bucket, reason, detail = C.examine("A. - a clean title.pdf",
                                           tmp_path, build_corpus_stats([]))
        assert bucket == C.NOT_EXAMINED
        assert reason == "typo-oracle-unavailable"
        assert detail == "no dictionary"
        assert bucket in C.RED, "an unexamined population must show as red"

    def test_a_raising_checker_is_a_violation_not_a_shrug(self, tmp_path,
                                                          monkeypatch):
        from maintenance import typos as T

        def boom(_name, _stats):
            raise RuntimeError("kaboom")
        monkeypatch.setattr(T, "examine_title", boom)
        bucket, reason, detail = C.examine("A. - a clean title.pdf",
                                           tmp_path, build_corpus_stats([]))
        assert bucket == C.VIOLATION
        assert reason == "typo-check-raised"
        assert "kaboom" in detail

    def test_a_clean_title_is_untouched_by_any_of_this(self, corpus, tmp_path):
        bucket, _r, _d = C.examine(
            "A. - stochastic processes and control 1.pdf", tmp_path, corpus)
        assert bucket != C.TYPO


class TestPrecedence:
    """A typo outranks a rename proposal, and is outranked by a bug."""

    def test_the_typo_wins_over_a_proposed_rename(self, tmp_path):
        """The rename proposed for the real Mortini line was "Amererican
        mathematical Monthly" — the casing engine building on top of a
        misspelling. Returning that proposal would ask the owner to
        approve a change derived from the error."""
        names = [f"A. - the american mathematical monthly {i}"
                 for i in range(30)]
        names += ["B. - Notes on Amererican Mathematical Monthly Problems"]
        corpus = build_corpus_stats(names)
        bucket, _r, _d = C.examine(
            "B. - Notes on Amererican Mathematical Monthly Problems.pdf",
            tmp_path, corpus)
        assert bucket == C.TYPO

    def test_a_structural_violation_still_outranks_a_typo(self, tmp_path,
                                                          corpus):
        """A file with no author/title separator has no title to spell
        check, and saying so is more useful than a spelling opinion."""
        bucket, reason, _d = C.examine("stochstic.pdf", tmp_path, corpus)
        assert bucket == C.NOT_EXAMINED
        assert reason == "no-author-title-separator"
