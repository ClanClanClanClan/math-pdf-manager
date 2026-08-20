"""The suite must not be able to touch anything the owner owns.

Two halves, and they fail for different reasons on purpose.

**Half one — the wall is ARMED.**  ``tests/conftest.py`` redirects
``$HOME`` and ``$MATH_LIBRARY`` at import time and wraps the filesystem
mutators.  Every test here drives a real primitive (``open``,
``os.replace``, ``Path.write_text``) at a real production path and
asserts it is refused.  None of them asserts that a helper "returns
True": that is the failure mode this repo keeps reproducing — four tests
proved ``_retire_source()`` worked and none proved the daemon called it,
so re-arming ``path.unlink()`` stayed green.

  Every probe is chosen so that it is HARMLESS with the guard removed:
  the target's parent directory does not exist, so a de-guarded
  ``open(..., "w")`` raises ``FileNotFoundError`` without creating a
  byte.  That is what makes it safe to prove these tests failing by
  mutation against the owner's real paths.

**Half two — the test tree does not NAME the real world.**  A guard on
the write path cannot stop a test from shelling out to ``launchctl``,
opening a socket, or reading the owner's home.  One test in this suite
really did bootstrap a launchd agent into the owner's
``~/Library/LaunchAgents``; another really did download 5.4 MB of
Springer PDFs into the checkout.  So the tree is scanned for the shapes
that reach outside the sandbox, and new ones fail with ``file:line``.

Known gap, stated rather than hidden: the write guard wraps the Python
layer (``builtins.open``/``io.open``/``os.*``).  Code that opens a file
from C without going through those — an extension module doing its own
``open(2)`` — is not intercepted.  Nothing in this project does that
today; ``sqlite3`` is the one to watch if that changes.
"""
from __future__ import annotations

import ast
import os
import uuid
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parents[1]


# ==========================================================================
# Half one: the containment wall is armed
# ==========================================================================
#: Unique per session, and never reused.  A fixed probe name is not
#: safe: mutation-proving this file once created
#: ``…/Work/Maths/__pytest_guard_probe__``, and after it was deleted
#: Dropbox restored the empty directory from its own sync — so the next
#: de-guarded run found the parent PRESENT and really did land a file in
#: the owner's library.  A name that has never existed cannot come back.
_PROBE_DIR = f"__pytest_guard_probe_{uuid.uuid4().hex}__"


def _probe_under(root: Path) -> Path:
    """A path inside ``root`` whose PARENT does not exist.

    Writing to it is a no-op even when the guard is gone — ``open(...,
    "w")``, ``os.replace`` and ``os.mkdir`` all raise
    ``FileNotFoundError`` under a missing parent without creating a
    byte.  That is what makes it safe to prove these tests failing
    against the owner's real paths.  Every probe below must preserve
    that property: no ``makedirs``, no ``parents=True``.
    """
    probe = root / _PROBE_DIR / "probe.txt"
    assert not probe.parent.exists(), (
        f"{probe.parent} already exists — the probe is only harmless while "
        "its parent is absent; do not proceed"
    )
    return probe


def _assert_nothing_landed(probe: Path) -> None:
    assert not probe.exists(), f"the probe file was created: {probe}"
    assert not probe.parent.exists(), (
        f"the probe directory was created: {probe.parent}"
    )


