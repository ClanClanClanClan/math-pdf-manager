#!/usr/bin/env python3
"""
Unicode Constants - Refactored Data Loader
Loads Unicode constants from JSON data files for better maintainability
"""

import json
from pathlib import Path
from typing import Dict, Any

# Path to data files
DATA_DIR = Path(__file__).parent / "src" / "data" / "unicode"

def load_constants() -> Dict[str, Any]:
    """Load all Unicode constants from JSON files"""
    constants_file = DATA_DIR / "constants.json"
    
    if not constants_file.exists():
        raise FileNotFoundError(f"Constants file not found: {constants_file}")
    
    with open(constants_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_mapping(name: str) -> Dict[str, str]:
    """Load a specific mapping from JSON file"""
    mapping_file = DATA_DIR / f"{name}.json"
    
    if not mapping_file.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_file}")
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        return json.load(f)

# Load constants at module level for backward compatibility
try:
    _constants = load_constants()
    
    # Export constants as module-level variables
    globals().update(_constants)
    
    # Also provide easy access to mappings
    SUPERSCRIPT_MAP = _constants.get('SUPERSCRIPT_MAP', {})
    SUBSCRIPT_MAP = _constants.get('SUBSCRIPT_MAP', {})
    MATHBB_MAP = _constants.get('MATHBB_MAP', {})
    SUFFIXES = _constants.get('SUFFIXES', [])
    
except FileNotFoundError as e:
    print(f"Warning: Could not load Unicode constants: {e}")
    # Fallback to empty mappings
    SUPERSCRIPT_MAP = {}
    SUBSCRIPT_MAP = {}
    MATHBB_MAP = {}
    SUFFIXES = []

# Utility functions
def get_superscript(char: str) -> str:
    """Get superscript version of character"""
    return SUPERSCRIPT_MAP.get(char, char)

def get_subscript(char: str) -> str:
    """Get subscript version of character"""
    return SUBSCRIPT_MAP.get(char, char)

def get_mathbb(char: str) -> str:
    """Get mathbb version of character"""
    return MATHBB_MAP.get(char, char)

def is_suffix(word: str) -> bool:
    """Check if word is a known suffix"""
    return word in SUFFIXES

# Stats for monitoring
def get_stats() -> Dict[str, int]:
    """Get statistics about loaded constants"""
    return {
        "superscripts": len(SUPERSCRIPT_MAP),
        "subscripts": len(SUBSCRIPT_MAP),
        "mathbb": len(MATHBB_MAP),
        "suffixes": len(SUFFIXES),
        "total_constants": len(_constants) if '_constants' in globals() else 0
    }
