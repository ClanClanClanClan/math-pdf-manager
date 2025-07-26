#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Math-PDF manager (DI Refactored Version v19 - DEPENDENCY INJECTION)
─────────────────────────────────────────────────────────────────────────────
REFACTORING v19:
• STRATEGIC: Implemented dependency injection framework
• STRATEGIC: Reduced coupling between components
• STRATEGIC: Improved testability and maintainability
• STRATEGIC: Enhanced configuration management
• All previous fixes preserved
"""


import argparse
import sys
import time
from pathlib import Path

# Dependency injection imports
from core.dependency_injection import (
    inject, IConfigurationService, ILoggingService, IFileService, IValidationService,
    IMetricsService, INotificationService
)
from core.utils.service_registry import get_service_registry
from core.config.config_migration import ConfigurationData
from processing.main_processing import process_files, verify_configuration
from constants import (
    DEFAULT_HTML_OUTPUT, DEFAULT_CSV_OUTPUT, DEFAULT_TEMPLATE_DIR
)
from validators.filename_checker import enable_debug
# Consolidated DI helpers - extracted from main_di_helpers.py

def validate_cli_inputs_di(args: argparse.Namespace, validation_service: IValidationService) -> bool:
    """Validate CLI inputs using dependency injection."""
    if args.root:
        root_path = Path(args.root)
        if not root_path.exists():
            print(f"Error: Root path '{args.root}' does not exist")
            return False
        if not root_path.is_dir():
            print(f"Error: Root path '{args.root}' is not a directory")
            return False
    
    if args.exceptions_file:
        exceptions_path = Path(args.exceptions_file)
        if not validation_service.validate_file_path(str(exceptions_path)):
            print(f"Error: Exceptions file '{args.exceptions_file}' is not valid")
            return False
    
    output_path = Path(args.output)
    if output_path.exists() and not output_path.is_file():
        print(f"Error: Output path '{args.output}' exists but is not a file")
        return False
    
    return True

def validate_template_dir_di(template_dir: Path, validation_service: IValidationService) -> bool:
    """Validate template directory using dependency injection."""
    if not template_dir.exists():
        print(f"Error: Template directory '{template_dir}' does not exist")
        return False
    if not template_dir.is_dir():
        print(f"Error: Template directory '{template_dir}' is not a directory")
        return False
    return True

def setup_environment_di(args: argparse.Namespace, logging_service: ILoggingService) -> Path:
    """Setup environment using dependency injection."""
    script_dir = Path(__file__).parent
    
    if args.debug:
        logging_service.debug("Debug mode enabled")
        enable_debug()
    
    return script_dir

# Service registry for module-level service access
# (imports moved to top of file)

# TimeoutError is imported from author_processing.py (custom class)

# ═══════════════════════════════════════════════════════════════════
# STREAMLINED MAIN FUNCTION - Using extracted modules
# ═══════════════════════════════════════════════════════════════════


def main(argv: list[str] | None = None) -> None:
    """Main function with simplified service locator pattern."""
    
    # Setup services using simplified pattern
    from core.services import setup_services, get_service
    from core.dependency_injection.interfaces import (
        IConfigurationService, ILoggingService, IFileService, 
        IValidationService, IMetricsService, INotificationService
    )
    
    setup_services()
    
    # Get services from simplified registry
    config_service = get_service(IConfigurationService)
    logging_service = get_service(ILoggingService)
    file_service = get_service(IFileService)
    validation_service = get_service(IValidationService)
    metrics_service = get_service(IMetricsService) 
    notification_service = get_service(INotificationService)
    
    # Track main function execution
    metrics_service.increment_counter("main_function_calls")
    metrics_service.record_gauge("startup_timestamp", time.time())
    
    # Setup argument parsing
    ap = argparse.ArgumentParser("Math-PDF manager")
    ap.add_argument("root", nargs="?", help="Folder to scan OR config shortcut")
    ap.add_argument("--auto-fix-nfc", action="store_true", dest="fix_nfc")
    ap.add_argument("--auto-fix-authors", action="store_true", dest="fix_auth")
    ap.add_argument("--ignore-nfc-on-macos", action="store_true", dest="ignore_nfc_macos")
    ap.add_argument("--exceptions-file", dest="exceptions_file")
    ap.add_argument("--problems_only", choices=["all", "short"])
    ap.add_argument("--dry_run", action="store_true")
    ap.add_argument("--output", default=DEFAULT_HTML_OUTPUT)
    ap.add_argument("--csv_output", default=DEFAULT_CSV_OUTPUT)
    ap.add_argument("--template_dir", default=DEFAULT_TEMPLATE_DIR)
    ap.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    ap.add_argument("--debug", action="store_true", help="Enable debug mode for word list troubleshooting")
    
    # Security enhancements from main_secure.py
    ap.add_argument("--backup", action="store_true", help="Create backups before changes")
    ap.add_argument("--max-files", type=int, default=10000, help="Maximum files to process (safety limit)")
    ap.add_argument("--json", action="store_true", help="Output results as JSON")
    ap.add_argument("--secure-mode", action="store_true", help="Enable enhanced security validation")
    ap.add_argument("--strict", action="store_true", help="Strict validation mode")

    args = ap.parse_args(argv)

    # Setup environment
    script_dir = setup_environment_di(args, logging_service)

    # Enable debug mode if requested
    if args.debug:
        enable_debug()
        logging_service.info("🔍 Debug mode enabled - comprehensive word list debugging active")

    # Adjust logging level if verbose
    if args.verbose:
        logging_service.info("Verbose mode enabled")

    # SECURITY: Validate CLI inputs
    metrics_service.increment_counter("cli_validation_attempts")
    if not validate_cli_inputs_di(args, validation_service):
        metrics_service.increment_counter("cli_validation_failures")
        notification_service.send_notification("Invalid CLI inputs detected", "error")
        sys.exit(1)
    metrics_service.increment_counter("cli_validation_successes")

    # SECURITY: Validate template directory
    metrics_service.increment_counter("template_validation_attempts")
    if not validate_template_dir_di(args.template_dir, validation_service):
        metrics_service.increment_counter("template_validation_failures")
        notification_service.send_notification("Template directory validation failed", "error")
        sys.exit(1)
    metrics_service.increment_counter("template_validation_successes")

    # Load configuration
    logging_service.info("=== Loading Configuration ===")
    metrics_service.increment_counter("config_loading_attempts")
    config_start_time = time.time()
    
    config_data = ConfigurationData()
    config_data.load_all(args, script_dir)
    
    metrics_service.record_timing("config_loading_duration", (time.time() - config_start_time) * 1000)
    metrics_service.record_gauge("config_keys_loaded", len(config_data.config) if config_data.config else 0)

    # Verify configuration
    validation_errors = verify_configuration(config_data)
    if validation_errors:
        for error in validation_errors:
            logging_service.warning(f"⚠️  {error}")
            metrics_service.increment_counter("config_validation_warnings")
        notification_service.send_notification(f"Configuration validation issues: {len(validation_errors)} warnings", "warning")

    logging_service.info("✅ Configuration loading complete - ALL lists imported!")
    notification_service.send_notification("Configuration loaded successfully", "info")

    # Process files
    process_files(args, config_data, script_dir)
    
    # Final metrics and notification
    metrics_service.increment_counter("main_function_completions")
    notification_service.send_notification("Processing completed successfully", "info")


if __name__ == "__main__":
    main()
