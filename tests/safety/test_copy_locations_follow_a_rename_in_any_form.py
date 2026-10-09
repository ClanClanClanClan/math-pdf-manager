"""A rename updates the record's copy locations whatever Unicode form they are in.

Found applying the owner's surname rulings, 2026-10-09: seven Strasbourg
records listed their paper twice afterwards -- under the new name and,
stale, under the old one. Their stored locations were decomposed (NFD) in
the folder part ("Séminaires de probabilités") and composed in the
filename; the rename was asked for in NFC. ``repath_copy_locations``
compared whole strings exactly, so it never found the old entry, and
``repath_topic_copies`` then matched the basename and reported a
"collision" with the paper itself. Non-negotiable 8.

Only the STORED strings vary in form here; the files on disk always use
the real spelling, so these tests mean the same on APFS and on CI's
byte-exact filesystem.
"""
from __future__ import annotations

import json
import logging
import os
import unicodedata
from pathlib import Path

import sys

import pytest

from processing.identity import PaperIdentity, enable_sidecar_mirror, find_sidecar
from processing.undo_log import UndoLog, logged_rename

NFC = lambda s: unicodedata.normalize("NFC", s)       # noqa: E731
NFD = lambda s: unicodedata.normalize("NFD", s)       # noqa: E731

FOLDER = "08 - Séminaires de probabilités de Strasbourg/Séminaire 31 - 1997"
OLD = "103-le Gall, J.-F. - Marches aléatoires.pdf"
NEW = "103-Le Gall, J.-F. - Marches aléatoires.pdf"


@pytest.fixture
def lib(tmp_path):
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _paper(lib, stored_form):
    pdf = lib / NFC(FOLDER) / NFC(OLD)
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 x")
    ident = PaperIdentity()
    ident.copy_locations = [stored_form(str(pdf))]
    ident.save(pdf, recompute_hash=True)
    return pdf


def _mixed(path: str) -> str:
    """The shape found on disk: folder part NFD, filename NFC."""
    head, _, name = path.rpartition("/")
    return NFD(head) + "/" + NFC(name)


@pytest.mark.parametrize("stored", [NFC, NFD, _mixed], ids=["nfc", "nfd", "mixed"])
def test_the_old_entry_is_replaced_not_kept(lib, stored, caplog):
    pdf = _paper(lib, stored)
    new = pdf.with_name(NFC(NEW))
    log = UndoLog(log_dir=lib / ".operation_log")
    log.begin_transaction("t")
    with caplog.at_level(logging.WARNING):
        logged_rename(pdf, new, undo_log=log)
    log.commit()
    locs = json.loads(find_sidecar(new).read_text())["copy_locations"]
    assert [NFC(x) for x in locs] == [NFC(str(new))], locs
    assert "would collide" not in caplog.text, "the paper was taken for its own copy"


def test_entries_differing_only_in_form_collapse_to_one(lib):
    pdf = _paper(lib, NFC)
    ident = PaperIdentity.load(pdf)
    ident.copy_locations = [NFC(str(pdf)), NFD(str(pdf))]
    ident.save(pdf, recompute_hash=False)
    new = pdf.with_name(NFC(NEW))
    logged_rename(pdf, new)
    locs = json.loads(find_sidecar(new).read_text())["copy_locations"]
    assert [NFC(x) for x in locs] == [NFC(str(new))]


def test_a_case_only_rename_of_a_topic_copy_is_not_a_collision(lib, caplog):
    """APFS folds case: the 'existing' target of le Gall -> Le Gall is the
    copy itself. The check said collision, so topic copies were never
    renamed for a capitalisation change (non-negotiable 7)."""
    pdf = _paper(lib, NFC)
    topic = lib / "07a - BSDEs" / NFC(OLD)
    topic.parent.mkdir(parents=True)
    topic.write_bytes(b"%PDF-1.4 x")
    ident = PaperIdentity.load(pdf)
    ident.copy_locations.append(str(topic))
    ident.save(pdf, recompute_hash=False)
    with caplog.at_level(logging.WARNING):
        logged_rename(pdf, pdf.with_name(NFC(NEW)))
    assert "would collide" not in caplog.text
    assert [NFC(n) for n in os.listdir(topic.parent)] == [NFC(NEW)]


def test_a_real_topic_copy_is_still_renamed_with_it(lib):
    """The other half of the helper's job must survive the fix."""
    pdf = _paper(lib, _mixed)
    topic = lib / "07a - BSDEs" / NFC(OLD)
    topic.parent.mkdir(parents=True)
    topic.write_bytes(b"%PDF-1.4 x")
    ident = PaperIdentity.load(pdf)
    ident.copy_locations.append(str(topic))   # as on disk: on a byte-exact
                                              # filesystem an NFD spelling of
                                              # it is a different, missing file
    ident.save(pdf, recompute_hash=False)
    new = pdf.with_name(NFC(NEW))
    logged_rename(pdf, new)
    locs = {NFC(x) for x in json.loads(find_sidecar(new).read_text())["copy_locations"]}
    assert locs == {NFC(str(new)), NFC(str(topic.with_name(NFC(NEW))))}
    # The folder listing, not exists(): on APFS the old capitalisation
    # still "exists" -- it is the same file.
    assert [NFC(n) for n in os.listdir(topic.parent)] == [NFC(NEW)]


def test_a_record_already_listing_both_names_is_cleaned(lib):
    """The state the seven damaged records were left in: the old name
    (decomposed) AND the new one. A second pass must remove the stale
    entry, not return early because the new name is "already there"."""
    from processing.identity import repath_copy_locations
    pdf = _paper(lib, _mixed)
    new = pdf.with_name(NFC(NEW))
    pdf.rename(new)                                   # the file, as after the first pass
    rec = find_sidecar(pdf)
    rec.rename(rec.with_name(NFC(NEW)[:-4] + ".meta.json"))
    ident = PaperIdentity.load(new)
    ident.copy_locations = [_mixed(str(pdf)), str(new)]
    ident.save(new, recompute_hash=False)
    assert repath_copy_locations(new, old_path=pdf, new_path=new)
    assert [NFC(x) for x in PaperIdentity.load(new).copy_locations] == [NFC(str(new))]


def test_the_new_name_listed_in_another_form_is_not_listed_twice(lib):
    pdf = _paper(lib, NFC)
    new = pdf.with_name(NFC(NEW))
    ident = PaperIdentity.load(pdf)
    ident.copy_locations = [str(pdf), NFD(str(new))]
    ident.save(pdf, recompute_hash=False)
    logged_rename(pdf, new)
    locs = json.loads(find_sidecar(new).read_text())["copy_locations"]
    assert len(locs) == 1 and NFC(locs[0]) == NFC(str(new)), locs


@pytest.mark.skipif(sys.platform != "darwin", reason="APFS folds Unicode forms")
def test_a_topic_copy_stored_decomposed_is_renamed_too(lib):
    pdf = _paper(lib, NFC)
    topic = lib / "07a - BSDEs" / NFC(OLD)
    topic.parent.mkdir(parents=True)
    topic.write_bytes(b"%PDF-1.4 x")
    if not Path(NFD(str(topic))).exists():
        pytest.skip("this volume does not fold Unicode forms")
    ident = PaperIdentity.load(pdf)
    ident.copy_locations.append(NFD(str(topic)))
    ident.save(pdf, recompute_hash=False)
    logged_rename(pdf, pdf.with_name(NFC(NEW)))
    assert [NFC(n) for n in os.listdir(topic.parent)] == [NFC(NEW)]
