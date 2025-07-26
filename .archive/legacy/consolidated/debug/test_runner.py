#!/usr/bin/env python3
"""
Simple test runner to check current test status
"""
import os
import sys
import subprocess
import importlib.util

def check_imports():
    """Check if key modules can be imported"""
    print("Testing imports...")
    
    # Test main imports
    try:
        import main
        print("✓ main.py imports successfully")
    except Exception as e:
        print(f"✗ main.py import failed: {e}")
        
    # Test filename_checker imports  
    try:
        import filename_checker
        print("✓ filename_checker.py imports successfully")
    except Exception as e:
        print(f"✗ filename_checker.py import failed: {e}")
        
    # Test validators imports
    try:
        from validators.filename import FilenameValidator
        print("✓ validators.filename imports successfully")
    except Exception as e:
        print(f"✗ validators.filename import failed: {e}")

def run_basic_test():
    """Run a basic test to check functionality"""
    print("\nRunning basic test...")
    
    try:
        # Try to import and run a simple test
        from tests.test_basic_validation import test_basic_functionality
        test_basic_functionality()
        print("✓ Basic validation test passed")
    except Exception as e:
        print(f"✗ Basic validation test failed: {e}")

def run_pytest():
    """Try to run pytest"""
    print("\nTrying to run pytest...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/test_basic_validation.py', 
            '-v'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
    except Exception as e:
        print(f"✗ pytest execution failed: {e}")

def main():
    """Main test runner"""
    print("=" * 50)
    print("TEST STATUS CHECKER")
    print("=" * 50)
    
    check_imports()
    run_basic_test()
    run_pytest()

if __name__ == "__main__":
    main()