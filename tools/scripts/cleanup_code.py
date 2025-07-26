#!/usr/bin/env python3
"""
Automated Code Cleanup Script
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Set


class CodeCleaner:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.backup_path = f"{file_path}.backup"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
        
        self.lines = self.content.split('\n')
        self.changes_made = []
    
    def backup_file(self):
        """Create a backup of the original file"""
        with open(self.backup_path, 'w', encoding='utf-8') as f:
            f.write(self.content)
        print(f"📋 Backup created: {self.backup_path}")
    
    def remove_unused_imports(self) -> bool:
        """Remove unused import statements"""
        # Common unused imports to remove
        unused_imports = [
            r'^from __future__ import annotations\s*$',
            r'^import threading\s*$',
            r'^from typing import Optional\s*$',
            r'^import signal\s*$',
            r'^from utils import load_yaml_config\s*$',
            r'^from mathematician_name_validator import MathematicianNameValidator\s*$',
            r'^from typing import Union\s*$',
            r'^import difflib\s*$'
        ]
        
        removed_count = 0
        new_lines = []
        
        for line in self.lines:
            should_remove = False
            for pattern in unused_imports:
                if re.match(pattern, line.strip()):
                    should_remove = True
                    removed_count += 1
                    self.changes_made.append(f"Removed unused import: {line.strip()}")
                    break
            
            if not should_remove:
                new_lines.append(line)
        
        if removed_count > 0:
            self.lines = new_lines
            print(f"🗑️ Removed {removed_count} unused imports")
            return True
        
        return False
    
    def remove_old_todo_comments(self) -> bool:
        """Remove old TODO, FIXME, HACK comments"""
        removed_count = 0
        new_lines = []
        
        for line in self.lines:
            # Check for old TODO comments with dates from 2020-2023
            if re.search(r'#\s*(TODO|FIXME|HACK).*202[0-3]', line, re.IGNORECASE):
                removed_count += 1
                self.changes_made.append(f"Removed old TODO: {line.strip()}")
                continue
            
            # Check for commented-out code (lines starting with # and containing = or def)
            if re.match(r'^\s*#\s*(def |.*=)', line):
                removed_count += 1
                self.changes_made.append(f"Removed commented code: {line.strip()}")
                continue
            
            new_lines.append(line)
        
        if removed_count > 0:
            self.lines = new_lines
            print(f"🗑️ Removed {removed_count} old TODO/commented code lines")
            return True
        
        return False
    
    def remove_duplicate_imports(self) -> bool:
        """Remove duplicate import statements"""
        seen_imports = set()
        removed_count = 0
        new_lines = []
        
        for line in self.lines:
            # Check if this looks like an import statement
            if re.match(r'^\s*(import|from)', line):
                normalized = re.sub(r'\s+', ' ', line.strip())
                if normalized in seen_imports:
                    removed_count += 1
                    self.changes_made.append(f"Removed duplicate import: {line.strip()}")
                    continue
                seen_imports.add(normalized)
            
            new_lines.append(line)
        
        if removed_count > 0:
            self.lines = new_lines
            print(f"🗑️ Removed {removed_count} duplicate imports")
            return True
        
        return False
    
    def remove_empty_lines_excess(self) -> bool:
        """Remove excessive empty lines (more than 2 consecutive)"""
        new_lines = []
        empty_count = 0
        removed_count = 0
        
        for line in self.lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:  # Allow up to 2 consecutive empty lines
                    new_lines.append(line)
                else:
                    removed_count += 1
            else:
                empty_count = 0
                new_lines.append(line)
        
        if removed_count > 0:
            self.lines = new_lines
            print(f"🗑️ Removed {removed_count} excessive empty lines")
            return True
        
        return False
    
    def clean_whitespace(self) -> bool:
        """Clean up whitespace issues"""
        changes = 0
        new_lines = []
        
        for line in self.lines:
            # Remove trailing whitespace
            cleaned_line = line.rstrip()
            if cleaned_line != line:
                changes += 1
            new_lines.append(cleaned_line)
        
        if changes > 0:
            self.lines = new_lines
            print(f"🧹 Cleaned {changes} lines of trailing whitespace")
            return True
        
        return False
    
    def standardize_quotes(self) -> bool:
        """Standardize quote usage to double quotes"""
        changes = 0
        new_lines = []
        
        for line in self.lines:
            # Simple regex to replace single quotes with double quotes
            # This is a basic implementation - more sophisticated logic would be needed for production
            if "'" in line and not line.strip().startswith('#'):
                # Only replace if it's not in a comment and not an apostrophe
                new_line = re.sub(r"'([^']*)'", r'"\1"', line)
                if new_line != line:
                    changes += 1
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        
        if changes > 0:
            self.lines = new_lines
            print(f"📝 Standardized {changes} quote usages")
            return True
        
        return False
    
    def apply_all_cleanups(self) -> bool:
        """Apply all cleanup operations"""
        print(f"🧹 Starting cleanup of {Path(self.file_path).name}")
        
        # Create backup first
        self.backup_file()
        
        # Apply all cleanups
        cleanups = [
            self.remove_unused_imports,
            self.remove_old_todo_comments,
            self.remove_duplicate_imports,
            self.remove_empty_lines_excess,
            self.clean_whitespace,
            # self.standardize_quotes,  # Commented out as it might be too aggressive
        ]
        
        any_changes = False
        for cleanup in cleanups:
            if cleanup():
                any_changes = True
        
        return any_changes
    
    def save_changes(self):
        """Save the cleaned content back to the file"""
        cleaned_content = '\n'.join(self.lines)
        
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"💾 Saved cleaned file: {self.file_path}")
        
        # Print summary of changes
        if self.changes_made:
            print(f"\n📊 Summary of changes made:")
            for change in self.changes_made[:10]:  # Show first 10 changes
                print(f"  • {change}")
            if len(self.changes_made) > 10:
                print(f"  • ... and {len(self.changes_made) - 10} more changes")
    
    def remove_backup(self):
        """Remove the backup file"""
        if os.path.exists(self.backup_path):
            os.remove(self.backup_path)
            print(f"🗑️ Removed backup: {self.backup_path}")


def clean_file(file_path: str) -> bool:
    """Clean a single file"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    if not file_path.endswith('.py'):
        print(f"⚠️ Skipping non-Python file: {file_path}")
        return False
    
    try:
        cleaner = CodeCleaner(file_path)
        if cleaner.apply_all_cleanups():
            cleaner.save_changes()
            print(f"✅ Successfully cleaned {file_path}")
            return True
        else:
            print(f"ℹ️ No changes needed for {file_path}")
            cleaner.remove_backup()
            return False
    except Exception as e:
        print(f"❌ Error cleaning {file_path}: {e}")
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python cleanup_code.py <file1.py> [file2.py] ...")
        print("   or: python cleanup_code.py --all  # Clean all .py files")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        # Clean all Python files in current directory
        python_files = list(Path('.').glob('*.py'))
        print(f"🧹 Found {len(python_files)} Python files to clean")
        
        cleaned_count = 0
        for file_path in python_files:
            if clean_file(str(file_path)):
                cleaned_count += 1
        
        print(f"\n🎉 Cleanup complete! Cleaned {cleaned_count}/{len(python_files)} files")
    else:
        # Clean specific files
        cleaned_count = 0
        for file_path in sys.argv[1:]:
            if clean_file(file_path):
                cleaned_count += 1
        
        print(f"\n🎉 Cleanup complete! Cleaned {cleaned_count}/{len(sys.argv[1:])} files")


if __name__ == "__main__":
    main()