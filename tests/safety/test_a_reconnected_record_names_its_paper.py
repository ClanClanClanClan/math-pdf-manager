"""A reconnected record names its paper where it is now.

``sidecar_repair.apply_reconnect`` (Conformance: "Reconnect N record(s)" and
"Put N record(s) with their papers in the trash") moved a stranded record
beside its paper and changed nothing else. A record is stranded by a rename
that bypassed ``logged_rename`` -- which is also what would have repathed
its ``copy_locations`` -- so after reconnecting it still listed the paper's
OLD name: a file that no longer exists. Measured 2026-10-10: 10 live
records name a missing file; 9 of them are orphans left by renames, all
nine among the 37 the reconnect matches.

Now the reconnect finishes the rename the record missed: the entry for the
old place becomes the paper's current path (added when nothing named it),
as a recorded field edit in the same transaction, so undo puts the record
back byte for byte. The old place is found by asking which entry the record
ANSWERS to -- would a paper there read this very file? -- so a coded
``.sidecars/<sha1>`` record, whose old name cannot be read back, is
handled by the same rule: the hash cannot be inverted, but it can be
checked. An entry the record does not answer to is left as it is and,
if it names no file, reported.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unicodedata
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from processing.identity import (
    MAX_BASENAME_BYTES, MIRROR_DIR_NAME, compute_content_hash,
    enable_sidecar_mirror, find_sidecar, repathed_locations, sidecar_path,
)
from processing.sidecar_repair import (
    _places_it_answers_for, apply_reconnect, apply_trash_reconnect,
    find_orphans, plan_reconnect,
)
from processing.undo_log import UndoLog

SHELF = "01 - Published papers/S"

#: Most of the real library: written before the identification fields.
OLD_SCHEMA = {
    "schema_version": 1, "original_filename": "x.pdf", "doi": "10.1/x",
    "arxiv_id": "", "first_ingested_at": "2025-01-01T00:00:00",
    "first_ingest_tx_id": "", "publication_checks": [], "recheck_count": 0,
    "last_check_date": "", "permanently_unpublished": False,
    "topic_codes": [], "topic_suggestion": "", "topic_confidence": 0.0,
    "classifier_text": "first page", "classifier_text_tried": True,
}

KINDS = ("ordinary", "nfd", "over-long", "over-long-nfd",
         "full-name-252", "full-name-255")


def _dump(d: dict) -> str:
    return json.dumps(d, indent=2, ensure_ascii=False, sort_keys=True)


@pytest.fixture
def lib(tmp_path):
    enable_sidecar_mirror(tmp_path)
    return tmp_path


def _name(kind: str, tag: str = "A") -> str:
    """A PDF name of this kind. ``tag`` makes the old and new names differ."""
    head = f"Smith, J. - {tag} "
    if kind == "ordinary":
        return head + "result.pdf"
    if kind == "nfd":
        return unicodedata.normalize("NFD", f"Élie, R. - {tag} équations rétrogrades.pdf")
    if kind == "over-long":
        return head + "x" * (250 - len(head)) + ".pdf"
    if kind == "over-long-nfd":
        h = unicodedata.normalize("NFD", f"Élie, R. - {tag} ")
        return h + "y" * (250 - len(h.encode())) + ".pdf"
    n = int(kind.rsplit("-", 1)[1])
    return head + "z" * (n - len(".meta.json") - len(head)) + ".pdf"


def _strand(lib, kind="ordinary", *, new_kind="ordinary", locations="old",
            record=None, folder=SHELF):
    """A paper with a record, renamed the WRONG way: the record stays.

    ``locations``: "old" -- the record lists the old path (as ingest and
    ``logged_rename`` write it); a list -- exactly that; None -- no field.
    Returns ``(record, old_pdf_path, new_pdf_path)``.
    """
    old = lib / folder / _name(kind, "A")
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes(b"%PDF-1.4 " + old.name.encode())
    rec = (lib / MIRROR_DIR_NAME / folder / (old.stem + ".meta.json")
           if kind.startswith("full-name") else sidecar_path(old))
    data = dict(OLD_SCHEMA if record is None else record,
                content_sha256=compute_content_hash(old))
    if locations == "old":
        data["copy_locations"] = [str(old)]
    elif locations is not None:
        data["copy_locations"] = list(locations)
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(_dump(data), encoding="utf-8")
    assert find_sidecar(old) == rec, "control: the paper reads its record"
    new = old.with_name(_name(new_kind, "B"))
    old.rename(new)                                   # outside the app
    assert find_orphans(lib) == [rec], "control: the rename stranded it"
    return rec, old, new


def _topic_copy(lib, old, new):
    """A hardlink in a topic folder under the old name, with a record of
    its own (without one it is a second record-less paper with these
    contents, and the plan rightly refuses to choose)."""
    topic = lib / "07a - BSDEs" / old.name
    topic.parent.mkdir(parents=True, exist_ok=True)
    os.link(new, topic)
    rec = sidecar_path(topic)
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(_dump({"doi": "10.1/topic"}), encoding="utf-8")
    return topic


def _reconnect(lib, *, check_preview=True):
    """Plan and press, as the page does -- and check that what the page
    would have said before the press (``still``) is what the press did."""
    plan = plan_reconnect(lib)
    assert len(plan["matched"]) == 1, plan
    out = apply_reconnect(lib, plan, dry_run=False)
    if check_preview and out["moved"]:
        said = dict(plan["still"]).get(plan["matched"][0][0], [])
        assert said == out["moved"][0]["still"], (
            "the page warned one thing and the button did another")
    return out


def _locations(pdf):
    return json.loads(find_sidecar(pdf).read_text(encoding="utf-8")).get(
        "copy_locations", "ABSENT")


def _undo(lib, tx_id):
    results = UndoLog(log_dir=lib / ".operation_log").undo_transaction(tx_id)
    assert all(r["ok"] for r in results), results
    return results


# ------------------------------------------- the nine records the owner has
#
# Measured read-only on the real library, 2026-10-10: the 9 orphans whose
# copy_locations name their paper's OLD file, all among the 37 "Reconnect"
# matches. Each is (the entry as stored, the paper's name on disk now),
# code point for code point: Bättig's entry is composed and its file
# decomposed; the Astérisque entry mixes a decomposed folder with a
# composed name. All 9 are ordinary records.

NINE = [
    ("01 - Published papers/B/B\u00e4ttig, R. J. - Completness of securities market models\u2014an operator point of view.pdf",
     "Ba\u0308ttig, R. J. - Completeness of securities market models\u2014an operator point of view.pdf"),
    ("01 - Published papers/D/Duncan, T. E., Pasik-Duncan, B. - Linear\u2013quadratic fractional Gausian control.pdf",
     "Duncan, T. E., Pasik-Duncan, B. - Linear\u2013quadratic fractional Gaussian control.pdf"),
    ("01 - Published papers/L/Lions, P.-L., Souganidis, P. E. - Stochastic homogenization of Hamilon-Jacobi and \"viscous\"-Hamilton\u2013Jacobi equations with convex nonlinearities - revisited.pdf",
     "Lions, P.-L., Souganidis, P. E. - Stochastic homogenization of Hamilton-Jacobi and \"viscous\"-Hamilton\u2013Jacobi equations with convex nonlinearities, revisited.pdf"),
    ("05 - Books and lecture notes/05 - Aste\u0301risque/Ast\u00e9risque 100 - Faisceaux pervers \u2013 A. A. Beilinson, J. Bernstein, P. Deligne, O. Gabber \u2013 Ast\u00e9risque 100, 1982 \u2013 Soci\u00e9t\u00e9 Math\u00e9matique de France \u2013 378a1f3fd8847fe6a926ca6df2c7e591 \u2013 Anna\u2019s Archive.pdf",
     "Aste\u0301risque 100 - Beilinson, A. A., Bernstein, J., Deligne, P., Gabber, O. - Faisceaux pervers.pdf"),
    ("05 - Books and lecture notes/06 - Saint-Flour/021 - Biane, P., Durrett, R. T. - Lectures on probability theory, \u00e9cole d'\u00e9t\u00e9 de probabilites de Saint-Flour XXIII, 1993.pdf",
     "021 - Biane, P., Durrett, R. T. - Lectures on probability theory, \u00e9cole d\u2019\u00e9t\u00e9 de probabilit\u00e9s de Saint-Flour XXIII, 1993.pdf"),
    ("05 - Books and lecture notes/A/Andersen, T. G., Davis, R. A., Krei\u00df, J.-P., Mikosch, T. - Handbook of financiel time series.pdf",
     "Andersen, T. G., Davis, R. A., Krei\u00df, J.-P., Mikosch, T. - Handbook of financial time series.pdf"),
    ("05 - Books and lecture notes/F/Fleming, W. H., Soner, H. M. - Controlled Makov processes and viscosity solutions.pdf",
     "Fleming, W. H., Soner, H. M. - Controlled Markov processes and viscosity solutions.pdf"),
    ("05 - Books and lecture notes/W/Wise, G. L., Hall, E. B. - Couterexamples in probability and real analysis.pdf",
     "Wise, G. L., Hall, E. B. - Counterexamples in probability and real analysis.pdf"),
    ("08 - Se\u0301minaires de probabilite\u0301s de Strasbourg/Se\u0301minaire 25 - 1991/374-Albeverio, S. A., Ma, Z.-M. - Necessary and sufficient condtions for the existence of m-perfect processes associated with Dirichlet forms.pdf",
     "374-Albeverio, S. A., Ma, Z.-M. - Necessary and sufficient conditions for the existence of m-perfect processes associated with Dirichlet forms.pdf"),
]


@pytest.mark.parametrize("entry,now", NINE, ids=[n.split(" - ")[0][:24] for _, n in NINE])
def test_each_of_the_nine_names_its_paper_after_reconnect(lib, entry, now):
    old = lib / entry
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes(b"%PDF-1.4 " + entry.encode())
    rec = sidecar_path(old)
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(_dump(dict(OLD_SCHEMA, content_sha256=compute_content_hash(old),
                              copy_locations=[str(old)])), encoding="utf-8")
    new = old.with_name(now)
    old.rename(new)                                   # the rename that stranded it
    assert find_orphans(lib) == [rec], "control"
    before = rec.read_bytes()
    plan = plan_reconnect(lib)
    assert plan["matched"] == [(rec, new)]
    assert plan["still"] == [], "nothing to warn about before the press"
    out = apply_reconnect(lib, plan, dry_run=False)
    assert out["moved"][0]["still"] == []
    assert _locations(new) == [str(new)], "the record names the paper as it is now"
    assert find_orphans(lib) == []
    _undo(lib, out["tx_id"])
    assert rec.read_bytes() == before


# --------------------------------------------- every kind of record and name

@pytest.mark.parametrize("new_kind", ["ordinary", "over-long"])
@pytest.mark.parametrize("kind", KINDS)
def test_the_old_place_becomes_the_new_one_and_undo_restores_every_byte(
        lib, kind, new_kind):
    rec, old, new = _strand(lib, kind, new_kind=new_kind)
    before = rec.read_bytes()
    out = _reconnect(lib)
    assert out["reconnected"] == 1 and out["moved"][0]["still"] == []
    assert _locations(new) == [str(new)]
    after = json.loads(find_sidecar(new).read_text(encoding="utf-8"))
    assert {k for k in set(after) | set(json.loads(before))
            if after.get(k) != json.loads(before).get(k)} == {"copy_locations"}
    _undo(lib, out["tx_id"])
    assert rec.read_bytes() == before, "the record that came back is not the one that left"
    assert find_sidecar(new) is None


@pytest.mark.parametrize("kind", KINDS)
def test_the_edit_is_in_the_same_transaction_after_the_move(lib, kind):
    rec, old, new = _strand(lib, kind)
    out = _reconnect(lib)
    tx = json.loads((lib / ".operation_log" / f"{out['tx_id']}.json").read_text())
    assert [op["type"] for op in tx["operations"]] == ["rename", "sidecar_edit"]
    edit = tx["operations"][1]
    assert edit["path"] == str(new)
    assert edit["changes"] == {"copy_locations": [[str(old)], [str(new)]]}


def test_a_coded_record_finds_its_old_name_by_checking_the_hash(lib):
    """``.sidecars/<sha1>``: the name cannot be read back, but each entry
    can be checked -- the one whose name hashes to the record's is the
    paper's old place."""
    rec, old, new = _strand(lib, "over-long")
    assert ".sidecars" in rec.parts, "control: a coded record"
    assert _places_it_answers_for(rec, [str(old)]) == [str(old)]
    assert _places_it_answers_for(rec, [str(old.with_name("other.pdf"))]) == []


