#!/usr/bin/env python3
"""
Tests for Unified Configuration System

Comprehensive tests to ensure the unified configuration system works correctly.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.core.unified_config import (
    UnifiedConfigManager, get_config_manager, get_config, set_config,
    ConfigSecurityLevel, ConfigSource, ConfigValue, ConfigSchema,
    EnvironmentConfigSource, YAMLConfigSource, JSONConfigSource
)


class TestUnifiedConfigManager:
    """Test the unified configuration manager."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create config manager with temporary directory."""
        return UnifiedConfigManager(config_dir=temp_config_dir)
    
    def test_initialization(self, config_manager):
        """Test configuration manager initialization."""
        assert config_manager is not None
        assert len(config_manager.sources) > 0
        assert config_manager.validator is not None
        assert config_manager.cache is not None
        assert config_manager.security is not None
    
    def test_default_config_loading(self, config_manager):
        """Test loading of default configuration."""
        config_manager.load()
        
        # Should have default values
        assert config_manager.get('app_name') == 'Math PDF Manager'
        assert config_manager.get('version') == '2.0.0'
        assert config_manager.get('debug') is False
        assert config_manager.get('max_workers') == 4
    
    def test_environment_variable_override(self, config_manager):
        """Test environment variable override."""
        with patch.dict(os.environ, {'debug': 'true', 'max_workers': '8'}):
            config_manager.reload()
            
            # Environment variables should override defaults
            assert config_manager.get('debug') == 'true'  # String from env
            assert config_manager.get('max_workers') == '8'  # String from env
    
    def test_yaml_config_loading(self, temp_config_dir, config_manager):
        """Test loading from YAML configuration file."""
        # Create test YAML config
        config_content = """
app_name: "Test Application"
database_url: "sqlite:///test.db"
custom_setting: "test_value"
nested:
  setting1: "value1"
  setting2: 42
"""
        
        yaml_file = temp_config_dir / "config.yaml"
        with open(yaml_file, 'w') as f:
            f.write(config_content)
        
        # Reinitialize to pick up the new config file
        config_manager = UnifiedConfigManager(config_dir=temp_config_dir)
        config_manager.load()
        
        # Should load values from YAML
        assert config_manager.get('app_name') == 'Test Application'
        assert config_manager.get('database_url') == 'sqlite:///test.db'
        assert config_manager.get('custom_setting') == 'test_value'
        
        # Test nested values
        nested = config_manager.get('nested')
        assert nested['setting1'] == 'value1'
        assert nested['setting2'] == 42
    
    def test_json_config_loading(self, temp_config_dir):
        """Test loading from JSON configuration file."""
        # Create test JSON config
        config_content = {
            "app_name": "JSON Test App",
            "api_key": "test-api-key-123",
            "settings": {
                "timeout": 30,
                "retries": 3
            }
        }
        
        json_file = temp_config_dir / "settings.local.json"
        import json
        with open(json_file, 'w') as f:
            json.dump(config_content, f)
        
        # Initialize with temp config dir
        config_manager = UnifiedConfigManager(config_dir=temp_config_dir)
        config_manager.load()
        
        # Should load values from JSON
        assert config_manager.get('app_name') == 'JSON Test App'
        assert config_manager.get('api_key') == 'test-api-key-123'
        
        settings = config_manager.get('settings')
        assert settings['timeout'] == 30
        assert settings['retries'] == 3
    
    def test_priority_order(self, temp_config_dir):
        """Test configuration source priority order."""
        # Create YAML config (lower priority)
        yaml_content = """
test_value: "yaml_value"
shared_key: "from_yaml"
"""
        yaml_file = temp_config_dir / "config.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)
        
        # Create local config (higher priority)
        local_content = """
test_value: "local_value"
local_only: "local_setting"
"""
        local_file = temp_config_dir / "settings.local.yaml"
        with open(local_file, 'w') as f:
            f.write(local_content)
        
        # Test with environment override (highest priority)
        with patch.dict(os.environ, {'test_value': 'env_value'}):
            config_manager = UnifiedConfigManager(config_dir=temp_config_dir)
            config_manager.load()
            
            # Environment should have highest priority
            assert config_manager.get('test_value') == 'env_value'
            
            # Local config should override main config
            assert config_manager.get('shared_key') == 'from_yaml'
            
            # Local-only setting should be available
            assert config_manager.get('local_only') == 'local_setting'
    
    def test_command_line_args(self, config_manager):
        """Test command-line argument handling."""
        cli_args = {
            'debug': True,
            'output_file': '/tmp/output.txt',
            'verbose': 2
        }
        
        config_manager.add_command_line_args(cli_args)
        
        # CLI args should be available
        assert config_manager.get('debug') is True
        assert config_manager.get('output_file') == '/tmp/output.txt'
        assert config_manager.get('verbose') == 2
    
    def test_set_and_get(self, config_manager):
        """Test setting and getting configuration values."""
        # Set a new value
        config_manager.set('test_key', 'test_value')
        
        # Should be able to retrieve it
        assert config_manager.get('test_key') == 'test_value'
        
        # Test with default
        assert config_manager.get('nonexistent_key', 'default') == 'default'
    
    def test_get_all(self, config_manager):
        """Test getting all configuration values."""
        config_manager.load()
        
        all_config = config_manager.get_all()
        
        # Should be a dictionary of ConfigValue objects
        assert isinstance(all_config, dict)
        assert len(all_config) > 0
        
        # Each value should be a ConfigValue
        for key, value in all_config.items():
            assert isinstance(value, ConfigValue)
            assert value.key == key
            assert hasattr(value, 'source')
            assert hasattr(value, 'security_level')
    
    def test_source_info(self, config_manager):
        """Test getting source information."""
        config_manager.load()
        
        # Get source info for a default value
        info = config_manager.get_source_info('app_name')
        assert info is not None
        assert info.source == ConfigSource.DEFAULTS
        assert info.value == 'Math PDF Manager'
    
    def test_export_config(self, config_manager):
        """Test configuration export."""
        config_manager.load()
        
        # Export all configuration
        exported = config_manager.export_config()
        
        assert isinstance(exported, dict)
        assert 'app_name' in exported
        assert exported['app_name'] == 'Math PDF Manager'
        
        # Test excluding secrets
        config_manager.set('secret_key', 'super-secret', ConfigSource.DEFAULTS)
        config_manager._config['secret_key'].security_level = ConfigSecurityLevel.SECRET
        
        exported_no_secrets = config_manager.export_config(include_secrets=False)
        exported_with_secrets = config_manager.export_config(include_secrets=True)
        
        assert 'secret_key' not in exported_no_secrets
        assert 'secret_key' in exported_with_secrets


