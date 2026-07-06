"""
Tests for session_store — covers memory path and mocked Redis path.
"""
import os
os.environ.setdefault("GROQ_API_KEY", "gsk-test-key")

import json
import pytest
from unittest.mock import MagicMock, patch


class TestMemorySessionStore:
    def setup_method(self):
        from backend.modules import session_store
        # Ensure lazy Redis check returns None (memory mode)
        session_store._redis_client = None
        session_store._redis_checked = True
        session_store._mem.clear()

    def test_new_session_returns_uuid(self):
        from backend.modules import session_store
        sid = session_store.new_session()
        assert len(sid) == 36  # UUID4 format

    def test_session_exists_after_creation(self):
        from backend.modules import session_store
        sid = session_store.new_session()
        assert session_store.session_exists(sid) is True

    def test_nonexistent_session_not_found(self):
        from backend.modules import session_store
        assert session_store.session_exists("fake-id") is False

    def test_set_and_get_value(self):
        from backend.modules import session_store
        sid = session_store.new_session()
        session_store.set_value(sid, "filename", "sales.csv")
        assert session_store.get_value(sid, "filename") == "sales.csv"

    def test_get_missing_key_returns_none(self):
        from backend.modules import session_store
        sid = session_store.new_session()
        assert session_store.get_value(sid, "nonexistent") is None

    def test_set_on_missing_session_raises(self):
        from backend.modules import session_store
        with pytest.raises(KeyError):
            session_store.set_value("bad-session", "key", "value")

    def test_delete_session(self):
        from backend.modules import session_store
        sid = session_store.new_session()
        session_store.delete_session(sid)
        assert session_store.session_exists(sid) is False

    def test_delete_nonexistent_session_safe(self):
        from backend.modules import session_store
        session_store.delete_session("does-not-exist")  # should not raise

    def test_multiple_sessions_isolated(self):
        from backend.modules import session_store
        sid1 = session_store.new_session()
        sid2 = session_store.new_session()
        session_store.set_value(sid1, "filename", "a.csv")
        session_store.set_value(sid2, "filename", "b.csv")
        assert session_store.get_value(sid1, "filename") == "a.csv"
        assert session_store.get_value(sid2, "filename") == "b.csv"


class TestRedisSessionStore:
    def _make_redis_mock(self, store: dict):
        mock = MagicMock()
        mock.ping.return_value = True
        mock.exists.side_effect   = lambda k: int(k in store)
        mock.get.side_effect      = lambda k: store.get(k)
        mock.setex.side_effect    = lambda k, ttl, v: store.update({k: v})
        mock.delete.side_effect   = lambda k: store.pop(k, None)
        return mock

    def test_redis_new_session(self):
        redis_store = {}
        mock_redis = self._make_redis_mock(redis_store)
        from backend.modules import session_store
        with patch.object(session_store, "_get_redis", return_value=mock_redis):
            sid = session_store.new_session()
        assert f"session:{sid}" in redis_store

    def test_redis_set_and_get(self):
        redis_store = {}
        mock_redis = self._make_redis_mock(redis_store)
        from backend.modules import session_store
        with patch.object(session_store, "_get_redis", return_value=mock_redis):
            sid = session_store.new_session()
            session_store.set_value(sid, "filename", "test.csv")
            result = session_store.get_value(sid, "filename")
        assert result == "test.csv"

    def test_redis_expired_session_raises(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # simulates expired key
        from backend.modules import session_store
        with patch.object(session_store, "_get_redis", return_value=mock_redis):
            with pytest.raises(KeyError, match="expired or not found"):
                session_store.get_value("expired-sid", "filename")
