#!/usr/bin/env python3
"""
Configuration Unification Implementation

Creates a unified configuration system that consolidates all configuration sources
and provides a single, coherent interface for configuration management.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import logging

def create_unified_config_system():
    """Create the unified configuration system."""
    
    print("🚀 IMPLEMENTING UNIFIED CONFIGURATION SYSTEM")
    print("=" * 60)
    
    # Step 1: Create the core interfaces and enums
    interfaces_code = '''#!/usr/bin/env python3
"""
Unified Configuration System - Core Interfaces

Defines the interfaces and base classes for the unified configuration system.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Set
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
    def get_all(self) -> Dict[str, ConfigValue]:
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
'''
    
    # Step 2: Create configuration sources
    sources_code = '''#!/usr/bin/env python3
"""
Unified Configuration System - Configuration Sources

Implements various configuration sources (environment, files, etc.).
"""

import os
import yaml
import json
from pathlib import Path
from typing import Any, Dict, Optional
import logging

from .interfaces import IConfigSource, ConfigSource


class EnvironmentConfigSource(IConfigSource):
    """Configuration source for environment variables."""
    
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self.logger = logging.getLogger(__name__)
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        
        for key, value in os.environ.items():
            if self.prefix and not key.startswith(self.prefix):
                continue
            
            # Remove prefix if specified
            config_key = key[len(self.prefix):] if self.prefix else key
            
            # Try to parse as JSON for complex values
            try:
                config[config_key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                config[config_key] = value
        
        return config
    
    def save(self, config: Dict[str, Any]) -> bool:
        """Environment variables cannot be saved."""
        return False
    
    def is_available(self) -> bool:
        """Environment variables are always available."""
        return True
    
    @property
    def source_type(self) -> ConfigSource:
        return ConfigSource.ENVIRONMENT
    
    @property
    def priority(self) -> int:
        return 1  # Highest priority


class YAMLConfigSource(IConfigSource):
    """Configuration source for YAML files."""
    
    def __init__(self, file_path: Path, source_type: ConfigSource = ConfigSource.MAIN_CONFIG):
        self.file_path = Path(file_path)
        self._source_type = source_type
        self.logger = logging.getLogger(__name__)
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.is_available():
            return {}
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
                self.logger.debug(f"Loaded config from {self.file_path}")
                return config
        except Exception as e:
            self.logger.error(f"Failed to load YAML config from {self.file_path}: {e}")
            return {}
    
    def save(self, config: Dict[str, Any]) -> bool:
        """Save configuration to YAML file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            self.logger.info(f"Saved config to {self.file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save YAML config to {self.file_path}: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if YAML file exists and is readable."""
        return self.file_path.exists() and self.file_path.is_file()
    
    @property
    def source_type(self) -> ConfigSource:
        return self._source_type
    
    @property
    def priority(self) -> int:
        priorities = {
            ConfigSource.LOCAL_FILE: 3,
            ConfigSource.ENV_FILE: 4,
            ConfigSource.MAIN_CONFIG: 5
        }
        return priorities.get(self._source_type, 5)


class JSONConfigSource(IConfigSource):
    """Configuration source for JSON files."""
    
    def __init__(self, file_path: Path, source_type: ConfigSource = ConfigSource.MAIN_CONFIG):
        self.file_path = Path(file_path)
        self._source_type = source_type
        self.logger = logging.getLogger(__name__)
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if not self.is_available():
            return {}
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.logger.debug(f"Loaded config from {self.file_path}")
                return config
        except Exception as e:
            self.logger.error(f"Failed to load JSON config from {self.file_path}: {e}")
            return {}
    
    def save(self, config: Dict[str, Any]) -> bool:
        """Save configuration to JSON file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved config to {self.file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save JSON config to {self.file_path}: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if JSON file exists and is readable."""
        return self.file_path.exists() and self.file_path.is_file()
    
    @property
    def source_type(self) -> ConfigSource:
        return self._source_type
    
    @property
    def priority(self) -> int:
        priorities = {
            ConfigSource.LOCAL_FILE: 3,
            ConfigSource.ENV_FILE: 4,
            ConfigSource.MAIN_CONFIG: 5
        }
        return priorities.get(self._source_type, 5)


class DefaultsConfigSource(IConfigSource):
    """Configuration source for default values."""
    
    def __init__(self, defaults: Dict[str, Any]):
        self.defaults = defaults or {}
        self.logger = logging.getLogger(__name__)
    
    def load(self) -> Dict[str, Any]:
        """Load default configuration values."""
        return self.defaults.copy()
    
    def save(self, config: Dict[str, Any]) -> bool:
        """Defaults are read-only."""
        return False
    
    def is_available(self) -> bool:
        """Defaults are always available."""
        return True
    
    @property
    def source_type(self) -> ConfigSource:
        return ConfigSource.DEFAULTS
    
    @property
    def priority(self) -> int:
        return 99  # Lowest priority


class CommandLineConfigSource(IConfigSource):
    """Configuration source for command-line arguments."""
    
    def __init__(self, args: Optional[Dict[str, Any]] = None):
        self.args = args or {}
        self.logger = logging.getLogger(__name__)
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from command-line arguments."""
        return self.args.copy()
    
    def save(self, config: Dict[str, Any]) -> bool:
        """Command-line arguments cannot be saved."""
        return False
    
    def is_available(self) -> bool:
        """Available if arguments were provided."""
        return bool(self.args)
    
    @property
    def source_type(self) -> ConfigSource:
        return ConfigSource.COMMAND_LINE
    
    @property
    def priority(self) -> int:
        return 2  # Second highest priority
'''
    
    # Step 3: Create the unified configuration manager
    manager_code = '''#!/usr/bin/env python3
"""
Unified Configuration System - Main Manager

The central configuration manager that orchestrates all configuration sources.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

from .interfaces import (
    IUnifiedConfigManager, IConfigSource, IConfigValidator, IConfigCache,
    ConfigValue, ConfigSource, ConfigSecurityLevel, ConfigSchema
)
from .sources import (
    EnvironmentConfigSource, YAMLConfigSource, JSONConfigSource,
    DefaultsConfigSource, CommandLineConfigSource
)
from .validators import ConfigValidator
from .cache import ConfigCache
from .security import ConfigSecurityManager


class UnifiedConfigManager(IUnifiedConfigManager):
    """
    Unified configuration manager that consolidates all configuration sources.
    
    This is the main entry point for all configuration access in the application.
    It manages multiple configuration sources with proper priority handling,
    validation, caching, and security.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the unified configuration manager."""
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.sources: List[IConfigSource] = []
        self.validator = ConfigValidator()
        self.cache = ConfigCache()
        self.security = ConfigSecurityManager()
        
        # Configuration state
        self._config: Dict[str, ConfigValue] = {}
        self._schemas: Dict[str, ConfigSchema] = {}
        self._loaded = False
        
        # Initialize default sources
        self._initialize_sources()
        self._load_schemas()
    
    def _initialize_sources(self):
        """Initialize all configuration sources in priority order."""
        
        # 1. Environment variables (highest priority)
        self.sources.append(EnvironmentConfigSource())
        
        # 2. Command line arguments (will be set externally)
        # This is added when CLI args are available
        
        # 3. Local configuration file
        local_config = self.config_dir / "settings.local.yaml"
        if local_config.exists():
            self.sources.append(YAMLConfigSource(local_config, ConfigSource.LOCAL_FILE))
        
        # 4. Environment-specific configuration
        env = self.get_environment()
        env_config = self.config_dir / f"settings.{env}.yaml"
        if env_config.exists():
            self.sources.append(YAMLConfigSource(env_config, ConfigSource.ENV_FILE))
        
        # 5. Main configuration file
        main_config = self.config_dir / "config.yaml"
        if main_config.exists():
            self.sources.append(YAMLConfigSource(main_config, ConfigSource.MAIN_CONFIG))
        
        # 6. Defaults (lowest priority)
        defaults = self._get_default_config()
        self.sources.append(DefaultsConfigSource(defaults))
        
        # Sort sources by priority
        self.sources.sort(key=lambda s: s.priority)
    
    def _load_schemas(self):
        """Load configuration schemas."""
        schema_file = self.config_dir / "config_definitions.yaml"
        if schema_file.exists():
            try:
                import yaml
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_data = yaml.safe_load(f) or {}
                
                for key, definition in schema_data.items():
                    self._schemas[key] = ConfigSchema(
                        key=key,
                        type=self._parse_type(definition.get('type', 'str')),
                        security_level=ConfigSecurityLevel(definition.get('security_level', 'public')),
                        required=definition.get('required', False),
                        default=definition.get('default'),
                        description=definition.get('description'),
                        validation_rules=definition.get('validation'),
                        env_var=definition.get('env_var')
                    )
                    
            except Exception as e:
                self.logger.error(f"Failed to load schemas: {e}")
    
    def get_environment(self) -> str:
        """Get current environment (development, staging, production)."""
        return os.environ.get('ENVIRONMENT', 'development').lower()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            # Application defaults
            'app_name': 'Math PDF Manager',
            'version': '2.0.0',
            'debug': False,
            'log_level': 'INFO',
            
            # Performance defaults
            'cache_ttl': 3600,
            'max_workers': 4,
            'timeout': 30,
            
            # Security defaults
            'encryption_enabled': True,
            'session_timeout': 3600,
            
            # Processing defaults
            'max_file_size_mb': 100,
            'supported_formats': ['pdf'],
            'ocr_enabled': False,
            
            # Paths (will be overridden by actual config)
            'base_path': str(Path.cwd()),
            'data_path': 'data',
            'cache_path': 'cache',
            'logs_path': 'logs'
        }
    
    def _parse_type(self, type_str: str) -> type:
        """Parse type string to Python type."""
        type_map = {
            'str': str,
            'string': str,
            'int': int,
            'integer': int,
            'float': float,
            'bool': bool,
            'boolean': bool,
            'list': list,
            'dict': dict
        }
        return type_map.get(type_str.lower(), str)
    
    def add_command_line_args(self, args: Dict[str, Any]):
        """Add command-line arguments as a configuration source."""
        if args:
            # Remove any existing command line source
            self.sources = [s for s in self.sources if s.source_type != ConfigSource.COMMAND_LINE]
            
            # Add new command line source
            cli_source = CommandLineConfigSource(args)
            self.sources.append(cli_source)
            
            # Re-sort by priority
            self.sources.sort(key=lambda s: s.priority)
            
            # Force reload
            self._loaded = False
            self.reload()
    
    def load(self):
        """Load configuration from all sources."""
        if self._loaded:
            return
        
        self.logger.info("Loading configuration from all sources...")
        
        # Clear existing configuration
        self._config.clear()
        
        # Load from each source in reverse priority order (lowest to highest)
        for source in reversed(self.sources):
            if not source.is_available():
                continue
            
            try:
                source_config = source.load()
                self.logger.debug(f"Loaded {len(source_config)} keys from {source.source_type.value}")
                
                # Merge configuration with proper priority
                for key, value in source_config.items():
                    # Only override if this source has higher priority
                    if key not in self._config or source.priority < self._config[key].source.value:
                        
                        # Get schema if available
                        schema = self._schemas.get(key)
                        security_level = schema.security_level if schema else ConfigSecurityLevel.PUBLIC
                        
                        # Handle secure values
                        if security_level in [ConfigSecurityLevel.SENSITIVE, ConfigSecurityLevel.SECRET]:
                            value = self.security.decrypt_if_needed(value)
                        
                        self._config[key] = ConfigValue(
                            key=key,
                            value=value,
                            source=source.source_type,
                            security_level=security_level,
                            description=schema.description if schema else None,
                            required=schema.required if schema else False
                        )
                        
            except Exception as e:
                self.logger.error(f"Failed to load from {source.source_type.value}: {e}")
        
        self._loaded = True
        self.logger.info(f"Configuration loaded: {len(self._config)} keys from {len(self.sources)} sources")
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value."""
        if not self._loaded:
            self.load()
        
        # Check cache first
        cached_value = self.cache.get(key)
        if cached_value is not None:
            return cached_value
        
        # Get from configuration
        if key in self._config:
            value = self._config[key].value
            
            # Cache the value
            self.cache.set(key, value)
            return value
        
        # Return default or schema default
        schema = self._schemas.get(key)
        if schema and schema.default is not None:
            return schema.default
        
        return default
    
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.DEFAULTS) -> None:
        """Set configuration value."""
        # Validate if schema exists
        schema = self._schemas.get(key)
        if schema:
            if not self.validator.validate(key, value, schema):
                errors = self.validator.get_validation_errors()
                raise ValueError(f"Validation failed for {key}: {', '.join(errors)}")
        
        # Handle security
        security_level = schema.security_level if schema else ConfigSecurityLevel.PUBLIC
        if security_level in [ConfigSecurityLevel.SENSITIVE, ConfigSecurityLevel.SECRET]:
            value = self.security.encrypt_if_needed(value, security_level)
        
        # Set the value
        self._config[key] = ConfigValue(
            key=key,
            value=value,
            source=source,
            security_level=security_level,
            required=schema.required if schema else False
        )
        
        # Invalidate cache
        self.cache.invalidate(key)
    
    def get_all(self) -> Dict[str, ConfigValue]:
        """Get all configuration values."""
        if not self._loaded:
            self.load()
        return self._config.copy()
    
    def reload(self) -> None:
        """Reload configuration from all sources."""
        self._loaded = False
        self.cache.invalidate()  # Clear all cache
        self.load()
    
    def validate_all(self) -> bool:
        """Validate all configuration values."""
        if not self._loaded:
            self.load()
        
        all_valid = True
        validation_errors = []
        
        # Check required values
        for key, schema in self._schemas.items():
            if schema.required and key not in self._config:
                all_valid = False
                validation_errors.append(f"Required configuration key missing: {key}")
        
        # Validate existing values
        for key, config_value in self._config.items():
            schema = self._schemas.get(key)
            if schema:
                if not self.validator.validate(key, config_value.value, schema):
                    all_valid = False
                    errors = self.validator.get_validation_errors()
                    validation_errors.extend(errors)
        
        if validation_errors:
            self.logger.error(f"Configuration validation failed: {validation_errors}")
        
        return all_valid
    
    def get_source_info(self, key: str) -> Optional[ConfigValue]:
        """Get source information for a configuration key."""
        if not self._loaded:
            self.load()
        return self._config.get(key)
    
    def get_keys_by_source(self, source: ConfigSource) -> List[str]:
        """Get all keys from a specific source."""
        if not self._loaded:
            self.load()
        return [key for key, value in self._config.items() if value.source == source]
    
    def export_config(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export configuration to a dictionary."""
        if not self._loaded:
            self.load()
        
        exported = {}
        for key, config_value in self._config.items():
            # Skip secrets unless explicitly requested
            if (config_value.security_level == ConfigSecurityLevel.SECRET and 
                not include_secrets):
                continue
            
            exported[key] = config_value.value
        
        return exported
    
    def get_schema(self, key: str) -> Optional[ConfigSchema]:
        """Get schema for a configuration key."""
        return self._schemas.get(key)
    
    def add_schema(self, schema: ConfigSchema):
        """Add a configuration schema."""
        self._schemas[schema.key] = schema


