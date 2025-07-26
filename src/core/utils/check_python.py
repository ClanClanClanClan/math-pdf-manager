#!/usr/bin/env python3
import sys
print(f"Python version: {sys.version}")
print(f"Current working directory: {sys.path[0]}")

# Try importing key modules
try:
    import yaml  # noqa: F401
    print("✓ yaml available")
except ImportError:
    print("✗ yaml not available")

try:
    import cryptography  # noqa: F401
    print("✓ cryptography available")
except ImportError:
    print("✗ cryptography not available")

try:
    from pathlib import Path  # noqa: F401
    print("✓ pathlib available")
except ImportError:
    print("✗ pathlib not available")

# Test basic import
try:
    import os
    sys.path.insert(0, os.getcwd())
    from main import main
    print("✓ main.py imports successfully")
    
    # Try help
    try:
        main(['--help'])
    except SystemExit:
        print("✓ --help works")
    
except Exception as e:
    print(f"✗ main.py import failed: {e}")
    import traceback
    traceback.print_exc()