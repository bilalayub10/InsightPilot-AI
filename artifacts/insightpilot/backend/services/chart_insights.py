"""
InsightPilot AI — AI Chart Insight Engine.

For every generated chart, produces a structured explanation grounded
exclusively in the supplied data.  Never hallucinate.

Output schema:
    { title, summary, business_impact, recommendation, confidence }

Provider chain (first success wins):
    1. Google Gemini   (GEMINI_API_KEY)
    2. OpenRouter      (OPENROUTER_API_KEY)
    3. Deterministic   (pattern-based, never fails)
"""

from __future__ import annotations

import json
import logging
import statistics
from typing import Any

from services.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_OUTPUT_TOKENS = 512
_TEMPERATURE = 0.15
_TIMEOUT = 25.0

_SYSTEM_PROMPT = """\
You are a senior data analyst generating concise chart commentary for an executive dashboard.

STRICT RULES — no exceptions:
- Describe ONLY patterns, values, and trends that are EXPLICITLY present in the data provided.
- Do NOT mention any data, statistics, or patterns not visible in the supplied JSON.
- Do NOT reference AI, LLMs, Gemini, or OpenRouter.
- Do NOT use generic filler phrases ("it is worth noting", "it is important to mention").
- Every sentence must be directly traceable to a specific data point or range.
- If the data is insufficient to make a confident statement, say so briefly.
- Write in executive prose: concise, direct, no jargon.

You will receive:
- chart: the chart specification (type, axes, title, business question)
- data: the actual aggregated data points (label/value pairs)
- context: supporting signals (domain, KPIs, anomalies)

Return VALID JSON ONLY — no markdown, no code fences:
{
  "title": "short insight title (5-8 words max)",
  "summary": "1-2 sentences describing what the data shows",
  "business_impact": "1 sentence on the business implication",
  "recommendation": "1 actionable sentence starting with a verb",
  "confidence": 0
}

confidence must be an integer 0-100 reflecting how clearly the data supports the insight."""

_REQUIRED_KEYS: frozenset[str] = frozenset({
    "title", "summary", "business_impact", "recommendation", "confidence",
})


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ChartInsightService:
    """
    Generates AI-powered chart insights.

    Provider chain: Gemini → OpenRouter → Deterministic fallback.
    Never raises; always returns a valid dict.
    """

    def __init__(self) -> None:
        self._client = LLMClient()
        self._fallback = _DeterministicInsights()

    async def generate(
        self,
        chart_spec: dict[str, Any],
        data_points: list[dict[str, Any]],
        profile: dict[str, Any],
        kpis: list[dict[str, Any]],
        anomalies: dict[str, Any],
        domain: str,
    ) -> dict[str, Any]:
        """
        Generate a ChartInsight dict.  Never raises.  Never returns None.
        """
        payload = _serialise_payload(chart_spec, data_points, profile, kpis, anomalies, domain)

        try:
            result = await self._client.complete_json(
                system_prompt=_SYSTEM_PROMPT,
                user_message=payload,
                required_keys=_REQUIRED_KEYS,
                max_tokens=_MAX_OUTPUT_TOKENS,
                temperature=_TEMPERATURE,
                timeout=_TIMEOUT,
                service_name="ChartInsights",
            )
            # Clamp confidence
            result["confidence"] = max(0, min(100, int(result.get("confidence", 50))))
            return result
        except Exception as exc:
            logger.info(
                "ChartInsights: LLM unavailable (%s) — using deterministic fallback for '%s'.",
                exc, chart_spec.get("title"),
            )
            return self._fallback.generate(chart_spec, data_points, domain)


# ---------------------------------------------------------------------------
# Deterministic fallback
# ---------------------------------------------------------------------------


