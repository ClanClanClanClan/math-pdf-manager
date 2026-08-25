"""A running daemon watching a deleted folder must not report "ON".

THE OUTAGE THIS ENCODES. On 19 Aug 2026 the watcher started, logged
"Watching /Users/.../Downloads/MathInbox for new PDFs...", and ran for
five days and twenty-one hours. At some point the folder was removed.
macOS does not tear down the watch when that happens -- the kqueue just
never fires again -- so the process stayed up, launchctl kept reporting
state = running, and the sidebar kept rendering

    Automatic filing: ON  (running as process 6282)

while the Settings page told the owner a downloaded PDF "is filed into
your library automatically from there". Every word of that was false.

The defect is not the missing folder. It is that ``watcher_status``
answered a question nobody asked -- "is a process alive?" -- and the
badge presented the answer to a different question: "are my PDFs being
filed?". "I didn't look" and "it's fine" came back as the same value.
"""
import pytest

from ui.cockpit_actions import watcher_status, start_watcher


@pytest.fixture
def inbox(tmp_path, monkeypatch):
    """Point WatcherConfig.load() at a temp inbox we control."""
    box = tmp_path / "MathInbox"
    box.mkdir()

    class _Cfg:
        inbox_dir = box

    import ui.cockpit_actions as actions
    import watcher.config as wconfig
    monkeypatch.setattr(wconfig.WatcherConfig, "load", staticmethod(lambda: _Cfg()))
    return box


def _alive(monkeypatch, running=True, pid=6282):
    """Force the launchctl layer to report a live process."""
    import ui.cockpit_actions as actions

    class _Proc:
        returncode = 0
        stdout = f"\tstate = {'running' if running else 'not running'}\n\tpid = {pid}\n"
        stderr = ""

    monkeypatch.setattr(actions, "_launchctl", lambda *a, **k: _Proc())


def test_alive_with_a_live_folder_is_filing(inbox, monkeypatch):
    _alive(monkeypatch)
    s = watcher_status()
    assert s["running"] is True
    assert s["filing"] is True
    assert s["problem"] is None


def test_alive_with_a_deleted_folder_is_not_filing(inbox, monkeypatch):
    """THE REGRESSION. This is the exact five-day state."""
    _alive(monkeypatch)
    inbox.rmdir()
    s = watcher_status()
    assert s["running"] is True, "the process really is up"
    assert s["filing"] is False, "but nothing is being filed"
    assert s["problem"] and "no longer exists" in s["problem"]
    assert str(inbox) in s["problem"], "must name the folder, not just complain"


def test_a_file_where_the_folder_should_be_is_not_a_folder(inbox, monkeypatch):
    """is_dir(), not exists() -- a regular file is not an inbox."""
    _alive(monkeypatch)
    inbox.rmdir()
    inbox.write_text("not a folder")
    s = watcher_status()
    assert s["filing"] is False


def test_a_dead_process_is_never_filing(inbox, monkeypatch):
    _alive(monkeypatch, running=False)
    s = watcher_status()
    assert s["running"] is False
    assert s["filing"] is False
    assert s["problem"] is None, "off on purpose is not a fault to report"


def test_filing_is_never_true_without_running(inbox, monkeypatch):
    """The property, over both axes: filing implies running."""
    for alive in (True, False):
        for folder in (True, False):
            if folder and not inbox.exists():
                inbox.mkdir()
            if not folder and inbox.exists():
                inbox.rmdir()
            _alive(monkeypatch, running=alive)
            s = watcher_status()
            assert not (s["filing"] and not s["running"])
            assert s["filing"] == (alive and folder)


def test_every_return_path_carries_the_folder_verdict(inbox, monkeypatch):
    """All four exits, including the launchctl-list fallback and 'not loaded'.

    The first version of this fix patched one exit of four. A status
    dict missing the key reads as False at the call site, which is the
    silent-failure shape all over again -- so assert the key EXISTS.
    """
    import ui.cockpit_actions as actions

    class _Fail:
        returncode = 1
        stdout = ""
        stderr = "Could not find service"

    class _ListHit:
        returncode = 1
        stdout = ""
        stderr = "boom"

    # exit 1: `print` fails, `list` has the label
    calls = {"n": 0}

    def _two_step(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return _ListHit()

        class _L:
            returncode = 0
            stdout = f"6282\t0\t{actions.WATCHER_LABEL}\n"
            stderr = ""
        return _L()

    monkeypatch.setattr(actions, "_launchctl", _two_step)
    s = watcher_status()
    assert "filing" in s and s["filing"] is True

    # exit 2: `print` fails and the label is absent -> not loaded
    monkeypatch.setattr(actions, "_launchctl", lambda *a, **k: _Fail())
    s = watcher_status()
    assert "filing" in s and s["filing"] is False


def test_status_never_raises_when_the_config_is_unreadable(monkeypatch):
    """An unreadable config must degrade to "not filing", not to a crash.

    A traceback in the sidebar takes the whole cockpit down; and a
    swallowed exception that returned filing=True would be the original
    bug wearing a different hat.
    """
    import watcher.config as wconfig
    import ui.cockpit_actions as actions

    def _boom():
        raise OSError("config is shredded")

    monkeypatch.setattr(wconfig.WatcherConfig, "load", staticmethod(_boom))
    _alive(monkeypatch)
    s = watcher_status()
    assert s["filing"] is False
    assert "cannot tell where the inbox is" in s["problem"]


def test_starting_the_watcher_rebuilds_a_missing_inbox(inbox, monkeypatch):
    """The sidebar promises off-and-on rebuilds the folder. Keep the promise.

    Without this, the recovery the error message recommends produces a
    second running-and-deaf daemon, and the owner has been told the
    problem is fixed.
    """
    import ui.cockpit_actions as actions
    inbox.rmdir()
    assert not inbox.exists()

    monkeypatch.setattr(actions.Path, "home", staticmethod(lambda: inbox.parent))
    (inbox.parent / "Library" / "LaunchAgents").mkdir(parents=True)
    (inbox.parent / "Library" / "LaunchAgents"
     / f"{actions.WATCHER_LABEL}.plist").write_text("<plist/>")

    class _OK:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(actions, "_launchctl", lambda *a, **k: _OK())
    ok, _ = start_watcher()
    assert ok
    assert inbox.is_dir(), "start must recreate the folder it is about to watch"


@pytest.mark.parametrize("state,expected", [
    ("running", True),
    ("not running", False),
    ("waiting", False),
    ("exited", False),
])
def test_the_state_line_is_parsed_by_value_not_by_substring(
    inbox, monkeypatch, state, expected
):
    """"state = not running" contains the word "running".

    The parser asked ``"running" in line``, so a loaded-but-stopped
    service came back running=True. Found by the property test above
    rather than by reading the code: the two-axis sweep asserted
    filing == (alive and folder) and the "not alive" half never held.
    """
    import ui.cockpit_actions as actions

    class _Proc:
        returncode = 0
        stdout = f"\tstate = {state}\n\tpid = 6282\n"
        stderr = ""

    monkeypatch.setattr(actions, "_launchctl", lambda *a, **k: _Proc())
    assert watcher_status()["running"] is expected
