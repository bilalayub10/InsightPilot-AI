"""
Analysis trigger route.

Orchestrates the full analytics pipeline:

    AnalyticsService   — structural profile (row count, types, missing, duplicates)
         ↓
    BusinessClassifier — detect business domain from column names
         ↓
    KPIDetector        — compute domain-appropriate KPIs from the DataFrame
         ↓
    ChartPlanner       — recommend chart types and pick x/y columns (domain-aware)
         ↓
    AnomalyDetector    — flag outliers, missing data, duplicates, skewness

ChartPlanner output is fully preserved and returned as `charts` in the response.
`trendData` and `distributionData` are derived from the first line/bar chart's
data for backward compatibility.
"""

import asyncio
import json
import math
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from models.schemas import (
    AnalyzeInput,
    AnalyzeResult,
    BusinessContext,
    CeoBriefing,
    CeoBriefingHealth,
    ChartDataPoint,
    ChartInsight,
    ChartSpec,
    DatasetStatus,
    KpiMetric,
    PriorityAction,
    Trend,
)
from services.ingest import IngestService, UPLOADS_DIR
from services.file_loader import FileLoaderError
import services.container as svc

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResult)
async def analyze_dataset(body: AnalyzeInput) -> AnalyzeResult:
    """
    Run the full analytics pipeline on the dataset identified by ``datasetId``.
    """

    # 1. Resolve dataset
    try:
        meta = IngestService.resolve(body.datasetId)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # 2. Load DataFrame (single load shared by all downstream services)
    try:
        df, _file_meta = svc.file_loader.load_path(meta["file_path"])
    except FileLoaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset file not found: {meta['file_path']}",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not load dataset: {exc}")

    # 3. Structural profile
    try:
        profile = svc.analytics.profile_dataframe(df)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Profiling failed: {exc}")

    # 4. Business domain classification
    classification = svc.classifier.classify(profile["column_names"])
    domain = classification["domain"]

    # 5. KPI detection
    raw_kpis = svc.kpi_detector.detect(df, domain)
    kpis = [
        KpiMetric(
            label=k["label"],
            value=k["value"],
            change=0.0,
            trend=Trend.flat,
        )
        for k in raw_kpis
    ]

    # 6. Chart planning
    raw_plan = svc.chart_planner.plan(df, domain)
    logger.info("analyze | domain=%s | charts=%s", domain, [c["title"] for c in raw_plan])

    # 7. Compute data for each chart spec
    chart_data_list: list[list[ChartDataPoint]] = [
        _compute_chart_data(df, spec) for spec in raw_plan
    ]

    # 8. Anomaly detection
    anomalies = svc.anomaly_detector.detect(df)

    # 8b. Generate AI chart insights — all charts run concurrently
    raw_insight_results = await asyncio.gather(
        *[
            svc.chart_insights_svc.generate(
                chart_spec=spec,
                data_points=[{"label": dp.label, "value": dp.value} for dp in data],
                profile=profile,
                kpis=raw_kpis,
                anomalies=anomalies,
                domain=domain,
            )
            for spec, data in zip(raw_plan, chart_data_list)
        ],
        return_exceptions=True,
    )

    # 8c. Build ChartSpec objects with insights attached
    chart_specs: list[ChartSpec] = []
    for spec, data, insight_result in zip(raw_plan, chart_data_list, raw_insight_results):
        insight: ChartInsight | None = None
        if isinstance(insight_result, dict):
            try:
                insight = ChartInsight(**insight_result)
            except Exception as exc:
                logger.warning("Failed to construct ChartInsight for '%s': %s", spec.get("title"), exc)
        else:
            logger.warning("Chart insight generation failed for '%s': %s", spec.get("title"), insight_result)

        chart_specs.append(
            ChartSpec(
                type=spec["type"],
                x=spec["x"],
                y=spec["y"],
                title=spec["title"],
                priority=spec.get("priority", 50),
                confidence=spec.get("confidence", 0.5),
                reason=spec.get("reason", ""),
                business_question=spec.get("business_question", ""),
                aggregation=spec.get("aggregation", "sum"),
                data=data,
                insight=insight,
            )
        )

    # 9. Backward-compat: derive trendData / distributionData from charts
    trend_data = next((cs.data for cs in chart_specs if cs.type == "line"), [])
    dist_data  = next((cs.data for cs in chart_specs if cs.type in ("bar", "pie")), [])

    # 10. Insights + summary
    insights = _build_insights(profile, classification, anomalies)
    summary  = _build_summary(profile, classification)

    # 11. Structured business context
    raw_context = await svc.context_builder.build(
        profile=profile,
        classification=classification,
        kpis=raw_kpis,
        anomalies=anomalies,
        chart_plan=raw_plan,
    )
    business_context = BusinessContext(
        executive_summary=raw_context["executive_summary"],
        strengths=raw_context["strengths"],
        risks=raw_context["risks"],
        opportunities=raw_context["opportunities"],
        recommended_questions=raw_context["recommended_questions"],
        priority_actions=[PriorityAction(**a) for a in raw_context["priority_actions"]],
        analysis_confidence=raw_context["analysis_confidence"],
        dataset_quality_score=raw_context["dataset_quality_score"],
    )

    # 12. CEO Briefing — deterministic executive summary
    raw_briefing = svc.ceo_briefing_svc.build(
        profile=profile,
        classification=classification,
        kpis=raw_kpis,
        anomalies=anomalies,
        chart_plan=raw_plan,
    )
    ceo_briefing = CeoBriefing(
        business_domain=raw_briefing["business_domain"],
        confidence=raw_briefing["confidence"],
        overall_health=CeoBriefingHealth(**raw_briefing["overall_health"]),
        urgency=raw_briefing["urgency"],
        biggest_risk=raw_briefing["biggest_risk"],
        top_opportunity=raw_briefing["top_opportunity"],
        priority_action=raw_briefing["priority_action"],
        executive_summary=raw_briefing["executive_summary"],
        key_takeaways=raw_briefing["key_takeaways"],
    )

    result = AnalyzeResult(
        datasetId=body.datasetId,
        domain=domain,
        status=DatasetStatus.done,
        summary=summary,
        kpis=kpis,
        charts=chart_specs,
        trendData=trend_data,
        distributionData=dist_data,
        insights=insights,
        analyzedAt=datetime.now(timezone.utc).isoformat(),
        businessContext=business_context,
        ceoBriefing=ceo_briefing,
    )

    # 13. Cache the full result for the report generator
    try:
        cache_path = UPLOADS_DIR / f"{body.datasetId}.analysis.json"
        cache_path.write_text(result.model_dump_json())
    except Exception as exc:
        logger.warning("Failed to cache analysis result for %s: %s", body.datasetId, exc)

    return result


