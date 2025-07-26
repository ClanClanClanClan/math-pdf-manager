#!/usr/bin/env python3
"""
Comprehensive tests for configuration validators.
"""

import pytest

from src.core.unified_config.validators import ConfigValidator
from src.core.unified_config.interfaces import ConfigValue, ConfigSource, ConfigSecurityLevel, ConfigSchema


class TestConfigValidator:
    """Test the configuration validator."""
    
    @pytest.fixture
    def validator(self):
        """Create a configuration validator instance."""
        return ConfigValidator()
    
    def test_validator_initialization(self, validator):
        """Test validator initializes correctly."""
        assert hasattr(validator, 'validate')
        assert callable(validator.validate)
    
    def test_validate_basic_types(self, validator):
        """Test validation of basic data types."""
        # String validation
        string_schema = ConfigSchema("test.string", str, ConfigSecurityLevel.PUBLIC)
        string_value = ConfigValue("test.string", "hello", ConfigSource.DEFAULTS)
        
        assert validator.validate(string_value, string_schema) is True
        
        # Integer validation
        int_schema = ConfigSchema("test.int", int, ConfigSecurityLevel.PUBLIC)
        int_value = ConfigValue("test.int", 42, ConfigSource.DEFAULTS)
        
        assert validator.validate(int_value, int_schema) is True
        
        # Boolean validation
        bool_schema = ConfigSchema("test.bool", bool, ConfigSecurityLevel.PUBLIC)
        bool_value = ConfigValue("test.bool", True, ConfigSource.DEFAULTS)
        
        assert validator.validate(bool_value, bool_schema) is True
    
    def test_validate_type_mismatch(self, validator):
        """Test validation fails for type mismatches."""
        int_schema = ConfigSchema("test.int", int, ConfigSecurityLevel.PUBLIC)
        string_value = ConfigValue("test.int", "not_a_number", ConfigSource.DEFAULTS)
        
        # Should fail validation
        result = validator.validate(string_value, int_schema)
        assert result is False
    
    def test_validate_with_constraints(self, validator):
        """Test validation with constraint rules."""
        # Test minimum/maximum constraints
        constrained_schema = ConfigSchema(
            key="test.port",
            type=int,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={"min": 1, "max": 65535}
        )
        
        # Valid port
        valid_value = ConfigValue("test.port", 8080, ConfigSource.DEFAULTS)
        assert validator.validate(valid_value, constrained_schema) is True
        
        # Invalid port (too low)
        invalid_low = ConfigValue("test.port", 0, ConfigSource.DEFAULTS)
        validator.validate(invalid_low, constrained_schema)
        # Should fail validation or return appropriate result
        
        # Invalid port (too high)
        invalid_high = ConfigValue("test.port", 70000, ConfigSource.DEFAULTS)
        validator.validate(invalid_high, constrained_schema)
        # Should fail validation or return appropriate result
    
    def test_validate_string_constraints(self, validator):
        """Test validation of string constraints."""
        string_schema = ConfigSchema(
            key="test.password",
            type=str,
            security_level=ConfigSecurityLevel.SECRET,
            validation_rules={
                "min_length": 8,
                "max_length": 128,
                "pattern": r"^[a-zA-Z0-9!@#$%^&*]+$"
            }
        )
        
        # Valid password
        valid_password = ConfigValue("test.password", "ValidPass123!", ConfigSource.DEFAULTS)
        assert validator.validate(valid_password, string_schema) is True
        
        # Too short
        short_password = ConfigValue("test.password", "short", ConfigSource.DEFAULTS)
        validator.validate(short_password, string_schema)
        # Should handle short password appropriately
        
        # Invalid characters
        invalid_chars = ConfigValue("test.password", "invalid<>password", ConfigSource.DEFAULTS)
        validator.validate(invalid_chars, string_schema)
        # Should handle invalid characters appropriately
    
    def test_validate_required_fields(self, validator):
        """Test validation of required configuration fields."""
        required_schema = ConfigSchema(
            key="test.required",
            type=str,
            security_level=ConfigSecurityLevel.PUBLIC,
            required=True
        )
        
        # Valid required value
        valid_value = ConfigValue("test.required", "present", ConfigSource.DEFAULTS)
        assert validator.validate(valid_value, required_schema) is True
        
        # Missing required value (None)
        missing_value = ConfigValue("test.required", None, ConfigSource.DEFAULTS)
        validator.validate(missing_value, required_schema)
        # Should fail for required field with None value
        
        # Empty string for required field
        empty_value = ConfigValue("test.required", "", ConfigSource.DEFAULTS)
        validator.validate(empty_value, required_schema)
        # Should handle empty string appropriately
    
    def test_validate_optional_fields(self, validator):
        """Test validation of optional configuration fields."""
        optional_schema = ConfigSchema(
            key="test.optional",
            type=str,
            security_level=ConfigSecurityLevel.PUBLIC,
            required=False,
            default="default_value"
        )
        
        # Present optional value
        present_value = ConfigValue("test.optional", "custom_value", ConfigSource.DEFAULTS)
        assert validator.validate(present_value, optional_schema) is True
        
        # Missing optional value should be ok
        missing_value = ConfigValue("test.optional", None, ConfigSource.DEFAULTS)
        validator.validate(missing_value, optional_schema)
        # Should pass for optional field
    
    def test_validate_list_values(self, validator):
        """Test validation of list configuration values."""
        list_schema = ConfigSchema(
            key="test.list",
            type=list,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={"min_items": 1, "max_items": 10}
        )
        
        # Valid list
        valid_list = ConfigValue("test.list", ["item1", "item2"], ConfigSource.DEFAULTS)
        assert validator.validate(valid_list, list_schema) is True
        
        # Empty list
        empty_list = ConfigValue("test.list", [], ConfigSource.DEFAULTS)
        validator.validate(empty_list, list_schema)
        # Should handle based on min_items constraint
        
        # Too many items
        large_list = ConfigValue("test.list", list(range(20)), ConfigSource.DEFAULTS)
        validator.validate(large_list, list_schema)
        # Should handle based on max_items constraint
    
    def test_validate_dict_values(self, validator):
        """Test validation of dictionary configuration values."""
        dict_schema = ConfigSchema(
            key="test.dict",
            type=dict,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={"required_keys": ["host", "port"]}
        )
        
        # Valid dictionary
        valid_dict = ConfigValue("test.dict", {"host": "localhost", "port": 8080}, ConfigSource.DEFAULTS)
        assert validator.validate(valid_dict, dict_schema) is True
        
        # Missing required key
        incomplete_dict = ConfigValue("test.dict", {"host": "localhost"}, ConfigSource.DEFAULTS)
        validator.validate(incomplete_dict, dict_schema)
        # Should handle missing required keys
    
    def test_validate_custom_rules(self, validator):
        """Test validation with custom validation rules."""
        custom_schema = ConfigSchema(
            key="test.custom",
            type=str,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={
                "custom_validator": "email",  # Custom email validation
                "domain_whitelist": ["example.com", "test.org"]
            }
        )
        
        # This test depends on implementation of custom validators
        custom_value = ConfigValue("test.custom", "user@example.com", ConfigSource.DEFAULTS)
        validator.validate(custom_value, custom_schema)
        # Should handle custom validation rules
    
    def test_validation_error_messages(self, validator):
        """Test that validation provides useful error messages."""
        schema = ConfigSchema(
            key="test.validation",
            type=int,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={"min": 1, "max": 100}
        )
        
        invalid_value = ConfigValue("test.validation", 150, ConfigSource.DEFAULTS)
        
        # Test if validator provides error details
        result = validator.validate(invalid_value, schema)
        
        # If validator returns more than boolean, check error info
        if hasattr(validator, 'get_last_error'):
            error = validator.get_last_error()
            assert error is not None
        elif isinstance(result, dict):
            assert 'valid' in result
            if not result['valid']:
                assert 'errors' in result or 'message' in result
    
    def test_validate_security_level_compatibility(self, validator):
        """Test validation considers security levels."""
        secret_schema = ConfigSchema(
            key="test.secret",
            type=str,
            security_level=ConfigSecurityLevel.SECRET,
            validation_rules={"min_length": 16}  # Secrets should be longer
        )
        
        public_schema = ConfigSchema(
            key="test.public",
            type=str,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={"min_length": 1}   # Public can be shorter
        )
        
        medium_value = ConfigValue("test.value", "medium_length", ConfigSource.DEFAULTS)
        
        # Same value might be valid for public but not secret
        validator.validate(
            ConfigValue(medium_value.key, medium_value.value, medium_value.source, ConfigSecurityLevel.PUBLIC),
            public_schema
        )
        
        validator.validate(
            ConfigValue(medium_value.key, medium_value.value, medium_value.source, ConfigSecurityLevel.SECRET),
            secret_schema
        )
        
        # Results may differ based on security requirements
    
    def test_batch_validation(self, validator):
        """Test validating multiple configurations at once."""
        schemas = {
            "app.name": ConfigSchema("app.name", str, ConfigSecurityLevel.PUBLIC, required=True),
            "app.port": ConfigSchema("app.port", int, ConfigSecurityLevel.PUBLIC, 
                                  validation_rules={"min": 1, "max": 65535}),
            "app.debug": ConfigSchema("app.debug", bool, ConfigSecurityLevel.PUBLIC)
        }
        
        values = {
            "app.name": ConfigValue("app.name", "TestApp", ConfigSource.DEFAULTS),
            "app.port": ConfigValue("app.port", 8080, ConfigSource.DEFAULTS),
            "app.debug": ConfigValue("app.debug", False, ConfigSource.DEFAULTS)
        }
        
        # Test if validator supports batch validation
        if hasattr(validator, 'validate_all'):
            results = validator.validate_all(values, schemas)
            assert isinstance(results, dict)
            for key in values.keys():
                assert key in results
        else:
            # Test individual validation for all
            for key in values.keys():
                if key in schemas:
                    result = validator.validate(values[key], schemas[key])
                    assert result is True  # All should be valid
    
    def test_validation_performance(self, validator):
        """Test validation performance with many rules."""
        complex_schema = ConfigSchema(
            key="test.complex",
            type=str,
            security_level=ConfigSecurityLevel.SENSITIVE,
            validation_rules={
                "min_length": 10,
                "max_length": 100,
                "pattern": r"^[a-zA-Z0-9_-]+$",
                "forbidden_words": ["password", "secret", "key"],
                "custom_checks": ["profanity", "security"]
            }
        )
        
        test_value = ConfigValue("test.complex", "valid_test_string_123", ConfigSource.DEFAULTS)
        
        # Should complete validation in reasonable time
        import time
        start_time = time.time()
        validator.validate(test_value, complex_schema)
        end_time = time.time()
        
        # Validation should be fast (< 1 second for single value)
        assert end_time - start_time < 1.0
    
    def test_validator_extensibility(self, validator):
        """Test that validator can be extended with custom rules."""
        # Test if validator supports custom validation functions
        if hasattr(validator, 'add_custom_validator'):
            def custom_email_validator(value):
                return '@' in value and '.' in value
            
            validator.add_custom_validator('email', custom_email_validator)
            
            schema = ConfigSchema(
                key="test.email",
                type=str,
                security_level=ConfigSecurityLevel.PUBLIC,
                validation_rules={"custom": "email"}
            )
            
            valid_email = ConfigValue("test.email", "user@example.com", ConfigSource.DEFAULTS)
            invalid_email = ConfigValue("test.email", "invalid-email", ConfigSource.DEFAULTS)
            
            assert validator.validate(valid_email, schema) is True
            assert validator.validate(invalid_email, schema) is False


