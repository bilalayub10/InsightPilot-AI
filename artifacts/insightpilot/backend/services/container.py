"""
InsightPilot AI — service container.

Module-level singletons for all stateless services.  Both the /api/analyze
and /api/copilot routes previously declared identical sets of singletons;
importing from here eliminates that duplication.

All services are stateless and safe to share across requests.
"""

from services.analytics import AnalyticsService
from services.business_classifier import BusinessClassifier
from services.kpi_detector import KPIDetector
from services.chart_planner import ChartPlanner
from services.anomaly_detector import AnomalyDetector
from services.file_loader import FileLoader
from services.llm_business_context import LLMBusinessContext
from services.ceo_briefing import CEOBriefingService
from services.chart_insights import ChartInsightService
from services.copilot import CopilotService

analytics = AnalyticsService()
classifier = BusinessClassifier()
kpi_detector = KPIDetector()
chart_planner = ChartPlanner()
anomaly_detector = AnomalyDetector()
file_loader = FileLoader()
context_builder = LLMBusinessContext()
ceo_briefing_svc = CEOBriefingService()
chart_insights_svc = ChartInsightService()
copilot_svc = CopilotService()
