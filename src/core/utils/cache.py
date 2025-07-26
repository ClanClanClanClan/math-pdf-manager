#!/usr/bin/env python3
"""
High-performance caching utilities
Optimized for academic document processing
"""

import hashlib
# Removed pickle import for security - using JSON instead
import time
from pathlib import Path
from typing import Any, Optional, Dict, Callable, TypeVar
from functools import wraps
import threading

T = TypeVar('T')


class LRUCache:
    """Thread-safe LRU cache with size limits and TTL."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: list = []
        self.lock = threading.Lock()
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = []
        
        for key, data in self.cache.items():
            if current_time - data['timestamp'] > self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_key(key)
    
    def _remove_key(self, key: str):
        """Remove key from cache and access order."""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            self.access_order.remove(key)
    
    def _evict_lru(self):
        """Evict least recently used item."""
        if self.access_order:
            lru_key = self.access_order[0]
            self._remove_key(lru_key)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            self._cleanup_expired()
            
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]['value']
            
            return None
    
    def put(self, key: str, value: Any):
        """Put value in cache."""
        with self.lock:
            self._cleanup_expired()
            
            # Remove if already exists
            if key in self.cache:
                self._remove_key(key)
            
            # Evict if at capacity
            while len(self.cache) >= self.max_size:
                self._evict_lru()
            
            # Add new entry
            self.cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
            self.access_order.append(key)
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()


class DiskCache:
    """Persistent disk-based cache for expensive computations."""
    
    def __init__(self, cache_dir: str = ".cache", max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.lock = threading.Lock()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"cache_{key_hash}.pkl"
    
    def _cleanup_old_files(self):
        """Remove old cache files to stay under size limit."""
        cache_files = list(self.cache_dir.glob("cache_*.pkl"))
        
        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda f: f.stat().st_mtime)
        
        total_size = sum(f.stat().st_size for f in cache_files)
        
        while total_size > self.max_size_bytes and cache_files:
            oldest = cache_files.pop(0)
            total_size -= oldest.stat().st_size
            try:
                oldest.unlink()
            except OSError:
                pass  # File might have been deleted by another process
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            # SECURITY: Use safer JSON instead of pickle for cache
            with open(cache_path, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
            
            # Update access time
            cache_path.touch()
            
            return data
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            # Corrupted or inaccessible file
            try:
                cache_path.unlink()
            except OSError:
                pass
            return None
    
    def put(self, key: str, value: Any):
        """Put value in disk cache."""
        with self.lock:
            cache_path = self._get_cache_path(key)
            
            try:
                # SECURITY: Use safer JSON instead of pickle for cache
                with open(cache_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(value, f, ensure_ascii=False, indent=2)
                
                # Cleanup old files if needed
                self._cleanup_old_files()
                
            except (TypeError, OSError):
                # Couldn't save - that's okay, cache is optional (value not JSON-serializable)
                pass


# Global cache instances
_memory_cache = LRUCache(max_size=1000, ttl_seconds=3600)
_disk_cache = DiskCache(cache_dir=".cache", max_size_mb=100)


def memoize_with_ttl(ttl_seconds: int = 3600, use_disk: bool = False):
    """
    Decorator for caching function results with TTL.
    
    Args:
        ttl_seconds: Time to live for cached results
        use_disk: Whether to use disk cache for persistence
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Create cache key from function name and arguments
            key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = hashlib.sha256(key_data.encode()).hexdigest()
            
            # Try to get from cache
            cache = _disk_cache if use_disk else _memory_cache
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Compute result and cache it
            result = func(*args, **kwargs)
            cache.put(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


def cache_file_processing(func: Callable[[Path], T]) -> Callable[[Path], T]:
    """
    Decorator for caching file processing results based on file modification time.
    """
    @wraps(func)
    def wrapper(file_path: Path) -> T:
        # Include file modification time in cache key for invalidation
        try:
            mtime = file_path.stat().st_mtime
            key_data = f"{func.__name__}:{file_path}:{mtime}"
            cache_key = hashlib.sha256(key_data.encode()).hexdigest()
            
            # Check disk cache (file processing results should persist)
            cached_result = _disk_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Process file and cache result
            result = func(file_path)
            _disk_cache.put(cache_key, result)
            
            return result
            
        except OSError:
            # File doesn't exist or can't be accessed - don't cache
            return func(file_path)
    
    return wrapper