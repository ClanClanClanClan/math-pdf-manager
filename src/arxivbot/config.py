"""Configuration helpers for the lightweight ArXiv bot implementation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


def _default_sources() -> Dict[str, Dict[str, Any]]:
    return {
        "arxiv": {"enabled": True},
        "hal": {"enabled": False},
        "biorxiv": {"enabled": False},
    }


def _default_scoring() -> Dict[str, Any]:
    return {"k_neighbours": 5, "default_tau": 0.35}


@dataclass
class ArxivBotConfig:
    """Runtime configuration for the ArXiv bot."""

    data_dir: Path
    download_dir: Path
    ingest_dir: Path
    personal_corpus_path: Path
    sources: Dict[str, Dict[str, Any]] = field(default_factory=_default_sources)
    scoring: Dict[str, Any] = field(default_factory=_default_scoring)
    profiles: list[Dict[str, Any]] = field(default_factory=list)

    def ensure_directories(self) -> None:
        """Create directories referenced by the configuration if they are missing."""

        for path in (self.data_dir, self.download_dir, self.ingest_dir, self.personal_corpus_path):
            path.mkdir(parents=True, exist_ok=True)


def _load_file(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fall back to a trivial key=value format for convenience in tests.
        config: Dict[str, Any] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
        return config


def load_or_create_config(path: Optional[str | Path] = None) -> ArxivBotConfig:
    """Load configuration from *path* or create a sensible default."""

    config_path = Path(path) if path else None
    if config_path and config_path.is_file():
        data = _load_file(config_path)
        base_dir = Path(data.get("data_dir", config_path.parent / "data"))
    elif config_path and config_path.exists():
        base_dir = config_path
        data = {}
    else:
        base_dir = Path.home() / ".mathpdf" / "arxivbot"
        data = {}

    data_dir = Path(data.get("data_dir", base_dir)).expanduser().resolve()
    download_dir = Path(data.get("download_dir", data_dir / "downloads"))
    ingest_dir = Path(data.get("ingest_dir", data_dir / "ingest"))
    personal_corpus = Path(data.get("personal_corpus_path", data_dir / "corpus"))

    cfg = ArxivBotConfig(
        data_dir=data_dir,
        download_dir=download_dir,
        ingest_dir=ingest_dir,
        personal_corpus_path=personal_corpus,
        sources=data.get("sources", _default_sources()),
        scoring=data.get("scoring", _default_scoring()),
        profiles=data.get("profiles", []),
    )
    cfg.ensure_directories()
    return cfg


__all__ = ["ArxivBotConfig", "load_or_create_config"]
