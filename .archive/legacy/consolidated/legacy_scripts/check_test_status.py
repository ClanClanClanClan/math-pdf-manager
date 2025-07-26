#!/usr/bin/env python3
"""Check basic test status without external dependencies"""

import sys
import os
import traceback

def check_imports():
    """Check if critical modules import correctly"""
    print("Checking imports...")
    
    # Check if main module imports
    try:
        import main
        print("✓ main.py imports successfully")
    except ImportError as e:
        print(f"✗ main.py import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ main.py import error: {e}")
        return False
    
    # Check if filename_checker imports
    try:
        import filename_checker
        print("✓ filename_checker.py imports successfully")
    except ImportError as e:
        print(f"✗ filename_checker.py import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ filename_checker.py import error: {e}")
        return False
    
    # Check validators
    try:
        from validators.filename import FilenameValidator
        print("✓ validators.filename imports successfully")
    except ImportError as e:
        print(f"✗ validators.filename import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ validators.filename import error: {e}")
        return False
    
    return True

def run_simple_test():
    """Run a simple test to check basic functionality"""
    print("\nRunning simple test...")
    
    try:
        # Test minimal functionality
        exec(open('tests/test_minimal.py').read())
        print("✓ Minimal test completed")
    except Exception as e:
        print(f"✗ Minimal test failed: {e}")
        traceback.print_exc()

def main():
    """Main function"""
    print("=" * 50)
    print("TEST STATUS CHECK")
    print("=" * 50)
    
    if check_imports():
        print("✓ All critical imports successful")
        run_simple_test()
    else:
        print("✗ Import failures detected")
        sys.exit(1)

if __name__ == "__main__":
    main()