#!/usr/bin/env python3
"""Command line entrypoint for the Math-PDF manager.

This module provides a working CLI that orchestrates configuration loading,
basic validation, optional discovery workflow execution, and local PDF
processing.  The previous iteration only contained placeholders; this version
connects the wiring to the real processing helpers so the tool can be executed
end-to-end again.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

from constants import DEFAULT_CSV_OUTPUT, DEFAULT_HTML_OUTPUT, DEFAULT_TEMPLATE_DIR
from core.config.config_migration import ConfigurationData
from core.dependency_injection.interfaces import (
    IConfigurationService,
    IFileService,
    ILoggingService,
    IMetricsService,
    INotificationService,
    IValidationService,
)
from core.services import get_service, setup_services
from processing.main_processing import process_files, verify_configuration

try:
    from validators.filename_checker import enable_debug as enable_filename_debug  # type: ignore
except Exception:  # pragma: no cover - debug helper is optional
    enable_filename_debug = None


def build_argument_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser."""

    parser = argparse.ArgumentParser("Math-PDF manager")
    parser.add_argument("root", nargs="?", help="Folder containing PDF files to analyse")

    parser.add_argument("--auto-fix-nfc", action="store_true", dest="fix_nfc")
    parser.add_argument("--auto-fix-authors", action="store_true", dest="fix_auth")
    parser.add_argument("--ignore-nfc-on-macos", action="store_true", dest="ignore_nfc_macos")
    parser.add_argument("--exceptions-file", dest="exceptions_file")
    parser.add_argument("--problems_only", choices=["all", "short"])
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument("--output", default=DEFAULT_HTML_OUTPUT)
    parser.add_argument("--csv-output", default=DEFAULT_CSV_OUTPUT)
    parser.add_argument("--template-dir", default=DEFAULT_TEMPLATE_DIR)
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--debug", action="store_true", help="Enable debug helpers for filename validator")

    parser.add_argument("--backup", action="store_true", help="Create backups before changes")
    parser.add_argument("--max-files", type=int, default=10000, help="Maximum files to process")
    parser.add_argument("--json", action="store_true", help="Write JSON summary to --output path")
    parser.add_argument("--secure-mode", action="store_true", help="Enable enhanced security validation")
    parser.add_argument("--strict", action="store_true", help="Strict validation mode")

    # Discovery / automation options
    parser.add_argument("--discover", action="store_true", help="Run discovery workflow instead of local processing")
    parser.add_argument("--categories", nargs='+', default=['cs.LG', 'math.PR'], help="ArXiv categories for discovery")
    parser.add_argument("--max-papers", type=int, default=50, help="Maximum papers per category during discovery")
    parser.add_argument("--relevance-threshold", type=float, default=0.25, help="Minimum relevance score to accept a paper")
    parser.add_argument("--download-papers", action="store_true", help="Download discovered papers after scoring")
    parser.add_argument("--monitoring-port", type=int, default=9099, help="Monitoring port for discovery workflow")

    return parser


def validate_cli_inputs(args: argparse.Namespace, validation_service: IValidationService) -> bool:
    """Validate CLI arguments using the unified validation service."""

    if args.discover and not args.download_papers:
        # Discovery without downloads can proceed without a local root directory.
        pass
    else:
        if not args.root:
            print("Error: root directory is required unless --discover is used without downloads", file=sys.stderr)
            return False

        try:
            validation_service.validate_file_path(Path(args.root))
        except Exception as exc:  # pragma: no cover - relies on validation service exceptions
            print(f"Error: invalid root path '{args.root}': {exc}", file=sys.stderr)
            return False

    if args.exceptions_file:
        try:
            validation_service.validate_file_path(Path(args.exceptions_file))
        except Exception as exc:
            print(f"Error: invalid exceptions file '{args.exceptions_file}': {exc}", file=sys.stderr)
            return False

    # Normalise output destinations: we only ensure that the parent directories exist.
    for output_arg in ("output", "csv_output"):
        path_value = getattr(args, output_arg, None)
        if not path_value:
            continue
        output_path = Path(path_value).expanduser()
        parent = output_path.parent
        if parent and not parent.exists():
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                print(f"Error: cannot create directory '{parent}': {exc}", file=sys.stderr)
                return False

    return True


