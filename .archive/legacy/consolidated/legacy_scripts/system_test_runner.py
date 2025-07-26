#!/usr/bin/env python3
"""
System test runner using os.system to avoid shell snapshot issues
"""
import os
import sys
from pathlib import Path

# Change to project directory
project_dir = "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts"
os.chdir(project_dir)

print("Math-PDF Manager System Test Runner")
print("=" * 60)
print(f"Working directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")

# Test 1: Run individual test files
test_files = [
    "test_functionality.py",
    "test_refactoring.py", 
    "test_main.py"
]

for test_file in test_files:
    print(f"\n{'=' * 40}")
    print(f"Running: {test_file}")
    print(f"{'=' * 40}")
    
    if os.path.exists(test_file):
        # Use os.system to run the test
        result = os.system(f'python3 "{test_file}"')
        exit_code = result >> 8  # Extract exit code
        
        print(f"Exit code: {exit_code}")
        if exit_code == 0:
            print("✓ Test completed successfully")
        else:
            print("✗ Test failed or had issues")
    else:
        print(f"✗ Test file not found: {test_file}")

# Test 2: Run pytest on tests directory
print(f"\n{'=' * 40}")
print("Running pytest on tests/ directory")
print(f"{'=' * 40}")

if os.path.exists("tests"):
    result = os.system('python3 -m pytest tests/ -v --tb=short --no-header')
    exit_code = result >> 8
    
    print(f"pytest exit code: {exit_code}")
    if exit_code == 0:
        print("✓ pytest completed successfully")
    else:
        print("✗ pytest failed or had issues")
else:
    print("✗ tests/ directory not found")

print(f"\n{'=' * 60}")
print("System test runner completed")