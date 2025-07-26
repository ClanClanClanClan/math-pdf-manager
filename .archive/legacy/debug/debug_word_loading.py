#!/usr/bin/env python3
"""
Simple script to debug word loading without complex dependencies
"""

import os
import sys
from pathlib import Path
import yaml

def load_yaml_config_simple(config_path):
    """Simple YAML loading with manual parsing fallback"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try YAML first
        try:
            import yaml
            return yaml.safe_load(content) or {}
        except Exception as e:
            # Manual parsing fallback
            return parse_yaml_manually(content)
    except Exception as e:
        print(f"Failed to load config: {e}")
        return {}

def parse_yaml_manually(content):
    """Manual YAML parsing for lists"""
    result = {}
    lines = content.split('\n')
    current_key = None
    current_list = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        if line.endswith(':') and not line.startswith('-'):
            # New key
            if current_key and current_list:
                result[current_key] = current_list
            current_key = line[:-1].strip()
            current_list = []
        elif line.startswith('- ') and current_key:
            # List item
            item = line[2:].strip()
            if item:
                current_list.append(item)
    
    # Add last list
    if current_key and current_list:
        result[current_key] = current_list
    
    return result

def load_words_file_simple(path, description="word file"):
    """Simple word file loading"""
    if not path:
        print(f"No path specified for {description}")
        return set()
    
    resolved_path = Path(path).expanduser().resolve()
    print(f"Loading {description}: {resolved_path}")
    
    if not resolved_path.exists():
        print(f"{description} not found: {resolved_path}")
        return set()
    
    try:
        with open(resolved_path, 'r', encoding='utf-8') as f:
            words = {
                line.strip() 
                for line in f 
                if line.strip() and not line.strip().startswith('#')
            }
        print(f"✓ Loaded {len(words)} words from {description}")
        return words
    except Exception as e:
        print(f"Failed to load {description}: {e}")
        return set()

def main():
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("=== DEBUGGING WORD LOADING ===")
    
    # Load config
    cfg = load_yaml_config_simple("config.yaml")
    print(f"Config keys: {list(cfg.keys())}")
    
    # Load word files
    known_words = load_words_file_simple("known_words.txt", "known words")
    name_dash_whitelist = load_words_file_simple("name_dash_whitelist.txt", "name dash whitelist")
    
    # Load compound terms from config
    compound_terms = set(cfg.get("compound_terms", []))
    print(f"✓ Compound terms from config: {len(compound_terms)}")
    
    # Load capitalization whitelist from config
    capitalization_whl = set(cfg.get("capitalization_whitelist", []))
    print(f"✓ Capitalization whitelist from config: {len(capitalization_whl)}")
    
    # Test specific problem words
    problem_words = [
        'individual-based', 'pseudo-continuity', 'Short-time', 
        'non-existence', 'Itô-Wentzell', 'mean-field', 'non-linear'
    ]
    
    print("\n=== PROBLEM WORD CHECK ===")
    for word in problem_words:
        in_known = word in known_words
        in_dash = word in name_dash_whitelist
        in_compound = word in compound_terms
        in_cap = word in capitalization_whl
        
        # Case-insensitive check
        in_known_ci = any(w.lower() == word.lower() for w in known_words)
        in_dash_ci = any(w.lower() == word.lower() for w in name_dash_whitelist)
        in_compound_ci = any(w.lower() == word.lower() for w in compound_terms)
        in_cap_ci = any(w.lower() == word.lower() for w in capitalization_whl)
        
        print(f"'{word}':")
        print(f"  - known_words: {in_known} (case-insensitive: {in_known_ci})")
        print(f"  - name_dash_whitelist: {in_dash} (case-insensitive: {in_dash_ci})")
        print(f"  - compound_terms: {in_compound} (case-insensitive: {in_compound_ci})")
        print(f"  - capitalization_whitelist: {in_cap} (case-insensitive: {in_cap_ci})")
        print(f"  - found_anywhere: {in_known or in_dash or in_compound or in_cap}")
        print(f"  - found_anywhere_ci: {in_known_ci or in_dash_ci or in_compound_ci or in_cap_ci}")
        
        # Look for partial matches
        if not (in_known or in_dash or in_compound or in_cap):
            similar_words = []
            for word_set, name in [(known_words, 'known_words'), (name_dash_whitelist, 'dash_whitelist'), 
                                 (compound_terms, 'compound_terms'), (capitalization_whl, 'cap_whitelist')]:
                matches = [w for w in word_set if word.lower() in w.lower() or w.lower() in word.lower()]
                if matches:
                    similar_words.extend([(name, m) for m in matches[:3]])
            
            if similar_words:
                print(f"  - similar_words: {similar_words}")
        print()
    
    # Check if compound terms contains hyphenated words
    hyphenated_compounds = [w for w in compound_terms if '-' in w]
    print(f"Hyphenated compound terms: {len(hyphenated_compounds)}")
    if hyphenated_compounds:
        print("Sample hyphenated compounds:", hyphenated_compounds[:10])
    
    # Check capitalization whitelist for hyphenated words
    hyphenated_cap = [w for w in capitalization_whl if '-' in w]
    print(f"Hyphenated words in capitalization_whitelist: {len(hyphenated_cap)}")
    if hyphenated_cap:
        print("Sample hyphenated cap words:", hyphenated_cap[:10])

if __name__ == "__main__":
    main()