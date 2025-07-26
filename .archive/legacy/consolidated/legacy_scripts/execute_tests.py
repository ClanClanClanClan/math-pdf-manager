#!/usr/bin/env python3
"""Direct test execution - runs tests and captures output"""

import sys
import os
import io
import contextlib

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Capture output
output_buffer = io.StringIO()

with contextlib.redirect_stdout(output_buffer):
    with contextlib.redirect_stderr(output_buffer):
        try:
            # Import and execute the run_tests module
            exec(open('run_tests.py').read())
        except Exception as e:
            print(f"Error executing tests: {e}")
            import traceback
            traceback.print_exc()

# Get the output
output = output_buffer.getvalue()
print("TEST EXECUTION OUTPUT:")
print("=" * 60)
print(output)
print("=" * 60)

# Now let's run a few specific tests manually
print("\n🔍 MANUAL SPECIFIC TESTS")
print("=" * 60)

# Test 1: Direct import test
print("\n1. Direct Import Test:")
try:
    from validators.debug_utils import enable_debug, debug_print
    enable_debug()
    debug_print("Manual test message")
    print("✅ Direct import successful")
except Exception as e:
    print(f"❌ Direct import failed: {e}")

# Test 2: Math utilities test
print("\n2. Math Utilities Test:")
try:
    from validators.math_utils import find_math_regions, contains_math
    test_formula = "Einstein's equation: $E = mc^2$"
    regions = find_math_regions(test_formula)
    has_math = contains_math(test_formula)
    print(f"Test text: {test_formula}")
    print(f"Math regions found: {len(regions)}")
    print(f"Contains math: {has_math}")
    print("✅ Math utilities working")
except Exception as e:
    print(f"❌ Math utilities failed: {e}")

# Test 3: Unicode constants test
print("\n3. Unicode Constants Test:")
try:
    from validators.unicode_constants import SUPERSCRIPT_MAP, MATHBB_MAP
    print(f"Superscript 2: '{SUPERSCRIPT_MAP.get('2')}'")
    print(f"Mathbb R: '{MATHBB_MAP.get('R')}'")
    print("✅ Unicode constants working")
except Exception as e:
    print(f"❌ Unicode constants failed: {e}")

# Test 4: Backward compatibility test
print("\n4. Backward Compatibility Test:")
try:
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    print("✅ Backward compatibility working")
except Exception as e:
    print(f"❌ Backward compatibility failed: {e}")

print("\n🎯 FINAL VERDICT")
print("=" * 60)
print("If you see mostly ✅ symbols above, the refactoring is working correctly!")
print("If you see ❌ symbols, those components need attention.")