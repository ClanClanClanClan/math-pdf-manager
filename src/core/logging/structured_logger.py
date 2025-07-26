#!/usr/bin/env python3
"""
Structured Logging System
Provides consistent, structured logging across the application
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from functools import wraps
import threading
from contextlib import contextmanager

# Thread-local storage for context
_context = threading.local()


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add thread context if available
        if hasattr(_context, 'data'):
            log_data["context"] = _context.data
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno', 
                          'module', 'msecs', 'message', 'pathname', 'process',
                          'processName', 'relativeCreated', 'thread', 
                          'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class PerformanceLogger:
    """Logger for performance metrics."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    @contextmanager
    def measure_time(self, operation: str, **extra):
        """Context manager to measure operation time."""
        start_time = datetime.utcnow()
        
        try:
            yield
        finally:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.logger.info(
                f"Performance: {operation}",
                extra={
                    "operation": operation,
                    "duration_ms": duration_ms,
                    "performance_metric": True,
                    **extra
                }
            )
    
    def log_metric(self, metric_name: str, value: Union[int, float], unit: str = "", **extra):
        """Log a performance metric."""
        self.logger.info(
            f"Metric: {metric_name}",
            extra={
                "metric_name": metric_name,
                "metric_value": value,
                "metric_unit": unit,
                "performance_metric": True,
                **extra
            }
        )


class SecurityLogger:
    """Logger for security events."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_access(self, user: str, resource: str, action: str, allowed: bool, **extra):
        """Log access attempt."""
        self.logger.info(
            f"Access {'granted' if allowed else 'denied'}: {user} -> {resource}",
            extra={
                "security_event": "access",
                "user": user,
                "resource": resource,
                "action": action,
                "allowed": allowed,
                **extra
            }
        )
    
    def log_auth_attempt(self, user: str, method: str, success: bool, **extra):
        """Log authentication attempt."""
        level = logging.INFO if success else logging.WARNING
        self.logger.log(
            level,
            f"Authentication {'successful' if success else 'failed'}: {user}",
            extra={
                "security_event": "auth",
                "user": user,
                "auth_method": method,
                "success": success,
                **extra
            }
        )
    
    def log_suspicious_activity(self, description: str, severity: str = "medium", **extra):
        """Log suspicious activity."""
        level_map = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL
        }
        self.logger.log(
            level_map.get(severity, logging.WARNING),
            f"Suspicious activity: {description}",
            extra={
                "security_event": "suspicious",
                "description": description,
                "severity": severity,
                **extra
            }
        )


def setup_logging(
    app_name: str = "main",
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    json_format: bool = True,
    console_output: bool = True
) -> logging.Logger:
    """
    Set up structured logging for the application.
    
    Args:
        app_name: Name of the application
        log_level: Logging level
        log_file: Optional log file path
        json_format: Use JSON formatting
        console_output: Enable console output
    
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    # Suppress noisy library loggers
    suppressed_loggers = ["fitz", "pdfminer", "pdfplumber"]
    for lib_name in suppressed_loggers:
        lib_logger = logging.getLogger(lib_name)
        lib_logger.setLevel(logging.ERROR)
    
    return logger


@contextmanager
def log_context(**context_data):
    """Add context to all logs within this context manager."""
    if not hasattr(_context, 'data'):
        _context.data = {}
    
    old_context = _context.data.copy()
    _context.data.update(context_data)
    
    try:
        yield
    finally:
        _context.data = old_context


def log_function_call(logger: logging.Logger):
    """Decorator to log function calls with arguments and results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log function call
            logger.debug(
                f"Calling {func.__name__}",
                extra={
                    "function_call": func.__name__,
                    "args": str(args)[:200],  # Truncate long args
                    "kwargs": str(kwargs)[:200]
                }
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful completion
                logger.debug(
                    f"Completed {func.__name__}",
                    extra={
                        "function_call": func.__name__,
                        "success": True
                    }
                )
                
                return result
                
            except Exception as e:
                # Log error
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    extra={
                        "function_call": func.__name__,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


# Convenience function to get logger with extensions
def get_logger(name: str) -> tuple[logging.Logger, PerformanceLogger, SecurityLogger]:
    """
    Get logger with performance and security extensions.
    
    Returns:
        Tuple of (logger, performance_logger, security_logger)
    """
    logger = logging.getLogger(name)
    perf_logger = PerformanceLogger(logger)
    sec_logger = SecurityLogger(logger)
    
    return logger, perf_logger, sec_logger