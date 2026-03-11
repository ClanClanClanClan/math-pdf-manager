#!/usr/bin/env python3
"""
Service Interfaces
Phase 1, Week 2: Strategic Transformation

Define clear interfaces for dependency injection to ensure loose coupling
and testability.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from pathlib import Path

class IConfigurationService(ABC):
    """Interface for configuration management."""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        pass
    
    @abstractmethod
    def get_section(self, section: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get configuration section."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        pass

class ILoggingService(ABC):
    """Interface for logging service."""
    
    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        pass
    
    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        pass
    
    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        pass

class IFileService(ABC):
    """Interface for file operations."""
    
    @abstractmethod
    def read_file(self, path: Path) -> str:
        """Read file content."""
        pass
    
    @abstractmethod
    def write_file(self, path: Path, content: str) -> None:
        """Write file content."""
        pass
    
    @abstractmethod
    def exists(self, path: Path) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    def list_files(self, directory: Path, pattern: str = "*") -> List[Path]:
        """List files in directory."""
        pass

class IValidationService(ABC):
    """Comprehensive validation service interface consolidating all validation systems.

    NOTE: This interface violates the Interface Segregation Principle (ISP) by
    combining path/file, network, security, content, and configuration validation
    into a single contract.  A future refactor should split it into focused
    interfaces (e.g. IPathValidator, INetworkValidator, IContentValidator,
    IConfigValidator) so that consumers only depend on the slice they need.
    """
    
    # === Core Path & File Validation ===
    @abstractmethod
    def validate_file_path(self, path: Path, base_path: Optional[Path] = None, allow_symlinks: bool = False) -> Path:
        """Validate file path for security and accessibility."""
        pass
    
    @abstractmethod
    def validate_filename(self, filename: str, allow_paths: bool = False) -> str:
        """Validate filename for security."""
        pass
    
    @abstractmethod
    def validate_template_directory(self, template_dir: str) -> bool:
        """Validate template directory exists and is accessible."""
        pass
    
    # === CLI & Input Validation ===
    @abstractmethod
    def validate_cli_arguments(self, args: Any) -> bool:
        """Validate command-line arguments for safety."""
        pass
    
    @abstractmethod
    def validate_string(self, value: str, min_length: int = 0, max_length: int = 1000, 
                       allowed_chars: Optional[set] = None) -> str:
        """Validate and sanitize string input."""
        pass
    
    # === Network & Format Validation ===
    @abstractmethod
    def validate_email(self, email: str) -> str:
        """Validate email address format."""
        pass
    
    @abstractmethod
    def validate_url(self, url: str, allowed_schemes: List[str] = None) -> str:
        """Validate URL format and scheme."""
        pass
    
    @abstractmethod
    def validate_ip_address(self, ip: str, version: Optional[int] = None) -> str:
        """Validate IP address."""
        pass
    
    # === Security Validation ===
    @abstractmethod
    def validate_against_sql_injection(self, value: str) -> str:
        """Check for SQL injection patterns."""
        pass
    
    @abstractmethod
    def validate_file_extension(self, filename: str, allowed_extensions: Optional[set] = None,
                               file_type: Optional[str] = None) -> str:
        """Validate file extension against allowed types."""
        pass
    
    @abstractmethod
    def validate_file_size(self, size: int, max_size_mb: float = 100) -> int:
        """Validate file size constraints."""
        pass
    
    # === Content & Mathematical Validation ===
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Detect language of mathematical/academic text."""
        pass
    
    @abstractmethod
    def has_mathematical_content(self, text: str) -> bool:
        """Check if text contains mathematical notation."""
        pass
    
    @abstractmethod
    def validate_mathematician_name(self, name: str) -> bool:
        """Validate if name appears to be a mathematician."""
        pass
    
    # === Configuration & Data Validation ===
    @abstractmethod
    def validate_config(self, config: Dict[str, Any], schema: Optional[Dict] = None) -> List[str]:
        """Validate configuration against schema, return list of errors."""
        pass
    
    @abstractmethod
    def validate_dict_structure(self, data: Dict[str, Any], required_keys: Optional[List[str]] = None,
                               optional_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate dictionary structure and keys."""
        pass
    
    # === Numeric Validation ===
    @abstractmethod
    def validate_integer(self, value: Any, min_value: Optional[int] = None, 
                        max_value: Optional[int] = None) -> int:
        """Validate integer input with optional bounds."""
        pass

class IMetricsService(ABC):
    """Interface for metrics collection."""
    
    @abstractmethod
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment counter metric."""
        pass
    
    @abstractmethod
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record gauge metric."""
        pass
    
    @abstractmethod
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record timing metric."""
        pass

class INotificationService(ABC):
    """Interface for notification services."""
    
    @abstractmethod
    def send_notification(self, message: str, level: str = "info") -> None:
        """Send notification."""
        pass
    
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str) -> None:
        """Send email notification."""
        pass

class ICacheService(ABC):
    """Interface for caching services."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete cached value."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass

class ISecurityService(ABC):
    """Interface for security services."""
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash password securely."""
        pass
    
    @abstractmethod
    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against hash."""
        pass
    
    @abstractmethod
    def generate_token(self, data: Dict[str, Any]) -> str:
        """Generate secure token."""
        pass
    
    @abstractmethod
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode token."""
        pass

# Protocol for dependency injection
class Injectable(Protocol):
    """Protocol for injectable services."""
    
    def __init__(self, *args, **kwargs) -> None:
        """Initialize service with dependencies."""
        pass