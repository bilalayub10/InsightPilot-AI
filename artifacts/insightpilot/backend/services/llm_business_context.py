"""
InsightPilot AI — LLM-powered Business Context Builder.

Tries providers in order until one succeeds:
  1. Google Gemini   (GEMINI_API_KEY)
  2. OpenRouter      (OPENROUTER_API_KEY)
  3. Deterministic   (BusinessContextBuilder — never fails)

The API contract is always honoured: build() never raises, never returns None.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from services.llm_client import LLMClient
from services.business_context import BusinessContextBuilder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_OUTPUT_TOKENS = 2048
_TEMPERATURE = 0.2
_TIMEOUT = 30.0

_SYSTEM_PROMPT = """\
You are an experienced Business Intelligence Consultant producing executive analysis reports.

Strict rules — no exceptions:
- Never invent statistics, KPIs, trends, or anomalies not present in the supplied JSON.
- Every statement must be directly supported by the data provided.
- If information is insufficient, state so explicitly — do not fill gaps with assumptions.
- Do not mention Google, Gemini, OpenRouter, AI, or LLM anywhere in your output.
- Write like a senior McKinsey or Bain consultant: concise, precise, executive language.
- Return VALID JSON ONLY. No markdown. No code fences. No prose outside JSON.

Return exactly this structure and nothing else:
{
  "executive_summary": "string",
  "strengths": ["string"],
  "risks": ["string"],
  "opportunities": ["string"],
  "recommended_questions": ["string"],
  "priority_actions": [{"title": "string", "priority": "High|Medium|Low", "reason": "string"}],
  "analysis_confidence": 0,
  "dataset_quality_score": 0
}"""

_REQUIRED_KEYS: frozenset[str] = frozenset({
    "executive_summary", "strengths", "risks", "opportunities",
    "recommended_questions", "priority_actions",
    "analysis_confidence", "dataset_quality_score",
})


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class LLMBusinessContext:
    """
    Builds structured BusinessContext using LLMs.

    Provider chain (first success wins):
      1. Google Gemini  — requires GEMINI_API_KEY
      2. OpenRouter     — requires OPENROUTER_API_KEY
      3. Deterministic  — BusinessContextBuilder (always available)
    """

    def __init__(self) -> None:
        self._client = LLMClient()
        self._fallback = BusinessContextBuilder()

    async def build(
        self,
        profile: dict[str, Any],
        classification: dict[str, Any],
        kpis: list[dict[str, Any]],
        anomalies: dict[str, Any],
        chart_plan: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Generate BusinessContext; falls back through the provider chain on errors.

        Returns a dict matching the BusinessContext schema — never None, never raises.
        """
        payload = _serialise_payload(profile, classification, kpis, anomalies, chart_plan)
        domain  = classification.get("domain", "generic")

        try:
            return await self._client.complete_json(
                system_prompt=_SYSTEM_PROMPT,
                user_message=payload,
                required_keys=_REQUIRED_KEYS,
                max_tokens=_MAX_OUTPUT_TOKENS,
                temperature=_TEMPERATURE,
                timeout=_TIMEOUT,
                service_name="BusinessContext",
            )
        except Exception as exc:
            logger.info(
                "BusinessContext: LLM unavailable (%s) — using deterministic fallback.", exc
            )
            return self._fallback.build(
                profile=profile,
                domain=domain,
                classification=classification,
                kpis=kpis,
                anomalies=anomalies,
                chart_plan=chart_plan,
            )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _serialise_payload(
    profile: dict[str, Any],
    classification: dict[str, Any],
    kpis: list[dict[str, Any]],
    anomalies: dict[str, Any],
    chart_plan: list[dict[str, Any]],
) -> str:
    kpi_clean = [{k: v for k, v in kpi.items() if k != "raw_value"} for kpi in kpis]
    return json.dumps(
        {
            "profile":        profile,
            "classification": classification,
            "kpis":           kpi_clean,
            "anomalies":      anomalies,
            "chart_plan":     chart_plan,
        },
        default=str,
    )
