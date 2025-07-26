#!/usr/bin/env python3
"""
EXECUTE YOUR TESTS - Run the actual test suite that exists
"""

import sys
import os
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

print("🔥🔥🔥 EXECUTING YOUR ACTUAL TEST SUITE 🔥🔥🔥")
print("=" * 80)

# Execute test_functionality.py
print("\n1. RUNNING test_functionality.py")
print("=" * 50)

try:
    exec(open('test_functionality.py').read())
    print("✅ test_functionality.py executed successfully")
except Exception as e:
    print(f"❌ test_functionality.py failed: {e}")
    import traceback
    traceback.print_exc()

# Execute test_refactoring.py  
print("\n2. RUNNING test_refactoring.py")
print("=" * 50)

try:
    exec(open('test_refactoring.py').read())
    print("✅ test_refactoring.py executed successfully")
except Exception as e:
    print(f"❌ test_refactoring.py failed: {e}")
    import traceback
    traceback.print_exc()

# Execute tests/test_basic_validation.py
print("\n3. RUNNING tests/test_basic_validation.py")
print("=" * 50)

try:
    exec(open('tests/test_basic_validation.py').read())
    print("✅ tests/test_basic_validation.py executed successfully")
except Exception as e:
    print(f"❌ tests/test_basic_validation.py failed: {e}")
    import traceback
    traceback.print_exc()

# Execute test_main.py
print("\n4. RUNNING test_main.py")
print("=" * 50)

try:
    exec(open('test_main.py').read())
    print("✅ test_main.py executed successfully")
except Exception as e:
    print(f"❌ test_main.py failed: {e}")
    import traceback
    traceback.print_exc()

# Test critical imports
print("\n5. TESTING CRITICAL IMPORTS")
print("=" * 50)

imports_to_test = [
    'validators',
    'validators.debug_utils', 
    'validators.unicode_constants',
    'validators.math_utils',
    'filename_checker_compatibility',
    'main',
    'filename_checker',
]

for module_name in imports_to_test:
    try:
        __import__(module_name)
        print(f"✅ {module_name}")
    except Exception as e:
        print(f"❌ {module_name}: {e}")

print("\n🏁 TEST EXECUTION COMPLETE!")
print("=" * 80)