# ---------------------------------------------------------------------------
# Chart data computation
# ---------------------------------------------------------------------------

def _compute_chart_data(df: pd.DataFrame, spec: dict) -> list[ChartDataPoint]:
    """
    Compute pre-rendered data points for a single ChartPlanner spec.

    All chart types return list[ChartDataPoint] (label, value pairs)
    so the frontend can use a single data shape regardless of chart type.
    """
    chart_type = spec["type"]
    x_col = spec["x"]
    y_col = spec["y"]
    agg   = spec.get("aggregation", "sum")

    try:
        if chart_type == "histogram":
            return _histogram_data(df, x_col)

        if chart_type == "scatter":
            return _scatter_data(df, x_col, y_col)

        if chart_type == "pie" or y_col in ("count", "frequency"):
            if x_col not in df.columns:
                return []
            counts = df[x_col].value_counts().head(10)
            return [
                ChartDataPoint(label=str(lbl), value=float(cnt))
                for lbl, cnt in counts.items()
                if _finite(float(cnt))
            ]

        # line / bar — grouped aggregation
        if x_col not in df.columns or y_col not in df.columns:
            return []

        subset = df[[x_col, y_col]].dropna()
        if subset.empty:
            return []

        grouped = _aggregate(subset, x_col, y_col, agg)

        if chart_type == "line":
            grouped = grouped.sort_values(x_col).head(24)
        else:
            grouped = grouped.sort_values(y_col, ascending=False).head(10)

        return [
            ChartDataPoint(label=str(row[x_col]), value=float(row[y_col]))
            for _, row in grouped.iterrows()
            if _finite(float(row[y_col]))
        ]

    except Exception as exc:
        logger.warning("_compute_chart_data failed for spec '%s': %s", spec.get("title"), exc)
        return []


