#!/usr/bin/env python3
"""Simple manual test to verify modules"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("🧪 SIMPLE MANUAL TEST")
print("=" * 40)

# Test 1: Basic validator imports
print("\n1. Testing validators package...")
try:
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    print("✅ validators package imported successfully")
    print(f"   - SUPERSCRIPT_MAP has {len(SUPERSCRIPT_MAP)} entries")
    print(f"   - Sample: '2' -> '{SUPERSCRIPT_MAP.get('2')}'")
except Exception as e:
    print(f"❌ validators package import failed: {e}")

# Test 2: Debug utilities
print("\n2. Testing debug utilities...")
try:
    from validators.debug_utils import enable_debug, debug_print, is_debug_enabled
    print(f"   - Debug initially: {is_debug_enabled()}")
    enable_debug()
    print(f"   - Debug after enable: {is_debug_enabled()}")
    debug_print("Test message")
    print("✅ debug utilities working")
except Exception as e:
    print(f"❌ debug utilities failed: {e}")

# Test 3: Math utilities
print("\n3. Testing math utilities...")
try:
    from validators.math_utils import find_math_regions, contains_math
    test_text = "Formula: $x^2 + y^2 = z^2$"
    regions = find_math_regions(test_text)
    has_math = contains_math(test_text)
    print(f"   - Test text: '{test_text}'")
    print(f"   - Math regions: {len(regions)}")
    print(f"   - Contains math: {has_math}")
    print("✅ math utilities working")
except Exception as e:
    print(f"❌ math utilities failed: {e}")

# Test 4: Compatibility layer
print("\n4. Testing compatibility layer...")
try:
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    print("✅ compatibility layer working")
except Exception as e:
    print(f"❌ compatibility layer failed: {e}")

# Test 5: Run original test
print("\n5. Running original test_refactoring.py...")
try:
    import test_refactoring
    print("✅ test_refactoring.py imported successfully")
    print("   Running main()...")
    result = test_refactoring.main()
    if result:
        print("✅ test_refactoring.py passed")
    else:
        print("❌ test_refactoring.py failed")
except Exception as e:
    print(f"❌ test_refactoring.py failed: {e}")

print("\n" + "=" * 40)
print("🎯 MANUAL TEST COMPLETE")
print("=" * 40)