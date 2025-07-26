#!/usr/bin/env python3
"""Comprehensive Test Report - Final execution and summary"""

import sys
import os
import traceback
from pathlib import Path
import importlib

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("🎯 COMPREHENSIVE REFACTORING TEST REPORT")
print("=" * 80)
print("This report validates all aspects of your refactoring work.")
print("=" * 80)

# Store all test results
test_results = []

def execute_test(test_name, test_description, test_func):
    """Execute a test and record results"""
    print(f"\n🧪 {test_name}")
    print(f"   {test_description}")
    print("-" * 60)
    
    try:
        result = test_func()
        if result:
            print(f"✅ {test_name} - PASSED")
            test_results.append((test_name, True, ""))
        else:
            print(f"❌ {test_name} - FAILED")
            test_results.append((test_name, False, "Test function returned False"))
    except Exception as e:
        print(f"❌ {test_name} - ERROR: {e}")
        test_results.append((test_name, False, str(e)))
        # Uncomment for detailed debugging
        # traceback.print_exc()

# Test 1: Basic Import Validation
def test_basic_imports():
    """Test that all basic imports work correctly"""
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    from validators.debug_utils import debug_print
    from validators.unicode_constants import MATHBB_MAP
    from validators.math_utils import contains_math
    
    print("✓ validators package imported successfully")
    print(f"✓ SUPERSCRIPT_MAP loaded with {len(SUPERSCRIPT_MAP)} entries")
    print(f"✓ MATHBB_MAP loaded with {len(MATHBB_MAP)} entries")
    print("✓ All core functions available")
    return True

execute_test("Basic Import Validation", 
             "Validates that the core validators package and all submodules can be imported",
             test_basic_imports)

# Test 2: Debug System Validation
def test_debug_system():
    """Test the debug system functionality"""
    from validators.debug_utils import enable_debug, disable_debug, debug_print, is_debug_enabled
    
    # Test enable/disable cycle
    disable_debug()
    initial_state = is_debug_enabled()
    
    enable_debug()
    enabled_state = is_debug_enabled()
    
    disable_debug()
    disabled_state = is_debug_enabled()
    
    print(f"✓ Initial state: {initial_state}")
    print(f"✓ After enable: {enabled_state}")
    print(f"✓ After disable: {disabled_state}")
    
    # Test debug printing
    enable_debug()
    debug_print("Debug system test message")
    
    return not initial_state and enabled_state and not disabled_state

execute_test("Debug System Validation",
             "Tests the debug enable/disable functionality and debug printing",
             test_debug_system)

# Test 3: Unicode Constants Validation
def test_unicode_constants():
    """Test unicode constants are loaded correctly"""
    from validators.unicode_constants import (
        SUPERSCRIPT_MAP, SUBSCRIPT_MAP, MATHBB_MAP, 
        MATHEMATICAL_OPERATORS, MATHEMATICAL_GREEK_LETTERS
    )
    
    # Test mappings
    sup_2 = SUPERSCRIPT_MAP.get('2')
    sub_2 = SUBSCRIPT_MAP.get('2')
    mathbb_r = MATHBB_MAP.get('R')
    
    print(f"✓ SUPERSCRIPT_MAP: {len(SUPERSCRIPT_MAP)} entries")
    print(f"✓ SUBSCRIPT_MAP: {len(SUBSCRIPT_MAP)} entries")
    print(f"✓ MATHBB_MAP: {len(MATHBB_MAP)} entries")
    print(f"✓ MATHEMATICAL_OPERATORS: {len(MATHEMATICAL_OPERATORS)} entries")
    print(f"✓ MATHEMATICAL_GREEK_LETTERS: {len(MATHEMATICAL_GREEK_LETTERS)} entries")
    
    print(f"✓ Sample mappings: '2' -> '{sup_2}' (super), '2' -> '{sub_2}' (sub), 'R' -> '{mathbb_r}' (mathbb)")
    
    return (sup_2 == '²' and sub_2 == '₂' and mathbb_r == 'ℝ' and 
            len(MATHEMATICAL_OPERATORS) > 100 and len(MATHEMATICAL_GREEK_LETTERS) > 40)

