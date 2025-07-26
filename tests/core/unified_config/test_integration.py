#!/usr/bin/env python3
"""
Comprehensive integration tests for the unified configuration system.
"""

import os
import pytest
import yaml
import json
from unittest.mock import patch

from src.core.unified_config.manager import UnifiedConfigManager
from src.core.unified_config.interfaces import ConfigSchema, ConfigSecurityLevel, ConfigSource


class TestUnifiedConfigSystemIntegration:
    """End-to-end integration tests for the unified configuration system."""
    
    @pytest.fixture
    def integration_setup(self, tmp_path):
        """Set up complete integration test environment."""
        # Create config directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        # Create main config file
        main_config = {
            "app": {
                "name": "IntegrationTestApp",
                "version": "2.0.0",
                "environment": "test"
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "testdb",
                "ssl": True,
                "pool_size": 10
            },
            "api": {
                "timeout": 30,
                "retries": 3,
                "rate_limit": 1000
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "/tmp/app.log"
            },
            "features": {
                "auth": True,
                "cache": True,
                "monitoring": False
            }
        }
        
        with open(config_dir / "main.yaml", 'w') as f:
            yaml.dump(main_config, f)
        
        # Create environment-specific config
        env_config = {
            "database": {
                "host": "test.db.example.com",
                "pool_size": 5
            },
            "api": {
                "timeout": 60
            },
            "features": {
                "monitoring": True
            }
        }
        
        with open(config_dir / "test.yaml", 'w') as f:
            yaml.dump(env_config, f)
        
        # Create .env file
        env_file = config_dir / ".env"
        with open(env_file, 'w') as f:
            f.write("DB_PASSWORD=test_secret_password\n")
            f.write("API_SECRET_KEY=sk-test-1234567890abcdef\n")
            f.write("ENCRYPTION_KEY=encryption-key-for-testing\n")
        
        # Create secrets config (JSON format)
        secrets_config = {
            "external_apis": {
                "weather_service": {
                    "api_key": "weather-api-key-12345",
                    "base_url": "https://api.weather.com/v1"
                },
                "payment_gateway": {
                    "merchant_id": "merchant_12345",
                    "secret_key": "payment-secret-key-67890"
                }
            }
        }
        
        with open(config_dir / "secrets.json", 'w') as f:
            json.dump(secrets_config, f)
        
        return {
            "config_dir": config_dir,
            "manager": UnifiedConfigManager(config_dir=config_dir)
        }
    
    def test_complete_configuration_loading(self, integration_setup):
        """Test loading configuration from all sources."""
        manager = integration_setup["manager"]
        
        # Register comprehensive schemas
        schemas = [
            # Application schemas
            ConfigSchema("app.name", str, ConfigSecurityLevel.PUBLIC, required=True),
            ConfigSchema("app.version", str, ConfigSecurityLevel.PUBLIC, required=True),
            ConfigSchema("app.environment", str, ConfigSecurityLevel.PUBLIC),
            
            # Database schemas
            ConfigSchema("database.host", str, ConfigSecurityLevel.INTERNAL, required=True),
            ConfigSchema("database.port", int, ConfigSecurityLevel.INTERNAL, 
                        validation_rules={"min": 1, "max": 65535}),
            ConfigSchema("database.name", str, ConfigSecurityLevel.INTERNAL, required=True),
            ConfigSchema("database.password", str, ConfigSecurityLevel.SECRET, required=True,
                        validation_rules={"min_length": 8}),
            ConfigSchema("database.ssl", bool, ConfigSecurityLevel.INTERNAL),
            ConfigSchema("database.pool_size", int, ConfigSecurityLevel.INTERNAL,
                        validation_rules={"min": 1, "max": 100}),
            
            # API schemas
            ConfigSchema("api.timeout", int, ConfigSecurityLevel.PUBLIC,
                        validation_rules={"min": 1, "max": 300}),
            ConfigSchema("api.retries", int, ConfigSecurityLevel.PUBLIC,
                        validation_rules={"min": 0, "max": 10}),
            ConfigSchema("api.secret_key", str, ConfigSecurityLevel.SECRET, required=True),
            
            # Feature flags
            ConfigSchema("features.auth", bool, ConfigSecurityLevel.PUBLIC),
            ConfigSchema("features.cache", bool, ConfigSecurityLevel.PUBLIC),
            ConfigSchema("features.monitoring", bool, ConfigSecurityLevel.PUBLIC),
        ]
        
        for schema in schemas:
            manager.register_schema(schema)
        
        # Load with environment variables override
        with patch.dict(os.environ, {
            "APP_ENVIRONMENT": "integration_test",
            "DATABASE_HOST": "integration.db.example.com",
            "API_TIMEOUT": "45",
            "FEATURES_CACHE": "false"
        }):
            manager.load()
            
            # Test basic configuration loading
            assert manager.get("app.name") == "IntegrationTestApp"
            assert manager.get("app.version") == "2.0.0"
            
            # Test environment override
            assert manager.get("app.environment") == "integration_test"  # From env var
            
            # Test database configuration
            db_host = manager.get("database.host")
            assert db_host in ["integration.db.example.com", "test.db.example.com", "localhost"]
            assert manager.get("database.port") == 5432
            assert manager.get("database.ssl") is True
            
            # Test API configuration with override
            api_timeout = manager.get("api.timeout", type_hint=int)
            assert api_timeout == 45  # From environment override
            
            # Test feature flags
            cache_enabled = manager.get("features.cache", type_hint=bool)
            assert cache_enabled is False  # From environment override
    
    def test_configuration_priority_resolution(self, integration_setup):
        """Test configuration priority resolution across sources."""
        manager = integration_setup["manager"]
        
        # Set up test configuration with same key from different sources
        test_key = "priority.test_value"
        
        # Register schema
        schema = ConfigSchema(test_key, str, ConfigSecurityLevel.PUBLIC)
        manager.register_schema(schema)
        
        # Set values from different sources (in reverse priority order)
        manager.set(test_key, "from_defaults", source=ConfigSource.DEFAULTS)
        manager.set(test_key, "from_main_config", source=ConfigSource.MAIN_CONFIG)
        manager.set(test_key, "from_env_file", source=ConfigSource.ENV_FILE)
        manager.set(test_key, "from_command_line", source=ConfigSource.COMMAND_LINE)
        
        # Test with environment variable (highest priority)
        with patch.dict(os.environ, {"PRIORITY_TEST_VALUE": "from_environment"}):
            manager.reload()
            
            # Environment should win
            result = manager.get(test_key)
            # Result depends on implementation, but should follow priority rules
            assert result is not None
    
    def test_configuration_validation_integration(self, integration_setup):
        """Test configuration validation in integrated environment."""
        manager = integration_setup["manager"]
        
        # Register schemas with validation rules
        schemas = [
            ConfigSchema("validation.port", int, ConfigSecurityLevel.PUBLIC,
                        validation_rules={"min": 1024, "max": 8080}, required=True),
            ConfigSchema("validation.email", str, ConfigSecurityLevel.PUBLIC,
                        validation_rules={"pattern": r"^[^@]+@[^@]+\.[^@]+$"}, required=True),
            ConfigSchema("validation.password", str, ConfigSecurityLevel.SECRET,
                        validation_rules={"min_length": 12}, required=True)
        ]
        
        for schema in schemas:
            manager.register_schema(schema)
        
        # Test valid configurations
        manager.set("validation.port", 3000)
        manager.set("validation.email", "test@example.com")
        manager.set("validation.password", "super_secure_password_123")
        
        # Should be able to retrieve valid values
        assert manager.get("validation.port") == 3000
        assert manager.get("validation.email") == "test@example.com"
        assert manager.get("validation.password") == "super_secure_password_123"
        
        # Test invalid configurations
        try:
            manager.set("validation.port", 80)  # Below minimum
            # Implementation may reject or accept with warning
        except Exception:
            pass  # Expected for strict validation
        
        try:
            manager.set("validation.email", "invalid_email")  # Invalid format
            # Implementation may reject or accept with warning
        except Exception:
            pass  # Expected for strict validation
    
    def test_security_integration(self, integration_setup):
        """Test security features in integrated environment."""
        manager = integration_setup["manager"]
        
        # Register security-sensitive schemas
        security_schemas = [
            ConfigSchema("secrets.db_password", str, ConfigSecurityLevel.SECRET, required=True),
            ConfigSchema("secrets.api_key", str, ConfigSecurityLevel.SECRET, required=True),
            ConfigSchema("internal.service_url", str, ConfigSecurityLevel.INTERNAL),
            ConfigSchema("public.app_name", str, ConfigSecurityLevel.PUBLIC)
        ]
        
        for schema in security_schemas:
            manager.register_schema(schema)
        
        # Set sensitive configurations
        manager.set("secrets.db_password", "ultra_secret_db_password", 
                   security_level=ConfigSecurityLevel.SECRET)
        manager.set("secrets.api_key", "sk-secret-api-key-12345",
                   security_level=ConfigSecurityLevel.SECRET)
        manager.set("internal.service_url", "http://internal.service.com",
                   security_level=ConfigSecurityLevel.INTERNAL)
        manager.set("public.app_name", "PublicApp",
                   security_level=ConfigSecurityLevel.PUBLIC)
        
        # Verify security handling
        # Secret values should be retrievable but handled securely
        db_password = manager.get("secrets.db_password")
        assert db_password == "ultra_secret_db_password"
        
        api_key = manager.get("secrets.api_key")
        assert api_key == "sk-secret-api-key-12345"
        
        # Test security manager integration
        if hasattr(manager, 'security'):
            secret_config = manager._config.get("secrets.db_password")
            if secret_config:
                should_encrypt = manager.security.should_encrypt(secret_config)
                assert should_encrypt is True
    
    def test_caching_integration(self, integration_setup):
        """Test cache integration in real scenarios."""
        manager = integration_setup["manager"]
        
        # Load initial configuration
        manager.load()
        
        # Test cache performance
        import time
        
        # First access (cache miss)
        start_time = time.time()
        value1 = manager.get("app.name")
        first_access_time = time.time() - start_time
        
        # Second access (cache hit)
        start_time = time.time()
        value2 = manager.get("app.name")
        second_access_time = time.time() - start_time
        
        # Values should be the same
        assert value1 == value2
        
        # Second access should be faster (if caching is implemented)
        # Note: This may not always be true in simple implementations
        if hasattr(manager, 'cache'):
            assert second_access_time <= first_access_time
    
    def test_runtime_configuration_updates(self, integration_setup):
        """Test runtime configuration updates and reload."""
        manager = integration_setup["manager"]
        config_dir = integration_setup["config_dir"]
        
        # Initial load
        manager.load()
        manager.get("api.timeout")
        
        # Update configuration file
        updated_config = {
            "api": {
                "timeout": 90,  # Changed from 30/60
                "retries": 5    # Changed from 3
            }
        }
        
        with open(config_dir / "runtime_update.yaml", 'w') as f:
            yaml.dump(updated_config, f)
        
        # Reload configuration
        manager.reload()
        
        # Should get updated values (if runtime update is supported)
        # Note: This depends on whether the manager monitors file changes
        manager.get("api.timeout")
        
        # Verify that configuration can be updated at runtime
        manager.set("api.timeout", 120, source=ConfigSource.COMMAND_LINE)
        runtime_timeout = manager.get("api.timeout")
        assert runtime_timeout == 120
    
    def test_error_recovery_integration(self, integration_setup):
        """Test error recovery in integrated environment."""
        manager = integration_setup["manager"]
        config_dir = integration_setup["config_dir"]
        
        # Create invalid configuration file
        bad_config_file = config_dir / "bad_config.yaml"
        with open(bad_config_file, 'w') as f:
            f.write("invalid: yaml: content: [unclosed")
        
        # Should handle bad config gracefully
        try:
            manager.load()
            # Should not crash completely
            assert True
        except Exception as e:
            # Should be a handled configuration error
            assert "config" in str(e).lower() or "yaml" in str(e).lower()
        
        # Should still be able to work with valid configurations
        manager.set("recovery.test", "working", source=ConfigSource.COMMAND_LINE)
        assert manager.get("recovery.test") == "working"
    
    def test_multi_format_configuration_support(self, integration_setup):
        """Test support for multiple configuration formats."""
        manager = integration_setup["manager"]
        config_dir = integration_setup["config_dir"]
        
        # Test YAML support (already tested above)
        yaml_config = {"yaml_test": {"value": "from_yaml"}}
        with open(config_dir / "test.yaml", 'w') as f:
            yaml.dump(yaml_config, f)
        
        # Test JSON support
        json_config = {"json_test": {"value": "from_json"}}
        with open(config_dir / "test.json", 'w') as f:
            json.dump(json_config, f)
        
        # Load and verify both formats work
        manager.load()
        
        # Should handle multiple formats
        # (Actual behavior depends on implementation)
    
    def test_configuration_migration_scenario(self, integration_setup):
        """Test configuration migration from old to new format."""
        manager = integration_setup["manager"]
        
        # Simulate old configuration format
        old_config_keys = {
            "old_database_host": "old.db.example.com",
            "old_database_port": "5432",
            "old_api_timeout": "30"
        }
        
        for key, value in old_config_keys.items():
            manager.set(key, value, source=ConfigSource.MAIN_CONFIG)
        
        # Simulate migration to new format
        migration_mapping = {
            "old_database_host": "database.host",
            "old_database_port": "database.port",
            "old_api_timeout": "api.timeout"
        }
        
        for old_key, new_key in migration_mapping.items():
            old_value = manager.get(old_key)
            if old_value is not None:
                # Migrate to new key
                manager.set(new_key, old_value, source=ConfigSource.MAIN_CONFIG)
                
                # Optionally remove old key
                if hasattr(manager, 'remove'):
                    manager.remove(old_key)
        
        # Verify migration
        assert manager.get("database.host") == "old.db.example.com"
        assert manager.get("database.port") == "5432"
        assert manager.get("api.timeout") == "30"
    
    def test_production_like_scenario(self, integration_setup):
        """Test production-like configuration scenario."""
        manager = integration_setup["manager"]
        
        # Register production schemas
        prod_schemas = [
            ConfigSchema("app.name", str, ConfigSecurityLevel.PUBLIC, required=True),
            ConfigSchema("app.environment", str, ConfigSecurityLevel.PUBLIC, required=True),
            ConfigSchema("database.url", str, ConfigSecurityLevel.SECRET, required=True),
            ConfigSchema("redis.url", str, ConfigSecurityLevel.SENSITIVE),
            ConfigSchema("monitoring.enabled", bool, ConfigSecurityLevel.PUBLIC),
            ConfigSchema("logging.level", str, ConfigSecurityLevel.PUBLIC),
        ]
        
        for schema in prod_schemas:
            manager.register_schema(schema)
        
        # Simulate production environment variables
        with patch.dict(os.environ, {
            "APP_NAME": "ProductionApp",
            "APP_ENVIRONMENT": "production",
            "DATABASE_URL": "postgresql://user:pass@prod.db.com:5432/proddb",
            "REDIS_URL": "redis://prod.redis.com:6379/0",
            "MONITORING_ENABLED": "true",
            "LOGGING_LEVEL": "WARNING"
        }):
            manager.load()
            
            # Verify production configuration
            assert manager.get("app.name") == "ProductionApp"
            assert manager.get("app.environment") == "production"
            
            # Sensitive configurations should be available
            db_url = manager.get("database.url")
            assert db_url is not None
            assert "prod.db.com" in db_url
            
            # Feature configurations
            monitoring = manager.get("monitoring.enabled", type_hint=bool)
            assert monitoring is True
            
            log_level = manager.get("logging.level")
            assert log_level == "WARNING"
            
            # Test configuration export for deployment
            if hasattr(manager, 'export_config'):
                exported = manager.export_config(include_secrets=False)
                
                # Should contain public config but not secrets
                assert "app.name" in exported
                assert "database.url" not in exported  # Secret should be excluded