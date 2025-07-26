#!/usr/bin/env python3
"""
Unified Configuration System - Core Interfaces

Defines the interfaces and base classes for the unified configuration system.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass


class ConfigSecurityLevel(Enum):
    """Security levels for configuration values."""
    PUBLIC = "public"        # No protection needed
    INTERNAL = "internal"    # Basic access control
    SENSITIVE = "sensitive"  # Encrypted storage
    SECRET = "secret"        # Keyring + encryption


class ConfigSource(Enum):
    """Configuration source types in priority order."""
    ENVIRONMENT = "environment"      # Highest priority
    COMMAND_LINE = "command_line"
    LOCAL_FILE = "local_file"
    ENV_FILE = "env_file"
    MAIN_CONFIG = "main_config"
    DEFAULTS = "defaults"            # Lowest priority
    
    def get_priority(self) -> int:
        """Get the priority (lower = higher priority)."""
        priority_map = {
            ConfigSource.ENVIRONMENT: 1,
            ConfigSource.COMMAND_LINE: 2,
            ConfigSource.LOCAL_FILE: 3,
            ConfigSource.ENV_FILE: 4,
            ConfigSource.MAIN_CONFIG: 5,
            ConfigSource.DEFAULTS: 99
        }
        return priority_map.get(self, 50)


@dataclass
class ConfigValue:
    """Represents a configuration value with metadata."""
    key: str
    value: Any
    source: ConfigSource
    security_level: ConfigSecurityLevel = ConfigSecurityLevel.PUBLIC
    description: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None
    validation_rules: Optional[Dict[str, Any]] = None


@dataclass
class ConfigSchema:
    """Configuration schema definition."""
    key: str
    type: Type
    security_level: ConfigSecurityLevel
    required: bool = False
    default: Optional[Any] = None
    description: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None
    env_var: Optional[str] = None


class IConfigSource(ABC):
    """Interface for configuration sources."""
    
    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """Load configuration from this source."""
        pass
    
    @abstractmethod
    def save(self, config: Dict[str, Any]) -> bool:
        """Save configuration to this source if supported."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this configuration source is available."""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> ConfigSource:
        """Get the source type."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Get the priority (lower = higher priority)."""
        pass


class IConfigValidator(ABC):
    """Interface for configuration validators."""
    
    @abstractmethod
    def validate(self, key: str, value: Any, schema: ConfigSchema) -> bool:
        """Validate a configuration value."""
        pass
    
    @abstractmethod
    def get_validation_errors(self) -> List[str]:
        """Get validation errors from last validation."""
        pass


class IConfigCache(ABC):
    """Interface for configuration caching."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached configuration value."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached configuration value."""
        pass
    
    @abstractmethod
    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate cache (specific key or all)."""
        pass


class IUnifiedConfigManager(ABC):
    """Interface for the unified configuration manager."""
    
    @abstractmethod
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.DEFAULTS) -> None:
        """Set configuration value."""
        pass
    
    @abstractmethod
    def get_all(self, prefix: Optional[str] = None) -> Dict[str, ConfigValue]:
        """Get all configuration values."""
        pass
    
    @abstractmethod
    def reload(self) -> None:
        """Reload configuration from all sources."""
        pass
    
    @abstractmethod
    def validate_all(self) -> bool:
        """Validate all configuration values."""
        pass
    
    @abstractmethod
    def get_source_info(self, key: str) -> Optional[ConfigValue]:
        """Get source information for a configuration key."""
        pass