def _aggregate(df: pd.DataFrame, x_col: str, y_col: str, agg: str) -> pd.DataFrame:
    g = df.groupby(x_col)[y_col]
    if agg == "mean":
        return g.mean().reset_index()
    if agg == "count":
        return g.count().reset_index()
    return g.sum().reset_index()


def _histogram_data(df: pd.DataFrame, col: str) -> list[ChartDataPoint]:
    if col not in df.columns:
        return []
    series = df[col].dropna()
    if series.empty:
        return []
    n_bins = min(10, series.nunique())
    if n_bins < 2:
        return []
    counts, edges = np.histogram(series.astype(float), bins=n_bins)
    return [
        ChartDataPoint(label=f"{edges[i]:.1f}–{edges[i + 1]:.1f}", value=float(cnt))
        for i, cnt in enumerate(counts)
        if _finite(float(cnt))
    ]


def _scatter_data(df: pd.DataFrame, x_col: str, y_col: str) -> list[ChartDataPoint]:
    """Return up to 100 (x, y) pairs; label = str(x), value = y."""
    if x_col not in df.columns or y_col not in df.columns:
        return []
    subset = df[[x_col, y_col]].dropna().head(100)
    return [
        ChartDataPoint(label=str(row[x_col]), value=float(row[y_col]))
        for _, row in subset.iterrows()
        if _finite(float(row[y_col]))
    ]


def _finite(v: float) -> bool:
    return not (math.isnan(v) or math.isinf(v))


# ---------------------------------------------------------------------------
# Insight builders
# ---------------------------------------------------------------------------

def _build_insights(profile: dict, classification: dict, anomalies: dict) -> list[str]:
    insights: list[str] = []

    domain     = classification["domain"].replace("_", " ").title()
    confidence = classification["confidence"]
    insights.append(
        f"Dataset classified as '{domain}' with {confidence}% confidence "
        f"based on columns: {', '.join(classification['matched_columns'][:4])}."
    )

    dupe = anomalies.get("duplicate_warning")
    insights.append(
        dupe["message"] if dupe
        else "No duplicate rows detected — data integrity is clean."
    )

    missing_warnings = anomalies.get("missing_data_warnings", [])
    if not missing_warnings:
        insights.append("Dataset is complete — no missing values found.")
    else:
        insights.append(missing_warnings[0]["message"])
        if len(missing_warnings) > 1:
            other_cols = [w["column"] for w in missing_warnings[1:4]]
            insights.append(f"Additional columns with missing data: {', '.join(other_cols)}.")

    unusual       = anomalies.get("unusual_values", [])
    high_outliers = [u for u in unusual if u.get("severity") in ("high", "medium")]
    if high_outliers:
        col_list = ", ".join(u["column"] for u in high_outliers[:3])
        insights.append(
            f"Significant outliers detected in: {col_list}. "
            "Review these values before modelling."
        )

    skewed = anomalies.get("suspicious_distributions", [])
    if skewed:
        insights.append(skewed[0]["message"])

    n_num = len(profile["numeric_columns"])
    n_cat = len(profile["categorical_columns"])
    n_dt  = len(profile["datetime_columns"])
    insights.append(
        f"Column breakdown: {n_num} numeric, {n_cat} categorical"
        + (f", {n_dt} datetime" if n_dt else "")
        + f" out of {profile['column_count']} total."
    )

    return insights


def _build_summary(profile: dict, classification: dict) -> str:
    domain = classification["domain"].replace("_", " ").title()
    return (
        f"{domain} dataset — {profile['row_count']:,} rows, "
        f"{profile['column_count']} columns "
        f"({len(profile['numeric_columns'])} numeric, "
        f"{len(profile['categorical_columns'])} categorical). "
        f"Missing values: {profile['total_missing_values']:,}. "
        f"Duplicate rows: {profile['duplicate_rows']:,}."
    )
