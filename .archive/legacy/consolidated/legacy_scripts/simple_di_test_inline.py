#!/usr/bin/env python3
"""
Simple inline DI test to verify functionality without shell dependencies.
"""

import sys
import os

# Add the current directory to Python path
current_dir = "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts"
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_imports():
    """Test importing DI components."""
    print("Testing DI Framework Imports...")
    
    # Test 1: Import DIContainer
    try:
        from core.dependency_injection import DIContainer
        print("✓ DIContainer: SUCCESS")
    except Exception as e:
        print(f"✗ DIContainer: FAILED - {e}")
        return False
    
    # Test 2: Import get_container
    try:
        from core.dependency_injection import get_container
        print("✓ get_container: SUCCESS")
    except Exception as e:
        print(f"✗ get_container: FAILED - {e}")
        return False
    
    # Test 3: Import setup_default_services
    try:
        from core.dependency_injection import setup_default_services
        print("✓ setup_default_services: SUCCESS")
    except Exception as e:
        print(f"✗ setup_default_services: FAILED - {e}")
        return False
    
    # Test 4: Import interfaces
    try:
        from core.dependency_injection import (
            IConfigurationService, ILoggingService, IFileService, IValidationService,
            IMetricsService, INotificationService, ICacheService, ISecurityService
        )
        print("✓ All interfaces: SUCCESS")
    except Exception as e:
        print(f"✗ All interfaces: FAILED - {e}")
        return False
    
    # Test 5: Import implementations
    try:
        from core.dependency_injection import (
            ConfigurationService, LoggingService, FileService, ValidationService,
            MetricsService, NotificationService, InMemoryCacheService, SecurityService
        )
        print("✓ All implementations: SUCCESS")
    except Exception as e:
        print(f"✗ All implementations: FAILED - {e}")
        return False
    
    return True

def test_setup():
    """Test setup_default_services function."""
    print("\nTesting setup_default_services...")
    
    try:
        from core.dependency_injection import setup_default_services
        container = setup_default_services()
        print("✓ setup_default_services: SUCCESS")
        return container
    except Exception as e:
        print(f"✗ setup_default_services: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return None

def test_service_resolution(container):
    """Test service resolution."""
    print("\nTesting service resolution...")
    
    if container is None:
        print("✗ Cannot test resolution - no container")
        return False
    
    try:
        from core.dependency_injection import (
            IConfigurationService, ILoggingService, IFileService, IValidationService,
            IMetricsService, INotificationService, ICacheService, ISecurityService
        )
        
        services = [
            ('IConfigurationService', IConfigurationService),
            ('ILoggingService', ILoggingService),
            ('IFileService', IFileService),
            ('IValidationService', IValidationService),
            ('IMetricsService', IMetricsService),
            ('INotificationService', INotificationService),
            ('ICacheService', ICacheService),
            ('ISecurityService', ISecurityService)
        ]
        
        resolved_count = 0
        for name, interface in services:
            try:
                service = container.resolve(interface)
                print(f"✓ {name}: SUCCESS - {type(service).__name__}")
                resolved_count += 1
            except Exception as e:
                print(f"✗ {name}: FAILED - {e}")
        
        print(f"\nServices resolved: {resolved_count}/8")
        return resolved_count == 8
        
    except Exception as e:
        print(f"✗ Service resolution setup: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

def test_inject_decorator():
    """Test the @inject decorator."""
    print("\nTesting @inject decorator...")
    
    try:
        from core.dependency_injection import inject, ILoggingService
        
        @inject(ILoggingService)
        def test_function(message: str, loggingservice: ILoggingService):
            loggingservice.info(f"Test: {message}")
            return "injection_success"
        
        result = test_function("Testing injection")
        if result == "injection_success":
            print("✓ @inject decorator: SUCCESS")
            return True
        else:
            print("✗ @inject decorator: FAILED - Unexpected result")
            return False
            
    except Exception as e:
        print(f"✗ @inject decorator: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DEPENDENCY INJECTION FRAMEWORK TEST")
    print("=" * 60)
    
    # Test imports
    imports_ok = test_imports()
    
    if not imports_ok:
        print("\n❌ CRITICAL: Cannot proceed - imports failed")
        sys.exit(1)
    
    # Test setup
    container = test_setup()
    
    # Test service resolution
    resolution_ok = test_service_resolution(container)
    
    # Test injection decorator
    injection_ok = test_inject_decorator()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print(f"Imports: {'PASS' if imports_ok else 'FAIL'}")
    print(f"Setup: {'PASS' if container is not None else 'FAIL'}")
    print(f"Resolution: {'PASS' if resolution_ok else 'FAIL'}")
    print(f"Injection: {'PASS' if injection_ok else 'FAIL'}")
    
    all_pass = imports_ok and container is not None and resolution_ok and injection_ok
    
    if all_pass:
        print("\n🎉 ALL TESTS PASSED!")
        print("✓ DI framework imports successfully")
        print("✓ All 8 services register and resolve")
        print("✓ @inject decorator works")
    else:
        print("\n❌ SOME TESTS FAILED!")
        
    print("\n" + "=" * 60)