#!/usr/bin/env python3
"""Test script to verify main.py can be imported."""

import sys
import traceback

def test_main_import():
    """Test if main.py can be imported successfully."""
    try:
        import main
        print("✓ main.py imports successfully")
        
        # Test if main function exists and has proper decorators
        if hasattr(main, 'main'):
            print("✓ main() function exists")
            
            # Check if function has inject decorators
            func = main.main
            if hasattr(func, '__wrapped__'):
                print("✓ main() function has decorators")
            else:
                print("? main() function decorators not detected")
        else:
            print("✗ main() function not found")
            
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_main_import()