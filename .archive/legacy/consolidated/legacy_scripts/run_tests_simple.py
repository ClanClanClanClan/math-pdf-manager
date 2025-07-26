#!/usr/bin/env python3
"""Simple test runner to execute the MANIAC test"""

import os
import sys
import subprocess

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("🔥 SIMPLE TEST RUNNER")
print("=" * 50)

# Run the MANIAC test
try:
    result = subprocess.run([sys.executable, "MANIAC_TEST_EXECUTION.py"], 
                          capture_output=True, text=True, cwd=current_dir)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    print(f"\nReturn code: {result.returncode}")
    
except Exception as e:
    print(f"Error running test: {e}")

# Also try running the comprehensive test
print("\n" + "=" * 50)
print("🔥 COMPREHENSIVE TEST RUNNER")
print("=" * 50)

try:
    result = subprocess.run([sys.executable, "comprehensive_test_report.py"], 
                          capture_output=True, text=True, cwd=current_dir)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    print(f"\nReturn code: {result.returncode}")
    
except Exception as e:
    print(f"Error running comprehensive test: {e}")