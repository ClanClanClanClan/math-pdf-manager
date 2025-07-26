#!/usr/bin/env python3
"""Manual execution of test_refactoring.py tests"""

import sys
import os
import traceback

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("🔧 MANUAL TEST EXECUTION")
print("=" * 50)

def manual_test_debug_utils():
    """Manual test of debug utilities"""
    print("\n🧪 Testing debug utilities...")
    try:
        from validators.debug_utils import enable_debug, debug_print
        
        print("✅ Debug utilities import successful")
        enable_debug()
        debug_print("Debug test message")
        return True
    except Exception as e:
        print(f"❌ Debug utilities test failed: {e}")
        traceback.print_exc()
        return False

def manual_test_unicode_constants():
    """Manual test of unicode constants"""
    print("\n🧪 Testing unicode constants...")
    try:
        from validators.unicode_constants import SUPERSCRIPT_MAP, MATHBB_MAP
        
        print("✅ Unicode constants import successful")
        print(f"SUPERSCRIPT_MAP has {len(SUPERSCRIPT_MAP)} entries")
        print(f"MATHBB_MAP has {len(MATHBB_MAP)} entries")
        
        # Test specific mappings
        print(f"Sample: '2' -> '{SUPERSCRIPT_MAP.get('2')}'")
        print(f"Sample: 'R' -> '{MATHBB_MAP.get('R')}'")
        return True
    except Exception as e:
        print(f"❌ Unicode constants test failed: {e}")
        traceback.print_exc()
        return False

def manual_test_math_utils():
    """Manual test of math utilities"""
    print("\n🧪 Testing math utilities...")
    try:
        from validators.math_utils import find_math_regions, contains_math
        
        print("✅ Math utilities import successful")
        
        # Test math detection
        test_text = "This is a formula: $x^2 + y^2 = z^2$"
        regions = find_math_regions(test_text)
        has_math = contains_math(test_text)
        
        print(f"Found {len(regions)} math regions in test text")
        print(f"Contains math: {has_math}")
        print(f"Math regions: {regions}")
        return True
    except Exception as e:
        print(f"❌ Math utilities test failed: {e}")
        traceback.print_exc()
        return False

def manual_test_validators_package():
    """Manual test of validators package"""
    print("\n🧪 Testing validators package...")
    try:
        from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
        
        print("✅ Validators package import successful")
        
        # Test basic functionality
        enable_debug()
        test_text = "Test $x^2$"
        regions = find_math_regions(test_text)
        print(f"Package test: found {len(regions)} regions")
        return True
    except Exception as e:
        print(f"❌ Validators package test failed: {e}")
        traceback.print_exc()
        return False

def manual_test_compatibility_layer():
    """Manual test of compatibility layer"""
    print("\n🧪 Testing compatibility layer...")
    try:
        from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
        
        print("✅ Compatibility layer import successful")
        
        # Test basic functionality
        enable_debug()
        test_text = "Test $x^2$"
        regions = find_math_regions(test_text)
        print(f"Compatibility test: found {len(regions)} regions")
        return True
    except Exception as e:
        print(f"❌ Compatibility layer test failed: {e}")
        traceback.print_exc()
        return False

def manual_test_main_modules():
    """Manual test of main modules"""
    print("\n🧪 Testing main modules...")
    main_modules = ['main', 'filename_checker', 'pdf_parser', 'scanner']
    results = []
    
    for module_name in main_modules:
        try:
            module = __import__(module_name)
            print(f"✅ {module_name} imported successfully")
            results.append(True)
        except Exception as e:
            print(f"❌ {module_name} import failed: {e}")
            results.append(False)
    
    return all(results)

def manual_test_detailed_functionality():
    """Detailed functionality test"""
    print("\n🧪 Testing detailed functionality...")
    try:
        from validators.debug_utils import enable_debug, disable_debug, is_debug_enabled
        from validators.math_utils import detect_math_context
        from validators.unicode_constants import MATHEMATICAL_OPERATORS
        
        # Test debug system
        enable_debug()
        assert is_debug_enabled() == True
        print("✓ Debug enable works")
        
        disable_debug()
        assert is_debug_enabled() == False
        print("✓ Debug disable works")
        
        # Test math context detection
        test_text = "Einstein's famous equation: E = mc²"
        context = detect_math_context(test_text)
        print(f"✓ Math context detection works: {context}")
        
        # Test unicode constants
        print(f"✓ Mathematical operators loaded: {len(MATHEMATICAL_OPERATORS)} symbols")
        
        return True
    except Exception as e:
        print(f"❌ Detailed functionality test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all manual tests"""
    print("🚀 RUNNING ALL MANUAL TESTS")
    
    tests = [
        ("Debug Utils", manual_test_debug_utils),
        ("Unicode Constants", manual_test_unicode_constants),
        ("Math Utils", manual_test_math_utils),
        ("Validators Package", manual_test_validators_package),
        ("Compatibility Layer", manual_test_compatibility_layer),
        ("Main Modules", manual_test_main_modules),
        ("Detailed Functionality", manual_test_detailed_functionality),
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n📊 MANUAL TEST SUMMARY")
    print("=" * 50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL MANUAL TESTS PASSED!")
        print("🔧 Your refactoring is working correctly!")
    else:
        print("⚠️  Some manual tests failed:")
        for test_name, result in results:
            if not result:
                print(f"  - {test_name}")
    
    print("\n🎯 SPECIFIC TEST RESULTS:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    print(f"\nManual test execution complete. Success: {success}")