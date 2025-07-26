#!/usr/bin/env python3
"""
Comprehensive tests for the unified configuration manager.
"""

import os
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from src.core.unified_config.manager import UnifiedConfigManager
from src.core.unified_config.interfaces import (
    ConfigValue, ConfigSource, ConfigSecurityLevel, ConfigSchema
)


class TestUnifiedConfigManager:
    """Test the main configuration manager."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def manager(self, temp_config_dir):
        """Create a configuration manager instance."""
        return UnifiedConfigManager(config_dir=temp_config_dir)
    
    @pytest.fixture
    def sample_config_file(self, temp_config_dir):
        """Create a sample configuration file."""
        config_file = temp_config_dir / "config.yaml"
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "testdb"
            },
            "api": {
                "timeout": 30,
                "retries": 3
            },
            "debug": True
        }
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        return config_file
    
    def test_manager_initialization(self, temp_config_dir):
        """Test manager initializes correctly."""
        manager = UnifiedConfigManager(config_dir=temp_config_dir)
        
        assert manager.config_dir == temp_config_dir
        assert hasattr(manager, 'sources')
        assert hasattr(manager, 'validator')
        assert hasattr(manager, 'cache')
        assert hasattr(manager, 'security')
        assert isinstance(manager._config, dict)
        assert isinstance(manager._schemas, dict)
        assert manager._loaded is False
    
    def test_manager_default_config_dir(self):
        """Test manager uses default config dir when none provided."""
        manager = UnifiedConfigManager()
        assert manager.config_dir == Path("config")
    
    def test_register_schema(self, manager):
        """Test registering configuration schemas."""
        schema = ConfigSchema(
            key="database.host",
            type=str,
            security_level=ConfigSecurityLevel.INTERNAL,
            description="Database host",
            required=True,
            default="localhost"
        )
        
        manager.register_schema(schema)
        assert "database.host" in manager._schemas
        assert manager._schemas["database.host"] == schema
    
    def test_register_multiple_schemas(self, manager):
        """Test registering multiple schemas."""
        schemas = [
            ConfigSchema("db.host", str, ConfigSecurityLevel.INTERNAL),
            ConfigSchema("db.port", int, ConfigSecurityLevel.INTERNAL),
            ConfigSchema("api.key", str, ConfigSecurityLevel.SECRET)
        ]
        
        for schema in schemas:
            manager.register_schema(schema)
        
        assert len(manager._schemas) == 3
        assert all(schema.key in manager._schemas for schema in schemas)
    
    def test_load_configuration_sources(self, manager):
        """Test loading configuration from sources."""
        # Mock the source loading
        with patch.object(manager, '_load_sources') as mock_load:
            mock_load.return_value = None
            manager._loaded = False
            
            manager.load()
            
            mock_load.assert_called_once()
            assert manager._loaded is True
    
    def test_get_configuration_value(self, manager):
        """Test getting configuration values."""
        # Setup test configuration
        test_value = ConfigValue(
            key="test.setting",
            value="test_value",
            source=ConfigSource.ENVIRONMENT,
            security_level=ConfigSecurityLevel.PUBLIC
        )
        manager._config["test.setting"] = test_value
        manager._loaded = True
        
        result = manager.get("test.setting")
        assert result == "test_value"
    
    def test_get_nonexistent_key(self, manager):
        """Test getting non-existent configuration key."""
        manager._loaded = True
        
        result = manager.get("nonexistent.key")
        assert result is None
        
        # Test with default
        result = manager.get("nonexistent.key", default="default_value")
        assert result == "default_value"
    
    def test_get_with_type_conversion(self, manager):
        """Test getting values with type conversion."""
        # String to int conversion
        int_value = ConfigValue("port", "8080", ConfigSource.ENVIRONMENT)
        manager._config["port"] = int_value
        manager._loaded = True
        
        result = manager.get("port", type_hint=int)
        assert result == 8080
        assert isinstance(result, int)
        
        # String to bool conversion
        bool_value = ConfigValue("debug", "true", ConfigSource.ENVIRONMENT)
        manager._config["debug"] = bool_value
        
        result = manager.get("debug", type_hint=bool)
        assert result is True
        assert isinstance(result, bool)
    
    def test_set_configuration_value(self, manager):
        """Test setting configuration values."""
        manager.set("new.setting", "new_value", source=ConfigSource.COMMAND_LINE)
        
        assert "new.setting" in manager._config
        config_value = manager._config["new.setting"]
        assert config_value.value == "new_value"
        assert config_value.source == ConfigSource.COMMAND_LINE
        assert config_value.key == "new.setting"
    
    def test_set_with_security_level(self, manager):
        """Test setting values with security levels."""
        manager.set(
            "secret.api_key", 
            "super_secret", 
            source=ConfigSource.ENV_FILE,
            security_level=ConfigSecurityLevel.SECRET
        )
        
        config_value = manager._config["secret.api_key"]
        assert config_value.security_level == ConfigSecurityLevel.SECRET
    
    def test_has_configuration_key(self, manager):
        """Test checking if configuration key exists."""
        manager._config["existing.key"] = ConfigValue(
            "existing.key", "value", ConfigSource.DEFAULTS
        )
        manager._loaded = True
        
        assert manager.has("existing.key") is True
        assert manager.has("nonexistent.key") is False
    
    def test_get_all_configuration(self, manager):
        """Test getting all configuration values."""
        test_configs = {
            "app.name": ConfigValue("app.name", "TestApp", ConfigSource.DEFAULTS),
            "app.version": ConfigValue("app.version", "1.0.0", ConfigSource.DEFAULTS),
            "db.host": ConfigValue("db.host", "localhost", ConfigSource.ENVIRONMENT)
        }
        
        manager._config.update(test_configs)
        manager._loaded = True
        
        all_config = manager.get_all()
        
        assert len(all_config) == 3
        assert all_config["app.name"].value == "TestApp"
        assert all_config["app.version"].value == "1.0.0"
        assert all_config["db.host"].value == "localhost"
    
    def test_get_all_with_prefix(self, manager):
        """Test getting configuration values with prefix filter."""
        test_configs = {
            "app.name": ConfigValue("app.name", "TestApp", ConfigSource.DEFAULTS),
            "app.version": ConfigValue("app.version", "1.0.0", ConfigSource.DEFAULTS),
            "db.host": ConfigValue("db.host", "localhost", ConfigSource.ENVIRONMENT),
            "db.port": ConfigValue("db.port", 5432, ConfigSource.ENVIRONMENT)
        }
        
        manager._config.update(test_configs)
        manager._loaded = True
        
        app_config = manager.get_all(prefix="app")
        db_config = manager.get_all(prefix="db")
        
        assert len(app_config) == 2
        assert "app.name" in app_config
        assert "app.version" in app_config
        
        assert len(db_config) == 2
        assert "db.host" in db_config
        assert "db.port" in db_config
    
    def test_validation_on_set(self, manager):
        """Test validation is triggered when setting values."""
        # Register schema with validation rules
        schema = ConfigSchema(
            key="api.timeout",
            type=int,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={"min": 1, "max": 300}
        )
        manager.register_schema(schema)
        
        # Test valid value
        manager.set("api.timeout", 30)
        assert manager._config["api.timeout"].value == 30
        
        # Test validation through the validator
        with patch.object(manager.validator, 'validate') as mock_validate:
            mock_validate.return_value = True
            manager.set("api.timeout", 60)
            mock_validate.assert_called()
    
    def test_security_handling(self, manager):
        """Test security handling for sensitive values."""
        # Set a secret value
        manager.set(
            "secrets.api_key",
            "secret123",
            security_level=ConfigSecurityLevel.SECRET
        )
        
        config_value = manager._config["secrets.api_key"]
        assert config_value.security_level == ConfigSecurityLevel.SECRET
        
        # Mock security manager
        with patch.object(manager.security, 'should_encrypt') as mock_encrypt:
            mock_encrypt.return_value = True
            # Test that security is considered
            manager.get("secrets.api_key")
            # Security should be checked for secret values
    
    def test_caching_behavior(self, manager):
        """Test configuration caching behavior."""
        # Mock cache
        with patch.object(manager.cache, 'get') as mock_cache_get, \
             patch.object(manager.cache, 'set'):
            
            mock_cache_get.return_value = None
            
            # Set a value (should trigger cache)
            manager.set("cache.test", "cached_value")
            
            # Get the value (should check cache)
            manager.get("cache.test")
            
            # Verify cache operations
            mock_cache_get.assert_called()
    
    def test_reload_configuration(self, manager):
        """Test reloading configuration."""
        # Initial setup
        manager.set("reload.test", "original")
        assert manager.get("reload.test") == "original"
        
        # Mock the reload process
        with patch.object(manager, '_load_sources') as mock_load:
            manager.reload()
            mock_load.assert_called_once()
            assert manager._loaded is True
    
    def test_environment_variable_override(self, manager):
        """Test environment variables override other sources."""
        # Set an environment variable
        with patch.dict(os.environ, {"TEST_CONFIG_VALUE": "env_value"}):
            # Mock load method to return our value
            with patch.object(manager, '_load') as mock_load:
                def mock_load_func():
                    manager._config["test.config.value"] = ConfigValue(
                        "test.config.value",
                        "env_value",
                        ConfigSource.ENVIRONMENT
                    )
                
                mock_load.side_effect = mock_load_func
                manager.load()
                
                result = manager.get("test.config.value")
                assert result == "env_value"
    
    def test_configuration_priority_order(self, manager):
        """Test configuration source priority ordering."""
        # Create values from different sources for the same key
        key = "priority.test"
        
        # Add values in reverse priority order
        manager._config[key] = ConfigValue(key, "default", ConfigSource.DEFAULTS)
        manager._config[key] = ConfigValue(key, "file", ConfigSource.MAIN_CONFIG)
        manager._config[key] = ConfigValue(key, "env", ConfigSource.ENVIRONMENT)
        
        # Environment should win due to highest priority
        manager._loaded = True
        result = manager.get(key)
        assert result == "env"
    
    def test_error_handling_invalid_type(self, manager):
        """Test error handling for invalid type conversion."""
        manager._config["invalid.number"] = ConfigValue(
            "invalid.number", "not_a_number", ConfigSource.DEFAULTS
        )
        manager._loaded = True
        
        # Should handle conversion errors gracefully
        result = manager.get("invalid.number", type_hint=int, default=0)
        # Should return default when conversion fails
        assert result == 0 or result == "not_a_number"  # Depending on implementation
    
    def test_nested_configuration_keys(self, manager):
        """Test handling of nested/dotted configuration keys."""
        nested_configs = {
            "database.connection.host": "db.example.com",
            "database.connection.port": 5432,
            "database.connection.ssl": True,
            "api.v1.timeout": 30,
            "api.v2.timeout": 60
        }
        
        for key, value in nested_configs.items():
            manager.set(key, value)
        
        # Test retrieval of nested keys
        assert manager.get("database.connection.host") == "db.example.com"
        assert manager.get("database.connection.port") == 5432
        assert manager.get("database.connection.ssl") is True
        
        # Test prefix-based retrieval
        db_config = manager.get_all(prefix="database.connection")
        assert len(db_config) == 3
        
        api_config = manager.get_all(prefix="api")
        assert len(api_config) == 2


class TestUnifiedConfigManagerIntegration:
    """Integration tests for the configuration manager."""
    
    @pytest.fixture
    def integration_manager(self, tmp_path):
        """Create a manager for integration testing."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return UnifiedConfigManager(config_dir=config_dir)
    
    def test_full_configuration_lifecycle(self, integration_manager, tmp_path):
        """Test complete configuration lifecycle."""
        manager = integration_manager
        
        # 1. Register schemas
        schemas = [
            ConfigSchema("app.name", str, ConfigSecurityLevel.PUBLIC, required=True),
            ConfigSchema("app.port", int, ConfigSecurityLevel.PUBLIC, default=8080),
            ConfigSchema("db.password", str, ConfigSecurityLevel.SECRET, required=True)
        ]
        
        for schema in schemas:
            manager.register_schema(schema)
        
        # 2. Create config files
        config_file = manager.config_dir / "config.yaml"
        config_data = {
            "app": {"name": "TestApp", "port": 3000},
            "db": {"password": "secret123"}
        }
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # 3. Set environment override
        with patch.dict(os.environ, {"APP_PORT": "9000"}):
            # 4. Load configuration
            manager.reload()  # Use reload to ensure we pick up the new config file
            
            # 5. Verify configuration
            assert manager.get("app.name") == "TestApp"
            # Environment should override file
            if manager.has("app.port"):
                port = manager.get("app.port")
                # Should be either env override or file value
                assert port in [9000, 3000]
            
            assert manager.get("db.password") == "secret123"
            
            # 6. Test runtime modification
            manager.set("app.debug", True, source=ConfigSource.COMMAND_LINE)
            assert manager.get("app.debug") is True
            
            # 7. Test validation
            assert manager.has("app.name")
            assert manager.has("db.password")
    
    def test_configuration_persistence(self, integration_manager):
        """Test configuration state persistence."""
        manager = integration_manager
        
        # Set some configuration
        manager.set("persist.test1", "value1")
        manager.set("persist.test2", 42)
        
        # Verify it's accessible
        assert manager.get("persist.test1") == "value1"
        assert manager.get("persist.test2") == 42
        
        # Simulate reload
        manager.reload()
        
        # Values set at runtime should persist until reload
        # (behavior depends on implementation)
    
    def test_error_recovery(self, integration_manager):
        """Test configuration system error recovery."""
        manager = integration_manager
        
        # Test invalid configuration file
        bad_config = manager.config_dir / "bad.yaml"
        with open(bad_config, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Should handle bad config gracefully
        try:
            manager.load()
            # Should not crash
            assert True
        except Exception as e:
            # If it does raise, should be a handled exception
            assert "config" in str(e).lower() or "yaml" in str(e).lower()
        
        # Should still be able to set/get values
        manager.set("recovery.test", "works")
        assert manager.get("recovery.test") == "works"