class TestTheWallIsArmed:
    """Real primitives, real production paths, refused."""

    def test_the_guard_is_installed_at_all(self, real_world_guard):
        assert real_world_guard.installed, (
            "tests/conftest.py did not install the write guard; every test "
            "in this file below is then only proving FileNotFoundError"
        )

    @pytest.mark.parametrize("which", ["real_library", "real_dotdir"])
    def test_opening_a_write_handle_on_the_owners_data_is_refused(
            self, real_world_guard, which):
        """``open(..., "w")`` under the real library or ``~/.mathpdf``."""
        probe = _probe_under(getattr(real_world_guard, which))
        with pytest.raises(real_world_guard.exception):
            with open(probe, "w") as fh:                # noqa: SIM115
                fh.write("this must never reach the disk")
        _assert_nothing_landed(probe)

    def test_append_mode_is_refused_too(self, real_world_guard):
        """Append is the mode that produced the 342 junk activity rows."""
        probe = _probe_under(real_world_guard.real_dotdir)
        with pytest.raises(real_world_guard.exception):
            with open(probe, "a", encoding="utf-8") as fh:   # noqa: SIM115
                fh.write("{}\n")
        _assert_nothing_landed(probe)

    def test_pathlib_write_text_is_refused(self, real_world_guard):
        """``Path.write_text`` routes through ``io.open``, not ``builtins``.

        Wrapping only ``builtins.open`` would leave this hole wide open,
        and ``Path(...).write_text`` is how most of this codebase writes.
        """
        probe = _probe_under(real_world_guard.real_library)
        with pytest.raises(real_world_guard.exception):
            probe.write_text("nope", encoding="utf-8")
        _assert_nothing_landed(probe)

    def test_pathlib_write_bytes_is_refused(self, real_world_guard):
        probe = _probe_under(real_world_guard.real_library)
        with pytest.raises(real_world_guard.exception):
            probe.write_bytes(b"%PDF-1.4 nope")
        _assert_nothing_landed(probe)

    def test_low_level_os_open_is_refused(self, real_world_guard):
        probe = _probe_under(real_world_guard.real_library)
        with pytest.raises(real_world_guard.exception):
            os.open(probe, os.O_WRONLY | os.O_CREAT, 0o644)
        _assert_nothing_landed(probe)

    def test_moving_a_file_into_the_library_is_refused(
            self, real_world_guard, tmp_path):
        """The atomic-write pattern: write to tmp, ``os.replace`` into place.

        A guard that only wrapped ``open`` would let every atomic writer
        in this codebase through.
        """
        src = tmp_path / "staged.pdf"
        src.write_bytes(b"%PDF-1.4 staged")
        dest = _probe_under(real_world_guard.real_library)
        with pytest.raises(real_world_guard.exception):
            os.replace(src, dest)
        _assert_nothing_landed(dest)
        assert src.exists(), "the staged file was consumed by a refused move"

    def test_deleting_from_the_library_is_refused(self, real_world_guard):
        """Re-arming a hard delete is the exact defect this repo shipped."""
        victim = real_world_guard.real_library / f"{_PROBE_DIR}.pdf"
        assert not victim.exists(), (
            "the probe name exists in the real library; pick another rather "
            "than risk a de-guarded run unlinking a real file"
        )
        with pytest.raises(real_world_guard.exception):
            os.unlink(victim)
        with pytest.raises(real_world_guard.exception):
            Path(victim).unlink()

    def test_creating_a_directory_in_the_library_is_refused(
            self, real_world_guard):
        """``os.mkdir``, not ``os.makedirs``.

        ``makedirs`` builds the intermediates, so a de-guarded run of it
        would really create a directory in the owner's library — which
        is exactly what happened the first time this test was mutated.
        A single ``mkdir`` under a missing parent cannot.
        """
        probe = _probe_under(real_world_guard.real_library)
        with pytest.raises(real_world_guard.exception):
            os.mkdir(probe.parent / "child")
        with pytest.raises(real_world_guard.exception):
            Path(probe.parent / "child").mkdir()
        assert not probe.parent.exists()

    def test_the_checkout_itself_stays_writable(
            self, real_world_guard, tmp_path):
        """Negative control.

        The repo lives INSIDE the library root, so an over-broad guard
        would stop pytest writing its own cache and every test would
        error for the wrong reason.
        """
        repo = TESTS_ROOT.parent
        assert real_world_guard.offending_path(repo / ".pytest_cache") is None
        assert real_world_guard.offending_path(tmp_path / "x.pdf") is None
        # …and an ordinary tmp write still works through the wrapper.
        (tmp_path / "x.pdf").write_bytes(b"ok")
        assert (tmp_path / "x.pdf").read_bytes() == b"ok"

    def test_case_folding_does_not_open_a_bypass(self, real_world_guard):
        """APFS folds case; a case-sensitive prefix check is a hole.

        This library has already lost 771 renames to exactly this
        assumption, so the guard compares casefolded.
        """
        shouty = Path(str(real_world_guard.real_library).upper()) / "x.pdf"
        assert real_world_guard.offending_path(shouty) is not None


