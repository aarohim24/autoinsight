"""
Integration tests for FastAPI routes.
Uses httpx.AsyncClient with the ASGI app directly — no server needed.
Mocks session store and LLM calls.
"""

import io
import json
import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("GROQ_API_KEY", "gsk-test-key")

# In-memory mock store
_store: dict = {}

def _mock_new_session():
    import uuid
    sid = str(uuid.uuid4())
    _store[sid] = {}
    return sid

def _mock_exists(sid):
    return sid in _store

def _mock_set(sid, key, val):
    _store.setdefault(sid, {})[key] = val

def _mock_get(sid, key):
    return _store.get(sid, {}).get(key)

def _mock_delete(sid):
    _store.pop(sid, None)


SAMPLE_CSV = b"""date,region,sales,units
2023-01-01,North,10000,500
2023-01-02,South,9000,450
2023-01-03,East,8000,400
"""

VALID_INSIGHTS = {
    "insights": ["Sales are healthy"],
    "possible_reasons": ["Good market"],
    "actionable_suggestions": ["Keep going"],
}


@pytest.fixture(autouse=True)
def patch_store():
    _store.clear()
    patches = [
        patch("backend.modules.session_store.new_session",   side_effect=_mock_new_session),
        patch("backend.modules.session_store.session_exists", side_effect=_mock_exists),
        patch("backend.modules.session_store.set_value",     side_effect=_mock_set),
        patch("backend.modules.session_store.get_value",     side_effect=_mock_get),
        patch("backend.modules.session_store.delete_session", side_effect=_mock_delete),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture
def app():
    from backend.main import create_app
    return create_app()


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app, raise_server_exceptions=False)


# ── Upload tests ───────────────────────────────────────────────────────────

class TestUpload:
    def test_valid_upload(self, client):
        resp = client.post("/api/upload-data",
                           files={"file": ("data.csv", SAMPLE_CSV, "text/csv")})
        assert resp.status_code == 201
        body = resp.json()
        assert "session_id" in body
        assert body["loaded_rows"] == 3

    def test_non_csv_rejected(self, client):
        resp = client.post("/api/upload-data",
                           files={"file": ("data.json", b'{"a":1}', "application/json")})
        assert resp.status_code in (400, 415)

    def test_empty_file_rejected(self, client):
        resp = client.post("/api/upload-data",
                           files={"file": ("empty.csv", b"", "text/csv")})
        assert resp.status_code == 400

    def test_file_too_large_rejected(self, client):
        # Generate content > 50 MB by patching the size check in data_processor
        with patch("backend.modules.data_processor.MAX_FILE_BYTES", 100):
            resp = client.post("/api/upload-data",
                               files={"file": ("big.csv", b"a,b\n" + b"1,2\n" * 50, "text/csv")})
        assert resp.status_code in (413, 422)


# ── Analyze tests ──────────────────────────────────────────────────────────

class TestAnalyze:
    def _upload_and_get_session(self, client) -> str:
        resp = client.post("/api/upload-data",
                           files={"file": ("data.csv", SAMPLE_CSV, "text/csv")})
        assert resp.status_code == 201
        return resp.json()["session_id"]

    def test_analyze_returns_summary(self, client):
        sid = self._upload_and_get_session(client)
        resp = client.get("/api/analyze", headers={"X-Session-Id": sid})
        assert resp.status_code == 200
        body = resp.json()
        assert "summary" in body
        assert "preview" in body
        assert body["summary"]["shape"]["rows"] == 3

    def test_analyze_without_session_fails(self, client):
        resp = client.get("/api/analyze", headers={"X-Session-Id": "nonexistent"})
        assert resp.status_code == 404

    def test_analyze_missing_header_fails(self, client):
        resp = client.get("/api/analyze")
        assert resp.status_code == 422


# ── Insights tests ─────────────────────────────────────────────────────────

class TestInsights:
    def _upload_and_get_session(self, client) -> str:
        resp = client.post("/api/upload-data",
                           files={"file": ("data.csv", SAMPLE_CSV, "text/csv")})
        return resp.json()["session_id"]

    def test_insights_returns_structured_data(self, client):
        sid = self._upload_and_get_session(client)
        with patch("backend.modules.llm_engine.generate_insights",
                   new=AsyncMock(return_value=VALID_INSIGHTS)), \
             patch("backend.modules.cache.get", return_value=None), \
             patch("backend.modules.cache.set"):
            resp = client.post("/api/generate-insights", headers={"X-Session-Id": sid})
        assert resp.status_code == 200
        body = resp.json()
        assert "insights" in body
        assert "possible_reasons" in body
        assert "actionable_suggestions" in body

    def test_insights_served_from_cache(self, client):
        sid = self._upload_and_get_session(client)
        cached = {**VALID_INSIGHTS}
        with patch("backend.modules.cache.get", return_value=cached):
            resp = client.post("/api/generate-insights", headers={"X-Session-Id": sid})
        assert resp.status_code == 200
        assert resp.json().get("_cached") is True


# ── Query tests ────────────────────────────────────────────────────────────

class TestQuery:
    def _upload_and_get_session(self, client) -> str:
        resp = client.post("/api/upload-data",
                           files={"file": ("data.csv", SAMPLE_CSV, "text/csv")})
        return resp.json()["session_id"]

    def test_valid_query(self, client):
        sid = self._upload_and_get_session(client)
        mock_answer = {"answer": "Sales look healthy.", "confidence": "high", "caveat": ""}
        with patch("backend.modules.llm_engine.answer_nl_query",
                   new=AsyncMock(return_value=mock_answer)):
            resp = client.post("/api/query",
                               json={"question": "How are sales?"},
                               headers={"X-Session-Id": sid})
        assert resp.status_code == 200
        assert resp.json()["answer"] == "Sales look healthy."

    def test_empty_question_rejected(self, client):
        sid = self._upload_and_get_session(client)
        resp = client.post("/api/query",
                           json={"question": "  "},
                           headers={"X-Session-Id": sid})
        assert resp.status_code == 422

    def test_question_too_long_rejected(self, client):
        sid = self._upload_and_get_session(client)
        resp = client.post("/api/query",
                           json={"question": "x" * 501},
                           headers={"X-Session-Id": sid})
        assert resp.status_code == 422


# ── Health check ───────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
