# Simple Service Locator Implementation Plan

## New Service Locator Architecture

### Core Service Locator (`src/core/services/locator.py`)

```python
#!/usr/bin/env python3
"""
Simple Service Locator Pattern
Replaces complex dependency injection framework with straightforward service management.
"""

import logging
from typing import Type, TypeVar, Dict, Any, Callable, Optional
from threading import Lock

T = TypeVar('T')

class ServiceLocator:
    """
    Simple service locator for managing application services.
    
    Provides singleton and transient service management without the complexity
    of a full dependency injection framework.
    """
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = Lock()
        self._configured = False
    
    def register_singleton(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        """Register a singleton service factory."""
        with self._lock:
            self._factories[service_type] = factory
            self._singletons[service_type] = None
    
    def register_transient(self, service_type: Type[T], factory: Callable[[], T]) -> None:
        """Register a transient service factory."""
        with self._lock:
            self._factories[service_type] = factory
    
    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """Register a service instance directly."""
        with self._lock:
            self._services[service_type] = instance
    
    def get(self, service_type: Type[T]) -> T:
        """Get service instance."""
        # Check direct instances first
        if service_type in self._services:
            return self._services[service_type]
        
        # Check singletons
        if service_type in self._singletons:
            if self._singletons[service_type] is None:
                with self._lock:
                    # Double-check locking pattern
                    if self._singletons[service_type] is None:
                        self._singletons[service_type] = self._factories[service_type]()
            return self._singletons[service_type]
        
        # Check transients
        if service_type in self._factories:
            return self._factories[service_type]()
        
        raise ValueError(f"Service not registered: {service_type}")
    
    def configure_defaults(self) -> None:
        """Configure default application services."""
        if self._configured:
            return
            
        # Import services here to avoid circular dependencies
        from core.dependency_injection.interfaces import (
            IConfigurationService, ILoggingService, IFileService, 
            IValidationService, IMetricsService, INotificationService,
            ICacheService, ISecurityService
        )
        from core.dependency_injection.implementations import (
            ConfigurationService, LoggingService, FileService,
            MetricsService, NotificationService, InMemoryCacheService, 
            SecurityService
        )
        from core.dependency_injection.validation_service import UnifiedValidationService
        
        # Register core services with dependency resolution
        self.register_singleton(IConfigurationService, self._create_config_service)
        self.register_singleton(ILoggingService, self._create_logging_service)
        self.register_singleton(IFileService, self._create_file_service)
        self.register_singleton(IValidationService, self._create_validation_service)
        self.register_singleton(IMetricsService, self._create_metrics_service)
        self.register_singleton(INotificationService, self._create_notification_service)
        self.register_singleton(ICacheService, self._create_cache_service)
        self.register_singleton(ISecurityService, self._create_security_service)
        
        self._configured = True
    
    # Service factory methods with dependency resolution
    def _create_config_service(self):
        from core.dependency_injection.implementations import ConfigurationService
        return ConfigurationService()
    
    def _create_logging_service(self):
        from core.dependency_injection.implementations import LoggingService
        config_service = self.get(IConfigurationService)
        return LoggingService(config_service)
    
    def _create_file_service(self):
        from core.dependency_injection.implementations import FileService
        logging_service = self.get(ILoggingService)
        return FileService(logging_service)
    
    def _create_validation_service(self):
        from core.dependency_injection.validation_service import UnifiedValidationService
        logging_service = self.get(ILoggingService)
        return UnifiedValidationService(logging_service)
    
    def _create_metrics_service(self):
        from core.dependency_injection.implementations import MetricsService
        logging_service = self.get(ILoggingService)
        return MetricsService(logging_service)
    
    def _create_notification_service(self):
        from core.dependency_injection.implementations import NotificationService
        logging_service = self.get(ILoggingService)
        return NotificationService(logging_service)
    
    def _create_cache_service(self):
        from core.dependency_injection.implementations import InMemoryCacheService
        logging_service = self.get(ILoggingService)
        return InMemoryCacheService(logging_service)
    
    def _create_security_service(self):
        from core.dependency_injection.implementations import SecurityService
        logging_service = self.get(ILoggingService)
        return SecurityService(logging_service)
    
    def is_registered(self, service_type: Type) -> bool:
        """Check if service is registered."""
        return (service_type in self._services or 
                service_type in self._factories or 
                service_type in self._singletons)
    
    def clear(self) -> None:
        """Clear all registered services (for testing)."""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()
            self._configured = False

# Global service locator instance
_locator = ServiceLocator()

def get_locator() -> ServiceLocator:
    """Get the global service locator."""
    if not _locator._configured:
        _locator.configure_defaults()
    return _locator

def get_service(service_type: Type[T]) -> T:
    """Convenience function to get a service."""
    return get_locator().get(service_type)

# Convenience functions for common services
def get_logging_service():
    from core.dependency_injection.interfaces import ILoggingService
    return get_service(ILoggingService)

def get_validation_service():
    from core.dependency_injection.interfaces import IValidationService
    return get_service(IValidationService)

def get_config_service():
    from core.dependency_injection.interfaces import IConfigurationService
    return get_service(IConfigurationService)

def get_file_service():
    from core.dependency_injection.interfaces import IFileService
    return get_service(IFileService)
```