def test_a_coded_record_spelled_nfd_answers_to_an_nfc_entry(lib):
    """The hash is of the name as it was spelled. A record coded from the
    decomposed name must still be found from a composed entry."""
    rec, old, new = _strand(lib, "over-long-nfd",
                            locations=None)
    nfc = unicodedata.normalize("NFC", str(old))
    assert nfc != str(old), "control: the entry is in the other form"
    assert _places_it_answers_for(rec, [nfc]) == [nfc]


def test_a_coded_record_spelled_nfc_answers_to_an_nfd_entry(lib):
    """And the other way round: the record coded from the composed name,
    the entry stored decomposed (stored forms do differ from the name's:
    commit 1d06eea found seven such records on 2026-10-09)."""
    rec, old, new = _strand(lib, "over-long-nfd", locations=None)
    composed = old.with_name(unicodedata.normalize("NFC", _name("over-long-nfd", "C")))
    composed.write_bytes(b"%PDF-1.4 composed")
    coded = sidecar_path(composed)
    coded.write_text(_dump({"doi": "10.1/c"}), encoding="utf-8")
    nfd = unicodedata.normalize("NFD", str(composed))
    assert nfd != str(composed) and ".sidecars" in coded.parts, "control"
    assert _places_it_answers_for(coded, [nfd]) == [nfd]


