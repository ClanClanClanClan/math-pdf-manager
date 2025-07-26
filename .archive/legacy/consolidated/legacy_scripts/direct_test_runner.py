#\!/usr/bin/env python3
"""Direct test runner that avoids corrupted dependencies"""

import os
import sys
import importlib.util

def run_test_file(filepath):
    """Run a test file directly without pytest"""
    print(f"\n{'='*60}")
    print(f"Running: {filepath}")
    print('='*60)
    
    try:
        # Load the test module
        spec = importlib.util.spec_from_file_location("test_module", filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules["test_module"] = module
        spec.loader.exec_module(module)
        
        # Count test functions
        test_count = 0
        passed = 0
        failed = 0
        
        # Run all test_ functions
        for name in dir(module):
            if name.startswith('test_') and callable(getattr(module, name)):
                test_count += 1
                try:
                    print(f"\n  Running {name}...", end='')
                    getattr(module, name)()
                    print(" ✅ PASSED")
                    passed += 1
                except Exception as e:
                    print(f" ❌ FAILED: {e}")
                    failed += 1
        
        # Run main if exists
        if hasattr(module, 'main'):
            module.main()
            
        print(f"\nResults: {passed}/{test_count} passed")
        return passed == test_count
        
    except Exception as e:
        print(f"❌ Error loading/running {filepath}: {e}")
        return False

def main():
    """Run all test files that don't depend on corrupted libraries"""
    
    print("🧪 DIRECT TEST RUNNER - Avoiding corrupted dependencies")
    print("="*70)
    
    # Test files that should work without hypothesis/jinja2
    test_files = [
        'test_functionality.py',
        'test_refactoring.py',
        'tests/test_utils.py',
        'tests/test_scanner.py',
        'tests/test_duplicate_detector.py',
        'tests/test_math_detector.py',
        'tests/test_paper_validator.py',
        'tests/test_ito_possessive.py',
    ]
    
    results = []
    
    for test_file in test_files:
        if os.path.exists(test_file):
            results.append((test_file, run_test_file(test_file)))
    
    print("\n" + "="*70)
    print("📊 FINAL SUMMARY")
    print("="*70)
    
    passed_files = sum(1 for _, passed in results if passed)
    total_files = len(results)
    
    for test_file, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_file}")
    
    print(f"\nTotal: {passed_files}/{total_files} test files passed")
    
    if passed_files == total_files:
        print("\n🎉 ALL TESTS PASSED\!")
    else:
        print("\n❌ SOME TESTS FAILED")

if __name__ == "__main__":
    main()
EOF < /dev/null