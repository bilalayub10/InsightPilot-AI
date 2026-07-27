"""
InsightPilot AI — FastAPI application entry point.

This module creates the FastAPI app, configures CORS, and registers all
API routers under the /api prefix.  No business logic lives here — only
application wiring.
"""

import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.health import router as health_router
from api.routes.upload import router as upload_router
from api.routes.analyze import router as analyze_router
from api.routes.copilot import router as copilot_router
from api.routes.report import router as report_router

START_TIME = time.time()

app = FastAPI(
    title="InsightPilot AI",
    description="Autonomous business analytics platform API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers — all mounted under /api so the reverse proxy can route correctly
# ---------------------------------------------------------------------------

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(analyze_router, prefix="/api", tags=["analyze"])
app.include_router(copilot_router, prefix="/api", tags=["copilot"])
app.include_router(report_router, prefix="/api", tags=["report"])