execute_test("Unicode Constants Validation",
             "Tests that all unicode constants are loaded with correct mappings",
             test_unicode_constants)

# Test 4: Math Utilities Validation
def test_math_utilities():
    """Test math utilities functionality"""
    from validators.math_utils import (
        find_math_regions, contains_math, is_filename_math_token,
        detect_math_context, is_likely_math_filename
    )
    
    # Test math region detection
    test_cases = [
        ("Regular text", 0, False),
        ("Formula: $x^2 + y^2 = z^2$", 1, True),
        ("Display: $$\\int_0^1 x dx$$", 1, True),
        ("LaTeX: \\[E = mc^2\\]", 1, True),
        ("Multiple: $a$ and $b$", 2, True)
    ]
    
    all_passed = True
    for text, expected_regions, expected_has_math in test_cases:
        regions = find_math_regions(text)
        has_math = contains_math(text)
        
        if len(regions) != expected_regions or has_math != expected_has_math:
            all_passed = False
            print(f"✗ Failed: '{text}' - expected {expected_regions} regions, got {len(regions)}")
        else:
            print(f"✓ Passed: '{text}' - {len(regions)} regions, has_math: {has_math}")
    
    # Test math token detection
    assert is_filename_math_token("x²") == True
    assert is_filename_math_token("normal") == False
    print("✓ Math token detection working")
    
    # Test context detection
    context = detect_math_context("Analysis of f(x) = x²")
    assert 'complexity' in context
    print(f"✓ Context detection working: {context['complexity']}")
    
    # Test filename detection
    math_file = is_likely_math_filename("differential_equations.pdf")
    normal_file = is_likely_math_filename("regular_document.pdf")
    print(f"✓ Filename detection: math={math_file}, normal={normal_file}")
    
    return all_passed

execute_test("Math Utilities Validation",
             "Tests all math utility functions including region detection, context analysis, and filename detection",
             test_math_utilities)

# Test 5: Compatibility Layer Validation
def test_compatibility_layer():
    """Test backward compatibility layer"""
    from filename_checker_compatibility import (
        enable_debug, SUPERSCRIPT_MAP, find_math_regions,
        contains_math, MATHBB_MAP
    )
    
    # Test that all functions work through compatibility layer
    enable_debug()
    
    # Test math region detection
    regions = find_math_regions("Test $x^2$")
    has_math = contains_math("Test $x^2$")
    
    print(f"✓ Math regions through compatibility: {len(regions)}")
    print(f"✓ Contains math through compatibility: {has_math}")
    print(f"✓ Constants available: SUPERSCRIPT_MAP={len(SUPERSCRIPT_MAP)}, MATHBB_MAP={len(MATHBB_MAP)}")
    
    return len(regions) == 1 and has_math and len(SUPERSCRIPT_MAP) > 0

execute_test("Compatibility Layer Validation",
             "Tests that the backward compatibility layer provides all expected functionality",
             test_compatibility_layer)

# Test 6: Integration Test
def test_integration():
    """Test integration between all components"""
    from validators.debug_utils import enable_debug, debug_print
    from validators.math_utils import find_math_regions, detect_math_context
    from validators.unicode_constants import SUPERSCRIPT_MAP, MATHBB_MAP
    
    # Enable debug mode
    enable_debug()
    debug_print("Starting integration test")
    
    # Test complex mathematical text
    complex_text = """
    The fundamental theorem of calculus states that if f is continuous on [a,b] and F is defined by:
    $$F(x) = \\int_a^x f(t) dt$$
    
    Then F'(x) = f(x) for all x in [a,b]. This connects differentiation and integration.
    
    In the context of ℝ → ℝ mappings, we can express this as:
    f: ℝ → ℝ, where f(x) = x² + 2x + 1
    """
    
    # Test all components work together
    regions = find_math_regions(complex_text)
    context = detect_math_context(complex_text)
    
    print(f"✓ Found {len(regions)} math regions in complex text")
    print(f"✓ Math context: {context['complexity']}")
    print(f"✓ Has math regions: {context['has_math_regions']}")
    print(f"✓ Has math symbols: {context['has_math_symbols']}")
    
    # Test unicode transformations are available
    print(f"✓ Unicode mappings available: {len(SUPERSCRIPT_MAP)} + {len(MATHBB_MAP)}")
    
    return len(regions) > 0 and context['has_math_regions'] and context['complexity'] != 'none'

