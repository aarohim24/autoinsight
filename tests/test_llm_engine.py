"""
Unit tests for llm_engine module.
Mocks httpx so no real API calls are made.
"""

import json
import os
import sys
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("GROQ_API_KEY", "gsk-test-key")

from backend.modules import llm_engine as llm

SAMPLE_SUMMARY = {
    "shape": {"rows": 500, "columns": 9},
    "numeric_stats": {
        "sales": {"mean": 8000, "median": 7900, "std": 1200, "min": 4000, "max": 12000,
                  "missing_pct": 0.0, "skewness": 0.1}
    },
    "categorical_stats": {
        "region": {"unique": 4, "top_values": {"North": 125, "South": 100}, "missing_pct": 0}
    },
    "strong_correlations": [{"col1": "sales", "col2": "units", "r": 0.85}],
    "trends": [{"column": "sales", "direction": "decreasing", "magnitude_pct": -30.0}],
    "missing_overview": {},
}

VALID_INSIGHTS = {
    "insights": ["Sales are declining by 30%", "Strong correlation between sales and units"],
    "possible_reasons": ["Market saturation", "Pricing strategy"],
    "actionable_suggestions": ["Review pricing", "Expand market"],
}


class TestGetApiKey:
    def test_missing_key_raises(self):
        env = {k: v for k, v in os.environ.items() if k != "GROQ_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
                llm._get_api_key()

    def test_key_returned(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk-abc123"}):
            assert llm._get_api_key() == "gsk-abc123"


class TestBuildSummaryText:
    def test_contains_filename(self):
        text = llm._build_summary_text(SAMPLE_SUMMARY, "test.csv")
        assert "test.csv" in text

    def test_contains_shape(self):
        text = llm._build_summary_text(SAMPLE_SUMMARY, "test.csv")
        assert "500" in text and "9" in text

    def test_contains_numeric_stats(self):
        text = llm._build_summary_text(SAMPLE_SUMMARY, "test.csv")
        assert "sales" in text
        assert "8000" in text

    def test_contains_correlation(self):
        text = llm._build_summary_text(SAMPLE_SUMMARY, "test.csv")
        assert "0.85" in text

    def test_contains_trend(self):
        text = llm._build_summary_text(SAMPLE_SUMMARY, "test.csv")
        assert "decreasing" in text


class TestParseJson:
    def test_valid_json(self):
        raw = json.dumps({"insights": ["a"], "possible_reasons": [], "actionable_suggestions": []})
        result = llm._parse_json(raw)
        assert result["insights"] == ["a"]

    def test_strips_markdown_fences(self):
        raw = "```json\n" + json.dumps({"insights": ["b"]}) + "\n```"
        result = llm._parse_json(raw)
        assert result["insights"] == ["b"]

    def test_fallback_on_invalid_json(self):
        result = llm._parse_json("NOT JSON AT ALL", fallback_key="insights")
        assert "insights" in result
        assert "NOT JSON AT ALL" in result["insights"][0]


class TestGenerateInsights:
    @pytest.mark.asyncio
    async def test_returns_parsed_insights(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(VALID_INSIGHTS)}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await llm.generate_insights(SAMPLE_SUMMARY, "sales.csv")

        assert "insights" in result
        assert len(result["insights"]) >= 1
        assert "possible_reasons" in result
        assert "actionable_suggestions" in result

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self):
        """Verifies tenacity retries on NetworkError before succeeding."""
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.raise_for_status = MagicMock()
        mock_ok.json.return_value = {
            "choices": [{"message": {"content": json.dumps(VALID_INSIGHTS)}}]
        }

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.NetworkError("transient network failure")
            return mock_ok

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=side_effect)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await llm.generate_insights(SAMPLE_SUMMARY, "sales.csv")

        assert call_count == 2
        assert "insights" in result
