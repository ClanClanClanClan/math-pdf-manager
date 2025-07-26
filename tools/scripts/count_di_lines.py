#!/usr/bin/env python3
"""
Count lines of code in dependency injection implementation files.
Excludes blank lines and comments.
"""

import os
import re
from pathlib import Path

def count_code_lines(file_path: Path) -> tuple[int, int, int]:
    """
    Count total lines, code lines, and comment lines in a file.
    
    Returns:
        tuple: (total_lines, code_lines, comment_lines)
    """
    if not file_path.exists():
        return (0, 0, 0)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return (0, 0, 0)
    
    total_lines = len(lines)
    code_lines = 0
    comment_lines = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Skip blank lines
        if not stripped:
            continue
            
        # Check if line is a comment (starts with #)
        if stripped.startswith('#'):
            comment_lines += 1
            continue
            
        # Check if line is within a docstring
        if stripped.startswith('"""') or stripped.startswith("'''"):
            # This is a simplified approach - actual docstring detection would be more complex
            comment_lines += 1
            continue
            
        # Check if line only contains docstring content
        if re.match(r'^["\'].*["\']$', stripped) and len(stripped) > 10:
            comment_lines += 1
            continue
            
        # Otherwise, it's a code line
        code_lines += 1
    
    return (total_lines, code_lines, comment_lines)

def main():
    """Count lines in dependency injection files."""
    
    # Define the DI files to check
    base_path = Path("/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts")
    
    files_to_check = [
        "core/dependency_injection/container.py",
        "core/dependency_injection/interfaces.py", 
        "core/dependency_injection/implementations.py",
        "core/dependency_injection/__init__.py",
        "main_di_helpers.py"
    ]
    
    print("Dependency Injection Implementation Line Count Analysis")
    print("=" * 60)
    print()
    
    total_all_lines = 0
    total_code_lines = 0
    total_comment_lines = 0
    
    for file_path_str in files_to_check:
        file_path = base_path / file_path_str
        total_lines, code_lines, comment_lines = count_code_lines(file_path)
        
        print(f"File: {file_path_str}")
        print(f"  Total lines:   {total_lines:4d}")
        print(f"  Code lines:    {code_lines:4d}")
        print(f"  Comment lines: {comment_lines:4d}")
        print(f"  Blank lines:   {total_lines - code_lines - comment_lines:4d}")
        print()
        
        total_all_lines += total_lines
        total_code_lines += code_lines
        total_comment_lines += comment_lines
    
    print("=" * 60)
    print("SUMMARY:")
    print(f"Total files analyzed: {len(files_to_check)}")
    print(f"Total lines (all):    {total_all_lines:4d}")
    print(f"Total code lines:     {total_code_lines:4d}")
    print(f"Total comment lines:  {total_comment_lines:4d}")
    print(f"Total blank lines:    {total_all_lines - total_code_lines - total_comment_lines:4d}")
    print()
    
    # Analysis
    if total_code_lines >= 800:
        print(f"✓ CLAIM VERIFIED: {total_code_lines} lines of code meets '800+ lines' requirement")
    else:
        print(f"✗ CLAIM NOT VERIFIED: {total_code_lines} lines of code is less than 800 lines")
    
    print(f"Code percentage: {(total_code_lines / total_all_lines * 100):.1f}%")

if __name__ == "__main__":
    main()