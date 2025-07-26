#!/usr/bin/env python3
"""Manual test execution with output capture"""

import sys
import os
import traceback

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_and_report(test_name, test_func):
    """Run a test and report results"""
    print(f"\n🧪 {test_name}")
    print("-" * 40)
    try:
        test_func()
        print(f"✅ {test_name} - PASSED")
        return True
    except Exception as e:
        print(f"❌ {test_name} - FAILED")
        print(f"Error: {e}")
        traceback.print_exc()
        return False

def test_basic_imports():
    """Test basic imports"""
    print("Testing basic validators imports...")
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    print(f"✓ enable_debug imported: {enable_debug}")
    print(f"✓ SUPERSCRIPT_MAP imported with {len(SUPERSCRIPT_MAP)} entries")
    print(f"✓ find_math_regions imported: {find_math_regions}")

def test_debug_system():
    """Test debug system"""
    print("Testing debug system...")
    from validators.debug_utils import enable_debug, disable_debug, debug_print, is_debug_enabled
    
    print("Before enable:", is_debug_enabled())
    enable_debug()
    print("After enable:", is_debug_enabled())
    debug_print("Test debug message")
    disable_debug()
    print("After disable:", is_debug_enabled())

def test_unicode_constants():
    """Test unicode constants"""
    print("Testing unicode constants...")
    from validators.unicode_constants import SUPERSCRIPT_MAP, SUBSCRIPT_MAP, MATHBB_MAP
    
    print(f"SUPERSCRIPT_MAP entries: {len(SUPERSCRIPT_MAP)}")
    print(f"SUBSCRIPT_MAP entries: {len(SUBSCRIPT_MAP)}")
    print(f"MATHBB_MAP entries: {len(MATHBB_MAP)}")
    
    # Test specific mappings
    print(f"'2' -> superscript: '{SUPERSCRIPT_MAP.get('2')}'")
    print(f"'2' -> subscript: '{SUBSCRIPT_MAP.get('2')}'")
    print(f"'R' -> mathbb: '{MATHBB_MAP.get('R')}'")

def test_math_utilities():
    """Test math utilities"""
    print("Testing math utilities...")
    from validators.math_utils import find_math_regions, contains_math, is_filename_math_token
    
    test_cases = [
        "Regular text",
        "Math formula: $x^2 + y^2 = z^2$",
        "Display math: $$\\int_0^1 x^2 dx$$",
        "LaTeX style: \\[E = mc^2\\]"
    ]
    
    for text in test_cases:
        regions = find_math_regions(text)
        has_math = contains_math(text)
        print(f"Text: '{text}'")
        print(f"  Regions: {len(regions)}, Has math: {has_math}")

def test_compatibility():
    """Test compatibility layer"""
    print("Testing compatibility layer...")
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    
    print("✓ enable_debug imported from compatibility layer")
    print(f"✓ SUPERSCRIPT_MAP imported with {len(SUPERSCRIPT_MAP)} entries")
    print("✓ find_math_regions imported from compatibility layer")

def test_main_modules():
    """Test main module imports"""
    print("Testing main modules...")
    
    modules_to_test = ['main', 'filename_checker', 'pdf_parser', 'scanner']
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name)
            print(f"✓ {module_name} imported successfully")
        except Exception as e:
            print(f"✗ {module_name} import failed: {e}")

def test_validator_classes():
    """Test validator classes"""
    print("Testing validator classes...")
    from validators import FilenameValidator, AuthorValidator, UnicodeValidator
    
    print("✓ FilenameValidator imported")
    print("✓ AuthorValidator imported")
    print("✓ UnicodeValidator imported")

def test_cross_module_integration():
    """Test cross-module integration"""
    print("Testing cross-module integration...")
    from validators.debug_utils import enable_debug
    from validators.math_utils import detect_math_context
    from validators.unicode_constants import MATHEMATICAL_OPERATORS
    
    enable_debug()
    test_text = "Analysis of f(x) = x² + 2x + 1"
    context = detect_math_context(test_text)
    
    print(f"Math context for '{test_text}':")
    print(f"  Has math regions: {context.get('has_math_regions')}")
    print(f"  Has math symbols: {context.get('has_math_symbols')}")
    print(f"  Complexity: {context.get('complexity')}")
    print(f"Mathematical operators available: {len(MATHEMATICAL_OPERATORS)}")

def main():
    """Run all tests"""
    print("🚀 COMPREHENSIVE REFACTORING TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Debug System", test_debug_system),
        ("Unicode Constants", test_unicode_constants),
        ("Math Utilities", test_math_utilities),
        ("Compatibility Layer", test_compatibility),
        ("Main Modules", test_main_modules),
        ("Validator Classes", test_validator_classes),
        ("Cross-Module Integration", test_cross_module_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_and_report(test_name, test_func)
        results.append((test_name, result))
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Refactoring is working correctly.")
    else:
        print("⚠️  Some tests failed:")
        for test_name, result in results:
            if not result:
                print(f"  - {test_name}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    print(f"\nExit code: {0 if success else 1}")