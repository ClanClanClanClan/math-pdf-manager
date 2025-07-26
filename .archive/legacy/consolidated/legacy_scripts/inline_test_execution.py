#!/usr/bin/env python3
"""
Inline test execution - runs tests directly in Python
"""
import sys
import os
import subprocess
from pathlib import Path

# Setup paths
project_dir = Path("/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts")
os.chdir(str(project_dir))
sys.path.insert(0, str(project_dir))

print("Math-PDF Manager Inline Test Execution")
print("=" * 60)

# Try to run tests using subprocess with full path
python_executable = sys.executable

tests_to_run = [
    ("test_functionality.py", "Comprehensive functionality test"),
    ("test_refactoring.py", "Refactoring validation test"),
    ("test_main.py", "Main module test")
]

print(f"Using Python executable: {python_executable}")
print(f"Working directory: {os.getcwd()}")

for test_file, description in tests_to_run:
    print(f"\n{'=' * 40}")
    print(f"Running: {test_file}")
    print(f"Description: {description}")
    print(f"{'=' * 40}")
    
    try:
        # Use subprocess with shell=True to avoid shell snapshot issues
        result = subprocess.run(
            f'"{python_executable}" "{test_file}"',
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(project_dir),
            timeout=300  # 5 minute timeout
        )
        
        print(f"Exit code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✓ Test completed successfully")
        else:
            print("✗ Test failed or had issues")
            
    except subprocess.TimeoutExpired:
        print("✗ Test timed out (5 minutes)")
    except Exception as e:
        print(f"✗ Error running test: {e}")

# Try to run pytest on tests directory
print(f"\n{'=' * 40}")
print("Running pytest on tests/ directory")
print(f"{'=' * 40}")

try:
    result = subprocess.run(
        f'"{python_executable}" -m pytest tests/ -v --tb=short --no-header',
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(project_dir),
        timeout=600  # 10 minute timeout
    )
    
    print(f"Exit code: {result.returncode}")
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
except subprocess.TimeoutExpired:
    print("✗ pytest timed out (10 minutes)")
except Exception as e:
    print(f"✗ Error running pytest: {e}")

print(f"\n{'=' * 60}")
print("Inline test execution completed")