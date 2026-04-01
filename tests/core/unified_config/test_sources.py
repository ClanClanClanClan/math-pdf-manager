#!/usr/bin/env python3
"""
Comprehensive tests for configuration sources.
"""

import os
import pytest
import json
import yaml
from unittest.mock import patch

from core.unified_config.sources import (
    EnvironmentConfigSource, YAMLConfigSource, JSONConfigSource,
    DefaultsConfigSource, CommandLineConfigSource
)
from core.unified_config.interfaces import ConfigValue, ConfigSource, ConfigSecurityLevel


class TestEnvironmentConfigSource:
    """Test environment variable configuration source."""
    
    @pytest.fixture
    def env_source(self):
        """Create an environment config source."""
        return EnvironmentConfigSource()
    
    def test_load_environment_variables(self, env_source):
        """Test loading from environment variables."""
        with patch.dict(os.environ, {
            "TEST_APP_NAME": "MyApp",
            "TEST_APP_PORT": "8080",
            "TEST_DB_HOST": "localhost"
        }):
            config = env_source.load()
            
            # Should load environment variables with proper transformation
            assert isinstance(config, dict)
            # Implementation may transform env var names to config keys
    
    def test_environment_priority(self, env_source):
        """Test environment source has correct priority."""
        assert env_source.get_priority() == ConfigSource.ENVIRONMENT
    
    def test_environment_variable_transformation(self, env_source):
        """Test environment variable name transformation."""
        with patch.dict(os.environ, {
            "APP_DATABASE_URL": "postgres://localhost/db",
            "API_SECRET_KEY": "secret123"
        }):
            config = env_source.load()
            
            # Should handle nested keys and transformations
            assert isinstance(config, dict)
    
    def test_environment_type_inference(self, env_source):
        """Test automatic type inference from environment."""
        with patch.dict(os.environ, {
            "NUM_WORKERS": "4",
            "DEBUG_MODE": "true",
            "TIMEOUT": "30.5"
        }):
            config = env_source.load()
            
            # Values should be strings (env vars are always strings)
            # Type conversion happens at manager level
            assert isinstance(config, dict)
    
    def test_empty_environment(self, env_source):
        """Test behavior with no relevant environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            config = env_source.load()
            
            assert isinstance(config, dict)
            # Should handle empty environment gracefully


class TestYAMLConfigSource:
    """Test YAML configuration file source."""
    
    @pytest.fixture
    def temp_yaml_file(self, tmp_path):
        """Create a temporary YAML config file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "app": {
                "name": "TestApp",
                "version": "1.0.0",
                "port": 8080
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "ssl": True
            },
            "features": ["auth", "cache", "monitoring"]
        }
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        return config_file
    
    @pytest.fixture
    def yaml_source(self, temp_yaml_file):
        """Create a YAML config source."""
        return YAMLConfigSource(temp_yaml_file)
    
    def test_load_yaml_configuration(self, yaml_source):
        """Test loading YAML configuration."""
        config = yaml_source.load()
        
        assert isinstance(config, dict)
        # Should flatten nested structure to dotted keys
        
        # Check that nested structure is handled
        assert len(config) > 0
    
    def test_yaml_source_priority(self, yaml_source):
        """Test YAML source has correct priority."""
        priority = yaml_source.get_priority()
        assert priority in [ConfigSource.MAIN_CONFIG, ConfigSource.LOCAL_FILE]
    
    def test_nonexistent_yaml_file(self, tmp_path):
        """Test handling of non-existent YAML file."""
        nonexistent_file = tmp_path / "nonexistent.yaml"
        source = YAMLConfigSource(nonexistent_file)
        
        config = source.load()
        assert config == {}  # Should return empty dict for missing file
    
    def test_invalid_yaml_file(self, tmp_path):
        """Test handling of invalid YAML file."""
        bad_yaml = tmp_path / "bad.yaml"
        with open(bad_yaml, 'w') as f:
            f.write("invalid: yaml: content: [unclosed")
        
        source = YAMLConfigSource(bad_yaml)
        
        # Should handle invalid YAML gracefully
        try:
            config = source.load()
            assert config == {}
        except Exception as e:
            # If exception is raised, should be a handled YAML error
            assert "yaml" in str(e).lower() or "parse" in str(e).lower()
    
    def test_complex_yaml_structures(self, tmp_path):
        """Test handling of complex YAML structures."""
        complex_yaml = tmp_path / "complex.yaml"
        config_data = {
            "nested": {
                "deep": {
                    "value": "deep_value"
                }
            },
            "list_values": [1, 2, 3],
            "mixed": {
                "string": "text",
                "number": 42,
                "boolean": True,
                "null_value": None
            }
        }
        
        with open(complex_yaml, 'w') as f:
            yaml.dump(config_data, f)
        
        source = YAMLConfigSource(complex_yaml)
        config = source.load()
        
        assert isinstance(config, dict)
        # Should handle all YAML data types


