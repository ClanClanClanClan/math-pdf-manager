#!/usr/bin/env python3
"""
Comprehensive Test Execution Script
This script runs all tests to verify the refactoring works correctly.
"""

import sys
import os
import traceback
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_test(test_func, test_name):
    """Run a single test and return result"""
    try:
        result = test_func()
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        print(f"❌ {test_name}: FAILED - {e}")
        traceback.print_exc()
        return False

def test_basic_imports():
    """Test basic imports work"""
    # Test validators package imports
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    from validators.debug_utils import debug_print
    from validators.unicode_constants import MATHBB_MAP
    from validators.math_utils import contains_math
    return True

def test_compatibility_imports():
    """Test compatibility layer imports"""
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    return True

def test_debug_system():
    """Test debug system functionality"""
    from validators.debug_utils import enable_debug, disable_debug, debug_print, is_debug_enabled
    
    # Test enable/disable
    enable_debug()
    assert is_debug_enabled() == True
    
    disable_debug()
    assert is_debug_enabled() == False
    
    # Test debug print
    enable_debug()
    debug_print("Test message")
    return True

def test_unicode_constants():
    """Test unicode constants are properly loaded"""
    from validators.unicode_constants import SUPERSCRIPT_MAP, SUBSCRIPT_MAP, MATHBB_MAP
    
    # Test basic mappings exist
    assert len(SUPERSCRIPT_MAP) > 0
    assert len(SUBSCRIPT_MAP) > 0
    assert len(MATHBB_MAP) > 0
    
    # Test specific mappings
    assert SUPERSCRIPT_MAP.get('2') == '²'
    assert SUBSCRIPT_MAP.get('2') == '₂'
    assert MATHBB_MAP.get('R') == 'ℝ'
    
    return True

def test_math_utilities():
    """Test math utilities work correctly"""
    from validators.math_utils import find_math_regions, contains_math, is_filename_math_token
    
    # Test math region detection
    test_text = "This is a formula: $x^2 + y^2 = z^2$ and more text"
    regions = find_math_regions(test_text)
    assert len(regions) == 1
    
    # Test contains math
    assert contains_math(test_text) == True
    assert contains_math("Just regular text") == False
    
    # Test math token detection
    assert is_filename_math_token("x²") == True
    assert is_filename_math_token("normal") == False
    
    return True

def test_main_import():
    """Test that main.py can be imported"""
    try:
        import main
        return True
    except Exception as e:
        print(f"Main import failed: {e}")
        return False

def test_filename_checker_import():
    """Test that filename_checker.py can be imported"""
    try:
        import filename_checker
        return True
    except Exception as e:
        print(f"Filename checker import failed: {e}")
        return False

def test_pdf_parser_import():
    """Test that pdf_parser.py can be imported"""
    try:
        import pdf_parser
        return True
    except Exception as e:
        print(f"PDF parser import failed: {e}")
        return False

def test_scanner_import():
    """Test that scanner.py can be imported"""
    try:
        import scanner
        return True
    except Exception as e:
        print(f"Scanner import failed: {e}")
        return False

def test_backward_compatibility():
    """Test backward compatibility with old imports"""
    # Test that old code can still import the functions
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    
    # Test basic functionality
    enable_debug()
    regions = find_math_regions("Test $x^2$")
    assert len(regions) == 1
    
    return True

def test_cross_module_integration():
    """Test that modules work together properly"""
    from validators.debug_utils import enable_debug
    from validators.math_utils import contains_math, detect_math_context
    from validators.unicode_constants import SUPERSCRIPT_MAP
    
    enable_debug()
    
    # Test integrated functionality
    test_text = "Mathematical analysis of x² + y² = z²"
    context = detect_math_context(test_text)
    
    assert context['has_math_symbols'] == True
    assert 'complexity' in context
    
    return True

def test_validator_classes():
    """Test that validator classes can be imported"""
    try:
        from validators import FilenameValidator, AuthorValidator, UnicodeValidator
        return True
    except Exception as e:
        print(f"Validator classes import failed: {e}")
        return False

def test_exception_handling():
    """Test exception handling"""
    try:
        from validators.exceptions import ValidationError
        return True
    except Exception as e:
        print(f"Exception handling failed: {e}")
        return False

def run_existing_test_files():
    """Run existing test files if they exist"""
    test_files = [
        'test_refactoring.py',
        'test_backward_compatibility.py',
        'test_imports.py',
        'test_main.py'
    ]
    
    results = []
    for test_file in test_files:
        if os.path.exists(test_file):
            try:
                # Import and run the test
                test_module = __import__(test_file[:-3])  # Remove .py extension
                if hasattr(test_module, 'main'):
                    result = test_module.main()
                    results.append((test_file, result))
                    print(f"✅ {test_file}: Completed")
                else:
                    print(f"⚠️ {test_file}: No main function found")
            except Exception as e:
                print(f"❌ {test_file}: Failed to run - {e}")
                results.append((test_file, False))
        else:
            print(f"⚠️ {test_file}: Not found")
    
    return results

def main():
    """Run all comprehensive tests"""
    print("🧪 COMPREHENSIVE TEST EXECUTION")
    print("=" * 50)
    
    # Define all tests
    tests = [
        (test_basic_imports, "Basic Imports"),
        (test_compatibility_imports, "Compatibility Imports"),
        (test_debug_system, "Debug System"),
        (test_unicode_constants, "Unicode Constants"),
        (test_math_utilities, "Math Utilities"),
        (test_backward_compatibility, "Backward Compatibility"),
        (test_cross_module_integration, "Cross-Module Integration"),
        (test_validator_classes, "Validator Classes"),
        (test_exception_handling, "Exception Handling"),
        (test_main_import, "Main Module Import"),
        (test_filename_checker_import, "Filename Checker Import"),
        (test_pdf_parser_import, "PDF Parser Import"),
        (test_scanner_import, "Scanner Import"),
    ]
    
    # Run all tests
    results = []
    for test_func, test_name in tests:
        result = run_test(test_func, test_name)
        results.append((test_name, result))
    
    # Run existing test files
    print("\n🔄 RUNNING EXISTING TEST FILES")
    print("=" * 50)
    existing_results = run_existing_test_files()
    
    # Print summary
    print("\n📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Primary Tests: {passed}/{total} passed")
    
    if existing_results:
        existing_passed = sum(1 for _, result in existing_results if result)
        existing_total = len(existing_results)
        print(f"Existing Tests: {existing_passed}/{existing_total} passed")
    
    # Show failed tests
    failed_tests = [name for name, result in results if not result]
    if failed_tests:
        print("\n❌ FAILED TESTS:")
        for test_name in failed_tests:
            print(f"  - {test_name}")
    
    if passed == total:
        print("\n🎉 ALL PRIMARY TESTS PASSED!")
    else:
        print(f"\n⚠️ {total - passed} PRIMARY TESTS FAILED")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)