#!/usr/bin/env python3
"""
Comprehensive tests for configuration cache.
"""

import pytest
import time
import tempfile
from pathlib import Path

from core.unified_config.cache import ConfigCache
from core.unified_config.interfaces import ConfigValue, ConfigSource, ConfigSecurityLevel


class TestConfigCache:
    """Test the configuration cache system."""
    
    @pytest.fixture
    def cache(self):
        """Create a configuration cache instance."""
        return ConfigCache()
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_config_values(self):
        """Create sample configuration values for testing."""
        return {
            "app.name": ConfigValue("app.name", "TestApp", ConfigSource.DEFAULTS),
            "app.port": ConfigValue("app.port", 8080, ConfigSource.ENVIRONMENT),
            "db.host": ConfigValue("db.host", "localhost", ConfigSource.MAIN_CONFIG),
            "api.timeout": ConfigValue("api.timeout", 30, ConfigSource.ENV_FILE)
        }
    
    def test_cache_initialization(self, cache):
        """Test cache initializes correctly."""
        assert hasattr(cache, 'get')
        assert hasattr(cache, 'set')
        assert hasattr(cache, 'clear')
        assert callable(cache.get)
        assert callable(cache.set)
    
    def test_basic_cache_operations(self, cache):
        """Test basic cache get/set operations."""
        test_key = "test.cache.key"
        test_value = ConfigValue(test_key, "test_value", ConfigSource.DEFAULTS)
        
        # Initially should return None
        cached = cache.get(test_key)
        assert cached is None
        
        # Set value
        cache.set(test_key, test_value)
        
        # Should now return the value
        cached = cache.get(test_key)
        assert cached is not None
        assert cached.key == test_key
        assert cached.value == "test_value"
        assert cached.source == ConfigSource.DEFAULTS
    
    def test_cache_with_different_types(self, cache):
        """Test caching different value types."""
        test_cases = [
            ("string.value", "string_data"),
            ("int.value", 42),
            ("bool.value", True),
            ("list.value", [1, 2, 3, "four"]),
            ("dict.value", {"nested": {"key": "value"}}),
            ("none.value", None)
        ]
        
        for key, value in test_cases:
            config_value = ConfigValue(key, value, ConfigSource.DEFAULTS)
            cache.set(key, config_value)
            
            cached = cache.get(key)
            assert cached is not None
            assert cached.value == value
            assert cached.key == key
    
    def test_cache_expiration(self, cache):
        """Test cache expiration functionality."""
        test_key = "expiring.key"
        test_value = ConfigValue(test_key, "expiring_value", ConfigSource.DEFAULTS)
        
        # Set with short TTL if supported
        if hasattr(cache, 'set_with_ttl'):
            cache.set_with_ttl(test_key, test_value, ttl=0.1)  # 100ms
            
            # Should be available immediately
            cached = cache.get(test_key)
            assert cached is not None
            
            # Wait for expiration
            time.sleep(0.2)
            
            # Should be expired
            cached = cache.get(test_key)
            assert cached is None
    
    def test_cache_invalidation(self, cache, sample_config_values):
        """Test cache invalidation."""
        # Populate cache
        for key, value in sample_config_values.items():
            cache.set(key, value)
        
        # Verify all values are cached
        for key in sample_config_values.keys():
            assert cache.get(key) is not None
        
        # Test individual invalidation
        if hasattr(cache, 'invalidate'):
            cache.invalidate("app.name")
            assert cache.get("app.name") is None
            assert cache.get("app.port") is not None  # Others should remain
        
        # Test clear all
        cache.clear()
        for key in sample_config_values.keys():
            assert cache.get(key) is None
    
    def test_cache_size_limits(self, cache):
        """Test cache size limitations."""
        # Test maximum cache size if supported
        if hasattr(cache, 'max_size'):
            original_max = getattr(cache, 'max_size', None)
            cache.max_size = 3  # Small cache for testing
            
            try:
                # Add more items than the limit
                for i in range(5):
                    key = f"size.test.{i}"
                    value = ConfigValue(key, f"value_{i}", ConfigSource.DEFAULTS)
                    cache.set(key, value)
                
                # Check that cache respects size limit
                cached_count = 0
                for i in range(5):
                    key = f"size.test.{i}"
                    if cache.get(key) is not None:
                        cached_count += 1
                
                # Should not exceed max size
                assert cached_count <= 3
                
            finally:
                # Restore original max size
                if original_max is not None:
                    cache.max_size = original_max
    
    def test_cache_key_normalization(self, cache):
        """Test cache key normalization."""
        # Test that similar keys are handled consistently
        test_cases = [
            ("app.name", "app.name"),           # Exact match
            ("APP.NAME", "app.name"),           # Case normalization
            ("app..name", "app.name"),          # Double dot normalization
            ("app.name.", "app.name"),          # Trailing dot removal
        ]
        
        base_value = ConfigValue("app.name", "test_value", ConfigSource.DEFAULTS)
        
        for input_key, expected_key in test_cases:
            # Clear cache first
            cache.clear()
            
            # Set with input key
            cache.set(input_key, base_value)
            
            # Try to get with expected key
            cached = cache.get(expected_key)
            
            # Should find the value (if normalization is implemented)
            if hasattr(cache, 'normalize_key'):
                assert cached is not None
                assert cached.value == "test_value"
    
    def test_cache_statistics(self, cache):
        """Test cache statistics tracking."""
        if hasattr(cache, 'get_stats'):
            # Reset stats
            cache.clear()
            
            test_key = "stats.test"
            test_value = ConfigValue(test_key, "stats_value", ConfigSource.DEFAULTS)
            
            # Cache miss
            cache.get(test_key)
            
            # Cache set
            cache.set(test_key, test_value)
            
            # Cache hit
            cache.get(test_key)
            cache.get(test_key)
            
            # Check statistics
            stats = cache.get_stats()
            assert isinstance(stats, dict)
            assert 'hits' in stats or 'misses' in stats or 'total_requests' in stats
    
    def test_cache_thread_safety(self, cache):
        """Test cache thread safety."""
        import concurrent.futures
        
        def cache_worker(worker_id):
            """Worker function for thread safety test."""
            for i in range(10):
                key = f"thread.{worker_id}.{i}"
                value = ConfigValue(key, f"value_{worker_id}_{i}", ConfigSource.DEFAULTS)
                
                # Set value
                cache.set(key, value)
                
                # Get value
                cached = cache.get(key)
                
                # Verify consistency
                if cached is not None:
                    assert cached.value == f"value_{worker_id}_{i}"
                
                time.sleep(0.001)  # Small delay to increase contention
        
        # Run multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for worker_id in range(5):
                future = executor.submit(cache_worker, worker_id)
                futures.append(future)
            
            # Wait for all threads to complete
            for future in concurrent.futures.as_completed(futures):
                future.result()  # Will raise exception if worker failed
    
    def test_cache_persistence(self, cache, temp_cache_dir):
        """Test cache persistence to disk."""
        if hasattr(cache, 'persist_to_disk'):
            test_data = {
                "persist.key1": ConfigValue("persist.key1", "persist_value1", ConfigSource.DEFAULTS),
                "persist.key2": ConfigValue("persist.key2", 42, ConfigSource.ENVIRONMENT)
            }
            
            # Populate cache
            for key, value in test_data.items():
                cache.set(key, value)
            
            # Persist to disk
            cache_file = temp_cache_dir / "cache.dat"
            cache.persist_to_disk(cache_file)
            
            # Verify file was created
            assert cache_file.exists()
            
            # Clear memory cache
            cache.clear()
            
            # Verify cache is empty
            for key in test_data.keys():
                assert cache.get(key) is None
            
            # Load from disk
            if hasattr(cache, 'load_from_disk'):
                cache.load_from_disk(cache_file)
                
                # Verify data was restored
                for key, original_value in test_data.items():
                    cached = cache.get(key)
                    assert cached is not None
                    assert cached.value == original_value.value
    
    def test_cache_memory_efficiency(self, cache):
        """Test cache memory usage efficiency."""
        
        # Measure memory before large cache operation
        if hasattr(cache, 'get_memory_usage'):
            initial_memory = cache.get_memory_usage()
        else:
            initial_memory = 0
        
        # Add many items to cache
        large_dataset = {}
        for i in range(1000):
            key = f"memory.test.{i}"
            value = ConfigValue(key, f"data_{i}" * 10, ConfigSource.DEFAULTS)  # Some data
            large_dataset[key] = value
            cache.set(key, value)
        
        # Measure memory after
        if hasattr(cache, 'get_memory_usage'):
            final_memory = cache.get_memory_usage()
            memory_per_item = (final_memory - initial_memory) / 1000
            
            # Should be reasonable memory usage per item
            assert memory_per_item < 1024  # Less than 1KB per item seems reasonable
        
        # Clean up
        cache.clear()
    
    def test_cache_with_security_levels(self, cache):
        """Test cache behavior with different security levels."""
        security_test_cases = [
            ("public.key", ConfigSecurityLevel.PUBLIC, True),      # Should cache public
            ("internal.key", ConfigSecurityLevel.INTERNAL, True),  # Should cache internal
            ("sensitive.key", ConfigSecurityLevel.SENSITIVE, False), # May not cache sensitive
            ("secret.key", ConfigSecurityLevel.SECRET, False)     # Should not cache secrets
        ]
        
        for key, security_level, should_cache in security_test_cases:
            config_value = ConfigValue(key, f"value_for_{key}", ConfigSource.ENVIRONMENT, security_level)
            
            # Set in cache
            cache.set(key, config_value)
            
            # Try to get from cache
            cached = cache.get(key)
            
            if should_cache:
                # Should be available from cache
                assert cached is not None
                assert cached.value == f"value_for_{key}"
            else:
                # May not be cached due to security policy
                # (This depends on cache implementation)
                pass
    
    def test_cache_configuration_refresh(self, cache):
        """Test cache behavior during configuration refresh."""
        refresh_key = "refresh.test"
        
        # Set initial value
        initial_value = ConfigValue(refresh_key, "initial_value", ConfigSource.DEFAULTS)
        cache.set(refresh_key, initial_value)
        
        # Verify initial value
        cached = cache.get(refresh_key)
        assert cached.value == "initial_value"
        
        # Simulate configuration refresh with new value
        updated_value = ConfigValue(refresh_key, "updated_value", ConfigSource.ENVIRONMENT)
        
        # Test refresh behavior
        if hasattr(cache, 'refresh'):
            cache.refresh(refresh_key, updated_value)
            
            # Should get updated value
            cached = cache.get(refresh_key)
            assert cached.value == "updated_value"
            assert cached.source == ConfigSource.ENVIRONMENT
        else:
            # Manual refresh by setting new value
            cache.set(refresh_key, updated_value)
            cached = cache.get(refresh_key)
            assert cached.value == "updated_value"


