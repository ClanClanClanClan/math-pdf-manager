"""A lookup that FAILED must never be remembered as "not on arXiv".

MEASURED 2026-10-15 on the real "12 - To be sorted" (2,414 PDFs, 85.5%
of which ask arXiv): with arXiv unreachable each Sort Queue paper took
10.2-10.9 s to show and 10.1 s more to approve, because a failed lookup
was never remembered -- nor was a genuine "no such id", which was asked
again on every extraction. The fix remembers answers, and that is
exactly where the non-negotiable bites: "I could not ask" and "arXiv
says there is no such paper" are different answers. Store the first as
the second and a paper is named from its own (often wrong) metadata for
a day with a message claiming arXiv had nothing.

Every test here injects the network's behaviour; none reaches it.
"""
from __future__ import annotations

import json
import time

import pytest
import requests
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as hst

from processing import lookup_cache as lc
from processing import ingest

ATOM = 'xmlns="http://www.w3.org/2005/Atom"'
OS = 'xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"'


def feed(entries=(), total=None, *, counted=True):
    """An arXiv API reply. ``entries`` is [(id, title)]; arXiv's real
    replies carry their own <id> and a result count, and so do these."""
    body = "".join(
        f"<entry><id>http://arxiv.org/abs/{i}v1</id><title>{t}</title>"
        f"<author><name>Author {i}</name></author></entry>"
        for i, t in entries)
    count = (f"<opensearch:totalResults>{len(entries) if total is None else total}"
             f"</opensearch:totalResults>") if counted else ""
    return f'<?xml version="1.0"?><feed {ATOM} {OS}>{count}{body}</feed>'.encode()


def error_feed(bad_id):
    """What arXiv sends when ONE id in the request is malformed (measured:
    the whole batch is refused with a single entry naming it)."""
    return (f'<?xml version="1.0"?><feed {ATOM} {OS}>'
            "<opensearch:totalResults>1</opensearch:totalResults>"
            f"<entry><id>https://arxiv.org/api/errors#incorrect_id_format_for_{bad_id}"
            "</id><title>Error</title></entry></feed>").encode()


class Resp:
    def __init__(self, status=200, content=b"", payload=None):
        self.status_code = status
        self.content = content
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


@pytest.fixture
def net(monkeypatch):
    """Scripted network. Push behaviours; each request pops one.

    A behaviour is a Resp, an exception instance (raised), or a callable
    taking the requested ids and returning either.
    """
    script: list = []
    calls: list = []

    def fake_get(url, *a, **k):
        if "id_list=" in url:
            ids = url.split("id_list=")[1].split("&")[0].split(",")
        else:
            ids = [url.rsplit("/works/", 1)[-1]]
        calls.append(ids)
        if not script:
            raise AssertionError(f"unexpected request for {ids}")
        b = script.pop(0)
        if callable(b) and not isinstance(b, Resp):
            b = b(ids)
        if isinstance(b, BaseException):
            raise b
        return b

    monkeypatch.setattr(requests, "get", fake_get)

    class Net:
        pass
    n = Net()
    n.script, n.calls = script, calls
    return n


def stored(ns, key):
    """What is on disk for ns:key, read raw -- not through the code under test."""
    p = lc.cache_path()
    if not p.exists():
        return None
    return json.loads(p.read_text()).get(f"{ns}:{key}")


# ---------------------------------------------------------------------------
# The three answers, from the network
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("failure", [
    requests.exceptions.ConnectionError("offline"),
    requests.exceptions.ConnectTimeout("no route"),
    requests.exceptions.ReadTimeout("slow"),
    Resp(503), Resp(429), Resp(502), Resp(500),
], ids=["offline", "connect-timeout", "read-timeout", "503", "429", "502", "500"])
def test_a_network_failure_is_unknown_and_never_stored(net, failure):
    net.script.append(failure)
    ans = ingest.arxiv_lookup("2401.00001v2")
    assert ans.state == lc.UNKNOWN
    assert ans.record == {}
    assert ans.reason, "an unknown must say why"
    assert stored("arxiv", "2401.00001") is None, (
        "a failure was written to the cache -- it would be read back as an answer")
    assert lc.unreachable("arxiv"), "the failure did not pause further asking"


