#!/usr/bin/env python3
"""
Legacy function importer that properly loads all functions from original files
"""

import sys
import importlib.util
import types
from pathlib import Path

def import_legacy_module(module_path, module_name):
    """Import a module bypassing the dataclass issues"""
    try:
        # Read the source code
        with open(module_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Create a module object
        module = types.ModuleType(module_name)
        module.__file__ = str(module_path)
        
        # Set it in sys.modules to avoid import issues
        sys.modules[module_name] = module
        
        # Execute the source in the module's namespace
        exec(source, module.__dict__)
        
        return module
    except Exception as e:
        print(f"Failed to import {module_path}: {e}")
        return None

def get_all_legacy_functions():
    """Get all functions from original filename_checker.py and utils.py"""
    functions = {}
    classes = {}
    constants = {}
    
    # Import utils.py FIRST (so it takes precedence)
    utils_path = Path(__file__).parent / "utils.py"
    if utils_path.exists():
        utils_module = import_legacy_module(utils_path, "legacy_utils")
        if utils_module:
            for name in dir(utils_module):
                if name.startswith('_'):
                    continue
                    
                obj = getattr(utils_module, name, None)
                if callable(obj):
                    functions[name] = obj
                elif isinstance(obj, type):
                    classes[name] = obj
                elif not callable(obj) and not isinstance(obj, types.ModuleType):
                    constants[name] = obj
                    
            print(f"✅ Imported {len(functions)} functions from utils.py")
    
    # Import filename_checker.py (only add what's not already there)
    filename_checker_path = Path(__file__).parent / "filename_checker.py"
    if filename_checker_path.exists():
        fc_module = import_legacy_module(filename_checker_path, "legacy_filename_checker")
        if fc_module:
            fc_count = 0
            for name in dir(fc_module):
                if name.startswith('_'):
                    continue
                    
                obj = getattr(fc_module, name, None)
                # Don't override functions we already have from utils
                if callable(obj) and name not in functions:
                    functions[name] = obj
                    fc_count += 1
                elif isinstance(obj, type) and name not in classes:
                    classes[name] = obj
                elif not callable(obj) and not isinstance(obj, types.ModuleType) and name not in constants:
                    constants[name] = obj
                    
            print(f"✅ Imported {fc_count} additional functions from filename_checker.py")
    
    # Combine all imports
    all_imports = {}
    all_imports.update(functions)
    all_imports.update(classes)
    all_imports.update(constants)
    
    return all_imports

if __name__ == "__main__":
    funcs = get_all_legacy_functions()
    print(f"Total legacy functions available: {len(funcs)}")
    print("Sample functions:", list(funcs.keys())[:10])