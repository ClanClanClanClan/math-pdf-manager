#!/usr/bin/env python3
"""
Direct execution of your test suite without shell dependencies
"""
import sys
import os

# Ensure we're in the right directory
os.chdir('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts')
sys.path.insert(0, '.')

print("🚀 RUNNING YOUR ACTUAL TEST SUITE")
print("=" * 60)
print(f"Working directory: {os.getcwd()}")

# Execute test_functionality.py
print("\n1. EXECUTING test_functionality.py")
print("=" * 50)
try:
    # Import and run the comprehensive test
    from test_functionality import run_comprehensive_test
    print("✅ Successfully imported run_comprehensive_test")
    
    # Execute the actual test
    result = run_comprehensive_test()
    print(f"\n🏆 test_functionality.py RESULT: {'PASSED' if result else 'FAILED'}")
    
except Exception as e:
    print(f"❌ ERROR executing test_functionality.py: {e}")
    import traceback
    traceback.print_exc()

# Execute test_refactoring.py
print("\n2. EXECUTING test_refactoring.py")
print("=" * 50)
try:
    # Import and run the main function
    from test_refactoring import main
    print("✅ Successfully imported main from test_refactoring")
    
    # Execute the actual test
    result = main()
    print(f"\n🏆 test_refactoring.py RESULT: {'PASSED' if result else 'FAILED'}")
    
except Exception as e:
    print(f"❌ ERROR executing test_refactoring.py: {e}")
    import traceback
    traceback.print_exc()

# Test basic validation from tests/ directory
print("\n3. EXECUTING tests/test_basic_validation.py")
print("=" * 50)
try:
    # Import and run basic validation tests
    sys.path.insert(0, 'tests')
    from test_basic_validation import test_file_validation, test_author_validation
    print("✅ Successfully imported test functions")
    
    # Execute basic validation tests
    result1 = test_file_validation()
    result2 = test_author_validation()
    print(f"\n🏆 Basic validation tests RESULT: {'PASSED' if result1 and result2 else 'FAILED'}")
    
except Exception as e:
    print(f"❌ ERROR executing basic validation tests: {e}")
    import traceback
    traceback.print_exc()

# Test main functionality
print("\n4. EXECUTING test_main.py")
print("=" * 50)
try:
    # Import and run main tests
    import test_main
    print("✅ Successfully imported test_main")
    
    # If it has a main function, run it
    if hasattr(test_main, 'main'):
        result = test_main.main()
        print(f"\n🏆 test_main.py RESULT: {'PASSED' if result else 'FAILED'}")
    else:
        print("✅ test_main.py imported successfully (no main function to run)")
        
except Exception as e:
    print(f"❌ ERROR executing test_main.py: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✨ TEST EXECUTION COMPLETE")
print("=" * 60)