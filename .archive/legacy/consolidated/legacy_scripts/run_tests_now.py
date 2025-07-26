#!/usr/bin/env python3
"""
Direct test execution to run your actual test suite
"""
import sys
import os
import subprocess

# Change to the correct directory
os.chdir('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts')

print("=== RUNNING YOUR ACTUAL TEST SUITE ===")
print("Current directory:", os.getcwd())

# Run test_functionality.py
print("\n1. Running test_functionality.py")
print("=" * 50)
try:
    from test_functionality import run_comprehensive_test
    result1 = run_comprehensive_test()
    print(f"test_functionality.py result: {result1}")
except Exception as e:
    print(f"ERROR running test_functionality.py: {e}")
    import traceback
    traceback.print_exc()

# Run test_refactoring.py
print("\n2. Running test_refactoring.py")
print("=" * 50)
try:
    from test_refactoring import main
    result2 = main()
    print(f"test_refactoring.py result: {result2}")
except Exception as e:
    print(f"ERROR running test_refactoring.py: {e}")
    import traceback
    traceback.print_exc()

# Run pytest on tests directory
print("\n3. Running pytest on tests/ directory")
print("=" * 50)
try:
    result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '-v'], 
                          capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
except Exception as e:
    print(f"ERROR running pytest: {e}")

# Run some individual key test files
print("\n4. Running individual test files")
print("=" * 50)
key_tests = [
    'test_main.py',
    'test_auth_manager.py',
    'tests/test_basic_validation.py',
    'tests/test_filename_checker.py',
    'tests/test_scanner.py'
]

for test_file in key_tests:
    if os.path.exists(test_file):
        print(f"\nRunning {test_file}:")
        try:
            result = subprocess.run([sys.executable, test_file], 
                                  capture_output=True, text=True)
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print(f"STDOUT: {result.stdout}")
            if result.stderr:
                print(f"STDERR: {result.stderr}")
        except Exception as e:
            print(f"ERROR running {test_file}: {e}")
    else:
        print(f"File not found: {test_file}")

print("\n=== TEST EXECUTION COMPLETE ===")