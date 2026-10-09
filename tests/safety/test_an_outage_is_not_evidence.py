"""A Crossref lookup that did not happen is not evidence that a paper is unpublished.

Cockpit audit finding 1 (approved) said a failed publication check was
reported as "✓ done, 0 newly-published papers found". The verification
pass found the likelier path, and following it found worse:

  * ``CrossrefChecker.check_title`` swallows timeouts, connection errors
    and 5xx responses and returns ``None`` -- the same value it returns
    for "Crossref has no match". So during an outage every paper came back
    "not published", and the check reported a confident 0.
  * Those entries then went into ``update_publication_state``, which
    recorded each as a MISS: the recheck counter advanced, and after
    three misses the paper was latched ``permanently_unpublished`` and
    never re-checked again. Three runs during an outage would have
    permanently written off papers that were never actually checked.
  * A 200 response whose body was not JSON (a captive portal, a proxy
    page) raised straight out of the scan from outside the try block.

Now "could not ask" is a third value (``published: None``) all the way
through: the checker says when a lookup failed, the scan records it, the
state machine records NOTHING for it, and the cockpit reports how many
papers were not checked instead of folding them into the zero.

Finding 2 rides on the same path: the record rewrites were irreversible,
on a page whose caption said it "changes nothing". The state update now
takes an undo log, and the cockpit opens a transaction around the check.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from processing.identity import PaperIdentity
from processing.publication_state import update_publication_state

COCKPIT = Path(__file__).resolve().parents[2] / "src" / "ui" / "cockpit.py"


# ------------------------------------------------------------ the checker

class _Resp:
    def __init__(self, status=200, body=None, text_body=None):
        self.status_code = status
        self._body = body
        self._text = text_body
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.exceptions.HTTPError(str(self.status_code))

    def json(self):
        if self._text is not None:
            raise ValueError("Expecting value: line 1 column 1")
        return self._body


def _checker(monkeypatch, behaviour):
    from processing import publication_checker as pc
    c = pc.CrossrefChecker(cache_path=None)
    monkeypatch.setattr(pc.time, "sleep", lambda *_: None)
    c._throttle = lambda: None if hasattr(c, "_throttle") else None

    def _get(*a, **k):
        if isinstance(behaviour, Exception):
            raise behaviour
        return behaviour

    monkeypatch.setattr(c.session, "get", _get)
    return c


@pytest.mark.parametrize("failure", ["timeout", "connection", "503", "not-json"])
def test_a_failed_lookup_says_it_failed(monkeypatch, failure):
    import requests
    behaviour = {
        "timeout": requests.exceptions.Timeout("slow"),
        "connection": requests.exceptions.ConnectionError("offline"),
        "503": _Resp(status=503),
        "not-json": _Resp(status=200, text_body="<html>captive portal</html>"),
    }[failure]
    c = _checker(monkeypatch, behaviour)
    assert c.check_title("Some title of a paper", ["Author"]) is None
    assert c.last_lookup_failed is True, failure
    assert c.failed_lookups == 1


def test_an_answered_lookup_with_no_match_is_not_a_failure(monkeypatch):
    c = _checker(monkeypatch, _Resp(body={"message": {"items": []}}))
    assert c.check_title("Some title of a paper", ["Author"]) is None
    assert c.last_lookup_failed is False, "no match IS an answer"


def test_the_flag_resets_on_the_next_successful_lookup(monkeypatch):
    import requests
    c = _checker(monkeypatch, requests.exceptions.Timeout("slow"))
    c.check_title("First title here", ["A"])
    assert c.last_lookup_failed
    monkeypatch.setattr(c.session, "get",
                        lambda *a, **k: _Resp(body={"message": {"items": []}}))
    c.check_title("Second title here", ["B"])
    assert c.last_lookup_failed is False, "a stale True would mislabel this paper"


# --------------------------------------------------- the scan records it

def test_the_scan_marks_an_unanswered_paper_UNKNOWN_not_unpublished(tmp_path, monkeypatch):
    import requests
    from processing import publication_checker as pc
    d = tmp_path / "02 - Unpublished papers"
    d.mkdir()
    (d / "Author, A. - A long enough title for parsing.pdf").write_bytes(b"%PDF-1.4")
    c = _checker(monkeypatch, requests.exceptions.ConnectionError("offline"))
    out = pc.scan_directory(d, checker=c)
    assert len(out) == 1
    assert out[0]["published"] is None, "unknown, not False"
    assert out[0]["lookup_failed"] is True


# ------------------------------------------ the state machine ignores it

def _paper(tmp_path) -> Path:
    pdf = tmp_path / "p.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    PaperIdentity().save(pdf)
    return pdf


def test_an_unknown_result_records_nothing(tmp_path):
    pdf = _paper(tmp_path)
    summary = update_publication_state([{"file": str(pdf), "published": None}])
    ident = PaperIdentity.load(pdf)
    assert ident.recheck_count == 0
    assert not ident.publication_checks
    assert summary.unchecked == [str(pdf)]


def test_any_number_of_outages_never_latches_a_paper(tmp_path):
    """THE CORRUPTION. Before the fix, three of these wrote the paper off."""
    pdf = _paper(tmp_path)
    for _ in range(6):
        update_publication_state([{"file": str(pdf), "published": None}])
    ident = PaperIdentity.load(pdf)
    assert not ident.permanently_unpublished
    assert ident.recheck_count == 0


def test_real_misses_still_latch_so_the_guard_is_not_simply_off(tmp_path):
    """Pin the other direction: the state machine still works on evidence."""
    pdf = _paper(tmp_path)
    for _ in range(5):
        update_publication_state([{"file": str(pdf), "published": False}])
    assert PaperIdentity.load(pdf).permanently_unpublished


# ---------------------------------------------- finding 2: undoable writes

def test_the_record_rewrite_goes_into_the_undo_log_when_one_is_open(tmp_path):
    from processing.undo_log import UndoLog
    pdf = _paper(tmp_path)
    log = UndoLog(log_dir=tmp_path / ".operation_log")
    log.begin_transaction("publication check (test)")
    update_publication_state([{"file": str(pdf), "published": False}], undo_log=log)
    assert log.has_operations(), "the sidecar rewrite was not recorded"
    log.commit()


def test_the_cockpit_opens_a_transaction_around_the_check():
    src = COCKPIT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "id", "") == "check_publications"]
    assert calls, "check_publications is no longer called from the cockpit?"
    assert all(any(k.arg == "undo_log" for k in c.keywords) for c in calls), (
        "the Maintenance page's publication check must pass an undo log")


def _maintenance_strings() -> str:
    """Every string literal the Maintenance page can show -- and only
    those: "changes nothing" is TRUE of a preview button elsewhere."""
    tree = ast.parse(COCKPIT.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "render_maintenance")
    return " ".join(n.value for n in ast.walk(fn)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str))


def test_the_maintenance_page_no_longer_claims_it_changes_nothing():
    """Its caption said "it changes nothing" while the publication check
    rewrote records and latched a permanent flag."""
    text = _maintenance_strings()
    assert "Run checks" in text, "wrong function inspected"
    for claim in ("it changes nothing", "nothing in your library is changed",
                  "they only look and report"):
        assert claim not in text, f"false claim still on the page: {claim!r}"
    assert "reversible from the Activity page" in text, (
        "the page must now say the record changes can be undone")


def test_check_publications_reports_a_missing_folder_instead_of_skipping_silently(tmp_path):
    from maintenance.weekly_report import check_publications
    out = check_publications(tmp_path)          # neither 02 nor 03 exists
    assert len(out["_not_checked"]) == 2
    assert out["unchecked"] == []
