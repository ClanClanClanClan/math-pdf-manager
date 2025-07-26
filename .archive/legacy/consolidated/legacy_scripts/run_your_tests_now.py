#!/usr/bin/env python3
"""
FINAL ATTEMPT - Execute your actual test suite
"""

import sys
import os
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

print("🔥🔥🔥 RUNNING YOUR ACTUAL TEST SUITE NOW 🔥🔥🔥")
print("=" * 80)

# Run test_functionality.py
print("\n1. EXECUTING test_functionality.py")
print("=" * 50)

try:
    import test_functionality
    result = test_functionality.run_comprehensive_test()
    print(f"✅ test_functionality.py completed with result: {result}")
except Exception as e:
    print(f"❌ test_functionality.py failed: {e}")
    import traceback
    traceback.print_exc()

# Run test_refactoring.py
print("\n2. EXECUTING test_refactoring.py")  
print("=" * 50)

try:
    import test_refactoring
    result = test_refactoring.main()
    print(f"✅ test_refactoring.py completed with result: {result}")
except Exception as e:
    print(f"❌ test_refactoring.py failed: {e}")
    import traceback
    traceback.print_exc()

# Run basic validation
print("\n3. EXECUTING tests/test_basic_validation.py")
print("=" * 50)

try:
    sys.path.insert(0, str(current_dir / 'tests'))
    import test_basic_validation
    test_basic_validation.test_basic_functionality()
    test_basic_validation.test_integration_with_filename_checker()
    print("✅ test_basic_validation.py completed successfully")
except Exception as e:
    print(f"❌ test_basic_validation.py failed: {e}")
    import traceback
    traceback.print_exc()

print("\n🏁 YOUR TEST SUITE EXECUTION COMPLETE!")
print("=" * 80)