@pytest.mark.parametrize("kind", ["nfd", "over-long-nfd"])
def test_an_entry_in_the_other_unicode_form_is_replaced_not_kept(lib, kind):
    rec, old, new = _strand(lib, kind, locations=None)
    data = json.loads(rec.read_text(encoding="utf-8"))
    data["copy_locations"] = [unicodedata.normalize("NFC", str(old))]
    rec.write_text(_dump(data), encoding="utf-8")
    before = rec.read_bytes()
    out = _reconnect(lib)
    assert _locations(new) == [str(new)] and out["moved"][0]["still"] == []
    _undo(lib, out["tx_id"])
    assert rec.read_bytes() == before


@pytest.mark.skipif(sys.platform != "darwin", reason="APFS folds case")
def test_an_entry_differing_only_in_case_is_the_old_place(lib):
    rec, old, new = _strand(lib, "ordinary", locations=None)
    upper = str(old.with_suffix(".PDF"))
    if not Path(str(rec).replace(".meta.json", ".META.json")).exists():
        pytest.skip("this volume is case-sensitive")
    assert _places_it_answers_for(rec, [upper]) == [upper]


# --------------------------------------------------- what is not the old place

def test_a_topic_copy_with_the_same_name_is_not_the_old_place(lib):
    """A hardlink in a topic folder carries the old basename -- and, for a
    coded record, the same hash. It lives in another folder, so a paper
    there would read another record; it is left exactly as it is."""
    rec, old, new = _strand(lib, "over-long", locations=None)
    topic = _topic_copy(lib, old, new)
    data = json.loads(rec.read_text(encoding="utf-8"))
    data["copy_locations"] = [str(old), str(topic)]
    rec.write_text(_dump(data), encoding="utf-8")
    assert _places_it_answers_for(rec, [str(topic)]) == []
    out = _reconnect(lib)
    assert _locations(new) == [str(new), str(topic)]
    assert out["moved"][0]["still"] == [], "the topic copy exists: nothing wrong"
    assert topic.exists(), "a reconnect renames no other file"


