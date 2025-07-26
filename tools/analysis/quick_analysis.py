#!/usr/bin/env python3

import os
import glob
import subprocess
from pathlib import Path

def analyze_files():
    """Quick analysis of Python files"""
    script_dir = Path("/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts")
    
    # Find all Python files in the main directory
    python_files = []
    for file in script_dir.glob("*.py"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                line_count = len(f.readlines())
            python_files.append((file.name, line_count))
        except:
            python_files.append((file.name, 0))
    
    # Sort by line count
    python_files.sort(key=lambda x: x[1], reverse=True)
    
    print("PYTHON FILES BY LINE COUNT")
    print("="*50)
    
    for filename, lines in python_files:
        if lines > 1000:
            print(f"{lines:4d} lines - {filename} [VERY LARGE]")
        elif lines > 500:
            print(f"{lines:4d} lines - {filename} [LARGE]")
        elif lines > 200:
            print(f"{lines:4d} lines - {filename} [MEDIUM]")
        else:
            print(f"{lines:4d} lines - {filename}")
    
    print(f"\nTotal files: {len(python_files)}")
    large_files = [f for f in python_files if f[1] > 500]
    print(f"Files over 500 lines: {len(large_files)}")
    
    return python_files

if __name__ == "__main__":
    analyze_files()