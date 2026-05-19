"""Watcher configuration with YAML file support."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Defaults
from core.config_paths import get_library_root as _get_library_root
_DEFAULT_INBOX = Path.home() / "Downloads" / "MathInbox"
_DEFAULT_LIBRARY = _get_library_root()
_DEFAULT_LOG_DIR = Path.home() / ".mathpdf"
_CONFIG_PATHS = [
    Path.home() / ".mathpdf" / "watcher.yaml",
    Path(__file__).resolve().parent.parent.parent / "config" / "watcher.yaml",
]


@dataclass
class WatcherConfig:
    """Configuration for the filesystem watcher daemon."""

    # Paths
    inbox_dir: Path = field(default_factory=lambda: _DEFAULT_INBOX)
    library_root: Path = field(default_factory=lambda: _DEFAULT_LIBRARY)
    log_dir: Path = field(default_factory=lambda: _DEFAULT_LOG_DIR)

    # Ingestion defaults
    default_status: str = "working"  # working, unpublished, published
    default_year: int = field(default_factory=lambda: datetime.now().year)
    auto_classify_topic: bool = True

    # Watcher behaviour
    settle_seconds: float = 2.0  # wait for file to finish writing
    poll_interval: float = 1.0   # watchdog polling interval
    delete_source: bool = False  # delete from inbox after filing

    # Notifications
    notifications: bool = True
    notification_sound: str = "Glass"

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "WatcherConfig":
        """Load config from YAML file, falling back to defaults."""
        if path and path.exists():
            return cls._from_yaml(path)

        for candidate in _CONFIG_PATHS:
            if candidate.exists():
                logger.info("Loading watcher config from %s", candidate)
                return cls._from_yaml(candidate)

        logger.info("No watcher config found, using defaults")
        return cls()

    @classmethod
    def _from_yaml(cls, path: Path) -> "WatcherConfig":
        # Distinguish parse errors from I/O errors so the user knows
        # whether to fix the file or check permissions.
        try:
            text = path.read_text()
        except OSError as exc:
            logger.error(
                "Cannot read watcher config at %s (%s); falling back to defaults",
                path, exc,
            )
            return cls()

        try:
            data = yaml.safe_load(text) or {}
        except yaml.YAMLError as exc:
            logger.error(
                "Watcher config at %s has invalid YAML (%s); falling back to defaults. "
                "Fix the file and restart the watcher to apply settings.",
                path, exc,
            )
            return cls()
        except Exception as exc:
            logger.error(
                "Unexpected error parsing watcher config at %s: %s; falling back to defaults",
                path, exc,
            )
            return cls()

        if not isinstance(data, dict):
            logger.error(
                "Watcher config at %s did not produce a mapping (got %s); falling back to defaults",
                path, type(data).__name__,
            )
            return cls()

        return cls(
            inbox_dir=Path(os.path.expanduser(data.get("inbox_dir", str(_DEFAULT_INBOX)))),
            library_root=Path(os.path.expanduser(data.get("library_root", str(_DEFAULT_LIBRARY)))),
            log_dir=Path(os.path.expanduser(data.get("log_dir", str(_DEFAULT_LOG_DIR)))),
            default_status=data.get("default_status", "working"),
            default_year=(
                datetime.now().year
                if data.get("default_year") in (None, "current")
                else int(data["default_year"])
            ),
            auto_classify_topic=data.get("auto_classify_topic", True),
            settle_seconds=data.get("settle_seconds", 2.0),
            poll_interval=data.get("poll_interval", 1.0),
            delete_source=data.get("delete_source", False),
            notifications=data.get("notifications", True),
            notification_sound=data.get("notification_sound", "Glass"),
        )

    def ensure_dirs(self) -> None:
        """Create inbox and log directories if they don't exist."""
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def save(self, path: Optional[Path] = None) -> Path:
        """Atomically persist this config to YAML.

        If ``path`` is None, writes to the first writable candidate in
        ``_CONFIG_PATHS`` (creating it if missing).  Atomic write via
        tmp + rename so a crash mid-write leaves the previous config
        intact.
        """
        target = path
        if target is None:
            # Prefer an existing path (the user already chose a
            # location); otherwise the first candidate that we can
            # create.
            for candidate in _CONFIG_PATHS:
                if candidate.exists():
                    target = candidate
                    break
            if target is None:
                target = _CONFIG_PATHS[0]
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "inbox_dir": str(self.inbox_dir),
            "library_root": str(self.library_root),
            "log_dir": str(self.log_dir),
            "default_status": self.default_status,
            "default_year": (
                "current" if self.default_year == datetime.now().year
                else int(self.default_year)
            ),
            "auto_classify_topic": bool(self.auto_classify_topic),
            "settle_seconds": float(self.settle_seconds),
            "poll_interval": float(self.poll_interval),
            "delete_source": bool(self.delete_source),
            "notifications": bool(self.notifications),
            "notification_sound": self.notification_sound,
        }
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
        os.replace(tmp, target)
        return target