# Global configuration manager instance
_config_manager: Optional[UnifiedConfigManager] = None


def get_config_manager() -> UnifiedConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = UnifiedConfigManager()
    return _config_manager


def get_config(key: str, default: Optional[Any] = None) -> Any:
    """Convenience function to get configuration value."""
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any) -> None:
    """Convenience function to set configuration value."""
    get_config_manager().set(key, value)


def reload_config() -> None:
    """Convenience function to reload configuration."""
    get_config_manager().reload()
'''
    
    # Step 4: Create supporting components (validator, cache, security)
    validator_code = '''#!/usr/bin/env python3
"""
Unified Configuration System - Validator

Provides validation for configuration values based on schemas.
"""

import re
import ipaddress
from typing import Any, List
from urllib.parse import urlparse

from .interfaces import IConfigValidator, ConfigSchema, ConfigSecurityLevel


class ConfigValidator(IConfigValidator):
    """Configuration validator with comprehensive validation rules."""
    
    def __init__(self):
        self.errors: List[str] = []
    
    def validate(self, key: str, value: Any, schema: ConfigSchema) -> bool:
        """Validate a configuration value against its schema."""
        self.errors.clear()
        
        # Type validation
        if not self._validate_type(value, schema.type):
            self.errors.append(f"{key}: Expected {schema.type.__name__}, got {type(value).__name__}")
            return False
        
        # Custom validation rules
        if schema.validation_rules:
            if not self._validate_rules(key, value, schema.validation_rules):
                return False
        
        return len(self.errors) == 0
    
    def get_validation_errors(self) -> List[str]:
        """Get validation errors from last validation."""
        return self.errors.copy()
    
    def _validate_type(self, value: Any, expected_type: type) -> bool:
        """Validate value type."""
        if expected_type == str:
            return isinstance(value, str)
        elif expected_type == int:
            return isinstance(value, int) or (isinstance(value, str) and value.isdigit())
        elif expected_type == float:
            return isinstance(value, (int, float)) or (isinstance(value, str) and self._is_number(value))
        elif expected_type == bool:
            return isinstance(value, bool) or value in ['true', 'false', '1', '0', 'yes', 'no']
        elif expected_type == list:
            return isinstance(value, list)
        elif expected_type == dict:
            return isinstance(value, dict)
        
        return True
    
    def _validate_rules(self, key: str, value: Any, rules: dict) -> bool:
        """Validate value against custom rules."""
        
        # String validation
        if isinstance(value, str):
            if 'min_length' in rules and len(value) < rules['min_length']:
                self.errors.append(f"{key}: String too short (min: {rules['min_length']})")
                return False
            
            if 'max_length' in rules and len(value) > rules['max_length']:
                self.errors.append(f"{key}: String too long (max: {rules['max_length']})")
                return False
            
            if 'pattern' in rules:
                pattern = re.compile(rules['pattern'])
                if not pattern.match(value):
                    self.errors.append(f"{key}: Does not match required pattern")
                    return False
            
            if 'format' in rules:
                if not self._validate_format(key, value, rules['format']):
                    return False
        
        # Numeric validation
        if isinstance(value, (int, float)):
            if 'min_value' in rules and value < rules['min_value']:
                self.errors.append(f"{key}: Value too small (min: {rules['min_value']})")
                return False
            
            if 'max_value' in rules and value > rules['max_value']:
                self.errors.append(f"{key}: Value too large (max: {rules['max_value']})")
                return False
        
        # List validation
        if isinstance(value, list):
            if 'min_items' in rules and len(value) < rules['min_items']:
                self.errors.append(f"{key}: Too few items (min: {rules['min_items']})")
                return False
            
            if 'max_items' in rules and len(value) > rules['max_items']:
                self.errors.append(f"{key}: Too many items (max: {rules['max_items']})")
                return False
        
        # Choice validation
        if 'choices' in rules and value not in rules['choices']:
            self.errors.append(f"{key}: Invalid choice. Must be one of: {rules['choices']}")
            return False
        
        return True
    
    def _validate_format(self, key: str, value: str, format_type: str) -> bool:
        """Validate string format."""
        
        if format_type == 'email':
            pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$')
            if not pattern.match(value):
                self.errors.append(f"{key}: Invalid email format")
                return False
        
        elif format_type == 'url':
            try:
                result = urlparse(value)
                if not all([result.scheme, result.netloc]):
                    raise ValueError()
            except:
                self.errors.append(f"{key}: Invalid URL format")
                return False
        
        elif format_type == 'ip':
            try:
                ipaddress.ip_address(value)
            except ValueError:
                self.errors.append(f"{key}: Invalid IP address")
                return False
        
        elif format_type == 'path':
            from pathlib import Path
            try:
                Path(value)
            except:
                self.errors.append(f"{key}: Invalid path format")
                return False
        
        elif format_type == 'api_key':
            # Basic API key validation (alphanumeric, reasonable length)
            if not re.match(r'^[a-zA-Z0-9_-]{16,128}$', value):
                self.errors.append(f"{key}: Invalid API key format")
                return False
        
        return True
    
    def _is_number(self, value: str) -> bool:
        """Check if string represents a number."""
        try:
            float(value)
            return True
        except ValueError:
            return False
