#!/usr/bin/env python3
"""
Comprehensive test for the Math-PDF manager system
"""
import sys
import os
import subprocess
import traceback
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.getcwd())

def check_dependencies():
    """Check if required dependencies are installed."""
    print("=== Checking Dependencies ===")
    
    required_packages = [
        'yaml',
        'cryptography',
        'pathlib',
        'argparse',
        'logging',
        'json',
        'unicodedata',
        'time',
        'dataclasses',
        'typing',
        'abc',
        'functools',
        'inspect'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\nMissing packages: {missing}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    print("✓ All dependencies available")
    return True

def test_core_files():
    """Test if core files exist."""
    print("\n=== Checking Core Files ===")
    
    required_files = [
        'main.py',
        'main_processing.py',
        'config_loader.py',
        'service_registry.py',
        'main_di_helpers.py',
        'constants.py',
        'core/dependency_injection/__init__.py',
        'core/dependency_injection/interfaces.py',
        'core/dependency_injection/container.py',
        'core/dependency_injection/implementations.py',
        'core/config/secure_config.py',
        'secure_credential_manager.py',
        'filename_checker.py',
        'my_spellchecker.py',
        'utils.py',
        'text_normalization.py',
        'reporter.py',
        'scanner.py',
        'file_operations.py',
        'duplicate_detector.py'
    ]
    
    missing = []
    for file in required_files:
        file_path = Path(file)
        if file_path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - MISSING")
            missing.append(file)
    
    if missing:
        print(f"\nMissing files: {missing}")
        return False
    
    print("✓ All core files present")
    return True

def test_imports():
    """Test imports step by step."""
    print("\n=== Testing Imports ===")
    
    import_tests = [
        ("Basic modules", "import yaml, pathlib, logging, json, time"),
        ("Core interfaces", "from core.dependency_injection.interfaces import ILoggingService"),
        ("Secure config", "from core.config.secure_config import SecureConfigManager"),
        ("DI container", "from core.dependency_injection.container import DIContainer"),
        ("DI implementations", "from core.dependency_injection.implementations import LoggingService"),
        ("Service registry", "from service_registry import get_service_registry"),
        ("Config loader", "from config_loader import ConfigurationData"),
        ("Constants", "from constants import DEFAULT_HTML_OUTPUT"),
        ("Main helpers", "from main_di_helpers import validate_cli_inputs_di"),
        ("Main processing", "from main_processing import process_files"),
        ("Main module", "from main import main"),
    ]
    
    failed = []
    for name, import_stmt in import_tests:
        try:
            exec(import_stmt)
            print(f"✓ {name}")
        except Exception as e:
            print(f"✗ {name}: {e}")
            failed.append((name, str(e)))
    
    if failed:
        print(f"\nFailed imports: {len(failed)}")
        for name, error in failed:
            print(f"  {name}: {error}")
        return False
    
    print("✓ All imports successful")
    return True

def test_di_framework():
    """Test the dependency injection framework."""
    print("\n=== Testing DI Framework ===")
    
    try:
        from core.dependency_injection import setup_default_services, get_container
        from service_registry import get_service_registry
        
        # Setup services
        setup_default_services()
        print("✓ Default services setup")
        
        # Get container
        container = get_container()
        print("✓ Container retrieval")
        
        # Test service registry
        registry = get_service_registry()
        registry.initialize()
        print("✓ Service registry initialization")
        
        # Test service resolution
        logging_service = registry.logging_service
        print("✓ Logging service resolution")
        
        # Test logging
        logging_service.info("Test message")
        print("✓ Logging service functionality")
        
        return True
        
    except Exception as e:
        print(f"✗ DI framework test failed: {e}")
        traceback.print_exc()
        return False

def test_help_flag():
    """Test the --help flag."""
    print("\n=== Testing Help Flag ===")
    
    try:
        from main import main
        
        # Test help flag
        try:
            main(['--help'])
            print("✗ Help should have exited")
            return False
        except SystemExit as e:
            if e.code == 0:
                print("✓ Help flag works correctly")
                return True
            else:
                print(f"✗ Help exited with code {e.code}")
                return False
        except Exception as e:
            print(f"✗ Help flag failed: {e}")
            return False
    
    except Exception as e:
        print(f"✗ Cannot test help flag: {e}")
        return False

def test_dry_run():
    """Test dry run mode."""
    print("\n=== Testing Dry Run ===")
    
    try:
        from main import main
        
        # Create a test directory
        test_dir = Path("test_dry_run")
        test_dir.mkdir(exist_ok=True)
        
        # Create a test file
        test_file = test_dir / "Test Author - Sample Paper.pdf"
        test_file.touch()
        
        try:
            # Run with dry run
            main([str(test_dir), '--dry_run'])
            print("✓ Dry run completed successfully")
            success = True
        except Exception as e:
            print(f"✗ Dry run failed: {e}")
            success = False
        finally:
            # Clean up
            test_file.unlink(missing_ok=True)
            test_dir.rmdir()
        
        return success
        
    except Exception as e:
        print(f"✗ Cannot test dry run: {e}")
        return False

def main():
    """Run all tests."""
    print("Math-PDF Manager System Testing")
    print("=" * 50)
    
    tests = [
        ("Dependencies", check_dependencies),
        ("Core Files", test_core_files),
        ("Imports", test_imports),
        ("DI Framework", test_di_framework),
        ("Help Flag", test_help_flag),
        ("Dry Run", test_dry_run),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} CRASHED: {e}")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"Total: {passed + failed} tests")
    
    if failed == 0:
        print("🎉 All tests passed! The system is working correctly.")
    else:
        print(f"⚠️  {failed} test(s) failed. Check the output above for details.")
    
    return failed == 0

if __name__ == "__main__":
    sys.exit(0 if main() else 1)