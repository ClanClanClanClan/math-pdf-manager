#\!/usr/bin/env python3
"""Debug Erdős–Rényi tokenization issue"""

import unicodedata
from validators.filename import robust_tokenize_with_math, spelling_and_format_errors
from my_spellchecker import SpellChecker, SpellCheckerConfig

# Test data
title = "Erdős–Rényi poissonized"
name_dash_whitelist = ["Erdős–Rényi"]  # This is what's in the file

# Load word lists
known_words = set()
capitalization_whitelist = set()
exceptions = set()
dash_whitelist = set(name_dash_whitelist)

# Combined allowed words
all_allowed_words = known_words | capitalization_whitelist | exceptions | dash_whitelist

print(f"Title: '{title}'")
print(f"Dash whitelist: {dash_whitelist}")
print(f"All allowed words: {all_allowed_words}")
print()

# Test tokenization
tokens = robust_tokenize_with_math(title, all_allowed_words)
print("Tokens:")
for tok in tokens:
    print(f"  {tok.kind}: '{tok.value}' at {tok.start}-{tok.end}")
print()

# Check normalization
print("Normalization check:")
for word in ["Erdős–Rényi", "Erdős", "Rényi"]:
    nfc = unicodedata.normalize('NFC', word)
    print(f"  '{word}' -> NFC: '{nfc}' (equal: {word == nfc})")

# Check if it's in the set
test_term = "Erdős–Rényi"
print(f"\n'{test_term}' in dash_whitelist: {test_term in dash_whitelist}")
print(f"'{unicodedata.normalize('NFC', test_term)}' in dash_whitelist: {unicodedata.normalize('NFC', test_term) in dash_whitelist}")

# Test spelling_and_format_errors
print("\nTesting spelling_and_format_errors:")
speller = SpellChecker(SpellCheckerConfig(known_words=known_words))
errors = spelling_and_format_errors(title, known_words, capitalization_whitelist, exceptions, dash_whitelist, speller)
for err in errors:
    print(f"  Error: {err}")