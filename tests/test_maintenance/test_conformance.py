"""The standing check that replaces the owner's eye.

Every test here is written against a real incident: if the check would
not have caught it, the check is not worth running.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402

from maintenance.conformance import (  # noqa: E402
    CANONICAL, MECHANICAL, NOT_EXAMINED, OWNER_QUEUE, VIOLATION,
    check_config_reachability, diff_against, examine, load_previous, run, save,
)


@pytest.fixture()
def lib(tmp_path):
    from processing.identity import enable_sidecar_mirror
    (tmp_path / "01 - Published papers" / "S").mkdir(parents=True)
    (tmp_path / "12 - To be sorted").mkdir(parents=True)
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _add(lib, name, folder="01 - Published papers/S"):
    p = lib / folder / name
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_minimal_pdf(p, title="t", author="Smith, J.")
    return p


class TestTheFiveBuckets:

    def test_a_clean_name_is_canonical(self, lib):
        b, _r, _d = examine("Smith, J. - A note on stochastic control.pdf", lib)
        assert b == CANONICAL

    def test_an_unspaced_initial_is_mechanical(self, lib):
        b, _r, detail = examine("Shiryaev, A.N. - Stochastic disorder problems.pdf", lib)
        assert b == MECHANICAL
        assert "A. N." in detail

    def test_a_missing_separator_is_NOT_EXAMINED_and_says_why(self, lib):
        """Incident (1). The file the 6,180-file sweep never looked at."""
        b, reason, detail = examine("ProofCouncil.pdf", lib)
        assert b == NOT_EXAMINED
        assert reason == "no-author-title-separator"
        assert "never examined" in detail

    def test_a_title_ruling_is_OWNER_QUEUE_not_an_alarm(self, lib):
        """The good kind of pending: the code has an opinion and wants a
        ruling.  It must NOT be reported as a code defect."""
        b, reason, _d = examine(
            "Smith, J. - Trading signals In VIX futures.pdf", lib)
        assert b == OWNER_QUEUE
        assert b not in (NOT_EXAMINED, VIOLATION)


class TestInvariantsThatFire:
    """Each of these must FAIL LOUDLY, because each is a real bug class."""

    def test_a_rule_that_destroys_the_separator_is_a_violation(self, lib, monkeypatch):
        """Incident (2): "J. - , Propagation" -> "J. -, Propagation".

        Simulated by re-introducing the unguarded rule, so the test
        fails if the guard is ever removed from the real code.
        """
        import re
        from processing import filename_normalizer as fnorm

        def unguarded(name: str) -> str:
            # The rule exactly as it was before the guard: applied to the
            # RAW name, it eats the separator's own space.
            return re.sub(r"\s+,", ",", name)

        monkeypatch.setattr(fnorm, "normalize_filename", unguarded)
        b, reason, _d = examine(
            "Jourdain, B., Reygner, J. - , Propagation of chaos.pdf", lib)
        assert b == VIOLATION
        assert reason == "separator-count-changed"

    def test_the_real_rule_does_not_trip_it(self, lib):
        b, _r, _d = examine(
            "Jourdain, B., Reygner, J. - , Propagation of chaos.pdf", lib)
        assert b != VIOLATION

    def test_non_idempotence_is_a_violation(self, lib, monkeypatch):
        from processing import filename_normalizer as fnorm

        def unstable(name: str) -> str:
            return name + "x"       # f(f(x)) != f(x): no fixpoint

        monkeypatch.setattr(fnorm, "normalize_filename", unstable)
        b, reason, _d = examine("Smith, J. - A note.pdf", lib)
        assert b == VIOLATION and reason == "not-idempotent"


class TestConfigReachability:
    """Incident (4): a ruling the owner made that could never fire."""

    def _rule(self, lib, *phrases):
        from processing.title_vocab import vocab_path
        vp = vocab_path(lib)
        vp.parent.mkdir(parents=True, exist_ok=True)
        vp.write_text(json.dumps({"proper": [], "common": [],
                                  "phrases": list(phrases), "pending": {}},
                                 ensure_ascii=False))

    def test_a_working_ruling_is_silent(self, lib):
        self._rule(lib, "Euro-Par", "New York")
        assert check_config_reachability(lib) == []

    def test_a_ruling_that_cannot_fire_is_reported(self, lib, monkeypatch):
        """A ruling that is inert is indistinguishable from one never made.

        Simulated by dropping the library context, which is precisely
        what the dead '" " in p' filter amounted to for these two names.
        """
        self._rule(lib, "Euro-Par", "S-Plus")
        import processing.title_normalize as tn
        real = tn.propose_title_case

        monkeypatch.setattr(tn, "propose_title_case",
                            lambda title, library_root=None: real(title, None))
        out = check_config_reachability(lib)
        assert any(f.reason == "ruling-cannot-fire" for f in out), out
        assert any("Euro-Par" in f.detail for f in out), out


class TestTheReport:

    def test_run_classifies_and_never_writes(self, lib):
        _add(lib, "Smith, J. - A note on stochastic control.pdf")
        _add(lib, "Shiryaev, A.N. - Stochastic disorder problems.pdf")
        _add(lib, "ProofCouncil.pdf")
        before = sorted(p.name for p in lib.rglob("*.pdf"))
        rep = run(lib)
        assert sorted(p.name for p in lib.rglob("*.pdf")) == before
        assert rep.counts[CANONICAL] >= 1
        assert rep.counts[MECHANICAL] >= 1
        assert rep.counts[NOT_EXAMINED] >= 1
        assert "not_examined:no-author-title-separator" in rep.reasons

    def test_the_inbox_is_counted_but_not_judged(self, lib):
        _add(lib, "2401.07160v3.pdf", folder="12 - To be sorted")
        _add(lib, "Smith, J. - A note on stochastic control.pdf")
        rep = run(lib)
        assert rep.globals_["inbox_skipped"] == 1
        assert rep.counts[NOT_EXAMINED] == 0

    def test_coverage_can_never_exceed_100(self, lib):
        """The Stats page reports 100.14%, which is not a coverage."""
        _add(lib, "Smith, J. - A note on stochastic control.pdf")
        stray = lib / ".mathpdf-sidecars" / "01 - Published papers" / "S" / "ghost.meta.json"
        stray.parent.mkdir(parents=True, exist_ok=True)
        stray.write_text("{}")
        rep = run(lib)
        assert rep.globals_["coverage_pct"] <= 100.0
        assert rep.globals_["orphaned_records"] == 1

    def test_save_then_diff(self, lib):
        _add(lib, "Smith, J. - A note on stochastic control.pdf")
        rep = run(lib)
        p = save(lib, rep)
        assert p.exists()
        assert diff_against(rep, None) == {}
        older = dict(json.loads(p.read_text()))
        older["counts"] = dict(older["counts"], canonical=0)
        assert diff_against(rep, older)["canonical"] == rep.counts[CANONICAL]

    def test_load_previous_ignores_todays_own_report(self, lib):
        rep = run(lib)
        save(lib, rep)
        assert load_previous(lib) is None


class TestMathsIsMechanicalNotAJudgement:
    """A change produced only by the maths convention is arithmetic.

    The generic classifier compares letter signatures, so "l_r" -> "lᵣ"
    reads as a text REWRITE — the loudest category — for a change of
    typeface the owner already ruled on. Miscategorising it would train
    the owner to ignore the one bucket that must stay meaningful.
    """

    @pytest.mark.parametrize("name,frag", [
        ("Geiss, S. - Norms of diagonal operators in l_r.pdf", "lᵣ"),
        ("Erdos, P. - On numbers of the form ε_i in a set.pdf", "εᵢ"),
        ("Smith, J. - L^2 estimates for elliptic equations.pdf", "L²"),
    ])
    def test_a_maths_only_change_is_mechanical(self, lib, name, frag):
        b, reason, detail = examine(name, lib)
        assert b == MECHANICAL, (b, reason, detail)
        assert reason == "math-typography"
        assert frag in detail

    def test_a_casing_change_is_still_the_owners_call(self, lib):
        b, reason, _d = examine(
            "Smith, J. - Trading signals In VIX futures.pdf", lib)
        assert b == OWNER_QUEUE

    def test_maths_AND_casing_together_stays_the_owners_call(self, lib):
        """Only a PURE maths change is mechanical; if the casing also
        moved, the owner still has to see it.

        The vocabulary is required: a bare library proves no word common,
        so the caser would change nothing and the proposal really WOULD
        be maths-only.  Omitting it is how this test first passed while
        asserting the opposite of what it claims.
        """
        from processing.title_vocab import vocab_path
        vp = vocab_path(lib)
        vp.parent.mkdir(parents=True, exist_ok=True)
        vp.write_text(json.dumps(
            {"proper": [], "phrases": [], "pending": {},
             "common": ["estimates", "equations", "elliptic"]},
            ensure_ascii=False))
        b, _r, detail = examine(
            "Smith, J. - L^2 Estimates In elliptic Equations.pdf", lib)
        assert b == OWNER_QUEUE, detail


class TestTheCheckerDoesNotHaveItsOwnDisease:
    """Four ways this module said "fine" about things it had not settled.

    It exists because "I did not look" and "it is fine" were the same
    value. Each test below is a place where it made that same mistake.
    """

    def test_an_empty_scan_is_never_all_clear(self, lib):
        """An empty library, an unreadable folder or a mistyped root all
        reported "every invariant holds" — the same sentence, and the
        same lie, as the banner this module replaced."""
        rep = run(lib)
        assert rep.scanned == 0
        assert not rep.is_all_clear()

    def test_a_real_clean_library_IS_all_clear(self, lib):
        _add(lib, "Smith, J. - A note on stochastic control.pdf")
        rep = run(lib)
        assert rep.scanned == 1
        assert rep.is_all_clear() == (rep.red_count() == 0)

    def test_undecided_words_are_reported_not_buried(self, lib):
        """1,595 real files were CANONICAL while the caser had explicitly
        returned words it could not decide. The name IS a fixpoint, so
        canonical is right — but the open question must be visible."""
        b, reason, detail = examine(
            "Smith, J. - A study of Zorglub calculus.pdf", lib)
        assert b == CANONICAL
        assert reason == "rests-on-undecided-words"
        assert "Zorglub" in detail

    def test_a_settled_title_reports_no_uncertainty(self, lib):
        b, reason, _d = examine(
            "Smith, J. - A note on stochastic control.pdf", lib)
        assert b == CANONICAL and reason == ""

    def test_the_maths_refusal_list_is_consulted(self, lib):
        """math_typography.problems() exists to say "I looked and would
        not touch this"; not calling it left 5 files reported canonical
        with unbalanced brackets or nested scripts."""
        b, reason, _d = examine(
            "Geiss, S. - Absolutely L_{exp_q}-summing norms.pdf", lib)
        assert b == NOT_EXAMINED
        assert reason == "maths-refused"

    def test_trashed_records_are_not_orphans(self, lib):
        """133 of 159 "orphans" were the owner's own deleted papers — a
        red number that could never reach zero."""
        _add(lib, "Smith, J. - A note on stochastic control.pdf")
        ghost = (lib / ".mathpdf-sidecars" / ".trash" / "gone.meta.json")
        ghost.parent.mkdir(parents=True, exist_ok=True)
        ghost.write_text("{}")
        rep = run(lib)
        assert rep.globals_["orphaned_records"] == 0

    def test_library_wide_findings_are_not_counted_as_files(self, lib):
        """sum(counts) exceeded `scanned` by 15: a file-shaped metric
        carrying non-file entries."""
        _add(lib, "Smith, J. - A note on stochastic control.pdf")
        stray = lib / ".mathpdf-sidecars" / "x.meta.json"
        stray.parent.mkdir(parents=True, exist_ok=True)
        stray.write_text("{}")
        rep = run(lib)
        assert sum(rep.counts.values()) == rep.scanned
        assert rep.globals_["library_wide_findings"] >= 1
        assert rep.red_count() >= rep.globals_["library_wide_findings"]

    def test_out_of_scope_documents_are_counted(self, lib):
        """188 .djvu and 9 .epub files were in no bucket and no skip
        count, so five buckets summing to the PDF population read as
        "the library is accounted for"."""
        _add(lib, "Smith, J. - A note on stochastic control.pdf")
        (lib / "01 - Published papers" / "S" / "Old, B. - Scan.djvu").write_text("x")
        rep = run(lib)
        assert rep.globals_["documents_out_of_scope"] == 1


class TestTheCheckerDoesNotGradeItselfWithItself:
    """E4. The first version asked `proposed == canonicalise(title)` —
    a tautology, because the pipeline had just applied canonicalise. Any
    output that function produced, including a wrong one, was stamped
    "unambiguous, auto-applyable". Verification now uses an INDEPENDENT
    detector (core.text_processing.math_detector)."""

    def test_a_genuine_maths_change_is_recognised(self, lib):
        b, reason, _d = examine(
            "Smith, J. - L^2 estimates for elliptic equations.pdf", lib)
        assert b == MECHANICAL and reason == "math-typography"

    def test_a_change_touching_PROSE_is_not_called_maths(self, lib, monkeypatch):
        """The tautology's real cost: a converter that also mangled prose
        would still have been labelled mechanical. Make it mangle prose
        and confirm the independent detector refuses the label."""
        from processing import math_typography as mt
        real = mt.canonicalise
        monkeypatch.setattr(
            mt, "canonicalise",
            lambda t: real(t).replace("estimates", "ESTIMATES"))
        b, reason, _d = examine(
            "Smith, J. - L^2 estimates for elliptic equations.pdf", lib)
        assert reason != "math-typography", (b, reason)

    def test_the_independent_detector_is_what_decides(self):
        from maintenance.conformance import _change_confined_to_maths as C
        assert C("L^2 estimates", "L² estimates")
        assert not C("L^2 estimates", "L² bounds")
        assert not C("same", "same")


class TestConfigReachabilityHasTeeth:
    """E9/E10. load_vocab degrades a corrupt or missing file to an EMPTY
    vocabulary and never raises, so the probe loop ran zero times and
    returned [] — the same answer as "all fifteen rulings work"."""

    def _write(self, lib, text):
        from processing.title_vocab import vocab_path
        vp = vocab_path(lib)
        vp.parent.mkdir(parents=True, exist_ok=True)
        vp.write_text(text)
        return vp

    def test_a_corrupt_vocabulary_is_reported_not_silently_empty(self, lib):
        self._write(lib, "{not json")
        out = check_config_reachability(lib)
        assert any(f.reason == "vocabulary-unreadable" for f in out), out

    def test_rulings_lost_between_file_and_loader_are_reported(self, lib, monkeypatch):
        self._write(lib, json.dumps(
            {"proper": [], "common": [], "pending": {},
             "phrases": ["Euro-Par", "New York", "Root barrier"]}))
        from processing import title_vocab
        real = title_vocab.load_vocab
        monkeypatch.setattr(title_vocab, "load_vocab",
                            lambda root: dict(real(root), phrases=[]))
        out = check_config_reachability(lib)
        assert any(f.reason == "rulings-lost-on-load" for f in out), out
        assert any("3 in the file, 0 reached" in f.detail for f in out), out

    def test_a_healthy_vocabulary_is_still_silent(self, lib):
        self._write(lib, json.dumps(
            {"proper": [], "common": [], "pending": {},
             "phrases": ["Euro-Par", "New York"]}))
        assert check_config_reachability(lib) == []
