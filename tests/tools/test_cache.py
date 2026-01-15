"""Tests for TTLCache implementation."""

from __future__ import annotations

import threading
import time
from typing import Optional

import pytest

from ralph_agi.tools.cache import CacheEntry, TTLCache


# =============================================================================
# CacheEntry Tests
# =============================================================================


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            value="test_value",
            expires_at=time.time() + 100,
        )

        assert entry.value == "test_value"
        assert not entry.is_expired()
        assert entry.ttl_remaining > 99

    def test_entry_expired(self):
        """Test expired entry detection."""
        entry = CacheEntry(
            value="expired",
            expires_at=time.time() - 1,  # Already expired
        )

        assert entry.is_expired()
        assert entry.ttl_remaining == 0

    def test_entry_age(self):
        """Test entry age calculation."""
        entry = CacheEntry(
            value="test",
            expires_at=time.time() + 100,
        )

        # Age should be very small (just created)
        assert entry.age < 0.1

        # Wait a bit
        time.sleep(0.1)
        assert entry.age >= 0.1

    def test_entry_ttl_remaining(self):
        """Test TTL remaining calculation."""
        ttl = 10
        entry = CacheEntry(
            value="test",
            expires_at=time.time() + ttl,
        )

        remaining = entry.ttl_remaining
        assert 9 < remaining <= 10

    def test_entry_ttl_remaining_expired(self):
        """Test TTL remaining for expired entry."""
        entry = CacheEntry(
            value="test",
            expires_at=time.time() - 5,  # Expired 5 seconds ago
        )

        assert entry.ttl_remaining == 0


# =============================================================================
# TTLCache Basic Tests
# =============================================================================


class TestTTLCacheBasic:
    """Basic tests for TTLCache."""

    def test_cache_init_default_ttl(self):
        """Test cache initialization with default TTL."""
        cache = TTLCache[str]()

        assert cache.default_ttl == 300.0  # 5 minutes
        assert cache.size() == 0

    def test_cache_init_custom_ttl(self):
        """Test cache initialization with custom TTL."""
        cache = TTLCache[str](default_ttl=60.0)

        assert cache.default_ttl == 60.0

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_get_missing_key(self):
        """Test getting a missing key."""
        cache = TTLCache[str]()

        result = cache.get("nonexistent")

        assert result is None

    def test_has_existing_key(self):
        """Test has() for existing key."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("key", "value")

        assert cache.has("key") is True

    def test_has_missing_key(self):
        """Test has() for missing key."""
        cache = TTLCache[str]()

        assert cache.has("nonexistent") is False

    def test_size(self):
        """Test cache size."""
        cache = TTLCache[int](default_ttl=100)

        assert cache.size() == 0

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        assert cache.size() == 3

    def test_keys(self):
        """Test getting cache keys."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        keys = cache.keys()

        assert set(keys) == {"key1", "key2"}


# =============================================================================
# TTLCache TTL Tests
# =============================================================================


class TestTTLCacheExpiration:
    """Tests for cache TTL expiration."""

    def test_get_expired_returns_none(self):
        """Test that getting expired key returns None."""
        cache = TTLCache[str](default_ttl=0.1)  # 100ms TTL

        cache.set("key", "value")

        # Should exist initially
        assert cache.get("key") == "value"

        # Wait for expiration
        time.sleep(0.15)

        # Should be None after expiration
        assert cache.get("key") is None

    def test_expired_entry_removed_on_access(self):
        """Test that expired entries are removed on access."""
        cache = TTLCache[str](default_ttl=0.1)

        cache.set("key", "value")
        time.sleep(0.15)

        # Access triggers removal
        cache.get("key")

        assert cache.size() == 0

    def test_has_expired_key(self):
        """Test has() for expired key."""
        cache = TTLCache[str](default_ttl=0.1)

        cache.set("key", "value")
        time.sleep(0.15)

        assert cache.has("key") is False

    def test_custom_ttl_override(self):
        """Test per-entry TTL override."""
        cache = TTLCache[str](default_ttl=10)

        # Use shorter TTL for this entry
        cache.set("short", "value", ttl=0.1)

        time.sleep(0.15)

        assert cache.get("short") is None

    def test_longer_ttl_override(self):
        """Test longer TTL override."""
        cache = TTLCache[str](default_ttl=0.1)

        # Use longer TTL for this entry
        cache.set("long", "value", ttl=10)

        time.sleep(0.15)

        # Should still exist
        assert cache.get("long") == "value"

    def test_cleanup_expired(self):
        """Test cleanup_expired() removes all expired entries."""
        cache = TTLCache[str](default_ttl=0.1)

        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3", ttl=10)  # This one stays

        time.sleep(0.15)

        removed = cache.cleanup_expired()

        assert removed == 2
        assert cache.size() == 1
        assert cache.get("c") == "3"


