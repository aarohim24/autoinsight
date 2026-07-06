"""
API Routes for AutoInsight
- Fully async
- Per-session isolation via session_id header/cookie
- Rate limiting on LLM endpoints
- Input validation
"""

import os
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.modules import cache as insight_cache
from backend.modules import data_processor as dp
from backend.modules import llm_engine as llm
from backend.modules import session_store as store

logger = structlog.get_logger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

_ALLOWED_MIME = {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"}
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB — enforced again at route layer


# ── Session dependency ──────────────────────────────────────────────────────

def get_session(x_session_id: str = Header(..., alias="X-Session-Id")) -> str:
    if not store.session_exists(x_session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please upload a CSV to create a new session.",
        )
    return x_session_id


# ── POST /upload-data ──────────────────────────────────────────────────────

@router.post("/upload-data", status_code=201)
@limiter.limit("10/minute")
async def upload_data(request: Request, file: UploadFile = File(...)):
    # Content-type check (lenient — browsers set this inconsistently)
    if file.content_type and file.content_type not in _ALLOWED_MIME and not file.filename.endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only CSV files are accepted.")

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Filename must end with .csv")

    contents = await file.read()

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(contents)//1_048_576} MB). Max is 50 MB.",
        )

    session_id = store.new_session()

    try:
        meta = dp.load_csv(contents, file.filename, session_id)
    except ValueError as exc:
        store.delete_session(session_id)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        store.delete_session(session_id)
        logger.error("upload_unexpected_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to process CSV.")

    logger.info("upload_success", session_id=session_id, filename=file.filename)
    return {"status": "ok", **meta}


# ── GET /analyze ───────────────────────────────────────────────────────────

@router.get("/analyze")
@limiter.limit("30/minute")
async def analyze(request: Request, session_id: str = Depends(get_session)):
    try:
        summary = dp.compute_summary(session_id)
        preview = dp.get_preview(session_id, n=50)
        meta    = dp.get_metadata(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("analyze_error", session_id=session_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Analysis failed.")
    return {"meta": meta, "summary": summary, "preview": preview}


# ── POST /generate-insights ────────────────────────────────────────────────

@router.post("/generate-insights")
@limiter.limit("5/minute")
async def generate_insights(request: Request, session_id: str = Depends(get_session)):
    try:
        summary = dp.compute_summary(session_id)
        meta    = dp.get_metadata(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Cache hit?
    cached = insight_cache.get("insights", summary)
    if cached:
        logger.info("insights_cache_hit", session_id=session_id)
        return {**cached, "_cached": True}

    try:
        insights = await llm.generate_insights(summary, meta["filename"])
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error("insights_error", session_id=session_id, error=str(exc))
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    insight_cache.set("insights", summary, insights)
    return insights


# ── POST /query ────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question must not be empty.")
        if len(v) > 500:
            raise ValueError("Question must be 500 characters or fewer.")
        return v


@router.post("/query")
@limiter.limit("10/minute")
async def natural_language_query(
    request: Request,
    body: QueryRequest,
    session_id: str = Depends(get_session),
):
    try:
        summary = dp.compute_summary(session_id)
        meta    = dp.get_metadata(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    try:
        result = await llm.answer_nl_query(body.question, summary, meta["filename"])
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error("query_error", session_id=session_id, error=str(exc))
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    return result


@router.delete("/session")
async def delete_session(session_id: str = Depends(get_session)):
    store.delete_session(session_id)
    return {"status": "ok", "message": "Session deleted."}


# ── GET /session/status ────────────────────────────────────────────────────

@router.get("/session/status")
async def session_status(session_id: str = Depends(get_session)):
    """Return session liveness and remaining TTL (for frontend expiry countdown)."""
    ttl = store.get_session_ttl(session_id)
    return {
        "active": True,
        "session_id": session_id,
        "ttl_seconds": ttl,
    }