class TestConfigurationSources:
    """Test individual configuration sources."""
    
    def test_environment_config_source(self):
        """Test environment variable configuration source."""
        source = EnvironmentConfigSource()
        
        assert source.is_available() is True
        assert source.source_type == ConfigSource.ENVIRONMENT
        assert source.priority == 1  # Highest priority
        
        with patch.dict(os.environ, {'TEST_VAR': 'test_value', 'TEST_NUM': '42'}):
            config = source.load()
            
            assert 'TEST_VAR' in config
            assert config['TEST_VAR'] == 'test_value'
            assert 'TEST_NUM' in config
            assert config['TEST_NUM'] == '42'
    
    def test_environment_config_source_with_prefix(self):
        """Test environment source with prefix."""
        source = EnvironmentConfigSource(prefix="APP_")
        
        with patch.dict(os.environ, {'APP_DEBUG': 'true', 'OTHER_VAR': 'ignored'}):
            config = source.load()
            
            assert 'DEBUG' in config  # Prefix removed
            assert config['DEBUG'] == 'true'
            assert 'OTHER_VAR' not in config  # Doesn't match prefix
    
    def test_yaml_config_source(self, tmp_path):
        """Test YAML configuration source."""
        yaml_file = tmp_path / "test.yaml"
        yaml_content = """
app_name: "Test App"
settings:
  debug: true
  timeout: 30
"""
        yaml_file.write_text(yaml_content)
        
        source = YAMLConfigSource(yaml_file)
        
        assert source.is_available() is True
        assert source.source_type == ConfigSource.MAIN_CONFIG
        
        config = source.load()
        assert config['app_name'] == 'Test App'
        assert config['settings']['debug'] is True
        assert config['settings']['timeout'] == 30
    
    def test_json_config_source(self, tmp_path):
        """Test JSON configuration source."""
        json_file = tmp_path / "test.json"
        json_content = {
            "database_url": "postgresql://localhost/test",
            "cache": {
                "enabled": True,
                "ttl": 3600
            }
        }
        
        import json
        with open(json_file, 'w') as f:
            json.dump(json_content, f)
        
        source = JSONConfigSource(json_file)
        
        assert source.is_available() is True
        config = source.load()
        
        assert config['database_url'] == 'postgresql://localhost/test'
        assert config['cache']['enabled'] is True
        assert config['cache']['ttl'] == 3600


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns the same instance."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is manager2
    
    def test_global_get_config(self):
        """Test global get_config function."""
        # This should work with the default config
        app_name = get_config('app_name', 'fallback')
        
        # Should get the default value
        assert app_name in ['Math PDF Manager', 'fallback']
    
    def test_global_set_config(self):
        """Test global set_config function."""
        set_config('test_global', 'global_value')
        
        # Should be able to retrieve it
        assert get_config('test_global') == 'global_value'


class TestConfigurationValidation:
    """Test configuration validation."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create config manager with temporary directory."""
        return UnifiedConfigManager(config_dir=temp_config_dir)
    
    def test_schema_validation(self, config_manager):
        """Test configuration schema validation."""
        # Add a schema
        schema = ConfigSchema(
            key='test_port',
            type=int,
            security_level=ConfigSecurityLevel.PUBLIC,
            required=True,
            validation_rules={
                'min_value': 1024,
                'max_value': 65535
            }
        )
        
        config_manager.add_schema(schema)
        
        # Valid value should work
        config_manager.set('test_port', 8080)
        assert config_manager.get('test_port') == 8080
        
        # Invalid value should raise error
        with pytest.raises(ValueError):
            config_manager.set('test_port', 80)  # Below minimum
        
        with pytest.raises(ValueError):
            config_manager.set('test_port', 70000)  # Above maximum


if __name__ == "__main__":
    pytest.main([__file__, "-v"])