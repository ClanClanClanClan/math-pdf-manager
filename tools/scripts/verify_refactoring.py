#!/usr/bin/env python3
"""Verify refactoring by checking all components"""

import sys
import os
import importlib.util

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("🔍 REFACTORING VERIFICATION")
print("=" * 60)

def check_file_exists(filepath):
    """Check if a file exists"""
    exists = os.path.exists(filepath)
    print(f"{'✅' if exists else '❌'} {filepath}")
    return exists

def check_module_import(module_name, items_to_check=None):
    """Check if a module can be imported"""
    try:
        module = importlib.import_module(module_name)
        print(f"✅ {module_name} - imported successfully")
        
        if items_to_check:
            for item in items_to_check:
                if hasattr(module, item):
                    print(f"   ✓ {item} available")
                else:
                    print(f"   ✗ {item} missing")
        
        return True
    except Exception as e:
        print(f"❌ {module_name} - import failed: {e}")
        return False

def check_function_call(module_name, function_name, *args, **kwargs):
    """Check if a function can be called"""
    try:
        module = importlib.import_module(module_name)
        func = getattr(module, function_name)
        result = func(*args, **kwargs)
        print(f"✅ {module_name}.{function_name}() - works, result: {result}")
        return True
    except Exception as e:
        print(f"❌ {module_name}.{function_name}() - failed: {e}")
        return False

# Check file structure
print("\n📁 FILE STRUCTURE CHECK")
print("-" * 30)

files_to_check = [
    "validators/__init__.py",
    "validators/debug_utils.py",
    "validators/unicode_constants.py",
    "validators/math_utils.py",
    "validators/author.py",
    "validators/filename.py",
    "validators/unicode.py",
    "validators/exceptions.py",
    "validators/math_context.py",
    "filename_checker_compatibility.py",
    "test_refactoring.py",
    "main.py",
    "filename_checker.py",
    "pdf_parser.py",
    "scanner.py"
]

file_results = []
for filepath in files_to_check:
    result = check_file_exists(filepath)
    file_results.append((filepath, result))

# Check module imports
print("\n🔧 MODULE IMPORT CHECK")
print("-" * 30)

modules_to_check = [
    ("validators", ["enable_debug", "SUPERSCRIPT_MAP", "find_math_regions"]),
    ("validators.debug_utils", ["enable_debug", "debug_print", "is_debug_enabled"]),
    ("validators.unicode_constants", ["SUPERSCRIPT_MAP", "MATHBB_MAP", "SUBSCRIPT_MAP"]),
    ("validators.math_utils", ["find_math_regions", "contains_math", "detect_math_context"]),
    ("filename_checker_compatibility", ["enable_debug", "SUPERSCRIPT_MAP", "find_math_regions"]),
]

import_results = []
for module_name, items in modules_to_check:
    result = check_module_import(module_name, items)
    import_results.append((module_name, result))

# Check core application modules
print("\n🏗️ CORE APPLICATION MODULE CHECK")
print("-" * 30)

core_modules = ["main", "filename_checker", "pdf_parser", "scanner"]
core_results = []
for module_name in core_modules:
    result = check_module_import(module_name)
    core_results.append((module_name, result))

# Test basic functionality
print("\n⚙️ FUNCTIONALITY TEST")
print("-" * 30)

functionality_results = []

# Test debug system
try:
    from validators.debug_utils import enable_debug, is_debug_enabled
    enable_debug()
    debug_enabled = is_debug_enabled()
    print(f"✅ Debug system - enable works: {debug_enabled}")
    functionality_results.append(("Debug System", True))
except Exception as e:
    print(f"❌ Debug system - failed: {e}")
    functionality_results.append(("Debug System", False))

# Test math utilities
try:
    from validators.math_utils import find_math_regions, contains_math
    test_text = "Mathematical formula: $x^2 + y^2 = z^2$"
    regions = find_math_regions(test_text)
    has_math = contains_math(test_text)
    print(f"✅ Math utilities - found {len(regions)} regions, has_math: {has_math}")
    functionality_results.append(("Math Utilities", True))
except Exception as e:
    print(f"❌ Math utilities - failed: {e}")
    functionality_results.append(("Math Utilities", False))

# Test unicode constants
try:
    from validators.unicode_constants import SUPERSCRIPT_MAP, MATHBB_MAP
    sup_2 = SUPERSCRIPT_MAP.get('2')
    mathbb_r = MATHBB_MAP.get('R')
    print(f"✅ Unicode constants - sup_2: '{sup_2}', mathbb_r: '{mathbb_r}'")
    functionality_results.append(("Unicode Constants", True))
except Exception as e:
    print(f"❌ Unicode constants - failed: {e}")
    functionality_results.append(("Unicode Constants", False))

# Test compatibility layer
try:
    from filename_checker_compatibility import enable_debug, SUPERSCRIPT_MAP, find_math_regions
    test_regions = find_math_regions("Test $x^2$")
    print(f"✅ Compatibility layer - found {len(test_regions)} regions")
    functionality_results.append(("Compatibility Layer", True))
except Exception as e:
    print(f"❌ Compatibility layer - failed: {e}")
    functionality_results.append(("Compatibility Layer", False))

# Test original test script
print("\n📋 ORIGINAL TEST SCRIPT")
print("-" * 30)

try:
    import test_refactoring
    print("✅ test_refactoring.py imported successfully")
    
    # Try running the main function
    try:
        result = test_refactoring.main()
        print(f"✅ test_refactoring.main() result: {result}")
        test_script_result = result
    except Exception as e:
        print(f"❌ test_refactoring.main() failed: {e}")
        test_script_result = False
        
except Exception as e:
    print(f"❌ test_refactoring.py import failed: {e}")
    test_script_result = False

# Summary
print("\n📊 VERIFICATION SUMMARY")
print("=" * 60)

file_passed = sum(1 for _, result in file_results if result)
file_total = len(file_results)
print(f"File Structure: {file_passed}/{file_total} files exist")

import_passed = sum(1 for _, result in import_results if result)
import_total = len(import_results)
print(f"Module Imports: {import_passed}/{import_total} modules imported")

core_passed = sum(1 for _, result in core_results if result)
core_total = len(core_results)
print(f"Core Modules: {core_passed}/{core_total} core modules imported")

func_passed = sum(1 for _, result in functionality_results if result)
func_total = len(functionality_results)
print(f"Functionality: {func_passed}/{func_total} functions working")

print(f"Original Test Script: {'✅' if test_script_result else '❌'}")

# Overall verdict
all_passed = (file_passed == file_total and 
              import_passed == import_total and
              func_passed == func_total and
              test_script_result)

print(f"\n🎯 OVERALL VERDICT: {'✅ REFACTORING WORKING' if all_passed else '❌ ISSUES FOUND'}")

if not all_passed:
    print("\n🔧 ISSUES FOUND:")
    for filepath, result in file_results:
        if not result:
            print(f"  - Missing file: {filepath}")
    
    for module_name, result in import_results:
        if not result:
            print(f"  - Import failed: {module_name}")
    
    for module_name, result in core_results:
        if not result:
            print(f"  - Core module failed: {module_name}")
    
    for func_name, result in functionality_results:
        if not result:
            print(f"  - Functionality failed: {func_name}")
    
    if not test_script_result:
        print(f"  - Original test script failed")

print("\n✨ VERIFICATION COMPLETE")
print("=" * 60)