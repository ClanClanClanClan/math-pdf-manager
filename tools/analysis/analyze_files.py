#!/usr/bin/env python3

import os
import glob
from pathlib import Path

def count_lines_in_file(filepath):
    """Count lines in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def analyze_python_files():
    """Analyze all Python files in the Scripts directory"""
    scripts_dir = Path("/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts")
    
    # Get all Python files in the main Scripts directory (not subdirectories)
    python_files = list(scripts_dir.glob("*.py"))
    
    file_analysis = []
    
    for file_path in python_files:
        line_count = count_lines_in_file(file_path)
        file_analysis.append({
            'file': file_path.name,
            'lines': line_count,
            'path': str(file_path)
        })
    
    # Sort by line count (descending)
    file_analysis.sort(key=lambda x: x['lines'], reverse=True)
    
    print("="*80)
    print("PYTHON FILE ANALYSIS - SCRIPTS DIRECTORY")
    print("="*80)
    
    print(f"\nTotal Python files: {len(file_analysis)}")
    
    # Files over 500 lines
    large_files = [f for f in file_analysis if f['lines'] > 500]
    print(f"Files over 500 lines: {len(large_files)}")
    
    # Files over 1000 lines
    very_large_files = [f for f in file_analysis if f['lines'] > 1000]
    print(f"Files over 1000 lines: {len(very_large_files)}")
    
    print("\n" + "="*80)
    print("ALL FILES BY LINE COUNT")
    print("="*80)
    
    for file_info in file_analysis:
        status = ""
        if file_info['lines'] > 1000:
            status = " [VERY LARGE]"
        elif file_info['lines'] > 500:
            status = " [LARGE]"
        elif file_info['lines'] > 200:
            status = " [MEDIUM]"
        
        print(f"{file_info['lines']:4d} lines - {file_info['file']}{status}")
    
    print("\n" + "="*80)
    print("LARGE FILES (>500 lines) - PRIORITY FOR REFACTORING")
    print("="*80)
    
    for file_info in large_files:
        print(f"{file_info['lines']:4d} lines - {file_info['file']}")
    
    return file_analysis

if __name__ == "__main__":
    analyze_python_files()