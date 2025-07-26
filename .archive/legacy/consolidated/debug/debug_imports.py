#!/usr/bin/env python3
"""
Debug import issues step by step
"""
import sys
import os
import traceback

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_import(module_name, import_statement):
    """Test a single import."""
    print(f"Testing {module_name}...")
    try:
        exec(import_statement)
        print(f"✓ {module_name} imported successfully")
        return True
    except Exception as e:
        print(f"✗ {module_name} failed: {e}")
        traceback.print_exc()
        print("-" * 50)
        return False

# Test imports step by step
tests = [
    ("Basic Python modules", "import yaml, pathlib, logging"),
    ("Core interfaces", "from core.dependency_injection.interfaces import ILoggingService"),
    ("Secure config", "from core.config.secure_config import SecureConfigManager"),
    ("DI container", "from core.dependency_injection.container import DIContainer"),
    ("DI implementations", "from core.dependency_injection.implementations import LoggingService"),
    ("Service registry", "from service_registry import get_service_registry"),
    ("Config loader", "from config_loader import ConfigurationData"),
    ("Main processing", "from main_processing import process_files"),
    ("Constants", "from constants import DEFAULT_HTML_OUTPUT"),
    ("Main module", "from main import main"),
]

print("=== Import Testing ===")
for name, statement in tests:
    success = test_import(name, statement)
    if not success:
        print(f"Stopping at first failure: {name}")
        break
    print()

print("=== Testing help functionality ===")
try:
    from main import main
    print("Attempting to call main(['--help'])...")
    main(['--help'])
except SystemExit as e:
    print(f"✓ Help worked correctly (SystemExit with code {e.code})")
except Exception as e:
    print(f"✗ Help failed: {e}")
    traceback.print_exc()