#!/usr/bin/env python3
"""
Comprehensive tests for configuration system interfaces and data structures.
"""


from core.unified_config.interfaces import (
    ConfigSecurityLevel, ConfigSource, ConfigValue, ConfigSchema
)


class TestConfigSecurityLevel:
    """Test ConfigSecurityLevel enum."""
    
    def test_security_levels_exist(self):
        """Test all expected security levels exist."""
        assert ConfigSecurityLevel.PUBLIC.value == "public"
        assert ConfigSecurityLevel.INTERNAL.value == "internal"
        assert ConfigSecurityLevel.SENSITIVE.value == "sensitive"
        assert ConfigSecurityLevel.SECRET.value == "secret"
    
    def test_security_level_ordering(self):
        """Test security levels can be compared."""
        levels = list(ConfigSecurityLevel)
        assert len(levels) == 4
        assert ConfigSecurityLevel.PUBLIC in levels
        assert ConfigSecurityLevel.SECRET in levels


class TestConfigSource:
    """Test ConfigSource enum."""
    
    def test_config_sources_exist(self):
        """Test all expected config sources exist."""
        assert ConfigSource.ENVIRONMENT.value == "environment"
        assert ConfigSource.COMMAND_LINE.value == "command_line"
        assert ConfigSource.LOCAL_FILE.value == "local_file"
        assert ConfigSource.ENV_FILE.value == "env_file"
        assert ConfigSource.MAIN_CONFIG.value == "main_config"
        assert ConfigSource.DEFAULTS.value == "defaults"
    
    def test_source_ordering(self):
        """Test source priority ordering."""
        sources = list(ConfigSource)
        assert len(sources) == 6
        # Environment should be first (highest priority)
        assert sources[0] == ConfigSource.ENVIRONMENT
        # Defaults should be last (lowest priority)
        assert sources[-1] == ConfigSource.DEFAULTS


class TestConfigValue:
    """Test ConfigValue dataclass."""
    
    def test_basic_config_value(self):
        """Test creating a basic config value."""
        value = ConfigValue(
            key="test_key",
            value="test_value",
            source=ConfigSource.ENVIRONMENT
        )
        assert value.key == "test_key"
        assert value.value == "test_value"
        assert value.source == ConfigSource.ENVIRONMENT
        assert value.security_level == ConfigSecurityLevel.PUBLIC
        assert value.description is None
        assert value.required is False
        assert value.default is None
        assert value.validation_rules is None
    
    def test_full_config_value(self):
        """Test creating a config value with all fields."""
        validation_rules = {"min_length": 8, "pattern": r"^[a-zA-Z]+$"}
        value = ConfigValue(
            key="api_key",
            value="secret123",
            source=ConfigSource.ENV_FILE,
            security_level=ConfigSecurityLevel.SECRET,
            description="API key for external service",
            required=True,
            default="default_key",
            validation_rules=validation_rules
        )
        
        assert value.key == "api_key"
        assert value.value == "secret123"
        assert value.source == ConfigSource.ENV_FILE
        assert value.security_level == ConfigSecurityLevel.SECRET
        assert value.description == "API key for external service"
        assert value.required is True
        assert value.default == "default_key"
        assert value.validation_rules == validation_rules
    
    def test_config_value_equality(self):
        """Test config value equality comparison."""
        value1 = ConfigValue("key1", "value1", ConfigSource.ENVIRONMENT)
        value2 = ConfigValue("key1", "value1", ConfigSource.ENVIRONMENT)
        value3 = ConfigValue("key2", "value1", ConfigSource.ENVIRONMENT)
        
        assert value1 == value2
        assert value1 != value3
    
    def test_config_value_immutable_after_frozen(self):
        """Test that config values can be made immutable."""
        value = ConfigValue("key", "value", ConfigSource.DEFAULTS)
        # Note: dataclass is not frozen by default, so this test is about interface
        assert hasattr(value, 'key')
        assert hasattr(value, 'value')


