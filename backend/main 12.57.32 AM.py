"""
AutoInsight – FastAPI Application Entry Point
- Structured JSON logging via structlog
- CORS restricted to configured origin
- Rate limiter wired to app
- Startup checks: API key present
- Global error handlers for clean JSON errors
"""

import logging
import os
import sys
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.routes.api import limiter, router

# ── Structured logging setup ───────────────────────────────────────────────

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, LOG_LEVEL, logging.INFO)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
)

logger = structlog.get_logger(__name__)


# ── CORS origins ──────────────────────────────────────────────────────────

_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:8501")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]


# ── Lifespan (startup/shutdown) ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        logger.error(
            "startup_check_failed",
            reason="ANTHROPIC_API_KEY not set",
            hint="Export it: export ANTHROPIC_API_KEY=sk-ant-...",
        )
    else:
        logger.info("startup_check_passed", api_key_prefix=api_key[:12] + "...")
    logger.info("startup_complete", allowed_origins=ALLOWED_ORIGINS, log_level=LOG_LEVEL)
    yield
    # Shutdown (nothing to clean up yet)


# ── App factory ───────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="AutoInsight API",
        description="Automatic data insights powered by Claude",
        version="1.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    # Routes
    app.include_router(router, prefix="/api")

    # ── Global exception handlers ──────────────────────────────────────────

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again."},
        )

    # ── Health ─────────────────────────────────────────────────────────────

    @app.get("/health", tags=["ops"])
    async def health():
        return {
            "status": "ok",
            "service": "AutoInsight",
            "version": app.version,
            "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        }

    return app


app = create_app()
