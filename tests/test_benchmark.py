"""
Unit tests for scripts/benchmark.py.

Validates:
  - run_mock() passes all 15 benchmark questions structurally
  - _check_structure() correctly accepts / rejects results
  - _check_rubric() correctly matches / misses answer text
  - buildSuggestedQuestions equivalent logic (via rubric matching)
  - CLI --mock exits 0 on success
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Allow importing from scripts/ without installing
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("GROQ_API_KEY", "gsk-test-key")

from scripts.benchmark import (
    BENCHMARK,
    _check_rubric,
    _check_structure,
    run_mock,
    _patch_store,
    _load_sample_dataset,
)


# ── _check_structure ──────────────────────────────────────────────────────────

class TestCheckStructure:
    def test_valid_result_passes(self):
        ok, reason = _check_structure(
            {"answer": "Sales are declining.", "confidence": "high", "caveat": ""}
        )
        assert ok is True
        assert reason == "ok"

    def test_missing_answer_fails(self):
        ok, _ = _check_structure({"confidence": "high", "caveat": ""})
        assert ok is False

    def test_empty_answer_fails(self):
        ok, _ = _check_structure({"answer": "  ", "confidence": "high", "caveat": ""})
        assert ok is False

    def test_missing_confidence_fails(self):
        ok, _ = _check_structure({"answer": "OK", "caveat": ""})
        assert ok is False

    def test_invalid_confidence_fails(self):
        ok, _ = _check_structure(
            {"answer": "OK", "confidence": "very_high", "caveat": ""}
        )
        assert ok is False

    def test_missing_caveat_fails(self):
        ok, _ = _check_structure({"answer": "OK", "confidence": "low"})
        assert ok is False

    def test_all_confidence_values_accepted(self):
        for conf in ("high", "medium", "low"):
            ok, _ = _check_structure({"answer": "OK", "confidence": conf, "caveat": ""})
            assert ok is True, f"Expected {conf} to be accepted"

    def test_non_dict_result_fails(self):
        ok, _ = _check_structure("just a string")
        assert ok is False


# ── _check_rubric ─────────────────────────────────────────────────────────────

class TestCheckRubric:
    def test_empty_rubric_always_passes(self):
        ok, reason = _check_rubric({"answer": "anything"}, [])
        assert ok is True
        assert "no rubric" in reason

    def test_matching_term_passes(self):
        ok, reason = _check_rubric(
            {"answer": "The mean sales_usd is approximately 8000."},
            ["sales", "mean", "average"],
        )
        assert ok is True
        assert "matched" in reason

    def test_no_matching_term_fails(self):
        ok, reason = _check_rubric(
            {"answer": "I cannot determine this."},
            ["sales", "average", "mean"],
        )
        assert ok is False
        assert "none of" in reason

    def test_case_insensitive_match(self):
        ok, _ = _check_rubric(
            {"answer": "The MEAN value is high."},
            ["mean"],
        )
        assert ok is True

    def test_partial_substring_match(self):
        # "correlat" should match "correlated" and "correlation"
        ok, _ = _check_rubric(
            {"answer": "These columns are strongly correlated."},
            ["correlat"],
        )
        assert ok is True


# ── run_mock ──────────────────────────────────────────────────────────────────

class TestRunMock:
    def test_mock_passes_all_questions(self):
        report = run_mock(BENCHMARK)
        assert report["mode"] == "mock"
        assert report["structural_accuracy_pct"] == 100.0

    def test_mock_report_contains_all_questions(self):
        report = run_mock(BENCHMARK)
        assert len(report["results"]) == len(BENCHMARK)

    def test_mock_all_results_passed(self):
        report = run_mock(BENCHMARK)
        for r in report["results"]:
            assert r["passed_structure"] is True, f"Failed: {r['question']}"

    def test_mock_benchmark_covers_all_difficulties(self):
        difficulties = {q["difficulty"] for q in BENCHMARK}
        assert "easy" in difficulties
        assert "medium" in difficulties
        assert "hard" in difficulties

    def test_mock_benchmark_covers_all_categories(self):
        categories = {q["category"] for q in BENCHMARK}
        assert len(categories) >= 6, f"Expected ≥ 6 categories, got {categories}"

    def test_mock_15_questions_in_suite(self):
        assert len(BENCHMARK) == 15


# ── Sample dataset loading (with patched store) ───────────────────────────────

@pytest.fixture()
def patched_store():
    """
    Patch session_store for one test, then restore originals.
    Prevents _patch_store() from leaking into other test modules when the
    full pytest suite runs.
    """
    from backend.modules import session_store as _store_module

    originals = {
        fn: getattr(_store_module, fn)
        for fn in (
            "new_session", "session_exists", "set_value",
            "get_value", "delete_session", "get_session_ttl",
        )
    }
    _patch_store()
    yield
    for fn, orig in originals.items():
        setattr(_store_module, fn, orig)


class TestLoadSampleDataset:
    def test_loads_sample_sales_csv(self, patched_store):
        sid, summary = _load_sample_dataset()
        assert sid is not None
        assert summary["shape"]["rows"] > 0
        assert summary["shape"]["columns"] == 9

    def test_summary_has_expected_columns(self, patched_store):
        _sid, summary = _load_sample_dataset()
        numeric = summary["numeric_columns"]
        categorical = summary["categorical_columns"]
        assert "sales_usd" in numeric
        assert "units_sold" in numeric
        assert "region" in categorical or "channel" in categorical

    def test_summary_has_trends(self, patched_store):
        """sample_sales.csv has a deliberate declining sales trend."""
        _sid, summary = _load_sample_dataset()
        assert isinstance(summary["trends"], list)

    def test_summary_data_quality_score_in_range(self, patched_store):
        _sid, summary = _load_sample_dataset()
        score = summary["data_quality_score"]
        assert 0 <= score <= 100



# ── CLI smoke test ────────────────────────────────────────────────────────────

class TestCli:
    def test_mock_mode_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "scripts/benchmark.py", "--mock"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env={**os.environ, "GROQ_API_KEY": "gsk-test-key"},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "15/15" in result.stdout
        assert "100%" in result.stdout

    def test_missing_args_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, "scripts/benchmark.py"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode != 0

    def test_mock_with_category_filter(self):
        result = subprocess.run(
            [
                sys.executable,
                "scripts/benchmark.py",
                "--mock",
                "--category",
                "Multi-step",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env={**os.environ, "GROQ_API_KEY": "gsk-test-key"},
        )
        assert result.returncode == 0
        assert "Filtered to" in result.stdout
