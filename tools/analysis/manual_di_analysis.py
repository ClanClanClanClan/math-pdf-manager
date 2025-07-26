#!/usr/bin/env python3
"""
Manual analysis of the DI framework by examining imports step by step.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

print("MANUAL DI FRAMEWORK ANALYSIS")
print("=" * 60)

def test_step_by_step():
    """Test each component step by step to identify the exact failure point."""
    
    # Step 1: Test core config import
    print("Step 1: Testing core.config.secure_config import...")
    try:
        from core.config.secure_config import SecureConfigManager
        print("✓ SecureConfigManager import: SUCCESS")
        
        # Test instantiation
        config_manager = SecureConfigManager()
        print("✓ SecureConfigManager instantiation: SUCCESS")
        
    except Exception as e:
        print(f"✗ SecureConfigManager: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Test DI container import
    print("\nStep 2: Testing core.dependency_injection.container import...")
    try:
        from core.dependency_injection.container import DIContainer
        print("✓ DIContainer import: SUCCESS")
        
        # Test instantiation
        container = DIContainer()
        print("✓ DIContainer instantiation: SUCCESS")
        
    except Exception as e:
        print(f"✗ DIContainer: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Test interfaces import
    print("\nStep 3: Testing core.dependency_injection.interfaces import...")
    try:
        from core.dependency_injection.interfaces import (
            IConfigurationService, ILoggingService, IFileService, IValidationService,
            IMetricsService, INotificationService, ICacheService, ISecurityService
        )
        print("✓ All interfaces import: SUCCESS")
        
    except Exception as e:
        print(f"✗ Interfaces: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Test implementations import (this is where issues might occur)
    print("\nStep 4: Testing core.dependency_injection.implementations import...")
    try:
        from core.dependency_injection.implementations import ConfigurationService
        print("✓ ConfigurationService import: SUCCESS")
        
        from core.dependency_injection.implementations import LoggingService
        print("✓ LoggingService import: SUCCESS")
        
        from core.dependency_injection.implementations import FileService
        print("✓ FileService import: SUCCESS")
        
        from core.dependency_injection.implementations import ValidationService
        print("✓ ValidationService import: SUCCESS")
        
        from core.dependency_injection.implementations import MetricsService
        print("✓ MetricsService import: SUCCESS")
        
        from core.dependency_injection.implementations import NotificationService
        print("✓ NotificationService import: SUCCESS")
        
        from core.dependency_injection.implementations import InMemoryCacheService
        print("✓ InMemoryCacheService import: SUCCESS")
        
        from core.dependency_injection.implementations import SecurityService
        print("✓ SecurityService import: SUCCESS")
        
    except Exception as e:
        print(f"✗ Implementations: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Test DI __init__ import
    print("\nStep 5: Testing core.dependency_injection.__init__ import...")
    try:
        from core.dependency_injection import get_container
        print("✓ get_container import: SUCCESS")
        
        from core.dependency_injection import setup_default_services
        print("✓ setup_default_services import: SUCCESS")
        
    except Exception as e:
        print(f"✗ DI __init__: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Test setup_default_services execution
    print("\nStep 6: Testing setup_default_services execution...")
    try:
        container = setup_default_services()
        print("✓ setup_default_services execution: SUCCESS")
        print(f"✓ Container returned: {type(container).__name__}")
        
    except Exception as e:
        print(f"✗ setup_default_services execution: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 7: Test service resolution
    print("\nStep 7: Testing individual service resolution...")
    
    services_to_test = [
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
    for service_name, service_interface in services_to_test:
        try:
            service_instance = container.resolve(service_interface)
            print(f"✓ {service_name}: SUCCESS - {type(service_instance).__name__}")
            resolved_count += 1
        except Exception as e:
            print(f"✗ {service_name}: FAILED - {e}")
            # Don't print traceback for each service failure to keep output clean
    
    print(f"\nService Resolution Summary: {resolved_count}/8 services resolved")
    
    # Step 8: Test @inject decorator
    print("\nStep 8: Testing @inject decorator...")
    try:
        from core.dependency_injection import inject
        
        @inject(ILoggingService)
        def test_function(message: str, loggingservice: ILoggingService):
            loggingservice.info(f"Test: {message}")
            return "injection_worked"
        
        result = test_function("Testing injection")
        if result == "injection_worked":
            print("✓ @inject decorator: SUCCESS")
        else:
            print("✗ @inject decorator: FAILED - Unexpected result")
            
    except Exception as e:
        print(f"✗ @inject decorator: FAILED - {e}")
        import traceback
        traceback.print_exc()
    
    return True

def analyze_service_dependencies():
    """Analyze the dependency chain to understand what might be failing."""
    
    print("\n" + "=" * 60)
    print("ANALYZING SERVICE DEPENDENCIES")
    print("=" * 60)
    
    try:
        from core.dependency_injection.implementations import (
            ConfigurationService, LoggingService, FileService, ValidationService,
            MetricsService, NotificationService, InMemoryCacheService, SecurityService
        )
        from core.dependency_injection.interfaces import IConfigurationService
        
        print("Service Dependencies Analysis:")
        print("1. ConfigurationService: No dependencies")
        print("2. LoggingService: Depends on IConfigurationService")
        print("3. FileService: Depends on ILoggingService")
        print("4. ValidationService: Depends on ILoggingService")
        print("5. MetricsService: Depends on ILoggingService")
        print("6. NotificationService: Depends on ILoggingService")
        print("7. InMemoryCacheService: Depends on ILoggingService")
        print("8. SecurityService: Depends on ILoggingService")
        
        print("\nTesting manual instantiation:")
        
        # Test ConfigurationService (no dependencies)
        config_service = ConfigurationService()
        print("✓ ConfigurationService: Manual instantiation SUCCESS")
        
        # Test LoggingService (needs IConfigurationService)
        logging_service = LoggingService(config_service)
        print("✓ LoggingService: Manual instantiation SUCCESS")
        
        # Test services that depend on LoggingService
        file_service = FileService(logging_service)
        print("✓ FileService: Manual instantiation SUCCESS")
        
        validation_service = ValidationService(logging_service)
        print("✓ ValidationService: Manual instantiation SUCCESS")
        
        metrics_service = MetricsService(logging_service)
        print("✓ MetricsService: Manual instantiation SUCCESS")
        
        notification_service = NotificationService(logging_service)
        print("✓ NotificationService: Manual instantiation SUCCESS")
        
        cache_service = InMemoryCacheService(logging_service)
        print("✓ InMemoryCacheService: Manual instantiation SUCCESS")
        
        security_service = SecurityService(logging_service)
        print("✓ SecurityService: Manual instantiation SUCCESS")
        
        print("\n✓ ALL SERVICES CAN BE MANUALLY INSTANTIATED")
        print("✓ This suggests the issue is in the DI container's auto-wiring logic")
        
    except Exception as e:
        print(f"✗ Manual instantiation failed: {e}")
        import traceback
        traceback.print_exc()

def test_service_decorator_registration():
    """Test if the @service decorator is working correctly."""
    
    print("\n" + "=" * 60)
    print("TESTING @service DECORATOR REGISTRATION")
    print("=" * 60)
    
    try:
        from core.dependency_injection import get_container
        from core.dependency_injection.interfaces import (
            IConfigurationService, ILoggingService, IFileService, IValidationService,
            IMetricsService, INotificationService, ICacheService, ISecurityService
        )
        
        container = get_container()
        
        # Check if services are registered in the container
        print("Checking container registrations:")
        
        # The services should be auto-registered when the implementations module is imported
        # Let's import the implementations to trigger registration
        import core.dependency_injection.implementations
        
        # Now check what's in the container
        services_to_check = [
            IConfigurationService, ILoggingService, IFileService, IValidationService,
            IMetricsService, INotificationService, ICacheService, ISecurityService
        ]
        
        for service_interface in services_to_check:
            service_name = service_interface.__name__
            
            # Check if it's registered as singleton
            if service_name in container._singletons:
                print(f"✓ {service_name}: Registered as SINGLETON")
            elif service_name in container._transients:
                print(f"✓ {service_name}: Registered as TRANSIENT")
            elif service_name in container._services:
                print(f"✓ {service_name}: Registered as SERVICE INSTANCE")
            elif service_name in container._factories:
                print(f"✓ {service_name}: Registered as FACTORY")
            else:
                print(f"✗ {service_name}: NOT REGISTERED")
        
    except Exception as e:
        print(f"✗ Service registration check failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting manual DI framework analysis...\n")
    
    success = test_step_by_step()
    
    if success:
        analyze_service_dependencies()
        test_service_decorator_registration()
        
        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)
        print("The DI framework appears to be working correctly!")
        print("If there are issues, they are likely in:")
        print("1. Service auto-registration (@service decorator)")
        print("2. Container resolution logic")
        print("3. Dependency injection in container._create_instance()")
    else:
        print("\n" + "=" * 60)
        print("ANALYSIS FAILED")
        print("=" * 60)
        print("Critical errors prevent the DI framework from working.")