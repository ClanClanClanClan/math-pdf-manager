#!/usr/bin/env python3
"""Execute refactoring tests by importing and running them"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Capture execution results
execution_log = []

def log_result(test_name, success, details=""):
    """Log test results"""
    status = "✅ PASS" if success else "❌ FAIL"
    execution_log.append((test_name, success, details))
    print(f"{status} {test_name}")
    if details:
        print(f"    {details}")

print("🚀 EXECUTING REFACTORING TESTS")
print("=" * 60)

# Test 1: Import validators package
print("\n1. Testing validators package import...")
try:
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    log_result("Validators Package Import", True, f"SUPERSCRIPT_MAP has {len(SUPERSCRIPT_MAP)} entries")
except Exception as e:
    log_result("Validators Package Import", False, str(e))

# Test 2: Import debug utils
print("\n2. Testing debug utils import...")
try:
    from validators.debug_utils import enable_debug, debug_print
    log_result("Debug Utils Import", True)
except Exception as e:
    log_result("Debug Utils Import", False, str(e))

# Test 3: Import unicode constants
print("\n3. Testing unicode constants import...")
try:
    from validators.unicode_constants import SUPERSCRIPT_MAP, MATHBB_MAP
    log_result("Unicode Constants Import", True, f"SUPERSCRIPT_MAP: {len(SUPERSCRIPT_MAP)}, MATHBB_MAP: {len(MATHBB_MAP)}")
except Exception as e:
    log_result("Unicode Constants Import", False, str(e))

# Test 4: Import math utils
print("\n4. Testing math utils import...")
try:
    from validators.math_utils import find_math_regions, contains_math
    log_result("Math Utils Import", True)
except Exception as e:
    log_result("Math Utils Import", False, str(e))

# Test 5: Import compatibility layer
print("\n5. Testing compatibility layer import...")
try:
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    log_result("Compatibility Layer Import", True)
except Exception as e:
    log_result("Compatibility Layer Import", False, str(e))

# Test 6: Execute debug functionality test
print("\n6. Testing debug functionality...")
try:
    from validators.debug_utils import enable_debug, disable_debug, debug_print, is_debug_enabled
    
    # Test enable/disable
    enable_debug()
    debug_enabled = is_debug_enabled()
    debug_print("Debug test message")
    disable_debug()
    debug_disabled = not is_debug_enabled()
    
    success = debug_enabled and debug_disabled
    log_result("Debug Functionality", success, f"Enable: {debug_enabled}, Disable: {debug_disabled}")
except Exception as e:
    log_result("Debug Functionality", False, str(e))

# Test 7: Execute unicode constants test
print("\n7. Testing unicode constants functionality...")
try:
    from validators.unicode_constants import SUPERSCRIPT_MAP, MATHBB_MAP
    
    # Test specific mappings
    sup_2 = SUPERSCRIPT_MAP.get('2')
    mathbb_r = MATHBB_MAP.get('R')
    
    success = sup_2 == '²' and mathbb_r == 'ℝ'
    log_result("Unicode Constants Functionality", success, f"'2' -> '{sup_2}', 'R' -> '{mathbb_r}'")
except Exception as e:
    log_result("Unicode Constants Functionality", False, str(e))

# Test 8: Execute math utils test
print("\n8. Testing math utils functionality...")
try:
    from validators.math_utils import find_math_regions, contains_math
    
    # Test math detection
    test_text = "This is a formula: $x^2 + y^2 = z^2$"
    regions = find_math_regions(test_text)
    has_math = contains_math(test_text)
    
    success = len(regions) > 0 and has_math
    log_result("Math Utils Functionality", success, f"Found {len(regions)} regions, has_math: {has_math}")
except Exception as e:
    log_result("Math Utils Functionality", False, str(e))

# Test 9: Execute validators package functionality
print("\n9. Testing validators package functionality...")
try:
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    
    enable_debug()
    test_text = "Test $x^2$"
    regions = find_math_regions(test_text)
    
    success = len(regions) > 0
    log_result("Validators Package Functionality", success, f"Found {len(regions)} regions")
except Exception as e:
    log_result("Validators Package Functionality", False, str(e))

# Test 10: Execute compatibility layer functionality
print("\n10. Testing compatibility layer functionality...")
try:
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    
    enable_debug()
    test_text = "Test $x^2$"
    regions = find_math_regions(test_text)
    
    success = len(regions) > 0
    log_result("Compatibility Layer Functionality", success, f"Found {len(regions)} regions")
except Exception as e:
    log_result("Compatibility Layer Functionality", False, str(e))

# Test 11: Execute original test script
print("\n11. Testing original test script...")
try:
    import test_refactoring
    
    # Try to run the main function
    result = test_refactoring.main()
    log_result("Original Test Script", result, f"test_refactoring.main() returned: {result}")
except Exception as e:
    log_result("Original Test Script", False, str(e))

# Test 12: Test main module imports
print("\n12. Testing main module imports...")
modules_to_test = ['main', 'filename_checker', 'pdf_parser', 'scanner']
main_module_results = []

for module_name in modules_to_test:
    try:
        module = __import__(module_name)
        main_module_results.append(True)
        print(f"    ✅ {module_name} imported successfully")
    except Exception as e:
        main_module_results.append(False)
        print(f"    ❌ {module_name} import failed: {e}")

main_modules_success = all(main_module_results)
log_result("Main Module Imports", main_modules_success, f"{sum(main_module_results)}/{len(main_module_results)} modules imported")

# Test 13: Advanced functionality test
print("\n13. Testing advanced functionality...")
try:
    from validators.math_utils import detect_math_context, is_likely_math_filename
    from validators.unicode_constants import MATHEMATICAL_OPERATORS
    
    # Test math context detection
    test_text = "Einstein's equation: E = mc²"
    context = detect_math_context(test_text)
    
    # Test filename detection
    math_filename = is_likely_math_filename("theorem_proof.pdf")
    
    success = 'complexity' in context and isinstance(math_filename, bool)
    log_result("Advanced Functionality", success, f"Context: {context['complexity']}, Math filename: {math_filename}")
except Exception as e:
    log_result("Advanced Functionality", False, str(e))

# Summary
print("\n📊 EXECUTION SUMMARY")
print("=" * 60)

passed_tests = sum(1 for _, success, _ in execution_log if success)
total_tests = len(execution_log)
success_rate = (passed_tests / total_tests) * 100

print(f"Tests passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

if passed_tests == total_tests:
    print("🎉 ALL TESTS PASSED! Your refactoring is working perfectly!")
else:
    print("⚠️  Some tests failed. Details:")
    for test_name, success, details in execution_log:
        if not success:
            print(f"  ❌ {test_name}: {details}")

print("\n🎯 DETAILED RESULTS:")
for test_name, success, details in execution_log:
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status} {test_name}")
    if details:
        print(f"      {details}")

print(f"\n🏁 EXECUTION COMPLETE - Success Rate: {success_rate:.1f}%")
print("=" * 60)

# Return success/failure
success = passed_tests == total_tests
print(f"Overall result: {'SUCCESS' if success else 'FAILURE'}")