# =============================================================================
# TTLCache Invalidation Tests
# =============================================================================


class TestTTLCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_existing(self):
        """Test invalidating existing key."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("key", "value")
        result = cache.invalidate("key")

        assert result is True
        assert cache.get("key") is None

    def test_invalidate_missing(self):
        """Test invalidating missing key."""
        cache = TTLCache[str]()

        result = cache.invalidate("nonexistent")

        assert result is False

    def test_invalidate_prefix(self):
        """Test invalidating by prefix."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("tools:fs", "1")
        cache.set("tools:git", "2")
        cache.set("schemas:fs", "3")

        removed = cache.invalidate_prefix("tools:")

        assert removed == 2
        assert cache.has("tools:fs") is False
        assert cache.has("tools:git") is False
        assert cache.has("schemas:fs") is True

    def test_invalidate_prefix_empty(self):
        """Test invalidating prefix with no matches."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("key", "value")
        removed = cache.invalidate_prefix("nomatch:")

        assert removed == 0
        assert cache.size() == 1

    def test_clear(self):
        """Test clearing entire cache."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")

        removed = cache.clear()

        assert removed == 3
        assert cache.size() == 0


# =============================================================================
# TTLCache Entry Access Tests
# =============================================================================


class TestTTLCacheEntryAccess:
    """Tests for accessing full cache entries."""

    def test_get_entry(self):
        """Test getting full cache entry."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("key", "value")
        entry = cache.get_entry("key")

        assert entry is not None
        assert entry.value == "value"
        assert entry.ttl_remaining > 99

    def test_get_entry_missing(self):
        """Test get_entry for missing key."""
        cache = TTLCache[str]()

        entry = cache.get_entry("nonexistent")

        assert entry is None

    def test_get_entry_expired(self):
        """Test get_entry for expired key."""
        cache = TTLCache[str](default_ttl=0.1)

        cache.set("key", "value")
        time.sleep(0.15)

        entry = cache.get_entry("key")

        assert entry is None


# =============================================================================
# TTLCache Stats Tests
# =============================================================================


class TestTTLCacheStats:
    """Tests for cache statistics."""

    def test_stats_empty_cache(self):
        """Test stats on empty cache."""
        cache = TTLCache[str](default_ttl=60)

        stats = cache.stats()

        assert stats["size"] == 0
        assert stats["default_ttl"] == 60
        assert stats["entries"] == {}

    def test_stats_with_entries(self):
        """Test stats with entries."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.stats()

        assert stats["size"] == 2
        assert "key1" in stats["entries"]
        assert "key2" in stats["entries"]
        assert stats["entries"]["key1"]["ttl_remaining"] > 99

    def test_stats_excludes_expired(self):
        """Test stats excludes expired entries."""
        cache = TTLCache[str](default_ttl=0.1)

        cache.set("expired", "value")
        cache.set("valid", "value", ttl=100)

        time.sleep(0.15)

        stats = cache.stats()

        assert stats["size"] == 1
        assert "valid" in stats["entries"]
        assert "expired" not in stats["entries"]


