"""Test configuration — and the containment wall around the real world.

Two things live here:

1. ``sys.path`` setup so ``src/`` imports resolve (historic).

2. A CONTAINMENT WALL.  The suite has been writing into the owner's
   real HOME: 477 rows in ``~/.mathpdf/cockpit_activity.jsonl``, 342 of
   them ``conflict.bulk_keep_canonical`` produced by tests, and the last
   100 rows — exactly the window the cockpit Activity page renders — are
   100% test junk.  The owner opens his UI and sees our noise.

   The old autouse fixture below pointed ``MATH_LIBRARY`` at a tmp dir
   *per test*, which is too late for five modules
   (``processing.ingest``, ``processing.bulk_sort``,
   ``processing.upgrade_to_published``, ``processing.paper_transition``,
   ``maintenance.weekly_report``) that evaluate::

       LIBRARY_ROOT = _get_library_root()

   at IMPORT time.  Import happens during collection, before any
   function-scoped fixture runs, so those constants froze onto the real
   Dropbox library.  Nothing wrote there today; that was luck, not
   design.

   So the wall has three courses of bricks, all laid at conftest IMPORT
   time — the earliest moment pytest gives us, before a single test
   module is imported:

     a. ``MATH_LIBRARY`` is exported to a session-scoped temp library, so
        import-time constants freeze onto a throwaway path.
     b. ``HOME`` (and the XDG dirs) are redirected to a session-scoped
        temp home, so ``Path.home() / ".mathpdf"`` — bound at import time
        in ``watcher.config``, ``ui.attention_queue`` and
        ``ui.cockpit_actions`` — lands in the sandbox.
     c. A write guard wraps the filesystem mutators (``open``,
        ``io.open``, ``os.open`` and the ``os`` rename/unlink/mkdir
        family) and raises :class:`RealWorldWriteBlocked` on any write
        under the real library or the real ``~/.mathpdf``.  (b) makes
        stray writes land elsewhere; (c) makes them *impossible* even
        when a module hardcodes an absolute path or a test un-redirects
        HOME itself.

   The guard is prefix comparison on an already-materialised string: two
   ``str.startswith`` calls in the common case.  It runs on every open in
   a 2,109-test suite and costs microseconds.

The checkout itself lives *inside* the library root
(``…/Work/Maths/Scripts``), so that subtree is explicitly exempt —
otherwise pytest could not write its own cache.
"""
from __future__ import annotations

import atexit
import builtins
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# --------------------------------------------------------------------------
# sys.path
# --------------------------------------------------------------------------
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# --------------------------------------------------------------------------
# The real world, captured BEFORE anything is redirected
# --------------------------------------------------------------------------
def _real_home() -> Path:
    """The owner's actual home, read from the password database.

    Deliberately not ``Path.home()``: that reads ``$HOME``, which this
    module is about to rewrite, and which an outer runner may already
    have rewritten.  ``pwd`` cannot be fooled by an environment.
    """
    try:
        import pwd
        return Path(pwd.getpwuid(os.getuid()).pw_dir)
    except Exception:                                   # pragma: no cover
        return Path(os.environ.get("HOME", "/")).resolve()


REAL_HOME = _real_home()

# Every spelling of the real library we can name without guessing.
# ``constants`` is the single source of truth; the two literal forms are
# belt-and-braces in case constants ever stops resolving.
_REAL_LIBRARIES: list[Path] = [
    REAL_HOME / "Library" / "CloudStorage" / "Dropbox" / "Work" / "Maths",
    REAL_HOME / "Dropbox" / "Work" / "Maths",
]
try:                                                    # pragma: no branch
    from constants import DEFAULT_LIBRARY_ROOT as _DEFAULT_LIB
    _REAL_LIBRARIES.insert(0, Path(_DEFAULT_LIB))
except Exception:                                       # pragma: no cover
    pass

REAL_LIBRARY = _REAL_LIBRARIES[0]
REAL_DOTDIR = REAL_HOME / ".mathpdf"

#: Writes under these prefixes abort the test.
PROTECTED: tuple[Path, ...] = tuple(
    dict.fromkeys([*_REAL_LIBRARIES, REAL_DOTDIR])
)

#: …except under these, which are the source checkout (it lives inside
#: the library root) and pytest's own scratch space.
EXEMPT: tuple[Path, ...] = tuple(
    dict.fromkeys(
        [project_root.resolve(), *[lib / "Scripts" for lib in _REAL_LIBRARIES]]
    )
)


class RealWorldWriteBlocked(RuntimeError):
    """A test tried to write to the owner's real library or ``~/.mathpdf``.

    This is never a flake and never a fixture problem: some code under
    test resolved a production path instead of the sandbox.  Fix the
    path, do not weaken the guard.
    """


