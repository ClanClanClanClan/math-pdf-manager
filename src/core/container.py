"""
Service container for dependency injection

This module provides a simple dependency injection container to manage
service instances and their dependencies throughout the application.
"""
from typing import Dict, Any, TypeVar, Callable, Optional
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """Simple dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._initialized = False
        
    def register_service(self, name: str, instance: Any) -> None:
        """Register a service instance"""
        self._services[name] = instance
        logger.debug(f"Registered service: {name}")
    
    def register_factory(self, name: str, factory: Callable) -> None:
        """Register a factory function for creating service instances"""
        self._factories[name] = factory
        logger.debug(f"Registered factory: {name}")
    
    def register_singleton(self, name: str, factory: Callable) -> None:
        """Register a singleton factory (creates instance only once)"""
        self._factories[name] = factory
        self._singletons[name] = None
        logger.debug(f"Registered singleton: {name}")
    
    def get_service(self, name: str) -> Any:
        """Get a service instance"""
        # Check if it's a direct service
        if name in self._services:
            return self._services[name]
        
        # Check if it's a singleton that's already created
        if name in self._singletons and self._singletons[name] is not None:
            return self._singletons[name]
        
        # Check if we have a factory
        if name in self._factories:
            instance = self._factories[name]()
            
            # If it's a singleton, store the instance
            if name in self._singletons:
                self._singletons[name] = instance
            
            return instance
        
        raise ValueError(f"Service not found: {name}")
    
    def has_service(self, name: str) -> bool:
        """Check if a service is registered"""
        return (name in self._services or 
                name in self._factories or 
                name in self._singletons)
    
    def initialize_default_services(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize default services"""
        if self._initialized:
            return
        
        config = config or {}
        
        # Register basic services
        self._register_default_services(config)
        
        self._initialized = True
        logger.info("Service container initialized with default services")
    
    def _register_default_services(self, config: Dict[str, Any]) -> None:
        """Register the default set of services"""
        from pathlib import Path
        
        # Configuration service
        self.register_service('config', config)
        
        # Path service
        self.register_service('project_root', Path.cwd())
        
        # Cache directory
        cache_dir = config.get('cache_dir', Path.home() / '.cache' / 'math-pdf-manager')
        self.register_service('cache_dir', Path(cache_dir))
        
        # Output directory
        output_dir = config.get('output_dir', Path.cwd() / 'output')
        self.register_service('output_dir', Path(output_dir))
        
        # Register factory for logger
        def logger_factory():
            return logging.getLogger('math_pdf_manager')
        
        self.register_factory('logger', logger_factory)
        
        # Register factories for validators (lazy loading)
        def filename_validator_factory():
            from validators.filename import FilenameValidator
            strict_mode = config.get('strict_mode', False)
            return FilenameValidator(strict_mode=strict_mode)
        
        def author_validator_factory():
            from validators.author import AuthorValidator
            strict_mode = config.get('strict_mode', False)
            return AuthorValidator(strict_mode=strict_mode)
        
        def unicode_validator_factory():
            from validators.unicode import UnicodeValidator
            return UnicodeValidator()
        
        self.register_singleton('filename_validator', filename_validator_factory)
        self.register_singleton('author_validator', author_validator_factory)
        self.register_singleton('unicode_validator', unicode_validator_factory)
        
        # Register scanner factory
        def scanner_factory():
            from scanner import Scanner
            return Scanner()
        
        self.register_singleton('scanner', scanner_factory)
        
        # Register duplicate detector factory
        def duplicate_detector_factory():
            from duplicate_detector import DuplicateDetector
            return DuplicateDetector()
        
        self.register_singleton('duplicate_detector', duplicate_detector_factory)
        
        # Register reporter factory
        def reporter_factory():
            from reporter import Reporter
            output_dir = self.get_service('output_dir')
            return Reporter(output_dir=output_dir)
        
        self.register_singleton('reporter', reporter_factory)
    
    def clear(self) -> None:
        """Clear all registered services"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._initialized = False
        logger.debug("Service container cleared")
    
    def list_services(self) -> Dict[str, str]:
        """List all registered services and their types"""
        services = {}
        
        for name in self._services:
            services[name] = type(self._services[name]).__name__
        
        for name in self._factories:
            if name in self._singletons:
                services[name] = "Singleton (not created)" if self._singletons[name] is None else f"Singleton ({type(self._singletons[name]).__name__})"
            else:
                services[name] = "Factory"
        
        return services


# Global container instance
_container = ServiceContainer()


def get_container() -> ServiceContainer:
    """Get the global service container"""
    return _container


def get_service(name: str) -> Any:
    """Convenience function to get a service from the global container"""
    return _container.get_service(name)


def register_service(name: str, instance: Any) -> None:
    """Convenience function to register a service in the global container"""
    _container.register_service(name, instance)


def initialize_services(config: Optional[Dict[str, Any]] = None) -> None:
    """Initialize the global service container"""
    _container.initialize_default_services(config)