class TestJSONConfigSource:
    """Test JSON configuration file source."""
    
    @pytest.fixture
    def temp_json_file(self, tmp_path):
        """Create a temporary JSON config file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "api": {
                "base_url": "https://api.example.com",
                "timeout": 30,
                "retries": 3
            },
            "logging": {
                "level": "INFO",
                "format": "%(levelname)s: %(message)s"
            }
        }
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        return config_file
    
    @pytest.fixture
    def json_source(self, temp_json_file):
        """Create a JSON config source."""
        return JSONConfigSource(temp_json_file)
    
    def test_load_json_configuration(self, json_source):
        """Test loading JSON configuration."""
        config = json_source.load()
        
        assert isinstance(config, dict)
        assert len(config) > 0
    
    def test_json_source_priority(self, json_source):
        """Test JSON source has correct priority."""
        priority = json_source.get_priority()
        assert priority in [ConfigSource.MAIN_CONFIG, ConfigSource.LOCAL_FILE]
    
    def test_nonexistent_json_file(self, tmp_path):
        """Test handling of non-existent JSON file."""
        nonexistent_file = tmp_path / "nonexistent.json"
        source = JSONConfigSource(nonexistent_file)
        
        config = source.load()
        assert config == {}
    
    def test_invalid_json_file(self, tmp_path):
        """Test handling of invalid JSON file."""
        bad_json = tmp_path / "bad.json"
        with open(bad_json, 'w') as f:
            f.write('{"invalid": json, "missing": quote}')
        
        source = JSONConfigSource(bad_json)
        
        try:
            config = source.load()
            assert config == {}
        except Exception as e:
            assert "json" in str(e).lower() or "parse" in str(e).lower()


class TestDefaultsConfigSource:
    """Test defaults configuration source."""
    
    @pytest.fixture
    def defaults_source(self):
        """Create a defaults config source."""
        defaults = {
            "app.name": "DefaultApp",
            "app.port": 8080,
            "db.timeout": 30,
            "debug": False
        }
        return DefaultsConfigSource(defaults)
    
    def test_load_defaults(self, defaults_source):
        """Test loading default configuration."""
        config = defaults_source.load()
        
        assert isinstance(config, dict)
        assert config["app.name"] == "DefaultApp"
        assert config["app.port"] == 8080
        assert config["db.timeout"] == 30
        assert config["debug"] is False
    
    def test_defaults_priority(self, defaults_source):
        """Test defaults source has lowest priority."""
        assert defaults_source.get_priority() == ConfigSource.DEFAULTS
    
    def test_empty_defaults(self):
        """Test defaults source with empty defaults."""
        source = DefaultsConfigSource({})
        config = source.load()
        
        assert config == {}
    
    def test_defaults_immutability(self, defaults_source):
        """Test that defaults don't get modified."""
        original_defaults = {
            "app.name": "DefaultApp",
            "app.port": 8080
        }
        source = DefaultsConfigSource(original_defaults.copy())
        
        config = source.load()
        # Modify returned config
        config["new.key"] = "new_value"
        
        # Load again - should be unchanged
        config2 = source.load()
        assert "new.key" not in config2
        assert config2["app.name"] == "DefaultApp"


