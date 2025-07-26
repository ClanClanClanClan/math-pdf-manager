#!/usr/bin/env python3
"""
Unified Configuration System - Cache

Provides caching for configuration values to improve performance.
"""

import sys
import time
import threading
from typing import Any, Dict, Optional

from .interfaces import IConfigCache


class ConfigCache(IConfigCache):
    """Secure in-memory cache for configuration values."""
    
    # Security limits
    MAX_CACHE_SIZE = 1000  # Maximum number of entries
    MAX_KEY_LENGTH = 256   # Maximum key length
    MAX_VALUE_SIZE = 1024 * 1024  # 1MB maximum value size
    
    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = min(default_ttl, 86400)  # Max 24 hours TTL
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()  # Thread safety
    
    def _validate_key(self, key: str) -> None:
        """Validate cache key for security."""
        if not isinstance(key, str):
            raise ValueError("Cache key must be a string")
        if len(key) > self.MAX_KEY_LENGTH:
            raise ValueError(f"Cache key too long: {len(key)} > {self.MAX_KEY_LENGTH}")
        if not key.strip():
            raise ValueError("Cache key cannot be empty")
        # Prevent keys with dangerous characters
        if any(ord(c) < 32 for c in key if c not in '\t\n\r '):
            raise ValueError("Cache key contains control characters")
    
    def _validate_value(self, value: Any) -> None:
        """Validate cache value for security."""
        value_size = sys.getsizeof(value)
        if value_size > self.MAX_VALUE_SIZE:
            raise ValueError(f"Cache value too large: {value_size} > {self.MAX_VALUE_SIZE}")
    
    def _evict_if_needed(self) -> None:
        """Evict old entries if cache is too large."""
        if len(self._cache) >= self.MAX_CACHE_SIZE:
            # Remove oldest entries
            sorted_entries = sorted(
                self._cache.items(), 
                key=lambda x: x[1]['created']
            )
            # Remove oldest 10% of entries
            to_remove = len(sorted_entries) // 10 + 1
            for key, _ in sorted_entries[:to_remove]:
                del self._cache[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached configuration value with security validation."""
        try:
            self._validate_key(key)
        except ValueError:
            self._misses += 1
            return None
            
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                # Check if expired
                if entry['expires'] > time.time():
                    self._hits += 1
                    return entry['value']
                else:
                    # Remove expired entry
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached configuration value with security validation."""
        self._validate_key(key)
        self._validate_value(value)
        
        # Validate TTL
        if ttl is not None:
            ttl = min(max(ttl, 1), 86400)  # Clamp between 1 second and 24 hours
        
        with self._lock:
            self._evict_if_needed()
            
            expires = time.time() + (ttl or self.default_ttl)
            self._cache[key] = {
                'value': value,
                'expires': expires,
                'created': time.time()
            }
    
    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate cache (specific key or all) with security validation."""
        with self._lock:
            if key is None:
                self._cache.clear()
            else:
                try:
                    self._validate_key(key)
                    if key in self._cache:
                        del self._cache[key]
                except ValueError:
                    # Ignore invalid keys for invalidation
                    pass
    
    def clear(self) -> None:
        """Clear all cache entries securely."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(1 for entry in self._cache.values() 
                           if entry['expires'] > current_time)
        
        return {
            'total_entries': len(self._cache),
            'valid_entries': valid_entries,
            'expired_entries': len(self._cache) - valid_entries,
            'hits': self._hits,
            'misses': self._misses,
            'total_requests': self._hits + self._misses
        }
