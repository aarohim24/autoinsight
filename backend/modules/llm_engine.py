"""
LLM Module for AutoInsight
- API key loaded from environment (ANTHROPIC_API_KEY)
- Fully async via httpx.AsyncClient
- Exponential backoff retry via tenacity
- Structured logging
"""

import json
import os
import re

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    RetryCallState,
)

logger = structlog.get_logger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-3-5-sonnet-20241022"
_RETRYABLE_STATUS = {429, 500, 502, 503, 529}


def _get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Export it before starting the server: export ANTHROPIC_API_KEY=sk-ant-..."
        )
    return key


def _log_retry(retry_state: RetryCallState) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "llm_retry",
        attempt=retry_state.attempt_number,
        exc=str(exc) if exc else None,
    )


@retry(
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.TimeoutException, httpx.NetworkError)
    ),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    before_sleep=_log_retry,
    reraise=True,
)
async def _call_claude(system: str, user: str, max_tokens: int = 1500) -> str:
    """Async Anthropic Messages API call with retry."""
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": _get_api_key(),
        "anthropic-version": "2023-06-01",
    }

    logger.info("llm_call_start", model=MODEL, max_tokens=max_tokens)
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)

    if resp.status_code in _RETRYABLE_STATUS:
        logger.warning("llm_retryable_error", status=resp.status_code)
        resp.raise_for_status()

    resp.raise_for_status()
    data = resp.json()
    text = data["content"][0]["text"]
    logger.info("llm_call_done", output_chars=len(text))
    return text


def _build_summary_text(summary: dict, filename: str) -> str:
    lines = [f"Dataset: {filename}"]
    shape = summary.get("shape", {})
    lines.append(f"Shape: {shape.get('rows')} rows x {shape.get('columns')} columns")

    numeric_stats = summary.get("numeric_stats", {})
    if numeric_stats:
        lines.append("\nNumeric columns:")
        for col, s in list(numeric_stats.items())[:12]:
            lines.append(
                f"  {col}: mean={s['mean']}, median={s['median']}, std={s['std']}, "
                f"min={s['min']}, max={s['max']}, missing={s['missing_pct']}%, skew={s['skewness']}"
            )

    cat_stats = summary.get("categorical_stats", {})
    if cat_stats:
        lines.append("\nCategorical columns:")
        for col, s in list(cat_stats.items())[:8]:
            top = list(s["top_values"].keys())[:3]
            lines.append(f"  {col}: {s['unique']} unique values, top: {top}")

    strong_corrs = summary.get("strong_correlations", [])
    if strong_corrs:
        lines.append("\nStrong correlations (|r| > 0.6):")
        for c in strong_corrs[:6]:
            lines.append(f"  {c['col1']} <-> {c['col2']}: r={c['r']}")

    trends = summary.get("trends", [])
    if trends:
        lines.append("\nDetected trends:")
        for t in trends[:6]:
            lines.append(f"  {t['column']}: {t['direction']} ({t['magnitude_pct']:+.1f}%)")

    missing = summary.get("missing_overview", {})
    if missing:
        lines.append("\nColumns with missing values:")
        for col, n in list(missing.items())[:8]:
            lines.append(f"  {col}: {n} missing")

    return "\n".join(lines)


def _parse_json(raw: str, fallback_key: str = "insights") -> dict:
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("llm_json_parse_failed", raw_snippet=raw[:120])
        return {fallback_key: [raw], "possible_reasons": [], "actionable_suggestions": []}


async def generate_insights(summary: dict, filename: str) -> dict:
    """Return 3-5 key insights, possible reasons, and actionable suggestions."""
    summary_text = _build_summary_text(summary, filename)
    system = (
        "You are AutoInsight, an expert data analyst AI. "
        "Analyse the dataset summary and respond ONLY with valid JSON - no markdown - matching:\n"
        '{"insights":["..."],"possible_reasons":["..."],"actionable_suggestions":["..."]}\n'
        "insights: 3-5 key findings for a non-technical stakeholder.\n"
        "possible_reasons: 2-3 plausible explanations.\n"
        "actionable_suggestions: 2-3 concrete next steps."
    )
    raw = await _call_claude(system, f"Dataset summary:\n\n{summary_text}", max_tokens=1200)
    return _parse_json(raw, "insights")


async def answer_nl_query(question: str, summary: dict, filename: str) -> dict:
    """Answer a natural-language question about the dataset."""
    summary_text = _build_summary_text(summary, filename)
    system = (
        "You are AutoInsight, an expert data analyst AI. "
        "Answer the user's question about their dataset concisely for a non-technical audience. "
        'Respond ONLY with valid JSON: {"answer":"...","confidence":"high|medium|low","caveat":"..."}'
    )
    raw = await _call_claude(
        system,
        f"Dataset summary:\n{summary_text}\n\nQuestion: {question}",
        max_tokens=600,
    )
    return _parse_json(raw, "answer")
