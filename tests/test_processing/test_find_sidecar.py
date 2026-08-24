"""Where a sidecar IS, as distinct from where it should GO.

``sidecar_path`` answers the second question. Using it for the first one
silently orphans files: a PDF name can sit under the 255-byte limit while
``<stem>.meta.json`` is over it, because ".meta.json" is six bytes longer
than ".pdf". A sidecar written under an older convention then becomes
invisible, the rename moves the PDF, and the identity record stays behind --
with "no sidecar" and "a sidecar I could not find" returning the same None.
"""
import json

import pytest

from processing.identity import (
    MAX_BASENAME_BYTES, MIRROR_DIR_NAME, find_sidecar, sidecar_candidates,
    sidecar_path,
)


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / "Maths"
    (root / "01 - Published papers" / "R").mkdir(parents=True)
    (root / MIRROR_DIR_NAME).mkdir()
    monkeypatch.setenv("MATH_LIBRARY", str(root))
    return root


#: A stem in the window where the two rules disagree: the sidecar name is
#: over MAX_BASENAME_BYTES (251, the module's own conservative limit) but
#: still under the filesystem's 255, so the file CAN exist at the mirror path
#: while ``sidecar_path`` answers with the hashed fallback.
#:
#: Four bytes wide, so it has to be constructed. A long-looking string does
#: not do it: my first attempt was under 251 (the two agreed, and the guard
#: assertion said so) and my second was over 255 (the filesystem refused to
#: create it, which is why the fallback exists at all).
def _boundary_stem(lead: str) -> str:
    target = 255 - len(".meta.json")              # meta name lands exactly on 255
    filler = "Jentzen, A., "
    stem = (lead + filler * ((target - len(lead)) // len(filler) + 1))[:target]
    assert len((stem + ".pdf").encode()) <= 255
    assert MAX_BASENAME_BYTES < len((stem + ".meta.json").encode()) <= 255
    return stem


def _pdf(library, name):
    p = library / "01 - Published papers" / "R" / f"{name}.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    return p


class TestItFindsWhatIsThere:
    def test_the_canonical_location(self, library):
        pdf = _pdf(library, "Rogers, L. C. G. - A short title")
        want = sidecar_path(pdf)
        want.parent.mkdir(parents=True, exist_ok=True)
        want.write_text("{}")
        assert find_sidecar(pdf) == want

    def test_the_mirror_entry_under_its_full_name(self, library):
        """The case that orphaned files: the PDF name fits, the sidecar name
        does not, so sidecar_path answers with the hashed fallback while the
        sidecar sits in the mirror under its full name."""
        long_name = _boundary_stem("Ackermann, J., ")
        pdf = _pdf(library, long_name)
        rel = pdf.relative_to(library)
        actual = library / MIRROR_DIR_NAME / rel.with_suffix(".meta.json")
        actual.parent.mkdir(parents=True, exist_ok=True)
        actual.write_text('{"from": "the mirror"}')
        assert sidecar_path(pdf) != actual, "this test needs the two to disagree"
        assert find_sidecar(pdf) == actual
        assert json.loads(find_sidecar(pdf).read_text())["from"] == "the mirror"

    def test_the_natural_sibling_from_before_the_mirror_tree(self, library):
        pdf = _pdf(library, "Yor, M. - Older convention")
        sibling = pdf.with_suffix(".meta.json")
        sibling.write_text('{"from": "a sibling"}')
        assert find_sidecar(pdf) == sibling


class TestItDoesNotInvent:
    def test_no_sidecar_anywhere_returns_none(self, library):
        assert find_sidecar(_pdf(library, "Nobody, A. - Nothing here")) is None

    def test_it_never_returns_a_path_that_does_not_exist(self, library):
        pdf = _pdf(library, "Nobody, A. - Nothing here")
        found = find_sidecar(pdf)
        assert found is None or found.exists()


class TestPrecedence:
    def test_the_canonical_location_wins_when_several_exist(self, library):
        """12 papers in the real library have BOTH -- an old named entry and a
        newer hashed one, drifting apart since the length boundary moved.
        The canonical one is the answer; the other is a data question, not a
        resolution question."""
        long_name = _boundary_stem("Perolat, J., ")
        pdf = _pdf(library, long_name)
        rel = pdf.relative_to(library)
        named = library / MIRROR_DIR_NAME / rel.with_suffix(".meta.json")
        named.parent.mkdir(parents=True, exist_ok=True)
        named.write_text('{"which": "named"}')
        canonical = sidecar_path(pdf)
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text('{"which": "canonical"}')
        assert find_sidecar(pdf) == canonical

    def test_candidates_are_unique_and_start_with_the_canonical_one(self, library):
        pdf = _pdf(library, "Rogers, L. C. G. - A short title")
        cands = sidecar_candidates(pdf)
        assert cands[0] == sidecar_path(pdf)
        assert len(cands) == len({str(c) for c in cands})


class TestTheRenameCarriesIt:
    def test_a_sidecar_stored_under_the_old_convention_still_travels(self, library):
        """The whole point. Before this, logged_rename asked sidecar_path for
        the SOURCE, found nothing at the hashed location, and left the mirror
        entry behind while the PDF moved."""
        from processing.undo_log import logged_rename
        long_name = _boundary_stem("Ackermann, J., ")
        pdf = _pdf(library, long_name)
        rel = pdf.relative_to(library)
        old_side = library / MIRROR_DIR_NAME / rel.with_suffix(".meta.json")
        old_side.parent.mkdir(parents=True, exist_ok=True)
        # A REALISTIC record. My first version used {"identity": "kept"},
        # which is not a valid sidecar, so the schema-normalising write after
        # the rename replaced it with defaults and the test read the failure
        # as "the sidecar did not travel". It had travelled.
        old_side.write_text(json.dumps({
            "schema_version": 1,
            "doi": "10.1000/kept",
            "content_sha256": "abc123",
            "first_ingest_tx_id": "deadbeef",
        }))

        new_pdf = pdf.with_name(long_name.replace("Ackermann, J.,", "Ackermann, J.;", 1) + ".pdf")
        logged_rename(pdf, new_pdf)

        assert new_pdf.exists()
        assert not old_side.exists(), "the sidecar was left behind"
        moved = find_sidecar(new_pdf)
        assert moved is not None, "the sidecar is nowhere to be found"
        assert json.loads(moved.read_text())["doi"] == "10.1000/kept"