# =============================================================================
# TTLCache Thread Safety Tests
# =============================================================================


class TestTTLCacheThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_writes(self):
        """Test concurrent write operations."""
        cache = TTLCache[int](default_ttl=100)
        errors: list[Exception] = []

        def writer(start: int):
            try:
                for i in range(100):
                    cache.set(f"key_{start + i}", start + i)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(i * 100,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cache.size() == 500

    def test_concurrent_reads(self):
        """Test concurrent read operations."""
        cache = TTLCache[int](default_ttl=100)

        # Populate cache
        for i in range(100):
            cache.set(f"key_{i}", i)

        errors: list[Exception] = []
        results: list[int] = []

        def reader():
            try:
                for i in range(100):
                    val = cache.get(f"key_{i}")
                    if val is not None:
                        results.append(val)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 1000

    def test_concurrent_mixed_operations(self):
        """Test concurrent mixed read/write/invalidate."""
        cache = TTLCache[int](default_ttl=100)
        errors: list[Exception] = []

        def worker(worker_id: int):
            try:
                for i in range(50):
                    key = f"key_{worker_id}_{i}"
                    cache.set(key, i)
                    cache.get(key)
                    if i % 5 == 0:
                        cache.invalidate(key)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(i,))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# =============================================================================
# TTLCache Type Tests
# =============================================================================


class TestTTLCacheTypes:
    """Tests for different value types."""

    def test_cache_list(self):
        """Test caching list values."""
        cache = TTLCache[list[str]](default_ttl=100)

        cache.set("tools", ["read", "write", "delete"])
        result = cache.get("tools")

        assert result == ["read", "write", "delete"]

    def test_cache_dict(self):
        """Test caching dict values."""
        cache = TTLCache[dict[str, int]](default_ttl=100)

        cache.set("counts", {"a": 1, "b": 2})
        result = cache.get("counts")

        assert result == {"a": 1, "b": 2}

    def test_cache_none_value(self):
        """Test caching None as a value (different from missing)."""
        cache = TTLCache[Optional[str]](default_ttl=100)

        cache.set("nullable", None)

        # None value is valid
        assert cache.has("nullable") is True
        assert cache.get("nullable") is None

    def test_cache_complex_objects(self):
        """Test caching complex nested objects."""
        cache = TTLCache[dict](default_ttl=100)

        complex_value = {
            "tools": [
                {"name": "read", "args": ["path"]},
                {"name": "write", "args": ["path", "content"]},
            ],
            "version": 1,
        }

        cache.set("complex", complex_value)
        result = cache.get("complex")

        assert result == complex_value
        assert result["tools"][0]["name"] == "read"


# =============================================================================
# Edge Cases
# =============================================================================


class TestTTLCacheEdgeCases:
    """Tests for edge cases."""

    def test_overwrite_existing_key(self):
        """Test overwriting an existing key."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("key", "value1")
        cache.set("key", "value2")

        assert cache.get("key") == "value2"
        assert cache.size() == 1

    def test_empty_string_key(self):
        """Test empty string as key."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("", "empty_key_value")

        assert cache.get("") == "empty_key_value"

    def test_unicode_keys(self):
        """Test Unicode keys."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("键", "value1")
        cache.set("🔑", "value2")

        assert cache.get("键") == "value1"
        assert cache.get("🔑") == "value2"

    def test_very_short_ttl(self):
        """Test very short TTL."""
        cache = TTLCache[str](default_ttl=0.01)  # 10ms

        cache.set("quick", "value")
        time.sleep(0.02)

        assert cache.get("quick") is None

    def test_zero_ttl_immediate_expiration(self):
        """Test zero TTL expires immediately."""
        cache = TTLCache[str](default_ttl=100)

        cache.set("instant", "value", ttl=0)

        # Even with ttl=0, the entry might still be valid for a tiny moment
        # Let's just check it expires quickly
        time.sleep(0.01)
        assert cache.get("instant") is None
