#!/usr/bin/env python3
"""
Standardized Error Handling System
Provides consistent error handling across the application
"""

import sys
import traceback
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union
from functools import wraps
from datetime import datetime, timezone
import logging

T = TypeVar('T')


class BaseError(Exception):
    """Base class for all application errors."""
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now(timezone.utc)
        
        # Capture stack trace
        self.traceback = traceback.format_exc() if sys.exc_info()[0] else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/API responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp.isoformat(),
                "type": self.__class__.__name__
            }
        }


class ValidationError(BaseError):
    """Raised when input validation fails."""
    pass


class AuthenticationError(BaseError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(BaseError):
    """Raised when authorization fails."""
    pass


class ResourceNotFoundError(BaseError):
    """Raised when a requested resource is not found."""
    pass


class ResourceExistsError(BaseError):
    """Raised when trying to create a resource that already exists."""
    pass


class ConfigurationError(BaseError):
    """Raised when configuration is invalid or missing."""
    pass


class ExternalServiceError(BaseError):
    """Raised when an external service fails."""
    
    def __init__(
        self, 
        message: str, 
        service: str,
        status_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.service = service
        self.status_code = status_code
        self.details["service"] = service
        if status_code:
            self.details["status_code"] = status_code


class ProcessingError(BaseError):
    """Raised when data processing fails."""
    pass


class RateLimitError(BaseError):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self, 
        message: str,
        limit: int,
        window: int,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        self.details.update({
            "limit": limit,
            "window": window,
            "retry_after": retry_after
        })


class ErrorHandler:
    """Centralized error handling utilities."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_handlers: Dict[Type[Exception], Callable] = {}
    
    def register_handler(
        self, 
        error_type: Type[Exception], 
        handler: Callable[[Exception], Any]
    ):
        """Register a custom error handler for a specific error type."""
        self.error_handlers[error_type] = handler
    
    def handle_error(self, error: Exception) -> Optional[Any]:
        """
        Handle an error using registered handlers.
        
        Returns:
            Result from handler if one exists, None otherwise
        """
        # Try specific handler first
        handler = self.error_handlers.get(type(error))
        if handler:
            return handler(error)
        
        # Try parent classes
        for error_class, handler in self.error_handlers.items():
            if isinstance(error, error_class):
                return handler(error)
        
        # Default handling
        if isinstance(error, BaseError):
            self.logger.error(
                f"{error.code}: {error.message}",
                extra=error.to_dict()
            )
        else:
            self.logger.error(
                f"Unhandled error: {str(error)}",
                exc_info=True
            )
        
        return None


def error_handler(
    *error_types: Type[Exception],
    default_return: Any = None,
    logger: Optional[logging.Logger] = None,
    reraise: bool = True,
    on_error: Optional[Callable[[Exception], Any]] = None
):
    """
    Decorator for consistent error handling.
    
    Args:
        error_types: Exception types to catch
        default_return: Value to return on error
        logger: Logger for error messages
        reraise: Whether to re-raise the exception
        on_error: Custom error handler function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Union[T, Any]:
            try:
                return func(*args, **kwargs)
            except error_types as e:
                # Log the error
                if logger:
                    logger.error(
                        f"Error in {func.__name__}: {str(e)}",
                        exc_info=True,
                        extra={
                            "function": func.__name__,
                            "args": str(args)[:200],
                            "kwargs": str(kwargs)[:200]
                        }
                    )
                
                # Call custom handler
                if on_error:
                    result = on_error(e)
                    if result is not None:
                        return result
                
                # Re-raise or return default
                if reraise:
                    raise
                return default_return
        
        return wrapper
    return decorator


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
):
    """
    Decorator to retry function on error with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to retry on
        logger: Logger for retry messages
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import time
            
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if logger:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed "
                            f"for {func.__name__}: {str(e)}"
                        )
                    
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
            
            # All attempts failed
            if logger:
                logger.error(
                    f"All {max_attempts} attempts failed for {func.__name__}"
                )
            
            raise last_exception
        
        return wrapper
    return decorator


class ErrorContext:
    """Context manager for error handling with cleanup."""
    
    def __init__(
        self,
        operation: str,
        logger: Optional[logging.Logger] = None,
        cleanup: Optional[Callable] = None,
        suppress: bool = False
    ):
        self.operation = operation
        self.logger = logger or logging.getLogger(__name__)
        self.cleanup = cleanup
        self.suppress = suppress
    
    def __enter__(self):
        self.logger.debug(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.logger.error(
                f"Error in {self.operation}: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb)
            )
            
            # Run cleanup if provided
            if self.cleanup:
                try:
                    self.cleanup()
                except Exception as cleanup_error:
                    self.logger.error(
                        f"Cleanup failed: {cleanup_error}",
                        exc_info=True
                    )
        
        # Suppress exception if requested
        return self.suppress