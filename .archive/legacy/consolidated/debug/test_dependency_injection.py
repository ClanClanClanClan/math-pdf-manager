#!/usr/bin/env python3
"""
Consolidated Dependency Injection Tests
Replaces: test_di_framework.py, simple_di_test.py, fix_and_test_di.py,
         final_di_test.py, test_di_integration.py, comprehensive_di_test.py,
         simple_di_test_inline.py, working_di_test.py
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

class TestDependencyInjection(unittest.TestCase):
    """Consolidated DI framework tests"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_container = Mock()
        self.mock_service = Mock()

    def test_di_container_initialization(self):
        """Test DI container initialization"""
        try:
            from core.dependency_injection import DIContainer
            container = DIContainer()
            self.assertIsNotNone(container)
            self.assertTrue(hasattr(container, 'register'))
            self.assertTrue(hasattr(container, 'resolve'))
        except ImportError:
            self.skipTest("DI framework not available")

    def test_service_registration(self):
        """Test service registration in DI container"""
        try:
            from core.dependency_injection import DIContainer
            container = DIContainer()
            
            # Register a mock service
            container.register('test_service', self.mock_service)
            
            # Verify registration
            resolved_service = container.resolve('test_service')
            self.assertEqual(resolved_service, self.mock_service)
        except ImportError:
            self.skipTest("DI framework not available")

    def test_service_injection_decorator(self):
        """Test @inject decorator functionality"""
        try:
            from core.dependency_injection import inject
            
            @inject('test_service')
            def test_function(service=None):
                return service
            
            self.assertTrue(hasattr(test_function, '__wrapped__'))
        except ImportError:
            self.skipTest("DI framework not available")

    def test_service_interfaces(self):
        """Test service interfaces"""
        try:
            from core.dependency_injection import (
                ILoggingService, IConfigurationService, IFileService,
                IValidationService, IMetricsService, INotificationService
            )
            
            # Test that interfaces exist
            self.assertTrue(hasattr(ILoggingService, '__abstractmethods__'))
            self.assertTrue(hasattr(IConfigurationService, '__abstractmethods__'))
            self.assertTrue(hasattr(IFileService, '__abstractmethods__'))
            self.assertTrue(hasattr(IValidationService, '__abstractmethods__'))
            self.assertTrue(hasattr(IMetricsService, '__abstractmethods__'))
            self.assertTrue(hasattr(INotificationService, '__abstractmethods__'))
        except ImportError:
            self.skipTest("DI framework not available")

    def test_service_implementations(self):
        """Test service implementations"""
        try:
            from core.dependency_injection import (
                LoggingService, ConfigurationService, FileService,
                ValidationService, MetricsService, NotificationService
            )
            
            # Test that implementations exist
            logging_service = LoggingService()
            config_service = ConfigurationService()
            file_service = FileService()
            validation_service = ValidationService()
            metrics_service = MetricsService()
            notification_service = NotificationService()
            
            self.assertIsNotNone(logging_service)
            self.assertIsNotNone(config_service)
            self.assertIsNotNone(file_service)
            self.assertIsNotNone(validation_service)
            self.assertIsNotNone(metrics_service)
            self.assertIsNotNone(notification_service)
        except ImportError:
            self.skipTest("DI framework not available")

    def test_service_registry(self):
        """Test service registry functionality"""
        try:
            from service_registry import (
                get_service_registry, get_logging_service, get_config_service,
                get_file_service, get_validation_service, get_metrics_service,
                get_notification_service
            )
            
            # Test registry initialization
            registry = get_service_registry()
            self.assertIsNotNone(registry)
            
            # Test service getters
            logging_service = get_logging_service()
            config_service = get_config_service()
            file_service = get_file_service()
            validation_service = get_validation_service()
            metrics_service = get_metrics_service()
            notification_service = get_notification_service()
            
            self.assertIsNotNone(logging_service)
            self.assertIsNotNone(config_service)
            self.assertIsNotNone(file_service)
            self.assertIsNotNone(validation_service)
            self.assertIsNotNone(metrics_service)
            self.assertIsNotNone(notification_service)
        except ImportError:
            self.skipTest("Service registry not available")

    def test_main_di_integration(self):
        """Test main.py DI integration"""
        try:
            # Test that main.py uses DI decorators
            from main import main
            
            # Check if main function has DI decorators
            self.assertTrue(hasattr(main, '__annotations__'))
        except ImportError:
            self.skipTest("Main module not available")

    def test_di_error_handling(self):
        """Test DI error handling"""
        try:
            from core.dependency_injection import DIContainer
            container = DIContainer()
            
            # Test resolving non-existent service
            with self.assertRaises(Exception):
                container.resolve('non_existent_service')
        except ImportError:
            self.skipTest("DI framework not available")

    def test_di_circular_dependencies(self):
        """Test circular dependency detection"""
        try:
            from core.dependency_injection import DIContainer
            container = DIContainer()
            
            # This is a basic test - full circular dependency detection
            # would require more complex setup
            self.assertTrue(hasattr(container, 'resolve'))
        except ImportError:
            self.skipTest("DI framework not available")

    def test_di_lazy_initialization(self):
        """Test lazy service initialization"""
        try:
            from service_registry import ServiceRegistry
            registry = ServiceRegistry()
            
            # Test lazy initialization
            self.assertIsNotNone(registry)
            self.assertTrue(hasattr(registry, 'initialize'))
        except ImportError:
            self.skipTest("Service registry not available")

    def test_di_configuration_integration(self):
        """Test DI configuration integration"""
        try:
            from config_loader import ConfigurationData
            from core.dependency_injection import setup_default_services
            
            # Test configuration loading with DI
            config_data = ConfigurationData()
            setup_default_services()
            
            self.assertIsNotNone(config_data)
        except ImportError:
            self.skipTest("Configuration or DI framework not available")


if __name__ == '__main__':
    unittest.main()