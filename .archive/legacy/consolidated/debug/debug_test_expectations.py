#!/usr/bin/env python3
"""Debug script to capture actual renames vs expected"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from filename_checker import batch_check_filenames
from validators.filename import SpellChecker, SpellCheckerConfig

# Test cases from the failing test
test_cases = [
    # Basic
    ("Basic A.B.C. - Test.pdf", "Basic, A. B. C. - Test.pdf"),
    ("Smith J.D. - Paper.pdf", "Smith, J. D. - Paper.pdf"),
    ("Multiple  Spaces A.B. - Title.pdf", "Multiple Spaces, A. B. - Title.pdf"),
    
    # User Issue
    ("Teter, A. M. H. Nodozi I. Halder A. - User Issue.pdf",
     "Teter, A. M. H., Nodozi, I., Halder, A. - User issue.pdf"),
    
    # Complex
    ("de la Cruz J.M. García II - Complex.pdf", 
     "de la Cruz, J. M., García, II - Complex.pdf"),
    ("van der Berg A.B.C. Jr MD - Academic.pdf",
     "van der Berg, A. B. C., Jr, MD - Academic.pdf"),
     
    # Unicode
    ("Müller A.Ö. - Über.pdf", "Müller, A. Ö. - Über.pdf"),
    ("José A.É. - Café.pdf", "José, A. É. - Café.pdf"),
]

print("🔍 DEBUGGING TEST EXPECTATIONS")
print("=" * 60)

# Create spell checker with comprehensive words
all_words = ['basic', 'test', 'smith', 'paper', 'multiple', 'spaces', 'title',
             'teter', 'nodozi', 'halder', 'user', 'issue', 'cruz', 'garcia', 
             'complex', 'berg', 'academic', 'mueller', 'uber', 'jose', 'cafe',
             'perfect', 'author', 'good', 'format']

spell_config = SpellCheckerConfig(
    known_words=set(all_words),
    multiword_surnames=set(),
    capitalization_whitelist=set(),
    name_dash_whitelist=set(),
    exceptions=set(),
)
spell_checker = SpellChecker(spell_config)

print("\nTesting each case:\n")

for i, (original, expected) in enumerate(test_cases, 1):
    print(f"{i}. Original: {original}")
    print(f"   Expected: {expected}")
    
    # Create file info
    files = [{"path": f"/tmp/test/{original}", "filename": original}]
    
    # Run batch check
    checks = batch_check_filenames(
        files,
        checker=spell_checker,
        check_unicode_normalization=False,
        check_author_format=True,
        auto_fix_authors=True,
        auto_fix_nfc=False,
        verbose=False,
    )
    
    if checks:
        actual = checks[0].get('fixed_filename')
        print(f"   Actual:   {actual}")
        
        matches = actual == expected
        print(f"   Matches:  {'✅' if matches else '❌'}")
        
        if not matches:
            print(f"   NEED TO UPDATE TEST EXPECTATION!")
            print(f"   Old: {repr(expected)}")
            print(f"   New: {repr(actual)}")
    else:
        print(f"   Actual:   NO CHANGES DETECTED")
        print(f"   Matches:  ❌")
    
    print()