"""
LLM Engine for AutoInsight.
Calls the Groq API with tenacity retry (4 attempts, exponential backoff 2-30s).
All functions are async and fully typed.
"""

import json
import os
import re
import traceback

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

MODEL = "llama-3.3-70b-versatile"
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_REQUEST_TIMEOUT = 30.0


def _get_api_key() -> str:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY not set. Get a free key at console.groq.com")
    return key


def _build_summary_text(summary: dict, filename: str) -> str:
    lines = [
        f"Dataset: {filename}",
        "Shape: {rows} rows x {cols} columns".format(
            rows=summary.get("shape", {}).get("rows"),
            cols=summary.get("shape", {}).get("columns"),
        ),
    ]
    for col, s in list(summary.get("numeric_stats", {}).items())[:12]:
        lines.append(
            f"  {col}: mean={s['mean']}, median={s['median']}, missing={s['missing_pct']}%"
        )
    for col, s in list(summary.get("categorical_stats", {}).items())[:8]:
        top = list(s["top_values"].keys())[:3]
        lines.append(f"  {col}: {s['unique']} unique, top: {top}")
    for c in summary.get("strong_correlations", [])[:6]:
        lines.append(f"  {c['col1']} <-> {c['col2']}: r={c['r']}")
    for t in summary.get("trends", [])[:6]:
        lines.append(f"  {t['column']}: {t['direction']} ({round(t['magnitude_pct'], 1)}%)")
    return "\n".join(lines)


def _parse_json(raw: str, fallback_key: str = "insights") -> dict:
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        return json.loads(clean)
    except Exception:
        return {fallback_key: [raw], "possible_reasons": [], "actionable_suggestions": []}


@retry(
    retry=retry_if_exception_type(
        (httpx.TransientError, httpx.NetworkError, httpx.TimeoutException)
    ),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def _call_groq(system: str, user: str) -> str:
    api_key = _get_api_key()
    logger.info("groq_call_start", model=MODEL)
    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.post(
                _GROQ_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": 1200,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            text: str = response.json()["choices"][0]["message"]["content"]
        logger.info("groq_call_done", chars=len(text))
        return text
    except Exception:
        logger.error("groq_call_failed", traceback=traceback.format_exc())
        raise


async def generate_insights(summary: dict, filename: str) -> dict:
    text = _build_summary_text(summary, filename)
    system = (
        "You are an expert data analyst. Respond ONLY with valid JSON, no markdown:\n"
        '{"insights":["..."],"possible_reasons":["..."],"actionable_suggestions":["..."]}\n'
        "insights: 3-5 key findings. possible_reasons: 2-3 explanations. actionable_suggestions: 2-3 steps."
    )
    raw = await _call_groq(system, f"Dataset summary:\n{text}")
    return _parse_json(raw, "insights")


async def answer_nl_query(question: str, summary: dict, filename: str) -> dict:
    text = _build_summary_text(summary, filename)
    system = (
        "You are a data analyst. Respond ONLY with valid JSON, no markdown:\n"
        '{"answer":"...","confidence":"high|medium|low","caveat":"..."}'
    )
    raw = await _call_groq(system, f"Dataset:\n{text}\n\nQuestion: {question}")
    return _parse_json(raw, "answer")