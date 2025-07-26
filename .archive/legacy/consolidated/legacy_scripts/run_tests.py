#!/usr/bin/env python3
"""Simple test runner that executes the tests"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🧪 STARTING COMPREHENSIVE TESTS")
print("=" * 60)

# Test 1: Basic Imports
print("\n1. Testing Basic Imports...")
try:
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    from validators.debug_utils import debug_print
    from validators.unicode_constants import MATHBB_MAP
    from validators.math_utils import contains_math
    print("✅ Basic imports successful")
except Exception as e:
    print(f"❌ Basic imports failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Compatibility Layer
print("\n2. Testing Compatibility Layer...")
try:
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    print("✅ Compatibility layer imports successful")
except Exception as e:
    print(f"❌ Compatibility layer imports failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Debug System
print("\n3. Testing Debug System...")
try:
    from validators.debug_utils import enable_debug, disable_debug, debug_print, is_debug_enabled
    enable_debug()
    print(f"Debug enabled: {is_debug_enabled()}")
    debug_print("Debug test message")
    disable_debug()
    print(f"Debug disabled: {is_debug_enabled()}")
    print("✅ Debug system working")
except Exception as e:
    print(f"❌ Debug system failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Unicode Constants
print("\n4. Testing Unicode Constants...")
try:
    from validators.unicode_constants import SUPERSCRIPT_MAP, SUBSCRIPT_MAP, MATHBB_MAP
    print(f"SUPERSCRIPT_MAP entries: {len(SUPERSCRIPT_MAP)}")
    print(f"SUBSCRIPT_MAP entries: {len(SUBSCRIPT_MAP)}")
    print(f"MATHBB_MAP entries: {len(MATHBB_MAP)}")
    print(f"Test mapping - 2 superscript: {SUPERSCRIPT_MAP.get('2')}")
    print(f"Test mapping - R mathbb: {MATHBB_MAP.get('R')}")
    print("✅ Unicode constants working")
except Exception as e:
    print(f"❌ Unicode constants failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Math Utilities
print("\n5. Testing Math Utilities...")
try:
    from validators.math_utils import find_math_regions, contains_math, is_filename_math_token
    test_text = "This is a formula: $x^2 + y^2 = z^2$ and more text"
    regions = find_math_regions(test_text)
    print(f"Found {len(regions)} math regions in test text")
    print(f"Contains math: {contains_math(test_text)}")
    print(f"Math token test: {is_filename_math_token('x²')}")
    print("✅ Math utilities working")
except Exception as e:
    print(f"❌ Math utilities failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Main Module Import
print("\n6. Testing Main Module Import...")
try:
    import main
    print("✅ Main module import successful")
except Exception as e:
    print(f"❌ Main module import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Core Modules
print("\n7. Testing Core Modules...")
modules_to_test = [
    'filename_checker',
    'pdf_parser',
    'scanner',
    'metadata_fetcher',
    'auth_manager'
]

for module_name in modules_to_test:
    try:
        __import__(module_name)
        print(f"✅ {module_name} import successful")
    except Exception as e:
        print(f"❌ {module_name} import failed: {e}")

# Test 8: Validator Classes
print("\n8. Testing Validator Classes...")
try:
    from validators import FilenameValidator, AuthorValidator, UnicodeValidator
    print("✅ Validator classes import successful")
except Exception as e:
    print(f"❌ Validator classes import failed: {e}")

# Test 9: Cross-Module Integration
print("\n9. Testing Cross-Module Integration...")
try:
    from validators.debug_utils import enable_debug
    from validators.math_utils import detect_math_context
    
    enable_debug()
    test_text = "Mathematical analysis of x² + y² = z²"
    context = detect_math_context(test_text)
    print(f"Math context: {context}")
    print("✅ Cross-module integration working")
except Exception as e:
    print(f"❌ Cross-module integration failed: {e}")
    import traceback
    traceback.print_exc()

# Test 10: Run Original Test Script
print("\n10. Running Original Test Script...")
try:
    import test_refactoring
    result = test_refactoring.main()
    if result:
        print("✅ Original test script passed")
    else:
        print("❌ Original test script failed")
except Exception as e:
    print(f"❌ Original test script failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("🏁 TESTING COMPLETE")
print("=" * 60)