@pytest.mark.parametrize("failure, words", [
    (requests.exceptions.ConnectionError("x"), "no connection"),
    (requests.exceptions.ConnectTimeout("x"), "did not answer in time"),
    (requests.exceptions.ReadTimeout("x"), "did not answer in time"),
    (requests.exceptions.TooManyRedirects("x"), "the request failed"),
], ids=["offline", "connect-timeout", "read-timeout", "other"])
def test_the_reason_is_in_plain_words(net, failure, words):
    net.script.append(failure)
    assert words in ingest.arxiv_lookup("2401.00001").reason


def test_an_unreachable_host_is_given_up_on_in_5_seconds(monkeypatch):
    """The recorded 10-11 s per paper was a 10 s CONNECT timeout. Reading a
    slow reply still gets its 10 s (single) or 30 s (batch)."""
    seen = []

    def fake_get(url, *a, **k):
        seen.append(k.get("timeout"))
        raise requests.exceptions.ConnectTimeout("x")
    monkeypatch.setattr(requests, "get", fake_get)
    ingest.arxiv_lookup("2401.00001")
    lc.forget_unreachable()
    ingest.prefetch_arxiv(["2401.00002", "2401.00003"])
    ingest.crossref_lookup("10.1/x")
    assert [t[0] for t in seen] == [5, 5, 5], seen
    assert [t[1] for t in seen] == [10, 30, 10], seen


def test_while_unreachable_nothing_is_asked_and_after_it_is(net):
    net.script.append(requests.exceptions.ConnectionError("offline"))
    assert ingest.arxiv_lookup("2401.00001").state == lc.UNKNOWN
    # The next papers do not each wait out their own timeout ...
    for i in range(2, 6):
        a = ingest.arxiv_lookup(f"2401.0000{i}")
        assert a.state == lc.UNKNOWN and "next try after" in a.reason
    assert len(net.calls) == 1
    # ... and once the pause is over arXiv is asked again, and believed.
    until, why = lc._DOWN["arxiv"]
    lc._DOWN["arxiv"] = (time.time() - 1, why)
    net.script.append(Resp(200, feed([("2401.00001", "Back online")])))
    a = ingest.arxiv_lookup("2401.00001")
    assert a.state == lc.FOUND and a.record["title"] == "Back online"
    assert len(net.calls) == 2


@pytest.mark.parametrize("reply", [
    Resp(400), Resp(404), Resp(200, b"<<not xml"),
    Resp(200, feed(counted=False)),
    Resp(200, feed([("1111.11111", "Someone else's paper")])),
    Resp(200, feed([("2401.00001", "")])),
], ids=["400", "404", "garbage", "no-count", "foreign-entry", "untitled"])
def test_a_reply_that_settles_nothing_is_unknown_and_not_stored(net, reply):
    net.script.append(reply)
    a = ingest.arxiv_lookup("2401.00001")
    assert a.state == lc.UNKNOWN, a
    assert stored("arxiv", "2401.00001") is None
    # Nothing about the SERVICE is wrong, so do not stop asking.
    assert lc.unreachable("arxiv") is None


def test_a_genuine_miss_is_absent_remembered_and_asked_once(net):
    net.script.append(Resp(200, feed([], total=0)))
    a = ingest.arxiv_lookup("2401.99999")
    assert a.state == lc.ABSENT
    assert stored("arxiv", "2401.99999")["state"] == "absent"
    b = ingest.arxiv_lookup("2401.99999v3")
    assert b.state == lc.ABSENT and b.cached
    assert len(net.calls) == 1, "a remembered 'no such id' was asked again"


def test_a_malformed_id_is_absent(net):
    net.script.append(Resp(200, error_feed("1234.56789")))
    assert ingest.arxiv_lookup("1234.56789").state == lc.ABSENT


def test_found_is_remembered_with_its_record(net):
    net.script.append(Resp(200, feed([("2401.00001", "A title")])))
    assert ingest.lookup_arxiv("2401.00001")["title"] == "A title"
    assert ingest.lookup_arxiv("2401.00001v9")["title"] == "A title"
    assert len(net.calls) == 1


# ---------------------------------------------------------------------------
# Batches
# ---------------------------------------------------------------------------

