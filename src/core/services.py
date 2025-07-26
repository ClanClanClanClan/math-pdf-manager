#!/usr/bin/env python3
"""
Simple Service Locator Pattern
Replacement for over-engineered dependency injection framework.

This provides clean service management with:
- Type-safe service resolution
- Singleton and transient lifetimes  
- Thread-safe lazy loading
- Simple configuration
- No decorator magic
"""

import threading
from typing import TypeVar, Generic, Dict, Type, Callable, Optional, Any
from abc import ABC, abstractmethod

T = TypeVar('T')


class ServiceLifetime:
    """Service lifetime management."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"


class ServiceRegistry:
    """
    Simple service locator for managing application services.
    
    Replaces the complex DI framework with a clean, maintainable pattern.
    """
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._lifetimes: Dict[Type, str] = {}
        self._lock = threading.RLock()
    
    def register_singleton(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a service as singleton (one instance per application)."""
        with self._lock:
            self._factories[interface] = implementation
            self._lifetimes[interface] = ServiceLifetime.SINGLETON
    
    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """Register a service as transient (new instance per request)."""
        with self._lock:
            self._factories[interface] = implementation
            self._lifetimes[interface] = ServiceLifetime.TRANSIENT
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register a pre-created instance."""
        with self._lock:
            self._services[interface] = instance
            self._lifetimes[interface] = ServiceLifetime.SINGLETON
    
    def get(self, interface: Type[T]) -> T:
        """Get a service instance."""
        with self._lock:
            # Check if we have a cached instance for singletons
            if interface in self._services:
                return self._services[interface]
            
            # Check if we have a factory registered
            if interface not in self._factories:
                raise ValueError(f"Service {interface.__name__} not registered")
            
            # Create new instance
            factory = self._factories[interface]
            instance = factory()
            
            # Cache if singleton
            if self._lifetimes[interface] == ServiceLifetime.SINGLETON:
                self._services[interface] = instance
            
            return instance
    
    def clear(self) -> None:
        """Clear all registered services (useful for testing)."""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._lifetimes.clear()


# Global service registry instance
_registry = ServiceRegistry()


def get_service(interface: Type[T]) -> T:
    """Get a service from the global registry."""
    return _registry.get(interface)


def register_singleton(interface: Type[T], implementation: Type[T]) -> None:
    """Register a singleton service in the global registry."""
    _registry.register_singleton(interface, implementation)


def register_transient(interface: Type[T], implementation: Type[T]) -> None:
    """Register a transient service in the global registry."""
    _registry.register_transient(interface, implementation)


def register_instance(interface: Type[T], instance: T) -> None:
    """Register an instance in the global registry."""
    _registry.register_instance(interface, instance)


def setup_services() -> None:
    """Setup default services - called once at application startup."""
    from core.dependency_injection.interfaces import (
        IConfigurationService, ILoggingService, IFileService, 
        IMetricsService, INotificationService
    )
    from core.dependency_injection.implementations import (
        ConfigurationService, LoggingService, FileService,
        MetricsService, NotificationService
    )
    
    # Register available services as singletons
    register_singleton(IConfigurationService, ConfigurationService)
    register_singleton(ILoggingService, LoggingService) 
    register_singleton(IFileService, FileService)
    register_singleton(IMetricsService, MetricsService)
    register_singleton(INotificationService, NotificationService)


def clear_services() -> None:
    """Clear all services (useful for testing)."""
    _registry.clear()