"""The namer stopped recomputing per title what does not depend on the title.

Measured over the library's 25,251 in-scope names, read-only, 2026-10-15:
the per-file loop of Conformance went from 158 s to 78 s, with 0 of the
25,251 verdicts different. Three things had been redone for every name:

  * the caser re-filtered the same ~1,250 whitelist entries with a regex
    to find its 463 multi-word phrases (~3 ms of a ~6 ms call), and
    rebuilt the whitelist union itself;
  * the surname authority re-resolved its own file's path -- one lstat
    per folder above it, ~14 on the owner's Dropbox -- for every name;
  * ``Path.relative_to`` rebuilt the library root's ancestors per call.

A cache is only safe if it cannot go stale. The tests that matter most
here are the ones where the input DOES change -- a new ruling, a reloaded
config -- and the answer must change with it.
"""
from __future__ import annotations

import json
import os
import unicodedata
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import core.sentence_case as SC
import processing.author_surnames as AS
import processing.title_normalize as TN
from processing.identity import lexical_relative


# ---------------------------------------------------------------------------
# The caser's phrase list
# ---------------------------------------------------------------------------
_words = st.sampled_from(["New", "York", "Euro-Par", "S–Plus", "de", "Rham",
                          "Itô", "x", "1990", "", " ", "Root", "barrier",
                          "Hamilton–Jacobi", "l'Hôpital", "GL(3)"])
_phrase = st.lists(_words, min_size=1, max_size=4).map(" ".join)


@settings(max_examples=300, deadline=None)
@given(cands=st.frozensets(_phrase, max_size=25))
def test_the_phrase_list_is_what_filtering_would_give(cands):
    TN._MULTIWORD_MEMO.clear()
    got = TN._multiword_phrases(cands)
    want = {p for p in cands if len(TN._WORD_RE.findall(p)) > 1}
    assert {p for p, _ in got} == want
    assert len(got) == len(want)                    # no duplicates
    assert all(low == p.lower() for p, low in got)
    lengths = [len(p) for p, _ in got]
    assert lengths == sorted(lengths, reverse=True)
    # asked again, the same answer -- from the memo this time, not rebuilt
    assert TN._multiword_phrases(cands) is got


def test_the_memo_does_not_grow_without_bound():
    TN._MULTIWORD_MEMO.clear()
    for i in range(40):
        TN._multiword_phrases(frozenset({f"Word{i} Other"}))
    assert 1 <= len(TN._MULTIWORD_MEMO) <= 8


def _vocab(lib: Path, **kw) -> None:
    p = lib / ".mathpdf-config" / "title_vocab.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"proper": [], "common": [], "phrases": [], "pending": {}}
    data.update(kw)
    p.write_text(json.dumps(data))
    # load_vocab is keyed on mtime: make each rewrite visibly newer.
    t = p.stat().st_mtime + 10 + len(json.dumps(data))
    os.utime(p, (t, t))


def test_a_new_proper_phrase_takes_effect_at_once(tmp_path):
    """The stale-cache case. In Title-Cased prose -- a capital run too long
    to be a name -- "Barrier" is judged alone and, being provably common,
    lowered. Once the owner records "Root Barrier" as a name it must be
    protected on the very next call, not after a restart; withdrawn, the
    protection must go with it."""
    title = "A Survey Of The Root Barrier Construction In Probability"
    common = ["barrier", "survey", "construction"]
    _vocab(tmp_path, common=common)
    before = TN.propose_title_case(title, tmp_path).proposed
    assert before == "A survey of the Root barrier construction in probability"
    _vocab(tmp_path, common=common, proper=["Root Barrier"])
    assert TN.propose_title_case(title, tmp_path).proposed == \
        "A survey of the Root Barrier construction in probability"
    _vocab(tmp_path, common=common)
    assert TN.propose_title_case(title, tmp_path).proposed == before


