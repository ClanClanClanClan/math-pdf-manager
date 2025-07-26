#!/usr/bin/env python3
"""
Debug Unicode normalization issues
"""

import unicodedata as _ud

def main():
    # Test the specific problem cases
    test_cases = [
        ("Short-time from filename", "Short-time"),
        ("short-time from known_words", "short-time"),
        ("Itô-Wentzell from filename", "Itô-Wentzell"),
        ("Itô–Wentzell from whitelist", "Itô–Wentzell"),
    ]
    
    print("=== UNICODE NORMALIZATION DEBUG ===")
    
    for description, text in test_cases:
        print(f"\n{description}: '{text}'")
        print(f"  Length: {len(text)}")
        print(f"  Bytes: {text.encode('utf-8')}")
        print(f"  Unicode names: {[_ud.name(c, 'UNKNOWN') for c in text]}")
        print(f"  NFC: '{_ud.normalize('NFC', text)}'")
        print(f"  NFD: '{_ud.normalize('NFD', text)}'")
        print(f"  NFC == original: {_ud.normalize('NFC', text) == text}")
        print(f"  NFD == original: {_ud.normalize('NFD', text) == text}")
    
    # Test dash characters specifically
    print("\n=== DASH CHARACTER ANALYSIS ===")
    dash_chars = [
        ("hyphen-minus", "-"),
        ("en-dash", "–"),
        ("em-dash", "—"),
    ]
    
    for name, char in dash_chars:
        print(f"{name}: '{char}' (U+{ord(char):04X}) - {_ud.name(char)}")
    
    # Test if the problem words match when normalized
    print("\n=== NORMALIZATION MATCHING TEST ===")
    
    filename_short = "Short-time"
    known_short = "short-time"
    print(f"'{filename_short}' vs '{known_short}':")
    print(f"  Case-insensitive: {filename_short.lower() == known_short.lower()}")
    
    filename_ito = "Itô-Wentzell"
    whitelist_ito = "Itô–Wentzell"
    print(f"'{filename_ito}' vs '{whitelist_ito}':")
    print(f"  Direct match: {filename_ito == whitelist_ito}")
    print(f"  NFC normalized: {_ud.normalize('NFC', filename_ito) == _ud.normalize('NFC', whitelist_ito)}")
    print(f"  NFD normalized: {_ud.normalize('NFD', filename_ito) == _ud.normalize('NFD', whitelist_ito)}")
    print(f"  Case-insensitive: {filename_ito.lower() == whitelist_ito.lower()}")
    
    # Test character-by-character
    print(f"  Character-by-character comparison:")
    for i, (c1, c2) in enumerate(zip(filename_ito, whitelist_ito)):
        if c1 != c2:
            print(f"    Position {i}: '{c1}' (U+{ord(c1):04X}) vs '{c2}' (U+{ord(c2):04X})")

if __name__ == "__main__":
    main()