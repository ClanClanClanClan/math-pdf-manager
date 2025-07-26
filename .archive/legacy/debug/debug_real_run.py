#!/usr/bin/env python3
"""Debug a real run of the filename checker on the problematic file"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from validators.filename import check_filename, SpellChecker
from my_spellchecker import SpellCheckerConfig

# Load word lists like main.py does
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

# Check specific entry
test_entry = "Erdős–Rényi"
print(f"'{test_entry}' in name_dash_whitelist: {test_entry in name_dash_whitelist}")

# Create SpellChecker like main.py does
compound_terms = set()  # Simplified for this test
spellchecker = SpellChecker(SpellCheckerConfig(
    known_words=known_words | compound_terms,
    capitalization_whitelist=set(),
    name_dash_whitelist=name_dash_whitelist
))

# Test the problematic filename
filename = "Curien, N. - Erdős–Rényi poissonized.pdf"
print(f"\nTesting filename: {filename}")

result = check_filename(
    filename,
    known_words=known_words,
    whitelist_pairs=list(name_dash_whitelist),
    exceptions=set(),
    compound_terms=compound_terms,
    spellchecker=spellchecker,
    capitalization_whitelist=set(),
    name_dash_whitelist=name_dash_whitelist,
    debug=True
)

print(f"\nResult:")
print(f"  Errors: {result.errors}")
print(f"  Suggestions: {result.suggestions}")
print(f"  Fixed filename: {result.fixed_filename}")