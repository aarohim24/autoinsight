"""
Unit tests for data_processor module.
Uses a mock session store to avoid Redis dependency.
"""

import io
import json
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Patch session store before importing data_processor
import sys
sys.path.insert(0, "/home/claude/autoinsight")

mock_store: dict = {}

def _mock_set(session_id, key, value):
    mock_store.setdefault(session_id, {})[key] = value

def _mock_get(session_id, key):
    return mock_store.get(session_id, {}).get(key)

with patch("backend.modules.session_store.set_value", side_effect=_mock_set), \
     patch("backend.modules.session_store.get_value", side_effect=_mock_get):
    from backend.modules import data_processor as dp


SESSION = "test-session-001"
SAMPLE_CSV = b"""date,region,sales,units,discount,satisfaction
2023-01-01,North,10000,500,0.1,4.5
2023-01-02,South,9000,450,0.2,4.2
2023-01-03,East,8000,400,0.3,3.9
2023-01-04,West,7000,350,0.4,3.6
2023-01-05,North,6000,300,0.35,3.3
"""


class TestLoadCSV:
    def setup_method(self):
        mock_store.clear()

    def test_basic_load(self):
        with patch("backend.modules.session_store.set_value", side_effect=_mock_set), \
             patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            meta = dp.load_csv(SAMPLE_CSV, "test.csv", SESSION)
        assert meta["loaded_rows"] == 5
        assert meta["original_rows"] == 5
        assert "sales" in meta["columns"]
        assert meta["session_id"] == SESSION

    def test_file_too_large(self):
        big = b"a" * (51 * 1024 * 1024)
        with pytest.raises(ValueError, match="too large"):
            dp.load_csv(big, "big.csv", SESSION)

    def test_empty_csv(self):
        with pytest.raises(ValueError, match="empty"):
            dp.load_csv(b"col1,col2\n", "empty.csv", SESSION)

    def test_malformed_csv(self):
        with pytest.raises(ValueError):
            dp.load_csv(b"\x00\x01\x02binary\x00\x00", "bad.csv", SESSION)

    def test_large_csv_sampled(self):
        rows = "a,b\n" + "\n".join(f"{i},{i*2}" for i in range(15_000))
        with patch("backend.modules.session_store.set_value", side_effect=_mock_set), \
             patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            meta = dp.load_csv(rows.encode(), "large.csv", SESSION)
        assert meta["loaded_rows"] == 10_000
        assert meta["original_rows"] == 15_000
        assert meta["sampled"] is True


class TestComputeSummary:
    def setup_method(self):
        mock_store.clear()
        with patch("backend.modules.session_store.set_value", side_effect=_mock_set), \
             patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            dp.load_csv(SAMPLE_CSV, "test.csv", SESSION)

    def test_shape(self):
        with patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            s = dp.compute_summary(SESSION)
        assert s["shape"]["rows"] == 5
        assert s["shape"]["columns"] == 6

    def test_numeric_columns_detected(self):
        with patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            s = dp.compute_summary(SESSION)
        assert "sales" in s["numeric_columns"]
        assert "units" in s["numeric_columns"]

    def test_categorical_columns_detected(self):
        with patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            s = dp.compute_summary(SESSION)
        assert "region" in s["categorical_columns"]

    def test_numeric_stats_keys(self):
        with patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            s = dp.compute_summary(SESSION)
        stat = s["numeric_stats"]["sales"]
        for key in ("mean", "median", "std", "min", "max", "missing", "missing_pct", "skewness"):
            assert key in stat, f"Missing key: {key}"

    def test_mean_correct(self):
        with patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            s = dp.compute_summary(SESSION)
        assert s["numeric_stats"]["sales"]["mean"] == pytest.approx(8000.0, rel=1e-3)

    def test_missing_values(self):
        csv_with_na = b"a,b\n1,\n2,3\n3,\n"
        with patch("backend.modules.session_store.set_value", side_effect=_mock_set), \
             patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            dp.load_csv(csv_with_na, "na.csv", SESSION)
            s = dp.compute_summary(SESSION)
        assert s["numeric_stats"]["b"]["missing"] == 2
        assert s["numeric_stats"]["b"]["missing_pct"] == pytest.approx(66.67, abs=0.1)

    def test_no_session_raises(self):
        with patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            with pytest.raises((ValueError, KeyError)):
                dp.compute_summary("nonexistent-session")

    def test_strong_correlations_detected(self):
        # sales and units have perfect correlation in sample data
        with patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            s = dp.compute_summary(SESSION)
        cols = [(c["col1"], c["col2"]) for c in s["strong_correlations"]]
        found = any(
            set(pair) == {"sales", "units"} or set(pair) == {"sales", "discount"}
            for pair in cols
        )
        assert found, f"Expected a strong correlation in {cols}"


class TestGetPreview:
    def setup_method(self):
        mock_store.clear()
        with patch("backend.modules.session_store.set_value", side_effect=_mock_set), \
             patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            dp.load_csv(SAMPLE_CSV, "test.csv", SESSION)

    def test_preview_length(self):
        with patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            rows = dp.get_preview(SESSION, n=3)
        assert len(rows) == 3

    def test_preview_keys(self):
        with patch("backend.modules.session_store.get_value", side_effect=_mock_get):
            rows = dp.get_preview(SESSION)
        assert "sales" in rows[0]