def test_a_batch_settles_present_and_absent_ids(net):
    net.script.append(Resp(200, feed([("2401.00002", "Two")])))
    assert ingest.prefetch_arxiv(["2401.00001", "2401.00002", "2401.00003"]) == 1
    assert stored("arxiv", "2401.00002")["state"] == "found"
    assert stored("arxiv", "2401.00001")["state"] == "absent"
    assert stored("arxiv", "2401.00003")["state"] == "absent"


def test_an_empty_reply_to_many_ids_settles_none_of_them(net):
    """25 ids from 25 real filenames, all absent at once, is not an answer;
    it is the API having a bad moment. Remembering it would hide 25 real
    papers for a day."""
    net.script.append(Resp(200, feed([], total=0)))
    ingest.prefetch_arxiv(["2401.00001", "2401.00002"])
    assert stored("arxiv", "2401.00001") is None
    assert stored("arxiv", "2401.00002") is None


def test_one_malformed_id_does_not_sink_its_batch(net):
    net.script.append(Resp(200, error_feed("2499.99")))
    net.script.append(lambda ids: Resp(200, feed([(i, f"T {i}") for i in ids])))
    found = ingest.prefetch_arxiv(["2401.00001", "2499.99", "2401.00002"])
    assert found == 2
    assert net.calls[1] == ["2401.00001", "2401.00002"], net.calls
    assert stored("arxiv", "2499.99")["state"] == "absent"


def test_a_batch_that_keeps_being_refused_is_retried_once_only(net):
    net.script.extend([Resp(200, error_feed("x")), Resp(200, error_feed("x"))])
    ingest.prefetch_arxiv(["2401.00001", "2401.00002"])
    assert len(net.calls) == 2


def test_prefetch_stops_at_the_first_network_failure(net):
    """Offline, 2,000 ids used to cost 80 requests x a 30 s timeout."""
    net.script.append(requests.exceptions.ConnectTimeout("down"))
    ids = [f"2401.{i:05d}" for i in range(60)]
    assert ingest.prefetch_arxiv(ids) == 0
    assert len(net.calls) == 1


def test_prefetch_does_not_ask_about_what_it_already_knows(net):
    lc.put("arxiv", "2401.00001", lc.Answer(lc.FOUND, {"title": "x"}))
    lc.put("arxiv", "2401.00002", lc.Answer(lc.ABSENT))
    assert ingest.prefetch_arxiv(["2401.00001v1", "2401.00002"]) == 0
    assert net.calls == []


# ---------------------------------------------------------------------------
# Property: under any mix of failures and reorderings, no false absence and
# no wrong record.
# ---------------------------------------------------------------------------

_IDS = [f"2402.{i:05d}" for i in range(12)]
_MODES = hst.sampled_from(["ok", "ok", "ok", "offline", "timeout", "503",
                           "garbage", "empty", "nocount"])


