#!/usr/bin/env python3
"""
Comprehensive coverage test for transformations.py - combining all unittest tests
"""

import os
import sys
import unittest

import coverage

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Start coverage
cov = coverage.Coverage()
cov.start()

# Import our new comprehensive test class
from test_transformations_100_final import TestTransformationsComplete

# Import our previous comprehensive test class  
from tests.unit.test_transformations_final_100 import TestTransformationsFinal100

# Create test suite with all available tests
suite = unittest.TestSuite()
loader = unittest.TestLoader()

# Add all our test classes
suite.addTests(loader.loadTestsFromTestCase(TestTransformationsComplete))
suite.addTests(loader.loadTestsFromTestCase(TestTransformationsFinal100))

print("Running comprehensive transformations coverage tests...")
print(f"Test classes loaded: TestTransformationsComplete, TestTransformationsFinal100")

# Run tests
runner = unittest.TextTestRunner(verbosity=1)
result = runner.run(suite)

# Stop coverage and generate report
cov.stop()
cov.save()

print(f"\n{'='*70}")
print("COMPREHENSIVE COVERAGE REPORT FOR transformations.py")
print(f"{'='*70}")

# Generate coverage report for transformations.py only
cov.report(include=['unicode_utils/transformations.py'], show_missing=True)

print(f"\n{'='*70}")
print(f"Total tests run: {result.testsRun}")
print(f"Failures: {len(result.failures)}")
print(f"Errors: {len(result.errors)}")
print(f"Success: {result.wasSuccessful()}")
print(f"{'='*70}")

if result.failures:
    print("\nFAILURES:")
    for test, traceback in result.failures:
        print(f"- {test}")

if result.errors:
    print("\nERRORS:")
    for test, traceback in result.errors:
        print(f"- {test}")