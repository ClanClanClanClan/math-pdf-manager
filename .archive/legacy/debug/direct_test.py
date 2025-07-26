#!/usr/bin/env python3
"""Direct test of filename_checker fixes"""

from validators.filename import check_filename, SpellChecker

# Test data
test_cases = [
    {
        'filename': "Author - Short-time analysis.pdf",
        'description': 'Should flag capital S in Short-time',
        'expect_errors': True
    },
    {
        'filename': "Author - short-time analysis.pdf", 
        'description': 'Should accept lowercase short-time if in known_words',
        'expect_errors': False  # Assuming short-time is in known_words
    },
    {
        'filename': "Author - Itô-Wentzell formula.pdf",
        'description': 'Should flag hyphen version if only en-dash in whitelist',
        'expect_errors': True
    },
    {
        'filename': "Author - Itô–Wentzell formula.pdf",
        'description': 'Should accept en-dash version if in whitelist',
        'expect_errors': False  # Assuming this is in name_dash_whitelist
    }
]

# Load actual word lists
known_words = set()
with open('known_words.txt', 'r') as f:
    for line in f:
        word = line.strip()
        if word and not word.startswith('#'):
            known_words.add(word)

name_dash_whitelist = set()
with open('name_dash_whitelist.txt', 'r') as f:
    for line in f:
        word = line.strip()
        if word and not word.startswith('#'):
            name_dash_whitelist.add(word)

print(f"Loaded {len(known_words)} known words")
print(f"Loaded {len(name_dash_whitelist)} name dash whitelist entries")

# Check what we have for test words
print("\nChecking test words:")
print(f"  'short-time' in known_words: {'short-time' in known_words}")
print(f"  'Itô-Wentzell' in name_dash_whitelist: {'Itô-Wentzell' in name_dash_whitelist}")
print(f"  'Itô–Wentzell' in name_dash_whitelist: {'Itô–Wentzell' in name_dash_whitelist}")

# Create spell checker
spellchecker = SpellChecker()

print("\n" + "="*80)
print("Running tests:")
print("="*80)

for test in test_cases:
    print(f"\nTest: {test['filename']}")
    print(f"Description: {test['description']}")
    
    result = check_filename(
        test['filename'],
        known_words=known_words,
        whitelist_pairs=list(name_dash_whitelist),
        exceptions=set(),
        compound_terms=set(),  # Not loading from config for simplicity
        spellchecker=spellchecker,
        capitalization_whitelist=set(),
        name_dash_whitelist=name_dash_whitelist,
        debug=False
    )
    
    has_errors = len(result.errors) > 0
    expected = test['expect_errors']
    
    if has_errors == expected:
        print(f"✓ PASS - {'Has errors' if has_errors else 'No errors'} as expected")
    else:
        print(f"✗ FAIL - Expected {'errors' if expected else 'no errors'}, got {'errors' if has_errors else 'no errors'}")
    
    if result.errors:
        for error in result.errors:
            print(f"  Error: {error}")