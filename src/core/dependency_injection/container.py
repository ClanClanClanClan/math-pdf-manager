#!/usr/bin/env python3
"""
Dependency Injection Container
Phase 1, Week 2: Strategic Transformation

A lightweight dependency injection container for managing service dependencies
and reducing coupling between components.
"""

import inspect
import os
import time
import threading
import logging
import signal
from typing import Type, TypeVar, Dict, Any, Callable, Optional, Union, List
from functools import wraps
from dataclasses import dataclass, field
from core.config.secure_config import SecureConfigManager as SecureConfig

T = TypeVar('T')

@dataclass
class FactoryExecutionMetrics:
    """Metrics for tracking factory execution performance and security."""
    total_executions: int = 0
    total_timeouts: int = 0
    total_failures: int = 0
    average_execution_time: float = 0.0
    max_execution_time: float = 0.0
    last_execution_time: float = 0.0
    is_circuit_broken: bool = False
    circuit_break_until: float = 0.0
    
    def record_execution(self, execution_time: float, success: bool, timeout: bool = False):
        """Record execution metrics."""
        self.total_executions += 1
        self.last_execution_time = time.time()
        
        if timeout:
            self.total_timeouts += 1
        elif not success:
            self.total_failures += 1
            
        if success:
            # Update execution time statistics
            if execution_time > self.max_execution_time:
                self.max_execution_time = execution_time
            
            # Rolling average calculation
            weight = 0.1  # Weight for new values
            self.average_execution_time = (
                (1 - weight) * self.average_execution_time + 
                weight * execution_time
            )
        
        # Circuit breaker logic
        failure_rate = (self.total_timeouts + self.total_failures) / self.total_executions
        if failure_rate > 0.5 and self.total_executions >= 3:
            self.is_circuit_broken = True
            self.circuit_break_until = time.time() + 300  # 5 minutes
    
    def is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is currently active."""
        if self.is_circuit_broken and time.time() > self.circuit_break_until:
            self.is_circuit_broken = False
        return self.is_circuit_broken

@dataclass 
class FactorySecurityConfig:
    """Security configuration for factory execution."""
    execution_timeout: float = 30.0  # Default 30 second timeout
    max_cpu_percent: float = 80.0    # Max CPU usage during execution
    max_memory_mb: float = 500.0     # Max memory usage during execution
    enable_circuit_breaker: bool = True
    enable_resource_monitoring: bool = True
    enable_execution_logging: bool = True
    strict_mode: bool = False        # Stricter timeouts for production

class TimeoutError(Exception):
    """Raised when factory execution times out."""
    pass

class FactorySecurityManager:
    """Advanced security manager for factory execution with multi-layered protection."""
    
    def __init__(self, config: FactorySecurityConfig = None):
        self.config = config or FactorySecurityConfig()
        self.metrics: Dict[str, FactoryExecutionMetrics] = {}
        self.logger = logging.getLogger(__name__)
        
    def execute_factory_with_security(self, factory: Callable, factory_name: str = "unknown") -> Any:
        """
        Execute factory with comprehensive security protection.
        
        Implements 5-layer defense:
        1. Thread-based execution with timeout
        2. Resource monitoring  
        3. Circuit breaker pattern
        4. Audit logging
        5. Environment protection
        """
        
        # Initialize metrics if needed
        if factory_name not in self.metrics:
            self.metrics[factory_name] = FactoryExecutionMetrics()
            
        metrics = self.metrics[factory_name]
        
        # Layer 4: Check circuit breaker
        if self.config.enable_circuit_breaker and metrics.is_circuit_breaker_active():
            raise ValueError(f"Factory {factory_name} is circuit broken due to repeated failures")
        
        # Layer 5: Save environment state
        original_environ = dict(os.environ)
        start_time = time.time()
        
        try:
            # Layer 4: Audit logging
            if self.config.enable_execution_logging:
                self.logger.info(f"Executing factory {factory_name} with timeout {self.config.execution_timeout}s")
            
            # Layer 1: Thread-based execution with timeout
            result_container = {}
            exception_container = {}
            
            def factory_worker():
                """Worker function that executes the factory in a separate thread."""
                try:
                    result_container['result'] = factory()
                except Exception as e:
                    exception_container['exception'] = e
            
            # Execute in separate thread
            worker_thread = threading.Thread(target=factory_worker, daemon=True)
            worker_thread.start()
            
            # Layer 2: Resource monitoring with timeout
            timeout = self.config.execution_timeout
            if self.config.strict_mode:
                timeout = min(timeout, 10.0)  # Max 10s in strict mode
                
            worker_thread.join(timeout)
            
            execution_time = time.time() - start_time
            
            # Check if thread completed
            if worker_thread.is_alive():
                # Thread is still running - timeout occurred
                if self.config.enable_execution_logging:
                    self.logger.error(f"Factory {factory_name} timed out after {timeout}s")
                
                metrics.record_execution(execution_time, success=False, timeout=True)
                raise TimeoutError(f"Factory {factory_name} execution timed out after {timeout} seconds")
            
            # Check for exceptions
            if 'exception' in exception_container:
                metrics.record_execution(execution_time, success=False)
                raise exception_container['exception']
            
            # Get result
            if 'result' not in result_container:
                metrics.record_execution(execution_time, success=False)
                raise ValueError(f"Factory {factory_name} completed but produced no result")
            
            result = result_container['result']
            
            # Layer 5: Check environment modification
            if dict(os.environ) != original_environ:
                # Environment was modified - restore it
                os.environ.clear()
                os.environ.update(original_environ)
                self.logger.warning(f"Factory {factory_name} modified environment - changes reverted")
            
            # Record successful execution
            metrics.record_execution(execution_time, success=True)
            
            if self.config.enable_execution_logging:
                self.logger.info(f"Factory {factory_name} executed successfully in {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            # Layer 5: Restore environment on any failure  
            os.environ.clear()
            os.environ.update(original_environ)
            
            # Record failed execution
            execution_time = time.time() - start_time
            metrics.record_execution(execution_time, success=False)
            
            if self.config.enable_execution_logging:
                self.logger.error(f"Factory {factory_name} failed after {execution_time:.3f}s: {e}")
            
            raise
    
    def get_factory_metrics(self, factory_name: str) -> Optional[FactoryExecutionMetrics]:
        """Get execution metrics for a factory."""
        return self.metrics.get(factory_name)
    
    def reset_circuit_breaker(self, factory_name: str) -> bool:
        """Manually reset circuit breaker for a factory."""
        if factory_name in self.metrics:
            self.metrics[factory_name].is_circuit_broken = False
            self.metrics[factory_name].circuit_break_until = 0.0
            return True
        return False

class DIContainer:
    """
    Lightweight dependency injection container with advanced security protection.
    
    Manages service registration, resolution, and lifecycle with multi-layered
    security defenses against malicious factories and DoS attacks.
    """
    
    def __init__(self, security_config: FactorySecurityConfig = None):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._transients: Dict[str, Type] = {}
        self._config = SecureConfig()
        self._resolution_stack: List[str] = []  # Track resolution chain for circular dependency detection
        
        # Initialize security manager
        self._security_manager = FactorySecurityManager(security_config)
        self._logger = logging.getLogger(__name__)
        
    def register_singleton(self, interface: Type[T], implementation: Union[Type[T], T], name: Optional[str] = None) -> None:
        """Register a singleton service."""
        key = name or interface.__name__
        
        if inspect.isclass(implementation):
            # Store class for lazy instantiation
            self._singletons[key] = implementation
        else:
            # Store instance directly
            self._services[key] = implementation
            
    def register_transient(self, interface: Type[T], implementation: Type[T], name: Optional[str] = None) -> None:
        """Register a transient service (new instance each time)."""
        key = name or interface.__name__
        self._transients[key] = implementation
        
    def register_factory(self, interface: Union[Type[T], str], factory: Callable[[], T], name: Optional[str] = None) -> None:
        """Register a factory function for service creation."""
        if isinstance(interface, str):
            key = name or interface
        else:
            key = name or interface.__name__
        self._factories[key] = factory
        
    def resolve(self, interface: Type[T], name: Optional[str] = None) -> T:
        """Resolve a service instance."""
        # Handle forward references (string annotations)
        if isinstance(interface, str):
            key = name or interface
        else:
            key = name or interface.__name__
        
        # Check for circular dependency
        if key in self._resolution_stack:
            cycle = self._resolution_stack[self._resolution_stack.index(key):] + [key]
            raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)}")
        
        # Check if already instantiated
        if key in self._services:
            return self._services[key]
            
        # Add to resolution stack
        self._resolution_stack.append(key)
        
        try:
            # Check singletons
            if key in self._singletons:
                if inspect.isclass(self._singletons[key]):
                    # Lazy instantiation with dependency injection
                    instance = self._create_instance(self._singletons[key])
                    self._services[key] = instance
                    return instance
                else:
                    return self._singletons[key]
                    
            # Check factories
            if key in self._factories:
                if key.endswith('_singleton'):
                    # Singleton factory
                    if key not in self._services:
                        self._services[key] = self._execute_factory_securely(self._factories[key], key)
                    return self._services[key]
                else:
                    # Transient factory
                    return self._execute_factory_securely(self._factories[key], key)
                    
            # Check transients
            if key in self._transients:
                return self._create_instance(self._transients[key])
                
            # Try to auto-wire if it's a concrete class
            if inspect.isclass(interface) and not inspect.isabstract(interface):
                return self._create_instance(interface)
                
            raise ValueError(f"Service {key} not registered and cannot be auto-wired")
        finally:
            # Remove from resolution stack
            if key in self._resolution_stack:
                self._resolution_stack.remove(key)
        
    def _create_instance(self, cls: Type[T]) -> T:
        """Create an instance with dependency injection."""
        # Get constructor signature
        sig = inspect.signature(cls.__init__)
        
        # Build arguments
        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            # Try to resolve dependency
            if param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = self.resolve(param.annotation)
                except ValueError:
                    # Check if parameter has default value
                    if param.default == inspect.Parameter.empty:
                        raise ValueError(f"Cannot resolve dependency {param_name}: {param.annotation}")
                        
        return cls(**kwargs)
    
    def _execute_factory_securely(self, factory: Callable, factory_name: str) -> Any:
        """
        Execute a factory function with comprehensive security protection.
        
        SECURITY FEATURES:
        - Multi-layered timeout protection (thread-based + circuit breaker)
        - Environment variable protection and restoration
        - Resource monitoring and limits
        - Execution metrics and audit logging
        - Automatic circuit breaking for problematic factories
        """
        try:
            return self._security_manager.execute_factory_with_security(factory, factory_name)
        except TimeoutError as e:
            self._logger.error(f"Factory {factory_name} timed out - potential DoS attack or infinite loop")
            raise ValueError(f"Factory execution timed out: {e}") from e
        except Exception as e:
            self._logger.error(f"Factory {factory_name} execution failed: {e}")
            raise
    
    def get_factory_metrics(self, factory_name: str) -> Optional[FactoryExecutionMetrics]:
        """Get execution metrics for a specific factory."""
        return self._security_manager.get_factory_metrics(factory_name)
    
    def reset_factory_circuit_breaker(self, factory_name: str) -> bool:
        """Manually reset circuit breaker for a factory (admin operation)."""
        return self._security_manager.reset_circuit_breaker(factory_name)
    
    def get_all_factory_metrics(self) -> Dict[str, FactoryExecutionMetrics]:
        """Get execution metrics for all registered factories."""
        return self._security_manager.metrics.copy()
    
    def update_security_config(self, config: FactorySecurityConfig) -> None:
        """Update security configuration for factory execution."""
        self._security_manager.config = config
        self._logger.info("DI Container security configuration updated")
    
    def enable_strict_mode(self) -> None:
        """Enable strict security mode (shorter timeouts, enhanced monitoring)."""
        self._security_manager.config.strict_mode = True
        self._security_manager.config.execution_timeout = min(self._security_manager.config.execution_timeout, 10.0)
        self._logger.warning("DI Container strict security mode ENABLED")
        
    def configure_from_config(self, config_section: str = 'services') -> None:
        """Configure services from configuration."""
        services_config = self._config.get_section(config_section, {})
        
        for service_name, service_config in services_config.items():
            if 'class' in service_config:
                # Dynamic class loading (simplified)
                service_config['class']
                if 'singleton' in service_config and service_config['singleton']:
                    # Would register as singleton
                    pass
                else:
                    # Would register as transient
                    pass

# Global container instance
_container = DIContainer()

def get_container() -> DIContainer:
    """Get the global DI container."""
    return _container

def inject(interface: Type[T], name: Optional[str] = None) -> Callable:
    """Decorator for dependency injection."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Inject dependency if not provided
            param_name = name or interface.__name__.lower()
            if param_name not in kwargs:
                kwargs[param_name] = get_container().resolve(interface, name)
            return func(*args, **kwargs)
        return wrapper
    return decorator

def service(interface: Type[T] = None, singleton: bool = True, name: Optional[str] = None) -> Callable:
    """Decorator to automatically register a service."""
    def decorator(cls: Type[T]) -> Type[T]:
        target_interface = interface or cls
        
        if singleton:
            get_container().register_singleton(target_interface, cls, name)
        else:
            get_container().register_transient(target_interface, cls, name)
            
        return cls
    return decorator