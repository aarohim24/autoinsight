import json
import os
import re
import structlog

logger = structlog.get_logger(__name__)
MODEL = "llama-3.3-70b-versatile"


def _get_api_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY not set. Get free key at console.groq.com")
    return key


def _build_summary_text(summary, filename):
    lines = ["Dataset: " + filename]
    shape = summary.get("shape", {})
    lines.append("Shape: " + str(shape.get("rows")) + " rows x " + str(shape.get("columns")) + " columns")
    for col, s in list(summary.get("numeric_stats", {}).items())[:12]:
        lines.append("  " + col + ": mean=" + str(s["mean"]) + ", median=" + str(s["median"]) + ", missing=" + str(s["missing_pct"]) + "%")
    for col, s in list(summary.get("categorical_stats", {}).items())[:8]:
        top = list(s["top_values"].keys())[:3]
        lines.append("  " + col + ": " + str(s["unique"]) + " unique, top: " + str(top))
    for c in summary.get("strong_correlations", [])[:6]:
        lines.append("  " + c["col1"] + " <-> " + c["col2"] + ": r=" + str(c["r"]))
    for t in summary.get("trends", [])[:6]:
        lines.append("  " + t["column"] + ": " + t["direction"] + " (" + str(round(t["magnitude_pct"], 1)) + "%)")
    return "\n".join(lines)


def _parse_json(raw, fallback_key="insights"):
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        return json.loads(clean)
    except Exception:
        return {fallback_key: [raw], "possible_reasons": [], "actionable_suggestions": []}


async def _call_groq(system, user):
    from groq import Groq
    import traceback
    try:
        logger.info("groq_init_start")
        client = Groq(api_key=_get_api_key())
        logger.info("groq_init_success")
    except Exception as e:
        logger.error("groq_init_failed", error=str(e), traceback=traceback.format_exc())
        raise
    logger.info("groq_call_start", model=MODEL)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=1200,
    )
    text = response.choices[0].message.content
    logger.info("groq_call_done", chars=len(text))
    return text


async def generate_insights(summary, filename):
    text = _build_summary_text(summary, filename)
    system = (
        "You are an expert data analyst. Respond ONLY with valid JSON, no markdown:\n"
        '{"insights":["..."],"possible_reasons":["..."],"actionable_suggestions":["..."]}\n'
        "insights: 3-5 key findings. possible_reasons: 2-3 explanations. actionable_suggestions: 2-3 steps."
    )
    raw = await _call_groq(system, "Dataset summary:\n" + text)
    return _parse_json(raw, "insights")


async def answer_nl_query(question, summary, filename):
    text = _build_summary_text(summary, filename)
    system = (
        "You are a data analyst. Respond ONLY with valid JSON, no markdown:\n"
        '{"answer":"...","confidence":"high|medium|low","caveat":"..."}'
    )
    raw = await _call_groq(system, "Dataset:\n" + text + "\n\nQuestion: " + question)
    return _parse_json(raw, "answer")