#: Constants that production modules evaluate WHILE BEING IMPORTED —
#: ``LIBRARY_ROOT = _get_library_root()`` and ``Path.home() /
#: ".mathpdf"`` at module scope.
#:
#: The import below happens at THIS module's import time, i.e. during
#: collection, in exactly the window those five modules are imported by
#: the rest of the suite — before any fixture has run.  Doing it inside
#: a test instead would import them under the autouse fixture's
#: environment, which papers over the very defect: the first version of
#: these tests did that, and both "conftest forgot to export
#: MATH_LIBRARY" and "conftest forgot to redirect HOME" survived it.
_IMPORT_TIME_BINDERS = [
    ("processing.ingest", "LIBRARY_ROOT"),
    ("processing.bulk_sort", "LIBRARY_ROOT"),
    ("processing.upgrade_to_published", "LIBRARY_ROOT"),
    ("processing.paper_transition", "LIBRARY_ROOT"),
    ("maintenance.weekly_report", "LIBRARY_ROOT"),
    ("watcher.config", "_DEFAULT_LOG_DIR"),
    ("ui.attention_queue", "DISMISSALS_PATH"),
]


def _capture_import_time_bindings() -> dict[str, Path]:
    import importlib
    out: dict[str, Path] = {}
    for module_name, attr in _IMPORT_TIME_BINDERS:
        mod = importlib.import_module(module_name)
        out[f"{module_name}.{attr}"] = Path(getattr(mod, attr))
    return out


IMPORT_TIME_BINDINGS = _capture_import_time_bindings()


class TestNothingIsFrozenToTheRealLibrary:
    """Those modules bind their root at IMPORT time.

    A per-test fixture cannot help them: by the time it runs, the
    constant is already a real Dropbox path.  ``tests/conftest.py``
    therefore exports ``MATH_LIBRARY`` and ``HOME`` at conftest import
    time, which is before any test module is imported.  These assert the
    postcondition — where the constants actually point — not that the
    export statement exists.
    """

    @pytest.mark.parametrize("name", sorted(IMPORT_TIME_BINDINGS))
    def test_the_constant_bound_during_collection_is_a_sandbox(
            self, real_world_guard, name):
        bound = IMPORT_TIME_BINDINGS[name]
        assert real_world_guard.offending_path(bound / "paper.pdf") is None, (
            f"{name} froze onto {bound} — the owner's real data. Anything "
            "this module writes lands in his papers or his cockpit."
        )
        assert real_world_guard.real_home not in bound.parents, (
            f"{name} = {bound} was bound before $HOME was redirected"
        )

    def test_home_is_redirected_for_the_whole_session(self, real_world_guard):
        home = Path.home()  # real-world-ok: asserting the redirect held
        assert home != real_world_guard.real_home, (
            "$HOME still points at the owner's home; ~/.mathpdf writes land "
            "in his cockpit Activity page"
        )
        assert real_world_guard.offending_path(
            home / ".mathpdf" / "cockpit_activity.jsonl") is None


class TestTheOwnersActivityLogIsNotWrittenTo:
    """The conservation law behind this whole file.

    Not "the cockpit resolves a sandbox path" — that is a helper being
    correct.  This drives the production path resolver, writes a row
    through it exactly as ``_log_activity`` does, and then asserts the
    owner's real file is byte-for-byte the file it was.
    """

    def test_writing_an_activity_row_leaves_the_owners_file_untouched(
            self, real_world_guard):
        real = real_world_guard.real_dotdir / "cockpit_activity.jsonl"
        before = (real.exists(),
                  real.stat().st_size if real.exists() else None,
                  real.stat().st_mtime_ns if real.exists() else None)

        from ui.cockpit import _activity_log_path
        path = _activity_log_path()
        with open(path, "a", encoding="utf-8") as fh:
            fh.write('{"action": "test.probe"}\n')

        after = (real.exists(),
                 real.stat().st_size if real.exists() else None,
                 real.stat().st_mtime_ns if real.exists() else None)
        assert before == after, (
            f"the suite modified {real}. That file is the owner's cockpit "
            "Activity page. (If another process wrote to it during this "
            "test, re-run; otherwise the redirect in tests/conftest.py is "
            "not holding.)"
        )
        assert path.read_text(encoding="utf-8").endswith('"test.probe"}\n'), (
            "the row went somewhere other than the sandbox activity log"
        )


