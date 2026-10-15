"""The Sort Queue reads the next papers while the owner looks at this one.

MEASURED 2026-10-15 on the real inbox: 68 of 2,414 waiting papers always
reach the local AI model (216 when arXiv is down), and a read took
7.0-68.3 s with the model already loaded. ``processing.read_ahead`` reads
the next 25 on a background thread; ``processing.local_model`` makes sure
only one model is ever loaded and that a paper is never read twice.

The model here is a stand-in that records how it was used: how many
copies were alive at once, how many reads ran at once, and every text it
read. A gate lets a test hold a read "in progress" for as long as it
needs to make the race it is testing actually happen.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as hst

from processing import ingest, local_model, read_ahead
from processing import lookup_cache as lc


def wait_until(cond, timeout=10.0, what="condition"):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return
        time.sleep(0.005)
    raise AssertionError(f"timed out waiting for {what}")


class Model:
    """The local model, as far as anything outside it can tell."""

    guard = threading.Lock()
    live = 0
    max_live = 0
    reading = 0
    max_reading = 0
    loads = 0
    texts: list = []
    gate: threading.Event = threading.Event()
    in_read = threading.Event()
    on_read = None
    closed_mid_read = False
    model_file: Path = Path("/nonexistent")

    @classmethod
    def reset(cls, model_file):
        cls.live = cls.max_live = cls.reading = cls.max_reading = 0
        cls.loads = 0
        cls.texts = []
        cls.gate = threading.Event()
        cls.gate.set()
        cls.in_read = threading.Event()
        cls.on_read = None
        cls.closed_mid_read = False
        cls.model_file = model_file

    def __init__(self, model_path):
        with Model.guard:
            Model.live += 1
            Model.loads += 1
            Model.max_live = max(Model.max_live, Model.live)
        self.busy = False

    def extract(self, text):
        with Model.guard:
            Model.reading += 1
            Model.max_reading = max(Model.max_reading, Model.reading)
            Model.texts.append(text)
        self.busy = True
        try:
            Model.in_read.set()
            if Model.on_read is not None:
                Model.on_read(text)
            assert Model.gate.wait(10), "a test forgot to open the gate"
            if "BREAK" in text:
                raise RuntimeError("the model fell over")
            return {"title": "Read: " + text.split()[0], "authors": ["A B"]}
        finally:
            self.busy = False
            with Model.guard:
                Model.reading -= 1

    def close(self):
        if self.busy:
            Model.closed_mid_read = True
        with Model.guard:
            Model.live -= 1

    @staticmethod
    def local_model_path():
        return Model.model_file

    @staticmethod
    def is_available():
        return True


@pytest.fixture
def model(tmp_path, monkeypatch):
    import pdf_processing.llm_extractor as llm_mod

    f = tmp_path / "model.gguf"
    f.write_bytes(b"weights")
    Model.reset(f)
    monkeypatch.setattr(llm_mod, "LLMMetadataExtractor", Model)
    monkeypatch.setenv("MATHPDF_READ_AHEAD", "1")
    yield Model
    Model.gate.set()


def paper(folder: Path, name: str, word: str) -> Path:
    """A PDF with no title anywhere, so only the model can name it."""
    from tests.test_processing.test_corroboration_and_registry import pdf_with_body

    body = (f"{word} studies something at some length. " * 8).strip()
    return pdf_with_body(folder / name, title="", author="", body=body)


def papers(tmp_path, n):
    d = tmp_path / "inbox"
    return [paper(d, f"scan_{i:03d}.pdf", f"Word{i}") for i in range(n)]


def read_words():
    return [t.split()[0] for t in Model.texts]


def join_thread(timeout=10):
    t = read_ahead._thread
    if t is not None:
        t.join(timeout)
        assert not t.is_alive()


# ---------------------------------------------------------------------------
# One model at a time
# ---------------------------------------------------------------------------

def test_outside_a_kept_block_every_read_loads_and_lets_go(model):
    local_model.read(Model, model.model_file, "one text")
    local_model.read(Model, model.model_file, "two text")
    assert Model.loads == 2
    assert Model.live == 0
    assert not local_model.is_loaded()


def test_inside_a_kept_block_the_model_is_loaded_once(model):
    with local_model.kept_loaded():
        for w in ("one", "two", "three"):
            local_model.read(Model, model.model_file, w + " text")
        assert local_model.is_loaded()
    assert Model.loads == 1
    assert Model.live == 0, "the model must be let go when the block ends"


def test_a_retrained_model_is_loaded_afresh_even_when_kept(model):
    with local_model.kept_loaded():
        local_model.read(Model, model.model_file, "one text")
        model.model_file.write_bytes(b"retrained weights, longer")
        local_model.read(Model, model.model_file, "one text")
        assert Model.live == 1, "the old copy must go before the new one loads"
    assert Model.loads == 2


def test_a_failed_read_lets_the_model_go_even_when_kept(model):
    with local_model.kept_loaded():
        with pytest.raises(RuntimeError):
            local_model.read(Model, model.model_file, "BREAK here")
        assert not local_model.is_loaded()
        local_model.read(Model, model.model_file, "fine text")
    assert Model.loads == 2


def test_ending_the_block_waits_for_a_read_in_progress(model):
    Model.gate.clear()
    reader = threading.Thread(
        target=local_model.read, args=(Model, model.model_file, "slow text"))
    ended = threading.Event()

    def keeper():
        with local_model.kept_loaded():
            reader.start()
            assert Model.in_read.wait(10)
        ended.set()

    k = threading.Thread(target=keeper)
    k.start()
    assert Model.in_read.wait(10)
    time.sleep(0.05)
    assert not ended.is_set(), "the block ended while the model was reading"
    Model.gate.set()
    k.join(10)
    reader.join(10)
    assert ended.is_set()
    assert not Model.closed_mid_read
    assert Model.live == 0


@settings(max_examples=30, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(plan=hst.lists(
    hst.tuples(hst.sampled_from(["alpha", "beta", "gamma", "delta"]),
               hst.booleans()),
    min_size=2, max_size=8))
def test_any_mix_of_readers_loads_one_model_and_reads_each_text_once(
        model, tmp_path, plan):
    """Property: whatever threads ask, in whatever order, with or without
    a kept block open, there is never a second model alive, never two
    reads at once, and a text is read by the model once."""
    Model.reset(model.model_file)
    lc._LOADED.clear()
    os.environ["MATHPDF_LOOKUP_CACHE"] = str(
        tmp_path / f"lookups-{time.monotonic_ns()}.json")
    start = threading.Barrier(len(plan))
    errors = []

    def go(word, keep):
        try:
            start.wait(10)
            if keep:
                with local_model.kept_loaded():
                    ingest._llm_extract_remembered(
                        Model, model.model_file, word + " text")
            else:
                ingest._llm_extract_remembered(
                    Model, model.model_file, word + " text")
        except Exception as exc:          # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=go, args=p) for p in plan]
    for t in threads:
        t.start()
    for t in threads:
        t.join(20)
    assert not errors
    assert Model.max_live <= 1
    assert Model.max_reading <= 1
    assert sorted(read_words()) == sorted({w for w, _ in plan})
    assert Model.live == 0 and not local_model.is_loaded()


# ---------------------------------------------------------------------------
# Reading ahead
# ---------------------------------------------------------------------------

def test_want_returns_at_once_while_the_model_reads(model, tmp_path):
    ps = papers(tmp_path, 3)
    Model.gate.clear()
    read_ahead.want(ps)
    assert Model.in_read.wait(10)
    for call in (lambda: read_ahead.want(ps), read_ahead.status,
                 lambda: read_ahead.want(ps[1:])):
        t0 = time.perf_counter()
        call()
        assert time.perf_counter() - t0 < 0.05, "the page waited for the model"
    assert read_ahead.status()["model_reading"]
    Model.gate.set()


def test_papers_are_read_in_order_and_the_page_then_reads_nothing(
        model, tmp_path):
    ps = papers(tmp_path, 4)
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 4, what="4 papers read")
    assert read_words() == ["Word0", "Word1", "Word2", "Word3"]
    assert Model.loads == 1, "kept loaded between papers"
    for i, p in enumerate(ps):
        meta = ingest.extract_metadata_from_pdf(p)
        assert meta["title_source"] == "llm"
        assert meta["title"] == f"Read: Word{i}"
    assert len(Model.texts) == 4, "the page read a paper again"


def test_the_page_waits_for_the_paper_being_read_instead_of_reading_it_again(
        model, tmp_path):
    ps = papers(tmp_path, 2)
    Model.gate.clear()
    read_ahead.want(ps)
    assert Model.in_read.wait(10)
    got = {}
    page = threading.Thread(
        target=lambda: got.setdefault("m", ingest.extract_metadata_from_pdf(ps[0])))
    page.start()
    time.sleep(0.1)
    assert page.is_alive(), "the page went ahead without the answer"
    Model.gate.set()
    page.join(10)
    assert got["m"]["title"] == "Read: Word0"
    assert read_words().count("Word0") == 1
    assert Model.max_live == 1


@pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnhandledThreadExceptionWarning")   # the death itself
def test_a_dying_thread_is_replaced_and_lets_the_model_go(
        model, tmp_path, monkeypatch):
    ps = papers(tmp_path, 3)
    real = read_ahead._read
    calls = []

    class Killed(BaseException):
        pass

    def dies_on_the_first(path):
        calls.append(path.name)
        if path == ps[0]:
            raise Killed("the thread is gone")
        return real(path)

    monkeypatch.setattr(read_ahead, "_read", dies_on_the_first)
    read_ahead.want(ps)
    wait_until(lambda: read_ahead._thread is None, what="the thread to die")
    assert not read_ahead.status()["running"]
    assert local_model._keepers == 0 and not local_model.is_loaded()
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 3, what="the rest read")
    assert calls.count(ps[0].name) == 1, "the paper that killed it was retried"
    assert read_words() == ["Word1", "Word2"]


def test_a_dead_thread_left_behind_does_not_block_a_restart(model, tmp_path):
    ps = papers(tmp_path, 1)
    dead = threading.Thread(target=lambda: None)
    dead.start()
    dead.join()
    read_ahead._thread = dead
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 1, what="the paper read")
    assert read_words() == ["Word0"]


def test_a_paper_that_vanishes_mid_read_is_passed_over(model, tmp_path):
    ps = papers(tmp_path, 3)

    def vanish(text):
        if text.split()[0] == "Word0":
            ps[0].unlink()
    Model.on_read = vanish
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 2, what="the rest read")
    assert not ps[0].exists()
    assert read_ahead.status()["running"], "the thread died with the file"
    assert read_words() == ["Word0", "Word1", "Word2"]
    read_ahead.want(ps)                      # the page renders again
    time.sleep(0.1)
    assert read_words() == ["Word0", "Word1", "Word2"], "re-read after vanishing"


def test_a_paper_gone_before_its_turn_is_not_even_opened(
        model, tmp_path, monkeypatch):
    ps = papers(tmp_path, 3)
    ps[1].unlink()
    opened = []
    real = read_ahead._read
    monkeypatch.setattr(read_ahead, "_read",
                        lambda p: (opened.append(p.name), real(p))[1])
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 2, what="two read")
    assert read_words() == ["Word0", "Word2"]
    assert opened == [ps[0].name, ps[2].name]


def test_a_failing_paper_is_not_retried_in_a_loop(model, tmp_path, monkeypatch):
    ps = papers(tmp_path, 2)
    tries = []

    def broken(path):
        tries.append(path.name)
        if path == ps[0]:
            raise OSError("unreadable")
        return {"title": "fine", "title_source": "embedded"}

    monkeypatch.setattr(ingest, "extract_metadata_from_pdf", broken)
    read_ahead.want(ps)
    first = read_ahead._thread
    wait_until(lambda: read_ahead.status()["ready"] == 2, what="both settled")
    assert read_ahead._thread is first and first.is_alive(), (
        "one unreadable paper took the thread down")
    for _ in range(4):
        read_ahead.want(ps)
        time.sleep(0.02)
    assert tries == [ps[0].name, ps[1].name]
    assert read_ahead._finished[read_ahead._identity(ps[0])].startswith("failed")


def test_racing_wants_start_one_thread(model, tmp_path, monkeypatch):
    ps = papers(tmp_path, 2)
    Model.gate.clear()
    inside, most = [0], [0]
    real = read_ahead._work
    count = threading.Lock()

    def counted():
        with count:
            inside[0] += 1
            most[0] = max(most[0], inside[0])
        try:
            real()
        finally:
            with count:
                inside[0] -= 1

    monkeypatch.setattr(read_ahead, "_work", counted)
    n = 16
    start = threading.Barrier(n)

    def rerun():
        start.wait(10)
        read_ahead.want(ps)

    threads = [threading.Thread(target=rerun) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    alive = [t for t in threading.enumerate() if t.name == "sort-queue-read-ahead"]
    assert len(alive) == 1
    Model.gate.set()
    wait_until(lambda: read_ahead.status()["ready"] == 2, what="both read")
    assert most[0] == 1
    assert read_words() == ["Word0", "Word1"]


def test_stop_finishes_the_paper_in_hand_and_starts_nothing_more(
        model, tmp_path):
    ps = papers(tmp_path, 3)
    Model.gate.clear()
    read_ahead.want(ps)
    assert Model.in_read.wait(10)
    read_ahead.stop()
    Model.gate.set()
    join_thread()
    assert read_words() == ["Word0"]
    assert not Model.closed_mid_read
    assert Model.live == 0 and not local_model.is_loaded(), "model kept after stop"
    assert lc.get("llm", ingest._llm_key(model.model_file, Model.texts[0])), (
        "the paper in hand was finished and remembered")


def test_want_after_stop_keeps_the_finishing_thread(model, tmp_path):
    ps = papers(tmp_path, 3)
    Model.gate.clear()
    read_ahead.want(ps)
    assert Model.in_read.wait(10)
    first = read_ahead._thread
    read_ahead.stop()
    read_ahead.want(ps)
    assert read_ahead._thread is first
    Model.gate.set()
    wait_until(lambda: read_ahead.status()["ready"] == 3, what="all read")
    assert read_words() == ["Word0", "Word1", "Word2"]
    assert Model.loads == 1


def test_an_idle_thread_lets_the_model_go(model, tmp_path, monkeypatch):
    monkeypatch.setattr(read_ahead, "IDLE_FOR", 0.2)
    ps = papers(tmp_path, 1)
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 1, what="read")
    wait_until(lambda: read_ahead._thread is None, what="the idle thread to end")
    assert not local_model.is_loaded()


def test_a_paper_that_changes_is_read_again(model, tmp_path):
    ps = papers(tmp_path, 1)
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 1, what="read")
    paper(ps[0].parent, ps[0].name, "Changed")
    st = ps[0].stat()
    os.utime(ps[0], ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 1 and len(Model.texts) == 2,
               what="re-read")
    assert read_words() == ["Word0", "Changed"]


def test_switched_off_by_the_environment(model, tmp_path, monkeypatch):
    monkeypatch.setenv("MATHPDF_READ_AHEAD", "0")
    read_ahead.want(papers(tmp_path, 2))
    assert read_ahead._thread is None
    assert Model.texts == []


def test_it_writes_nothing_beside_the_papers(model, tmp_path):
    ps = papers(tmp_path, 3)
    folder = ps[0].parent
    before = {p.name: (p.stat().st_mtime_ns, p.stat().st_size)
              for p in folder.iterdir()}
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 3, what="read")
    after = {p.name: (p.stat().st_mtime_ns, p.stat().st_size)
             for p in folder.iterdir()}
    assert after == before


def test_stop_while_idle_lets_the_model_go_at_once(model, tmp_path):
    """IDLE_FOR is two minutes; leaving the page must not wait it out."""
    ps = papers(tmp_path, 1)
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 1, what="read")
    assert local_model.is_loaded(), "kept loaded while waiting for more"
    t0 = time.perf_counter()
    read_ahead.stop()
    join_thread(timeout=5)
    assert time.perf_counter() - t0 < 2
    assert not local_model.is_loaded()


def test_coming_back_to_the_page_reads_ahead_as_before(model, tmp_path):
    """Leave, come back: the thread waits for the next papers with the
    model loaded, rather than quitting after each window."""
    ps = papers(tmp_path, 3)
    Model.gate.clear()
    read_ahead.want(ps[:1])
    assert Model.in_read.wait(10)
    read_ahead.stop()
    read_ahead.want(ps[:2])
    Model.gate.set()
    wait_until(lambda: read_ahead.status()["ready"] == 2, what="two read")
    time.sleep(0.1)
    assert read_ahead.status()["running"], "it quit as if he had left"
    assert local_model.is_loaded()
    read_ahead.want(ps)
    wait_until(lambda: read_ahead.status()["ready"] == 3, what="three read")
    assert Model.loads == 1


def test_an_unreadable_file_is_recorded_as_not_read(model, tmp_path):
    bad = tmp_path / "inbox" / "not_really.pdf"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_bytes(b"<html>a login page saved as .pdf</html>")
    read_ahead.want([bad])
    wait_until(lambda: read_ahead.status()["ready"] == 1, what="settled")
    assert read_ahead._finished[read_ahead._identity(bad)] == (
        "failed: not a PDF (missing magic bytes)")
    assert Model.texts == []


def test_papers_handed_over_while_it_looks_are_not_missed(
        model, tmp_path, monkeypatch):
    """The page can hand over new papers in the instant between the
    thread finding nothing to do and its going to sleep. IDLE_FOR is two
    minutes: missing that hand-over would leave them unread that long."""
    ps = papers(tmp_path, 2)
    real = read_ahead._next
    handed = []

    def racing_next():
        got = real()
        if got[0] is None and not handed:
            handed.append(1)
            read_ahead.want(ps[1:])          # the page, just now
        return got

    monkeypatch.setattr(read_ahead, "_next", racing_next)
    read_ahead.want(ps[:1])
    wait_until(lambda: "Word1" in read_words(), timeout=5,
               what="the paper handed over mid-look")
    assert handed, "the race was not staged"
    assert read_words() == ["Word0", "Word1"]


def test_a_thread_on_its_way_out_does_not_swallow_new_papers(
        model, tmp_path):
    """Leaving lets the model go, which waits for the turn; if he comes
    back during that wait, the papers must still be read."""
    ps = papers(tmp_path, 2)
    read_ahead.want(ps[:1])
    wait_until(lambda: read_ahead.status()["ready"] == 1, what="first read")
    old = read_ahead._thread
    with local_model.TURN:                    # the page is mid-read
        read_ahead.stop()
        wait_until(lambda: read_ahead._thread is not old, timeout=5,
                   what="the old thread to step aside")
        assert old.is_alive(), "it was meant to be waiting for the turn"
        read_ahead.want(ps)                   # he came back
    wait_until(lambda: "Word1" in read_words(), timeout=5,
               what="the new paper read")
    old.join(5)


def test_nothing_to_read_ahead_starts_nothing(model):
    """On the last paper the window is empty. A thread started anyway
    would hold the model loaded for IDLE_FOR with nothing to do."""
    read_ahead.want([])
    assert read_ahead._thread is None