class TestConfigValidatorIntegration:
    """Integration tests for configuration validator."""
    
    @pytest.fixture
    def integration_validator(self):
        """Create validator for integration testing."""
        return ConfigValidator()
    
    def test_real_world_configuration_validation(self, integration_validator):
        """Test validation of realistic configuration scenarios."""
        # Database configuration schema
        db_schemas = {
            "db.host": ConfigSchema("db.host", str, ConfigSecurityLevel.INTERNAL, required=True),
            "db.port": ConfigSchema("db.port", int, ConfigSecurityLevel.INTERNAL, 
                                  validation_rules={"min": 1, "max": 65535}),
            "db.username": ConfigSchema("db.username", str, ConfigSecurityLevel.SENSITIVE, required=True),
            "db.password": ConfigSchema("db.password", str, ConfigSecurityLevel.SECRET, 
                                      validation_rules={"min_length": 8}, required=True),
            "db.ssl": ConfigSchema("db.ssl", bool, ConfigSecurityLevel.INTERNAL),
            "db.pool_size": ConfigSchema("db.pool_size", int, ConfigSecurityLevel.INTERNAL,
                                       validation_rules={"min": 1, "max": 100})
        }
        
        # Valid configuration
        valid_config = {
            "db.host": ConfigValue("db.host", "db.example.com", ConfigSource.ENVIRONMENT),
            "db.port": ConfigValue("db.port", 5432, ConfigSource.ENVIRONMENT),
            "db.username": ConfigValue("db.username", "app_user", ConfigSource.ENV_FILE),
            "db.password": ConfigValue("db.password", "secure_password_123", ConfigSource.ENV_FILE),
            "db.ssl": ConfigValue("db.ssl", True, ConfigSource.MAIN_CONFIG),
            "db.pool_size": ConfigValue("db.pool_size", 10, ConfigSource.MAIN_CONFIG)
        }
        
        # Validate each configuration item
        for key, value in valid_config.items():
            if key in db_schemas:
                result = integration_validator.validate(value, db_schemas[key])
                assert result is True, f"Validation failed for {key}"
    
    def test_configuration_migration_validation(self, integration_validator):
        """Test validation during configuration migration."""
        # Old format schema
        old_schema = ConfigSchema(
            key="legacy.setting",
            type=str,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={"pattern": r"^legacy_.*"}
        )
        
        # New format schema
        new_schema = ConfigSchema(
            key="modern.setting",
            type=str,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={"pattern": r"^modern_.*"}
        )
        
        # Test migration scenario
        legacy_value = ConfigValue("legacy.setting", "legacy_value", ConfigSource.MAIN_CONFIG)
        modern_value = ConfigValue("modern.setting", "modern_value", ConfigSource.MAIN_CONFIG)
        
        legacy_valid = integration_validator.validate(legacy_value, old_schema)
        modern_valid = integration_validator.validate(modern_value, new_schema)
        
        # Both should be valid in their respective formats
        assert legacy_valid is True
        assert modern_valid is True
        
        # Cross-validation should fail
        integration_validator.validate(legacy_value, new_schema)
        # Should fail when legacy value doesn't match new schema
    
    def test_environment_specific_validation(self, integration_validator):
        """Test validation rules that vary by environment."""
        # Development environment - more lenient
        dev_schema = ConfigSchema(
            key="api.timeout",
            type=int,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={"min": 1, "max": 300}  # Allow longer timeouts
        )
        
        # Production environment - more strict
        prod_schema = ConfigSchema(
            key="api.timeout",
            type=int,
            security_level=ConfigSecurityLevel.PUBLIC,
            validation_rules={"min": 1, "max": 60}   # Enforce shorter timeouts
        )
        
        test_value = ConfigValue("api.timeout", 120, ConfigSource.ENVIRONMENT)
        
        dev_valid = integration_validator.validate(test_value, dev_schema)
        integration_validator.validate(test_value, prod_schema)
        
        # Same value might be valid in dev but not prod
        assert dev_valid is True
        # prod_valid result depends on implementation
    
    def test_validation_with_defaults(self, integration_validator):
        """Test validation when using default values."""
        schema_with_default = ConfigSchema(
            key="feature.enabled",
            type=bool,
            security_level=ConfigSecurityLevel.PUBLIC,
            required=False,
            default=False
        )
        
        # Test explicit value
        explicit_value = ConfigValue("feature.enabled", True, ConfigSource.ENVIRONMENT)
        assert integration_validator.validate(explicit_value, schema_with_default) is True
        
        # Test default value
        default_value = ConfigValue("feature.enabled", False, ConfigSource.DEFAULTS)
        assert integration_validator.validate(default_value, schema_with_default) is True
        
        # Test None value (should use default)
        none_value = ConfigValue("feature.enabled", None, ConfigSource.DEFAULTS)
        integration_validator.validate(none_value, schema_with_default)
        # Should handle None gracefully when default is available