def _sep(p: Path) -> str:
    s = str(p)
    return (s if s.endswith(os.sep) else s + os.sep).casefold()


_PROTECTED_PREFIXES: tuple[str, ...] = tuple(_sep(p) for p in PROTECTED)
_EXEMPT_PREFIXES: tuple[str, ...] = tuple(_sep(p) for p in EXEMPT)


def offending_path(target) -> str | None:
    """Return the path as a string if writing to it is forbidden, else None.

    APFS folds case, so the comparison is casefolded (see the
    case-insensitive-filesystem lesson: never compare these paths
    case-sensitively).
    """
    if isinstance(target, int):          # fd — os.truncate(fd, n) & friends
        return None
    try:
        s = os.fspath(target)
    except TypeError:
        return None
    if isinstance(s, bytes):
        s = os.fsdecode(s)
    elif not isinstance(s, str):         # pragma: no cover - defensive
        return None
    if not s.startswith(os.sep):
        s = os.path.abspath(s)
    low = s.casefold()

    def _under(path: str, prefix_with_sep: str) -> bool:
        """True for the directory ITSELF as well as anything inside it.

        The prefixes carry a trailing separator, so a bare
        ``…/Scripts`` — which is what ``os.mkdir`` passes when
        coverage.py creates its data directory — matched "protected"
        (it is inside the library) and MISSED "exempt" (no trailing
        slash). The guard then aborted the run with INTERNALERROR and
        no coverage was ever produced, which silently disabled the
        ratchet: the gate could not measure what it was gating.
        """
        return path == prefix_with_sep[:-1] or path.startswith(prefix_with_sep)

    for prefix in _PROTECTED_PREFIXES:
        if _under(low, prefix):
            for ok in _EXEMPT_PREFIXES:
                if _under(low, ok):
                    return None
            return s
    return None


def _refuse(path: str, how: str) -> None:
    raise RealWorldWriteBlocked(
        f"blocked {how} on the owner's real data: {path}\n"
        f"  protected: {', '.join(str(p) for p in PROTECTED)}\n"
        "  A test must never write outside its tmp_path sandbox. If a "
        "module resolved this path, it read a production constant "
        "instead of MATH_LIBRARY / $HOME."
    )


_WRITE_FLAGS = (
    os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
)

_ORIGINALS: dict = {}
_INSTALLED = False


def _install_write_guard() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    real_open = builtins.open
    real_os_open = os.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if ("r" not in mode) or ("+" in mode):
            bad = offending_path(file)
            if bad is not None:
                _refuse(bad, f"open(mode={mode!r})")
        return real_open(file, mode, *args, **kwargs)

    def guarded_os_open(path, flags, *args, **kwargs):
        if flags & _WRITE_FLAGS:
            bad = offending_path(path)
            if bad is not None:
                _refuse(bad, "os.open")
        return real_os_open(path, flags, *args, **kwargs)

    _ORIGINALS["builtins.open"] = real_open
    _ORIGINALS["io.open"] = io.open
    _ORIGINALS["os.open"] = real_os_open
    builtins.open = guarded_open
    io.open = guarded_open
    os.open = guarded_os_open

    # pathlib routes unlink/rename/replace/mkdir/rmdir straight at these,
    # and shutil.move/rmtree route through them too, so wrapping the os
    # layer covers Path.* without wrapping pathlib itself.
    def _wrap_os(name: str, *, arg_indices=(0,)):
        original = getattr(os, name, None)
        if original is None:                            # pragma: no cover
            return
        _ORIGINALS[f"os.{name}"] = original

        def guarded(*args, **kwargs):
            for i in arg_indices:
                if i < len(args):
                    bad = offending_path(args[i])
                    if bad is not None:
                        _refuse(bad, f"os.{name}")
            return original(*args, **kwargs)

        guarded.__name__ = name
        setattr(os, name, guarded)

    for _name in ("remove", "unlink", "rmdir", "removedirs", "mkdir",
                  "makedirs", "truncate", "chmod", "utime"):
        _wrap_os(_name)
    for _name in ("rename", "replace", "renames", "link", "symlink"):
        # both source and destination matter: a move OUT of the library
        # destroys the owner's file just as surely as a write INTO it.
        _wrap_os(_name, arg_indices=(0, 1))

    _INSTALLED = True


def _uninstall_write_guard() -> None:                   # pragma: no cover
    global _INSTALLED
    if not _INSTALLED:
        return
    builtins.open = _ORIGINALS["builtins.open"]
    io.open = _ORIGINALS["io.open"]
    for key, original in _ORIGINALS.items():
        if key.startswith("os."):
            setattr(os, key[3:], original)
    _INSTALLED = False


