"""
AutoInsight - LLM Module
Handles all interactions with the Anthropic Claude API.
"""

import json
import httpx
from typing import Optional

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"


async def _call_claude(system_prompt: str, user_message: str, max_tokens: int = 1000) -> str:
    """Make a single call to the Claude API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            ANTHROPIC_API_URL,
            headers={"Content-Type": "application/json"},
            json={
                "model": MODEL,
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


async def generate_insights(dataset_summary: str) -> dict:
    """
    Generate structured insights from a dataset summary.
    Returns a dict with keys: insights, reasons, suggestions.
    """
    system = (
        "You are an expert data analyst. "
        "Given a dataset summary, generate concise, actionable insights for non-technical users. "
        "Respond ONLY with valid JSON, no markdown fences, no preamble. "
        "JSON schema: "
        '{"insights": ["string", ...], "reasons": ["string", ...], "suggestions": ["string", ...]} '
        "Provide 3-5 items per key. Be specific, clear, and practical."
    )

    user_msg = f"Here is the dataset summary:\n\n{dataset_summary}\n\nGenerate insights."

    raw = await _call_claude(system, user_msg, max_tokens=1000)

    # Strip possible code fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(cleaned.split("\n")[1:])
    if cleaned.endswith("```"):
        cleaned = "\n".join(cleaned.split("\n")[:-1])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: return raw text wrapped
        return {
            "insights": [raw],
            "reasons": [],
            "suggestions": [],
        }


async def answer_natural_language_query(dataset_summary: str, question: str) -> str:
    """
    Answer a natural language question about the dataset.
    Returns a plain-text answer.
    """
    system = (
        "You are an expert data analyst assistant. "
        "The user has uploaded a dataset and you have its summary statistics. "
        "Answer the user's question clearly and concisely based on the summary. "
        "If you cannot determine the answer from the summary alone, say so and explain what additional data would help. "
        "Keep the answer under 200 words. Use plain English suitable for non-technical users."
    )

    user_msg = (
        f"Dataset Summary:\n{dataset_summary}\n\n"
        f"User Question: {question}"
    )

    return await _call_claude(system, user_msg, max_tokens=500)
