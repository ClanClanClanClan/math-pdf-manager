#!/usr/bin/env python3
"""
Module-Level Service Registry
Phase 1, Week 2: Critical DI Scope Fix

Provides module-level access to dependency injection services throughout the application.
This fixes the critical scope issues where services were used as globals but only existed in main().
"""

from typing import Optional, TypeVar, Type
# Import only interfaces and types at module level to avoid circular imports
from core.dependency_injection import (
    DIContainer,
    IConfigurationService, ILoggingService, IFileService, 
    IValidationService, IMetricsService, INotificationService,
    ICacheService, ISecurityService
)

T = TypeVar('T')

class ServiceRegistry:
    """
    Module-level service registry for global access to DI services.
    
    This pattern allows services to be accessed throughout the module
    while maintaining the benefits of dependency injection.
    """
    
    def __init__(self):
        self._container: Optional[DIContainer] = None
        self._logging_service: Optional[ILoggingService] = None
        self._file_service: Optional[IFileService] = None
        self._config_service: Optional[IConfigurationService] = None
        self._validation_service: Optional[IValidationService] = None
        self._metrics_service: Optional[IMetricsService] = None
        self._notification_service: Optional[INotificationService] = None
        self._cache_service: Optional[ICacheService] = None
        self._security_service: Optional[ISecurityService] = None
        self._initialized = False
        
    def initialize(self, container: Optional[DIContainer] = None) -> None:
        """Initialize the service registry with a DI container."""
        if container:
            self._container = container
        else:
            # Ensure default services are set up before getting container
            from core.dependency_injection import setup_default_services, get_container
            try:
                setup_default_services()
            except Exception:
                # If already set up, that's fine
                pass
            self._container = get_container()
        
        # Resolve all services
        try:
            self._logging_service = self._container.resolve(ILoggingService)
            self._file_service = self._container.resolve(IFileService)
            self._config_service = self._container.resolve(IConfigurationService)
            self._validation_service = self._container.resolve(IValidationService)
            self._metrics_service = self._container.resolve(IMetricsService)
            self._notification_service = self._container.resolve(INotificationService)
            self._cache_service = self._container.resolve(ICacheService)
            self._security_service = self._container.resolve(ISecurityService)
            self._initialized = True
        except Exception:
            # If services can't be resolved, create a fallback
            self._create_fallback_services()
            # Don't raise - just use fallback services
            self._initialized = True  # Mark as initialized with fallbacks
    
    def _create_fallback_services(self) -> None:
        """Create fallback services for when DI fails."""
        # Import here to avoid circular dependencies
        import logging
        
        # Create minimal fallback logging service
        class FallbackLoggingService:
            def __init__(self):
                self.logger = logging.getLogger('fallback')
                
            def debug(self, message: str, **kwargs) -> None:
                self.logger.debug(message)
                
            def info(self, message: str, **kwargs) -> None:
                self.logger.info(message)
                
            def warning(self, message: str, **kwargs) -> None:
                self.logger.warning(message)
                
            def error(self, message: str, **kwargs) -> None:
                self.logger.error(message)
        
        self._logging_service = FallbackLoggingService()
    
    @property
    def logging_service(self) -> ILoggingService:
        """Get the logging service."""
        if not self._initialized:
            self.initialize()
        if not self._logging_service:
            self._create_fallback_services()
        return self._logging_service
    
    @property
    def file_service(self) -> IFileService:
        """Get the file service."""
        if not self._initialized:
            self.initialize()
        return self._file_service
    
    @property
    def config_service(self) -> IConfigurationService:
        """Get the configuration service."""
        if not self._initialized:
            self.initialize()
        return self._config_service
    
    @property
    def validation_service(self) -> IValidationService:
        """Get the validation service."""
        if not self._initialized:
            self.initialize()
        return self._validation_service
    
    @property
    def metrics_service(self) -> IMetricsService:
        """Get the metrics service."""
        if not self._initialized:
            self.initialize()
        return self._metrics_service
    
    @property
    def notification_service(self) -> INotificationService:
        """Get the notification service."""
        if not self._initialized:
            self.initialize()
        return self._notification_service
    
    @property
    def cache_service(self) -> ICacheService:
        """Get the cache service."""
        if not self._initialized:
            self.initialize()
        return self._cache_service
    
    @property
    def security_service(self) -> ISecurityService:
        """Get the security service."""
        if not self._initialized:
            self.initialize()
        return self._security_service
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get a service by type."""
        if not self._initialized:
            self.initialize()
        return self._container.resolve(service_type)
    
    def is_initialized(self) -> bool:
        """Check if the registry is initialized."""
        return self._initialized

# Global service registry instance
_registry = ServiceRegistry()

def get_service_registry() -> ServiceRegistry:
    """Get the global service registry."""
    return _registry

# Convenience functions for common services
def get_logging_service() -> ILoggingService:
    """Get the global logging service."""
    return _registry.logging_service

def get_file_service() -> IFileService:
    """Get the global file service."""
    return _registry.file_service

def get_config_service() -> IConfigurationService:
    """Get the global configuration service."""
    return _registry.config_service

def get_validation_service() -> IValidationService:
    """Get the global validation service."""
    return _registry.validation_service

def get_metrics_service() -> IMetricsService:
    """Get the global metrics service."""
    return _registry.metrics_service

def get_notification_service() -> INotificationService:
    """Get the global notification service."""
    return _registry.notification_service

# Initialize services with defaults if running as module
def init_module_services():
    """Initialize module-level services for standalone usage."""
    from core.dependency_injection import setup_default_services
    setup_default_services()
    _registry.initialize()