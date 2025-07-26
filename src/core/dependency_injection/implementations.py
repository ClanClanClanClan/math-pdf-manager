#!/usr/bin/env python3
"""
Service Implementations
Phase 1, Week 2: Strategic Transformation

Concrete implementations of service interfaces for dependency injection.
"""

import logging
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.dependency_injection.interfaces import (
    IConfigurationService, ILoggingService, IFileService, IMetricsService, INotificationService, ICacheService, ISecurityService
)
from core.dependency_injection.container import service
from core.config.secure_config import SecureConfigManager as SecureConfig

# Import the unified validation service (auto-registers via @service decorator)

@service(IConfigurationService, singleton=True)
class ConfigurationService:
    """Configuration service implementation."""
    
    def __init__(self):
        self._config = SecureConfig()
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)
    
    def get_section(self, section: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get configuration section."""
        return self._config.get_section(section, default or {})
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config.set(key, value)

@service(ILoggingService, singleton=True)
class LoggingService:
    """Logging service implementation."""
    
    def __init__(self, config_service: IConfigurationService):
        self._logger = logging.getLogger('academic_papers')
        self._config = config_service
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = self._config.get('logging.level', 'INFO')
        self._logger.setLevel(getattr(logging, log_level))
        
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._logger.error(message, extra=kwargs)

@service(IFileService, singleton=True)
class FileService:
    """File service implementation."""
    
    def __init__(self, logging_service: ILoggingService):
        self._logger = logging_service
        
    def read_file(self, path: Path) -> str:
        """Read file content."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self._logger.error(f"Error reading file {path}: {e}")
            raise
    
    def write_file(self, path: Path, content: str) -> None:
        """Write file content."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            self._logger.error(f"Error writing file {path}: {e}")
            raise
    
    def exists(self, path: Path) -> bool:
        """Check if file exists."""
        return path.exists()
    
    def list_files(self, directory: Path, pattern: str = "*") -> List[Path]:
        """List files in directory."""
        try:
            return list(directory.glob(pattern))
        except Exception as e:
            self._logger.error(f"Error listing files in {directory}: {e}")
            return []

# ValidationService removed - replaced by UnifiedValidationService which auto-registers via @service decorator

@service(IMetricsService, singleton=True)
class MetricsService:
    """Metrics service implementation."""
    
    def __init__(self, logging_service: ILoggingService):
        self._logger = logging_service
        self._metrics = {}
        
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment counter metric."""
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        self._metrics[key] = self._metrics.get(key, 0) + value
        self._logger.debug(f"Counter {name} incremented by {value}")
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record gauge metric."""
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        self._metrics[key] = value
        self._logger.debug(f"Gauge {name} recorded value {value}")
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record timing metric."""
        key = f"{name}_timing:{json.dumps(tags or {}, sort_keys=True)}"
        self._metrics[key] = duration
        self._logger.debug(f"Timing {name} recorded duration {duration}ms")

@service(INotificationService, singleton=True)
class NotificationService:
    """Notification service implementation."""
    
    def __init__(self, logging_service: ILoggingService):
        self._logger = logging_service
        
    def send_notification(self, message: str, level: str = "info") -> None:
        """Send notification."""
        # For now, just log the notification
        if level == "error":
            self._logger.error(f"NOTIFICATION: {message}")
        elif level == "warning":
            self._logger.warning(f"NOTIFICATION: {message}")
        else:
            self._logger.info(f"NOTIFICATION: {message}")
    
    def send_email(self, to: str, subject: str, body: str) -> None:
        """Send email notification."""
        # Placeholder implementation
        self._logger.info(f"EMAIL: To={to}, Subject={subject}, Body={body[:100]}...")

@service(ICacheService, singleton=True)
class InMemoryCacheService:
    """In-memory cache service implementation."""
    
    def __init__(self, logging_service: ILoggingService):
        self._logger = logging_service
        self._cache = {}
        self._ttl = {}
        
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        if key in self._cache:
            # Check TTL
            if key in self._ttl and time.time() > self._ttl[key]:
                self.delete(key)
                return None
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value."""
        self._cache[key] = value
        if ttl:
            self._ttl[key] = time.time() + ttl
        self._logger.debug(f"Cache set: {key}")
    
    def delete(self, key: str) -> None:
        """Delete cached value."""
        self._cache.pop(key, None)
        self._ttl.pop(key, None)
        self._logger.debug(f"Cache deleted: {key}")
    
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        self._ttl.clear()
        self._logger.debug("Cache cleared")

@service(ISecurityService, singleton=True)
class SecurityService:
    """Security service implementation."""
    
    def __init__(self, logging_service: ILoggingService):
        self._logger = logging_service
        
    def hash_password(self, password: str) -> str:
        """Hash password securely."""
        import hashlib
        import secrets
        
        # Generate salt
        salt = secrets.token_hex(32)
        
        # Hash password with salt
        hash_value = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        
        return f"{salt}:{hash_value.hex()}"
    
    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against hash."""
        try:
            salt, stored_hash = hash.split(':')
            hash_value = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hash_value.hex() == stored_hash
        except Exception as e:
            self._logger.error(f"Password verification error: {e}")
            return False
    
    def generate_token(self, data: Dict[str, Any]) -> str:
        """Generate secure token."""
        import secrets
        import base64
        
        # Simple token generation (in production, use JWT or similar)
        token_data = {
            'data': data,
            'timestamp': time.time(),
            'random': secrets.token_hex(16)
        }
        
        return base64.b64encode(json.dumps(token_data).encode()).decode()
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode token."""
        try:
            import base64
            
            decoded = base64.b64decode(token.encode()).decode()
            token_data = json.loads(decoded)
            
            # Check if token is not too old (1 hour TTL)
            if time.time() - token_data['timestamp'] > 3600:
                return None
                
            return token_data['data']
        except Exception as e:
            self._logger.error(f"Token verification error: {e}")
            return None