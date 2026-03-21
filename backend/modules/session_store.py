"""
Session Store for AutoInsight
Uses Redis when available, falls back to in-process dict (dev/single-worker only).
Each upload gets a unique session_id; all subsequent calls must pass it.
"""

import json
import os
import uuid
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_USE_REDIS = False
_redis_client = None

# -- Try to connect to Redis --------------------------------------------------
try:
    import redis as redis_lib

    _redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    _r = redis_lib.from_url(_redis_url, decode_responses=True, socket_connect_timeout=2)
    _r.ping()
    _redis_client = _r
    _USE_REDIS = True
    logger.info("session_store_backend", backend="redis", url=_redis_url)
except Exception as exc:
    logger.warning("session_store_backend", backend="memory", reason=str(exc))

# -- In-memory fallback (single-process only) ---------------------------------
_mem: dict[str, dict[str, Any]] = {}
_SESSION_TTL = int(os.environ.get("SESSION_TTL_SECONDS", 3600))  # 1 hour default


# -- Public API ---------------------------------------------------------------

def new_session() -> str:
    """Create and return a fresh session ID."""
    sid = str(uuid.uuid4())
    if _USE_REDIS:
        _redis_client.setex(f"session:{sid}", _SESSION_TTL, "{}")
    else:
        _mem[sid] = {}
    logger.info("session_created", session_id=sid)
    return sid


def set_value(session_id: str, key: str, value: Any) -> None:
    if _USE_REDIS:
        raw = _redis_client.get(f"session:{session_id}") or "{}"
        data = json.loads(raw)
        data[key] = value
        _redis_client.setex(f"session:{session_id}", _SESSION_TTL, json.dumps(data))
    else:
        if session_id not in _mem:
            raise KeyError(f"Session {session_id} not found")
        _mem[session_id][key] = value


def get_value(session_id: str, key: str) -> Any:
    if _USE_REDIS:
        raw = _redis_client.get(f"session:{session_id}")
        if raw is None:
            raise KeyError(f"Session {session_id} expired or not found")
        return json.loads(raw).get(key)
    else:
        if session_id not in _mem:
            raise KeyError(f"Session {session_id} not found")
        return _mem[session_id].get(key)


def session_exists(session_id: str) -> bool:
    if _USE_REDIS:
        return bool(_redis_client.exists(f"session:{session_id}"))
    return session_id in _mem


def delete_session(session_id: str) -> None:
    if _USE_REDIS:
        _redis_client.delete(f"session:{session_id}")
    else:
        _mem.pop(session_id, None)
    logger.info("session_deleted", session_id=session_id)
