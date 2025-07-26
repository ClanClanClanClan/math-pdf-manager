#!/usr/bin/env python3
"""Test backward compatibility of text processing functions."""

import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

def test_backward_compatibility():
    """Test that old and new functions produce same results."""
    
    try:
        from my_spellchecker import canonicalize as old_canonicalize
        from core.text_processing import canonicalize as new_canonicalize
        
        test_cases = [
            'Café résumé',
            'Test—with—dashes', 
            'UPPERCASE text',
            'spéciâl chäractérs'
        ]
        
        all_match = True
        for test in test_cases:
            old_result = old_canonicalize(test)
            new_result = new_canonicalize(test)
            if old_result != new_result:
                print(f'❌ Mismatch for "{test}": old="{old_result}" new="{new_result}"')
                all_match = False
        
        if all_match:
            print('✓ All canonicalize functions produce identical results')
            return True
        else:
            print('❌ Functions produce different results')
            return False
            
    except Exception as e:
        print(f'❌ Backward compatibility test failed: {e}')
        return False

if __name__ == "__main__":
    success = test_backward_compatibility()
    sys.exit(0 if success else 1)