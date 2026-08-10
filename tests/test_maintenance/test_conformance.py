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