## Updated Service Registry (`src/core/utils/service_registry.py`)

```python
#!/usr/bin/env python3
"""
Module-Level Service Registry (Updated)
Now uses simple service locator instead of complex DI framework.
"""

from typing import Optional, TypeVar, Type

# Use the new service locator
from core.services.locator import get_locator, get_service
from core.dependency_injection.interfaces import (
    IConfigurationService, ILoggingService, IFileService, 
    IValidationService, IMetricsService, INotificationService,
    ICacheService, ISecurityService
)

T = TypeVar('T')

class ServiceRegistry:
    """
    Module-level service registry using service locator pattern.
    
    Provides backward compatibility for existing service access patterns.
    """
    
    def __init__(self):
        self._initialized = False
        
    def initialize(self, container=None) -> None:
        """Initialize the service registry."""
        # Container parameter kept for backward compatibility but ignored
        locator = get_locator()
        locator.configure_defaults()
        self._initialized = True
    
    @property
    def logging_service(self) -> ILoggingService:
        """Get the logging service."""
        return get_service(ILoggingService)
    
    @property 
    def file_service(self) -> IFileService:
        """Get the file service."""
        return get_service(IFileService)
    
    @property
    def config_service(self) -> IConfigurationService:
        """Get the configuration service."""
        return get_service(IConfigurationService)
    
    @property
    def validation_service(self) -> IValidationService:
        """Get the validation service."""
        return get_service(IValidationService)
    
    @property
    def metrics_service(self) -> IMetricsService:
        """Get the metrics service."""
        return get_service(IMetricsService)
    
    @property
    def notification_service(self) -> INotificationService:
        """Get the notification service."""
        return get_service(INotificationService)
    
    @property
    def cache_service(self) -> ICacheService:
        """Get the cache service."""
        return get_service(ICacheService)
    
    @property
    def security_service(self) -> ISecurityService:
        """Get the security service."""
        return get_service(ISecurityService)
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get a service by type."""
        return get_service(service_type)
    
    def is_initialized(self) -> bool:
        """Check if the registry is initialized."""
        return self._initialized

# Global service registry instance (for backward compatibility)
_registry = ServiceRegistry()

def get_service_registry() -> ServiceRegistry:
    """Get the global service registry."""
    return _registry

# Keep existing convenience functions for backward compatibility
def get_logging_service():
    """Get the global logging service."""
    return get_service(ILoggingService)

def get_file_service():
    """Get the global file service.""" 
    return get_service(IFileService)

def get_config_service():
    """Get the global configuration service."""
    return get_service(IConfigurationService)

def get_validation_service():
    """Get the global validation service."""
    return get_service(IValidationService)

def get_metrics_service():
    """Get the global metrics service."""
    return get_service(IMetricsService)

def get_notification_service():
    """Get the global notification service."""
    return get_service(INotificationService)

def init_module_services():
    """Initialize module-level services for standalone usage."""
    _registry.initialize()
```

## Updated Main Function (`src/main.py`)

```python
# Replace the decorator-heavy injection with simple service calls

# OLD CODE:
# @inject(IConfigurationService, name="config_service")
# @inject(ILoggingService, name="logging_service") 
# @inject(IFileService, name="file_service")
# @inject(IValidationService, name="validation_service")
# @inject(IMetricsService, name="metrics_service")
# @inject(INotificationService, name="notification_service")
# def main(argv: list[str] | None = None, 
#          config_service: IConfigurationService = None,
#          logging_service: ILoggingService = None,
#          file_service: IFileService = None,
#          validation_service: IValidationService = None,
#          metrics_service: IMetricsService = None,
#          notification_service: INotificationService = None) -> None:

# NEW CODE:
from core.services.locator import get_service
from core.dependency_injection.interfaces import (
    IConfigurationService, ILoggingService, IFileService, 
    IValidationService, IMetricsService, INotificationService
)

def main(argv: list[str] | None = None) -> None:
    """Main function using service locator pattern."""
    
    # Get services from service locator
    config_service = get_service(IConfigurationService)
    logging_service = get_service(ILoggingService)
    file_service = get_service(IFileService)
    validation_service = get_service(IValidationService)
    metrics_service = get_service(IMetricsService)
    notification_service = get_service(INotificationService)
    
    # Initialize service registry for backward compatibility
    registry = get_service_registry()
    registry.initialize()
    
    # Rest of main function remains exactly the same...
    metrics_service.increment_counter("main_function_calls")
    # ... existing code unchanged
```

