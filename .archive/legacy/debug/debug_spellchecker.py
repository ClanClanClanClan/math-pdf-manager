#!/usr/bin/env python3
"""Debug why SpellChecker is not finding words"""

from my_spellchecker import SpellChecker, SpellCheckerConfig

# Load word lists
known_words = set()
with open('known_words.txt', 'r') as f:
    for line in f:
        word = line.strip()
        if word and not word.startswith('#'):
            known_words.add(word)

compound_terms = set()  # For now, empty like in our test

print(f"Loaded {len(known_words)} known words")

# Test specific words
test_words = ['individual-based', 'pseudo-continuity', 'non-existence', 'short-time']

print("\nDirect lookup in known_words:")
for word in test_words:
    print(f"  '{word}' in known_words: {word in known_words}")

# Create SpellChecker and test
config = SpellCheckerConfig(
    known_words=known_words | compound_terms,
    capitalization_whitelist=set(),
    name_dash_whitelist=set()
)

spellchecker = SpellChecker(config)

print(f"\nSpellChecker has {len(spellchecker.config.known_words)} total words")

print("\nSpellChecker tests:")
for word in test_words:
    # Test individual word lookup
    is_known = word in spellchecker.config.known_words
    print(f"  '{word}' in spellchecker.config.known_words: {is_known}")
    
    # Test check_spelling method
    result = spellchecker.check_spelling(word)
    print(f"  spellchecker.check_spelling('{word}'): {result}")