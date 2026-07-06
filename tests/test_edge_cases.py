"""
Edge case tests for data_processor and new backend features.
Covers: unicode columns, single-row CSV, all-null columns,
outlier detection, data quality score, and the new session TTL endpoint.
"""

import io
import os
import pytest
from unittest.mock import patch

os.environ.setdefault("GROQ_API_KEY", "gsk-test-key")

from backend.modules import data_processor as dp
from backend.modules import session_store as store


# ── Shared fixtures ────────────────────────────────────────────────────────

_store: dict = {}

def _mock_new_session():
    import uuid
    sid = str(uuid.uuid4())
    _store[sid] = {}
    return sid

def _mock_exists(sid): return sid in _store
def _mock_set(sid, key, val): _store.setdefault(sid, {})[key] = val
def _mock_get(sid, key): return _store.get(sid, {}).get(key)
def _mock_delete(sid): _store.pop(sid, None)
def _mock_ttl(sid): return 3540  # 59 minutes


@pytest.fixture(autouse=True)
def patch_store():
    _store.clear()
    patches = [
        patch("backend.modules.session_store.new_session",   side_effect=_mock_new_session),
        patch("backend.modules.session_store.session_exists", side_effect=_mock_exists),
        patch("backend.modules.session_store.set_value",     side_effect=_mock_set),
        patch("backend.modules.session_store.get_value",     side_effect=_mock_get),
        patch("backend.modules.session_store.delete_session", side_effect=_mock_delete),
        patch("backend.modules.session_store.get_session_ttl", side_effect=_mock_ttl),
    ]
    for p in patches: p.start()
    yield
    for p in patches: p.stop()


# ── Unicode column names ────────────────────────────────────────────────────

class TestUnicodeColumns:
    def test_unicode_column_names_parsed(self):
        csv = "名前,年齢,スコア\nAlice,30,95.5\nBob,25,88.0\n".encode("utf-8")
        sid = store.new_session()
        meta = dp.load_csv(csv, "unicode.csv", sid)
        assert "名前" in meta["columns"]
        assert "年齢" in meta["columns"]
        assert meta["loaded_rows"] == 2

    def test_unicode_values_preserved(self):
        csv = "city,value\n東京,100\n大阪,200\n".encode("utf-8")
        sid = store.new_session()
        dp.load_csv(csv, "cities.csv", sid)
        preview = dp.get_preview(sid, n=5)
        cities = [r["city"] for r in preview]
        assert "東京" in cities
        assert "大阪" in cities


# ── Single-row CSV ─────────────────────────────────────────────────────────

class TestSingleRowCsv:
    def test_single_data_row_loads(self):
        csv = b"col_a,col_b,col_c\n1,hello,3.14\n"
        sid = store.new_session()
        meta = dp.load_csv(csv, "single.csv", sid)
        assert meta["loaded_rows"] == 1

    def test_single_row_summary_no_crash(self):
        csv = b"col_a,col_b\n42,test\n"
        sid = store.new_session()
        dp.load_csv(csv, "single.csv", sid)
        summary = dp.compute_summary(sid)
        assert summary["shape"]["rows"] == 1
        # Trends require >= 10 rows — should be empty
        assert summary["trends"] == []


# ── All-null column ────────────────────────────────────────────────────────

class TestAllNullColumn:
    def test_all_null_numeric_column_handled(self):
        csv = b"col_a,col_b\n,1\n,2\n,3\n,4\n"
        sid = store.new_session()
        dp.load_csv(csv, "nulls.csv", sid)
        summary = dp.compute_summary(sid)
        # col_a is all-null — stats should be None, not crash
        if "col_a" in summary["numeric_stats"]:
            assert summary["numeric_stats"]["col_a"]["mean"] is None

    def test_missing_overview_captures_null_cols(self):
        csv = b"a,b\n1,\n2,\n3,\n"
        sid = store.new_session()
        dp.load_csv(csv, "partial_nulls.csv", sid)
        summary = dp.compute_summary(sid)
        assert "b" in summary["missing_overview"]


# ── Outlier detection ──────────────────────────────────────────────────────

class TestOutlierDetection:
    def test_outliers_detected_with_extreme_values(self):
        # 10 normal values + 1 extreme outlier
        rows = "\n".join(f"1,{i}" for i in range(10))
        csv = f"idx,value\n{rows}\n1,99999\n".encode()
        sid = store.new_session()
        dp.load_csv(csv, "outliers.csv", sid)
        summary = dp.compute_summary(sid)
        assert "value" in summary["outliers"]
        assert summary["outliers"]["value"]["count"] >= 1

    def test_no_outliers_for_uniform_data(self):
        rows = "\n".join(f"1,{i}" for i in range(20))
        csv = f"idx,value\n{rows}\n".encode()
        sid = store.new_session()
        dp.load_csv(csv, "uniform.csv", sid)
        summary = dp.compute_summary(sid)
        assert "value" not in summary["outliers"]


# ── Data quality score ─────────────────────────────────────────────────────

class TestDataQualityScore:
    def test_clean_data_scores_high(self):
        rows = "\n".join(f"a,{i},{i*1.5}" for i in range(20))
        csv = f"cat,num1,num2\n{rows}\n".encode()
        sid = store.new_session()
        dp.load_csv(csv, "clean.csv", sid)
        summary = dp.compute_summary(sid)
        assert summary["data_quality_score"] > 50

    def test_data_quality_score_in_range(self):
        csv = b"a,b\n1,2\n3,4\n5,6\n"
        sid = store.new_session()
        dp.load_csv(csv, "simple.csv", sid)
        summary = dp.compute_summary(sid)
        score = summary["data_quality_score"]
        assert 0 <= score <= 100


# ── Session TTL endpoint ───────────────────────────────────────────────────

class TestSessionTtlEndpoint:
    @pytest.fixture
    def client(self):
        from backend.main import create_app
        from fastapi.testclient import TestClient
        return TestClient(create_app(), raise_server_exceptions=False)

    def test_session_status_returns_active_and_session_id(self, client):
        """Session status returns active=True for a known session."""
        # Inject a mock session directly via the autouse patch_store
        _store["test-session-123"] = {"filename": "test.csv"}

        with patch("backend.modules.session_store.get_session_ttl", return_value=3540):
            resp = client.get("/api/session/status", headers={"X-Session-Id": "test-session-123"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["active"] is True
        assert body["session_id"] == "test-session-123"
        assert body["ttl_seconds"] == 3540

    def test_session_status_invalid_session_returns_404(self, client):
        resp = client.get(
            "/api/session/status", headers={"X-Session-Id": "nonexistent-id"}
        )
        assert resp.status_code == 404
