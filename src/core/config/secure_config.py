"""
Secure Configuration Foundation
Provides secure, validated configuration management for the academic papers system.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import yaml
import json
from enum import Enum

# Try to import secure credential manager
try:
    from src.secure_credential_manager import SecureCredentialManager
    SECURE_CREDENTIALS_AVAILABLE = True
except ImportError:
    SECURE_CREDENTIALS_AVAILABLE = False

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass

class SecurityLevel(Enum):
    """Security levels for configuration values."""
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    SECRET = "secret"

@dataclass
class ConfigValue:
    """Represents a configuration value with metadata."""
    key: str
    value: Any
    security_level: SecurityLevel
    required: bool = False
    description: str = ""
    validation_func: Optional[callable] = None

class SecureConfigManager:
    """
    Centralized secure configuration management.
    
    Features:
    - No hardcoded defaults for sensitive values
    - Proper environment variable handling
    - Configuration validation
    - Security level enforcement
    - Centralized credential management
    """
    
    def __init__(self, app_name: str = "academic_papers"):
        self.app_name = app_name
        self.config_cache: Dict[str, Any] = {}
        self.config_definitions: Dict[str, ConfigValue] = {}
        
        # Initialize secure credential manager if available
        if SECURE_CREDENTIALS_AVAILABLE:
            self.credential_manager = SecureCredentialManager(app_name)
        else:
            self.credential_manager = None
            logger.warning("Secure credential manager not available, using fallback")
        
        # Load configuration definitions
        self._load_config_definitions()
    
    def _load_config_definitions(self):
        """Load configuration definitions from YAML file."""
        config_file = Path(__file__).parent / "config_definitions.yaml"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    definitions = yaml.safe_load(f)
                    self._parse_definitions(definitions)
            except Exception as e:
                logger.error(f"Failed to load config definitions: {e}")
    
    def _parse_definitions(self, definitions: Dict[str, Any]):
        """Parse configuration definitions from YAML."""
        for key, config in definitions.items():
            self.config_definitions[key] = ConfigValue(
                key=key,
                value=config.get('default'),
                security_level=SecurityLevel(config.get('security_level', 'public')),
                required=config.get('required', False),
                description=config.get('description', ''),
                validation_func=self._get_validation_func(config.get('validation'))
            )
    
    def _get_validation_func(self, validation_type: Optional[str]) -> Optional[callable]:
        """Get validation function for a configuration value."""
        if not validation_type:
            return None
        
        validators = {
            'url': self._validate_url,
            'email': self._validate_email,
            'file_path': self._validate_file_path,
            'integer': self._validate_integer,
            'boolean': self._validate_boolean,
            'api_key': self._validate_api_key
        }
        
        return validators.get(validation_type)
    
    def get_required(self, key: str) -> Any:
        """
        Get a required configuration value.
        
        Raises ConfigurationError if the value is not found or invalid.
        This replaces insecure patterns like:
        os.environ.get("API_KEY", "default_key")
        """
        value = self.get(key)
        if value is None:
            raise ConfigurationError(f"Required configuration '{key}' not found")
        return value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with proper security handling.
        
        Args:
            key: Configuration key
            default: Default value (only used for non-sensitive values)
        
        Returns:
            Configuration value or None if not found
        """
        # Check cache first
        if key in self.config_cache:
            return self.config_cache[key]
        
        # Get configuration definition
        config_def = self.config_definitions.get(key)
        
        # Try to get value from various sources
        value = self._get_from_sources(key, config_def)
        
        # Apply default only for non-sensitive values
        if value is None and default is not None:
            if config_def and config_def.security_level in [SecurityLevel.SENSITIVE, SecurityLevel.SECRET]:
                logger.warning(f"Not applying default for sensitive config '{key}'")
            else:
                value = default
        
        # Validate the value
        if value is not None and config_def and config_def.validation_func:
            if not config_def.validation_func(value):
                raise ConfigurationError(f"Invalid value for configuration '{key}'")
        
        # Cache and return
        self.config_cache[key] = value
        return value
    
    def _get_from_sources(self, key: str, config_def: Optional[ConfigValue]) -> Any:
        """Get configuration value from various sources in priority order."""
        
        # 1. Environment variables (highest priority)
        env_value = os.getenv(key.upper())
        if env_value is not None:
            return self._parse_env_value(env_value)
        
        # 2. Secure credential manager (for sensitive values)
        if (config_def and 
            config_def.security_level in [SecurityLevel.SENSITIVE, SecurityLevel.SECRET] and
            self.credential_manager):
            cred_value = self.credential_manager.get_credential(key.lower())
            if cred_value is not None:
                return cred_value
        
        # 3. Configuration file
        file_value = self._get_from_config_file(key)
        if file_value is not None:
            return file_value
        
        # 4. Default from definition
        if config_def and config_def.value is not None:
            return config_def.value
        
        return None
    
    def _get_from_config_file(self, key: str) -> Any:
        """Get value from main configuration file."""
        config_file = Path(__file__).parent.parent.parent / "config.yaml"
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                return self._get_nested_value(config, key)
        except Exception as e:
            logger.error(f"Failed to read config file: {e}")
            return None
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """Get nested value from config dictionary."""
        # Support dot notation for nested keys
        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return value
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type."""
        # Handle boolean values
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        # Handle integer values
        try:
            return int(value)
        except ValueError:
            pass
        
        # Handle JSON values
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Return as string
        return value
    
    def validate_all(self) -> List[str]:
        """Validate all configuration values and return list of errors."""
        errors = []
        
        for key, config_def in self.config_definitions.items():
            try:
                value = self.get(key)
                
                # Check required values
                if config_def.required and value is None:
                    errors.append(f"Required configuration '{key}' is missing")
                
                # Validate non-None values
                if value is not None and config_def.validation_func:
                    if not config_def.validation_func(value):
                        errors.append(f"Invalid value for configuration '{key}'")
                        
            except Exception as e:
                errors.append(f"Error validating '{key}': {e}")
        
        return errors
    
    def get_secure_credential(self, credential_type: str) -> Optional[str]:
        """
        Get a secure credential (password, API key, etc.).
        
        This method ensures no insecure defaults are used.
        """
        if not self.credential_manager:
            logger.error("Secure credential manager not available")
            return None
        
        return self.credential_manager.get_credential(credential_type)
    
    def set_credential(self, credential_type: str, value: str) -> bool:
        """Store a credential securely."""
        if not self.credential_manager:
            logger.error("Secure credential manager not available")
            return False
        
        return self.credential_manager.store_credential(credential_type, value)
    
    def clear_cache(self):
        """Clear the configuration cache."""
        self.config_cache.clear()
    
    def get_section(self, section: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get a configuration section."""
        if default is None:
            default = {}
        
        # Try to get the section from the config file
        section_data = self._get_from_config_file(section)
        if section_data is not None and isinstance(section_data, dict):
            return section_data
        
        # Fall back to getting individual keys that start with the section name
        result = {}
        section_prefix = f"{section}."
        
        for key, config_def in self.config_definitions.items():
            if key.startswith(section_prefix):
                sub_key = key[len(section_prefix):]
                value = self.get(key)
                if value is not None:
                    result[sub_key] = value
        
        return result if result else default

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of configuration (excluding sensitive values)."""
        summary = {}
        
        for key, config_def in self.config_definitions.items():
            if config_def.security_level in [SecurityLevel.SENSITIVE, SecurityLevel.SECRET]:
                summary[key] = {
                    'value': '***HIDDEN***',
                    'security_level': config_def.security_level.value,
                    'required': config_def.required,
                    'description': config_def.description
                }
            else:
                summary[key] = {
                    'value': self.get(key),
                    'security_level': config_def.security_level.value,
                    'required': config_def.required,
                    'description': config_def.description
                }
        
        return summary
    
    # Validation functions
    def _validate_url(self, value: str) -> bool:
        """Validate URL format."""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(value))
    
    def _validate_email(self, value: str) -> bool:
        """Validate email format."""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(email_pattern.match(value))
    
    def _validate_file_path(self, value: str) -> bool:
        """Validate file path exists."""
        return Path(value).exists()
    
    def _validate_integer(self, value: Any) -> bool:
        """Validate integer value."""
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _validate_boolean(self, value: Any) -> bool:
        """Validate boolean value."""
        return isinstance(value, bool) or str(value).lower() in ['true', 'false']
    
    def _validate_api_key(self, value: str) -> bool:
        """Validate API key format."""
        return (isinstance(value, str) and 
                len(value) >= 10 and 
                value not in ['your_api_key', 'api_key', 'default_key'])

# Global configuration manager instance
_config_manager = None

def get_config_manager() -> SecureConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = SecureConfigManager()
    return _config_manager

# Convenience functions
def get_required_config(key: str) -> Any:
    """Get a required configuration value."""
    return get_config_manager().get_required(key)

def get_config(key: str, default: Any = None) -> Any:
    """Get a configuration value with optional default."""
    return get_config_manager().get(key, default)

def get_secure_credential(credential_type: str) -> Optional[str]:
    """Get a secure credential."""
    return get_config_manager().get_secure_credential(credential_type)

def validate_config() -> List[str]:
    """Validate all configuration and return errors."""
    return get_config_manager().validate_all()