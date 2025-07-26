#!/usr/bin/env python3
"""Debug script for mathematical context detection"""

from src.validators.filename_checker.math_utils import is_mathematical_context
from src.validators.filename_checker.debug import enable_debug

enable_debug()

test_text = "From 9:15 AM discussing x=7"
print(f"Test text: '{test_text}'")
print(f"Length: {len(test_text)}")

# Check each character position
for i, char in enumerate(test_text):
    print(f"Position {i}: '{char}'")

# Test position 23 (should be 'x')
pos = 23
print(f"\nChecking position {pos}: '{test_text[pos]}'")
result = is_mathematical_context(test_text, pos)
print(f"Result: {result}")

# Check position 24 (the 'x')
pos = 24
print(f"\nChecking position {pos}: '{test_text[pos]}'")
result = is_mathematical_context(test_text, pos)
print(f"Result: {result}")

# Check position 26 (the '7')
pos = 26
print(f"\nChecking position {pos}: '{test_text[pos]}'")
result = is_mathematical_context(test_text, pos)
print(f"Result: {result}")