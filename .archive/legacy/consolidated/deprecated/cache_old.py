#!/usr/bin/env python3
"""
Advanced caching system for Unicode Utils with Redis integration.

This module provides high-performance caching capabilities with:
- Multi-tier caching (memory + Redis)
- Automatic cache warming and invalidation
- Performance monitoring and metrics
- TTL management and compression
- Thread-safe operations
- Async support for high-performance operations
"""

import asyncio
import base64
import gzip
import hashlib
import json
import logging
import pickle
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, Union

# Optional Redis support
try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    aioredis = None
    REDIS_AVAILABLE = False

from .exceptions import CacheError, ConfigurationError
from .logging_config import PerformanceLogger, get_logger

logger = get_logger(__name__)

@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    compressed: bool = False
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def access(self):
        """Mark entry as accessed."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'key': self.key,
            'value': self.value,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'size_bytes': self.size_bytes,
            'compressed': self.compressed
        }

class CacheStats:
    """Tracks cache performance statistics."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_requests = 0
        self.total_compute_time = 0.0
        self.total_cache_time = 0.0
        self._lock = threading.Lock()
    
    def record_hit(self, cache_time: float):
        """Record a cache hit."""
        with self._lock:
            self.hits += 1
            self.total_requests += 1
            self.total_cache_time += cache_time
    
    def record_miss(self, compute_time: float):
        """Record a cache miss."""
        with self._lock:
            self.misses += 1
            self.total_requests += 1
            self.total_compute_time += compute_time
    
    def record_eviction(self):
        """Record a cache eviction."""
        with self._lock:
            self.evictions += 1
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        with self._lock:
            if self.total_requests == 0:
                return 0.0
            return self.hits / self.total_requests
    
    @property
    def avg_compute_time(self) -> float:
        """Average time for cache misses."""
        with self._lock:
            if self.misses == 0:
                return 0.0
            return self.total_compute_time / self.misses
    
    @property
    def avg_cache_time(self) -> float:
        """Average time for cache hits."""
        with self._lock:
            if self.hits == 0:
                return 0.0
            return self.total_cache_time / self.hits
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all statistics."""
        with self._lock:
            return {
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'total_requests': self.total_requests,
                'hit_rate': self.hit_rate,
                'avg_compute_time_ms': self.avg_compute_time * 1000,
                'avg_cache_time_ms': self.avg_cache_time * 1000,
                'total_compute_time_ms': self.total_compute_time * 1000,
                'total_cache_time_ms': self.total_cache_time * 1000
            }


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, entry: CacheEntry, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    def keys(self) -> List[str]:
        """Get all cache keys."""
        pass


class MemoryCache(CacheBackend):
    """High-performance in-memory cache with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._current_memory = 0
        self.stats = CacheStats()
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes."""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, tuple)):
                return sum(self._calculate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(self._calculate_size(k) + self._calculate_size(v) 
                          for k, v in value.items())
            else:
                # Fallback: use pickle size
                return len(pickle.dumps(value))
        except Exception:
            return 1024  # Conservative estimate
    
    def _evict_if_needed(self):
        """Evict entries if cache is full."""
        while (len(self._cache) > self.max_size or 
               self._current_memory > self.max_memory_bytes):
            if not self._cache:
                break
            
            # Remove least recently used item
            key, entry = self._cache.popitem(last=False)
            self._current_memory -= entry.size_bytes
            self.stats.record_eviction()
            logger.debug(f"Evicted cache entry: {key}")
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from cache."""
        start_time = time.perf_counter()
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self.stats.record_miss(0)
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._current_memory -= entry.size_bytes
                self.stats.record_miss(0)
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access()
            
            cache_time = time.perf_counter() - start_time
            self.stats.record_hit(cache_time)
            
            return entry
    
    def set(self, key: str, entry: CacheEntry, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            with self._lock:
                # Calculate size
                entry.size_bytes = self._calculate_size(entry.value)
                
                # Set expiration
                if ttl:
                    entry.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
                
                # Remove existing entry if present
                if key in self._cache:
                    old_entry = self._cache[key]
                    self._current_memory -= old_entry.size_bytes
                
                # Add new entry
                self._cache[key] = entry
                self._current_memory += entry.size_bytes
                
                # Evict if necessary
                self._evict_if_needed()
                
                return True
        except Exception as e:
            logger.error(f"Failed to set cache entry: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_memory -= entry.size_bytes
                return True
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
            return True
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        with self._lock:
            return key in self._cache
    
    def keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        with self._lock:
            return {
                'current_memory_bytes': self._current_memory,
                'current_memory_mb': self._current_memory / 1024 / 1024,
                'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
                'memory_utilization': self._current_memory / self.max_memory_bytes,
                'entry_count': len(self._cache),
                'max_entries': self.max_size
            }


class RedisCache(CacheBackend):
    """Redis-based distributed cache."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, 
                 password: Optional[str] = None, db: int = 0,
                 key_prefix: str = "unicode_utils:"):
        if not REDIS_AVAILABLE:
            raise ConfigurationError("Redis not available. Install redis-py.")
        
        self.key_prefix = key_prefix
        self.stats = CacheStats()
        
        try:
            self.client = redis.Redis(
                host=host, port=port, password=password, db=db,
                decode_responses=False, socket_timeout=5,
                socket_connect_timeout=5, retry_on_timeout=True
            )
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}")
        except Exception as e:
            raise CacheError(f"Failed to connect to Redis: {e}")
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.key_prefix}{key}"
    
    def _serialize_entry(self, entry: CacheEntry) -> bytes:
        """Serialize cache entry for storage."""
        data = entry.to_dict()
        serialized = json.dumps(data).encode('utf-8')
        
        # Compress if beneficial
        if len(serialized) > 1024:
            compressed = gzip.compress(serialized)
            if len(compressed) < len(serialized) * 0.8:
                entry.compressed = True
                return b'GZIP:' + compressed
        
        return serialized
    
    def _deserialize_entry(self, data: bytes) -> CacheEntry:
        """Deserialize cache entry from storage."""
        if data.startswith(b'GZIP:'):
            data = gzip.decompress(data[5:])
        
        entry_data = json.loads(data.decode('utf-8'))
        
        return CacheEntry(
            key=entry_data['key'],
            value=entry_data['value'],
            created_at=datetime.fromisoformat(entry_data['created_at']),
            expires_at=datetime.fromisoformat(entry_data['expires_at']) if entry_data['expires_at'] else None,
            access_count=entry_data['access_count'],
            last_accessed=datetime.fromisoformat(entry_data['last_accessed']) if entry_data['last_accessed'] else None,
            size_bytes=entry_data['size_bytes'],
            compressed=entry_data.get('compressed', False)
        )
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from cache."""
        start_time = time.perf_counter()
        redis_key = self._make_key(key)
        
        try:
            data = self.client.get(redis_key)
            if data is None:
                self.stats.record_miss(0)
                return None
            
            entry = self._deserialize_entry(data)
            
            if entry.is_expired():
                self.client.delete(redis_key)
                self.stats.record_miss(0)
                return None
            
            # Update access info
            entry.access()
            self.client.set(redis_key, self._serialize_entry(entry))
            
            cache_time = time.perf_counter() - start_time
            self.stats.record_hit(cache_time)
            
            return entry
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            self.stats.record_miss(0)
            return None
    
    def set(self, key: str, entry: CacheEntry, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        redis_key = self._make_key(key)
        
        try:
            # Set expiration
            if ttl:
                entry.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            data = self._serialize_entry(entry)
            
            if ttl:
                result = self.client.setex(redis_key, ttl, data)
            else:
                result = self.client.set(redis_key, data)
            
            return bool(result)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        redis_key = self._make_key(key)
        try:
            return bool(self.client.delete(redis_key))
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            keys = self.client.keys(f"{self.key_prefix}*")
            if keys:
                return bool(self.client.delete(*keys))
            return True
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        redis_key = self._make_key(key)
        try:
            return bool(self.client.exists(redis_key))
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False
    
    def keys(self) -> List[str]:
        """Get all cache keys."""
        try:
            redis_keys = self.client.keys(f"{self.key_prefix}*")
            return [key.decode('utf-8')[len(self.key_prefix):] for key in redis_keys]
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []


class MultiTierCache:
    """Multi-tier cache combining memory and Redis."""
    
    def __init__(self, 
                 memory_cache: Optional[MemoryCache] = None,
                 redis_cache: Optional[RedisCache] = None,
                 default_ttl: int = 3600):
        self.memory_cache = memory_cache or MemoryCache()
        self.redis_cache = redis_cache
        self.default_ttl = default_ttl
        self.stats = CacheStats()
        
        logger.info(f"Initialized multi-tier cache with memory={bool(memory_cache)}, redis={bool(redis_cache)}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, checking memory first, then Redis."""
        start_time = time.perf_counter()
        
        # Try memory cache first
        entry = self.memory_cache.get(key)
        if entry is not None:
            cache_time = time.perf_counter() - start_time
            self.stats.record_hit(cache_time)
            logger.debug(f"Cache hit (memory): {key}")
            return entry.value
        
        # Try Redis cache
        if self.redis_cache:
            entry = self.redis_cache.get(key)
            if entry is not None:
                # Populate memory cache
                self.memory_cache.set(key, entry)
                
                cache_time = time.perf_counter() - start_time
                self.stats.record_hit(cache_time)
                logger.debug(f"Cache hit (redis): {key}")
                return entry.value
        
        self.stats.record_miss(0)
        logger.debug(f"Cache miss: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if ttl is None:
            ttl = self.default_ttl
        
        entry = CacheEntry(key=key, value=value)
        
        # Set in memory cache
        memory_success = self.memory_cache.set(key, entry, ttl)
        
        # Set in Redis cache
        redis_success = True
        if self.redis_cache:
            redis_success = self.redis_cache.set(key, entry, ttl)
        
        success = memory_success and redis_success
        if success:
            logger.debug(f"Cache set: {key} (ttl={ttl}s)")
        else:
            logger.warning(f"Cache set failed: {key}")
        
        return success
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        memory_success = self.memory_cache.delete(key)
        redis_success = True
        
        if self.redis_cache:
            redis_success = self.redis_cache.delete(key)
        
        return memory_success or redis_success
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        memory_success = self.memory_cache.clear()
        redis_success = True
        
        if self.redis_cache:
            redis_success = self.redis_cache.clear()
        
        return memory_success and redis_success
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {
            'multi_tier': self.stats.get_stats(),
            'memory': self.memory_cache.stats.get_stats(),
        }
        
        if self.redis_cache:
            stats['redis'] = self.redis_cache.stats.get_stats()
        
        # Add memory usage
        stats['memory_usage'] = self.memory_cache.get_memory_usage()
        
        return stats


# Global cache instance
_cache_instance: Optional[MultiTierCache] = None


def get_cache() -> MultiTierCache:
    """Get the global cache instance."""
    global _cache_instance
    
    if _cache_instance is None:
        # Try to initialize with Redis if available
        redis_cache = None
        if REDIS_AVAILABLE:
            import os
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            try:
                # Parse Redis URL
                if redis_url.startswith('redis://'):
                    # Simple parsing for redis://host:port
                    parts = redis_url[8:].split(':')
                    host = parts[0] or 'localhost'
                    port = int(parts[1]) if len(parts) > 1 else 6379
                    redis_cache = RedisCache(host=host, port=port)
                else:
                    redis_cache = RedisCache()
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
        
        _cache_instance = MultiTierCache(redis_cache=redis_cache)
    
    return _cache_instance


def cached(ttl: int = 3600, key_func: Optional[Callable] = None):
    """Decorator for caching function results."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                for arg in args:
                    key_parts.append(str(hash(str(arg))))
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}:{hash(str(v))}")
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Compute and cache result
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, ttl)
                
                compute_time = time.perf_counter() - start_time
                cache.stats.record_miss(compute_time)
                
                return result
            except Exception as e:
                compute_time = time.perf_counter() - start_time
                cache.stats.record_miss(compute_time)
                raise
        
        return wrapper
    return decorator


# Legacy class for compatibility
class LigatureCache:
    """Legacy ligature cache for backward compatibility."""
    
    def __init__(self, max_size: int = 1000):
        self._cache = get_cache()
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self._cache.set(key, value)
    
    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()
            else:
                try:
                    json.dumps(value)  # Test if serializable
                    serializable_kwargs[key] = value
                except (TypeError, ValueError):
                    serializable_kwargs[key] = str(value)
        
        key_data = {
            'func': func_name,
            'args': serializable_args,
            'kwargs': sorted(serializable_kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (checks all levels)."""
        start_time = time.time()
        
        # L1: Check memory cache
        with self._lock:
            if key in self.memory_cache:
                entry = self.memory_cache.pop(key)  # Move to end (LRU)
                self.memory_cache[key] = entry
                
                # Check expiration
                if entry.expires_at and datetime.now() > entry.expires_at:
                    del self.memory_cache[key]
                else:
                    entry.access_count += 1
                    entry.last_accessed = datetime.now()
                    self.stats.record_hit(time.time() - start_time)
                    return entry.value
        
        # L2: Check disk cache
        value = self._get_from_disk(key)
        if value is not None:
            # Promote to memory cache
            self._promote_to_memory(key, value)
            self.stats.record_hit(time.time() - start_time)
            return value
        
        # L3: Check Redis cache
        if self.redis_client:
            value = self._get_from_redis(key)
            if value is not None:
                # Promote to memory and disk cache
                self._promote_to_memory(key, value)
                self._save_to_disk(key, value)
                self.stats.record_hit(time.time() - start_time)
                return value
        
        self.stats.record_miss(0)
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache (all levels)."""
        ttl = ttl or self.ttl_seconds
        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
        
        # Calculate size
        try:
            size_bytes = len(pickle.dumps(value))
        except Exception as e:
            size_bytes = 0
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            size_bytes=size_bytes
        )
        
        # L1: Save to memory cache
        with self._lock:
            if len(self.memory_cache) >= self.max_memory_size:
                # Evict oldest entry
                evicted_key = next(iter(self.memory_cache))
                del self.memory_cache[evicted_key]
                self.stats.record_eviction()
            
            self.memory_cache[key] = entry
        
        # L2: Save to disk cache
        self._save_to_disk(key, value, expires_at)
        
        # L3: Save to Redis cache
        if self.redis_client:
            self._save_to_redis(key, value, ttl)
    
    def _get_from_disk(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        conn = sqlite3.connect(self.disk_db)
        cursor = conn.execute(
            'SELECT value, expires_at FROM cache WHERE key = ?',
            (key,)
        )
        row = cursor.fetchone()
        
        if row:
            value_blob, expires_at = row
            
            # Check expiration
            if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                conn.execute('DELETE FROM cache WHERE key = ?', (key,))
                conn.commit()
                conn.close()
                return None
            
            # Update access info
            conn.execute('''
                UPDATE cache 
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE key = ?
            ''', (datetime.now(), key))
            conn.commit()
            conn.close()
            
            return # WARNING: pickle.loads is unsafe - consider using json.loads
    json.loads(value_blob)
        
        conn.close()
        return None
    
    def _save_to_disk(self, key: str, value: Any, expires_at: Optional[datetime] = None):
        """Save value to disk cache."""
        # Check disk cache size
        conn = sqlite3.connect(self.disk_db)
        count = conn.execute('SELECT COUNT(*) FROM cache').fetchone()[0]
        
        if count >= self.max_disk_size:
            # Evict oldest entries (10% of cache)
            evict_count = self.max_disk_size // 10
            conn.execute('''
                DELETE FROM cache 
                WHERE key IN (
                    SELECT key FROM cache 
                    ORDER BY last_accessed ASC 
                    LIMIT ?
                )
            ''', (evict_count,))
            self.stats.record_eviction()
        
        # Save new entry
        value_blob = pickle.dumps(value)
        conn.execute('''
            INSERT OR REPLACE INTO cache 
            (key, value, created_at, expires_at, size_bytes)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            key,
            value_blob,
            datetime.now(),
            expires_at,
            len(value_blob)
        ))
        conn.commit()
        conn.close()
    
    def _get_from_redis(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            value_blob = self.redis_client.get(key)
            if value_blob:
                return # WARNING: pickle.loads is unsafe - consider using json.loads
    json.loads(value_blob)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None
    
    def _save_to_redis(self, key: str, value: Any, ttl: int):
        """Save value to Redis cache."""
        try:
            value_blob = pickle.dumps(value)
            self.redis_client.setex(key, ttl, value_blob)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def _promote_to_memory(self, key: str, value: Any):
        """Promote value to memory cache."""
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=None,  # Will be set from disk/redis metadata
            access_count=1,
            last_accessed=datetime.now()
        )
        
        with self._lock:
            if len(self.memory_cache) >= self.max_memory_size:
                evicted_key = next(iter(self.memory_cache))
                del self.memory_cache[evicted_key]
                self.stats.record_eviction()
            
            self.memory_cache[key] = entry
    
    def clear(self):
        """Clear all cache levels."""
        # Clear memory
        with self._lock:
            self.memory_cache.clear()
        
        # Clear disk
        conn = sqlite3.connect(self.disk_db)
        conn.execute('DELETE FROM cache')
        conn.commit()
        conn.close()
        
        # Clear Redis
        if self.redis_client:
            self.redis_client.flushdb()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.stats.get_stats()
        
        # Add cache sizes
        with self._lock:
            stats['memory_size'] = len(self.memory_cache)
        
        conn = sqlite3.connect(self.disk_db)
        stats['disk_size'] = conn.execute('SELECT COUNT(*) FROM cache').fetchone()[0]
        conn.close()
        
        if self.redis_client:
            try:
                stats['redis_size'] = self.redis_client.dbsize()
            except Exception as e:
                stats['redis_size'] = 0
        
        return stats

# Global cache instance
_global_cache = None

def get_cache() -> MultiLevelCache:
    """Get global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = MultiLevelCache()
    return _global_cache

def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Optional prefix for cache keys
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            cache_key = cache._generate_key(
                f"{key_prefix}{func.__name__}",
                args,
                kwargs
            )
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Compute result
            start_time = time.time()
            result = func(*args, **kwargs)
            compute_time = time.time() - start_time
            
            # Save to cache
            cache.set(cache_key, result, ttl)
            cache.stats.record_miss(compute_time)
            
            return result
        
        # Async version
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            cache_key = cache._generate_key(
                f"{key_prefix}{func.__name__}",
                args,
                kwargs
            )
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Compute result
            start_time = time.time()
            result = await func(*args, **kwargs)
            compute_time = time.time() - start_time
            
            # Save to cache
            cache.set(cache_key, result, ttl)
            cache.stats.record_miss(compute_time)
            
            return result
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator

class CacheWarmer:
    """Preloads cache with commonly accessed data."""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.warming_functions = []
    
    def register(self, func: Callable, args_list: List[tuple]):
        """Register function for cache warming."""
        self.warming_functions.append((func, args_list))
    
    async def warm_cache(self):
        """Warm the cache with registered functions."""
        logger.info("Starting cache warming...")
        
        tasks = []
        for func, args_list in self.warming_functions:
            for args in args_list:
                if asyncio.iscoroutinefunction(func):
                    task = func(*args)
                else:
                    task = asyncio.get_event_loop().run_in_executor(
                        None, func, *args
                    )
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Cache warming completed: {success_count}/{len(tasks)} successful")

# Specialized caches for different components
class NormalizationCache:
    """Specialized cache for normalization operations."""
    
    def __init__(self, max_size: int = 10000):
        self.cache = lru_cache(maxsize=max_size)(self._normalize)
        self.stats = CacheStats()
    
    def _normalize(self, text: str, form: str, level: str) -> str:
        # This would be replaced with actual normalization
        return text
    
    def normalize(self, text: str, form: str = "NFC", level: str = "standard") -> str:
        """Cached normalization."""
        start_time = time.time()
        result = self.cache(text, form, level)
        self.stats.record_hit(time.time() - start_time)
        return result

class LigatureCache:
    """Specialized cache for ligature transformations."""
    
    def __init__(self, max_size: int = 50000):
        self.max_size = max_size
        self.word_cache = lru_cache(maxsize=max_size)(self._transform_word)
        self.pattern_cache = {}
        self.stats = CacheStats()
    
    def _transform_word(self, word: str, rules: tuple) -> str:
        # This would be replaced with actual transformation
        return word
    
    def transform(self, word: str, rules: Dict[str, str]) -> str:
        """Cached ligature transformation."""
        start_time = time.time()
        rules_tuple = tuple(sorted(rules.items()))
        result = self.word_cache(word, rules_tuple)
        self.stats.record_hit(time.time() - start_time)
        return result

# Performance monitoring
class CacheMonitor:
    """Monitors cache performance and provides insights."""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.start_time = time.time()
    
    def get_report(self) -> Dict[str, Any]:
        """Generate performance report."""
        stats = self.cache.get_stats()
        uptime = time.time() - self.start_time
        
        report = {
            'uptime_seconds': uptime,
            'cache_stats': stats,
            'performance': {
                'requests_per_second': stats['total_requests'] / uptime if uptime > 0 else 0,
                'avg_speedup': stats['avg_compute_time'] / stats['avg_cache_time'] if stats['avg_cache_time'] > 0 else 0,
                'time_saved_hours': stats['time_saved'] / 3600
            },
            'recommendations': self._generate_recommendations(stats)
        }
        
        return report
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate cache tuning recommendations."""
        recommendations = []
        
        if stats['hit_rate'] < 0.5:
            recommendations.append("Low hit rate - consider increasing cache size or TTL")
        
        if stats['evictions'] > stats['total_requests'] * 0.1:
            recommendations.append("High eviction rate - increase cache size")
        
        if stats['memory_size'] < 100 and stats['hit_rate'] < 0.8:
            recommendations.append("Low memory usage - can safely increase memory cache size")
        
        return recommendations

# Export main components
__all__ = [
    'MultiLevelCache',
    'cached',
    'get_cache',
    'CacheWarmer',
    'NormalizationCache',
    'LigatureCache',
    'CacheMonitor',
    'CacheStats'
]