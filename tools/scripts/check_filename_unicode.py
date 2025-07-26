#!/usr/bin/env python3
"""Check if the actual filenames have Unicode normalization issues"""

import os
import unicodedata

test_dir = os.path.expanduser("~/Dropbox/Work/Maths/12 - Math articles - working papers/C/2022/")

print("Checking Unicode normalization in actual filenames...")
print()

for filename in os.listdir(test_dir):
    if filename.endswith('.pdf'):
        # Check specific problematic terms
        if any(term in filename for term in ['Erdős', 'Karhunen', 'Lévy']):
            nfc = unicodedata.normalize('NFC', filename)
            if filename != nfc:
                print(f"Normalization issue in filename:")
                print(f"  Original: '{filename}'")
                print(f"  NFC: '{nfc}'")
                print(f"  Equal: {filename == nfc}")
            else:
                print(f"Filename OK (NFC): '{filename[:80]}...'")
                
                # Extract the specific terms
                if 'Erdős–Rényi' in filename:
                    print(f"  Contains 'Erdős–Rényi' (NFC normalized)")
                if 'Karhunen–Loève' in filename:
                    print(f"  Contains 'Karhunen–Loève' (NFC normalized)")
                if 'Lévy-type' in filename:
                    print(f"  Contains 'Lévy-type' (NFC normalized)")
            print()