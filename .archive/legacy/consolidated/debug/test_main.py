#!/usr/bin/env python3
"""
Test script for the Math-PDF manager system.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all key modules can be imported."""
    print("=== Testing Imports ===")
    
    try:
        # Test core dependency injection
        from core.dependency_injection import get_container, inject, ILoggingService
        print("✓ Core dependency injection imports OK")
        
        # Test service registry
        from service_registry import get_service_registry
        print("✓ Service registry imports OK")
        
        # Test configuration loader
        from config_loader import ConfigurationData
        print("✓ Configuration loader imports OK")
        
        # Test main processing
        from main_processing import process_files, verify_configuration
        print("✓ Main processing imports OK")
        
        # Test main module
        from main import main
        print("✓ Main module imports OK")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_help_flag():
    """Test main.py --help functionality."""
    print("\n=== Testing --help Flag ===")
    
    try:
        # Call main with --help
        from main import main
        result = main(["--help"])
        print("✓ Help flag test completed")
        return True
        
    except SystemExit as e:
        # argparse calls sys.exit(0) for --help, which is expected
        if e.code == 0:
            print("✓ Help flag worked correctly (expected SystemExit)")
            return True
        else:
            print(f"✗ Help flag failed with exit code: {e.code}")
            return False
    except Exception as e:
        print(f"✗ Help flag test failed: {e}")
        return False

def test_dependency_injection():
    """Test the dependency injection framework."""
    print("\n=== Testing Dependency Injection ===")
    
    try:
        from core.dependency_injection import setup_default_services, get_container
        from service_registry import get_service_registry
        
        # Setup services
        setup_default_services()
        print("✓ Default services setup OK")
        
        # Get container
        container = get_container()
        print("✓ Container retrieval OK")
        
        # Get service registry
        registry = get_service_registry()
        registry.initialize()
        print("✓ Service registry initialization OK")
        
        # Test service resolution
        logging_service = registry.logging_service
        print("✓ Logging service resolution OK")
        
        return True
        
    except Exception as e:
        print(f"✗ Dependency injection test failed: {e}")
        return False

def test_dry_run():
    """Test dry run mode with a test directory."""
    print("\n=== Testing Dry Run Mode ===")
    
    try:
        # Create a test directory
        test_dir = Path(__file__).parent / "test_directory"
        test_dir.mkdir(exist_ok=True)
        
        # Create a test file
        test_file = test_dir / "Test Paper - Sample Author.pdf"
        test_file.touch()
        
        # Test main function with dry run
        from main import main
        result = main([str(test_dir), "--dry_run"])
        
        # Clean up
        test_file.unlink()
        test_dir.rmdir()
        
        print("✓ Dry run test completed")
        return True
        
    except Exception as e:
        print(f"✗ Dry run test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Math-PDF Manager System Tests")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Help Flag Test", test_help_flag),
        ("Dependency Injection Test", test_dependency_injection),
        ("Dry Run Test", test_dry_run)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            failed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    return failed == 0

if __name__ == "__main__":
    sys.exit(0 if main() else 1)