'''
    
    # Create directory structure and write files
    config_dir = Path("src/core/unified_config")
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Write all the files
    files_to_create = [
        ("interfaces.py", interfaces_code),
        ("sources.py", sources_code),
        ("manager.py", manager_code),
        ("validators.py", validator_code),
    ]
    
    for filename, content in files_to_create:
        file_path = config_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created {file_path}")
    
    # Create __init__.py
    init_content = '''"""
Unified Configuration System

A comprehensive configuration management system that consolidates all configuration
sources and provides a single, coherent interface for configuration access.

Usage:
    from src.core.unified_config import get_config, set_config, get_config_manager
    
    # Get configuration values
    database_url = get_config('database_url', 'sqlite:///default.db')
    debug_mode = get_config('debug', False)
    
    # Set configuration values
    set_config('log_level', 'DEBUG')
    
    # Access the manager directly
    manager = get_config_manager()
    manager.reload()
"""

from .manager import UnifiedConfigManager, get_config_manager, get_config, set_config, reload_config
from .interfaces import ConfigSecurityLevel, ConfigSource, ConfigValue, ConfigSchema
from .sources import (
    EnvironmentConfigSource, YAMLConfigSource, JSONConfigSource,
    DefaultsConfigSource, CommandLineConfigSource
)

__all__ = [
    # Main interface
    'get_config_manager',
    'get_config', 
    'set_config',
    'reload_config',
    
    # Core classes
    'UnifiedConfigManager',
    
    # Enums and data classes
    'ConfigSecurityLevel',
    'ConfigSource', 
    'ConfigValue',
    'ConfigSchema',
    
    # Sources
    'EnvironmentConfigSource',
    'YAMLConfigSource', 
    'JSONConfigSource',
    'DefaultsConfigSource',
    'CommandLineConfigSource'
]
'''
    
    with open(config_dir / "__init__.py", 'w', encoding='utf-8') as f:
        f.write(init_content)
    print(f"✅ Created {config_dir / '__init__.py'}")
    
    # Create additional supporting files
    cache_code = '''#!/usr/bin/env python3