def test_an_old_place_that_cannot_be_told_is_left_and_reported(lib):
    """The record lists only a place it does not answer to (an earlier name,
    from a history this move knows nothing about). That entry is not
    guessed to be the old place: it stays, the paper's path is added, and
    the reconnect says the record still names a file that is not there."""
    earlier = lib / SHELF / "Smith, J. - Earliest name.pdf"
    rec, old, new = _strand(lib, "over-long", locations=[str(earlier)])
    before = rec.read_bytes()
    out = _reconnect(lib)
    assert _locations(new) == [str(earlier), str(new)]
    assert out["moved"][0]["still"] == [
        f"it still lists a place where no file is: {earlier}"]
    _undo(lib, out["tx_id"])
    assert rec.read_bytes() == before


def test_a_record_with_no_locations_gains_the_papers_path(lib):
    """28 of the 37 real ones (measured 2026-10-10): the field is empty.
    The paper's path is added, as a rename through the app would have."""
    rec, old, new = _strand(lib, locations=[])
    out = _reconnect(lib)
    assert _locations(new) == [str(new)] and out["moved"][0]["still"] == []


def test_a_record_without_the_field_gets_none_back_on_undo(lib):
    rec, old, new = _strand(lib, locations=None)
    before = rec.read_bytes()
    out = _reconnect(lib)
    assert _locations(new) == [str(new)]
    tx = json.loads((lib / ".operation_log" / f"{out['tx_id']}.json").read_text())
    assert tx["operations"][1]["absent"] == ["copy_locations"]
    _undo(lib, out["tx_id"])
    assert rec.read_bytes() == before and "copy_locations" not in json.loads(before)


