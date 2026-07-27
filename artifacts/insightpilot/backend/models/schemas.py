"""
InsightPilot AI — Pydantic response/request schemas.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DatasetStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    processing = "processing"
    done = "done"
    error = "error"


class Trend(str, Enum):
    up = "up"
    down = "down"
    flat = "flat"


# ---------------------------------------------------------------------------
# Health schemas
# ---------------------------------------------------------------------------


class HealthStatus(BaseModel):
    status: str


class ServiceInfo(BaseModel):
    status: str
    version: str
    service: str
    uptime: float


# ---------------------------------------------------------------------------
# Upload schemas
# ---------------------------------------------------------------------------


class UploadResult(BaseModel):
    datasetId: str
    name: str
    rowCount: int
    columnCount: int
    columns: list[str]
    fileSizeKb: float
    status: DatasetStatus
    uploadedAt: str
    fileType: str = "CSV"
    worksheetName: Optional[str] = None
    domain: Optional[str] = None


# ---------------------------------------------------------------------------
# Analyze schemas
# ---------------------------------------------------------------------------


class AnalyzeInput(BaseModel):
    datasetId: str


class KpiMetric(BaseModel):
    label: str
    value: str
    change: float
    trend: Trend


class ChartDataPoint(BaseModel):
    label: str
    value: float


class ChartInsight(BaseModel):
    """AI-generated explanation for a single chart."""
    title: str
    summary: str
    business_impact: str
    recommendation: str
    confidence: int  # 0–100


class ChartSpec(BaseModel):
    """A single chart recommendation with pre-computed data points."""
    type: str                   # "line" | "bar" | "pie" | "histogram" | "scatter"
    x: str                      # column used as x-axis / category axis
    y: str                      # column used as y-axis / value axis (or "count"/"frequency")
    title: str
    priority: int               # business value rank 1–100
    confidence: float           # column-match confidence 0.0–1.0
    reason: str                 # why this chart was chosen
    business_question: str      # the analytic question this chart answers
    aggregation: str            # "sum" | "mean" | "count"
    data: list[ChartDataPoint]  # pre-computed, ready to render
    insight: Optional[ChartInsight] = None  # AI-generated chart explanation


class PriorityAction(BaseModel):
    title: str
    priority: str  # "High" | "Medium" | "Low"
    reason: str


class BusinessContext(BaseModel):
    executive_summary: str
    strengths: list[str]
    risks: list[str]
    opportunities: list[str]
    recommended_questions: list[str]
    priority_actions: list[PriorityAction]
    analysis_confidence: int
    dataset_quality_score: int


class CeoBriefingHealth(BaseModel):
    score: int
    status: str


class CeoBriefing(BaseModel):
    business_domain: str
    confidence: int
    overall_health: CeoBriefingHealth
    urgency: str
    biggest_risk: str
    top_opportunity: str
    priority_action: str
    executive_summary: str
    key_takeaways: list[str]


class AnalyzeResult(BaseModel):
    datasetId: str
    domain: str = "generic"                      # detected business domain key (e.g. "sales", "hr")
    status: DatasetStatus
    summary: str
    kpis: list[KpiMetric]
    charts: list[ChartSpec]                      # full chart specs with data
    trendData: list[ChartDataPoint]              # backward compat: first line chart data
    distributionData: list[ChartDataPoint]       # backward compat: first bar/pie chart data
    insights: list[str]
    analyzedAt: str
    businessContext: Optional[BusinessContext] = None
    ceoBriefing: Optional[CeoBriefing] = None


# ---------------------------------------------------------------------------
# Copilot schemas
# ---------------------------------------------------------------------------


class CopilotInput(BaseModel):
    datasetId: str
    question: str


class CopilotResponse(BaseModel):
    answer: str
    reasoning: str
    confidence: int
    follow_up_questions: list[str]
    domain: str