# ==========================================================================
# Half two: the test tree does not name the real world
# ==========================================================================
#
# Violations that already exist and that this task is not allowed to
# edit (the file belongs to another owner).  The ratchet asserts the set
# is EXACTLY this — a new violation fails, and a fixed one fails too so
# the entry gets deleted instead of rotting here forever.
#
#   integration/test_open_vs_paywalled.py — hits Springer/Elsevier live
#   with ``requests.head``/``requests.get`` and writes the downloaded
#   PDFs into a ``test_open_vs_paywalled/`` directory in the CHECKOUT.
#   The two 2026-08-04 PDFs (5.4 MB) at the repo root are its output.
#   It is a collected test (``test_direct_access``), so this happens on
#   every full-suite run that has a network.
ACCEPTED: dict[tuple[str, str], str] = {
    ("integration/test_open_vs_paywalled.py", "network"):
        "legacy script-style test; hits publishers live and downloads "
        "PDFs into the checkout. Not owned by this task — reported.",
}

_NET_ROOTS = {"requests", "urllib", "httpx", "aiohttp", "socket", "smtplib",
              "ftplib", "telnetlib", "paramiko"}
_NET_CALLS = {"get", "post", "head", "put", "delete", "patch", "request",
              "urlopen", "urlretrieve", "ClientSession", "Session",
              "create_connection", "socket", "connect", "sendmail", "SMTP"}
_SUBPROCESS_CALLS = {"run", "Popen", "call", "check_call", "check_output",
                     "getoutput", "getstatusoutput"}
_OS_EXEC_CALLS = {"system", "popen", "execv", "execvp", "spawnl", "spawnv"}
#: Entry points in ``ui.cockpit_actions`` that shell out to ``launchctl``
#: and can install/bootstrap a real launchd agent for the owner.
_LAUNCHD_CALLS = {"_launchctl", "install_launch_agents", "start_watcher",
                  "stop_watcher", "watcher_status"}
def _real_home_str() -> str:
    """The owner's home, named without reaching for it.

    ``tests/conftest.py`` publishes it before redirecting ``$HOME``; the
    ``pwd`` fallback keeps the scanner usable if this module is ever run
    standalone.  Deliberately not ``Path.home()`` — that now answers
    with the sandbox, which would make the rule below vacuous.
    """
    named = os.environ.get("MATHPDF_TEST_REAL_HOME")
    if named:
        return named.rstrip("/")
    import pwd
    return pwd.getpwuid(os.getuid()).pw_dir.rstrip("/")


#: Fragments that only ever appear in a path pointing at the real world.
#: NOT a bare "/Users/": a fake absolute path like
#: ``/Users/owner/Downloads/MathInbox`` in a rendering test reaches
#: nothing, and a rule that flags it gets suppressed within a week.
_REAL_PATH_FRAGMENTS = (
    _real_home_str() + "/",
    "Dropbox/Work/Maths",       # real-world-ok: the pattern, not a use
    "/.mathpdf",                # real-world-ok: the pattern, not a use
    "Library/CloudStorage",     # real-world-ok: the pattern, not a use
)