@pytest.mark.parametrize("bad", [None, "a string", {"a": 1}, ["/a.pdf", 7],
                                 ["/a.pdf", None]])
def test_a_list_that_is_not_a_list_is_left_and_reported(lib, bad):
    """Unknown is not fine: the record still moves (its DOI and text are
    what matter), the field is not touched, and the reconnect says so."""
    rec, old, new = _strand(lib, locations=None)
    data = json.loads(rec.read_text(encoding="utf-8"))
    data["copy_locations"] = bad
    rec.write_text(_dump(data), encoding="utf-8")
    before = rec.read_bytes()
    out = _reconnect(lib)
    assert out["reconnected"] == 1
    assert find_sidecar(new).read_bytes() == before, "nothing in it changed"
    assert out["moved"][0]["still"] == [
        "its list of the paper's places could not be read, so it was left as it was"]
    _undo(lib, out["tx_id"])
    assert rec.read_bytes() == before


def test_a_relative_entry_is_never_the_old_place(lib, monkeypatch):
    """Even from the library root, where read against the working directory
    it WOULD answer: what a relative entry names depends on where the
    process happens to run, so it is not taken as the old place."""
    rec, old, new = _strand(lib, locations=None)
    rel = str(old.relative_to(lib))
    monkeypatch.chdir(lib)
    assert _places_it_answers_for(rec, [str(old)]) == [str(old)], "control"
    assert _places_it_answers_for(rec, [rel]) == []


def test_a_record_that_vanished_answers_to_nothing(lib):
    rec, old, new = _strand(lib)
    rec.unlink()
    assert _places_it_answers_for(rec, [str(old)]) is None


def test_a_failed_edit_still_reconnects_and_says_so(lib, monkeypatch):
    import processing.identity as identity

    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(identity, "repath_copy_locations", boom)
    rec, old, new = _strand(lib)
    before = rec.read_bytes()
    out = _reconnect(lib, check_preview=False)       # no preview foresees a full disk
    assert out["reconnected"] == 1 and find_sidecar(new) is not None
    assert out["moved"][0]["still"] == [
        "its list of the paper's places could not be updated: disk full"]
    _undo(lib, out["tx_id"])
    assert rec.read_bytes() == before