class _DeterministicInsights:
    """
    Generates chart insights purely from the data points without any LLM.
    Produces pattern-based descriptions grounded only in the actual values.
    """

    def generate(
        self,
        chart_spec: dict[str, Any],
        data_points: list[dict[str, Any]],
        domain: str,
    ) -> dict[str, Any]:
        chart_type = chart_spec.get("type", "bar")
        title      = chart_spec.get("title", "Chart")
        x_col      = chart_spec.get("x", "category")
        y_col      = chart_spec.get("y", "value")

        if not data_points:
            return {
                "title": "Insufficient Data",
                "summary": f"No data points are available to analyse {title}.",
                "business_impact": "Analysis cannot be completed without data.",
                "recommendation": "Verify the dataset contains valid values for this chart's columns.",
                "confidence": 10,
            }

        values  = [float(p["value"]) for p in data_points]
        labels  = [str(p["label"]) for p in data_points]
        n       = len(values)
        total   = sum(values)
        max_v   = max(values)
        min_v   = min(values)
        max_lbl = labels[values.index(max_v)]
        min_lbl = labels[values.index(min_v)]

        if chart_type == "line":
            return self._line(title, x_col, y_col, labels, values, n, max_v, min_v, max_lbl, min_lbl)
        if chart_type == "bar":
            return self._bar(title, x_col, y_col, labels, values, n, total, max_v, min_v, max_lbl)
        if chart_type == "pie":
            return self._pie(title, x_col, labels, values, n, total, max_v, max_lbl)
        if chart_type == "histogram":
            return self._histogram(title, x_col, labels, values, n, max_v, max_lbl)
        if chart_type == "scatter":
            return self._scatter(title, x_col, y_col, n, values, labels)
        return self._generic(title, n, min_v, max_v, sum(values) / n)

    def _line(self, title, x, y, labels, values, n, max_v, min_v, max_lbl, min_lbl):
        mid = max(n // 2, 1)
        first_avg  = statistics.mean(values[:mid])
        second_avg = statistics.mean(values[mid:]) if n > 1 else first_avg
        pct = ((second_avg - first_avg) / first_avg * 100) if first_avg else 0

        if pct > 8:
            trend_word, dir_word = "upward", "increased"
            impact = "Sustained growth suggests positive momentum; monitor whether it is seasonal or structural."
            rec = f"Investigate the drivers behind the rise from {labels[0]} to {labels[-1]} to capitalise on the trend."
        elif pct < -8:
            trend_word, dir_word = "downward", "declined"
            impact = "A declining trajectory may signal demand erosion, churn, or operational inefficiency."
            rec = f"Identify the inflection point near {max_lbl} where values peaked and investigate root causes of the subsequent drop."
        else:
            trend_word, dir_word = "stable", "remained relatively flat"
            impact = "Consistent performance indicates stability, but limited growth headroom."
            rec = "Identify the levers that could break the plateau and accelerate growth."

        mean = sum(values) / n
        pct_range = abs(max_v - min_v) / mean * 100 if mean else 0
        volatility = "high" if pct_range > 50 else "moderate" if pct_range > 20 else "low"

        summary = (
            f"{title} shows a {trend_word} trend: {y} {dir_word} from "
            f"{labels[0]} to {labels[-1]}, peaking at {max_lbl} "
            f"({max_v:,.1f}) and reaching a low of {min_lbl} ({min_v:,.1f}). "
            f"Volatility is {volatility} ({pct_range:.0f}% spread relative to mean)."
        )
        return {"title": f"{trend_word.title()} Trend Detected", "summary": summary,
                "business_impact": impact, "recommendation": rec, "confidence": 62}

    def _bar(self, title, x, y, labels, values, n, total, max_v, min_v, max_lbl):
        top_share = (max_v / total * 100) if total else 0
        bot_lbl   = labels[values.index(min_v)]
        ratio     = (max_v / min_v) if min_v else float("inf")

        summary = (
            f"{max_lbl} leads with {max_v:,.1f}, representing {top_share:.1f}% of the "
            f"total across {n} categories. The lowest performer is {bot_lbl} at "
            f"{min_v:,.1f} — a {ratio:.1f}× gap between top and bottom."
        )
        impact = (
            f"Heavy concentration in {max_lbl} introduces dependency risk "
            "if that category underperforms."
        )
        rec = (
            f"Assess whether investment in lower-performing categories can reduce "
            f"the gap with {max_lbl}, or whether the concentration is strategically intentional."
        )
        return {"title": f"{max_lbl} Dominates {y}", "summary": summary,
                "business_impact": impact, "recommendation": rec, "confidence": 65}

    def _pie(self, title, x, labels, values, n, total, max_v, max_lbl):
        top_pct  = (max_v / total * 100) if total else 0
        rest_pct = 100 - top_pct

        summary = (
            f"{max_lbl} accounts for {top_pct:.1f}% of total {x} distribution "
            f"across {n} segments. The remaining {n - 1} segment(s) collectively "
            f"represent {rest_pct:.1f}%."
        )
        impact = (
            "High share concentration in a single segment amplifies exposure "
            "to segment-specific risks."
            if top_pct > 50
            else "Distribution is relatively balanced across segments, reducing concentration risk."
        )
        rec = (
            f"Monitor whether {max_lbl}'s share is growing over time and evaluate "
            "diversification if concentration exceeds risk thresholds."
        )
        return {"title": f"{max_lbl} Leads at {top_pct:.0f}%", "summary": summary,
                "business_impact": impact, "recommendation": rec, "confidence": 63}

    def _histogram(self, title, x, labels, values, n, max_v, max_lbl):
        peak_idx = values.index(max_v)

        if peak_idx <= n // 3:
            shape  = "right-skewed (most values concentrated at the lower end)"
            impact = "The right-skewed distribution suggests many small-value entries with rare high-value outliers."
            rec    = "Investigate the high-value tail — those entries may represent the most impactful cases."
        elif peak_idx >= n - n // 3:
            shape  = "left-skewed (most values concentrated at the upper end)"
            impact = "Concentration at higher values may indicate a premium or high-performance dataset."
            rec    = "Validate that the low-end tail does not contain data quality issues masking the true range."
        else:
            shape  = "approximately bell-shaped (values cluster around the middle)"
            impact = "A roughly normal distribution simplifies modelling assumptions and risk estimation."
            rec    = "Focus analysis on the tails — extreme values at both ends may represent outlier risks or opportunities."

        summary = (
            f"The distribution of {x} spans {labels[0]} to {labels[-1]} across {n} bins. "
            f"The highest frequency is in the {max_lbl} range with {max_v:,.0f} observations. "
            f"The distribution appears {shape}."
        )
        return {"title": f"{x} Distribution Shape", "summary": summary,
                "business_impact": impact, "recommendation": rec, "confidence": 60}

    def _scatter(self, title, x, y, n, values, labels):
        numeric_labels: list[float] = []
        for lbl in labels:
            try:
                numeric_labels.append(float(lbl))
            except (ValueError, TypeError):
                numeric_labels = []
                break

        if len(numeric_labels) == n and n > 3:
            covariance = sum(
                (lx - sum(numeric_labels) / n) * (ly - sum(values) / n)
                for lx, ly in zip(numeric_labels, values)
            )
            direction = "positive" if covariance > 0 else "negative" if covariance < 0 else "no clear"
            corr_desc = f"The data suggests a {direction} correlation between {x} and {y}."
        else:
            corr_desc = f"The scatter plot maps {x} against {y} across {n} data points."

        summary = (
            f"{corr_desc} Values of {y} range from {min(values):,.1f} to {max(values):,.1f} "
            f"across the {x} axis."
        )
        impact = f"Understanding the {x}/{y} relationship can inform forecasting and resource allocation."
        rec    = f"Compute the Pearson correlation coefficient between {x} and {y} to quantify and validate this relationship."
        return {"title": f"{x} vs {y} Relationship", "summary": summary,
                "business_impact": impact, "recommendation": rec, "confidence": 55}

    def _generic(self, title, n, min_v, max_v, mean):
        summary = (
            f"{title} contains {n} data points. Values range from {min_v:,.1f} "
            f"to {max_v:,.1f} with a mean of {mean:,.1f}."
        )
        return {"title": "Data Overview", "summary": summary,
                "business_impact": "Further analysis is required to assess the business implications.",
                "recommendation": "Segment the data by key categorical dimensions to surface meaningful patterns.",
                "confidence": 45}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _serialise_payload(
    chart_spec: dict[str, Any],
    data_points: list[dict[str, Any]],
    profile: dict[str, Any],
    kpis: list[dict[str, Any]],
    anomalies: dict[str, Any],
    domain: str,
) -> str:
    lean_profile = {
        "row_count":           profile.get("row_count"),
        "column_count":        profile.get("column_count"),
        "numeric_columns":     profile.get("numeric_columns", []),
        "categorical_columns": profile.get("categorical_columns", []),
        "total_missing_values": profile.get("total_missing_values"),
    }
    lean_kpis = [{"label": k.get("label"), "value": k.get("value")} for k in kpis[:5]]
    chart_cols = {chart_spec.get("x"), chart_spec.get("y")}
    relevant_anomalies = [
        u for u in anomalies.get("unusual_values", [])
        if u.get("column") in chart_cols
    ][:3]

    return json.dumps(
        {
            "chart": {
                "type":              chart_spec.get("type"),
                "title":             chart_spec.get("title"),
                "x_axis":            chart_spec.get("x"),
                "y_axis":            chart_spec.get("y"),
                "aggregation":       chart_spec.get("aggregation"),
                "business_question": chart_spec.get("business_question"),
            },
            "data": data_points,
            "context": {
                "domain":           domain,
                "dataset_rows":     lean_profile["row_count"],
                "top_kpis":         lean_kpis,
                "column_anomalies": relevant_anomalies,
            },
        },
        default=str,
    )
