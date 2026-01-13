"""Caching layer for tool discovery.

Provides a simple in-memory cache with TTL (time-to-live) support
for caching tool lists and reducing MCP round trips.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with value and expiration."""

    value: T
    expires_at: float
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return time.time() > self.expires_at

    @property
    def age(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at

    @property
    def ttl_remaining(self) -> float:
        """Get remaining TTL in seconds (0 if expired)."""
        remaining = self.expires_at - time.time()
        return max(0, remaining)


class TTLCache(Generic[T]):
    """Thread-safe in-memory cache with TTL support.

    Features:
    - Configurable default TTL
    - Per-entry TTL override
    - Automatic expiration on access
    - Thread-safe operations

    Usage:
        cache = TTLCache[list[ToolInfo]](default_ttl=300)  # 5 minutes

        # Store with default TTL
        cache.set("tools:filesystem", tools)

        # Store with custom TTL
        cache.set("tools:github", tools, ttl=60)  # 1 minute

        # Get (returns None if expired or missing)
        tools = cache.get("tools:filesystem")

        # Check without removing
        if cache.has("tools:filesystem"):
            ...

        # Force invalidation
        cache.invalidate("tools:filesystem")
    """

    def __init__(self, default_ttl: float = 300.0):
        """Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (default 5 minutes)
        """
        self._default_ttl = default_ttl
        self._entries: dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()

    @property
    def default_ttl(self) -> float:
        """Get default TTL in seconds."""
        return self._default_ttl

    def get(self, key: str) -> T | None:
        """Get value from cache.

        Returns None if key is missing or expired.
        Expired entries are automatically removed.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                del self._entries[key]
                return None

            return entry.value

    def get_entry(self, key: str) -> CacheEntry[T] | None:
        """Get full cache entry with metadata.

        Returns None if key is missing or expired.

        Args:
            key: Cache key

        Returns:
            CacheEntry or None
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                del self._entries[key]
                return None

            return entry

    def set(self, key: str, value: T, ttl: float | None = None) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Optional TTL override in seconds
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + effective_ttl

        with self._lock:
            self._entries[key] = CacheEntry(
                value=value,
                expires_at=expires_at,
            )

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired.

        Args:
            key: Cache key

        Returns:
            True if valid entry exists
        """
        return self.get_entry(key) is not None

    def invalidate(self, key: str) -> bool:
        """Remove a specific key from cache.

        Args:
            key: Cache key to remove

        Returns:
            True if key was removed, False if not found
        """
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys matching a prefix.

        Args:
            prefix: Key prefix to match

        Returns:
            Number of entries removed
        """
        with self._lock:
            keys_to_remove = [k for k in self._entries if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._entries[key]
            return len(keys_to_remove)

    def clear(self) -> int:
        """Remove all entries from cache.

        Returns:
            Number of entries removed
        """
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            return count

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            now = time.time()
            expired = [k for k, v in self._entries.items() if v.expires_at < now]
            for key in expired:
                del self._entries[key]
            return len(expired)

    def keys(self) -> list[str]:
        """Get all non-expired keys.

        Returns:
            List of valid cache keys
        """
        with self._lock:
            self.cleanup_expired()
            return list(self._entries.keys())

    def size(self) -> int:
        """Get number of non-expired entries.

        Returns:
            Cache size
        """
        with self._lock:
            self.cleanup_expired()
            return len(self._entries)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with size, keys, and per-entry TTL remaining
        """
        with self._lock:
            self.cleanup_expired()
            return {
                "size": len(self._entries),
                "default_ttl": self._default_ttl,
                "entries": {
                    key: {
                        "ttl_remaining": entry.ttl_remaining,
                        "age": entry.age,
                    }
                    for key, entry in self._entries.items()
                },
            }
