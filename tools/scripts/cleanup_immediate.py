#!/usr/bin/env python3
"""
Immediate cleanup script for Math-PDF Manager project.
This script handles Phase 1 cleanup tasks that can be safely automated.

Usage: python cleanup_immediate.py [--dry-run] [--backup-dir PATH]
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import json

class ProjectCleaner:
    def __init__(self, project_root, dry_run=False, backup_dir=None):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.backup_dir = Path(backup_dir) if backup_dir else None
        self.stats = {
            'backup_files': 0,
            'pycache_dirs': 0,
            'pyc_files': 0,
            'space_freed': 0,
            'errors': []
        }
        
    def log(self, message, level='INFO'):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
        
    def get_size(self, path):
        """Get size of file or directory in bytes."""
        if path.is_file():
            return path.stat().st_size
        total = 0
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
        return total
        
    def backup_file(self, file_path):
        """Backup a file before deletion."""
        if self.backup_dir:
            relative = file_path.relative_to(self.project_root)
            backup_path = self.backup_dir / relative
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            
    def remove_backup_files(self):
        """Remove all .bak, .backup, .old files."""
        self.log("Scanning for backup files...")
        patterns = ['*.bak', '*.backup', '*.old']
        
        for pattern in patterns:
            for file_path in self.project_root.rglob(pattern):
                # Skip .venv directory
                if '.venv' in file_path.parts:
                    continue
                    
                try:
                    size = self.get_size(file_path)
                    
                    if self.dry_run:
                        self.log(f"Would remove: {file_path} ({size:,} bytes)")
                    else:
                        self.backup_file(file_path)
                        file_path.unlink()
                        self.log(f"Removed: {file_path} ({size:,} bytes)")
                        
                    self.stats['backup_files'] += 1
                    self.stats['space_freed'] += size
                    
                except Exception as e:
                    self.stats['errors'].append(f"Error removing {file_path}: {e}")
                    self.log(f"Error removing {file_path}: {e}", 'ERROR')
                    
    def remove_pycache(self):
        """Remove all __pycache__ directories."""
        self.log("Scanning for __pycache__ directories...")
        
        for cache_dir in self.project_root.rglob('__pycache__'):
            # Skip .venv directory
            if '.venv' in cache_dir.parts:
                continue
                
            try:
                size = self.get_size(cache_dir)
                
                if self.dry_run:
                    self.log(f"Would remove: {cache_dir} ({size:,} bytes)")
                else:
                    shutil.rmtree(cache_dir)
                    self.log(f"Removed: {cache_dir} ({size:,} bytes)")
                    
                self.stats['pycache_dirs'] += 1
                self.stats['space_freed'] += size
                
            except Exception as e:
                self.stats['errors'].append(f"Error removing {cache_dir}: {e}")
                self.log(f"Error removing {cache_dir}: {e}", 'ERROR')
                
    def remove_pyc_files(self):
        """Remove orphaned .pyc and .pyo files."""
        self.log("Scanning for compiled Python files...")
        
        for pattern in ['*.pyc', '*.pyo']:
            for file_path in self.project_root.rglob(pattern):
                # Skip .venv directory and __pycache__ (already handled)
                if '.venv' in file_path.parts or '__pycache__' in file_path.parts:
                    continue
                    
                try:
                    size = self.get_size(file_path)
                    
                    if self.dry_run:
                        self.log(f"Would remove: {file_path} ({size:,} bytes)")
                    else:
                        file_path.unlink()
                        self.log(f"Removed: {file_path} ({size:,} bytes)")
                        
                    self.stats['pyc_files'] += 1
                    self.stats['space_freed'] += size
                    
                except Exception as e:
                    self.stats['errors'].append(f"Error removing {file_path}: {e}")
                    self.log(f"Error removing {file_path}: {e}", 'ERROR')
                    
    def remove_coverage_reports(self):
        """Remove htmlcov directory."""
        htmlcov = self.project_root / 'htmlcov'
        
        if htmlcov.exists():
            try:
                size = self.get_size(htmlcov)
                
                if self.dry_run:
                    self.log(f"Would remove: {htmlcov} ({size:,} bytes)")
                else:
                    shutil.rmtree(htmlcov)
                    self.log(f"Removed: {htmlcov} ({size:,} bytes)")
                    
                self.stats['space_freed'] += size
                
            except Exception as e:
                self.stats['errors'].append(f"Error removing {htmlcov}: {e}")
                self.log(f"Error removing {htmlcov}: {e}", 'ERROR')
                
    def update_gitignore(self):
        """Ensure .gitignore has proper entries."""
        gitignore_path = self.project_root / '.gitignore'
        
        required_entries = [
            '\n# Python',
            '__pycache__/',
            '*.py[cod]',
            '*$py.class',
            '*.so',
            '.Python',
            'env/',
            'venv/',
            '.venv/',
            '\n# Backup files',
            '*.bak',
            '*.backup',
            '*.old',
            '*~',
            '\n# Coverage',
            'htmlcov/',
            '.coverage',
            '.coverage.*',
            'coverage.xml',
            '*.cover',
            '\n# IDE',
            '.idea/',
            '.vscode/',
            '*.swp',
            '*.swo',
            '\n# OS',
            '.DS_Store',
            'Thumbs.db',
        ]
        
        if self.dry_run:
            self.log("Would update .gitignore with standard entries")
            return
            
        # Read existing gitignore
        existing = set()
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                existing = set(line.strip() for line in f if line.strip())
                
        # Add missing entries
        with open(gitignore_path, 'a') as f:
            for entry in required_entries:
                if entry.strip() and entry.strip() not in existing:
                    f.write(f"{entry}\n")
                    
        self.log("Updated .gitignore with standard entries")
        
    def generate_report(self):
        """Generate cleanup report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'stats': self.stats,
            'space_freed_mb': round(self.stats['space_freed'] / 1024 / 1024, 2)
        }
        
        report_path = self.project_root / f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if not self.dry_run:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            self.log(f"Report saved to: {report_path}")
            
        # Print summary
        print("\n" + "="*60)
        print("CLEANUP SUMMARY")
        print("="*60)
        print(f"Backup files removed: {self.stats['backup_files']}")
        print(f"__pycache__ directories removed: {self.stats['pycache_dirs']}")
        print(f"Compiled Python files removed: {self.stats['pyc_files']}")
        print(f"Total space freed: {report['space_freed_mb']:.2f} MB")
        print(f"Errors encountered: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print("\nErrors:")
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")
                
    def run(self):
        """Run all cleanup tasks."""
        self.log(f"Starting cleanup of {self.project_root}")
        if self.dry_run:
            self.log("DRY RUN MODE - No files will be deleted")
            
        if self.backup_dir:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"Backing up files to: {self.backup_dir}")
            
        # Run cleanup tasks
        self.remove_backup_files()
        self.remove_pycache()
        self.remove_pyc_files()
        self.remove_coverage_reports()
        self.update_gitignore()
        
        # Generate report
        self.generate_report()
        

def main():
    parser = argparse.ArgumentParser(description='Clean up Math-PDF Manager project')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Show what would be deleted without actually deleting')
    parser.add_argument('--backup-dir', type=str, 
                        help='Directory to backup files before deletion')
    parser.add_argument('--project-root', type=str, 
                        default=os.path.dirname(os.path.abspath(__file__)),
                        help='Project root directory')
    
    args = parser.parse_args()
    
    # Confirm with user
    if not args.dry_run:
        print("WARNING: This will delete files from your project!")
        print(f"Project root: {args.project_root}")
        if args.backup_dir:
            print(f"Backup directory: {args.backup_dir}")
            print("Auto-proceeding with cleanup (backup enabled)...")
        else:
            try:
                response = input("Are you sure you want to continue? (yes/no): ")
                if response.lower() != 'yes':
                    print("Cleanup cancelled.")
                    sys.exit(0)
            except EOFError:
                print("Auto-proceeding with cleanup...")
                pass
            
    cleaner = ProjectCleaner(
        project_root=args.project_root,
        dry_run=args.dry_run,
        backup_dir=args.backup_dir
    )
    cleaner.run()
    

if __name__ == '__main__':
    main()