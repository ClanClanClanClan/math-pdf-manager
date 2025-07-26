#!/usr/bin/env python3
"""Debug the exact main rename logic"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from filename_checker import batch_check_filenames
from validators.filename import SpellChecker, SpellCheckerConfig
from utils import is_canonically_equivalent

# Create a simple test case
files = [
    {
        "path": "/tmp/test/Basic A.B.C. - Test.pdf",
        "filename": "Basic A.B.C. - Test.pdf"
    }
]

print("🔍 DEBUGGING MAIN RENAME LOGIC")
print("=" * 50)

# Create spell checker (minimal setup)
spell_config = SpellCheckerConfig(
    known_words={'basic', 'test'},
    multiword_surnames=set(),
    capitalization_whitelist=set(),
    name_dash_whitelist=set(),
    exceptions=set(),
)
spell_checker = SpellChecker(spell_config)

# Run batch check
print(f"Testing file: {files[0]['filename']}")
checks = batch_check_filenames(
    files,
    checker=spell_checker,
    check_unicode_normalization=False,
    check_author_format=True,
    auto_fix_authors=True,
    auto_fix_nfc=False,
    verbose=True,
)

print("\nBatch check results:")
for result in checks:
    print(f"  Filename: {result['filename']}")
    print(f"  Fixed filename: {result.get('fixed_filename')}")
    print(f"  Fixed author: {result.get('fixed_author')}")
    print(f"  Errors: {result.get('errors', [])}")
    print(f"  Suggestions: {result.get('suggestions', [])}")

print("\nRename decision logic:")
for result in checks:
    if not result.get("fixed_filename"):
        print("  ❌ No fixed_filename - would not rename")
        continue
    
    old_name = result["filename"]
    new_name = result["fixed_filename"]
    
    print(f"  Old name: '{old_name}'")
    print(f"  New name: '{new_name}'")
    
    # Skip if no actual change
    if old_name == new_name:
        print("  ❌ Names are identical - would not rename")
        continue
    
    # Check what type of fix this is
    is_nfc_fix = is_canonically_equivalent(old_name, new_name)
    is_author_fix = result.get("fixed_author") is not None
    
    print(f"  Is NFC fix: {is_nfc_fix}")
    print(f"  Is author fix: {is_author_fix}")
    
    # For auto_fix_authors=True, auto_fix_nfc=False
    should_fix = False
    if is_author_fix:
        should_fix = True
        print("  ✅ Would rename due to author fix")
    else:
        print("  ❌ Would NOT rename - no author fix detected")
    
    print(f"  Final decision: {'RENAME' if should_fix else 'NO RENAME'}")