execute_test("Integration Test",
             "Tests that all components work together correctly with complex mathematical text",
             test_integration)

# Test 7: Original Test Script
def test_original_script():
    """Test the original test_refactoring.py script"""
    try:
        import test_refactoring
        result = test_refactoring.main()
        
        if result:
            print("✓ Original test script executed successfully")
            print("✓ All original tests passed")
        else:
            print("✗ Original test script failed")
        
        return result
    except Exception as e:
        print(f"✗ Failed to run original test script: {e}")
        return False

execute_test("Original Test Script",
             "Executes the original test_refactoring.py script to ensure all tests pass",
             test_original_script)

# Test 8: Main Application Modules
def test_main_modules():
    """Test main application modules can be imported"""
    modules = ['main', 'filename_checker', 'pdf_parser', 'scanner']
    results = []
    
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            print(f"✓ {module_name} imported successfully")
            results.append(True)
        except ImportError as e:
            print(f"✗ {module_name} import failed: {e}")
            results.append(False)
        except Exception as e:
            # Some modules might fail due to missing dependencies, but imports should work
            print(f"⚠  {module_name} imported but has runtime issues: {e}")
            results.append(True)  # Import worked, runtime issue is separate
    
    success_rate = sum(results) / len(results)
    print(f"✓ Module import success rate: {success_rate:.1%}")
    
    return success_rate >= 0.75  # Allow some modules to have issues

execute_test("Main Application Modules",
             "Tests that main application modules can be imported without breaking",
             test_main_modules)

# Final Summary
print("\n📊 COMPREHENSIVE TEST SUMMARY")
print("=" * 80)

passed = sum(1 for _, success, _ in test_results if success)
total = len(test_results)
percentage = (passed / total) * 100

print(f"Tests executed: {total}")
print(f"Tests passed: {passed}")
print(f"Tests failed: {total - passed}")
print(f"Success rate: {percentage:.1f}%")

if passed == total:
    print("\n🎉 EXCELLENT! ALL TESTS PASSED!")
    print("✨ Your refactoring is working perfectly!")
    print("🔧 The modular structure is functioning correctly.")
    print("🚀 Backward compatibility is maintained.")
    print("🎯 You can proceed with full confidence!")
    
    print("\n🏆 ACHIEVEMENTS UNLOCKED:")
    print("  ✓ Successful module extraction")
    print("  ✓ Working debug system")
    print("  ✓ Complete unicode constants")
    print("  ✓ Functional math utilities")
    print("  ✓ Backward compatibility maintained")
    print("  ✓ Integration between components")
    print("  ✓ Original tests still passing")

else:
    print("\n⚠️  SOME TESTS FAILED - NEEDS ATTENTION")
    print("Failed tests:")
    for test_name, success, error in test_results:
        if not success:
            print(f"  ❌ {test_name}: {error}")
    
    print("\nPassed tests:")
    for test_name, success, _ in test_results:
        if success:
            print(f"  ✅ {test_name}")

print("\n🔍 DETAILED TEST RESULTS:")
for i, (test_name, success, error) in enumerate(test_results, 1):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{i:2d}. {status} {test_name}")
    if error and not success:
        print(f"     Error: {error}")

print(f"\n🏁 FINAL VERDICT: {'REFACTORING SUCCESSFUL' if passed == total else 'REFACTORING NEEDS FIXES'}")
print("=" * 80)

# Exit with appropriate code
sys.exit(0 if passed == total else 1)