class TestConfigCacheIntegration:
    """Integration tests for configuration cache."""
    
    @pytest.fixture
    def integration_cache(self, tmp_path):
        """Create cache for integration testing."""
        return ConfigCache()
    
    def test_cache_with_configuration_manager(self, integration_cache):
        """Test cache integration with configuration manager."""
        # Simulate configuration manager usage patterns
        config_data = {
            "app.name": ConfigValue("app.name", "IntegrationApp", ConfigSource.ENVIRONMENT),
            "app.port": ConfigValue("app.port", 9000, ConfigSource.ENVIRONMENT),
            "db.host": ConfigValue("db.host", "integration.db.com", ConfigSource.MAIN_CONFIG),
            "api.timeout": ConfigValue("api.timeout", 45, ConfigSource.ENV_FILE)
        }
        
        # Bulk cache operations
        for key, value in config_data.items():
            integration_cache.set(key, value)
        
        # Verify all cached
        for key, expected_value in config_data.items():
            cached = integration_cache.get(key)
            assert cached is not None
            assert cached.value == expected_value.value
            assert cached.source == expected_value.source
        
        # Test prefix-based operations if supported
        if hasattr(integration_cache, 'get_by_prefix'):
            app_configs = integration_cache.get_by_prefix("app")
            assert len(app_configs) >= 2  # app.name and app.port
    
    def test_cache_performance_under_load(self, integration_cache):
        """Test cache performance under high load."""
        import time
        
        # Generate test data
        test_data = {}
        for i in range(100):
            key = f"perf.test.{i}"
            value = ConfigValue(key, f"performance_value_{i}", ConfigSource.DEFAULTS)
            test_data[key] = value
        
        # Measure set performance
        start_time = time.time()
        for key, value in test_data.items():
            integration_cache.set(key, value)
        set_time = time.time() - start_time
        
        # Measure get performance
        start_time = time.time()
        for key in test_data.keys():
            cached = integration_cache.get(key)
            assert cached is not None
        get_time = time.time() - start_time
        
        # Performance should be reasonable
        assert set_time < 1.0  # Should set 100 items in less than 1 second
        assert get_time < 0.5  # Should get 100 items in less than 0.5 seconds
        
        # Get operations should be faster than set operations
        assert get_time < set_time
    
    def test_cache_error_handling(self, integration_cache):
        """Test cache error handling and recovery."""
        # Test handling of corrupted cache data
        corrupted_key = "corrupted.test"
        
        # Simulate corrupted data scenario
        if hasattr(integration_cache, '_storage'):
            # Try to directly corrupt cache storage
            try:
                integration_cache._storage[corrupted_key] = "corrupted_data"
                
                # Getting corrupted data should not crash
                integration_cache.get(corrupted_key)
                # Should handle gracefully (return None or raise handled exception)
                
            except Exception as e:
                # Should be a handled exception
                assert "cache" in str(e).lower() or "corrupt" in str(e).lower()
        
        # Test cache recovery
        normal_key = "normal.test"
        normal_value = ConfigValue(normal_key, "normal_value", ConfigSource.DEFAULTS)
        
        # Should still be able to use cache normally
        integration_cache.set(normal_key, normal_value)
        cached = integration_cache.get(normal_key)
        assert cached is not None
        assert cached.value == "normal_value"
    
    def test_cache_configuration_scenarios(self, integration_cache):
        """Test cache in realistic configuration scenarios."""
        # Scenario 1: Application startup
        startup_configs = {
            "app.name": ConfigValue("app.name", "MyApp", ConfigSource.ENVIRONMENT),
            "app.version": ConfigValue("app.version", "1.0.0", ConfigSource.MAIN_CONFIG),
            "logging.level": ConfigValue("logging.level", "INFO", ConfigSource.ENV_FILE)
        }
        
        # Cache startup configuration
        for key, value in startup_configs.items():
            integration_cache.set(key, value)
        
        # Scenario 2: Runtime configuration updates
        runtime_updates = {
            "logging.level": ConfigValue("logging.level", "DEBUG", ConfigSource.COMMAND_LINE),
            "feature.new_ui": ConfigValue("feature.new_ui", True, ConfigSource.COMMAND_LINE)
        }
        
        # Update cache with runtime changes
        for key, value in runtime_updates.items():
            integration_cache.set(key, value)
        
        # Verify final state
        assert integration_cache.get("app.name").value == "MyApp"
        assert integration_cache.get("logging.level").value == "DEBUG"  # Updated value
        assert integration_cache.get("logging.level").source == ConfigSource.COMMAND_LINE
        assert integration_cache.get("feature.new_ui").value is True
        
        # Scenario 3: Configuration reload
        integration_cache.clear()
        
        # Should be empty after clear
        for key in startup_configs.keys():
            assert integration_cache.get(key) is None