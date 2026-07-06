"""
Insight Cache for AutoInsight
Caches LLM responses keyed on a hash of the dataset summary.
Uses Redis TTL when available, in-memory LRU otherwise.
"""

import hashlib
import json
import os
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

_CACHE_TTL = int(os.environ.get("CACHE_TTL_SECONDS", 3600))

# -- Lazy Redis client (reuses the same helper as session_store) --------------
_redis_client = None
_redis_checked = False


def _get_redis():
    """Return a connected Redis client, or None if unavailable."""
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        import redis as redis_lib

        _redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        pool = redis_lib.ConnectionPool.from_url(
            _redis_url, decode_responses=True, socket_connect_timeout=2
        )
        r = redis_lib.Redis(connection_pool=pool)
        r.ping()
        _redis_client = r
        logger.info("cache_backend", backend="redis")
    except Exception:
        _redis_client = None
        logger.info("cache_backend", backend="memory_lru")
    return _redis_client


# -- In-memory fallback -------------------------------------------------------
_mem_cache: dict[str, Any] = {}


def _make_key(prefix: str, summary: dict) -> str:
    canonical = json.dumps(summary, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:24]
    return f"cache:{prefix}:{digest}"


def get(prefix: str, summary: dict) -> Optional[dict]:
    key = _make_key(prefix, summary)
    r = _get_redis()
    if r:
        raw = r.get(key)
        if raw:
            logger.info("cache_hit", prefix=prefix, key=key)
            return json.loads(raw)
    else:
        if key in _mem_cache:
            logger.info("cache_hit", prefix=prefix, key=key)
            return _mem_cache[key]
    return None


def set(prefix: str, summary: dict, value: dict) -> None:
    key = _make_key(prefix, summary)
    r = _get_redis()
    if r:
        r.setex(key, _CACHE_TTL, json.dumps(value))
    else:
        # Simple bounded LRU: evict oldest if over 256 entries
        if len(_mem_cache) >= 256:
            oldest = next(iter(_mem_cache))
            del _mem_cache[oldest]
        _mem_cache[key] = value
    logger.info("cache_set", prefix=prefix, key=key, ttl=_CACHE_TTL)


def clear() -> None:
    """Clear the in-memory cache. Used for test isolation."""
    _mem_cache.clear()
