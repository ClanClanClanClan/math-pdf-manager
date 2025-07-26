#!/usr/bin/env python3
"""
Dependency Injection Integration Test
Phase 1, Week 2: Comprehensive DI Fix Validation

Test script to validate that the complete DI integration works properly.
"""

import sys
import traceback
from pathlib import Path

def test_di_import():
    """Test that DI framework can be imported."""
    print("🧪 Testing DI framework import...")
    try:
        from core.dependency_injection import (
            get_container, inject, 
            IConfigurationService, ILoggingService, IFileService, IValidationService,
            IMetricsService, INotificationService, ICacheService, ISecurityService,
            setup_default_services
        )
        print("✅ DI framework imports successfully")
        return True
    except Exception as e:
        print(f"❌ DI framework import failed: {e}")
        traceback.print_exc()
        return False

def test_service_registration():
    """Test that all services can be registered and resolved."""
    print("\n🧪 Testing service registration...")
    try:
        from core.dependency_injection import get_container, setup_default_services
        from core.dependency_injection.interfaces import (
            IConfigurationService, ILoggingService, IFileService, IValidationService,
            IMetricsService, INotificationService, ICacheService, ISecurityService
        )
        
        # Setup services
        container = setup_default_services()
        
        # Test resolution of all services
        services = {
            'config': container.resolve(IConfigurationService),
            'logging': container.resolve(ILoggingService),
            'file': container.resolve(IFileService),
            'validation': container.resolve(IValidationService),
            'metrics': container.resolve(IMetricsService),
            'notification': container.resolve(INotificationService),
            'cache': container.resolve(ICacheService),
            'security': container.resolve(ISecurityService),
        }
        
        print(f"✅ All 8 services resolved successfully")
        print(f"   Services: {list(services.keys())}")
        return True, services
    except Exception as e:
        print(f"❌ Service registration failed: {e}")
        traceback.print_exc()
        return False, {}

def test_service_functionality(services):
    """Test that services actually work."""
    print("\n🧪 Testing service functionality...")
    try:
        # Test logging service
        services['logging'].info("Test logging message")
        print("✅ Logging service works")
        
        # Test metrics service
        services['metrics'].increment_counter("test_counter")
        services['metrics'].record_gauge("test_gauge", 42.0)
        print("✅ Metrics service works")
        
        # Test notification service
        services['notification'].send_notification("Test notification", "info")
        print("✅ Notification service works")
        
        # Test cache service
        services['cache'].set("test_key", "test_value")
        cached_value = services['cache'].get("test_key")
        assert cached_value == "test_value"
        print("✅ Cache service works")
        
        # Test configuration service
        services['config'].set("test_config", "test_value")
        config_value = services['config'].get("test_config")
        assert config_value == "test_value"
        print("✅ Configuration service works")
        
        # Test validation service
        test_email = services['validation'].validate_email("test@example.com")
        assert test_email is True
        print("✅ Validation service works")
        
        # Test security service
        hashed = services['security'].hash_password("test_password")
        verified = services['security'].verify_password("test_password", hashed)
        assert verified is True
        print("✅ Security service works")
        
        # Test file service (simple existence check)
        test_file = Path(__file__)
        exists = services['file'].exists(test_file)
        assert exists is True
        print("✅ File service works")
        
        return True
    except Exception as e:
        print(f"❌ Service functionality test failed: {e}")
        traceback.print_exc()
        return False

def test_main_import():
    """Test that main.py can be imported with DI changes."""
    print("\n🧪 Testing main.py import...")
    try:
        # Add current directory to path
        current_dir = Path(__file__).parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        
        import main
        print("✅ main.py imports successfully")
        return True
    except Exception as e:
        print(f"❌ main.py import failed: {e}")
        traceback.print_exc()
        return False

def test_inject_decorator():
    """Test that the @inject decorator works."""
    print("\n🧪 Testing @inject decorator...")
    try:
        from core.dependency_injection import inject, ILoggingService, setup_default_services
        
        # Setup services first
        setup_default_services()
        
        @inject(ILoggingService, name="logging_service")
        def test_function(message: str, logging_service: ILoggingService = None):
            logging_service.info(f"Decorator test: {message}")
            return "success"
        
        result = test_function("Hello from decorator test!")
        assert result == "success"
        print("✅ @inject decorator works")
        return True
    except Exception as e:
        print(f"❌ @inject decorator test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all integration tests."""
    print("🧪 DEPENDENCY INJECTION INTEGRATION TESTS")
    print("=" * 50)
    
    results = []
    services = {}
    
    # Test 1: DI Framework Import
    results.append(test_di_import())
    
    # Test 2: Service Registration
    if results[-1]:
        success, services = test_service_registration()
        results.append(success)
    else:
        results.append(False)
    
    # Test 3: Service Functionality
    if results[-1] and services:
        results.append(test_service_functionality(services))
    else:
        results.append(False)
    
    # Test 4: Inject Decorator
    results.append(test_inject_decorator())
    
    # Test 5: Main.py Import
    results.append(test_main_import())
    
    # Summary
    print("\n📊 TEST RESULTS")
    print("=" * 30)
    
    test_names = [
        "DI Framework Import",
        "Service Registration", 
        "Service Functionality",
        "Inject Decorator",
        "Main.py Import"
    ]
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {name}: {status}")
    
    print(f"\nOVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - DI INTEGRATION IS WORKING!")
        return 0
    else:
        print("🚨 SOME TESTS FAILED - DI INTEGRATION NEEDS FIXES")
        return 1

if __name__ == "__main__":
    sys.exit(main())