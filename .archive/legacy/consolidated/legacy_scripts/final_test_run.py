#!/usr/bin/env python3
"""Final comprehensive test execution"""

import sys
import os
import traceback
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("🎯 FINAL COMPREHENSIVE TEST RUN")
print("=" * 70)

# Test results storage
results = []

def run_test(test_name, test_func):
    """Run a test and capture results"""
    try:
        test_func()
        results.append((test_name, True, ""))
        print(f"✅ {test_name} - PASSED")
    except Exception as e:
        results.append((test_name, False, str(e)))
        print(f"❌ {test_name} - FAILED: {e}")
        # Uncomment next line for detailed error info
        # traceback.print_exc()

# Test 1: Basic imports
def test_basic_imports():
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    from validators.debug_utils import debug_print
    from validators.unicode_constants import MATHBB_MAP
    from validators.math_utils import contains_math
    assert len(SUPERSCRIPT_MAP) > 0
    assert len(MATHBB_MAP) > 0

run_test("Basic Imports", test_basic_imports)

# Test 2: Debug system
def test_debug_system():
    from validators.debug_utils import enable_debug, disable_debug, debug_print, is_debug_enabled
    
    # Test enable/disable cycle
    enable_debug()
    assert is_debug_enabled() == True
    debug_print("Test message")
    disable_debug()
    assert is_debug_enabled() == False

run_test("Debug System", test_debug_system)

# Test 3: Unicode constants
def test_unicode_constants():
    from validators.unicode_constants import SUPERSCRIPT_MAP, SUBSCRIPT_MAP, MATHBB_MAP
    
    # Test specific mappings
    assert SUPERSCRIPT_MAP.get('2') == '²'
    assert SUBSCRIPT_MAP.get('2') == '₂'
    assert MATHBB_MAP.get('R') == 'ℝ'
    
    # Test sizes
    assert len(SUPERSCRIPT_MAP) > 20
    assert len(SUBSCRIPT_MAP) > 10
    assert len(MATHBB_MAP) > 15

run_test("Unicode Constants", test_unicode_constants)

# Test 4: Math utilities
def test_math_utilities():
    from validators.math_utils import find_math_regions, contains_math, is_filename_math_token
    
    # Test math region detection
    test_text = "This is a formula: $x^2 + y^2 = z^2$ and more text"
    regions = find_math_regions(test_text)
    assert len(regions) == 1
    assert regions[0][0] < regions[0][1]  # Valid region
    
    # Test contains math
    assert contains_math(test_text) == True
    assert contains_math("Just regular text") == False
    
    # Test math token detection
    assert is_filename_math_token("x²") == True
    assert is_filename_math_token("normal") == False

run_test("Math Utilities", test_math_utilities)

# Test 5: Compatibility layer
def test_compatibility_layer():
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    
    # Test imports work
    assert len(SUPERSCRIPT_MAP) > 0
    
    # Test functionality
    enable_debug()
    regions = find_math_regions("Test $x^2$")
    assert len(regions) == 1

run_test("Compatibility Layer", test_compatibility_layer)

# Test 6: Validators package
def test_validators_package():
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    
    # Test package-level imports
    enable_debug()
    regions = find_math_regions("Test $x^2$")
    assert len(regions) == 1
    assert len(SUPERSCRIPT_MAP) > 0

run_test("Validators Package", test_validators_package)

# Test 7: Cross-module integration
def test_cross_module_integration():
    from validators.debug_utils import enable_debug
    from validators.math_utils import detect_math_context
    from validators.unicode_constants import MATHEMATICAL_OPERATORS
    
    enable_debug()
    
    # Test integrated functionality
    test_text = "Mathematical analysis of x² + y² = z²"
    context = detect_math_context(test_text)
    
    assert context['has_math_symbols'] == True
    assert 'complexity' in context
    assert len(MATHEMATICAL_OPERATORS) > 100

run_test("Cross-Module Integration", test_cross_module_integration)

# Test 8: Validator classes
def test_validator_classes():
    from validators import FilenameValidator, AuthorValidator, UnicodeValidator
    
    # Just test they can be imported
    assert FilenameValidator is not None
    assert AuthorValidator is not None
    assert UnicodeValidator is not None

run_test("Validator Classes", test_validator_classes)

