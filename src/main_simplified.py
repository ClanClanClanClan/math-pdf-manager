#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Math-PDF manager (Simplified Architecture v20)
─────────────────────────────────────────────────────────────────────────────
REFACTORING v20:
• STRATEGIC: Replaced complex DI framework with simple service locator
• STRATEGIC: Eliminated 1,700+ lines of unnecessary abstraction
• STRATEGIC: Preserved all domain logic and functionality
• STRATEGIC: Improved startup time and maintainability
• All previous functionality preserved
"""

import argparse
import sys
import time
from pathlib import Path

# Simple service imports - no decorators or magic
from core.services import setup_services, get_service
from core.dependency_injection.interfaces import (
    IConfigurationService, ILoggingService, IFileService, 
    IValidationService, IMetricsService, INotificationService
)
from core.config.config_loader import ConfigurationData
from processing.main_processing import process_files, verify_configuration
from constants import (
    DEFAULT_HTML_OUTPUT, DEFAULT_CSV_OUTPUT, DEFAULT_TEMPLATE_DIR
)
from src.validators.filename_checker import enable_debug


def validate_cli_inputs(args: argparse.Namespace) -> bool:
    """Validate CLI inputs."""
    validation_service = get_service(IValidationService)
    
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


def validate_template_dir(template_dir: Path) -> bool:
    """Validate template directory."""
    if not template_dir.exists():
        print(f"Error: Template directory '{template_dir}' does not exist")
        return False
    if not template_dir.is_dir():
        print(f"Error: Template directory '{template_dir}' is not a directory")
        return False
    return True


def setup_environment(args: argparse.Namespace) -> Path:
    """Setup environment."""
    logging_service = get_service(ILoggingService)
    script_dir = Path(__file__).parent
    
    if args.debug:
        logging_service.debug("Debug mode enabled")
        enable_debug()
    
    return script_dir


def main(argv: list[str] | None = None) -> None:
    """
    Main function - clean and simple.
    
    No decorators, no magic, just straightforward service usage.
    """
    start_time = time.time()
    
    # Setup services once at startup
    setup_services()
    
    # Get services we need
    config_service = get_service(IConfigurationService)
    logging_service = get_service(ILoggingService)
    file_service = get_service(IFileService)
    validation_service = get_service(IValidationService)
    metrics_service = get_service(IMetricsService)
    notification_service = get_service(INotificationService)
    
    try:
        # Parse arguments
        from args_parser import create_args_parser
        parser = create_args_parser()
        args = parser.parse_args(argv)
        
        # Validate inputs
        if not validate_cli_inputs(args):
            sys.exit(1)
        
        # Setup environment
        script_dir = setup_environment(args)
        
        # Load configuration
        config_data = ConfigurationData()
        config_data.load_configuration(args)
        
        # Validate configuration
        if not verify_configuration(config_data, validation_service):
            sys.exit(1)
        
        # Validate template directory if specified
        if args.template_dir:
            template_dir = Path(args.template_dir)
        else:
            template_dir = script_dir / DEFAULT_TEMPLATE_DIR
        
        if not validate_template_dir(template_dir):
            sys.exit(1)
        
        # Process files
        logging_service.info("Starting file processing")
        metrics_service.start_operation("main_processing")
        
        try:
            process_files(
                args, config_data, template_dir,
                config_service, logging_service, file_service,
                validation_service, metrics_service
            )
            
            success = True
            logging_service.info("File processing completed successfully")
            
        except Exception as e:
            success = False
            logging_service.error(f"File processing failed: {e}")
            notification_service.notify_error(f"Processing failed: {e}")
            raise
        
        finally:
            metrics_service.end_operation("main_processing", success)
        
        # Send completion notification
        elapsed_time = time.time() - start_time
        notification_service.notify_completion(f"Processing completed in {elapsed_time:.2f}s")
        
    except KeyboardInterrupt:
        logging_service.warning("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging_service.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()