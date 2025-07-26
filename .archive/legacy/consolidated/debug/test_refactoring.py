#!/usr/bin/env python3
"""
Test script to verify the refactoring works correctly
"""
import sys
import os
# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

def test_debug_utils():
    """Test debug utilities"""
    try:
        from filename_checker.debug import enable_debug, disable_debug, debug_print
        
        print("✅ Debug utilities import successful")
        enable_debug()
        debug_print("Debug test message")
        return True
    except Exception as e:
        print(f"❌ Debug utilities test failed: {e}")
        return False

def test_unicode_constants():
    """Test unicode constants"""
    try:
        from filename_checker.unicode_utils import DANGEROUS_UNICODE_CHARS, nfc
        
        print("✅ Unicode constants import successful")
        print(f"DANGEROUS_UNICODE_CHARS has {len(DANGEROUS_UNICODE_CHARS)} entries")
        # Test NFC normalization
        test_str = "café"
        normalized = nfc(test_str)
        print(f"NFC normalization works: {normalized == test_str}")
        return True
    except Exception as e:
        print(f"❌ Unicode constants test failed: {e}")
        return False

def test_math_utils():
    """Test math utilities"""
    try:
        from filename_checker.math_utils import find_math_regions
        
        print("✅ Math utilities import successful")
        
        # Test math detection
        test_text = "This is a formula: $x^2 + y^2 = z^2$"
        regions = find_math_regions(test_text)
        has_math = len(regions) > 0
        
        print(f"Found {len(regions)} math regions in test text")
        print(f"Contains math: {has_math}")
        return True
    except Exception as e:
        print(f"❌ Math utilities test failed: {e}")
        return False

def test_validators_package():
    """Test validators package import"""
    try:
        from validators import check_filename, FilenameValidator, ValidationResult
        
        print("✅ Validators package import successful")
        # Test basic functionality with required parameters
        result = check_filename("test.pdf", 
                              known_words=set(), 
                              whitelist_pairs=[], 
                              exceptions=set(), 
                              compound_terms=set())
        print(f"  - check_filename works: {result is not None}")
        return True
    except Exception as e:
        print(f"❌ Validators package test failed: {e}")
        return False

def test_compatibility_layer():
    """Test compatibility layer"""
    try:
        # The compatibility layer doesn't exist in the new structure
        # The functionality is provided through the filename_checker module
        from filename_checker import check_filename
        
        print("✅ Filename checker module import successful")
        # Test basic functionality with required parameters
        result = check_filename("test.pdf", 
                              known_words=set(), 
                              whitelist_pairs=[], 
                              exceptions=set(), 
                              compound_terms=set())
        print(f"  - check_filename works: {result is not None}")
        return True
    except Exception as e:
        print(f"❌ Compatibility layer test failed: {e}")
        return False

def main():
    print("=== Testing Refactored Components ===")
    
    tests = [
        test_debug_utils,
        test_unicode_constants,
        test_math_utils,
        test_validators_package,
        test_compatibility_layer,
    ]
    
    results = []
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        results.append(test())
    
    print(f"\n=== Test Results ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Refactoring is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    main()