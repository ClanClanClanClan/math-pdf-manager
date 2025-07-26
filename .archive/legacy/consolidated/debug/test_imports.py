#!/usr/bin/env python3
"""Test imports for all modularized files."""

import sys
import traceback

def test_import(module_name, file_path):
    """Test if a module can be imported."""
    try:
        __import__(module_name)
        print(f"✓ {module_name} ({file_path}) imports successfully")
        return True
    except Exception as e:
        print(f"✗ {module_name} ({file_path}) failed to import: {e}")
        traceback.print_exc()
        return False

def main():
    """Test all module imports."""
    modules = [
        ("main", "main.py"),
        ("main_processing", "main_processing.py"),
        ("config_loader", "config_loader.py"),
        ("service_registry", "service_registry.py"),
        ("constants", "constants.py"),
        ("validation", "validation.py"),
    ]
    
    print("Testing module imports...")
    print("=" * 50)
    
    success_count = 0
    for module_name, file_path in modules:
        if test_import(module_name, file_path):
            success_count += 1
    
    print("=" * 50)
    print(f"Import test results: {success_count}/{len(modules)} modules imported successfully")
    
    if success_count == len(modules):
        print("All modules can be imported successfully!")
    else:
        print("Some modules failed to import - check error details above")

if __name__ == "__main__":
    main()