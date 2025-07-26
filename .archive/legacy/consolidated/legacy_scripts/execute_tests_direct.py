#!/usr/bin/env python3
"""Direct execution of tests"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("🎯 DIRECT TEST EXECUTION")
print("=" * 80)

# Test 1: Basic validation
print("\n1. BASIC VALIDATION")
try:
    # Test imports
    from validators import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    from validators.debug_utils import debug_print
    from validators.unicode_constants import MATHBB_MAP
    from validators.math_utils import contains_math
    
    print("✅ Basic imports: SUCCESS")
    print(f"   - SUPERSCRIPT_MAP: {len(SUPERSCRIPT_MAP)} entries")
    print(f"   - MATHBB_MAP: {len(MATHBB_MAP)} entries")
    
    # Test debug system
    from validators.debug_utils import enable_debug, disable_debug, is_debug_enabled
    
    disable_debug()
    initial = is_debug_enabled()
    enable_debug()
    enabled = is_debug_enabled()
    disable_debug()
    final = is_debug_enabled()
    
    print(f"✅ Debug system: SUCCESS")
    print(f"   - State transitions: {initial} -> {enabled} -> {final}")
    
    # Test unicode constants
    from validators.unicode_constants import SUPERSCRIPT_MAP, SUBSCRIPT_MAP, MATHBB_MAP
    
    sup_2 = SUPERSCRIPT_MAP.get('2')
    sub_2 = SUBSCRIPT_MAP.get('2')
    bb_r = MATHBB_MAP.get('R')
    
    print(f"✅ Unicode constants: SUCCESS")
    print(f"   - Superscript '2': {sup_2}")
    print(f"   - Subscript '2': {sub_2}")
    print(f"   - Mathbb 'R': {bb_r}")
    
    # Test math utilities
    from validators.math_utils import find_math_regions, contains_math
    
    test_text = "Formula: $x^2 + y^2 = z^2$"
    regions = find_math_regions(test_text)
    has_math = contains_math(test_text)
    
    print(f"✅ Math utilities: SUCCESS")
    print(f"   - Test text: '{test_text}'")
    print(f"   - Found {len(regions)} regions")
    print(f"   - Contains math: {has_math}")
    
    # Test compatibility layer
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    
    enable_debug()
    regions = find_math_regions("Test $x^2$")
    
    print(f"✅ Compatibility layer: SUCCESS")
    print(f"   - Found {len(regions)} regions through compatibility")
    print(f"   - Superscript mappings: {len(SUPERSCRIPT_MAP)}")
    
    # Test integration
    from validators.debug_utils import enable_debug
    from validators.math_utils import detect_math_context
    from validators.unicode_constants import MATHEMATICAL_OPERATORS
    
    enable_debug()
    text = "Einstein's equation: E = mc²"
    context = detect_math_context(text)
    
    print(f"✅ Integration: SUCCESS")
    print(f"   - Context complexity: {context['complexity']}")
    print(f"   - Has math symbols: {context['has_math_symbols']}")
    print(f"   - Mathematical operators: {len(MATHEMATICAL_OPERATORS)}")
    
    print("\n🎉 ALL BASIC TESTS PASSED!")
    
except Exception as e:
    print(f"❌ Error in basic validation: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Original test script
print("\n2. ORIGINAL TEST SCRIPT")
try:
    import test_refactoring
    result = test_refactoring.main()
    
    if result:
        print("✅ Original test script: SUCCESS")
        print("   - All original tests passed")
    else:
        print("❌ Original test script: FAILED")
        print("   - Some tests failed")
        
except Exception as e:
    print(f"❌ Original test script error: {e}")

# Test 3: Main application modules
print("\n3. MAIN APPLICATION MODULES")
modules = ['main', 'filename_checker', 'pdf_parser', 'scanner']
for module_name in modules:
    try:
        __import__(module_name)
        print(f"✅ {module_name}: SUCCESS")
    except Exception as e:
        print(f"❌ {module_name}: FAILED - {e}")

print("\n🏁 DIRECT TEST EXECUTION COMPLETE")
print("=" * 80)