def _dotted(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """ids of Constant nodes that are docstrings (prose, not paths)."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                out.add(id(body[0].value))
    return out


def _patch_targets(tree: ast.AST) -> str:
    """Every string handed to patch()/setattr()/setenv() in the file.

    Coarse on purpose: if a file patches ``subprocess.run`` anywhere, we
    do not flag its subprocess calls.  The point is to catch the file
    that mocks NOTHING, which is what every real incident looked like.
    """
    seen: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = _dotted(node.func)
        if not (fn.endswith("patch") or fn.endswith("patch.object")
                or fn.endswith("setattr") or fn.endswith("setenv")
                or fn.endswith("patch.dict")):
            continue
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                seen.append(arg.value)
            else:
                seen.append(_dotted(arg))
    return " ".join(seen)


def _first_argv_literal(node: ast.Call) -> str | None:
    """The literal binary name a subprocess call would execute, if any."""
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
        head = first.elts[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value
        # sys.executable -> re-entering this interpreter, not the OS
        if _dotted(head) in ("sys.executable", "self.python", "PYTHON"):
            return None
    return None


#: A line may opt out with a trailing ``# real-world-ok: <reason>``.
#: Visible in the diff, greppable in one command, and useless without a
#: reason -- unlike a silent global exclusion of this file, which is how
#: scanners quietly stop scanning.
_PRAGMA = "# real-world-ok:"


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return ``(lineno, kind, detail)`` for every real-world reach."""
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:                          # pragma: no cover
        return [(exc.lineno or 0, "unparseable", str(exc))]

    lines = source.splitlines()

    def excused(lineno: int) -> bool:
        if not (1 <= lineno <= len(lines)):
            return False
        text = lines[lineno - 1]
        if _PRAGMA not in text:
            return False
        return bool(text.split(_PRAGMA, 1)[1].strip())

    patched = _patch_targets(tree)
    docstrings = _docstring_nodes(tree)
    found: list[tuple[int, str, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            value = node.value
            # A real path has no spaces; prose that merely mentions
            # ``~/.mathpdf`` in a comment-like string is not a reach.
            if any(f in value for f in _REAL_PATH_FRAGMENTS) and (
                    not any(c.isspace() for c in value)):
                if value in patched:
                    continue
                found.append((node.lineno, "real_path_literal", value))
            continue

        if not isinstance(node, ast.Call):
            continue
        fn = _dotted(node.func)
        root, leaf = (fn.split(".", 1)[0], fn.rsplit(".", 1)[-1])

        if fn in ("Path.home", "pathlib.Path.home") or leaf == "expanduser":
            found.append((node.lineno, "owner_home", fn))

        if root == "subprocess" and leaf in _SUBPROCESS_CALLS:
            binary = _first_argv_literal(node)
            if binary is not None and "subprocess" not in patched:
                found.append((node.lineno, "subprocess", f"{fn}({binary!r})"))
        if root == "os" and leaf in _OS_EXEC_CALLS:
            found.append((node.lineno, "subprocess", fn))

        if leaf in _LAUNCHD_CALLS and "_launchctl" not in patched:
            found.append((node.lineno, "launchd", fn))

        if root in _NET_ROOTS and leaf in _NET_CALLS and root not in patched:
            found.append((node.lineno, "network", fn))

    return [f for f in found if not excused(f[0])]


def _test_tree_files() -> list[Path]:
    return sorted(p for p in TESTS_ROOT.rglob("*.py")
                  if "__pycache__" not in p.parts)


def _scan_tree() -> dict[tuple[str, str], list[str]]:
    """``(relpath, kind) -> ["relpath:line: detail", …]`` over the tree."""
    out: dict[tuple[str, str], list[str]] = {}
    for path in _test_tree_files():
        rel = path.relative_to(TESTS_ROOT).as_posix()
        for lineno, kind, detail in scan_file(path):
            out.setdefault((rel, kind), []).append(
                f"{rel}:{lineno}: {kind}: {detail}")
    return out


class TestTheTestTreeDoesNotNameTheRealWorld:

    def test_the_scanner_itself_notices(self, tmp_path):
        """A scanner nobody has seen fire is not evidence.

        Feed it one file containing one of each shape and assert it
        reports every one, with the right line.
        """
        sample = tmp_path / "test_pretend.py"
        sample.write_text(
            "import os, subprocess, requests\n"          # 1
            "from pathlib import Path\n"                 # 2
            "def test_a():\n"                            # 3
            "    Path.home()\n"                          # 4
            "    subprocess.run(['launchctl', 'list'])\n"  # 5
            "    requests.get('https://example.org')\n"   # 6
            "    os.system('rm -rf /')\n"                 # 7
            "    open('/Users/someone/.mathpdf/x', 'w')\n"  # 8
            "    from ui.cockpit_actions import start_watcher\n"  # 9
            "    start_watcher()\n",                      # 10
            encoding="utf-8")
        got = {(kind, line) for line, kind, _ in scan_file(sample)}
        assert ("owner_home", 4) in got
        assert ("subprocess", 5) in got
        assert ("network", 6) in got
        assert ("subprocess", 7) in got
        assert ("real_path_literal", 8) in got
        assert ("launchd", 10) in got

    def test_the_scanner_does_not_cry_wolf(self, tmp_path):
        """Mocked shapes and prose must NOT be flagged.

        A scanner that flags the correct code is worse than none: it
        gets suppressed, and then it stops noticing the real thing.
        """
        sample = tmp_path / "test_clean.py"
        sample.write_text(
            '"""Docstring mentioning ~/.mathpdf and launchctl freely."""\n'
            "import subprocess, sys\n"
            "from unittest.mock import patch\n"
            "def test_ok(tmp_path):\n"
            "    with patch('ui.cockpit_actions._launchctl'):\n"
            "        from ui.cockpit_actions import start_watcher\n"
            "        start_watcher()\n"
            "    subprocess.run([sys.executable, '-c', 'pass'])\n"
            "    (tmp_path / 'x').write_text('hi')\n",
            encoding="utf-8")
        assert scan_file(sample) == []

    def test_the_pragma_needs_a_reason(self, tmp_path):
        """``# real-world-ok:`` with nothing after it excuses nothing."""
        bare = tmp_path / "test_bare.py"
        bare.write_text(
            "from pathlib import Path\n"
            "def test_x():\n"
            "    Path.home()  # real-world-ok:\n",
            encoding="utf-8")
        assert [k for _, k, _ in scan_file(bare)] == ["owner_home"]

        excused = tmp_path / "test_excused.py"
        excused.write_text(
            "from pathlib import Path\n"
            "def test_x():\n"
            "    Path.home()  # real-world-ok: auditing the redirect\n",
            encoding="utf-8")
        assert scan_file(excused) == []

    def test_no_new_reach_into_the_real_world(self):
        new = {k: v for k, v in _scan_tree().items() if k not in ACCEPTED}
        assert not new, (
            "a test reaches outside its sandbox:\n  "
            + "\n  ".join(line for lines in new.values() for line in lines)
            + "\n\nUse tmp_path, mock the boundary, or -- if this really is "
              "unavoidable -- add it to ACCEPTED with the reason."
        )

    def test_the_accepted_list_has_no_stale_entries(self):
        """When someone fixes one of these, this fails until it is removed.

        Otherwise the ratchet quietly loosens over the years.
        """
        current = set(_scan_tree())
        stale = sorted(k for k in ACCEPTED if k not in current)
        assert not stale, (
            f"these no longer violate anything: {stale} -- delete them from "
            "ACCEPTED so the ratchet keeps its grip"
        )


class TestTheOSKeychainIsUnreachable:
    """A modal dialog is a denial of service against the owner.

    `secure_credential_manager._load_or_create_key` calls
    `keyring.set_password(..., "credential-store-fernet-key", ...)`,
    reached from auth.manager, downloader.browser_session and
    core.config.secure_config. With no unlocked login keychain in the
    session — which is the case for a launchd job, and for a machine
    where the dialog was dismissed once — every call raises a MODAL
    DIALOG. Six agents running the suite concurrently produced a
    non-stop stream of them and locked the owner out of his machine.

    The filesystem write guard cannot see this: the Keychain is not a
    file. conftest installs an in-memory backend at import time instead.
    """

    def test_the_backend_is_in_memory(self):
        import keyring
        assert type(keyring.get_keyring()).__name__ == "_MemoryKeyring", (
            f"tests are wired to {type(keyring.get_keyring()).__name__}; a "
            "real backend can raise a modal dialog on the owner's screen")

    def test_the_call_that_prompted_now_returns_from_memory(self):
        from secure_credential_manager import _load_or_create_key
        key = _load_or_create_key("academic_papers")
        assert key and len(key) == 44

    def test_nothing_reached_the_real_keychain(self):
        """The memory backend keeps its own store; assert the round-trip
        stays inside it."""
        import keyring
        keyring.set_password("probe-service", "probe-user", "secret")
        assert keyring.get_password("probe-service", "probe-user") == "secret"
        assert type(keyring.get_keyring())._store.get(
            ("probe-service", "probe-user")) == "secret"


class TestTheGuardCoversDirectoriesThemselves:
    """The prefixes carry a trailing separator, so a BARE directory path
    matched "protected" and missed "exempt".

    coverage.py calls os.mkdir on the checkout root with no trailing
    slash; the guard refused it, pytest died with INTERNALERROR, and no
    coverage was ever written — silently disabling the ratchet, because
    the gate could not measure what it was gating.
    """

    def test_the_library_root_itself_is_protected(self):
        from tests.conftest import REAL_LIBRARY, offending_path
        assert offending_path(str(REAL_LIBRARY)) is not None

    def test_the_checkout_itself_is_exempt(self):
        from tests.conftest import REAL_LIBRARY, offending_path
        assert offending_path(str(REAL_LIBRARY / "Scripts")) is None

    def test_files_inside_the_checkout_are_exempt(self):
        from tests.conftest import REAL_LIBRARY, offending_path
        assert offending_path(str(REAL_LIBRARY / "Scripts" / "coverage.json")) is None

    def test_papers_inside_the_library_are_protected(self):
        from tests.conftest import REAL_LIBRARY, offending_path
        assert offending_path(
            str(REAL_LIBRARY / "01 - Published papers" / "x.pdf")) is not None
