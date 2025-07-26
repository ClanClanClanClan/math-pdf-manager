#!/usr/bin/env python3
"""
Extract Unicode constants from unicode_constants.py to JSON data files
This will transform the 3,678 line file into manageable data files
"""

import json
import re
from pathlib import Path

# Import the current unicode_constants
import unicode_constants

def extract_constants():
    """Extract Unicode constants to JSON files"""
    
    # Create output directory
    output_dir = Path("src/data/unicode")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Extract core constants
    constants_data = {}
    
    # Get all module-level variables that are mappings or constants
    for name in dir(unicode_constants):
        if not name.startswith('_'):  # Skip private attributes
            value = getattr(unicode_constants, name)
            if isinstance(value, (dict, list, tuple, str, int, float, bool)):
                constants_data[name] = value
    
    # Write constants to JSON
    with open(output_dir / "constants.json", "w", encoding="utf-8") as f:
        json.dump(constants_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Extracted {len(constants_data)} constants to constants.json")
    
    # 2. Extract specific mappings for easier access
    mappings = {
        "superscripts": getattr(unicode_constants, 'SUPERSCRIPT_MAP', {}),
        "subscripts": getattr(unicode_constants, 'SUBSCRIPT_MAP', {}),
        "mathbb": getattr(unicode_constants, 'MATHBB_MAP', {}),
        "suffixes": getattr(unicode_constants, 'SUFFIXES', []),
    }
    
    # Write mappings to separate files
    for name, data in mappings.items():
        with open(output_dir / f"{name}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Extracted {name} to {name}.json")
    
    return len(constants_data)

def create_new_unicode_constants():
    """Create a new, minimal unicode_constants.py that loads from JSON"""
    
    new_content = '''#!/usr/bin/env python3
"""
Unicode Constants - Refactored Data Loader
Loads Unicode constants from JSON data files for better maintainability
"""

import json
from pathlib import Path
from typing import Dict, List, Any

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
'''
    
    # Write new unicode_constants.py
    with open("unicode_constants_new.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("✅ Created new unicode_constants_new.py")

if __name__ == "__main__":
    print("🚀 Extracting Unicode constants to JSON files...")
    
    try:
        # Extract constants
        count = extract_constants()
        
        # Create new module
        create_new_unicode_constants()
        
        print(f"""
✅ SUCCESS: Unicode constants extraction complete!

📊 Results:
- Original file: 3,678 lines
- Constants extracted: {count}
- Data files created: 5 JSON files
- New module: unicode_constants_new.py (~100 lines)

📁 Files created:
- src/data/unicode/constants.json
- src/data/unicode/superscripts.json
- src/data/unicode/subscripts.json
- src/data/unicode/mathbb.json
- src/data/unicode/suffixes.json
- unicode_constants_new.py

💡 Next steps:
1. Test the new module
2. Replace unicode_constants.py with unicode_constants_new.py
3. Update imports if needed
""")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()