def resolve_template_dir(args: argparse.Namespace, script_dir: Path, validation_service: IValidationService) -> Path:
    """Resolve and validate the template directory path."""

    template_dir = Path(args.template_dir)
    if not template_dir.is_absolute():
        template_dir = (script_dir / template_dir).resolve()

    if not validation_service.validate_template_directory(str(template_dir)):
        raise ValueError(f"Template directory invalid: {template_dir}")

    return template_dir


async def run_discovery_workflow(args: argparse.Namespace, logging_service: ILoggingService) -> Dict[str, Any]:
    """Execute the async discovery workflow."""

    logging_service.info("Starting discovery workflow")
    from discovery.integration import discover_papers_cli

    results = await discover_papers_cli(
        categories=args.categories,
        max_papers=args.max_papers,
        threshold=args.relevance_threshold,
        download=args.download_papers,
        monitoring_port=args.monitoring_port,
    )

    if 'error' in results:
        logging_service.error(f"Discovery failed: {results['error']}")
    else:
        logging_service.info(
            f"Discovery finished — {results.get('papers_discovered', 0)} papers found across {results.get('categories_processed', 0)} categories"
        )

    return results


def write_json_output(destination: Path, data: Dict[str, Any], file_service: IFileService, logging_service: ILoggingService) -> None:
    """Serialise *data* to *destination* using the shared file service."""

    payload = json.dumps(data, indent=2, sort_keys=True)
    file_service.write_file(destination, payload)
    logging_service.info(f"JSON summary written to {destination}")


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""

    setup_services()

    # Resolve core services once.  Configuration service is retrieved to ensure
    # the secure config system initialises, even though it is not directly used
    # inside this function yet.
    get_service(IConfigurationService)
    logging_service = get_service(ILoggingService)
    file_service = get_service(IFileService)
    validation_service = get_service(IValidationService)
    metrics_service = get_service(IMetricsService)
    notification_service = get_service(INotificationService)

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    metrics_service.increment_counter("cli_invocations")

    if args.debug and enable_filename_debug:
        enable_filename_debug()
        logging_service.info("Filename validator debug mode enabled")

    if not validate_cli_inputs(args, validation_service):
        notification_service.send_notification("CLI argument validation failed", "error")
        sys.exit(1)

    script_dir = Path(__file__).resolve().parent

    try:
        template_dir = resolve_template_dir(args, script_dir, validation_service)
    except ValueError as exc:
        logging_service.error(str(exc))
        notification_service.send_notification("Template directory validation failed", "error")
        sys.exit(1)

    logging_service.info("Loading configuration data")
    config_timer = time.time()
    config_data = ConfigurationData()
    config_data.load_all(args, script_dir)
    metrics_service.record_timing("config_load_ms", (time.time() - config_timer) * 1000)

    config_warnings = verify_configuration(config_data)
    for warning in config_warnings:
        logging_service.warning(warning)
        metrics_service.increment_counter("config_warnings")

    if args.discover:
        try:
            results = asyncio.run(run_discovery_workflow(args, logging_service))
        except Exception as exc:  # pragma: no cover - discovery uses external deps
            logging_service.error(f"Discovery workflow crashed: {exc}")
            notification_service.send_notification("Discovery workflow failed", "error")
            sys.exit(1)

        if args.json:
            write_json_output(Path(args.output).expanduser(), results, file_service, logging_service)

        notification_service.send_notification("Discovery workflow completed", "info")
        return

    root_path = Path(args.root).expanduser().resolve()
    try:
        metrics_service.increment_counter("processing_runs")
        summary = process_files(
            root_path,
            config_data,
            max_files=args.max_files,
            parallel_workers=1,
            dry_run=args.dry_run,
            logger_service=logging_service,
            metrics_service=metrics_service,
        )
    except FileNotFoundError as exc:
        logging_service.error(str(exc))
        notification_service.send_notification("Root directory not found", "error")
        sys.exit(1)
    except Exception as exc:
        logging_service.error(f"Processing failed: {exc}")
        notification_service.send_notification("Processing failed", "error")
        sys.exit(1)

    logging_service.info(
        f"Processing finished — {summary['processed']} succeeded, {summary['failed']} failed (searched {summary['total_candidate_files']} files)"
    )

    if args.json:
        write_json_output(Path(args.output).expanduser(), summary, file_service, logging_service)

    notification_service.send_notification("Processing completed successfully", "info")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