@settings(max_examples=150, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(exists=hst.lists(hst.booleans(), min_size=len(_IDS), max_size=len(_IDS)),
       modes=hst.lists(_MODES, min_size=1, max_size=12),
       batch=hst.integers(min_value=1, max_value=12),
       reverse=hst.booleans())
def test_no_failure_ever_becomes_an_absence(monkeypatch, tmp_path_factory,
                                            exists, modes, batch, reverse):
    monkeypatch.setenv("MATHPDF_LOOKUP_CACHE",
                       str(tmp_path_factory.mktemp("prop") / "c.json"))
    lc.forget_unreachable()
    monkeypatch.setattr(ingest, "ARXIV_BATCH", batch)
    truth = {i: (f"Title {i}" if e else None) for i, e in zip(_IDS, exists)}
    script = list(modes)

    def fake_get(url, *a, **k):
        ids = url.split("id_list=")[1].split("&")[0].split(",")
        mode = script.pop(0) if script else "ok"
        if mode == "offline":
            raise requests.exceptions.ConnectionError("x")
        if mode == "timeout":
            raise requests.exceptions.ReadTimeout("x")
        if mode == "503":
            return Resp(503)
        if mode == "garbage":
            return Resp(200, b"<feed")
        if mode == "empty" and len(ids) > 1:
            return Resp(200, feed([], total=0))
        if mode == "nocount":
            return Resp(200, feed([], counted=False))
        entries = [(i, truth[i]) for i in ids if truth.get(i)]
        if reverse:
            entries.reverse()           # arXiv reorders freely
        return Resp(200, feed(entries))

    monkeypatch.setattr(requests, "get", fake_get)
    ingest.prefetch_arxiv(_IDS)
    lc.forget_unreachable()
    for i in _IDS:
        ingest.arxiv_lookup(i)
    for i in _IDS:
        got = lc.get("arxiv", i)
        if got is None:
            continue                    # unknown: allowed, asked again later
        if got.state == lc.ABSENT:
            assert truth[i] is None, f"{i} exists but was remembered absent"
        else:
            assert got.record["title"] == truth[i], (
                f"{i} was remembered with another paper's record")


# ---------------------------------------------------------------------------
# The store: expiry, corruption, location
# ---------------------------------------------------------------------------

def test_found_expires_after_its_ttl():
    t0 = 1_800_000_000.0
    lc.put("arxiv", "k", lc.Answer(lc.FOUND, {"title": "t"}), now=t0)
    assert lc.get("arxiv", "k", now=t0 + lc.FOUND_TTL - 1).found
    assert lc.get("arxiv", "k", now=t0 + lc.FOUND_TTL) is None


def test_absent_expires_sooner_than_found():
    t0 = 1_800_000_000.0
    lc.put("arxiv", "k", lc.Answer(lc.ABSENT), now=t0)
    assert lc.get("arxiv", "k", now=t0 + lc.ABSENT_TTL - 1).state == lc.ABSENT
    assert lc.get("arxiv", "k", now=t0 + lc.ABSENT_TTL) is None
    assert lc.ABSENT_TTL < lc.FOUND_TTL


def test_an_expired_absence_is_asked_again(net):
    lc.put("arxiv", "2401.00001", lc.Answer(lc.ABSENT),
           now=time.time() - lc.ABSENT_TTL - 5)
    net.script.append(Resp(200, feed([("2401.00001", "Announced since")])))
    assert ingest.arxiv_lookup("2401.00001").record["title"] == "Announced since"


def test_unknown_is_refused_by_the_store_itself():
    lc.put("arxiv", "k", lc.Answer(lc.UNKNOWN, reason="offline"))
    assert stored("arxiv", "k") is None
    assert lc.get("arxiv", "k") is None


def test_a_found_without_a_record_is_not_stored():
    lc.put("arxiv", "k", lc.Answer(lc.FOUND, {}))
    assert stored("arxiv", "k") is None
    assert lc.get("arxiv", "k") is None


def test_a_stored_found_without_a_record_is_not_believed():
    p = lc.cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"arxiv:k": {"state": "found", "at": time.time(),
                                         "rec": {}}}))
    assert lc.get("arxiv", "k") is None


def test_a_timestamp_from_the_future_is_not_believed():
    lc.put("arxiv", "k", lc.Answer(lc.FOUND, {"title": "t"}),
           now=time.time() + 3600)
    assert lc.get("arxiv", "k") is None


@pytest.mark.parametrize("content", [
    b"", b"{", b"\xff\xfe\x00garbage", b"[1, 2, 3]", b"null", b'"a string"',
    b'{"arxiv:k": "not a dict"}',
    b'{"arxiv:k": {"state": "maybe", "at": 1e12, "rec": {}}}',
    b'{"arxiv:k": {"state": "found", "at": "yesterday", "rec": {"title": "t"}}}',
    b'{"arxiv:k": {"state": "found", "at": true, "rec": {"title": "t"}}}',
    b'{"arxiv:k": {"state": "found", "at": 1e9, "rec": ["t"]}}',
    b'{"arxiv:k": {"state": "unknown", "at": 1e12, "rec": {}}}',
], ids=["empty", "truncated", "binary", "list", "null", "string", "entry-str",
        "bad-state", "bad-at", "bool-at", "rec-list", "stored-unknown"])
def test_a_damaged_cache_is_ignored_then_replaced(content):
    p = lc.cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    assert lc.get("arxiv", "k") is None          # no exception, no answer
    lc.put("arxiv", "j", lc.Answer(lc.ABSENT))
    data = json.loads(p.read_text())             # valid JSON again
    assert data["arxiv:j"]["state"] == "absent"
    assert lc.get("arxiv", "j").state == lc.ABSENT


