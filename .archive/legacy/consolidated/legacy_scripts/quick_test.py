import sys
import os
sys.path.insert(0, os.getcwd())

try:
    print("Testing imports...")
    from main import main
    print("✓ main.py imports successfully")
    
    # Try to run help
    try:
        main(["--help"])
    except SystemExit:
        print("✓ --help flag works correctly")
    
    print("All basic tests passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()