"""
Tests for cache module — covers both memory and Redis paths.
"""
import sys, os
sys.path.insert(0, "/home/claude/autoinsight")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")

import json
import pytest
from unittest.mock import MagicMock, patch

SUMMARY_A = {"shape": {"rows": 100, "columns": 5}, "numeric_stats": {"sales": {"mean": 5000}}}
SUMMARY_B = {"shape": {"rows": 200, "columns": 3}, "numeric_stats": {"units": {"mean": 300}}}
VALUE_A    = {"insights": ["Revenue is stable"], "possible_reasons": [], "actionable_suggestions": []}


class TestMemoryCache:
    def setup_method(self):
        from backend.modules import cache
        cache._mem_cache.clear()

    def test_miss_returns_none(self):
        from backend.modules import cache
        assert cache.get("insights", SUMMARY_A) is None

    def test_set_then_get(self):
        from backend.modules import cache
        cache.set("insights", SUMMARY_A, VALUE_A)
        result = cache.get("insights", SUMMARY_A)
        assert result == VALUE_A

    def test_different_summary_is_miss(self):
        from backend.modules import cache
        cache.set("insights", SUMMARY_A, VALUE_A)
        assert cache.get("insights", SUMMARY_B) is None

    def test_different_prefix_is_miss(self):
        from backend.modules import cache
        cache.set("insights", SUMMARY_A, VALUE_A)
        assert cache.get("query", SUMMARY_A) is None

    def test_lru_eviction_at_256(self):
        from backend.modules import cache
        for i in range(256):
            cache.set("insights", {"shape": {"rows": i}}, {"insights": [str(i)]})
        assert len(cache._mem_cache) == 256
        # Adding one more should evict the oldest
        cache.set("insights", {"shape": {"rows": 9999}}, {"insights": ["new"]})
        assert len(cache._mem_cache) == 256

    def test_make_key_deterministic(self):
        from backend.modules.cache import _make_key
        k1 = _make_key("insights", SUMMARY_A)
        k2 = _make_key("insights", SUMMARY_A)
        assert k1 == k2

    def test_make_key_differs_by_prefix(self):
        from backend.modules.cache import _make_key
        assert _make_key("insights", SUMMARY_A) != _make_key("query", SUMMARY_A)


class TestRedisCache:
    def test_redis_set_and_get(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(VALUE_A)

        from backend.modules import cache
        # _redis_client being non-None is the Redis-enabled flag
        with patch.object(cache, "_redis_client", mock_redis):
            cache.set("insights", SUMMARY_A, VALUE_A)
            result = cache.get("insights", SUMMARY_A)

        mock_redis.setex.assert_called_once()
        assert result == VALUE_A

    def test_redis_miss_returns_none(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        from backend.modules import cache
        with patch.object(cache, "_redis_client", mock_redis):
            result = cache.get("insights", SUMMARY_A)

        assert result is None

    def test_redis_ttl_passed_to_setex(self):
        mock_redis = MagicMock()

        from backend.modules import cache
        with patch.object(cache, "_redis_client", mock_redis), \
             patch.object(cache, "_CACHE_TTL", 1800):
            cache.set("insights", SUMMARY_A, VALUE_A)

        args = mock_redis.setex.call_args[0]
        assert args[1] == 1800
