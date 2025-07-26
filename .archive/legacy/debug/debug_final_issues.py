#!/usr/bin/env python3
"""Debug the final remaining issues"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from validators.filename import check_filename, SpellChecker, find_dash_pairs_with_positions, clean_whitelist_pairs
from my_spellchecker import SpellCheckerConfig
import yaml
import unicodedata

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Load word lists
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

compound_terms = set(config.get('compound_terms', []))
capitalization_whitelist = set(config.get('capitalization_whitelist', []))

print("=== WHITELIST VERIFICATION ===")
print(f"'Erdős–Rényi' in name_dash_whitelist: {'Erdős–Rényi' in name_dash_whitelist}")
print(f"'Karhunen–Loève' in name_dash_whitelist: {'Karhunen–Loève' in name_dash_whitelist}")
print(f"'Lévy-type' in compound_terms: {'Lévy-type' in compound_terms}")
print(f"'Lévy' in capitalization_whitelist: {'Lévy' in capitalization_whitelist}")
print(f"'Itô' in capitalization_whitelist: {'Itô' in capitalization_whitelist}")
print()

# Test the dash pair detection
test_cases = [
    ("Erdős–Rényi poissonized", "Erdős–Rényi"),
    ("Karhunen–Loève expansion", "Karhunen–Loève"),
    ("Lévy-type signature models", "Lévy-type"),
    ("Itô's formula", "Itô's")
]

print("=== DASH PAIR DETECTION ===")
for title, expected in test_cases:
    pairs = find_dash_pairs_with_positions(title)
    print(f"Title: '{title}'")
    print(f"  Expected: '{expected}'")
    print(f"  Detected pairs: {pairs}")
    if pairs:
        for L, R, dash, start, end in pairs:
            candidate = f"{L}{dash}{R}"
            print(f"    Candidate: '{candidate}'")
    print()

# Test the clean_whitelist_pairs function
print("=== WHITELIST CLEANING ===")
cleaned_whitelist = set(clean_whitelist_pairs(list(name_dash_whitelist)))
print(f"Original whitelist size: {len(name_dash_whitelist)}")
print(f"Cleaned whitelist size: {len(cleaned_whitelist)}")
print(f"'Erdős–Rényi' in cleaned: {'Erdős–Rényi' in cleaned_whitelist}")
print(f"'Karhunen–Loève' in cleaned: {'Karhunen–Loève' in cleaned_whitelist}")
print()

# Test full filename checking
print("=== FULL FILENAME TESTS ===")
test_filenames = [
    "Author - Erdős–Rényi poissonized.pdf",
    "Author - Karhunen–Loève expansion of random measures.pdf",
    "Author - Universal approximation theorems for continuous functions of càdlàg paths and Lévy-type signature models.pdf",
    "Author - Itô's formula for the flow of measures.pdf"
]

spellchecker = SpellChecker(SpellCheckerConfig(
    known_words=known_words | compound_terms,
    capitalization_whitelist=capitalization_whitelist,
    name_dash_whitelist=name_dash_whitelist
))

for filename in test_filenames:
    print(f"\nTesting: {filename}")
    result = check_filename(
        filename,
        known_words=known_words,
        whitelist_pairs=list(name_dash_whitelist),
        exceptions=set(),
        compound_terms=compound_terms,
        spellchecker=spellchecker,
        capitalization_whitelist=capitalization_whitelist,
        name_dash_whitelist=name_dash_whitelist,
        debug=False
    )
    print(f"  Errors: {len(result.errors)}")
    for error in result.errors:
        print(f"    - {error}")