"""
Unified Configuration System - Cache

Provides caching for configuration values to improve performance.
"""

import time
from typing import Any, Dict, Optional

from .interfaces import IConfigCache


class ConfigCache(IConfigCache):
    """Simple in-memory cache for configuration values."""
    
    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached configuration value."""
        if key in self._cache:
            entry = self._cache[key]
            
            # Check if expired
            if entry['expires'] > time.time():
                return entry['value']
            else:
                # Remove expired entry
                del self._cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached configuration value."""
        expires = time.time() + (ttl or self.default_ttl)
        self._cache[key] = {
            'value': value,
            'expires': expires,
            'created': time.time()
        }
    
    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate cache (specific key or all)."""
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(1 for entry in self._cache.values() 
                           if entry['expires'] > current_time)
        
        return {
            'total_entries': len(self._cache),
            'valid_entries': valid_entries,
            'expired_entries': len(self._cache) - valid_entries
        }
'''
    
    security_code = '''#!/usr/bin/env python3
"""
Unified Configuration System - Security

Provides security features for configuration management.
"""

import os
import base64
from typing import Any
from cryptography.fernet import Fernet

from .interfaces import ConfigSecurityLevel


class ConfigSecurityManager:
    """Manages security for configuration values."""
    
    def __init__(self):
        self._encryption_key = self._get_or_create_key()
        self._cipher = Fernet(self._encryption_key) if self._encryption_key else None
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key."""
        key_env = os.environ.get('CONFIG_ENCRYPTION_KEY')
        if key_env:
            return base64.urlsafe_b64decode(key_env.encode())
        
        # For development, create a key (in production, this should be managed securely)
        return Fernet.generate_key()
    
    def encrypt_if_needed(self, value: Any, security_level: ConfigSecurityLevel) -> Any:
        """Encrypt value if security level requires it."""
        if security_level == ConfigSecurityLevel.SECRET and self._cipher:
            if isinstance(value, str):
                encrypted = self._cipher.encrypt(value.encode())
                return base64.urlsafe_b64encode(encrypted).decode()
        
        return value
    
    def decrypt_if_needed(self, value: Any) -> Any:
        """Decrypt value if it appears to be encrypted."""
        if isinstance(value, str) and self._cipher:
            try:
                # Check if it looks like our encrypted format
                if self._looks_encrypted(value):
                    encrypted_bytes = base64.urlsafe_b64decode(value.encode())
                    decrypted = self._cipher.decrypt(encrypted_bytes)
                    return decrypted.decode()
            except Exception:
                pass  # Not encrypted or failed to decrypt
        
        return value
    
    def _looks_encrypted(self, value: str) -> bool:
        """Heuristic to check if a string looks encrypted."""
        try:
            base64.urlsafe_b64decode(value.encode())
            # If it's valid base64 and long enough, might be encrypted
            return len(value) > 40 and not any(c in value for c in [' ', '.', '/', '\\\\'])
        except:
            return False
'''
    
    # Write additional files
    additional_files = [
        ("cache.py", cache_code),
        ("security.py", security_code),
    ]
    
    for filename, content in additional_files:
        file_path = config_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created {file_path}")
    
    print("\n🎉 UNIFIED CONFIGURATION SYSTEM CREATED!")
    print("=" * 60)
    print(f"📁 Created in: {config_dir}")
    print(f"📄 Files created: {len(files_to_create) + len(additional_files) + 1}")
    print("\n📋 Components:")
    print("  • UnifiedConfigManager - Central configuration orchestrator")
    print("  • ConfigSource implementations - Environment, YAML, JSON, etc.")
    print("  • ConfigValidator - Schema-based validation")
    print("  • ConfigCache - Performance optimization")
    print("  • ConfigSecurityManager - Credential protection")
    
    print("\n🔗 Usage:")
    print("  from src.core.unified_config import get_config, set_config")
    print("  database_url = get_config('database_url', 'default')")
    print("  set_config('debug', True)")


if __name__ == "__main__":
    create_unified_config_system()