import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.routes.api import limiter, router

# Load environment variables from .env file
load_dotenv()

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

# Allow ALL origins — fixes CORS permanently
ALLOWED_ORIGINS = ["*"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not groq_key:
        logger.error("no_groq_key", hint="Set GROQ_API_KEY environment variable")
    else:
        logger.info("startup_ok", groq_key_prefix=groq_key[:8] + "...")
    logger.info("startup_complete", allowed_origins=ALLOWED_ORIGINS)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="AutoInsight API",
        description="Instant data insights",
        version="1.2.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    app.include_router(router, prefix="/api")

    @app.get("/")
    async def root():
        return {
            "name": "AutoInsight API",
            "version": app.version,
            "status": "running",
            "docs": "http://localhost:8000/docs",
            "health": "http://localhost:8000/health",
            "api_prefix": "/api",
        }

    @app.exception_handler(Exception)
    async def err(request: Request, exc: Exception):
        logger.error("unhandled", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred."},
        )

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": app.version,
            "groq_key_set": bool(os.environ.get("GROQ_API_KEY")),
        }

    return app


app = create_app()