## Migration Steps

### Step 1: Create Service Locator Infrastructure
1. **Create directory**: `src/core/services/`
2. **Create file**: `src/core/services/__init__.py`
3. **Create file**: `src/core/services/locator.py` (with above implementation)

### Step 2: Update Service Implementations
1. **Remove decorators** from implementation classes:
   ```python
   # Remove: @service(IValidationService, singleton=True)
   class UnifiedValidationService:
   ```

2. **Keep constructor injection** - no changes needed to constructors

### Step 3: Update Main Function
1. **Remove @inject decorators** from main function
2. **Add service locator calls** at beginning of main
3. **Keep all parameter names** for backward compatibility in tests

### Step 4: Update Service Registry
1. **Replace implementation** with service locator calls
2. **Keep all property methods** for backward compatibility  
3. **Preserve convenience functions**

### Step 5: Update Imports
```python
# OLD:
from core.dependency_injection import inject, get_container, setup_default_services

# NEW: 
from core.services.locator import get_service, get_locator
```

### Step 6: Remove DI Framework Files
**Files to DELETE:**
- `src/core/dependency_injection/container.py` (419 lines)
- Complex parts of `src/core/dependency_injection/__init__.py`

**Files to KEEP:**
- `src/core/dependency_injection/interfaces.py` (service contracts)
- `src/core/dependency_injection/implementations.py` (service implementations)
- `src/core/dependency_injection/validation_service.py` (core validation logic)

## Testing Strategy

### Updated Test Setup
```python
# OLD DI test setup:
def test_service_injection():
    container = DIContainer()
    setup_default_services()
    service = container.resolve(IValidationService)

# NEW service locator test setup:
def test_service_locator():
    from core.services.locator import get_locator
    locator = get_locator()
    locator.configure_defaults()
    service = locator.get(IValidationService)
    
# Or even simpler:
def test_get_service():
    from core.services.locator import get_service
    service = get_service(IValidationService)
```

### Mock Testing
```python
# Service locator makes mocking easier:
def test_with_mock_service():
    from core.services.locator import get_locator
    locator = get_locator()
    
    # Clear and register mock
    locator.clear()
    mock_service = Mock(spec=IValidationService)
    locator.register_instance(IValidationService, mock_service)
    
    # Test code using the mock
    result = some_function_using_validation()
```

## Benefits Summary

### Code Reduction
- **Remove 700+ lines** of complex DI framework code
- **Simplify to ~150 lines** of service locator
- **Net reduction: ~550 lines** (75% smaller)

### Complexity Reduction  
- **No decorators**: Explicit service calls
- **No magic**: Clear registration and resolution
- **Simpler debugging**: Direct service access path
- **Better IDE support**: Explicit imports and type hints

### Maintenance Benefits
- **Easier onboarding**: No complex DI concepts
- **Clearer dependencies**: Explicit service calls
- **Simpler testing**: Direct service mocking
- **Faster startup**: No complex container initialization

### Preserved Functionality
- **All service interfaces**: Kept unchanged
- **All service implementations**: Minimal changes (remove decorators)
- **All domain logic**: Completely untouched
- **Backward compatibility**: Service registry preserved

## Risk Mitigation

### Rollback Plan
1. **Git branch**: Create migration branch before starting
2. **Incremental commits**: Commit each step separately
3. **Testing checkpoint**: Test after each phase
4. **Easy rollback**: Can revert to DI system if needed

### Compatibility Preservation
1. **Service interfaces**: No changes to contracts
2. **Service registry**: Backward compatible API
3. **Domain logic**: Zero changes to core algorithms
4. **Existing tests**: Minimal updates needed

This implementation provides all the benefits of dependency injection (loose coupling, testability, configurability) with a fraction of the complexity. The service locator pattern is a well-established alternative that's much easier to understand and maintain while providing the same core functionality.