@pytest.mark.parametrize("text", ["{ not json", "[1, 2]", "\udcff"])
def test_an_orphan_that_cannot_be_read_is_matched_to_nothing(lib, text):
    """A torn record (a crash, a sync caught mid-write) is not a reason for
    the check to fail: it matches no paper and stays listed."""
    rec, old, new = _strand(lib)
    rec.write_bytes(text.encode("utf-8", "surrogateescape"))
    plan = plan_reconnect(lib)
    assert plan["matched"] == [] and plan["unmatched"] == [rec]
    pairs = {"matched": [(rec, new)]}                  # as if planned earlier
    out = apply_reconnect(lib, pairs, dry_run=False)
    assert out["reconnected"] == 0 and "no longer match" in out["skipped"][0]["reason"]
    assert rec.read_bytes() == text.encode("utf-8", "surrogateescape")


def test_a_move_that_fails_is_not_counted(lib, monkeypatch):
    rec, old, new = _strand(lib)
    plan = plan_reconnect(lib)
    real = Path.rename

    def refuse(self, target):
        if self == rec:
            raise OSError("read-only volume")
        return real(self, target)
    monkeypatch.setattr(Path, "rename", refuse)
    out = apply_reconnect(lib, plan, dry_run=False)
    assert out["reconnected"] == 0 and out["moved"] == []
    assert out["skipped"] == [{"sidecar": rec.name, "reason": "read-only volume"}]
    assert rec.exists() and find_sidecar(new) is None


# ------------------------------------------------------------ into the trash

def test_a_record_joining_its_paper_in_the_trash_names_the_trash(lib):
    """The same move a retirement through ``logged_move`` makes, ending
    the same way: the record names where its paper is."""
    pdf = lib / "02 - Unpublished papers/C" / "Cao, C. - Recursive equilibrium.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 cao")
    rec = sidecar_path(pdf)
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(_dump(dict(OLD_SCHEMA, content_sha256=compute_content_hash(pdf),
                              copy_locations=[str(pdf)])), encoding="utf-8")
    trashed = lib / ".trash/upgraded_preprints" / pdf.name
    trashed.parent.mkdir(parents=True)
    pdf.rename(trashed)                                # the old retirement
    before = rec.read_bytes()
    plan = plan_reconnect(lib)
    assert plan["to_trash"] == [(rec, trashed)] and plan["still"] == []
    out = apply_trash_reconnect(lib, plan, dry_run=False)
    assert out["moved"][0]["still"] == []
    assert _locations(trashed) == [str(trashed)]
    _undo(lib, out["tx_id"])
    assert rec.read_bytes() == before


# ------------------------------------------------------ the pure list rule

def test_with_no_old_place_only_the_new_one_is_added():
    assert repathed_locations(["/a.pdf"], old_path=None, new_path=Path("/b.pdf")) \
        == ["/a.pdf", "/b.pdf"]
    assert repathed_locations(["/b.pdf"], old_path=None, new_path=Path("/b.pdf")) is None
    assert repathed_locations([], old_path=None, new_path=Path("/b.pdf")) == ["/b.pdf"]
    # "no old place" is not the place spelled "None"
    assert repathed_locations(["None"], old_path=None, new_path=Path("/b.pdf")) \
        == ["None", "/b.pdf"]


def test_a_record_already_naming_the_new_place_is_not_rewritten():
    """Nothing to swap and the paper already listed: the record is left
    exactly as it is, duplicates and all -- a move is not a clean-up."""
    locs = ["/b.pdf", "/a.pdf", "/a.pdf"]
    assert repathed_locations(locs, old_path=Path("/x.pdf"), new_path=Path("/b.pdf")) is None
    assert repathed_locations(locs, old_path=None, new_path=Path("/b.pdf")) is None


# ------------------------------------------------------------- the property

_EXTRA = st.sampled_from(["topic", "stale", "old-nfc", "old-dup", "elsewhere"])


