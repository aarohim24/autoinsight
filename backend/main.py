import logging, os, sys
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from backend.routes.api import limiter, router

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
structlog.configure(
    processors=[structlog.contextvars.merge_contextvars, structlog.processors.add_log_level, structlog.processors.TimeStamper(fmt="iso"), structlog.processors.StackInfoRenderer(), structlog.processors.JSONRenderer()],
    wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, LOG_LEVEL, logging.INFO)),
    context_class=dict, logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
)
logger = structlog.get_logger(__name__)
_raw = os.environ.get("ALLOWED_ORIGINS", "https://autoinsight-peach.vercel.app,http://localhost:3000,http://localhost:3001")
ALLOWED_ORIGINS = [o.strip() for o in _raw.split(",") if o.strip()]

@asynccontextmanager
async def lifespan(app: FastAPI):
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key: logger.error("no_api_key")
    else: logger.info("startup_ok", prefix=key[:12])
    logger.info("startup_complete", origins=ALLOWED_ORIGINS)
    yield

def create_app():
    app = FastAPI(title="AutoInsight", version="1.1.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["GET","POST","DELETE"], allow_headers=["*"], allow_credentials=False)
    app.include_router(router, prefix="/api")

    @app.exception_handler(Exception)
    async def err(request: Request, exc: Exception):
        logger.error("unhandled", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})

    @app.get("/health")
    async def health():
        return {"status": "ok", "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))}

    return app

app = create_app()
