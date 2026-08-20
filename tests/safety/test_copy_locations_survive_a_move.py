"""A sidecar's copy_locations must stay true after a move or rename.

These two helpers run inside `logged_move` and `logged_rename`
(undo_log.py:634, :638, :719) — that is, on EVERY one of the 15,133
recorded operations in the owner's library. A mutation campaign forced
each guard in them to False and 13 survived: the whole cluster could be
deleted and nothing in 2,248 tests would notice.

What goes wrong when they are wrong is quiet and durable: the sidecar
keeps pointing at a path the paper no longer occupies, so the topic copy
is orphaned, `remove_dead_location` cannot find it, and on undo the
identity no longer matches the file it belongs to.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from synth_library import _write_minimal_pdf  # noqa: E402

from processing.identity import (  # noqa: E402
    PaperIdentity, enable_sidecar_mirror, repath_copy_locations,
    repath_topic_copies, sidecar_path,
)


@pytest.fixture()
def lib(tmp_path):
    root = tmp_path / "lib"
    for d in ("01 - Published papers/S", "07a - BSDEs/01 - Published papers/S"):
        (root / d).mkdir(parents=True)
    enable_sidecar_mirror(root)
    return root


def _paper(lib, name="Smith, J. - A paper.pdf", copies=()):
    p = lib / "01 - Published papers" / "S" / name
    _write_minimal_pdf(p, title="t", author="Smith, J.")
    ident = PaperIdentity(original_filename=name)
    ident.copy_locations = [str(p), *[str(c) for c in copies]]
    ident.save(p)
    return p


class TestCopyLocationsAreRepathed:

    def test_the_canonical_entry_follows_the_move(self, lib):
        old = _paper(lib)
        new = old.parent / "Smith, J. - A renamed paper.pdf"
        old.rename(new)
        # sidecar still at the old name; move it as logged_rename would
        sidecar_path(old).rename(sidecar_path(new))
        assert repath_copy_locations(new, old_path=old, new_path=new)
        locs = PaperIdentity.load(new).copy_locations
        assert str(new) in locs
        assert str(old) not in locs, "the sidecar still points at a dead path"

    def test_a_second_call_changes_nothing(self, lib):
        """Idempotence: logged_move and logged_rename both call this, and
        a batch can touch the same paper twice."""
        old = _paper(lib)
        new = old.parent / "Smith, J. - Renamed.pdf"
        old.rename(new); sidecar_path(old).rename(sidecar_path(new))
        repath_copy_locations(new, old_path=old, new_path=new)
        first = PaperIdentity.load(new).copy_locations
        assert repath_copy_locations(new, old_path=old, new_path=new) is False
        assert PaperIdentity.load(new).copy_locations == first

    def test_no_sidecar_means_no_crash_and_no_claim(self, lib):
        p = lib / "01 - Published papers" / "S" / "Nobody, X. - Unfiled.pdf"
        _write_minimal_pdf(p, title="t", author="Nobody, X.")
        assert repath_copy_locations(p, old_path=p, new_path=p) is False

    def test_entries_that_are_not_ours_are_left_alone(self, lib):
        other = lib / "07a - BSDEs" / "01 - Published papers" / "S" / "Other, Y. - Different.pdf"
        _write_minimal_pdf(other, title="t", author="Other, Y.")
        old = _paper(lib, copies=[other])
        new = old.parent / "Smith, J. - Renamed.pdf"
        old.rename(new); sidecar_path(old).rename(sidecar_path(new))
        repath_copy_locations(new, old_path=old, new_path=new)
        assert str(other) in PaperIdentity.load(new).copy_locations, \
            "an unrelated paper's location was rewritten"


class TestTopicCopiesAreRenamedWithTheCanonical:

    def _with_topic_copy(self, lib):
        topic = lib / "07a - BSDEs" / "01 - Published papers" / "S"
        copy = topic / "Smith, J. - A paper.pdf"
        _write_minimal_pdf(copy, title="t", author="Smith, J.")
        return _paper(lib, copies=[copy]), copy

    def test_the_topic_copy_is_renamed_on_disk(self, lib):
        old, copy = self._with_topic_copy(lib)
        new = old.parent / "Smith, J. - A renamed paper.pdf"
        old.rename(new); sidecar_path(old).rename(sidecar_path(new))
        n = repath_topic_copies(new, old_path=old, new_path=new)
        assert n == 1
        assert not copy.exists(), "the topic copy kept the old name"
        assert (copy.parent / new.name).exists()
        assert str(copy.parent / new.name) in PaperIdentity.load(new).copy_locations

    def test_a_collision_leaves_both_files_alone(self, lib):
        """Two distinct files must never be merged to tidy a list."""
        old, copy = self._with_topic_copy(lib)
        new = old.parent / "Smith, J. - Renamed.pdf"
        occupied = copy.parent / new.name
        _write_minimal_pdf(occupied, title="someone else", author="Z, Z.")
        before = occupied.read_bytes()
        old.rename(new); sidecar_path(old).rename(sidecar_path(new))
        assert repath_topic_copies(new, old_path=old, new_path=new) == 0
        assert occupied.read_bytes() == before, "an unrelated file was clobbered"
        assert copy.exists(), "the topic copy was destroyed by the collision"

    def test_an_unchanged_basename_is_a_no_op(self, lib):
        """A move between folders keeps the name; nothing to rename."""
        old, copy = self._with_topic_copy(lib)
        dest_dir = lib / "07a - BSDEs" / "01 - Published papers" / "S"
        new = dest_dir / old.name
        assert repath_topic_copies(old, old_path=old, new_path=new) == 0
        assert copy.exists()

    def test_a_paper_with_no_copies_is_a_no_op(self, lib):
        old = _paper(lib)
        new = old.parent / "Smith, J. - Renamed.pdf"
        old.rename(new); sidecar_path(old).rename(sidecar_path(new))
        assert repath_topic_copies(new, old_path=old, new_path=new) == 0

    def test_a_copy_with_a_different_basename_is_never_renamed(self, lib):
        """The `p.name != old_name` guard. Without it, EVERY entry in
        copy_locations gets renamed to the new canonical name — including
        a different paper that happens to be listed there, which would
        rename someone else's file on disk.

        The earlier "not ours" test asserted this against
        repath_copy_locations, which never reaches this branch; the guard
        lives in repath_topic_copies and was untested.
        """
        topic = lib / "07a - BSDEs" / "01 - Published papers" / "S"
        stranger = topic / "Other, Y. - A completely different paper.pdf"
        _write_minimal_pdf(stranger, title="different", author="Other, Y.")
        old = _paper(lib, copies=[stranger])
        new = old.parent / "Smith, J. - Renamed.pdf"
        old.rename(new); sidecar_path(old).rename(sidecar_path(new))

        repath_topic_copies(new, old_path=old, new_path=new)

        assert stranger.exists(), \
            "a paper with an unrelated name was renamed on disk"
        assert str(stranger) in PaperIdentity.load(new).copy_locations
        assert not (topic / new.name).exists(), \
            "the stranger was renamed into the canonical's new name"
