#!/usr/bin/env python3
"""
Secure version of main.py entry point

This demonstrates how to refactor the main module with security improvements,
better error handling, and cleaner architecture.
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

# Import security utilities
from utils.security import PathValidator, SecureFileOperations
from core.exceptions import (
    MathPDFError, ConfigurationError, FileOperationError, 
    ValidationError, SecurityError
)
from core.models import ValidationResult, ScanResult, ProcessingStats

# Configure logging
logger = logging.getLogger(__name__)


class SecureArgumentParser:
    """Secure command-line argument parsing with validation"""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with all options"""
        parser = argparse.ArgumentParser(
            description="Math-PDF Manager: Organize mathematical PDFs",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s /path/to/pdfs --check --report
  %(prog)s --config myconfig.yaml --auto-fix-authors
  %(prog)s --bsde --check --strict
            """
        )
        
        # Path arguments
        parser.add_argument(
            'root',
            nargs='?',
            help='Root directory to process (or use --config shortcut)'
        )
        
        # Configuration
        config_group = parser.add_argument_group('Configuration')
        config_group.add_argument(
            '--config',
            type=Path,
            default=Path('config.yaml'),
            help='Configuration file path'
        )
        
        # Shortcuts (domain-specific)
        shortcuts = parser.add_argument_group('Domain shortcuts')
        shortcuts.add_argument('--bsde', action='store_true', 
                              help='Use BSDE folder')
        shortcuts.add_argument('--contract', action='store_true',
                              help='Use Contract Theory folder')
        shortcuts.add_argument('--control', action='store_true',
                              help='Use Control Theory folder')
        
        # Operations
        ops = parser.add_argument_group('Operations')
        ops.add_argument('--check', action='store_true',
                        help='Check filenames for issues')
        ops.add_argument('--duplicates', action='store_true',
                        help='Find duplicate files')
        ops.add_argument('--auto-fix-authors', action='store_true',
                        help='Automatically fix author formatting')
        ops.add_argument('--auto-fix-unicode', action='store_true',
                        help='Automatically fix Unicode normalization')
        
        # Options
        opts = parser.add_argument_group('Options')
        opts.add_argument('--strict', action='store_true',
                         help='Enable strict validation mode')
        opts.add_argument('--quiet', action='store_true',
                         help='Minimize output')
        opts.add_argument('--verbose', action='store_true',
                         help='Enable verbose output')
        opts.add_argument('--debug', action='store_true',
                         help='Enable debug mode')
        
        # Output
        output = parser.add_argument_group('Output')
        output.add_argument('--report', action='store_true',
                           help='Generate HTML report')
        output.add_argument('--json', action='store_true',
                           help='Output results as JSON')
        output.add_argument('--output-dir', type=Path,
                           default=Path('.'),
                           help='Output directory for reports')
        
        # Safety
        safety = parser.add_argument_group('Safety')
        safety.add_argument('--dry-run', action='store_true',
                           help='Preview changes without applying them')
        safety.add_argument('--backup', action='store_true',
                           help='Create backups before changes')
        safety.add_argument('--max-files', type=int, default=10000,
                           help='Maximum files to process (safety limit)')
        
        return parser
    
    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse and validate arguments"""
        parsed = self.parser.parse_args(args)
        
        # Validate arguments
        self._validate_args(parsed)
        
        return parsed
    
    def _validate_args(self, args: argparse.Namespace) -> None:
        """Validate parsed arguments for consistency and safety"""
        # Check mutually exclusive options
        shortcuts_used = sum([
            args.bsde, args.contract, args.control
        ])
        
        if shortcuts_used > 1:
            raise ValidationError(
                "Only one domain shortcut can be used at a time",
                field="shortcuts"
            )
        
        if shortcuts_used > 0 and args.root:
            raise ValidationError(
                "Cannot specify both root path and domain shortcut",
                field="root"
            )
        
        # Ensure we have a path to process
        if not args.root and shortcuts_used == 0:
            raise ValidationError(
                "Must specify either root path or domain shortcut",
                field="root"
            )
        
        # Validate output directory
        if args.report or args.json:
            if not args.output_dir.exists():
                args.output_dir.mkdir(parents=True, exist_ok=True)


class ConfigurationManager:
    """Secure configuration management"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load and validate configuration file"""
        if not self.config_path.exists():
            logger.warning(f"Configuration file not found: {self.config_path}")
            self.config = self._get_default_config()
            return
        
        try:
            # Validate file size (prevent loading huge files)
            if self.config_path.stat().st_size > 1_000_000:  # 1MB limit
                raise ConfigurationError(
                    "Configuration file too large",
                    config_file=str(self.config_path)
                )
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                # Use safe YAML loader
                self.config = yaml.safe_load(f)
            
            # Validate configuration structure
            self._validate_config()
            
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in configuration: {e}",
                config_file=str(self.config_path)
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {e}",
                config_file=str(self.config_path)
            )
    
    def _validate_config(self) -> None:
        """Validate configuration structure and values"""
        required_sections = ['folders', 'validation', 'output']
        
        for section in required_sections:
            if section not in self.config:
                logger.warning(f"Missing configuration section: {section}")
                self.config[section] = {}
        
        # Validate folder paths
        if 'folders' in self.config:
            for name, path in self.config['folders'].items():
                try:
                    # Ensure paths are strings
                    self.config['folders'][name] = str(path)
                except Exception as e:
                    logger.error(f"Invalid folder path for {name}: {e}")
                    del self.config['folders'][name]
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'folders': {},
            'validation': {
                'strict_mode': False,
                'max_title_length': 200,
                'max_author_length': 100,
            },
            'output': {
                'report_template': 'report_template.html',
                'json_indent': 2,
            },
            'processing': {
                'max_file_size': 100_000_000,  # 100MB
                'timeout': 300,  # 5 minutes
                'max_concurrent': 10,
            }
        }
    
    def get_folder_path(self, shortcut: str) -> Optional[Path]:
        """Get folder path for a shortcut"""
        if 'folders' not in self.config:
            return None
        
        shortcuts = self.config['folders'].get('shortcuts', {})
        if shortcut in shortcuts:
            return Path(shortcuts[shortcut])
        
        return None


