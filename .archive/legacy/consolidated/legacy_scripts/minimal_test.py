#!/usr/bin/env python3
"""
Minimal test to identify import issues
"""
import sys
import os
import traceback

# Add current directory to path
sys.path.insert(0, os.getcwd())

print("Python version:", sys.version)
print("Current directory:", os.getcwd())
print("Python path:", sys.path[:3])  # Show first 3 paths

print("\n=== Testing core imports ===")

try:
    # Test basic imports first
    from pathlib import Path
    print("✓ pathlib.Path")
    
    import yaml
    print("✓ yaml")
    
    # Test our core modules
    from core.dependency_injection.interfaces import ILoggingService
    print("✓ core.dependency_injection.interfaces")
    
    from core.dependency_injection.container import DIContainer
    print("✓ core.dependency_injection.container")
    
    from core.config.secure_config import SecureConfigManager
    print("✓ core.config.secure_config")
    
    from core.dependency_injection.implementations import LoggingService
    print("✓ core.dependency_injection.implementations")
    
    from service_registry import get_service_registry
    print("✓ service_registry")
    
    from config_loader import ConfigurationData
    print("✓ config_loader")
    
    from main_processing import process_files
    print("✓ main_processing")
    
    # Test main import
    from main import main
    print("✓ main")
    
    print("\n=== All imports successful! ===")
    
except Exception as e:
    print(f"\n✗ Import failed: {e}")
    traceback.print_exc()