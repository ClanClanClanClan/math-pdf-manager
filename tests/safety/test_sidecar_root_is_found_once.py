"""The library root is found once per folder, and resolved only when it must be.

Cockpit audit finding 18 (approved). Every identity load called
``sidecar_path``, which re-walked the folder chain testing for the
``.mathpdf-sidecars`` marker AND resolved both the PDF path and the root
-- for each of ~29,500 PDFs, although the answer is one constant. MEASURED
on the real library, 2026-10-09, 29,761 PDFs: sidecar_path 4.5-6.2 s ->
0.95 s, sidecar_candidates 8.0-8.9 s -> 1.9 s, and a differential over all
29,761 found ZERO paths that changed, for either function.

What must not break while doing that, each of which this file pins:
  * a marker created AFTER a first lookup must be found (negative answers
    are never cached -- enable_sidecar_mirror runs mid-process);
  * the configured-root fallback is resolved, and macOS /var is a symlink
    to /private/var -- the comparison there still needs both sides
    resolved, or the PDF silently gets the wrong sidecar convention;
  * a path containing ".." must not yield a relative path that keeps it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import processing.identity as ident
from processing.identity import MIRROR_DIR_NAME, sidecar_path


@pytest.fixture(autouse=True)
def _fresh_cache():
    ident._clear_library_root_cache()
    yield
    ident._clear_library_root_cache()


def _lib(tmp_path) -> Path:
    lib = tmp_path / "lib"
    (lib / MIRROR_DIR_NAME).mkdir(parents=True)
    return lib


def test_the_mirror_path_is_under_the_marker(tmp_path):
    lib = _lib(tmp_path)
    pdf = lib / "01 - Published papers" / "S" / "Smith, J. - T.pdf"
    assert sidecar_path(pdf) == (lib / MIRROR_DIR_NAME / "01 - Published papers"
                                 / "S" / "Smith, J. - T.meta.json")


def test_one_walk_serves_every_folder_on_the_way(tmp_path, monkeypatch):
    lib = _lib(tmp_path)
    sidecar_path(lib / "a" / "b" / "c" / "x.pdf")
    probes = []
    real_is_dir = Path.is_dir
    monkeypatch.setattr(Path, "is_dir",
                        lambda self: probes.append(self) or real_is_dir(self))
    sidecar_path(lib / "a" / "b" / "y.pdf")          # a folder already walked
    sidecar_path(lib / "a" / "b" / "c" / "z.pdf")
    assert not [p for p in probes if p.name == MIRROR_DIR_NAME], (
        "the marker was probed again for folders already resolved")


def test_a_marker_created_after_a_first_lookup_is_found(tmp_path, monkeypatch):
    """Negative answers must not be cached."""
    import core.config_paths as cp
    monkeypatch.setattr(cp, "get_library_root", lambda: tmp_path / "elsewhere")
    lib = tmp_path / "lib"
    pdf = lib / "01" / "a.pdf"
    pdf.parent.mkdir(parents=True)
    before = sidecar_path(pdf)
    assert MIRROR_DIR_NAME not in before.parts, "no marker yet: natural path"
    (lib / MIRROR_DIR_NAME).mkdir()
    after = sidecar_path(pdf)
    assert after == lib / MIRROR_DIR_NAME / "01" / "a.meta.json"


def test_the_symlinked_fallback_still_resolves_both_sides(tmp_path, monkeypatch):
    """The configured root is resolved; a PDF reached through a symlinked
    parent is not. Lexically they do not compare, so the resolve fallback
    must run -- the case the original code comment was written for."""
    import core.config_paths as cp
    real = tmp_path / "real_lib"
    (real / "01").mkdir(parents=True)
    link = tmp_path / "link_to_lib"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.setattr(cp, "get_library_root", lambda: real.resolve())
    (real / MIRROR_DIR_NAME).mkdir()
    ident._clear_library_root_cache()
    # Reach the PDF through the symlink, with the marker found via the walk
    # under the LINK name -- and separately via the fallback alone:
    got = sidecar_path(link / "01" / "a.pdf")
    assert got.name == "a.meta.json" and MIRROR_DIR_NAME in got.parts


def test_the_fallback_root_with_a_symlinked_pdf_path(tmp_path, monkeypatch):
    """No marker reachable lexically; only the resolved fallback matches."""
    real = tmp_path / "real2"
    (real / "01").mkdir(parents=True)
    link = tmp_path / "link2"
    link.symlink_to(real, target_is_directory=True)
    rel = ident._relative_to_root(link / "01" / "a.pdf", real.resolve())
    assert rel == Path("01") / "a.pdf"


def test_dot_dot_is_resolved_not_kept(tmp_path):
    lib = _lib(tmp_path)
    (lib / "01").mkdir()
    (lib / "02").mkdir()
    rel = ident._relative_to_root(lib / "01" / ".." / "02" / "a.pdf", lib)
    assert ".." not in rel.parts and rel == Path("02") / "a.pdf"
