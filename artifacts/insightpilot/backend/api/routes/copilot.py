"""
InsightPilot AI — Copilot route.

POST /api/copilot
  - Resolves the dataset from datasetId
  - Reuses all existing analytics services to build a structured context
  - Calls CopilotService (owns LLM provider logic)
  - Returns answer, reasoning, confidence, follow_up_questions

No business logic lives here.
"""

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import CopilotInput, CopilotResponse
from services.ingest import IngestService
from services.file_loader import FileLoaderError
import services.container as svc

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/copilot", response_model=CopilotResponse)
async def copilot_query(body: CopilotInput) -> CopilotResponse:
    """
    Answer a natural-language question about the dataset identified by
    ``datasetId`` using a Senior BI Consultant AI persona.
    """

    # 1. Resolve dataset
    try:
        meta = IngestService.resolve(body.datasetId)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # 2. Load DataFrame
    try:
        df, _file_meta = svc.file_loader.load_path(meta["file_path"])
    except FileLoaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset file not found: {meta['file_path']}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not load dataset: {exc}")

    # 3. Run analytics pipeline (no logic duplicated)
    try:
        profile = svc.analytics.profile_dataframe(df)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Profiling failed: {exc}")

    classification = svc.classifier.classify(profile["column_names"])
    domain         = classification["domain"]

    raw_kpis  = svc.kpi_detector.detect(df, domain)
    raw_plan  = svc.chart_planner.plan(df, domain)
    anomalies = svc.anomaly_detector.detect(df)

    # 4. Build structured business context (no raw rows, no CSV)
    business_context = {
        "domain":     domain,
        "confidence": classification.get("confidence", 0),
        "dataset_profile": {
            "rows":             profile["row_count"],
            "columns":          profile["column_count"],
            "numeric_columns":  profile["numeric_columns"],
            "categorical_cols": profile["categorical_columns"],
            "datetime_cols":    profile["datetime_columns"],
            "missing_values":   profile["total_missing_values"],
            "duplicate_rows":   profile["duplicate_rows"],
        },
        "kpis": [{"label": k["label"], "value": k["value"]} for k in raw_kpis],
        "charts": [
            {
                "title":             c["title"],
                "type":              c["type"],
                "business_question": c.get("business_question", ""),
                "confidence":        c.get("confidence", 0),
            }
            for c in raw_plan
        ],
        "anomalies": {
            "outlier_columns": [
                u["column"] for u in anomalies.get("unusual_values", [])
                if u.get("severity") in ("high", "medium")
            ],
            "missing_data_warnings": [
                w["message"] for w in anomalies.get("missing_data_warnings", [])
            ],
            "duplicate_warning": (anomalies.get("duplicate_warning") or {}).get("message"),
        },
        "matched_columns":  classification.get("matched_columns", []),
        "matched_keywords": classification.get("matched_keywords", []),
    }

    logger.info("copilot | domain=%s | question=%r", domain, body.question[:80] if body.question else "")

    # 5. Call AI Copilot service
    result = await svc.copilot_svc.answer(
        business_context=business_context,
        question=body.question,
    )

    return CopilotResponse(
        answer=result["answer"],
        reasoning=result["reasoning"],
        confidence=result["confidence"],
        follow_up_questions=result.get("follow_up_questions", []),
        domain=domain,
    )