# --------------------------------------------------------------------------
# The OS KEYCHAIN is not a filesystem write, so the guard above cannot see
# it.  `secure_credential_manager._load_or_create_key` calls
# `keyring.set_password(..., "credential-store-fernet-key", ...)`, reached
# from auth.manager, downloader.browser_session and core.config.
# secure_config.  On a Mac with no unlocked login keychain in the session,
# every such call raises a MODAL DIALOG — and a test run makes that call
# repeatedly.  Six concurrent agents running the suite produced a
# non-stop stream of "A keychain cannot be found to store
# credential-store-fernet-key", which locked the owner out of his machine
# until the runs were killed.
#
# An in-memory backend, installed before any test module is imported,
# makes reaching the real Keychain impossible rather than unlikely.
# --------------------------------------------------------------------------
def _install_memory_keyring() -> None:
    try:
        import keyring
        from keyring.backend import KeyringBackend
    except Exception:                               # pragma: no cover
        return                                      # keyring not installed

    class _MemoryKeyring(KeyringBackend):
        """Session-local, never touches the OS."""
        priority = 1                                # type: ignore[assignment]
        _store: dict = {}

        def get_password(self, service, username):
            return self._store.get((service, username))

        def set_password(self, service, username, password):
            self._store[(service, username)] = password

        def delete_password(self, service, username):
            self._store.pop((service, username), None)

    try:
        keyring.set_keyring(_MemoryKeyring())
    except Exception:                               # pragma: no cover
        pass


_install_memory_keyring()


# --------------------------------------------------------------------------
# Redirect the environment, then arm the guard.  Import time, on purpose:
# test modules are imported after this and their import-time constants
# then bind to the sandbox.
# --------------------------------------------------------------------------
SESSION_SANDBOX = Path(tempfile.mkdtemp(prefix="mathpdf-tests-"))
SESSION_HOME = SESSION_SANDBOX / "home"
SESSION_LIBRARY = SESSION_SANDBOX / "library"
(SESSION_HOME / ".mathpdf").mkdir(parents=True, exist_ok=True)
SESSION_LIBRARY.mkdir(parents=True, exist_ok=True)

os.environ["HOME"] = str(SESSION_HOME)
os.environ["USERPROFILE"] = str(SESSION_HOME)
os.environ["XDG_CONFIG_HOME"] = str(SESSION_HOME / ".config")
os.environ["XDG_CACHE_HOME"] = str(SESSION_HOME / ".cache")
os.environ["XDG_DATA_HOME"] = str(SESSION_HOME / ".local" / "share")
os.environ["XDG_STATE_HOME"] = str(SESSION_HOME / ".local" / "state")
os.environ["MATH_LIBRARY"] = str(SESSION_LIBRARY)
# So a subprocess (or a test that needs to *name* the real world without
# touching it) can find it without re-deriving the owner's home.
os.environ["MATHPDF_TEST_REAL_HOME"] = str(REAL_HOME)

_install_write_guard()


@atexit.register
def _cleanup_sandbox() -> None:                         # pragma: no cover
    shutil.rmtree(SESSION_SANDBOX, ignore_errors=True)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def real_world_guard():
    """Handle on the containment wall, for the tests that audit it.

    Exposes the protected prefixes and the exception type so
    ``tests/safety/test_no_test_touches_the_real_world.py`` can assert
    the wall is *armed*, not merely importable.
    """
    return _GuardHandle()


class _GuardHandle:
    exception = RealWorldWriteBlocked
    real_home = REAL_HOME
    real_library = REAL_LIBRARY
    real_dotdir = REAL_DOTDIR
    protected = PROTECTED
    exempt = EXEMPT

    @property
    def installed(self) -> bool:
        return _INSTALLED

    @staticmethod
    def offending_path(target):
        return offending_path(target)


@pytest.fixture(autouse=True)
def _never_touch_the_real_library(tmp_path_factory, monkeypatch):
    """Point every test at a throwaway library.

    Production helpers resolve the library from ``MATH_LIBRARY``, and a
    few of them construct their own ``UndoLog()`` deep inside (bulk_sort,
    process_report, bulk_apply).  Without this, running the suite wrote
    real transactions into the owner's real ``.operation_log`` — 342 of
    the 357 entries in his undo history were test junk, which buried the
    15 genuine ones and made the Activity page useless.

    ``MATH_LIBRARY`` is *also* set at module import time above, because
    five modules bind ``LIBRARY_ROOT`` before any fixture can run.  This
    fixture narrows it further to a per-test directory so tests cannot
    leak state into each other.

    A test that genuinely wants the real library can still set the
    variable itself — and the write guard will still stop it from
    writing there.
    """
    root = tmp_path_factory.mktemp("library")
    monkeypatch.setenv("MATH_LIBRARY", str(root))
    monkeypatch.setenv("HOME", str(SESSION_HOME))
    yield root