class MathPDFManager:
    """Main application class with improved architecture"""
    
    def __init__(self, config: ConfigurationManager):
        self.config = config
        self.stats = ProcessingStats()
        
        # Initialize components (dependency injection would be better)
        self._init_components()
    
    def _init_components(self) -> None:
        """Initialize application components"""
        # These would be properly injected in a full implementation
        from scanner import Scanner
        from validators.filename import FilenameChecker
        from duplicate_detector import DuplicateDetector
        from reporter import Reporter
        
        self.scanner = Scanner()
        self.checker = FilenameChecker()
        self.duplicate_detector = DuplicateDetector()
        self.reporter = Reporter()
    
    def run(self, args: argparse.Namespace) -> int:
        """Run the application with given arguments"""
        try:
            # Determine root path
            root_path = self._determine_root_path(args)
            
            # Validate path security
            safe_path = self._validate_path_security(root_path)
            
            logger.info(f"Processing directory: {safe_path}")
            
            # Scan files
            if args.check or args.duplicates or args.auto_fix_authors:
                scan_result = self._scan_directory(safe_path, args)
                
                if args.check:
                    self._check_filenames(scan_result, args)
                
                if args.duplicates:
                    self._find_duplicates(scan_result, args)
                
                if args.auto_fix_authors:
                    self._fix_authors(scan_result, args)
            
            # Generate reports
            if args.report:
                self._generate_report(args)
            
            # Complete statistics
            self.stats.complete()
            self._print_summary()
            
            return 0
            
        except MathPDFError as e:
            logger.error(f"{e.__class__.__name__}: {e}")
            if args.debug:
                logger.exception("Full traceback:")
            return 1
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 130
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")
            if args.debug:
                logger.exception("Full traceback:")
            return 2
    
    def _determine_root_path(self, args: argparse.Namespace) -> Path:
        """Determine root path from arguments"""
        if args.root:
            return Path(args.root)
        
        # Check shortcuts
        for shortcut in ['bsde', 'contract', 'control']:
            if getattr(args, shortcut, False):
                path = self.config.get_folder_path(shortcut)
                if path:
                    return path
                raise ConfigurationError(
                    f"No path configured for shortcut: {shortcut}"
                )
        
        raise ValidationError("No root path specified")
    
    def _validate_path_security(self, path: Path) -> Path:
        """Validate path for security issues"""
        # Get current working directory as base
        base_dir = Path.cwd()
        
        try:
            # Use our secure path validator
            safe_path = PathValidator.validate_path(
                path, 
                base_dir,
                allow_symlinks=False
            )
            return safe_path
        except SecurityError as e:
            logger.error(f"Security validation failed: {e}")
            raise
    
    def _scan_directory(self, path: Path, args: argparse.Namespace) -> ScanResult:
        """Scan directory for PDF files"""
        logger.info("Scanning for PDF files...")
        
        # Apply file limit for safety
        result = self.scanner.scan(
            path,
            max_files=args.max_files,
            follow_symlinks=False
        )
        
        logger.info(f"Found {result.pdf_files} PDF files")
        self.stats.files_processed = result.pdf_files
        
        return result
    
    def _check_filenames(self, scan_result: ScanResult, 
                        args: argparse.Namespace) -> None:
        """Check filenames for issues"""
        logger.info("Checking filenames...")
        
        for pdf_path in scan_result.files:
            try:
                result = self.checker.check_filename(pdf_path)
                if not result.is_valid:
                    logger.warning(f"{pdf_path}: {result.error_count} errors")
                    self.stats.files_failed += 1
                else:
                    self.stats.files_succeeded += 1
            except Exception as e:
                logger.error(f"Failed to check {pdf_path}: {e}")
                self.stats.files_failed += 1
    
    def _find_duplicates(self, scan_result: ScanResult,
                        args: argparse.Namespace) -> None:
        """Find duplicate files"""
        logger.info("Finding duplicates...")
        
        duplicates = self.duplicate_detector.find_duplicates(
            scan_result.files
        )
        
        logger.info(f"Found {len(duplicates)} duplicate groups")
    
    def _fix_authors(self, scan_result: ScanResult,
                    args: argparse.Namespace) -> None:
        """Fix author formatting in filenames"""
        logger.info("Fixing author formatting...")
        
        # Implementation would go here
        pass
    
    def _generate_report(self, args: argparse.Namespace) -> None:
        """Generate HTML/JSON report"""
        logger.info("Generating report...")
        
        # Implementation would go here
        pass
    
    def _print_summary(self) -> None:
        """Print processing summary"""
        print("\n" + "="*60)
        print("Processing Summary")
        print("="*60)
        print(f"Files processed: {self.stats.files_processed}")
        print(f"Files succeeded: {self.stats.files_succeeded}")
        print(f"Files failed: {self.stats.files_failed}")
        print(f"Total time: {self.stats.total_processing_time:.2f}s")
        if self.stats.files_processed > 0:
            print(f"Average time: {self.stats.average_processing_time:.2f}s")


def setup_logging(args: argparse.Namespace) -> None:
    """Configure logging based on arguments"""
    level = logging.INFO
    
    if args.debug:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    elif args.verbose:
        level = logging.DEBUG
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('pdfminer').setLevel(logging.WARNING)


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point with security improvements"""
    # Parse arguments securely
    parser = SecureArgumentParser()
    
    try:
        args = parser.parse_args(argv)
    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    # Setup logging
    setup_logging(args)
    
    # Load configuration
    try:
        config = ConfigurationManager(args.config)
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    
    # Run application
    app = MathPDFManager(config)
    return app.run(args)


if __name__ == '__main__':
    sys.exit(main())