def test_a_reloaded_config_is_seen(monkeypatch):
    """The sentence-case config is REPLACED when reloaded. A union cached
    against the old one would keep the old whitelist for the session."""
    one = {"capitalization_whitelist": ["Alpha Beta"]}
    monkeypatch.setattr(SC, "_CONFIG_CACHE", one)
    assert "Alpha Beta" in TN._whitelists()
    two = {"capitalization_whitelist": ["Gamma Delta"],
           "proper_adjectives": ["Gaussian"]}
    monkeypatch.setattr(SC, "_CONFIG_CACHE", two)
    wl = TN._whitelists()
    assert "Gamma Delta" in wl and "Gaussian" in wl and "Alpha Beta" not in wl


def test_a_cleared_config_is_reloaded_from_disk(monkeypatch):
    monkeypatch.setattr(SC, "_CONFIG_CACHE", {"capitalization_whitelist": ["Zz Qq"]})
    assert "Zz Qq" in TN._whitelists()
    SC._CONFIG_CACHE.clear()          # what tests/audit does between cases
    wl = TN._whitelists()
    assert "Zz Qq" not in wl
    assert len(wl) > 100              # the real config.yaml's entries


def test_the_union_is_built_once_per_config():
    assert TN._whitelists() is TN._whitelists()


def test_nobody_can_poison_the_shared_union():
    with pytest.raises(AttributeError):
        TN._whitelists().add("Poison")


# ---------------------------------------------------------------------------
# The surname authority's path
# ---------------------------------------------------------------------------
def test_the_authority_path_is_the_one_it_always_was():
    want = (Path(AS.__file__).resolve().parents[2]
            / "config" / "author_surnames.yaml")
    assert AS._config_path() == want
    assert want.is_file()


def test_the_authority_path_costs_no_lstat_after_the_first(monkeypatch):
    AS._config_path()
    calls = []
    real = os.lstat

    def spy(*a, **k):
        calls.append(a)
        return real(*a, **k)
    monkeypatch.setattr(os, "lstat", spy)
    for _ in range(50):
        AS._config_path()
    assert calls == []


# ---------------------------------------------------------------------------
# lexical_relative == Path.relative_to
# ---------------------------------------------------------------------------
_part = st.sampled_from(["a", "A", "b", "Maths", "..", "x y",
                         unicodedata.normalize("NFC", "é"),
                         unicodedata.normalize("NFD", "é"), "01 - P"])


def _mk(absolute: bool, parts: list) -> Path:
    return Path("/" if absolute else ".", *parts)


@settings(max_examples=500, deadline=None)
@given(abs_p=st.booleans(), abs_r=st.booleans(),
       p=st.lists(_part, max_size=5), r=st.lists(_part, max_size=4),
       prefix=st.booleans())
def test_lexical_relative_agrees_with_relative_to(abs_p, abs_r, p, r, prefix):
    root = _mk(abs_r, r)
    path = _mk(abs_r, r + p) if prefix else _mk(abs_p, p)
    try:
        want = path.relative_to(root)
    except ValueError:
        with pytest.raises(ValueError):
            lexical_relative(path, root)
        return
    got = lexical_relative(path, root)
    assert got == want and str(got) == str(want) and type(got) is type(want)


@pytest.mark.parametrize("path, root, want", [
    ("/L/a/b.pdf", "/L", "a/b.pdf"),
    ("/L", "/L", "."),                       # itself
    ("/", "/", "."),
    ("/L/a", "/", "L/a"),
    ("a/b", ".", "a/b"),
])
def test_lexical_relative_worked_cases(path, root, want):
    assert lexical_relative(Path(path), Path(root)) == Path(want)


@pytest.mark.parametrize("path, root", [
    ("/Lx/a.pdf", "/L"),                     # a prefix of the NAME is not a parent
    ("/l/a.pdf", "/L"),                      # lexical: APFS would fold, this does not
    ("/L/a.pdf", "L"),                       # absolute against relative
    ("L/a.pdf", "/L"),
    ("/a.pdf", "."),
    (unicodedata.normalize("NFD", "/é/a.pdf"), unicodedata.normalize("NFC", "/é")),
])
def test_lexical_relative_refuses_what_relative_to_refuses(path, root):
    with pytest.raises(ValueError):
        Path(path).relative_to(Path(root))
    with pytest.raises(ValueError):
        lexical_relative(Path(path), Path(root))
