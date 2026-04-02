"""
Unified Configuration System

A comprehensive configuration management system that consolidates all configuration
sources and provides a single, coherent interface for configuration access.

Usage:
    from core.unified_config import get_config, set_config, get_config_manager
    
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
