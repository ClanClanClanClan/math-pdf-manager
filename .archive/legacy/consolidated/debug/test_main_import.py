#!/usr/bin/env python3
"""
Test script to verify main.py can be imported with DI changes
"""

import sys
import os
import traceback

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Test if main.py can be imported."""
    print("Testing main.py import...")
    
    try:
        # Try importing main.py
        import main
        print("✓ main.py imported successfully")
        
        # Check if main function exists
        if hasattr(main, 'main'):
            print("✓ main() function found")
        else:
            print("✗ main() function not found")
        
        # Check if DI decorators are present
        if hasattr(main.main, '__annotations__'):
            print("✓ main() function has annotations")
        else:
            print("✗ main() function has no annotations")
            
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
    success = test_import()
    sys.exit(0 if success else 1)