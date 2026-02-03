"""
Performance Manager for FLOOSE
General-purpose caching and performance monitoring
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
from threading import Lock
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    timestamp: datetime
    key_hash: str
    access_count: int = 0
    last_access: datetime = None


class QueryCache:
    """In-memory cache for query results with TTL-based expiration"""

    def __init__(self, max_size: int = 500, ttl_minutes: int = 5):
        """
        Initialize query cache

        Args:
            max_size: Maximum number of cache entries
            ttl_minutes: Time-to-live for entries in minutes
        """
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() - entry.timestamp > self.ttl

    def _evict_oldest(self):
        """Evict least recently used entry"""
        if not self.cache:
            return

        oldest_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].last_access or self.cache[k].timestamp
        )

        del self.cache[oldest_key]
        self.evictions += 1

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not self._is_expired(entry):
                    entry.access_count += 1
                    entry.last_access = datetime.now()
                    self.hits += 1
                    return entry.data
                else:
                    del self.cache[key]

            self.misses += 1
            return None

    def set(self, key: str, data: Any):
        """Store value in cache"""
        with self.lock:
            if len(self.cache) >= self.max_size:
                self._evict_oldest()

            self.cache[key] = CacheEntry(
                data=data,
                timestamp=datetime.now(),
                key_hash=key,
                last_access=datetime.now()
            )

    def invalidate(self, key: str = None):
        """Invalidate specific key or entire cache"""
        with self.lock:
            if key:
                self.cache.pop(key, None)
            else:
                self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': (self.hits / total * 100) if total > 0 else 0,
            'evictions': self.evictions
        }


class PerformanceManager:
    """Performance monitoring and caching manager"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self.logger = logging.getLogger(__name__)
        self.query_cache = QueryCache(max_size=500, ttl_minutes=5)

        # Performance timings
        self._timings: Dict[str, list] = {}
        self._timing_lock = Lock()

        self._initialized = True
        self.logger.info("PerformanceManager initialized")

    def cache_query(self, key: str, loader: Callable[[], Any]) -> Any:
        """
        Get cached query result or execute and cache

        Args:
            key: Cache key
            loader: Function to load data if not cached

        Returns:
            Cached or freshly loaded data
        """
        cached = self.query_cache.get(key)
        if cached is not None:
            return cached

        data = loader()
        self.query_cache.set(key, data)
        return data

    def invalidate_cache(self, key: str = None):
        """Invalidate cache entries"""
        self.query_cache.invalidate(key)

    def time_operation(self, name: str):
        """
        Context manager for timing operations

        Usage:
            with perf.time_operation('query_projects'):
                # do work
        """
        return OperationTimer(self, name)

    def record_timing(self, name: str, duration: float):
        """Record a timing measurement"""
        with self._timing_lock:
            if name not in self._timings:
                self._timings[name] = []
            self._timings[name].append(duration)
            # Keep only last 100 measurements
            if len(self._timings[name]) > 100:
                self._timings[name] = self._timings[name][-100:]

    def get_timing_stats(self, name: str = None) -> Dict[str, Any]:
        """Get timing statistics"""
        with self._timing_lock:
            if name:
                timings = self._timings.get(name, [])
                if not timings:
                    return {}
                return {
                    'name': name,
                    'count': len(timings),
                    'avg_ms': sum(timings) / len(timings) * 1000,
                    'min_ms': min(timings) * 1000,
                    'max_ms': max(timings) * 1000
                }

            return {
                op: {
                    'count': len(times),
                    'avg_ms': sum(times) / len(times) * 1000 if times else 0,
                    'min_ms': min(times) * 1000 if times else 0,
                    'max_ms': max(times) * 1000 if times else 0
                }
                for op, times in self._timings.items()
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get all performance statistics"""
        return {
            'cache': self.query_cache.get_stats(),
            'timings': self.get_timing_stats()
        }


class OperationTimer:
    """Context manager for timing operations"""

    def __init__(self, manager: PerformanceManager, name: str):
        self.manager = manager
        self.name = name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        self.manager.record_timing(self.name, duration)
        return False


def performance_monitor(operation_name: str = None):
    """
    Decorator for monitoring function performance

    Args:
        operation_name: Name for the operation (defaults to function name)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            perf = get_performance_manager()

            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                perf.record_timing(name, duration)

        return wrapper
    return decorator


# Singleton instance
_perf_manager: PerformanceManager = None


def get_performance_manager() -> PerformanceManager:
    """Get the global PerformanceManager instance"""
    global _perf_manager
    if _perf_manager is None:
        _perf_manager = PerformanceManager()
    return _perf_manager
