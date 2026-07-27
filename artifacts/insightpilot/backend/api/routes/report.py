"""
Executive Report route.

POST /api/report  { "datasetId": "..." }
→ application/pdf

Reads the cached analysis result written by the /api/analyze route.
Delegates all PDF construction to ReportGenerator — no analytics are
re-run here.
"""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from services.ingest import IngestService, UPLOADS_DIR
from services.report_generator import generate_report

logger = logging.getLogger(__name__)
router = APIRouter()


class ReportInput(BaseModel):
    datasetId: str


@router.post("/report")
async def generate_executive_report(body: ReportInput) -> Response:
    """
    Generate and return a professional executive PDF report.

    Reads the cached AnalyzeResult sidecar written by /api/analyze.
    Raises 404 if the dataset or analysis cache is missing.
    Raises 500 on PDF generation failure.
    """
    # 1. Confirm dataset exists
    try:
        IngestService.resolve(body.datasetId)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # 2. Load cached analysis result
    cache_path = UPLOADS_DIR / f"{body.datasetId}.analysis.json"
    if not cache_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Analysis results not found for this dataset. "
                "Please run /api/analyze first."
            ),
        )

    try:
        analysis = json.loads(cache_path.read_text())
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load cached analysis: {exc}",
        )

    # 3. Generate PDF
    try:
        pdf_bytes = generate_report(analysis)
    except Exception as exc:
        logger.exception("PDF generation failed for dataset %s", body.datasetId)
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {exc}",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="InsightPilot_Executive_Report.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
