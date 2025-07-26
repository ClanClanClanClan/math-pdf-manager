#!/usr/bin/env python3
"""
Comprehensive Dependency Injection Framework Test
Tests all claimed functionality and identifies any issues.
"""

import sys
import traceback
from pathlib import Path
from typing import Dict, List, Any

def test_di_framework():
    """Comprehensive test of the DI framework."""
    
    results = {
        'import_tests': {},
        'setup_tests': {},
        'resolution_tests': {},
        'injection_tests': {},
        'errors': [],
        'summary': {}
    }
    
    print("=" * 80)
    print("COMPREHENSIVE DEPENDENCY INJECTION FRAMEWORK TEST")
    print("=" * 80)
    
    # Test 1: Import all DI components
    print("\n1. TESTING IMPORTS")
    print("-" * 40)
    
    import_tests = [
        ('DIContainer', 'from core.dependency_injection import DIContainer'),
        ('get_container', 'from core.dependency_injection import get_container'),
        ('inject', 'from core.dependency_injection import inject'),
        ('service', 'from core.dependency_injection import service'),
        ('setup_default_services', 'from core.dependency_injection import setup_default_services'),
        ('Interfaces', 'from core.dependency_injection import IConfigurationService, ILoggingService, IFileService, IValidationService, IMetricsService, INotificationService, ICacheService, ISecurityService'),
        ('Implementations', 'from core.dependency_injection import ConfigurationService, LoggingService, FileService, ValidationService, MetricsService, NotificationService, InMemoryCacheService, SecurityService')
    ]
    
    for test_name, import_statement in import_tests:
        try:
            exec(import_statement)
            results['import_tests'][test_name] = 'SUCCESS'
            print(f"✓ {test_name}: SUCCESS")
        except Exception as e:
            results['import_tests'][test_name] = f'FAILED: {str(e)}'
            results['errors'].append(f"Import {test_name}: {str(e)}")
            print(f"✗ {test_name}: FAILED - {str(e)}")
    
    # Test 2: Test setup_default_services()
    print("\n2. TESTING SETUP_DEFAULT_SERVICES")
    print("-" * 40)
    
    try:
        from core.dependency_injection import setup_default_services, get_container
        container = setup_default_services()
        results['setup_tests']['setup_default_services'] = 'SUCCESS'
        print("✓ setup_default_services(): SUCCESS")
        
        # Verify container is not None
        if container is not None:
            results['setup_tests']['container_returned'] = 'SUCCESS'
            print("✓ Container returned: SUCCESS")
        else:
            results['setup_tests']['container_returned'] = 'FAILED: None returned'
            print("✗ Container returned: FAILED - None returned")
            
    except Exception as e:
        results['setup_tests']['setup_default_services'] = f'FAILED: {str(e)}'
        results['errors'].append(f"setup_default_services: {str(e)}")
        print(f"✗ setup_default_services(): FAILED - {str(e)}")
        traceback.print_exc()
    
    # Test 3: Test service resolution
    print("\n3. TESTING SERVICE RESOLUTION")
    print("-" * 40)
    
    try:
        from core.dependency_injection import (
            get_container, IConfigurationService, ILoggingService, IFileService, 
            IValidationService, IMetricsService, INotificationService, ICacheService, ISecurityService
        )
        
        container = get_container()
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
        
        resolved_services = {}
        for service_name, service_interface in services_to_test:
            try:
                service_instance = container.resolve(service_interface)
                results['resolution_tests'][service_name] = 'SUCCESS'
                resolved_services[service_name] = service_instance
                print(f"✓ {service_name}: SUCCESS - {type(service_instance).__name__}")
            except Exception as e:
                results['resolution_tests'][service_name] = f'FAILED: {str(e)}'
                results['errors'].append(f"Resolve {service_name}: {str(e)}")
                print(f"✗ {service_name}: FAILED - {str(e)}")
                
    except Exception as e:
        results['errors'].append(f"Service resolution setup: {str(e)}")
        print(f"✗ Service resolution setup: FAILED - {str(e)}")
        traceback.print_exc()
    
    # Test 4: Test @inject decorator
    print("\n4. TESTING @inject DECORATOR")
    print("-" * 40)
    
    try:
        from core.dependency_injection import inject, ILoggingService
        
        @inject(ILoggingService)
        def test_function_with_injection(message: str, loggingservice: ILoggingService):
            loggingservice.info(f"Test message: {message}")
            return "SUCCESS"
        
        # Test the decorated function
        result = test_function_with_injection("Testing injection")
        if result == "SUCCESS":
            results['injection_tests']['inject_decorator'] = 'SUCCESS'
            print("✓ @inject decorator: SUCCESS")
        else:
            results['injection_tests']['inject_decorator'] = 'FAILED: Unexpected result'
            print("✗ @inject decorator: FAILED - Unexpected result")
            
    except Exception as e:
        results['injection_tests']['inject_decorator'] = f'FAILED: {str(e)}'
        results['errors'].append(f"@inject decorator: {str(e)}")
        print(f"✗ @inject decorator: FAILED - {str(e)}")
        traceback.print_exc()
    
    # Test 5: Test service functionality
    print("\n5. TESTING SERVICE FUNCTIONALITY")
    print("-" * 40)
    
    try:
        # Test configuration service
        if 'IConfigurationService' in resolved_services:
            config_service = resolved_services['IConfigurationService']
            try:
                config_service.set('test_key', 'test_value')
                value = config_service.get('test_key')
                if value == 'test_value':
                    print("✓ ConfigurationService: SUCCESS")
                    results['resolution_tests']['IConfigurationService_functionality'] = 'SUCCESS'
                else:
                    print("✗ ConfigurationService: FAILED - Value mismatch")
                    results['resolution_tests']['IConfigurationService_functionality'] = 'FAILED: Value mismatch'
            except Exception as e:
                print(f"✗ ConfigurationService: FAILED - {str(e)}")
                results['resolution_tests']['IConfigurationService_functionality'] = f'FAILED: {str(e)}'
        
        # Test cache service
        if 'ICacheService' in resolved_services:
            cache_service = resolved_services['ICacheService']
            try:
                cache_service.set('test_cache', 'cache_value')
                cached_value = cache_service.get('test_cache')
                if cached_value == 'cache_value':
                    print("✓ CacheService: SUCCESS")
                    results['resolution_tests']['ICacheService_functionality'] = 'SUCCESS'
                else:
                    print("✗ CacheService: FAILED - Value mismatch")
                    results['resolution_tests']['ICacheService_functionality'] = 'FAILED: Value mismatch'
            except Exception as e:
                print(f"✗ CacheService: FAILED - {str(e)}")
                results['resolution_tests']['ICacheService_functionality'] = f'FAILED: {str(e)}'
        
        # Test security service
        if 'ISecurityService' in resolved_services:
            security_service = resolved_services['ISecurityService']
            try:
                password = "test_password"
                hash_value = security_service.hash_password(password)
                is_valid = security_service.verify_password(password, hash_value)
                if is_valid:
                    print("✓ SecurityService: SUCCESS")
                    results['resolution_tests']['ISecurityService_functionality'] = 'SUCCESS'
                else:
                    print("✗ SecurityService: FAILED - Password verification failed")
                    results['resolution_tests']['ISecurityService_functionality'] = 'FAILED: Password verification failed'
            except Exception as e:
                print(f"✗ SecurityService: FAILED - {str(e)}")
                results['resolution_tests']['ISecurityService_functionality'] = f'FAILED: {str(e)}'
        
    except Exception as e:
        results['errors'].append(f"Service functionality tests: {str(e)}")
        print(f"✗ Service functionality tests: FAILED - {str(e)}")
        traceback.print_exc()
    
    # Test 6: Test missing dependencies/configuration
    print("\n6. TESTING MISSING DEPENDENCIES")
    print("-" * 40)
    
    try:
        # Check for secure credential manager
        try:
            from secure_credential_manager import SecureCredentialManager
            print("✓ SecureCredentialManager: AVAILABLE")
            results['setup_tests']['secure_credential_manager'] = 'AVAILABLE'
        except ImportError:
            print("⚠ SecureCredentialManager: NOT AVAILABLE (using fallback)")
            results['setup_tests']['secure_credential_manager'] = 'NOT_AVAILABLE'
        
        # Check for config file
        config_file = Path("config.yaml")
        if config_file.exists():
            print("✓ config.yaml: EXISTS")
            results['setup_tests']['config_file'] = 'EXISTS'
        else:
            print("⚠ config.yaml: NOT FOUND")
            results['setup_tests']['config_file'] = 'NOT_FOUND'
            
    except Exception as e:
        results['errors'].append(f"Dependency checks: {str(e)}")
        print(f"✗ Dependency checks: FAILED - {str(e)}")
    
    # Generate summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_tests = 0
    passed_tests = 0
    
    for category, tests in results.items():
        if category == 'errors' or category == 'summary':
            continue
        for test, result in tests.items():
            total_tests += 1
            if result == 'SUCCESS':
                passed_tests += 1
    
    results['summary'] = {
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': total_tests - passed_tests,
        'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
        'total_errors': len(results['errors'])
    }
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
    print(f"Total Errors: {len(results['errors'])}")
    
    if results['errors']:
        print("\nERRORS ENCOUNTERED:")
        for i, error in enumerate(results['errors'], 1):
            print(f"{i}. {error}")
    
    # Detailed verification of the "8 services" claim
    print("\n" + "=" * 80)
    print("VERIFICATION OF '8 SERVICES' CLAIM")
    print("=" * 80)
    
    expected_services = [
        'IConfigurationService', 'ILoggingService', 'IFileService', 'IValidationService',
        'IMetricsService', 'INotificationService', 'ICacheService', 'ISecurityService'
    ]
    
    resolved_count = 0
    for service in expected_services:
        if service in results['resolution_tests'] and results['resolution_tests'][service] == 'SUCCESS':
            resolved_count += 1
            print(f"✓ {service}: RESOLVED")
        else:
            print(f"✗ {service}: NOT RESOLVED")
    
    print(f"\nServices resolved: {resolved_count}/8")
    if resolved_count == 8:
        print("✓ CLAIM VERIFIED: All 8 services register and resolve")
    else:
        print("✗ CLAIM FAILED: Not all 8 services register and resolve")
    
    return results

if __name__ == "__main__":
    try:
        results = test_di_framework()
        
        # Exit with appropriate code
        if results['summary']['failed_tests'] == 0:
            print("\n🎉 ALL TESTS PASSED!")
            sys.exit(0)
        else:
            print(f"\n❌ {results['summary']['failed_tests']} TESTS FAILED")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        traceback.print_exc()
        sys.exit(2)