@settings(max_examples=60, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(kind=st.sampled_from(KINDS), new_kind=st.sampled_from(["ordinary", "over-long"]),
       listed=st.booleans(), extras=st.lists(_EXTRA, max_size=4))
def test_any_reconnect_names_the_paper_once_and_undoes_byte_for_byte(
        tmp_path, kind, new_kind, listed, extras):
    lib = Path(tempfile.mkdtemp(dir=tmp_path))
    enable_sidecar_mirror(lib)
    rec, old, new = _strand(lib, kind, new_kind=new_kind, locations=None)
    topic = lib / "07a - BSDEs" / old.name
    entries = [str(old)] if listed else []
    for e in extras:
        if e == "topic":
            if not topic.exists():
                _topic_copy(lib, old, new)
            entries.append(str(topic))
        elif e == "stale":
            entries.append(str(lib / SHELF / "Gone, G. - Earlier.pdf"))
        elif e == "old-nfc" and listed:
            entries.append(unicodedata.normalize("NFC", str(old)))
        elif e == "old-dup" and listed:
            entries.append(str(old))
        elif e == "elsewhere":
            entries.append("/Volumes/Elsewhere/a copy.pdf")
    data = json.loads(rec.read_text(encoding="utf-8"))
    data["copy_locations"] = entries
    rec.write_text(_dump(data), encoding="utf-8")
    before = rec.read_bytes()

    out = _reconnect(lib)
    after = _locations(new)
    nfc = lambda s: unicodedata.normalize("NFC", s)            # noqa: E731
    assert [nfc(e) for e in after].count(nfc(str(new))) == 1, "named exactly once"
    assert nfc(str(old)) not in {nfc(e) for e in after}, "the old place is gone"
    kept = [e for e in entries if nfc(e) != nfc(str(old))]
    assert [e for e in after if nfc(e) != nfc(str(new))] == list(dict.fromkeys(kept)), (
        "every other entry kept, in order")
    assert out["moved"][0]["still"] == [
        f"it still lists a place where no file is: {e}"
        for e in after if not os.path.lexists(e)]
    _undo(lib, out["tx_id"])
    assert rec.read_bytes() == before


# ------------------------------------------------------------- the cockpit

@pytest.fixture
def C(monkeypatch, tmp_path):
    from tests.ui.test_cockpit_smoke import _StreamlitModule
    fake = _StreamlitModule()
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    monkeypatch.setenv("MATH_LIBRARY", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delitem(sys.modules, "ui.cockpit", raising=False)
    import ui.cockpit as cockpit
    return cockpit


def _press(C, monkeypatch, prefix):
    monkeypatch.setattr(C.st, "checkbox", lambda *a, **k: True)
    monkeypatch.setattr(C.st, "button", lambda label, *a, **k: label.startswith(prefix))
    monkeypatch.setattr(C.st, "rerun", lambda: None)


def test_the_page_says_which_records_still_name_a_missing_file(C, lib, monkeypatch):
    earlier = lib / SHELF / "Smith, J. - Earliest name.pdf"
    rec, old, new = _strand(lib, locations=[str(earlier)])
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    _press(C, monkeypatch, "Reconnect")
    C._render_orphan_repair(lib, 1)
    kind, msg, details = C.st.session_state["flash"][-1][:3]
    assert kind == "success" and "Reconnected 1 of 1" in msg
    assert "1 moved record(s) still name a place where no file is" in msg
    assert details == [f"{old.stem} — it still lists a place where no file is: {earlier}"]


def test_a_clean_reconnect_says_nothing_more(C, lib, monkeypatch):
    rec, old, new = _strand(lib)
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    _press(C, monkeypatch, "Reconnect")
    C._render_orphan_repair(lib, 1)
    kind, msg, details = C.st.session_state["flash"][-1][:3]
    assert kind == "success" and "no file" not in msg and details == []
    assert _locations(new) == [str(new)]


def _warnings(C, monkeypatch):
    said = []
    monkeypatch.setattr(C.st, "warning", lambda msg, *a, **k: said.append(msg))
    return said


def test_the_page_warns_before_the_press_what_would_stay_wrong(C, lib, monkeypatch):
    earlier = lib / SHELF / "Smith, J. - Earliest name.pdf"
    rec, old, new = _strand(lib, locations=[str(earlier)])
    said = _warnings(C, monkeypatch)
    shown = []
    monkeypatch.setattr(C.st, "markdown", lambda m, *a, **k: shown.append(m))
    monkeypatch.setattr(C.st, "button", lambda *a, **k: False)
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    C._render_orphan_repair(lib, 1)
    warned = [w for w in said if "no file is" in w]
    assert len(warned) == 1
    assert warned[0].startswith("1 of these record(s) will still name a place "
                                "where no file is after reconnecting")
    assert f"`{old.stem}` — it still lists a place where no file is: {earlier}" in shown
    assert find_orphans(lib) == [rec], "nothing was pressed"


def test_the_page_says_nothing_more_when_nothing_would_stay_wrong(C, lib, monkeypatch):
    _strand(lib)
    said = _warnings(C, monkeypatch)
    monkeypatch.setattr(C.st, "button", lambda *a, **k: False)
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    C._render_orphan_repair(lib, 1)
    assert not any("no file is" in w for w in said)


def test_the_warning_names_only_the_records_of_its_own_button(C, lib, monkeypatch):
    """A shelf record that would stay wrong is not warned about under the
    trash button, nor the other way round."""
    earlier = lib / SHELF / "Smith, J. - Earliest name.pdf"
    _strand(lib, locations=[str(earlier)])
    pdf = lib / "02 - Unpublished papers/C" / "Cao, C. - X.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 cao")
    trec = sidecar_path(pdf)
    trec.parent.mkdir(parents=True, exist_ok=True)
    trec.write_text(_dump(dict(OLD_SCHEMA, content_sha256=compute_content_hash(pdf),
                               copy_locations=[str(pdf)])), encoding="utf-8")
    trashed = lib / ".trash/upgraded_preprints" / pdf.name
    trashed.parent.mkdir(parents=True)
    pdf.rename(trashed)
    said = _warnings(C, monkeypatch)
    monkeypatch.setattr(C.st, "button", lambda *a, **k: False)
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    C._render_orphan_repair(lib, 2)
    warned = [w for w in said if "no file is" in w]
    assert len(warned) == 1 and "after reconnecting" in warned[0]


def test_the_trash_button_warns_before_the_press_too(C, lib, monkeypatch):
    pdf = lib / "02 - Unpublished papers/C" / "Cao, C. - X.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 cao")
    rec = sidecar_path(pdf)
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(_dump(dict(OLD_SCHEMA, content_sha256=compute_content_hash(pdf),
                              copy_locations=[str(pdf), "/Volumes/Gone/x.pdf"])),
                   encoding="utf-8")
    trashed = lib / ".trash/upgraded_preprints" / pdf.name
    trashed.parent.mkdir(parents=True)
    pdf.rename(trashed)
    said = _warnings(C, monkeypatch)
    monkeypatch.setattr(C.st, "button", lambda *a, **k: False)
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    C._render_orphan_repair(lib, 1)
    warned = [w for w in said if "no file is" in w]
    assert len(warned) == 1 and "after joining their papers" in warned[0]


def test_the_trash_button_says_it_too(C, lib, monkeypatch):
    pdf = lib / "02 - Unpublished papers/C" / "Cao, C. - X.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 cao")
    rec = sidecar_path(pdf)
    rec.parent.mkdir(parents=True, exist_ok=True)
    gone = str(lib / "02 - Unpublished papers/C/Cao, C. - Earlier.pdf")
    rec.write_text(_dump(dict(OLD_SCHEMA, content_sha256=compute_content_hash(pdf),
                              copy_locations=[gone])), encoding="utf-8")
    trashed = lib / ".trash/upgraded_preprints" / pdf.name
    trashed.parent.mkdir(parents=True)
    pdf.rename(trashed)
    C.st.session_state["orphan_plan"] = C._orphan_plan_for_session(plan_reconnect(lib), lib)
    _press(C, monkeypatch, "Put ")
    C._render_orphan_repair(lib, 1)
    kind, msg, details = C.st.session_state["flash"][-1][:3]
    assert "still name a place where no file is" in msg
    assert f"Cao, C. - X — it still lists a place where no file is: {gone}" in details
