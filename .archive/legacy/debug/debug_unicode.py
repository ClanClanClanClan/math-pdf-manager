#!/usr/bin/env python3
"""Debug Unicode normalization issues"""

import unicodedata

# Test string from file
filename = "Curien, N. - Erdős–Rényi poissonized.pdf"
title = "Erdős–Rényi poissonized"

# Load whitelist entry
with open('name_dash_whitelist.txt', 'r') as f:
    for line in f:
        if 'Erdős' in line:
            whitelist_entry = line.strip()
            break

print(f"Filename: {repr(filename)}")
print(f"Title: {repr(title)}")
print(f"Whitelist entry: {repr(whitelist_entry)}")
print()

# Extract just the compound term
compound_from_title = "Erdős–Rényi"
compound_from_whitelist = whitelist_entry

print(f"Compound from title: {repr(compound_from_title)}")
print(f"Compound from whitelist: {repr(compound_from_whitelist)}")
print(f"Are they equal? {compound_from_title == compound_from_whitelist}")
print()

# Check Unicode normalization
for form in ['NFC', 'NFD', 'NFKC', 'NFKD']:
    title_norm = unicodedata.normalize(form, compound_from_title)
    whitelist_norm = unicodedata.normalize(form, compound_from_whitelist)
    print(f"{form}:")
    print(f"  Title: {repr(title_norm)}")
    print(f"  Whitelist: {repr(whitelist_norm)}")
    print(f"  Equal: {title_norm == whitelist_norm}")
    print()

# Check each character
print("Character-by-character comparison:")
for i, (tc, wc) in enumerate(zip(compound_from_title, compound_from_whitelist)):
    print(f"  [{i}] Title: '{tc}' (U+{ord(tc):04X}) vs Whitelist: '{wc}' (U+{ord(wc):04X}) - Match: {tc == wc}")

# Check if there are any extra characters
if len(compound_from_title) != len(compound_from_whitelist):
    print(f"Length mismatch: title={len(compound_from_title)}, whitelist={len(compound_from_whitelist)}")