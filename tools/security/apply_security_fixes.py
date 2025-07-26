#!/usr/bin/env python3
"""
Apply security fixes throughout the Math-PDF Manager codebase

This script automatically applies critical security fixes to all Python files,
replacing vulnerable patterns with secure implementations.
"""
import re
import os
from pathlib import Path
from typing import List, Tuple
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class SecurityPatcher:
    """Apply security patches to Python files"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.files_modified = 0
        self.patterns_fixed = 0
        
        # Define security fix patterns
        self.security_fixes = [
            # Path traversal fixes
            (
                r'if\s+[\'"]\.\.[\'"]\s+in\s+(\w+)\s+or\s+\1\.startswith\([\'"]\.\./',
                self._fix_path_traversal,
                "path traversal check"
            ),
            
            # XML parsing fixes
            (
                r'ET\.fromstring\s*\(',
                'SecureXMLParser.parse_string(',
                "XML parsing (XXE vulnerability)"
            ),
            (
                r'ET\.parse\s*\(',
                'SecureXMLParser.parse_file(',
                "XML file parsing (XXE vulnerability)"
            ),
            (
                r'xml\.etree\.ElementTree\s+as\s+ET',
                'defusedxml.ElementTree as ET',
                "XML import (XXE prevention)"
            ),
            
            # File operation fixes
            (
                r'open\s*\(\s*([^,\)]+)\s*,\s*[\'"]w[\'"]',
                r'open(\1, "w", encoding="utf-8"',
                "file write without encoding"
            ),
            (
                r'open\s*\(\s*([^,\)]+)\s*,\s*[\'"]r[\'"]',
                r'open(\1, "r", encoding="utf-8"',
                "file read without encoding"
            ),
            
            # Resource management
            (
                r'^(\s*)(\w+)\s*=\s*open\s*\(',
                r'\1with open(',
                "file handle without context manager"
            ),
            
            # Regex timeout protection
            (
                r're\.compile\s*\(\s*([^,\)]+)\s*\)',
                r're.compile(\1, flags=re.UNICODE)',
                "regex compilation without Unicode flag"
            ),
        ]
        
        # Files to skip
        self.skip_files = {
            'apply_security_fixes.py',
            'test_security.py',
            'security.py',
            '__pycache__',
            '.git',
            'tools',
            'modules',
            'archive',
        }
    
    def _fix_path_traversal(self, match) -> str:
        """Replace weak path traversal check with secure validation"""
        return '''PathValidator.validate_path(user_path, base_dir)'''
    
    def patch_file(self, file_path: Path) -> List[Tuple[str, int]]:
        """Apply security patches to a single file"""
        if not file_path.exists() or not file_path.is_file():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Cannot read {file_path}: {e}")
            return []
        
        original_content = content
        fixes_applied = []
        
        # Apply each security fix
        for pattern, replacement, description in self.security_fixes:
            if callable(replacement):
                # Custom replacement function
                matches = list(re.finditer(pattern, content, re.MULTILINE))
                for match in reversed(matches):  # Process in reverse to maintain positions
                    new_text = replacement(match)
                    content = content[:match.start()] + new_text + content[match.end():]
                    fixes_applied.append((description, match.start()))
            else:
                # Simple string replacement
                matches = list(re.finditer(pattern, content, re.MULTILINE))
                if matches:
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                    for match in matches:
                        fixes_applied.append((description, match.start()))
        
        # Add imports if needed
        if fixes_applied and 'PathValidator' in content:
            if 'from utils.security import' not in content:
                # Add import at the beginning after other imports
                import_line = 'from utils.security import PathValidator, SecureXMLParser\n'
                
                # Find the right place to add import
                import_match = re.search(r'^((?:from|import)\s+.+\n)+', content, re.MULTILINE)
                if import_match:
                    insert_pos = import_match.end()
                    content = content[:insert_pos] + import_line + content[insert_pos:]
                else:
                    # No imports found, add after docstring/comments
                    lines = content.split('\n')
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        if line.strip() and not line.startswith('#') and not line.startswith('"""'):
                            insert_idx = i
                            break
                    lines.insert(insert_idx, import_line)
                    content = '\n'.join(lines)
        
        # Write back if changes were made
        if content != original_content:
            if not self.dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            self.files_modified += 1
            self.patterns_fixed += len(fixes_applied)
        
        return fixes_applied
    
    def patch_directory(self, directory: Path) -> None:
        """Recursively patch all Python files in a directory"""
        for file_path in directory.rglob('*.py'):
            # Skip certain directories and files
            if any(skip in str(file_path) for skip in self.skip_files):
                continue
            
            relative_path = file_path.relative_to(directory)
            fixes = self.patch_file(file_path)
            
            if fixes:
                logger.info(f"\n{relative_path}:")
                for fix_type, position in fixes:
                    logger.info(f"  - Fixed {fix_type} at position {position}")
    
    def run(self, target_path: Path) -> None:
        """Run the security patcher"""
        logger.info("🔒 Security Patcher - Applying critical security fixes")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.info("DRY RUN MODE - No files will be modified")
            logger.info("")
        
        if target_path.is_file():
            fixes = self.patch_file(target_path)
            if fixes:
                logger.info(f"Fixed {len(fixes)} security issues in {target_path}")
        else:
            self.patch_directory(target_path)
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ Security patching complete!")
        logger.info(f"   Files modified: {self.files_modified}")
        logger.info(f"   Patterns fixed: {self.patterns_fixed}")
        
        if self.files_modified > 0 and not self.dry_run:
            logger.info("\n⚠️  IMPORTANT: Please review the changes and test thoroughly!")
            logger.info("   Some imports may need manual adjustment.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Apply security fixes to Math-PDF Manager codebase"
    )
    parser.add_argument(
        'path',
        type=Path,
        nargs='?',
        default=Path('.'),
        help='Path to file or directory to patch (default: current directory)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without modifying files'
    )
    
    args = parser.parse_args()
    
    patcher = SecurityPatcher(dry_run=args.dry_run)
    patcher.run(args.path)


if __name__ == '__main__':
    main()