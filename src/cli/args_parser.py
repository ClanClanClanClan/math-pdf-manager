"""
Command-line argument parsing for Math-PDF Manager

This module handles parsing and validation of command-line arguments,
providing a clean interface for the main application.
"""
import argparse
from pathlib import Path
from typing import Optional, List

from core.exceptions import ValidationError


class ArgumentParser:
    """Enhanced argument parser with validation"""
    
    def __init__(self):
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser"""
        parser = argparse.ArgumentParser(
            prog='mathpdf',
            description='Math-PDF Manager: Organize and validate mathematical PDFs',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_epilog()
        )
        
        # Add argument groups
        self._add_path_arguments(parser)
        self._add_operation_arguments(parser)
        self._add_option_arguments(parser)
        self._add_output_arguments(parser)
        
        return parser
    
    def _get_epilog(self) -> str:
        """Get help epilog with examples"""
        return """
Examples:
  %(prog)s /path/to/pdfs --check --report
  %(prog)s --config myconfig.yaml --auto-fix-authors
  %(prog)s --bsde --check --strict
  %(prog)s --duplicates --output-dir ./reports

For more information, see: https://github.com/username/math-pdf-manager
        """
    
    def _add_path_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add path-related arguments"""
        parser.add_argument(
            'root',
            nargs='?',
            type=Path,
            help='Root directory to process'
        )
        
        # Configuration
        parser.add_argument(
            '--config',
            type=Path,
            default=Path('config.yaml'),
            help='Configuration file (default: config.yaml)'
        )
        
        # Domain shortcuts
        shortcuts = parser.add_argument_group('Domain shortcuts')
        shortcuts.add_argument('--bsde', action='store_true',
                              help='Use BSDE folder from config')
        shortcuts.add_argument('--contract', action='store_true',
                              help='Use Contract Theory folder')
        shortcuts.add_argument('--control', action='store_true',
                              help='Use Control Theory folder')
        shortcuts.add_argument('--networks', action='store_true',
                              help='Use Optimal Control on Networks folder')
    
    def _add_operation_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add operation arguments"""
        ops = parser.add_argument_group('Operations')
        
        ops.add_argument('--check', action='store_true',
                        help='Check filenames for issues')
        ops.add_argument('--duplicates', action='store_true',
                        help='Find duplicate files')
        ops.add_argument('--metadata', action='store_true',
                        help='Extract and verify metadata')
        ops.add_argument('--auto-fix-authors', action='store_true',
                        help='Automatically fix author formatting')
        ops.add_argument('--auto-fix-unicode', action='store_true',
                        help='Automatically fix Unicode normalization')
        ops.add_argument('--auto-fix-all', action='store_true',
                        help='Apply all available fixes')
    
    def _add_option_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add option arguments"""
        opts = parser.add_argument_group('Options')
        
        opts.add_argument('--strict', action='store_true',
                         help='Enable strict validation')
        opts.add_argument('--dry-run', action='store_true',
                         help='Preview changes without applying')
        opts.add_argument('--backup', action='store_true',
                         help='Create backups before changes')
        opts.add_argument('--max-files', type=int, default=10000,
                         help='Maximum files to process')
        opts.add_argument('--parallel', type=int, default=1,
                         help='Number of parallel workers')
        
        # Verbosity
        verbosity = opts.add_mutually_exclusive_group()
        verbosity.add_argument('--quiet', action='store_true',
                              help='Minimal output')
        verbosity.add_argument('--verbose', action='store_true',
                              help='Detailed output')
        verbosity.add_argument('--debug', action='store_true',
                              help='Debug output')
    
    def _add_output_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add output arguments"""
        output = parser.add_argument_group('Output')
        
        output.add_argument('--report', action='store_true',
                           help='Generate HTML report')
        output.add_argument('--json', action='store_true',
                           help='Output results as JSON')
        output.add_argument('--csv', action='store_true',
                           help='Output results as CSV')
        output.add_argument('--output-dir', type=Path, default=Path('output'),
                           help='Output directory (default: output)')
    
    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse and validate arguments"""
        parsed = self.parser.parse_args(args)
        self._validate_args(parsed)
        return parsed
    
    def _validate_args(self, args: argparse.Namespace) -> None:
        """Validate parsed arguments"""
        # Check mutually exclusive shortcuts
        shortcuts = ['bsde', 'contract', 'control', 'networks']
        active_shortcuts = sum(getattr(args, s, False) for s in shortcuts)
        
        if active_shortcuts > 1:
            raise ValidationError("Only one domain shortcut can be used at a time")
        
        # Ensure we have a path to process
        if not args.root and active_shortcuts == 0:
            raise ValidationError("Must specify either a path or domain shortcut")
        
        # Validate operations
        operations = ['check', 'duplicates', 'metadata', 
                     'auto_fix_authors', 'auto_fix_unicode']
        if not any(getattr(args, op, False) for op in operations):
            if not (args.report or args.json or args.csv):
                raise ValidationError("No operation specified")
        
        # Handle --auto-fix-all
        if args.auto_fix_all:
            args.auto_fix_authors = True
            args.auto_fix_unicode = True
