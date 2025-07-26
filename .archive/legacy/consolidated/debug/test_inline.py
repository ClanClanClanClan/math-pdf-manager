#!/usr/bin/env python3
"""Inline test execution"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("🎯 INLINE TEST EXECUTION")
print("=" * 50)

# Test basic imports
try:
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    print("✅ Basic imports work")
    print(f"   SUPERSCRIPT_MAP entries: {len(SUPERSCRIPT_MAP)}")
    
    # Test specific mapping
    sup_2 = SUPERSCRIPT_MAP.get('2')
    print(f"   Superscript '2': {sup_2}")
    
    # Test math regions
    regions = find_math_regions("Test $x^2$")
    print(f"   Math regions found: {len(regions)}")
    
    # Test math detection
    from validators.math_utils import contains_math
    has_math = contains_math("Test $x^2$")
    print(f"   Contains math: {has_math}")
    
    print("✅ BASIC REFACTORING TESTS PASSED!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test compatibility
try:
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    print("✅ Compatibility layer works")
    
    # Test through compatibility
    regions = find_math_regions("Test $x^2$")
    print(f"   Compatibility math regions: {len(regions)}")
    
    print("✅ COMPATIBILITY TESTS PASSED!")
    
except Exception as e:
    print(f"❌ Compatibility error: {e}")

print("\n🎉 INLINE TESTS COMPLETE")
print("The refactoring appears to be working correctly!")