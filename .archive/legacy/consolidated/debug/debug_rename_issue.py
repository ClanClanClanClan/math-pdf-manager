#!/usr/bin/env python3
"""Debug the exact issue with file renaming"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from filename_checker import normalize_for_comparison, author_string_is_normalized
from author_processing import fix_author_block
from text_normalization import normalize_nfc_cached as nfc

# Test cases from the failing test
test_cases = [
    "Basic A.B.C.",
    "Smith J.D.",
    "Teter, A. M. H. Nodozi I. Halder A.",
    "de la Cruz J.M. García II"
]

print("🔍 DEBUGGING FILE RENAME ISSUE")
print("=" * 50)

for original in test_cases:
    print(f"\nOriginal: '{original}'")
    
    # What fix_author_block produces
    fixed = fix_author_block(original)
    print(f"Fixed:    '{fixed}'")
    print(f"Different? {original != fixed}")
    
    # What normalize_for_comparison does to each
    orig_normalized = normalize_for_comparison(nfc(original))
    fixed_normalized = normalize_for_comparison(nfc(fixed))
    
    print(f"Original normalized: '{orig_normalized}'")
    print(f"Fixed normalized:    '{fixed_normalized}'")
    print(f"Normalized equal? {orig_normalized == fixed_normalized}")
    
    # What author_string_is_normalized returns
    is_norm, result = author_string_is_normalized(original)
    print(f"author_string_is_normalized: {is_norm}")
    
    print("-" * 30)