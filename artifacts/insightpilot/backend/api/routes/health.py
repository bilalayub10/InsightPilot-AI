"""
Health check routes.

Placeholder only — returns mock status data.
"""

import time
from fastapi import APIRouter
from models.schemas import ServiceInfo, HealthStatus

START_TIME = time.time()

router = APIRouter()


@router.get("/healthz", response_model=HealthStatus)
async def healthz() -> HealthStatus:
    """Standard /healthz liveness probe."""
    return HealthStatus(status="ok")


@router.get("/health", response_model=ServiceInfo)
async def health() -> ServiceInfo:
    """Returns InsightPilot service info including uptime."""
    return ServiceInfo(
        status="ok",
        version="0.1.0",
        service="InsightPilot AI",
        uptime=round(time.time() - START_TIME, 2),
    )
