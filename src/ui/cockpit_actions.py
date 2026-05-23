"""Cockpit-driven actions: DOI download, watcher control, maintenance launch.

Phase 5 fills the remaining holes that previously forced the user to
drop into a terminal:

* Download a published version by DOI without leaving the cockpit.
* Start, stop, and check the watcher daemon via ``launchctl``.
* Run the weekly publication check now, see the report path, and
  load it into the Upgrade Queue.
* Browse and clear the ``04 - Papers to be downloaded/`` queue.
* Edit the YAML config (library root, Unpaywall email, …) from a form.

Every helper here returns a JSON-shaped result so the cockpit can
render it uniformly and write entries to the activity log.  Network
calls and subprocess spawns are isolated behind these helpers so the
cockpit UI stays declarative.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ``launchctl`` labels match the plist files in ``deploy/launchd/``.
WATCHER_LABEL = "ch.ethz.dpossamai.mathpdf.watcher"
WEEKLY_LABEL = "ch.ethz.dpossamai.mathpdf.weekly"


# ---------------------------------------------------------------------------
# DOI download
# ---------------------------------------------------------------------------

@dataclass
class DOIDownloadResult:
    ok: bool
    message: str
    pdf_path: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def download_doi_to_inbox(doi: str, inbox_dir: Path) -> DOIDownloadResult:
    """Resolve ``doi`` via the full strategy chain and drop the PDF in ``inbox_dir``.

    The watcher (running or not) will see the inbox file on its next
    scan.  If the watcher is off, the user can still pick it up by
    running ``python -m processing.bulk_sort`` or by moving the file
    manually.

    Returns a ``DOIDownloadResult`` so the cockpit can render the
    outcome uniformly.  Network errors are caught -- the user sees a
    helpful message rather than a stack trace.
    """
    doi = (doi or "").strip()
    if not doi:
        return DOIDownloadResult(ok=False, message="empty DOI")
    # Basic sanity gate against accidentally passing a URL.
    if doi.startswith("http"):
        # Strip a leading https://doi.org/ if present
        for prefix in ("https://doi.org/", "http://doi.org/",
                       "https://dx.doi.org/", "http://dx.doi.org/"):
            if doi.startswith(prefix):
                doi = doi[len(prefix):]
                break
    if "/" not in doi:
        return DOIDownloadResult(ok=False, message=f"not a DOI: {doi!r}")
    inbox_dir.mkdir(parents=True, exist_ok=True)
    try:
        from downloader.doi_downloader import DOIDownloader
    except ImportError as exc:
        return DOIDownloadResult(ok=False, message=f"downloader unavailable: {exc}")
    try:
        downloader = DOIDownloader()
        pdf = downloader.download(doi, inbox_dir)
    except Exception as exc:
        logger.exception("DOI download crashed for %s", doi)
        return DOIDownloadResult(ok=False, message=str(exc))
    if pdf is None:
        return DOIDownloadResult(
            ok=False,
            message=(
                "all strategies failed.  Try again after solving the "
                "Cloudflare challenge in the headful browser, or queue "
                "it for manual download from the publisher site."
            ),
        )
    return DOIDownloadResult(ok=True, message="downloaded", pdf_path=str(pdf))


# ---------------------------------------------------------------------------
# Watcher daemon control (launchctl)
# ---------------------------------------------------------------------------

def _launchctl(*args: str, capture: bool = True) -> subprocess.CompletedProcess:
    """Run ``launchctl`` with the given args, never raising."""
    return subprocess.run(
        ["launchctl", *args],
        capture_output=capture,
        text=True,
        check=False,
    )


def watcher_status() -> dict:
    """Return ``{running: bool, pid: int|None, raw: str}``.

    Parses ``launchctl print gui/<uid>/<label>`` if available; falls
    back to ``launchctl list`` which is more widely supported but
    less detailed.  Failures yield ``{running: False, pid: None}`` --
    a missing launchctl or a missing label both mean "not running".
    """
    try:
        uid = os.getuid()
    except AttributeError:  # Windows -- no daemon anyway
        return {"running": False, "pid": None, "raw": "unsupported platform"}
    proc = _launchctl("print", f"gui/{uid}/{WATCHER_LABEL}")
    raw = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        # Fall back to the old `list` interface
        proc = _launchctl("list")
        for line in (proc.stdout or "").splitlines():
            if WATCHER_LABEL in line:
                parts = line.split()
                pid: Optional[int]
                try:
                    pid = int(parts[0])
                except (IndexError, ValueError):
                    pid = None
                return {
                    "running": pid is not None and pid > 0,
                    "pid": pid,
                    "raw": line,
                }
        return {"running": False, "pid": None, "raw": "not loaded"}
    # Parse `print` output: look for "pid = NNN" and "state = running".
    # Use a regex match for the pid so trailing tokens (rare but
    # possible across launchctl versions) don't break parsing.
    pid: Optional[int] = None
    running = False
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("pid ="):
            m = re.search(r"\d+", s)
            if m:
                pid = int(m.group())
        if s.startswith("state ="):
            running = "running" in s
    return {"running": running, "pid": pid, "raw": raw}


def start_watcher() -> tuple[bool, str]:
    """``launchctl bootstrap`` the watcher plist (if installed).

    Plist install location is the standard launchd LaunchAgents
    folder under the user's home; this helper does NOT install the
    plist (that's a one-shot manual step described in
    ``deploy/launchd/install.sh``).
    """
    plist = Path.home() / "Library" / "LaunchAgents" / f"{WATCHER_LABEL}.plist"
    if not plist.exists():
        return False, (
            f"plist not installed at {plist}.  Run "
            f"deploy/launchd/install.sh once to install it."
        )
    uid = os.getuid()
    proc = _launchctl("bootstrap", f"gui/{uid}", str(plist))
    if proc.returncode != 0:
        # 'service already loaded' is fine
        msg = (proc.stderr or proc.stdout or "").strip()
        if "already loaded" in msg.lower() or "already bootstrapped" in msg.lower():
            return True, "already running"
        return False, msg or f"launchctl exit {proc.returncode}"
    return True, "watcher started"


def stop_watcher() -> tuple[bool, str]:
    """``launchctl bootout`` the watcher service."""
    uid = os.getuid()
    proc = _launchctl("bootout", f"gui/{uid}/{WATCHER_LABEL}")
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        if "could not find" in msg.lower() or "no such" in msg.lower():
            return True, "watcher was not running"
        return False, msg or f"launchctl exit {proc.returncode}"
    return True, "watcher stopped"


# ---------------------------------------------------------------------------
# Maintenance check launcher
# ---------------------------------------------------------------------------

@dataclass
class MaintenanceRunResult:
    ok: bool
    message: str
    report_path: Optional[str] = None
    summary: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)


def run_publication_check(
    library_root: Path,
    *,
    auto_apply_safe: bool = False,
    limit: Optional[int] = None,
    timeout: int = 1800,  # 30 minutes
) -> MaintenanceRunResult:
    """Run ``maintenance.weekly_report`` as a subprocess.

    Returns the JSON report's path so the cockpit can load it into
    the Upgrade Queue without making the user paste the path by hand.
    """
    # Use ``sys.executable`` so pyenv / conda / uv users keep their
    # active interpreter (and its installed deps) instead of falling
    # back to whatever ``python3`` happens to be first on PATH.
    cmd = [
        sys.executable, "-m", "maintenance.weekly_report",
        "--library", str(library_root),
        "--no-notify",
    ]
    if auto_apply_safe:
        cmd.append("--auto-apply-safe")
    if limit is not None:
        cmd += ["--limit", str(limit)]
    env = os.environ.copy()
    src = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False,
            timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired:
        return MaintenanceRunResult(
            ok=False,
            message=f"check timed out after {timeout}s -- run from CLI for full log",
        )
    except Exception as exc:
        return MaintenanceRunResult(ok=False, message=f"subprocess failed: {exc}")
    if proc.returncode != 0:
        return MaintenanceRunResult(
            ok=False,
            message=f"exit {proc.returncode}: {(proc.stderr or proc.stdout)[:500]}",
        )
    # The weekly task prints "Report: <path>" on success; pull it out.
    report_path: Optional[str] = None
    for line in (proc.stdout or "").splitlines():
        s = line.strip()
        if s.startswith("Report:"):
            report_path = s.split(":", 1)[1].strip()
            break
    # Load JSON summary if it exists
    summary: Optional[dict] = None
    if report_path:
        json_path = Path(report_path).with_suffix(".json")
        if json_path.exists():
            try:
                summary = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    return MaintenanceRunResult(
        ok=True,
        message="check complete",
        report_path=report_path,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# "To Download" queue (04/ browser)
# ---------------------------------------------------------------------------

def list_download_flags(library_root: Path) -> list[dict]:
    """Browse the ``04 - Papers to be downloaded/`` queue.

    Returns one dict per ``.txt`` flag::

        {
          "flag": Path,
          "journal": str,        # parent folder name
          "title": str,          # flag basename minus .txt
          "doi": str,            # parsed from body
          "url": str,            # parsed from body
          "body": str,           # raw flag content
          "mtime": float,
        }
    """
    flags_root = library_root / "04 - Papers to be downloaded"
    out: list[dict] = []
    if not flags_root.exists():
        return out
    for txt in sorted(flags_root.rglob("*.txt")):
        try:
            body = txt.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("cannot read flag %s: %s", txt, exc)
            continue
        doi = ""
        url = ""
        for line in body.splitlines():
            s = line.strip()
            if s.startswith("DOI:"):
                doi = s.split(":", 1)[1].strip()
            elif s.startswith("URL:"):
                url = s.split(":", 1)[1].strip()
        out.append({
            "flag": txt,
            "journal": txt.parent.name,
            "title": txt.stem,
            "doi": doi,
            "url": url,
            "body": body,
            "mtime": txt.stat().st_mtime,
        })
    return out


def mark_flag_done(flag: Path, library_root: Path) -> bool:
    """Move the flag .txt to ``.trash/done_flags/`` (recoverable)."""
    if not flag.exists():
        return False
    trash = library_root / ".trash" / "done_flags"
    trash.mkdir(parents=True, exist_ok=True)
    dest = trash / flag.name
    # Disambiguate collisions
    n = 1
    while dest.exists():
        dest = trash / f"{flag.stem} ({n}){flag.suffix}"
        n += 1
    shutil.move(str(flag), str(dest))
    return True


# ---------------------------------------------------------------------------
# Config editor
# ---------------------------------------------------------------------------

# Keys the cockpit form exposes.  Tuples of (key, label, type).
EDITABLE_CONFIG_KEYS: list[tuple[str, str, type]] = [
    ("library_root", "Library root (absolute path)", str),
    ("inbox_dir", "Watcher inbox folder", str),
    ("unpaywall_email", "Unpaywall API email", str),
    ("default_status", "Watcher default status (published/working/...)", str),
    ("settle_seconds", "Watcher settle seconds", float),
    ("notifications", "macOS notifications (true/false)", bool),
]


def load_cockpit_config() -> dict:
    """Read the cockpit-relevant config keys.

    The watcher uses YAML at the path returned by
    ``WatcherConfig.default_path()``.  Other knobs are env-only.
    This helper unions them into one dict for the form.
    """
    out: dict[str, Any] = {}
    try:
        from watcher.config import WatcherConfig
        cfg = WatcherConfig.load()
        out["library_root"] = str(cfg.library_root)
        out["inbox_dir"] = str(cfg.inbox_dir)
        out["default_status"] = cfg.default_status
        out["settle_seconds"] = cfg.settle_seconds
        out["notifications"] = cfg.notifications
    except Exception as exc:
        logger.warning("could not load watcher config: %s", exc)
    out["unpaywall_email"] = os.environ.get("UNPAYWALL_EMAIL", "")
    return out


def save_cockpit_config(values: dict, *, require_existing_paths: bool = True) -> tuple[bool, str]:
    """Write the cockpit-relevant config back to disk.

    Watcher keys go to the YAML file.  ``unpaywall_email`` is an env
    var; the cockpit cannot persist env vars itself, so we print a
    line the user can paste into their shell rc.  Returns ``(ok,
    message)`` for cockpit display.

    ``require_existing_paths``: when True (default), bounces the form
    if ``library_root`` or ``inbox_dir`` don't exist on disk.  Set to
    False for migrations that need to seed a path before creating it.
    """
    try:
        from watcher.config import WatcherConfig
    except ImportError as exc:
        return False, f"watcher.config unavailable: {exc}"
    # Pre-flight path validation so a typo doesn't silently break
    # every subsequent operation that touches the library.  Sentinel
    # check: the watcher inbox is allowed to not exist yet (we'll
    # create it on first ensure_dirs() call), but the library root
    # MUST already exist -- creating it implicitly would mask
    # configuration mistakes.
    if require_existing_paths and "library_root" in values:
        lib_path = Path(str(values["library_root"])).expanduser()
        if not lib_path.exists():
            return False, (
                f"library_root does not exist: {lib_path}.  "
                f"Create the folder first or correct the path."
            )
        if not lib_path.is_dir():
            return False, f"library_root is not a directory: {lib_path}"
    try:
        cfg = WatcherConfig.load()
        if "library_root" in values:
            cfg.library_root = Path(values["library_root"]).expanduser()
        if "inbox_dir" in values:
            cfg.inbox_dir = Path(values["inbox_dir"]).expanduser()
        if "default_status" in values:
            cfg.default_status = str(values["default_status"])
        if "settle_seconds" in values:
            cfg.settle_seconds = float(values["settle_seconds"])
        if "notifications" in values:
            cfg.notifications = bool(values["notifications"])
        cfg.save()
    except Exception as exc:
        return False, f"could not save: {exc}"
    extra_msg = ""
    if values.get("unpaywall_email"):
        extra_msg = (
            f"  -- add ``export UNPAYWALL_EMAIL='{values['unpaywall_email']}'`` "
            f"to your shell rc to persist the Unpaywall email."
        )
    return True, "config saved" + extra_msg
