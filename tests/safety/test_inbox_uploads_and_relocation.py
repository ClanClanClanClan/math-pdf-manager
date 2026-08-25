"""The inbox moved out of ~/Downloads, and the cockpit grew a door.

WHY THIS EXISTS. The inbox was ~/Downloads/MathInbox. The owner deleted it
-- "I don't want any folder on my Downloads folder, this is polluting me"
-- which is an entirely reasonable thing to do to a folder nobody told you
was load-bearing. The daemon then watched a directory that did not exist
for five days and twenty-one hours without noticing, because macOS does
not tear down a watch when its target disappears.

Two changes are under test:

  1. The default inbox is ~/.mathpdf/inbox, beside the logs and reports
     this tool already keeps. Nothing lands in Downloads.
  2. Uploading is the supported way in, so the folder is plumbing the
     owner never has to visit. Uploads must never overwrite and never
     leave a half-written PDF where the watcher can see it.
"""
import os
from pathlib import Path

import pytest

from ui.cockpit_actions import save_uploads_to_inbox
from watcher.config import WatcherConfig, _DEFAULT_INBOX, _LEGACY_INBOX, _migrate_inbox


class _Upload:
    """Mimics a Streamlit UploadedFile."""

    def __init__(self, name, data=b"%PDF-1.7 body"):
        self.name = name
        self._data = data

    def getvalue(self):
        return self._data


# ---------------------------------------------------------------- location

def test_the_default_inbox_is_not_in_downloads():
    """THE REGRESSION. The whole point of the move."""
    parts = {p.lower() for p in _DEFAULT_INBOX.parts}
    assert "downloads" not in parts, _DEFAULT_INBOX
    assert "desktop" not in parts and "documents" not in parts


def test_the_default_inbox_sits_with_the_other_tool_state():
    cfg = WatcherConfig()
    assert _DEFAULT_INBOX.parent == cfg.log_dir, (
        "the inbox should live beside the logs and reports, not somewhere new"
    )


def test_the_inbox_is_not_inside_the_library():
    """A watched folder inside a Dropbox-synced library invites a loop."""
    from core.config_paths import get_library_root
    root = Path(get_library_root()).resolve()
    assert root not in _DEFAULT_INBOX.resolve().parents


# --------------------------------------------------------------- migration

def test_a_config_still_naming_the_old_default_is_migrated():
    assert _migrate_inbox(_LEGACY_INBOX) == _DEFAULT_INBOX


def test_a_deliberately_customised_path_is_left_alone(tmp_path):
    """Overriding a choice someone actually made is how a tool loses trust."""
    mine = tmp_path / "my" / "own" / "inbox"
    assert _migrate_inbox(mine) == mine


def test_a_custom_downloads_path_is_still_left_alone():
    """Only the EXACT old default migrates, not anything under Downloads.

    Someone who typed their own Downloads path has made a choice.

    Derived from _LEGACY_INBOX rather than calling Path.home(), so this
    test names no real directory -- tests/safety/test_no_test_touches_the
    _real_world.py rejects a test tree that reaches for the owner's home,
    and it was right to reject the first draft of this one.
    """
    other = _LEGACY_INBOX.parent / "SomethingElse"
    assert other != _LEGACY_INBOX
    assert _migrate_inbox(other) == other


def test_a_legacy_inbox_with_files_in_it_is_not_silently_abandoned(
    tmp_path, monkeypatch
):
    """Migrating a folder that still holds papers would strand them.

    The automatic case is the one that actually happened -- the folder is
    gone. A folder with files is a different situation and must not be
    silently walked away from.
    """
    import watcher.config as wc
    legacy = tmp_path / "MathInbox"
    legacy.mkdir()
    (legacy / "waiting.pdf").write_bytes(b"%PDF")
    monkeypatch.setattr(wc, "_LEGACY_INBOX", legacy)
    assert wc._migrate_inbox(legacy) == legacy, "must not abandon queued files"

    (legacy / "waiting.pdf").unlink()
    assert wc._migrate_inbox(legacy) == wc._DEFAULT_INBOX, "empty is safe to move"


# ----------------------------------------------------------------- uploads

def test_a_pdf_is_saved(tmp_path):
    saved, failed = save_uploads_to_inbox([_Upload("paper.pdf")], tmp_path)
    assert not failed
    assert saved == [tmp_path / "paper.pdf"]
    assert (tmp_path / "paper.pdf").read_bytes().startswith(b"%PDF")


