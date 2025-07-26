#!/usr/bin/env python3
"""
Unified Configuration System - Main Manager

The central configuration manager that orchestrates all configuration sources.
"""

import os
import logging
import threading
from typing import Any, Dict, List, Optional
from pathlib import Path

from .interfaces import (
    IUnifiedConfigManager, IConfigSource, ConfigValue, ConfigSource, ConfigSecurityLevel, ConfigSchema
)
from .sources import (
    EnvironmentConfigSource, YAMLConfigSource, JSONConfigSource, DefaultsConfigSource, CommandLineConfigSource
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
        
        # Thread safety
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        
        # Initialize default sources
        self._initialize_sources()
        self._load_schemas()
        
        # Don't load configuration immediately - let it be loaded on first access
        # self.load()
    
    def _initialize_sources(self):
        """Initialize all configuration sources in priority order."""
        
        # 1. Environment variables (highest priority)
        self.sources.append(EnvironmentConfigSource(prefix="APP_"))
        # Also include unprefixed environment variables for flexibility
        self.sources.append(EnvironmentConfigSource())
        
        # 2. Command line arguments (will be set externally)
        # This is added when CLI args are available
        
        # 3. Local configuration file
        local_config_yaml = self.config_dir / "settings.local.yaml"
        local_config_json = self.config_dir / "settings.local.json"
        if local_config_yaml.exists():
            self.sources.append(YAMLConfigSource(local_config_yaml, ConfigSource.LOCAL_FILE))
        elif local_config_json.exists():
            self.sources.append(JSONConfigSource(local_config_json, ConfigSource.LOCAL_FILE))
        
        # 4. Environment-specific configuration
        env = self.get_environment()
        env_config = self.config_dir / f"settings.{env}.yaml"
        if env_config.exists():
            self.sources.append(YAMLConfigSource(env_config, ConfigSource.ENV_FILE))
        else:
            # Try alternative naming convention for tests
            env_config_alt = self.config_dir / f"{env}.yaml"
            if env_config_alt.exists():
                self.sources.append(YAMLConfigSource(env_config_alt, ConfigSource.ENV_FILE))
        
        # 5. Main configuration file
        main_config = self.config_dir / "config.yaml"
        if main_config.exists():
            self.sources.append(YAMLConfigSource(main_config, ConfigSource.MAIN_CONFIG))
        else:
            # Try alternative naming convention for tests
            main_config_alt = self.config_dir / "main.yaml"
            if main_config_alt.exists():
                self.sources.append(YAMLConfigSource(main_config_alt, ConfigSource.MAIN_CONFIG))
        
        # 6. Defaults (lowest priority)
        defaults = self._get_default_config()
        self.sources.append(DefaultsConfigSource(defaults))
        
        # Sort sources by priority
        self.sources.sort(key=lambda s: s.priority)
    
    def _flatten_config(self, config: Dict[str, Any], prefix: str = "", separator: str = ".") -> Dict[str, Any]:
        """Flatten nested configuration dictionary using dot notation."""
        flattened = {}
        
        for key, value in config.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                flattened.update(self._flatten_config(value, new_key, separator))
            else:
                flattened[new_key] = value
        
        return flattened
    
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
    
    def register_schema(self, schema: ConfigSchema) -> None:
        """Register a configuration schema."""
        self._schemas[schema.key] = schema
        
    
    
    def get(self, key: str, default: Optional[Any] = None, type_hint: Optional[type] = None) -> Any:
        """Get configuration value."""
        with self._lock:
            # Check cache first
            cached_value = self.cache.get(key)
            if cached_value is not None:
                if type_hint and cached_value is not None:
                    try:
                        if type_hint == bool and isinstance(cached_value, str):
                            return cached_value.lower() in ('true', '1', 'yes', 'on')
                        elif type_hint in (int, float) and isinstance(cached_value, str):
                            return type_hint(cached_value)
                        elif type_hint == str:
                            return str(cached_value)
                        else:
                            return type_hint(cached_value)
                    except (ValueError, TypeError):
                        pass  # Fall through to normal logic
                return cached_value
                
            if not self._loaded:
                self._load()
                
            if key in self._config:
                value = self._config[key].value
                # Cache the value
                self.cache.set(key, value)
                
                if type_hint and value is not None:
                    try:
                        if type_hint == bool and isinstance(value, str):
                            return value.lower() in ('true', '1', 'yes', 'on')
                        elif type_hint in (int, float) and isinstance(value, str):
                            return type_hint(value)
                        elif type_hint == str:
                            return str(value)
                        else:
                            return type_hint(value)
                    except (ValueError, TypeError):
                        return default
                return value
            return default
    
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.DEFAULTS, 
            security_level: ConfigSecurityLevel = ConfigSecurityLevel.PUBLIC) -> None:
        """Set configuration value."""
        with self._lock:
            # Ensure config is loaded first
            if not self._loaded:
                self._load()
                
            config_value = ConfigValue(
                key=key,
                value=value,
                source=source,
                security_level=security_level
            )
            
            # Validate if schema exists
            if key in self._schemas:
                is_valid = self.validator.validate(config_value, self._schemas[key])
                if not is_valid:
                    errors = self.validator.get_validation_errors()
                    error_msg = f"Validation failed for {key}: {'; '.join(errors)}"
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)
            
            self._config[key] = config_value
            # Invalidate cache for this key since the value changed
            self.cache.invalidate(key)
    
    def has(self, key: str) -> bool:
        """Check if configuration key exists."""
        with self._lock:
            if not self._loaded:
                self._load()
            return key in self._config
    
    def get_all(self, prefix: Optional[str] = None) -> Dict[str, ConfigValue]:
        """Get all configuration values, optionally filtered by prefix."""
        with self._lock:
            if not self._loaded:
                self._load()
                
            result = {}
            for key, config_value in self._config.items():
                if prefix is None or key.startswith(prefix):
                    result[key] = config_value
            return result
    
    def reload(self) -> None:
        """Reload configuration from all sources."""
        with self._lock:
            self._config.clear()
            self._loaded = False
            # Re-initialize sources to pick up new config files
            self.sources.clear()
            self._initialize_sources()
            self._load()
    
    def validate_all(self) -> bool:
        """Validate all configuration values."""
        with self._lock:
            all_valid = True
            for key, config_value in self._config.items():
                if key in self._schemas:
                    is_valid = self.validator.validate(config_value, self._schemas[key])
                    if not is_valid:
                        all_valid = False
                        self.logger.error(f"Validation failed for {key}")
            return all_valid

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
        with self._lock:
            if args:
                # Remove any existing command line source
                self.sources = [s for s in self.sources if s.source_type != ConfigSource.COMMAND_LINE]
                
                # Add new command line source
                cli_source = CommandLineConfigSource(args)
                self.sources.append(cli_source)
                
                # Re-sort by priority
                self.sources.sort(key=lambda s: s.priority)
                
                # Force reload
                self._config.clear()
                self._loaded = False
                self._load()
    
    def load(self):
        """Load configuration from all sources."""
        with self._lock:
            self._load()
    
    def _load_sources(self):
        """Load configuration from all available sources."""
        # This method exists for compatibility with tests
        pass
    
    def _load(self):
        """Internal load method - assumes lock is already held."""
        if self._loaded:
            return
        
        self.logger.info("Loading configuration from all sources...")
        
        # Call _load_sources for test compatibility
        self._load_sources()
        
        # Clear existing configuration
        self._config.clear()
        
        # Load from each source in reverse priority order (lowest to highest)
        for source in reversed(self.sources):
            if not source.is_available():
                continue
            
            try:
                source_config = source.load()
                self.logger.debug(f"Loaded {len(source_config)} keys from {source.source_type.value}")
                
                # Flatten nested configuration for dot-notation access
                flattened_config = self._flatten_config(source_config)
                
                # First, store the original nested values
                for key, value in source_config.items():
                    # Only override if this source has strictly higher priority (lower number = higher priority)
                    # This prevents equal priority sources from overriding each other unpredictably
                    current_priority = self._config[key].source.get_priority() if key in self._config else float('inf')
                    new_priority = source.source_type.get_priority()
                    
                    if key not in self._config or new_priority < current_priority:
                        
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
                
                # Then, also store flattened values for dot notation access
                for key, value in flattened_config.items():
                    # Only add flattened keys if they have strictly higher priority
                    current_priority = self._config[key].source.get_priority() if key in self._config else float('inf')
                    new_priority = source.source_type.get_priority()
                    
                    if key not in self._config or new_priority < current_priority:
                        
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