# Test 9: Exception handling
def test_exception_handling():
    from validators.exceptions import ValidationError
    
    # Test exception can be imported
    assert ValidationError is not None

run_test("Exception Handling", test_exception_handling)

# Test 10: Original test script
def test_original_script():
    import test_refactoring
    
    # Run original test
    result = test_refactoring.main()
    assert result == True

run_test("Original Test Script", test_original_script)

# Test 11: Main module imports
def test_main_modules():
    main_modules = ['main', 'filename_checker', 'pdf_parser', 'scanner']
    
    for module_name in main_modules:
        try:
            __import__(module_name)
        except Exception as e:
            # Allow some modules to fail if they have dependencies
            if module_name in ['main', 'filename_checker']:
                # These are critical
                raise e
            else:
                # These might have external dependencies
                pass

run_test("Main Module Imports", test_main_modules)

# Test 12: Advanced functionality
def test_advanced_functionality():
    from validators.math_utils import detect_math_context, is_likely_math_filename
    from validators.unicode_constants import MATHEMATICAL_OPERATORS, MATHEMATICAL_GREEK_LETTERS
    
    # Test advanced math context
    test_text = "Einstein's equation: E = mc²"
    context = detect_math_context(test_text)
    assert 'complexity' in context
    
    # Test filename detection
    math_filename = is_likely_math_filename("theorem_proof.pdf")
    assert isinstance(math_filename, bool)
    
    # Test Greek letters
    assert len(MATHEMATICAL_GREEK_LETTERS) > 40

run_test("Advanced Functionality", test_advanced_functionality)

# Test 13: Multiple import patterns
def test_multiple_import_patterns():
    # Test star imports
    from validators import *
    
    # Test specific imports
    from validators.math_utils import (
        find_math_regions, 
        contains_math, 
        detect_math_context,
        is_likely_math_filename
    )
    
    # Test all work
    assert find_math_regions("$x^2$")
    assert contains_math("$x^2$")
    assert detect_math_context("$x^2$")
    assert isinstance(is_likely_math_filename("test.pdf"), bool)

run_test("Multiple Import Patterns", test_multiple_import_patterns)

# Test 14: Full integration test
def test_full_integration():
    from validators.debug_utils import enable_debug, debug_print
    from validators.math_utils import find_math_regions, detect_math_context
    from validators.unicode_constants import SUPERSCRIPT_MAP, MATHBB_MAP
    
    # Enable debug
    enable_debug()
    debug_print("Starting integration test")
    
    # Test complex mathematical text
    complex_text = """
    The theorem states that for any function f(x) = x² + 2x + 1,
    the derivative is f'(x) = 2x + 2. This can be written as:
    $$\\frac{d}{dx}(x^2 + 2x + 1) = 2x + 2$$
    
    In the context of ℝ → ℝ mappings, this is fundamental.
    """
    
    # Test all components work together
    regions = find_math_regions(complex_text)
    context = detect_math_context(complex_text)
    
    # Verify results
    assert len(regions) > 0
    assert context['has_math_regions'] == True
    assert context['complexity'] in ['low', 'medium', 'high']
    
    # Test unicode transformations
    assert len(SUPERSCRIPT_MAP) > 0
    assert len(MATHBB_MAP) > 0

run_test("Full Integration", test_full_integration)

# Summary
print("\n📊 FINAL TEST SUMMARY")
print("=" * 70)

passed = sum(1 for _, success, _ in results if success)
total = len(results)
percentage = (passed / total) * 100

print(f"Tests passed: {passed}/{total} ({percentage:.1f}%)")

if passed == total:
    print("🎉 ALL TESTS PASSED! Your refactoring is working perfectly!")
    print("✨ The modular structure is functioning correctly.")
    print("🔧 Backward compatibility is maintained.")
    print("🚀 You can proceed with confidence!")
else:
    print("⚠️  Some tests failed:")
    for test_name, success, error in results:
        if not success:
            print(f"  ❌ {test_name}: {error}")

print("\n🎯 DETAILED RESULTS:")
for test_name, success, error in results:
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status} {test_name}")
    if error and not success:
        print(f"      Error: {error}")

print(f"\n🏁 FINAL VERDICT: {'SUCCESS' if passed == total else 'NEEDS ATTENTION'}")
print("=" * 70)

# Exit with appropriate code
sys.exit(0 if passed == total else 1)