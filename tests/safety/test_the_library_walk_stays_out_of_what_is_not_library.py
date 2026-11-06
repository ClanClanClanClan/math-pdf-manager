"""One library walk, which never enters a folder that is not the library.

Step-back audit, findings D12-2 and D12-3 (verified 3 of 3). ``iter_pdfs``
ran ``rglob`` over everything and dropped the paths it did not want
afterwards. So each walk went through a 126,000-file project and the code
folder, 89% of its time, and a test's temporary folder inside the code
folder failed the hourly "put back saved details" job 21 times in a row.
There were also two lists of what is not the library.

Measured on the real library, 2026-11-06, read-only: the old walk and this
one return the same 29,917 PDFs, in 2.5 s and 0.2 s.
"""
from __future__ import annotations

import os
import unicodedata
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as hst

from processing import identity as I
from processing.identity import PDF_GLOB, iter_pdfs
from processing.library_scope import NON_LIBRARY, exclusion_reason


def _pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF")
    return path


def _names(root, **k):
    return sorted(str(p.relative_to(root)) for p in iter_pdfs(root, **k))


@pytest.mark.parametrize("folder", NON_LIBRARY)
def test_a_folder_that_is_not_the_library_is_never_entered(tmp_path, monkeypatch, folder):
    """THE POINT. Filtered afterwards would pass a set comparison; this
    fails if the folder is ever opened."""
    _pdf(tmp_path / "01 - Published papers" / "A.pdf")
    _pdf(tmp_path / folder / "deep" / "decoy.pdf")
    opened = []
    real = os.scandir

    def _spy(path):
        opened.append(str(path))
        return real(path)

    monkeypatch.setattr(I.os, "scandir", _spy)
    assert _names(tmp_path) == ["01 - Published papers/A.pdf"]
    assert not any(folder in Path(p).parts for p in opened), opened


def test_nested_ones_are_skipped_too(tmp_path):
    _pdf(tmp_path / "07a - BSDEs" / "Scripts" / "fixture.pdf")
    _pdf(tmp_path / "07a - BSDEs" / "real.pdf")
    assert _names(tmp_path) == ["07a - BSDEs/real.pdf"]


def test_hidden_folders_are_not_entered(tmp_path):
    _pdf(tmp_path / ".mathpdf-sidecars" / "x.pdf")
    _pdf(tmp_path / "B.pdf")
    assert _names(tmp_path) == ["B.pdf"]


def test_a_hidden_root_is_walked(tmp_path):
    """Only what is below the root is judged by name."""
    _pdf(tmp_path / ".cache" / "lib" / "C.pdf")
    assert _names(tmp_path / ".cache" / "lib") == ["C.pdf"]


def test_a_root_inside_a_non_library_folder_yields_nothing(tmp_path):
    """As the old walk did: its filter read the whole path."""
    _pdf(tmp_path / "Scripts" / "tests" / "D.pdf")
    assert _names(tmp_path / "Scripts" / "tests") == []


def test_suffix_case_and_decomposed_names(tmp_path):
    nfd = unicodedata.normalize("NFD", "Élie.PDF")
    _pdf(tmp_path / nfd)
    _pdf(tmp_path / "x.Pdf")
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "a.pdfx").write_text("x")
    got = _names(tmp_path)
    assert len(got) == 2 and "x.Pdf" in got


def test_a_folder_named_like_a_pdf_is_a_folder(tmp_path):
    _pdf(tmp_path / "volume.pdf" / "inside.pdf")
    assert _names(tmp_path) == ["volume.pdf/inside.pdf"]


def test_a_link_to_a_folder_is_not_followed_but_a_link_to_a_pdf_counts(tmp_path):
    real = _pdf(tmp_path / "lib" / "real.pdf")
    outside = _pdf(tmp_path / "outside" / "z.pdf")
    (tmp_path / "lib" / "link-to-outside").symlink_to(outside.parent, target_is_directory=True)
    (tmp_path / "lib" / "alias.pdf").symlink_to(real)
    assert _names(tmp_path / "lib") == ["alias.pdf", "real.pdf"]


def test_a_missing_root_and_a_file_root_yield_nothing(tmp_path):
    heard = []
    assert list(iter_pdfs(tmp_path / "gone", on_unreadable=lambda *a: heard.append(a))) == []
    f = _pdf(tmp_path / "f.pdf")
    assert list(iter_pdfs(f, on_unreadable=lambda *a: heard.append(a))) == []
    assert heard == [], "nothing was left unlooked at"


def test_not_recursive_means_direct_children_only(tmp_path):
    _pdf(tmp_path / "top.pdf")
    _pdf(tmp_path / "sub" / "low.pdf")
    assert _names(tmp_path, recursive=False) == ["top.pdf"]
    _pdf(tmp_path / "Scripts" / "fixture.pdf")
    assert _names(tmp_path / "Scripts", recursive=False) == []


def test_an_unreadable_folder_is_reported_not_passed_over(tmp_path, monkeypatch):
    """"I did not look" is not "no papers there"."""
    _pdf(tmp_path / "ok" / "A.pdf")
    bad = tmp_path / "bad"
    _pdf(bad / "B.pdf")
    real = os.scandir

    def _scan(path):
        if str(path) == str(bad):
            raise PermissionError("no")
        return real(path)

    monkeypatch.setattr(I.os, "scandir", _scan)
    heard = []
    got = _names(tmp_path, on_unreadable=lambda f, e: heard.append((f, type(e))))
    assert got == ["ok/A.pdf"]
    assert heard == [(bad, PermissionError)]
    assert _names(tmp_path) == ["ok/A.pdf"], "and with nobody listening it still walks on"


def test_there_is_one_list():
    assert I._NON_LIBRARY_DIRS == frozenset(NON_LIBRARY)


@pytest.mark.parametrize("name", NON_LIBRARY)
def test_the_scope_rule_agrees_with_the_walk(name):
    assert exclusion_reason(f"{name}/x.pdf") is not None


_NAME = hst.sampled_from(["01", "07a - BSDEs", "A", "2021", "Scripts", ".hidden", "gmnap",
                          ".trash", "archive", "b.pdf", "c.PDF", "d.txt"])


@settings(max_examples=60, deadline=None)
@given(hst.lists(hst.lists(_NAME, min_size=1, max_size=4), max_size=12))
def test_property_the_same_papers_as_filtering_after_a_full_walk(tmp_path_factory, trees):
    """Whatever the tree, the pruned walk finds exactly what a full walk
    filtered afterwards finds, hidden folders aside."""
    root = tmp_path_factory.mktemp("lib")
    for parts in trees:
        path = root.joinpath(*parts)
        leaf = parts[-1]
        try:
            if leaf.lower().endswith((".pdf", ".txt")):
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.is_dir():
                    path.write_bytes(b"x")
            else:
                path.mkdir(parents=True, exist_ok=True)
        except (FileExistsError, NotADirectoryError):
            continue
    want = sorted(
        str(p.relative_to(root)) for p in root.rglob(PDF_GLOB)
        if p.is_file() and not any(
            part in NON_LIBRARY or part.startswith(".")
            for part in p.relative_to(root).parts[:-1]))
    assert sorted(_names(root)) == want
