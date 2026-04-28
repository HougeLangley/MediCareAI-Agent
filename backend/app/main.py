"""FastAPI application entry point.

Bootstrap order:
1. Load settings from environment
2. Configure structured logging
3. Initialize Sentry (production only)
4. Register routers & middleware
"""

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()

# Logging first
configure_logging(debug=settings.debug)

# Sentry in production
if settings.is_production and settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.05,
    )

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-Agent Autonomous Medical Collaboration System",
    debug=settings.debug,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# CORS — configured via env, not hardcoded
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Liveness probe."""
    return {"status": "ok", "version": settings.app_version, "env": settings.environment}


@app.get("/ready", tags=["System"])
async def readiness_check() -> dict:
    """Readiness probe — checks DB & Redis connectivity."""
    # TODO: add DB & Redis connectivity checks
    return {"status": "ready"}