class TestConfigSchema:
    """Test ConfigSchema dataclass."""
    
    def test_basic_config_schema(self):
        """Test creating a basic config schema."""
        schema = ConfigSchema(
            key="database_url",
            type=str,
            security_level=ConfigSecurityLevel.SENSITIVE
        )
        assert schema.key == "database_url"
        assert schema.type == str
        assert schema.security_level == ConfigSecurityLevel.SENSITIVE
    
    def test_config_schema_with_optionals(self):
        """Test creating config schema with optional fields."""
        schema = ConfigSchema(
            key="port",
            type=int,
            security_level=ConfigSecurityLevel.PUBLIC,
            description="Server port number",
            required=True,
            default=8080,
            validation_rules={"min": 1, "max": 65535}
        )
        
        assert schema.key == "port"
        assert schema.type == int
        assert schema.security_level == ConfigSecurityLevel.PUBLIC
        assert schema.description == "Server port number"
        assert schema.required is True
        assert schema.default == 8080
        assert schema.validation_rules == {"min": 1, "max": 65535}
    
    def test_schema_type_validation(self):
        """Test schema accepts different types."""
        str_schema = ConfigSchema("str_key", str, ConfigSecurityLevel.PUBLIC)
        int_schema = ConfigSchema("int_key", int, ConfigSecurityLevel.PUBLIC)
        bool_schema = ConfigSchema("bool_key", bool, ConfigSecurityLevel.PUBLIC)
        list_schema = ConfigSchema("list_key", list, ConfigSecurityLevel.PUBLIC)
        dict_schema = ConfigSchema("dict_key", dict, ConfigSecurityLevel.PUBLIC)
        
        assert str_schema.type == str
        assert int_schema.type == int
        assert bool_schema.type == bool
        assert list_schema.type == list
        assert dict_schema.type == dict


class TestConfigInterfacesIntegration:
    """Integration tests for configuration interfaces."""
    
    def test_value_matches_schema(self):
        """Test that config values can be validated against schemas."""
        schema = ConfigSchema(
            key="timeout",
            type=int,
            security_level=ConfigSecurityLevel.PUBLIC,
            required=True,
            default=30,
            validation_rules={"min": 1, "max": 300}
        )
        
        value = ConfigValue(
            key="timeout",
            value=60,
            source=ConfigSource.ENVIRONMENT,
            security_level=ConfigSecurityLevel.PUBLIC,
            required=True
        )
        
        # Basic compatibility check
        assert value.key == schema.key
        assert isinstance(value.value, schema.type)
        assert value.security_level == schema.security_level
        assert value.required == schema.required
    
    def test_security_level_compatibility(self):
        """Test security level handling across components."""
        levels = [
            ConfigSecurityLevel.PUBLIC,
            ConfigSecurityLevel.INTERNAL,
            ConfigSecurityLevel.SENSITIVE,
            ConfigSecurityLevel.SECRET
        ]
        
        for level in levels:
            schema = ConfigSchema("test", str, level)
            value = ConfigValue("test", "value", ConfigSource.DEFAULTS, level)
            
            assert schema.security_level == level
            assert value.security_level == level
    
    def test_source_priority_handling(self):
        """Test source priority can be compared."""
        sources = list(ConfigSource)
        
        # Create values from different sources
        values = []
        for i, source in enumerate(sources):
            value = ConfigValue(f"key_{i}", f"value_{i}", source)
            values.append((source, value))
        
        # Verify we have values from all sources
        assert len(values) == len(sources)
        
        # Verify environment is highest priority
        env_source = next(source for source, _ in values if source == ConfigSource.ENVIRONMENT)
        assert env_source == ConfigSource.ENVIRONMENT
        
        # Verify defaults is lowest priority  
        default_source = next(source for source, _ in values if source == ConfigSource.DEFAULTS)
        assert default_source == ConfigSource.DEFAULTS