"""
Command implementations for Math-PDF Manager

This module contains the actual command implementations that are
called based on parsed arguments.
"""
import logging
from pathlib import Path
from typing import List
import json

from core.models import ProcessingStats
from scanner import Scanner
from validators import FilenameValidator
from duplicate_detector import DuplicateDetector
from reporter import Reporter

logger = logging.getLogger(__name__)


class CommandProcessor:
    """Process commands based on parsed arguments"""
    
    def __init__(self, config):
        self.config = config
        self.stats = ProcessingStats()
        
        # Initialize components
        self.scanner = Scanner()
        self.validator = FilenameValidator(
            strict_mode=config.get('strict_mode', False)
        )
        self.duplicate_detector = DuplicateDetector()
        self.reporter = Reporter()
    
    def process_check_command(self, path: Path, args) -> None:
        """Process filename checking command"""
        logger.info("Checking filenames...")
        
        # Scan for files
        scan_result = self.scanner.scan(
            path,
            max_files=args.max_files,
            follow_symlinks=False
        )
        
        issues_found = []
        
        # Check each file
        for file_path in scan_result.files:
            result = self.validator.validate_filename(file_path)
            
            if not result.is_valid or result.issues:
                issues_found.append({
                    'file': str(file_path),
                    'issues': result.to_dict()
                })
                
                # Apply fixes if requested
                if args.auto_fix_authors or args.auto_fix_unicode:
                    self._apply_fixes(file_path, result, args)
        
        # Generate report
        if args.report:
            self._generate_report(issues_found, args)
        
        if args.json:
            self._output_json(issues_found, args)
        
        # Update stats
        self.stats.files_processed = len(scan_result.files)
        self.stats.files_failed = len(issues_found)
        self.stats.files_succeeded = len(scan_result.files) - len(issues_found)
    
    def process_duplicates_command(self, path: Path, args) -> None:
        """Process duplicate detection command"""
        logger.info("Finding duplicates...")
        
        # Scan for files
        scan_result = self.scanner.scan(path, max_files=args.max_files)
        
        # Find duplicates
        duplicate_groups = self.duplicate_detector.find_duplicates(
            scan_result.files
        )
        
        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        
        # Generate output
        if args.report:
            self._generate_duplicate_report(duplicate_groups, args)
        
        if args.json:
            self._output_json({
                'duplicate_groups': [
                    group.to_dict() for group in duplicate_groups
                ]
            }, args)
    
    def _apply_fixes(self, file_path: Path, result, args) -> None:
        """Apply automatic fixes to a file"""
        if not result.suggested_filename:
            return
        
        new_path = file_path.parent / result.suggested_filename
        
        if new_path == file_path:
            return  # No change needed
        
        if args.dry_run:
            logger.info(f"Would rename: {file_path.name} → {new_path.name}")
            return
        
        # Create backup if requested
        if args.backup:
            backup_path = file_path.with_suffix('.pdf.bak')
            file_path.rename(backup_path)
            backup_path.rename(file_path)
        
        # Apply rename
        try:
            file_path.rename(new_path)
            logger.info(f"Renamed: {file_path.name} → {new_path.name}")
        except OSError as e:
            logger.error(f"Failed to rename {file_path}: {e}")
    
    def _generate_report(self, issues: List[dict], args) -> None:
        """Generate HTML report"""
        output_file = args.output_dir / 'validation_report.html'
        self.reporter.generate_html_report(issues, output_file)
        logger.info(f"Report generated: {output_file}")
    
    def _output_json(self, data: dict, args) -> None:
        """Output data as JSON"""
        output_file = args.output_dir / 'results.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON output: {output_file}")
