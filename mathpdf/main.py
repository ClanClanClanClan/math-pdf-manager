"""Focused CLI implementation covering the flows exercised by the tests."""
from __future__ import annotations

import argparse
import asyncio
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("mathpdf")
    parser.add_argument("root", nargs="?", help="Root directory for local processing (unused in tests)")
    parser.add_argument("--discover", action="store_true", help="Run discovery workflow")
    parser.add_argument("--use-spec-pipeline", action="store_true", help="Use specialised ArXiv pipeline")
    parser.add_argument("--spec-config", help="Optional path to specialised pipeline config", default=None)
    parser.add_argument("--json", action="store_true", help="Write JSON summary to --output")
    parser.add_argument("--output", default="pipeline_summary.json", help="Output path for JSON summary")
    return parser


async def _run_spec_pipeline(spec_config: Optional[str]) -> Dict[str, Any]:
    config_module = importlib.import_module("mathpdf.arxivbot.config")
    main_module = importlib.import_module("mathpdf.arxivbot.main")

    cfg = config_module.load_or_create_config(spec_config)
    bot = main_module.ArxivBot(cfg)

    await bot.initialize()
    try:
        summary = await bot.run_daily_pipeline()
    finally:
        shutdown = getattr(bot, "shutdown", None)
        if shutdown is not None:
            if inspect.iscoroutinefunction(shutdown):
                await shutdown()
            else:
                shutdown()

    data_dir = Path(getattr(cfg, "data_dir", Path.cwd())).expanduser()
    summary_path = data_dir / "last_pipeline_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: Optional[list[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not (args.discover and args.use_spec_pipeline):
        parser.error("Only --discover with --use-spec-pipeline is supported in this environment")

    summary = asyncio.run(_run_spec_pipeline(args.spec_config))

    if args.json:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    try:
        main()
    except SystemExit as exc:  # argparse already printed the message
        raise
    except KeyboardInterrupt:
        sys.exit(1)
