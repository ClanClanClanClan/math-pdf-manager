#!/usr/bin/env python3
"""
Dependency Injection Module
Phase 1, Week 2: Strategic Transformation

Provides dependency injection framework for reducing coupling and improving testability.
"""

from .container import DIContainer, get_container, inject, service
from .interfaces import (
    IConfigurationService, ILoggingService, IFileService, IValidationService,
    IMetricsService, INotificationService, ICacheService, ISecurityService
)
from .implementations import (
    ConfigurationService, LoggingService, FileService,
    MetricsService, NotificationService, InMemoryCacheService, SecurityService
)
from .validation_service import UnifiedValidationService

__all__ = [
    # Container
    'DIContainer',
    'get_container',
    'inject',
    'service',
    
    # Interfaces
    'IConfigurationService',
    'ILoggingService', 
    'IFileService',
    'IValidationService',
    'IMetricsService',
    'INotificationService',
    'ICacheService',
    'ISecurityService',
    
    # Implementations
    'ConfigurationService',
    'LoggingService',
    'FileService',
    'UnifiedValidationService',
    'MetricsService',
    'NotificationService',
    'InMemoryCacheService',
    'SecurityService'
]

def setup_default_services():
    """Setup default service registrations."""
    container = get_container()
    
    # Import all implementations to trigger auto-registration
    from .implementations import (
        ConfigurationService, LoggingService, FileService,
        MetricsService, NotificationService, InMemoryCacheService, SecurityService
    )
    from .validation_service import UnifiedValidationService
    
    # Services are auto-registered via @service decorator when imported
    # Also register with names for @inject decorator compatibility
    container.register_singleton(IConfigurationService, ConfigurationService, "config_service")
    container.register_singleton(ILoggingService, LoggingService, "logging_service")
    container.register_singleton(IFileService, FileService, "file_service")
    container.register_singleton(IValidationService, UnifiedValidationService, "validation_service")
    container.register_singleton(IMetricsService, MetricsService, "metrics_service")
    container.register_singleton(INotificationService, NotificationService, "notification_service")
    container.register_singleton(ICacheService, InMemoryCacheService, "cache_service")
    container.register_singleton(ISecurityService, SecurityService, "security_service")
    
    # Verify all services are registered
    try:
        container.resolve(IConfigurationService)
        container.resolve(ILoggingService)
        container.resolve(IFileService)
        container.resolve(IValidationService)
        container.resolve(IMetricsService)
        container.resolve(INotificationService)
        container.resolve(ICacheService)
        container.resolve(ISecurityService)
        
        # Also verify named services work
        container.resolve(IConfigurationService, "config_service")
        container.resolve(ILoggingService, "logging_service")
        container.resolve(IFileService, "file_service")
        container.resolve(IValidationService, "validation_service")
        container.resolve(IMetricsService, "metrics_service")
        container.resolve(INotificationService, "notification_service")
        container.resolve(ICacheService, "cache_service")
        container.resolve(ISecurityService, "security_service")
    except Exception as e:
        raise RuntimeError(f"Failed to setup default services: {e}")
    
    return container