def test_the_inbox_is_created_if_missing(tmp_path):
    box = tmp_path / "does" / "not" / "exist"
    saved, failed = save_uploads_to_inbox([_Upload("a.pdf")], box)
    assert not failed and box.is_dir()


def test_a_colliding_name_never_overwrites(tmp_path):
    """Two different papers can share a filename.

    Overwriting one with the other destroys a paper with no undo record --
    the single thing this project refuses to do anywhere else.
    """
    (tmp_path / "paper.pdf").write_bytes(b"%PDF original")
    saved, failed = save_uploads_to_inbox([_Upload("paper.pdf", b"%PDF new")], tmp_path)
    assert not failed
    assert (tmp_path / "paper.pdf").read_bytes() == b"%PDF original"
    assert saved == [tmp_path / "paper (2).pdf"]


def test_collisions_keep_counting(tmp_path):
    for n in ("paper.pdf", "paper (2).pdf", "paper (3).pdf"):
        (tmp_path / n).write_bytes(b"%PDF")
    saved, _ = save_uploads_to_inbox([_Upload("paper.pdf")], tmp_path)
    assert saved == [tmp_path / "paper (4).pdf"]


def test_a_path_in_the_upload_name_cannot_escape_the_inbox(tmp_path):
    """An upload's name is untrusted input."""
    outside = tmp_path.parent / "escaped.pdf"
    saved, failed = save_uploads_to_inbox(
        [_Upload("../escaped.pdf"), _Upload("/etc/passwd.pdf")], tmp_path
    )
    assert not outside.exists()
    for p in saved:
        assert p.parent == tmp_path, p


def test_a_dotfile_name_cannot_hide_the_upload(tmp_path):
    """A leading dot would make the file invisible AND unwatched."""
    saved, _ = save_uploads_to_inbox([_Upload(".hidden.pdf")], tmp_path)
    assert saved and not saved[0].name.startswith(".")


def test_something_that_is_not_a_pdf_is_refused(tmp_path):
    saved, failed = save_uploads_to_inbox(
        [_Upload("trojan.pdf", b"MZ\x90\x00 this is an exe")], tmp_path
    )
    assert saved == []
    assert failed and "not a PDF" in failed[0][1]
    assert list(tmp_path.iterdir()) == []


def test_an_empty_file_is_refused(tmp_path):
    saved, failed = save_uploads_to_inbox([_Upload("empty.pdf", b"")], tmp_path)
    assert saved == [] and failed and "empty" in failed[0][1]


def test_a_name_without_an_extension_gets_one(tmp_path):
    saved, _ = save_uploads_to_inbox([_Upload("no-extension")], tmp_path)
    assert saved and saved[0].suffix == ".pdf"


def test_no_partial_file_is_left_where_the_watcher_can_see_it(tmp_path):
    """The watcher must never meet a half-written PDF.

    Written to a temp name and renamed, so the file appears complete or
    not at all. A .part left behind would be filed as a broken paper.
    """
    save_uploads_to_inbox([_Upload("a.pdf"), _Upload("b.pdf")], tmp_path)
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".part")]
    assert not leftovers, leftovers


def test_one_bad_upload_does_not_stop_the_good_ones(tmp_path):
    saved, failed = save_uploads_to_inbox(
        [_Upload("good1.pdf"), _Upload("bad.pdf", b"nope"), _Upload("good2.pdf")],
        tmp_path,
    )
    assert len(saved) == 2 and len(failed) == 1


def test_an_unwritable_inbox_reports_rather_than_raises(tmp_path):
    """A traceback takes the whole cockpit down."""
    blocked = tmp_path / "blocked"
    blocked.write_text("I am a file, not a directory")
    saved, failed = save_uploads_to_inbox([_Upload("a.pdf")], blocked)
    assert saved == [] and failed and failed[0][0] == "a.pdf"


def test_unicode_names_survive(tmp_path):
    """macOS hands filenames back NFD-decomposed."""
    import unicodedata
    saved, failed = save_uploads_to_inbox(
        [_Upload("Émile Borel, Théorie des probabilités.pdf")], tmp_path
    )
    assert not failed and saved
    on_disk = list(tmp_path.iterdir())[0].name
    assert unicodedata.normalize("NFC", on_disk).startswith("Émile")


def test_nothing_is_written_for_an_empty_upload_list(tmp_path):
    saved, failed = save_uploads_to_inbox([], tmp_path)
    assert saved == [] and failed == []
