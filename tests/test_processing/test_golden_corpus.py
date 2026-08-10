"""The naming pipeline's frozen behaviour, plus proof the guards matter.

Two jobs, and they are different:

* ``test_no_drift`` compares the pipeline's output for 425 inputs against
  a checked-in expectations file. It does not judge whether the output is
  RIGHT — it guarantees that if anyone changes it, a human sees the diff
  in review instead of discovering it on 29,000 files.

* ``TestEveryGuardIsLoadBearing`` is the other half. A frozen expectation
  is worthless if the code that produces it is dead, and this project has
  already shipped three tests that passed against deliberately broken
  code. Each case here breaks one guard on purpose and asserts the corpus
  notices.

Regenerate after an intentional change:
    PYTHONPATH=src python3.12 -m tests.harness.golden --bless
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
import golden  # noqa: E402


def test_the_corpus_is_not_empty_and_covers_both_sources():
    """A corpus that quietly lost its cases would pass every drift test."""
    cases = golden.load_cases()
    assert len(cases) > 400, len(cases)
    assert sum(1 for _i, why in cases if why == "library") > 350
    assert sum(1 for _i, why in cases if why != "library") > 30


def test_the_frozen_vocabulary_is_present():
    """Running without the owner's rulings exercises a different code
    path than production — the mistake that hid the inert phrase pass."""
    v = json.loads((Path(golden.__file__).with_name("golden_vocab.json")).read_text())
    assert v.get("phrases"), "the phrase rulings must be frozen with the corpus"
    lib = golden._fixture_library()
    from processing.title_vocab import load_vocab
    assert load_vocab(lib)["phrases"], "the fixture library must expose them"


def test_no_drift():
    expected = golden.load_expected()
    assert expected, "run --bless to create the expectations file"
    got = golden.compute()
    drifted = {k: (expected.get(k), v) for k, v in got.items()
               if expected.get(k) != v}
    missing = [k for k in expected if k not in got]
    report = "\n".join(
        f"\n  in : {k}\n  was: {was}\n  now: {now}"
        for k, (was, now) in list(drifted.items())[:15])
    assert not drifted, (
        f"{len(drifted)} of {len(got)} outputs changed.\n"
        f"If this was intentional, re-bless and put the diff in review."
        f"{report}")
    assert not missing, f"cases vanished from the corpus: {missing[:5]}"


class TestEveryGuardIsLoadBearing:
    """Break a guard, and the corpus must notice.

    Without this, a rule could quietly become dead code and every test
    would still pass — which is exactly how the phrase pass sat inert
    while its own unit tests were green.
    """

    def _drift_count(self) -> int:
        expected, got = golden.load_expected(), golden.compute()
        return sum(1 for k, v in got.items() if expected.get(k) != v)

    def test_baseline_is_clean(self):
        assert self._drift_count() == 0

    def test_breaking_the_maths_converter_is_detected(self, monkeypatch):
        from processing import math_typography as mt
        monkeypatch.setattr(mt, "canonicalise", lambda t: t)
        assert self._drift_count() > 0

    def test_breaking_the_all_or_nothing_rule_is_detected(self, monkeypatch):
        """Convert character by character, the way the old code did."""
        from processing import math_typography as mt
        real = mt._as_script

        def per_char(text, table):
            return "".join(table.get(c, c) for c in text)
        monkeypatch.setattr(mt, "_as_script", per_char)
        assert self._drift_count() > 0

    def test_breaking_the_author_spacing_is_detected(self, monkeypatch):
        from processing import move_normalizer as mn
        monkeypatch.setattr(mn, "normalize_authors_in_name",
                            lambda n: (n, False))
        assert self._drift_count() > 0

    def test_losing_the_owner_rulings_is_detected(self, monkeypatch):
        """The inert-phrase-pass bug, reproduced."""
        from processing import title_vocab
        real = title_vocab.load_vocab
        monkeypatch.setattr(
            title_vocab, "load_vocab",
            lambda root: dict(real(root), phrases=[]))
        assert self._drift_count() > 0

    def test_the_changed_flag_lying_is_detected(self, monkeypatch):
        """A correct `proposed` that no caller applies, because `changed`
        compared against a rebound local. Cost: every phrase ruling."""
        from processing import title_normalize as tn
        real = tn.propose_title_case

        def lying(title, library_root=None):
            p = real(title, library_root)
            return tn.TitleProposal(original=p.proposed, proposed=p.proposed,
                                    uncertain=p.uncertain)
        monkeypatch.setattr(tn, "propose_title_case", lying)
        assert self._drift_count() > 0
