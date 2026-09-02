"""The Name-phrases section on Settings.

A phrase ruling is the only vocabulary decision that can repair names
already in the library, and until this section existed the API had tests
but no production caller at all -- which in this project means it was
not shipped, because the owner does not use a terminal.

Two properties matter enough to pin:

1. It must not walk the library on RENDER. Every page in this cockpit
   obeys that rule; the sidebar attention badge exists solely to obey it,
   and the owner has already reported the Spelling page feeling laggy.
2. It must be reachable. A section defined but never called is the exact
   state decide_phrase was in before.
"""
import inspect
import sys

import pytest

from tests.ui.test_cockpit_smoke import st_stub  # noqa: F401  (fixture)


def _cockpit(st_stub):
    import ui.cockpit as cockpit
    return cockpit


def test_the_settings_page_actually_calls_the_section(st_stub):  # noqa: F811
    """Defined-but-never-called is the failure this section exists to fix."""
    cockpit = _cockpit(st_stub)
    src = inspect.getsource(cockpit.render_settings)
    assert "_render_phrase_rulings(" in src, (
        "the Name-phrases section is not reachable from Settings")


def test_it_is_a_section_and_not_a_page(st_stub):  # noqa: F811
    """Underscore-prefixed, so the page auto-discovery ignores it.

    The smoke suite treats every ``render_*`` attribute as a page and
    renders it standalone; a section that is really part of Settings
    would be smoke-tested out of context and, worse, would silently
    become a nav entry nobody routed.
    """
    cockpit = _cockpit(st_stub)
    assert hasattr(cockpit, "_render_phrase_rulings")
    assert not hasattr(cockpit, "render_phrase_rulings")


def test_rendering_draws_something(st_stub, tmp_path):  # noqa: F811
    """Against an EMPTY library — no rulings, no files, still a surface."""
    cockpit = _cockpit(st_stub)
    before = len(st_stub.calls)
    cockpit._render_phrase_rulings(tmp_path)
    assert len(st_stub.calls) > before, "the section drew nothing at all"


def test_it_does_NOT_walk_the_library_on_render(st_stub, tmp_path, monkeypatch):  # noqa: F811
    """The index is a ~9s walk; it belongs behind the button, not on render.

    Buttons return False under the stub, so a render that touches the
    index here is one that would touch it on every visit to Settings.
    """
    cockpit = _cockpit(st_stub)
    called = []

    def _boom(*a, **kw):
        called.append(a)
        return []

    monkeypatch.setattr(cockpit, "_search_index_cached", _boom)
    cockpit._render_phrase_rulings(tmp_path)
    assert not called, (
        "the section built the filename index on render; that is a library "
        "walk on every visit to Settings")


def test_a_broken_whitelist_does_not_take_the_page_down(st_stub, tmp_path,
                                                        monkeypatch):  # noqa: F811
    """Settings hosts the watcher and sign-in controls too.

    If a malformed config could raise here, one bad entry would cost the
    owner every other setting on the page.
    """
    cockpit = _cockpit(st_stub)
    import processing.title_normalize as tn
    monkeypatch.setattr(tn, "_whitelists",
                        lambda: (_ for _ in ()).throw(RuntimeError("bad yaml")))

    sink = []
    monkeypatch.setattr(
        st_stub, "columns",
        lambda spec, *a, **kw: [
            _RecordingColumn(sink)
            for _ in range(spec if isinstance(spec, int) else len(spec))
        ])
    before = len(st_stub.calls)
    cockpit._render_phrase_rulings(tmp_path)

    # Not merely "it did not raise" -- that is equally true of a section
    # that returned on its first line, which is the failure this is
    # guarding against. It must still DRAW: the owner keeps the add box
    # and the revoke list even when the suggestion source is broken.
    assert len(st_stub.calls) > before, "the section vanished instead of degrading"
    drawn = [c for c in st_stub.calls[before:]]
    assert "text_input" in drawn, (
        "the 'rule another name' box is gone, so a broken whitelist has "
        f"taken away the owner's only way to add a ruling: {drawn}")


class _RecordingColumn:
    """A column that remembers the markdown written into it.

    Row text is written as ``cols[0].markdown(...)``, i.e. on the COLUMN,
    not on the streamlit module -- patching ``st.markdown`` captures the
    section headings and misses every row, which is how the first draft
    of this test "proved" a suggestion was absent when it was present.
    """
    def __init__(self, sink):
        self._sink = sink

    def markdown(self, text, *a, **kw):
        self._sink.append(str(text))

    def caption(self, text, *a, **kw):
        self._sink.append(str(text))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def button(self, *a, **kw):
        return False

    def __getattr__(self, name):
        return lambda *a, **kw: None


def test_suggestions_exclude_what_is_already_ruled(st_stub, tmp_path,
                                                  monkeypatch):  # noqa: F811
    """A ruled phrase must not be offered again, even in another case."""
    cockpit = _cockpit(st_stub)
    import processing.title_normalize as tn
    import processing.title_vocab as tv
    monkeypatch.setattr(tn, "_whitelists",
                        lambda: {"Rutgers University", "Brown University"})
    monkeypatch.setattr(tv, "phrase_rulings", lambda lib: ["rutgers university"])

    sink = []
    monkeypatch.setattr(
        st_stub, "columns",
        lambda spec, *a, **kw: [
            _RecordingColumn(sink)
            for _ in range(spec if isinstance(spec, int) else len(spec))
        ])
    cockpit._render_phrase_rulings(tmp_path)
    body = "\n".join(sink)

    assert "**Brown University**" in body, (
        f"an unruled whitelist name was not suggested: {body!r}")
    # Ruled case-insensitively, so it is listed as in force, never as a
    # suggestion to add again.
    assert body.count("Rutgers University") == 0, (
        f"an already-ruled phrase was offered as a suggestion: {body!r}")
    assert "**rutgers university**" in body, (
        "the ruling in force was not listed")
