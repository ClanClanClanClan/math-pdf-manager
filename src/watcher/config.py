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
_DEFAULT_INBOX = Path.home() / "Downloads" / "MathInbox"
_DEFAULT_LIBRARY = Path.home() / "Library/CloudStorage/Dropbox/Work/Maths"
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
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except Exception as exc:
            logger.warning("Failed to load %s: %s", path, exc)
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
