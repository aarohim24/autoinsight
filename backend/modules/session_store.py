"""
Session Store for AutoInsight
Uses Redis when available, falls back to in-process dict (dev/single-worker only).
Each upload gets a unique session_id; all subsequent calls must pass it.

Redis connection is established lazily on first use to avoid crashing app
startup when Redis is temporarily unavailable.
"""

import json
import os
import uuid
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

_SESSION_TTL = int(os.environ.get("SESSION_TTL_SECONDS", 3600))  # 1 hour default

# -- In-memory fallback (single-process only) ---------------------------------
_mem: dict[str, dict[str, Any]] = {}

# -- Lazy Redis client --------------------------------------------------------
_redis_client = None
_redis_checked = False


def _get_redis():
    """Return a connected Redis client, or None if Redis is unavailable."""
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
        logger.info("session_store_backend", backend="redis", url=_redis_url)
    except Exception as exc:
        _redis_client = None
        logger.warning("session_store_backend", backend="memory", reason=str(exc))
    return _redis_client


# -- Public API ---------------------------------------------------------------

def new_session() -> str:
    """Create and return a fresh session ID."""
    sid = str(uuid.uuid4())
    r = _get_redis()
    if r:
        r.setex(f"session:{sid}", _SESSION_TTL, "{}")
    else:
        _mem[sid] = {}
    logger.info("session_created", session_id=sid)
    return sid


def set_value(session_id: str, key: str, value: Any) -> None:
    r = _get_redis()
    if r:
        raw = r.get(f"session:{session_id}") or "{}"
        data = json.loads(raw)
        data[key] = value
        r.setex(f"session:{session_id}", _SESSION_TTL, json.dumps(data))
    else:
        if session_id not in _mem:
            raise KeyError(f"Session {session_id} not found")
        _mem[session_id][key] = value


def get_value(session_id: str, key: str) -> Any:
    r = _get_redis()
    if r:
        raw = r.get(f"session:{session_id}")
        if raw is None:
            raise KeyError(f"Session {session_id} expired or not found")
        return json.loads(raw).get(key)
    else:
        if session_id not in _mem:
            raise KeyError(f"Session {session_id} not found")
        return _mem[session_id].get(key)


def session_exists(session_id: str) -> bool:
    r = _get_redis()
    if r:
        return bool(r.exists(f"session:{session_id}"))
    return session_id in _mem


def delete_session(session_id: str) -> None:
    r = _get_redis()
    if r:
        r.delete(f"session:{session_id}")
    else:
        _mem.pop(session_id, None)
    logger.info("session_deleted", session_id=session_id)


def get_session_ttl(session_id: str) -> Optional[int]:
    """Return remaining TTL in seconds, or None if not using Redis / not found."""
    r = _get_redis()
    if r:
        ttl = r.ttl(f"session:{session_id}")
        return ttl if ttl > 0 else None
    return None
