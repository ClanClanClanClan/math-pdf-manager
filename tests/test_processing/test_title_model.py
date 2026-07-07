"""Self-trained proper-vs-common word model (pure-Python NB)."""
from __future__ import annotations

import pytest

from processing.title_model import (
    _train_nb,
    harvest_examples,
    load_model,
    model_path,
    score_word,
    suggest,
    train_model,
)

# A tiny but morphologically representative synthetic corpus.
PROPER_WORDS = [
    "Kolmogorov", "Smirnov", "Petrov", "Malliavin", "Skorokhod", "Sobolev",
    "Zakai", "Novikov", "Girsanov", "Fourier", "Poincare", "Hadamard",
    "Lindeberg", "Feller", "Wasserstein", "Bernstein", "Hoeffding",
    "Chernov", "Varadhan", "Freidlin", "Dynkin", "Bellman", "Pontryagin",
    "Krylov", "Safonov", "Ladyzhenskaya", "Uraltseva", "Nirenberg",
    "Gagliardo", "Moser", "Harnack", "Schauder", "Perron", "Frobenius",
]
COMMON_WORDS = [
    "existence", "uniqueness", "solutions", "equations", "backward",
    "stochastic", "differential", "control", "optimal", "theory",
    "applications", "convergence", "estimates", "boundary", "problems",
    "methods", "analysis", "random", "measure", "process", "martingale",
    "diffusion", "volatility", "utility", "portfolio", "insurance",
    "asymptotic", "representation", "regularity", "viscosity", "monotone",
    "quadratic", "reflected", "singular", "horizon",
]


def _examples():
    return [(w, "proper") for w in PROPER_WORDS] + \
           [(w, "common") for w in COMMON_WORDS]


class TestNaiveBayes:

    def test_generalizes_to_unseen_words(self):
        model = _train_nb(_examples())
        # Unseen surname-shaped words score proper…
        assert score_word("Egorov", model) > 0.5
        assert score_word("Tikhonov", model) > 0.5
        # …and unseen ordinary academic words score common.
        assert score_word("integrability", model) < 0.5
        assert score_word("computations", model) < 0.5

    def test_score_bounds(self):
        model = _train_nb(_examples())
        for w in ["Kolmogorov", "existence", "xyz", "Q"]:
            assert 0.0 <= score_word(w, model) <= 1.0

    def test_suggest_returns_ruling_and_confidence(self):
        model = _train_nb(_examples())
        ruling, conf = suggest("Egorov", model)
        assert ruling in ("proper", "common")
        assert 0.5 <= conf <= 1.0


class TestTrainPersist:

    def _fake_harvest(self, monkeypatch, n=40):
        import processing.title_model as tm
        monkeypatch.setattr(
            tm, "harvest_examples",
            lambda lib: _examples() * (max(1, 200 // len(_examples())) + 1),
        )

    def test_train_saves_model_with_metrics(self, tmp_path, monkeypatch):
        self._fake_harvest(monkeypatch)
        m = train_model(tmp_path)
        assert m["metrics"]["held_out"] > 0
        assert 0.0 <= m["metrics"]["accuracy"] <= 1.0
        assert model_path(tmp_path).exists()
        loaded = load_model(tmp_path)
        assert loaded and loaded["trained_on"] == m["trained_on"]
        # Round-trip scoring works on the deserialized model.
        assert 0.0 <= score_word("Egorov", loaded) <= 1.0

    def test_too_few_examples_raises(self, tmp_path, monkeypatch):
        import processing.title_model as tm
        monkeypatch.setattr(tm, "harvest_examples", lambda lib: _examples())
        with pytest.raises(ValueError):
            train_model(tmp_path)

    def test_missing_model_loads_none(self, tmp_path):
        assert load_model(tmp_path) is None


class TestHarvest:

    def test_rulings_and_surnames_harvested(self, tmp_path, monkeypatch):
        # Isolate from corpus stats (empty lib) — rulings + filenames only.
        from processing.title_vocab import decide
        from processing.identity import enable_sidecar_mirror
        enable_sidecar_mirror(tmp_path)
        decide(tmp_path, "Zorglub", "proper")
        decide(tmp_path, "gadget", "common")
        d = tmp_path / "01 - Published papers" / "D"
        d.mkdir(parents=True)
        (d / "Dalang, R. C., Possamai, D. - Some title.pdf").write_bytes(b"%PDF")
        ex = harvest_examples(tmp_path)
        words = {(w, l) for w, l in ex}
        assert ("Zorglub", "proper") in words
        assert ("gadget", "common") in words
        assert ("Dalang", "proper") in words
        assert ("Possamai", "proper") in words