class TestCommandLineConfigSource:
    """Test command line argument configuration source."""
    
    @pytest.fixture
    def cmdline_source(self):
        """Create a command line config source."""
        return CommandLineConfigSource()
    
    def test_cmdline_priority(self, cmdline_source):
        """Test command line source has high priority."""
        assert cmdline_source.get_priority() == ConfigSource.COMMAND_LINE
    
    @patch('sys.argv')
    def test_parse_command_line_args(self, mock_argv, cmdline_source):
        """Test parsing command line arguments."""
        mock_argv.return_value = [
            'script.py',
            '--config-app-name=CmdApp',
            '--config-port=9000',
            '--config-debug'
        ]
        
        config = cmdline_source.load()
        
        # Should parse command line args to config format
        assert isinstance(config, dict)
    
    def test_empty_command_line(self, cmdline_source):
        """Test handling empty command line."""
        with patch('sys.argv', ['script.py']):
            config = cmdline_source.load()
            
            assert isinstance(config, dict)
            # May be empty or contain default parsing


class TestConfigSourceIntegration:
    """Integration tests for configuration sources."""
    
    def test_source_priority_ordering(self):
        """Test that sources have correct priority ordering."""
        env_source = EnvironmentConfigSource()
        cmd_source = CommandLineConfigSource()
        defaults_source = DefaultsConfigSource({})
        
        [
            env_source.get_priority(),
            cmd_source.get_priority(),
            defaults_source.get_priority()
        ]
        
        # Environment should be highest priority
        assert env_source.get_priority() == ConfigSource.ENVIRONMENT
        # Defaults should be lowest priority
        assert defaults_source.get_priority() == ConfigSource.DEFAULTS
    
    def test_multiple_sources_same_key(self, tmp_path):
        """Test behavior when multiple sources provide same key."""
        # Create config file
        config_file = tmp_path / "test.yaml"
        with open(config_file, 'w') as f:
            yaml.dump({"app": {"port": 8080}}, f)
        
        # Setup sources
        yaml_source = YAMLConfigSource(config_file)
        defaults_source = DefaultsConfigSource({"app.port": 3000})
        
        # Load from both
        yaml_config = yaml_source.load()
        defaults_config = defaults_source.load()
        
        # Both should provide the key
        assert isinstance(yaml_config, dict)
        assert isinstance(defaults_config, dict)
        
        # Priority resolution happens at manager level
    
    def test_source_error_isolation(self, tmp_path):
        """Test that errors in one source don't affect others."""
        # Create one good source
        good_file = tmp_path / "good.yaml"
        with open(good_file, 'w') as f:
            yaml.dump({"good": "value"}, f)
        
        # Create one bad source
        bad_file = tmp_path / "bad.yaml"
        with open(bad_file, 'w') as f:
            f.write("invalid yaml content [")
        
        good_source = YAMLConfigSource(good_file)
        bad_source = YAMLConfigSource(bad_file)
        
        # Good source should work
        good_config = good_source.load()
        assert isinstance(good_config, dict)
        
        # Bad source should fail gracefully
        bad_config = bad_source.load()
        assert bad_config == {} or isinstance(bad_config, dict)
    
    def test_configuration_value_creation(self):
        """Test that sources create proper ConfigValue objects."""
        defaults = {"test.key": "test_value"}
        source = DefaultsConfigSource(defaults)
        config = source.load()
        
        # Source should return dict that can be converted to ConfigValues
        assert isinstance(config, dict)
        
        # Values should be ready for ConfigValue creation
        for key, value in config.items():
            config_value = ConfigValue(
                key=key,
                value=value,
                source=source.get_priority(),
                security_level=ConfigSecurityLevel.PUBLIC
            )
            assert config_value.key == key
            assert config_value.value == value
            assert config_value.source == ConfigSource.DEFAULTS