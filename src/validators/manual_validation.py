#!/usr/bin/env python3
"""Manual validation of the refactoring work"""

import sys
import os

print("🎯 MANUAL VALIDATION OF REFACTORING WORK")
print("=" * 80)

# Test results
results = []

def test_result(name, success, details=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {name}: {details}")
    results.append((name, success))
    return success

# Test 1: Basic Imports
print("\n1. Testing Basic Imports")
try:
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    test_result("Basic validators import", True, "All imports successful")
except Exception as e:
    test_result("Basic validators import", False, f"Error: {e}")

# Test 2: Debug System
print("\n2. Testing Debug System")
try:
    from validators.debug_utils import enable_debug, disable_debug, is_debug_enabled
    
    disable_debug()
    initial = is_debug_enabled()
    enable_debug()
    enabled = is_debug_enabled()
    disable_debug()
    final = is_debug_enabled()
    
    success = not initial and enabled and not final
    test_result("Debug system", success, f"Transitions: {initial} -> {enabled} -> {final}")
except Exception as e:
    test_result("Debug system", False, f"Error: {e}")

# Test 3: Unicode Constants
print("\n3. Testing Unicode Constants")
try:
    from validators.unicode_constants import SUPERSCRIPT_MAP, SUBSCRIPT_MAP, MATHBB_MAP
    
    sup_2 = SUPERSCRIPT_MAP.get('2')
    sub_2 = SUBSCRIPT_MAP.get('2')
    bb_r = MATHBB_MAP.get('R')
    
    success = sup_2 == '²' and sub_2 == '₂' and bb_r == 'ℝ'
    test_result("Unicode constants", success, f"'2' -> '{sup_2}' (super), '2' -> '{sub_2}' (sub), 'R' -> '{bb_r}' (bb)")
except Exception as e:
    test_result("Unicode constants", False, f"Error: {e}")

# Test 4: Math Utilities
print("\n4. Testing Math Utilities")
try:
    from validators.math_utils import find_math_regions, contains_math
    
    # Test cases
    test_cases = [
        ("Regular text", 0, False),
        ("Formula: $x^2$", 1, True),
        ("Display: $$x^2$$", 1, True),
    ]
    
    all_passed = True
    for text, expected_regions, expected_has_math in test_cases:
        regions = find_math_regions(text)
        has_math = contains_math(text)
        
        if len(regions) != expected_regions or has_math != expected_has_math:
            all_passed = False
            break
    
    test_result("Math utilities", all_passed, f"Tested {len(test_cases)} cases")
except Exception as e:
    test_result("Math utilities", False, f"Error: {e}")

# Test 5: Compatibility Layer
print("\n5. Testing Compatibility Layer")
try:
    from validators.filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    
    enable_debug()
    regions = find_math_regions("Test $x^2$")
    
    success = len(regions) == 1 and len(SUPERSCRIPT_MAP) > 0
    test_result("Compatibility layer", success, f"{len(regions)} regions found, {len(SUPERSCRIPT_MAP)} superscript mappings")
except Exception as e:
    test_result("Compatibility layer", False, f"Error: {e}")

# Test 6: Integration Test
print("\n6. Testing Integration")
try:
    from validators.debug_utils import enable_debug
    from validators.math_utils import detect_math_context
    from validators.unicode_constants import MATHEMATICAL_OPERATORS
    
    enable_debug()
    
    text = "Einstein's equation: E = mc²"
    context = detect_math_context(text)
    
    success = (context['has_math_symbols'] and 
               'complexity' in context and 
               len(MATHEMATICAL_OPERATORS) > 100)
    
    test_result("Integration", success, f"Context: {context['complexity']}, operators: {len(MATHEMATICAL_OPERATORS)}")
except Exception as e:
    test_result("Integration", False, f"Error: {e}")

# Test 7: Original Test Script
print("\n7. Testing Original Test Script")
try:
    import test_refactoring
    result = test_refactoring.main()
    test_result("Original test script", result, "Successfully executed")
except Exception as e:
    test_result("Original test script", False, f"Error: {e}")

# Final Summary
print("\n" + "=" * 80)
print("📊 VALIDATION SUMMARY")
print("=" * 80)

passed = sum(1 for _, success in results if success)
total = len(results)
percentage = (passed / total) * 100

print(f"Tests passed: {passed}/{total} ({percentage:.1f}%)")

if passed == total:
    print("\n🎉 EXCELLENT! ALL TESTS PASSED!")
    print("✨ Your refactoring is working perfectly!")
    print("🔧 The modular structure is functioning correctly.")
    print("🚀 Backward compatibility is maintained.")
    print("🎯 You can proceed with full confidence!")
else:
    print("\n⚠️  SOME TESTS FAILED")
    print("Failed tests:")
    for name, success in results:
        if not success:
            print(f"  ❌ {name}")

print(f"\n🏁 FINAL VERDICT: {'REFACTORING SUCCESSFUL' if passed == total else 'NEEDS ATTENTION'}")
print("=" * 80)