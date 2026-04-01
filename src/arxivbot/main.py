"""Entry points for running the ArXiv bot pipeline."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .config import ArxivBotConfig, load_or_create_config
from .integration import ArxivBotIntegration

LOGGER = logging.getLogger(__name__)


class ArxivBot:
    """High-level orchestrator used by CLI and API layers."""

    def __init__(self, config: Optional[ArxivBotConfig] = None):
        self.config = config or load_or_create_config()
        self.integration = ArxivBotIntegration(self.config)

    async def initialize(self) -> None:
        await self.integration.initialize()

    async def run_daily_pipeline(self) -> Dict[str, Any]:
        results = await self.integration.daily_pipeline()

        accepted_cmos = results.get("accepted_cmos", [])
        harvested_counts = results.get("harvested", {})
        downloads = results.get("downloads", [])

        accepted_per_source: Dict[str, int] = {}
        downloaded_per_source: Dict[str, int] = {}
        for cmo in accepted_cmos:
            source = getattr(cmo, "source", "unknown")
            accepted_per_source[source] = accepted_per_source.get(source, 0) + 1
        for download in downloads:
            if download.get("success"):
                source = download.get("source", "arxiv")
                downloaded_per_source[source] = downloaded_per_source.get(source, 0) + 1

        summary = {
            "papers_harvested": sum(harvested_counts.values()),
            "papers_accepted": len(accepted_cmos),
            "papers_downloaded": sum(1 for item in downloads if item.get("success")),
            "harvested_per_source": harvested_counts,
            "accepted_per_source": accepted_per_source,
            "downloaded_per_source": downloaded_per_source,
            "elapsed_seconds": results.get("elapsed_seconds", 0.0),
            "digest_path": str(self._write_digest(accepted_cmos)),
        }

        return summary

    async def shutdown(self) -> None:
        await self.integration.shutdown()

    # ------------------------------------------------------------------
    def _write_digest(self, cmos) -> Path:
        data_dir = Path(self.config.data_dir)
        digest_dir = data_dir / "digests"
        digest_dir.mkdir(parents=True, exist_ok=True)
        digest_path = digest_dir / "digest_latest.md"
        lines = ["# Daily Pipeline Digest", ""]
        for cmo in cmos:
            lines.append(f"- {cmo.title}")
        digest_path.write_text("\n".join(lines), encoding="utf-8")
        return digest_path


async def _execute_pipeline(bot: ArxivBot) -> Dict[str, Any]:
    await bot.initialize()
    try:
        summary = await bot.run_daily_pipeline()
    finally:
        await bot.shutdown()
    return summary


def cli_main(argv: Optional[list[str]] = None) -> Dict[str, Any]:
    parser = argparse.ArgumentParser("mathpdf-arxivbot")
    parser.add_argument("--config", type=Path, default=None, help="Path to bot configuration file")
    parser.add_argument("--json", action="store_true", help="Write JSON summary to --output path")
    parser.add_argument("--output", type=Path, default=None, help="Output path for --json summaries")
    args = parser.parse_args(argv)

    config = load_or_create_config(args.config) if args.config else load_or_create_config()
    bot = ArxivBot(config)
    summary = asyncio.run(_execute_pipeline(bot))

    if args.json:
        output = args.output or Path.cwd() / "arxivbot_summary.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    else:
        print(json.dumps(summary, indent=2))

    return summary


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    logging.basicConfig(level=logging.INFO)
    cli_main()
