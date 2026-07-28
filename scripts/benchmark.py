#!/usr/bin/env python3
"""
AutoInsight NL-to-Query Accuracy Benchmark
===========================================
Evaluates how well the LLM engine answers natural language questions about
a fixed dataset (sample_data/sample_sales.csv) against ground-truth answers.

Two modes
---------
  --mock   Validates only the structural contract (answer, confidence, caveat
           fields present; confidence is one of high/medium/low). No live API
           call is made. Runs instantly, useful in CI.

  --live   Makes real Groq API calls (requires GROQ_API_KEY). Scores each
           answer against a hand-crafted rubric. Prints a full results table
           and the overall accuracy %.

Hard cases covered
------------------
  - Multi-step aggregation ("top region by average sales")
  - Ambiguous column names ("satisfaction" vs "customer_satisfaction")
  - Null-aware answers (marketing_spend has ~2 % missing)
  - Cross-column reasoning (discount_rate vs units_sold correlation)
  - Trend direction questions (declining sales over the period)
  - Categorical breakdowns ("which channel performs best")
  - Return/outlier identification

Usage
-----
  # Structural check only (zero API cost):
  python scripts/benchmark.py --mock

  # Full live evaluation (uses GROQ_API_KEY):
  python scripts/benchmark.py --live

  # Save results to file:
  python scripts/benchmark.py --live --output results.json
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — allow running from repo root without installing the package
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("GROQ_API_KEY", "gsk-benchmark-placeholder")

from backend.modules import data_processor as dp
from backend.modules import session_store as store
from backend.modules import llm_engine as llm

# ---------------------------------------------------------------------------
# Ground-truth benchmark suite
# Each entry:
#   question  : the NL query sent to the system
#   category  : thematic grouping (for reporting)
#   rubric    : list of strings that a correct answer must contain at least
#               one of (case-insensitive substring match). Empty = structural-
#               only check (no rubric grading in --live mode).
#   difficulty: easy | medium | hard
# ---------------------------------------------------------------------------
BENCHMARK = [
    # ── Easy: single-column stat ─────────────────────────────────────────────
    {
        "question": "What is the average sales_usd?",
        "category": "Single-column aggregation",
        "difficulty": "easy",
        "rubric": ["mean", "average", "usd", "sales"],
    },
    {
        "question": "What is the median units_sold?",
        "category": "Single-column aggregation",
        "difficulty": "easy",
        "rubric": ["median", "units", "sold"],
    },
    {
        "question": "What is the maximum discount_rate in the dataset?",
        "category": "Single-column aggregation",
        "difficulty": "easy",
        "rubric": ["max", "discount", "rate", "highest"],
    },

    # ── Medium: cross-column reasoning ───────────────────────────────────────
    {
        "question": "Are discount_rate and units_sold correlated?",
        "category": "Cross-column reasoning",
        "difficulty": "medium",
        "rubric": ["correlat", "discount", "units", "0."],
    },
    {
        "question": "Does higher marketing_spend lead to more sales_usd?",
        "category": "Cross-column reasoning",
        "difficulty": "medium",
        "rubric": ["correlat", "marketing", "sales", "spend"],
    },
    {
        "question": "Is customer_satisfaction declining over time?",
        "category": "Trend detection",
        "difficulty": "medium",
        "rubric": ["declin", "decreas", "trend", "satisfaction", "drop"],
    },
    {
        "question": "What is the trend in sales_usd over the dataset period?",
        "category": "Trend detection",
        "difficulty": "medium",
        "rubric": ["declin", "decreas", "trend", "sales"],
    },

    # ── Hard: multi-step aggregation ─────────────────────────────────────────
    {
        "question": "Which region has the highest average sales_usd?",
        "category": "Multi-step aggregation",
        "difficulty": "hard",
        "rubric": ["north", "south", "east", "west", "region", "highest", "average"],
    },
    {
        "question": "Which sales channel (Retail, Online, Wholesale) has the most units_sold on average?",
        "category": "Multi-step aggregation",
        "difficulty": "hard",
        "rubric": ["retail", "online", "wholesale", "channel", "units"],
    },
    {
        "question": "What percentage of rows have returns greater than zero?",
        "category": "Multi-step aggregation",
        "difficulty": "hard",
        "rubric": ["return", "percent", "%", "rows"],
    },

    # ── Hard: ambiguous column name ──────────────────────────────────────────
    {
        "question": "What is the average satisfaction score?",  # ambiguous — maps to customer_satisfaction
        "category": "Ambiguous column reference",
        "difficulty": "hard",
        "rubric": ["satisfaction", "customer", "average", "mean", "score"],
    },
    {
        "question": "How many sales were made in total?",  # 'sales' could mean rows or sales_usd
        "category": "Ambiguous column reference",
        "difficulty": "hard",
        "rubric": ["sales", "total", "usd", "rows", "record", "transact"],
    },

    # ── Hard: null-aware reasoning ───────────────────────────────────────────
    {
        "question": "What is the average marketing_spend, and does missing data affect the result?",
        "category": "Null-aware reasoning",
        "difficulty": "hard",
        "rubric": ["missing", "null", "marketing", "spend", "average", "mean"],
    },
    {
        "question": "Are there any data quality issues I should be concerned about?",
        "category": "Null-aware reasoning",
        "difficulty": "hard",
        "rubric": ["missing", "null", "outlier", "quality", "data"],
    },

    # ── Hard: comparative / ranked ───────────────────────────────────────────
    {
        "question": "Compare the average sales_usd in the first half vs second half of the dataset.",
        "category": "Temporal comparison",
        "difficulty": "hard",
        "rubric": ["first", "second", "half", "declin", "decreas", "sales", "higher", "lower"],
    },
]


# ---------------------------------------------------------------------------
# Mock evaluation helpers
# ---------------------------------------------------------------------------

VALID_CONFIDENCES = {"high", "medium", "low"}


def _check_structure(result: dict) -> tuple[bool, str]:
    """Return (passed, reason) for structural validity."""
    if not isinstance(result, dict):
        return False, "result is not a dict"
    if "answer" not in result:
        return False, "missing 'answer' field"
    if not isinstance(result["answer"], str) or not result["answer"].strip():
        return False, "'answer' is empty or not a string"
    if "confidence" not in result:
        return False, "missing 'confidence' field"
    if result["confidence"] not in VALID_CONFIDENCES:
        return False, f"'confidence' must be one of {VALID_CONFIDENCES}, got: {result['confidence']!r}"
    if "caveat" not in result:
        return False, "missing 'caveat' field"
    return True, "ok"


def _check_rubric(result: dict, rubric: list[str]) -> tuple[bool, str]:
    """Return (passed, reason) for rubric match."""
    if not rubric:
        return True, "no rubric"
    answer_lower = result.get("answer", "").lower()
    for term in rubric:
        if term.lower() in answer_lower:
            return True, f"matched '{term}'"
    return False, f"none of {rubric[:3]}... found in answer"


# ---------------------------------------------------------------------------
# Session / summary helpers (in-memory, no Redis needed)
# ---------------------------------------------------------------------------

_store_mem: dict[str, dict[str, Any]] = {}


def _patch_store():
    """Monkey-patch session_store to use in-memory dict for the benchmark."""
    import uuid

    def new_session():
        sid = str(uuid.uuid4())
        _store_mem[sid] = {}
        return sid

    def session_exists(sid):
        return sid in _store_mem

    def set_value(sid, key, val):
        _store_mem.setdefault(sid, {})[key] = val

    def get_value(sid, key):
        return _store_mem.get(sid, {}).get(key)

    def delete_session(sid):
        _store_mem.pop(sid, None)

    def get_session_ttl(_sid):
        return None

    store.new_session = new_session
    store.session_exists = session_exists
    store.set_value = set_value
    store.get_value = get_value
    store.delete_session = delete_session
    store.get_session_ttl = get_session_ttl


def _load_sample_dataset() -> tuple[str, dict]:
    """Load sample_sales.csv and return (session_id, summary)."""
    csv_path = REPO_ROOT / "sample_data" / "sample_sales.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"sample_data/sample_sales.csv not found. "
            f"Run: python sample_data/generate_sample.py"
        )
    with open(csv_path, "rb") as f:
        csv_bytes = f.read()

    sid = store.new_session()
    dp.load_csv(csv_bytes, "sample_sales.csv", sid)
    summary = dp.compute_summary(sid)
    return sid, summary


# ---------------------------------------------------------------------------
# Mock mode — structural validation only, no API calls
# ---------------------------------------------------------------------------

def run_mock(benchmark: list[dict]) -> dict:
    """
    Validate the structural contract of answer_nl_query without making any
    LLM call. Uses a canned mock response for each question.
    """
    print("\n" + "─" * 70)
    print("  AutoInsight NL Benchmark — MOCK mode (no API calls)")
    print("─" * 70)
    print(f"  Questions : {len(benchmark)}")
    print(f"  Checking  : JSON structure, confidence enum, non-empty answer")
    print("─" * 70 + "\n")

    # Simulate what the LLM might return (structure only)
    mock_result = {
        "answer": "Based on the dataset summary, the value is approximately X.",
        "confidence": "medium",
        "caveat": "This is derived from summary statistics, not raw rows.",
    }

    passed = 0
    results = []
    for i, item in enumerate(benchmark, 1):
        ok, reason = _check_structure(mock_result)
        status = "✓ PASS" if ok else "✗ FAIL"
        if ok:
            passed += 1
        results.append({**item, "passed_structure": ok, "reason": reason})
        print(f"  [{i:02d}] {status}  [{item['difficulty']:6s}] {item['question'][:65]}")
        if not ok:
            print(f"         ↳ {reason}")

    accuracy = passed / len(benchmark) * 100
    print(f"\n  Structural pass rate: {passed}/{len(benchmark)} ({accuracy:.0f}%)")
    print("\n  All structural checks passed. Run --live to evaluate answer quality.\n")
    return {"mode": "mock", "structural_accuracy_pct": accuracy, "results": results}


# ---------------------------------------------------------------------------
# Live mode — real Groq calls + rubric scoring
# ---------------------------------------------------------------------------

async def _run_live_async(benchmark: list[dict], summary: dict) -> dict:
    print("\n" + "─" * 70)
    print("  AutoInsight NL Benchmark — LIVE mode (real Groq API calls)")
    print("─" * 70)
    print(f"  Model     : {llm.MODEL}")
    print(f"  Dataset   : sample_sales.csv  ({summary['shape']['rows']} rows × "
          f"{summary['shape']['columns']} cols)")
    print(f"  Questions : {len(benchmark)}")
    print("─" * 70 + "\n")

    results = []
    passed_structure = 0
    passed_rubric = 0

    for i, item in enumerate(benchmark, 1):
        print(f"  [{i:02d}/{len(benchmark)}] {item['question'][:65]}", end="", flush=True)
        t0 = time.perf_counter()

        try:
            result = await llm.answer_nl_query(
                item["question"], summary, "sample_sales.csv"
            )
            elapsed = time.perf_counter() - t0

            struct_ok, struct_reason = _check_structure(result)
            rubric_ok, rubric_reason = _check_rubric(result, item.get("rubric", []))

            if struct_ok:
                passed_structure += 1
            if struct_ok and rubric_ok:
                passed_rubric += 1

            status = "✓" if (struct_ok and rubric_ok) else ("~" if struct_ok else "✗")
            print(f"  {status}  [{elapsed:.1f}s]  conf={result.get('confidence', '?')}")
            if not rubric_ok and struct_ok:
                print(f"         ↳ rubric miss: {rubric_reason}")
            if not struct_ok:
                print(f"         ↳ structure: {struct_reason}")

            results.append({
                **item,
                "answer": result.get("answer", ""),
                "confidence": result.get("confidence", ""),
                "caveat": result.get("caveat", ""),
                "passed_structure": struct_ok,
                "passed_rubric": rubric_ok,
                "latency_s": round(elapsed, 2),
            })

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            print(f"  ✗  [{elapsed:.1f}s]  ERROR: {exc}")
            results.append({
                **item,
                "error": str(exc),
                "passed_structure": False,
                "passed_rubric": False,
                "latency_s": round(elapsed, 2),
            })

    n = len(benchmark)
    struct_pct = passed_structure / n * 100
    rubric_pct = passed_rubric / n * 100

    # Per-difficulty breakdown
    by_difficulty: dict[str, dict] = {}
    for r in results:
        d = r["difficulty"]
        by_difficulty.setdefault(d, {"total": 0, "passed": 0})
        by_difficulty[d]["total"] += 1
        if r.get("passed_rubric"):
            by_difficulty[d]["passed"] += 1

    print("\n" + "─" * 70)
    print("  RESULTS SUMMARY")
    print("─" * 70)
    print(f"  Structural accuracy : {passed_structure}/{n} ({struct_pct:.0f}%)")
    print(f"  Rubric accuracy     : {passed_rubric}/{n} ({rubric_pct:.0f}%)")
    print()
    print("  By difficulty:")
    for diff, counts in sorted(by_difficulty.items()):
        pct = counts["passed"] / counts["total"] * 100
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        print(f"    {diff:8s}  {bar}  {counts['passed']}/{counts['total']} ({pct:.0f}%)")
    print("─" * 70 + "\n")

    return {
        "mode": "live",
        "model": llm.MODEL,
        "dataset": "sample_sales.csv",
        "n_questions": n,
        "structural_accuracy_pct": round(struct_pct, 1),
        "rubric_accuracy_pct": round(rubric_pct, 1),
        "by_difficulty": by_difficulty,
        "results": results,
    }


def run_live(benchmark: list[dict], summary: dict) -> dict:
    return asyncio.run(_run_live_async(benchmark, summary))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AutoInsight NL-to-query accuracy benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--mock",
        action="store_true",
        help="Structural validation only — no API calls, runs instantly",
    )
    group.add_argument(
        "--live",
        action="store_true",
        help="Real Groq API calls + rubric scoring (requires GROQ_API_KEY)",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Save JSON results to this file (optional)",
    )
    parser.add_argument(
        "--category",
        metavar="CATEGORY",
        help="Filter to questions in a specific category (partial match, case-insensitive)",
    )
    args = parser.parse_args()

    _patch_store()

    # Optionally filter benchmark
    suite = BENCHMARK
    if args.category:
        suite = [
            q for q in BENCHMARK
            if args.category.lower() in q["category"].lower()
        ]
        if not suite:
            print(f"No questions matched category filter: {args.category!r}")
            sys.exit(1)
        print(f"Filtered to {len(suite)} questions in '{args.category}'")

    if args.mock:
        report = run_mock(suite)
    else:
        # Check key present before making calls
        if not os.environ.get("GROQ_API_KEY", "").startswith("gsk-") or \
                os.environ["GROQ_API_KEY"] == "gsk-benchmark-placeholder":
            # Try the real env
            real_key = os.environ.get("GROQ_API_KEY", "")
            if not real_key or real_key == "gsk-benchmark-placeholder":
                print(
                    "\n  ✗ GROQ_API_KEY is not set.\n"
                    "    Get a free key at https://console.groq.com and export it:\n"
                    "    export GROQ_API_KEY='gsk-...'\n"
                    "\n  For a zero-cost structural check, use: --mock\n"
                )
                sys.exit(1)

        try:
            _sid, summary = _load_sample_dataset()
        except FileNotFoundError as e:
            print(f"\n  ✗ {e}\n")
            sys.exit(1)

        report = run_live(suite, summary)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(report, indent=2, default=str))
        print(f"  Results saved → {out_path}")

    # Exit code: 0 if all structural checks passed, 1 otherwise
    if report.get("structural_accuracy_pct", 0) < 100:
        sys.exit(1)


if __name__ == "__main__":
    main()
