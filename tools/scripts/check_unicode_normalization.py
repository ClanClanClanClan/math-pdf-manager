#!/usr/bin/env python3
"""Check Unicode normalization in name_dash_whitelist.txt"""

import unicodedata

# Read the file and check each line
with open('name_dash_whitelist.txt', "r", encoding="utf-8") as f:
    lines = f.readlines()

print("Checking for Unicode normalization issues...")
print()

issues = []
for i, line in enumerate(lines, 1):
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    
    # Check if line is NFC normalized
    nfc = unicodedata.normalize('NFC', line)
    if line != nfc:
        issues.append((i, line, nfc))

if issues:
    print(f"Found {len(issues)} lines with normalization issues:")
    for line_num, original, normalized in issues:
        print(f"\nLine {line_num}:")
        print(f"  Original:   '{original}' (len={len(original)})")
        print(f"  Normalized: '{normalized}' (len={len(normalized)})")
        # Show character details
        print("  Original chars:", [f"{c} (U+{ord(c):04X})" for c in original])
        print("  Normalized chars:", [f"{c} (U+{ord(c):04X})" for c in normalized])
else:
    print("No normalization issues found.")

# Specifically check the problematic entries
print("\n" + "="*60)
print("Checking specific problematic entries:")
for entry in ['Karhunen–Loève', 'Erdős–Rényi']:
    found = False
    for line in lines:
        line = line.strip()
        if entry in line or unicodedata.normalize('NFC', entry) in line:
            found = True
            print(f"\n'{entry}':")
            print(f"  Line in file: '{line}'")
            print(f"  NFC normalized: '{unicodedata.normalize('NFC', line)}'")
            print(f"  Match: {entry == line}")
            print(f"  Match after NFC: {entry == unicodedata.normalize('NFC', line)}")
            break
    if not found:
        print(f"\n'{entry}': NOT FOUND")