@pytest.mark.parametrize("rec", [[["title", "x"]], ["t"], "ab", 7, None])
def test_a_fresh_record_that_is_not_a_mapping_is_not_believed(rec):
    """A list of pairs would even convert cleanly into a record nobody
    stored; it must be refused, not reinterpreted."""
    p = lc.cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"arxiv:k": {"state": "found", "at": time.time(),
                                         "rec": rec}}))
    assert lc.get("arxiv", "k") is None


def test_a_damaged_entry_does_not_cost_the_good_ones():
    p = lc.cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    good = {"state": "found", "at": time.time(), "rec": {"title": "kept"}}
    p.write_text(json.dumps({"arxiv:good": good, "arxiv:bad": {"state": 7}}))
    assert lc.get("arxiv", "good").record == {"title": "kept"}
    lc.put("arxiv", "new", lc.Answer(lc.ABSENT))
    assert lc.get("arxiv", "good").record == {"title": "kept"}


def test_a_cache_that_cannot_be_written_only_costs_time(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("MATHPDF_LOOKUP_CACHE", str(blocker / "sub" / "c.json"))
    lc.put("arxiv", "k", lc.Answer(lc.ABSENT))   # must not raise
    assert lc.get("arxiv", "k") is None


def test_expired_entries_are_dropped_on_write():
    t0 = time.time()
    lc.put("arxiv", "old", lc.Answer(lc.ABSENT), now=t0 - lc.ABSENT_TTL - 1)
    lc.put("arxiv", "new", lc.Answer(lc.ABSENT), now=t0)
    assert "arxiv:old" not in json.loads(lc.cache_path().read_text())


def test_another_process_answers_are_seen():
    lc.put("arxiv", "a", lc.Answer(lc.ABSENT))
    assert lc.get("arxiv", "b") is None
    p = lc.cache_path()
    data = json.loads(p.read_text())
    data["arxiv:b"] = {"state": "found", "at": time.time(), "rec": {"title": "B"}}
    p.write_text(json.dumps(data) + " ")         # new size -> new identity
    assert lc.get("arxiv", "b").record == {"title": "B"}


def test_the_cache_lives_in_mathpdf_never_in_the_library(monkeypatch, tmp_path):
    from core.config_paths import get_library_root
    monkeypatch.delenv("MATHPDF_LOOKUP_CACHE")
    monkeypatch.setenv("HOME", str(tmp_path / "h"))
    p = lc.cache_path()
    assert p == tmp_path / "h" / ".mathpdf" / "cache" / "lookups.json"
    lib = get_library_root().resolve()
    assert lib not in p.resolve().parents


def test_unreachable_is_bounded_in_time():
    lc.mark_unreachable("arxiv", "no connection", now=1000.0)
    assert "no connection" in lc.unreachable("arxiv", now=1000.0 + lc.UNREACHABLE_FOR - 1)
    assert lc.unreachable("arxiv", now=1000.0 + lc.UNREACHABLE_FOR) is None
    assert lc.unreachable("arxiv", now=1000.0 + 1) is None, "expiry must forget it"


def test_forget_unreachable_asks_again_at_once():
    lc.mark_unreachable("arxiv", "x")
    lc.mark_unreachable("crossref", "y")
    lc.forget_unreachable("arxiv")
    assert lc.unreachable("arxiv") is None and lc.unreachable("crossref")
    lc.forget_unreachable()
    assert lc.unreachable("crossref") is None


# ---------------------------------------------------------------------------
# Crossref, same three answers
# ---------------------------------------------------------------------------

def test_crossref_404_is_absent_and_remembered(net):
    net.script.append(Resp(404))
    assert ingest.crossref_lookup("10.1/NOPE").state == lc.ABSENT
    assert ingest.crossref_lookup("10.1/nope").state == lc.ABSENT   # case-folded
    assert len(net.calls) == 1


@pytest.mark.parametrize("failure", [
    requests.exceptions.ConnectionError("x"), requests.exceptions.ReadTimeout("x"),
    Resp(503), Resp(429)], ids=["offline", "timeout", "503", "429"])
def test_crossref_failure_is_unknown_never_stored(net, failure):
    net.script.append(failure)
    a = ingest.crossref_lookup("10.1/x")
    assert a.state == lc.UNKNOWN and a.reason
    assert stored("crossref", "10.1/x") is None
    assert lc.unreachable("crossref")
    assert lc.unreachable("arxiv") is None, "Crossref trouble paused arXiv"


@pytest.mark.parametrize("reply", [Resp(400), Resp(200), Resp(200, payload={}),
                                   Resp(200, payload={"message": {"publisher": "x"}})],
                         ids=["400", "not-json", "no-message", "no-fields"])
def test_crossref_reply_that_settles_nothing(net, reply):
    net.script.append(reply)
    assert ingest.crossref_lookup("10.1/x").state == lc.UNKNOWN
    assert stored("crossref", "10.1/x") is None


def test_crossref_found_keeps_only_what_is_read(net):
    msg = {"title": ["T"], "author": [{"family": "F", "given": "G"}],
           "published-print": {"date-parts": [[2020]]}, "reference": ["huge"] * 50}
    net.script.append(Resp(200, payload={"message": msg}))
    a = ingest.crossref_lookup("10.1/x")
    assert a.found and a.record["title"] == ["T"]
    assert "reference" not in stored("crossref", "10.1/x")["rec"]


# ---------------------------------------------------------------------------
# Through the extractor: the page can tell the three apart
# ---------------------------------------------------------------------------

def _bare_pdf(tmp_path, name, title="Embedded title of the paper"):
    from tests.test_processing.test_stage0_fixes import write_pdf
    return write_pdf(tmp_path / name, title=title, author="Embedded, A.")


def test_extraction_reports_unknown_and_falls_back_to_the_pdf(net, tmp_path):
    pdf = _bare_pdf(tmp_path, "2401.00001v1.pdf")
    net.script.append(requests.exceptions.ConnectTimeout("down"))
    meta = ingest.extract_metadata_from_pdf(pdf)
    assert meta["lookups"]["arxiv"]["state"] == "unknown"
    assert meta["title_source"] == "embedded"
    assert meta["title"] == "Embedded title of the paper"


def test_extraction_reports_absent(net, tmp_path):
    pdf = _bare_pdf(tmp_path, "2401.99999v1.pdf")
    net.script.append(Resp(200, feed([], total=0)))
    meta = ingest.extract_metadata_from_pdf(pdf)
    assert meta["lookups"]["arxiv"]["state"] == "absent"
    assert meta["title_source"] == "embedded"


def test_approve_does_not_ask_again_what_the_preview_learned(net, tmp_path):
    """The cockpit extracts once to show the paper and once more on
    Approve. A remembered answer (here: no such id) costs nothing the
    second time; before, it cost a full request (10 s when unreachable)."""
    pdf = _bare_pdf(tmp_path, "2401.99999v1.pdf")
    net.script.append(Resp(200, feed([], total=0)))
    ingest.extract_metadata_from_pdf(pdf)
    ingest.extract_metadata_from_pdf(pdf)
    assert len(net.calls) == 1


def test_approve_during_an_outage_does_not_wait_again(net, tmp_path):
    pdf = _bare_pdf(tmp_path, "2401.00001v1.pdf")
    net.script.append(requests.exceptions.ConnectTimeout("down"))
    ingest.extract_metadata_from_pdf(pdf)
    meta = ingest.extract_metadata_from_pdf(pdf)
    assert len(net.calls) == 1
    assert meta["lookups"]["arxiv"]["state"] == "unknown"


# ---------------------------------------------------------------------------
# The local model
# ---------------------------------------------------------------------------

class _FakeModel:
    instances: list = []
    fail = False

    def __init__(self, model_path):
        _FakeModel.instances.append(model_path)

    def extract(self, text):
        if _FakeModel.fail:
            raise RuntimeError("model crashed")
        return {"title": f"Read: {text[:10]}", "authors": ["A B"]}

    def close(self):
        pass


@pytest.fixture
def model(tmp_path):
    _FakeModel.instances = []
    _FakeModel.fail = False
    m = tmp_path / "model.gguf"
    m.write_bytes(b"weights")
    return m


def test_the_model_reads_a_text_once(model):
    a = ingest._llm_extract_remembered(_FakeModel, model, "some first page text")
    b = ingest._llm_extract_remembered(_FakeModel, model, "some first page text")
    assert a == b == {"title": "Read: some first", "authors": ["A B"]}
    assert len(_FakeModel.instances) == 1


def test_a_different_text_is_read_afresh(model):
    ingest._llm_extract_remembered(_FakeModel, model, "text one, page one")
    ingest._llm_extract_remembered(_FakeModel, model, "text two, page one")
    assert len(_FakeModel.instances) == 2


def test_a_retrained_model_does_not_answer_from_memory(model):
    ingest._llm_extract_remembered(_FakeModel, model, "same text here")
    model.write_bytes(b"new weights, longer")
    ingest._llm_extract_remembered(_FakeModel, model, "same text here")
    assert len(_FakeModel.instances) == 2


def test_a_model_failure_is_not_remembered(model):
    _FakeModel.fail = True
    with pytest.raises(RuntimeError):
        ingest._llm_extract_remembered(_FakeModel, model, "a text")
    _FakeModel.fail = False
    assert ingest._llm_extract_remembered(_FakeModel, model, "a text")["title"]
    assert len(_FakeModel.instances) == 2


def test_a_no_title_answer_is_remembered_too(model, monkeypatch):
    """Reading 30-70 s to learn there is no title is worth remembering."""
    monkeypatch.setattr(_FakeModel, "extract",
                        lambda self, t: {"title": "", "authors": []})
    ingest._llm_extract_remembered(_FakeModel, model, "a text")
    ingest._llm_extract_remembered(_FakeModel, model, "a text")
    assert len(_FakeModel.instances) == 1


def test_while_crossref_is_unreachable_it_is_not_asked(net):
    net.script.append(requests.exceptions.ConnectTimeout("down"))
    ingest.crossref_lookup("10.1/a")
    assert ingest.crossref_lookup("10.1/b").state == lc.UNKNOWN
    assert len(net.calls) == 1


def test_extraction_reports_crossref_unknown(net, tmp_path):
    pdf = _bare_pdf(tmp_path, "10.1016_j.spa.2024.104321.pdf")
    net.script.append(requests.exceptions.ConnectionError("offline"))
    meta = ingest.extract_metadata_from_pdf(pdf)
    assert meta["lookups"]["crossref"]["state"] == "unknown"
    assert meta["lookups"]["crossref"]["reason"] == "no connection"
    assert meta["title_source"] == "embedded"


def test_extraction_asks_the_model_once_per_paper(monkeypatch, tmp_path, model):
    """Through the real extractor: show, then Approve, reads the paper once.
    Measured before: 28-72 s to show, 29-43 s again to approve."""
    import pdf_processing.llm_extractor as llm_mod
    from tests.test_processing.test_corroboration_and_registry import pdf_with_body

    class Fake(_FakeModel):
        @staticmethod
        def local_model_path():
            return model

        @staticmethod
        def is_available():
            return True

    monkeypatch.setattr(llm_mod, "LLMMetadataExtractor", Fake)
    body = ("On the regularity of something rather long. " * 8).strip()
    pdf = pdf_with_body(tmp_path / "scan_0042.pdf", title="", author="",
                        body=body)
    first = ingest.extract_metadata_from_pdf(pdf)
    second = ingest.extract_metadata_from_pdf(pdf)
    assert first["title_source"] == second["title_source"] == "llm"
    assert first["title"] == second["title"]
    assert len(_FakeModel.instances) == 1


# ---------------------------------------------------------------------------
# Which files name which ids (one pattern, shared by bulk sort and the page)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, expected", [
    ("2401.07160v3.pdf", ["2401.07160v3"]),
    ("1405.1234.pdf", ["1405.1234"]),               # before 2015: 4 digits
    ("1405.1234v12.pdf", ["1405.1234v12"]),
    ("arXiv-2105.10623.pdf", ["2105.10623"]),
    ("math.PR_0501001v2.pdf", ["math.PR/0501001v2"]),   # "/" stored as "_"
    ("Smith, J. - A properly named paper.pdf", []),
    ("Smith, J. - Remarks on 2401.12345.pdf", []),     # a title, not an id
    ("10.1016_j.spa.2024.104321.pdf", []),             # a DOI, not an id
])
def test_arxiv_ids_in_names(name, expected):
    from pathlib import Path
    assert ingest.arxiv_ids_in_names([Path("/x") / name]) == expected
