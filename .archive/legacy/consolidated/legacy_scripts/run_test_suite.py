#!/usr/bin/env python3
"""
Simple test runner to execute the Math-PDF Manager test suite
"""
import os
import sys
import subprocess

def run_test_suite():
    """Run the comprehensive test suite"""
    # Change to the project directory
    project_dir = "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts"
    os.chdir(project_dir)
    
    print("Math-PDF Manager Test Suite")
    print("=" * 50)
    
    # Add project directory to Python path
    sys.path.insert(0, project_dir)
    
    # Test 1: Run pytest on tests directory
    print("\n1. Running pytest on tests/ directory...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short",
            "--no-header"
        ], capture_output=True, text=True, cwd=project_dir)
        
        print(f"Exit code: {result.returncode}")
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
    except Exception as e:
        print(f"Error running pytest: {e}")
    
    # Test 2: Run individual test files
    test_files = [
        "test_main.py",
        "test_functionality.py", 
        "test_refactoring.py"
    ]
    
    for test_file in test_files:
        print(f"\n2. Running {test_file}...")
        try:
            result = subprocess.run([
                sys.executable, test_file
            ], capture_output=True, text=True, cwd=project_dir)
            
            print(f"Exit code: {result.returncode}")
            print("STDOUT:")
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
        except Exception as e:
            print(f"Error running {test_file}: {e}")
    
    # Test 3: Try to import key modules directly
    print("\n3. Testing module imports...")
    modules_to_test = [
        "main",
        "filename_checker", 
        "scanner",
        "utils",
        "validators",
        "core.models",
        "core.exceptions"
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✓ {module} imported successfully")
        except Exception as e:
            print(f"✗ {module} failed to import: {e}")

if __name__ == "__main__":
    run_test_suite()