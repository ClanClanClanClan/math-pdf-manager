#!/usr/bin/env python3
"""
Test script with fixes for missing dependencies
"""
import sys
import os
import traceback
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_basic_functionality():
    """Test the basic functionality of the system."""
    print("=== Basic Functionality Test ===")
    
    try:
        # Test 1: Import main module
        print("1. Testing main import...")
        from main import main
        print("   ✓ main imported successfully")
        
        # Test 2: Test help flag
        print("2. Testing help flag...")
        try:
            main(['--help'])
            print("   ✗ Help should have exited")
            return False
        except SystemExit as e:
            if e.code == 0:
                print("   ✓ Help flag works correctly")
            else:
                print(f"   ✗ Help exited with code {e.code}")
                return False
        except Exception as e:
            print(f"   ✗ Help failed: {e}")
            return False
        
        # Test 3: Test dry run with current directory
        print("3. Testing dry run with current directory...")
        try:
            main([str(Path.cwd()), '--dry_run'])
            print("   ✓ Dry run completed successfully")
        except Exception as e:
            print(f"   ✗ Dry run failed: {e}")
            traceback.print_exc()
            return False
        
        # Test 4: Test with a specific test directory
        print("4. Testing with test directory...")
        test_dir = Path("test_temp")
        test_dir.mkdir(exist_ok=True)
        
        # Create a test file
        test_file = test_dir / "Test Author - Sample Paper.pdf"
        test_file.touch()
        
        try:
            main([str(test_dir), '--dry_run', '--verbose'])
            print("   ✓ Test directory processing completed")
            success = True
        except Exception as e:
            print(f"   ✗ Test directory processing failed: {e}")
            success = False
        finally:
            # Clean up
            test_file.unlink(missing_ok=True)
            test_dir.rmdir()
        
        return success
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        traceback.print_exc()
        return False

def test_dependency_injection():
    """Test dependency injection framework."""
    print("\n=== Dependency Injection Test ===")
    
    try:
        # Test service registry
        from service_registry import get_service_registry
        registry = get_service_registry()
        registry.initialize()
        print("✓ Service registry initialized")
        
        # Test service resolution
        logging_service = registry.logging_service
        logging_service.info("Test message from DI framework")
        print("✓ Logging service working")
        
        return True
        
    except Exception as e:
        print(f"✗ DI test failed: {e}")
        traceback.print_exc()
        return False

def test_configuration_loading():
    """Test configuration loading."""
    print("\n=== Configuration Loading Test ===")
    
    try:
        from config_loader import ConfigurationData
        from pathlib import Path
        
        config_data = ConfigurationData()
        
        # Create a mock args object
        class MockArgs:
            def __init__(self):
                self.exceptions_file = None
        
        args = MockArgs()
        script_dir = Path(__file__).parent
        
        config_data.load_all(args, script_dir)
        print("✓ Configuration loaded successfully")
        
        # Check loaded data
        print(f"   Known words: {len(config_data.known_words)}")
        print(f"   Exceptions: {len(config_data.exceptions)}")
        print(f"   Compound terms: {len(config_data.compound_terms)}")
        print(f"   Capitalization whitelist: {len(config_data.capitalization_whitelist)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Math-PDF Manager System Testing")
    print("=" * 50)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Dependency Injection", test_dependency_injection),
        ("Configuration Loading", test_configuration_loading),
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
    
    print(f"\n{'='*50}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The system is working correctly.")
        print("\nYou can now run the main system with:")
        print("  python main.py --help")
        print("  python main.py /path/to/directory --dry_run")
    else:
        print(f"⚠️  {failed} test(s) failed. See output above for details.")
    
    return failed == 0

if __name__ == "__main__":
    sys.exit(0 if main() else 1)