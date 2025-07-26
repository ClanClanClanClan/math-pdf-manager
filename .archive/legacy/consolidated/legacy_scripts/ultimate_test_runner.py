#!/usr/bin/env python3
"""Ultimate test runner that executes all refactoring tests"""

import sys
import os
import subprocess
import importlib.util
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("🎯 ULTIMATE REFACTORING TEST RUNNER")
print("=" * 80)

# Test execution functions
def execute_python_file(filepath):
    """Execute a Python file and return success/failure"""
    try:
        spec = importlib.util.spec_from_file_location("test_module", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Try to run main function if it exists
        if hasattr(module, 'main'):
            return module.main()
        else:
            return True  # Successfully imported and executed
    except Exception as e:
        print(f"Error executing {filepath}: {e}")
        return False

def test_import_functionality():
    """Test all import functionality manually"""
    print("\n🔍 TESTING IMPORT FUNCTIONALITY")
    print("-" * 50)
    
    test_results = []
    
    # Test 1: Basic validators import
    try:
        from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
        print("✅ Basic validators import - SUCCESS")
        test_results.append(("Basic validators import", True))
    except Exception as e:
        print(f"❌ Basic validators import - FAILED: {e}")
        test_results.append(("Basic validators import", False))
    
    # Test 2: Debug utilities
    try:
        from validators.debug_utils import enable_debug, debug_print, is_debug_enabled
        enable_debug()
        debug_print("Test message")
        print("✅ Debug utilities - SUCCESS")
        test_results.append(("Debug utilities", True))
    except Exception as e:
        print(f"❌ Debug utilities - FAILED: {e}")
        test_results.append(("Debug utilities", False))
    
    # Test 3: Unicode constants
    try:
        from validators.unicode_constants import SUPERSCRIPT_MAP, MATHBB_MAP
        print(f"✅ Unicode constants - SUCCESS ({len(SUPERSCRIPT_MAP)} superscript, {len(MATHBB_MAP)} mathbb)")
        test_results.append(("Unicode constants", True))
    except Exception as e:
        print(f"❌ Unicode constants - FAILED: {e}")
        test_results.append(("Unicode constants", False))
    
    # Test 4: Math utilities
    try:
        from validators.math_utils import find_math_regions, contains_math
        test_text = "Formula: $x^2 + y^2 = z^2$"
        regions = find_math_regions(test_text)
        has_math = contains_math(test_text)
        print(f"✅ Math utilities - SUCCESS (found {len(regions)} regions, has_math: {has_math})")
        test_results.append(("Math utilities", True))
    except Exception as e:
        print(f"❌ Math utilities - FAILED: {e}")
        test_results.append(("Math utilities", False))
    
    # Test 5: Compatibility layer
    try:
        from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
        print("✅ Compatibility layer - SUCCESS")
        test_results.append(("Compatibility layer", True))
    except Exception as e:
        print(f"❌ Compatibility layer - FAILED: {e}")
        test_results.append(("Compatibility layer", False))
    
    return test_results

def test_main_application_modules():
    """Test main application modules"""
    print("\n🏗️ TESTING MAIN APPLICATION MODULES")
    print("-" * 50)
    
    modules = ['main', 'filename_checker', 'pdf_parser', 'scanner', 'metadata_fetcher']
    results = []
    
    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
            print(f"✅ {module_name} - SUCCESS")
            results.append((module_name, True))
        except Exception as e:
            print(f"❌ {module_name} - FAILED: {e}")
            results.append((module_name, False))
    
    return results

def test_comprehensive_functionality():
    """Test comprehensive functionality"""
    print("\n⚙️ TESTING COMPREHENSIVE FUNCTIONALITY")
    print("-" * 50)
    
    test_results = []
    
    try:
        # Test integrated workflow
        from validators.debug_utils import enable_debug
        from validators.math_utils import detect_math_context, is_likely_math_filename
        from validators.unicode_constants import MATHEMATICAL_OPERATORS
        
        enable_debug()
        
        # Test math context detection
        test_text = "Einstein's equation: E = mc²"
        context = detect_math_context(test_text)
        
        # Test filename detection
        math_filename_result = is_likely_math_filename("differential_equations.pdf")
        
        print(f"✅ Comprehensive functionality - SUCCESS")
        print(f"   Math context: {context.get('complexity', 'unknown')}")
        print(f"   Math filename detection: {math_filename_result}")
        print(f"   Math operators available: {len(MATHEMATICAL_OPERATORS)}")
        
        test_results.append(("Comprehensive functionality", True))
        
    except Exception as e:
        print(f"❌ Comprehensive functionality - FAILED: {e}")
        test_results.append(("Comprehensive functionality", False))
    
    return test_results

def run_original_tests():
    """Run original test files"""
    print("\n📋 RUNNING ORIGINAL TEST FILES")
    print("-" * 50)
    
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
                print(f"Running {test_file}...")
                result = execute_python_file(test_file)
                status = "SUCCESS" if result else "FAILED"
                print(f"✅ {test_file} - {status}")
                results.append((test_file, result))
            except Exception as e:
                print(f"❌ {test_file} - FAILED: {e}")
                results.append((test_file, False))
        else:
            print(f"⚠️  {test_file} - NOT FOUND")
            results.append((test_file, None))
    
    return results

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n🎪 TESTING EDGE CASES")
    print("-" * 50)
    
    test_results = []
    
    try:
        from validators.math_utils import find_math_regions, contains_math
        from validators.unicode_constants import SUPERSCRIPT_MAP
        
        # Test empty string
        empty_regions = find_math_regions("")
        assert empty_regions == []
        
        # Test no math
        no_math_regions = find_math_regions("Just regular text")
        assert no_math_regions == []
        
        # Test complex math
        complex_math = "$$\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}$$"
        complex_regions = find_math_regions(complex_math)
        assert len(complex_regions) > 0
        
        # Test unicode mappings
        assert '²' in SUPERSCRIPT_MAP.values()
        
        print("✅ Edge cases - SUCCESS")
        test_results.append(("Edge cases", True))
        
    except Exception as e:
        print(f"❌ Edge cases - FAILED: {e}")
        test_results.append(("Edge cases", False))
    
    return test_results

def main():
    """Main test runner"""
    all_results = []
    
    # Run all test categories
    print("🚀 STARTING COMPREHENSIVE TEST EXECUTION")
    
    # Test 1: Import functionality
    import_results = test_import_functionality()
    all_results.extend(import_results)
    
    # Test 2: Main application modules
    main_results = test_main_application_modules()
    all_results.extend(main_results)
    
    # Test 3: Comprehensive functionality
    comp_results = test_comprehensive_functionality()
    all_results.extend(comp_results)
    
    # Test 4: Edge cases
    edge_results = test_edge_cases()
    all_results.extend(edge_results)
    
    # Test 5: Original test files
    original_results = run_original_tests()
    all_results.extend(original_results)
    
    # Calculate overall results
    print("\n📊 OVERALL TEST RESULTS")
    print("=" * 80)
    
    passed = sum(1 for _, result in all_results if result is True)
    failed = sum(1 for _, result in all_results if result is False)
    not_found = sum(1 for _, result in all_results if result is None)
    total = len(all_results)
    
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    print(f"Tests not found: {not_found}")
    print(f"Total tests: {total}")
    
    if failed == 0:
        print("🎉 ALL AVAILABLE TESTS PASSED!")
        print("✨ Your refactoring is working correctly!")
        print("🔧 The modular structure is functioning properly.")
        print("🚀 You can proceed with confidence!")
    else:
        print("⚠️  Some tests failed. Here's what needs attention:")
        for test_name, result in all_results:
            if result is False:
                print(f"  ❌ {test_name}")
    
    # Detailed breakdown
    print("\n🎯 DETAILED BREAKDOWN")
    print("-" * 50)
    
    categories = {
        'Import Tests': import_results,
        'Main Module Tests': main_results,
        'Functionality Tests': comp_results,
        'Edge Case Tests': edge_results,
        'Original Tests': original_results
    }
    
    for category, results in categories.items():
        passed_in_category = sum(1 for _, result in results if result is True)
        total_in_category = len(results)
        percentage = (passed_in_category / total_in_category * 100) if total_in_category > 0 else 0
        
        print(f"{category}: {passed_in_category}/{total_in_category} ({percentage:.1f}%)")
    
    print(f"\n🏁 FINAL ASSESSMENT: {'EXCELLENT' if failed == 0 else 'NEEDS ATTENTION'}")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)