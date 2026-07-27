"""
InsightPilot AI — AI Copilot Service.

Accepts a structured business context and a natural-language question,
then calls Gemini (with OpenRouter fallback) to produce a Senior BI
Consultant response.

Design rules:
  - NEVER send raw DataFrame rows or CSV text to the LLM.
  - Only send structured summaries derived from existing services.
  - All business logic stays here; the route is thin.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from services.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_OUTPUT_TOKENS = 2048
_TEMPERATURE = 0.3
_TIMEOUT = 45.0

_SYSTEM_PROMPT = """\
You are a Senior Business Intelligence Consultant advising C-suite executives.

Your mandate:
- Answer questions concisely and with evidence from the data context provided.
- Never invent numbers, metrics, or trends not present in the supplied JSON.
- If information is unavailable, say so explicitly — do not fill gaps with assumptions.
- Do not mention Google, Gemini, OpenRouter, AI, LLM, or any model names in your output.
- Write like a McKinsey or Bain partner briefing a CEO: direct, precise, professional.
- Keep the "answer" field to 3–5 sentences maximum.
- Keep "reasoning" to 2–3 sentences explaining what data evidence supports your answer.
- Suggest 3 concise follow-up questions the executive might ask next.
- Confidence (0–100) reflects how completely the supplied data answers the question.

Return VALID JSON ONLY — no markdown fences, no prose outside JSON:
{
  "answer": "string",
  "reasoning": "string",
  "confidence": 0,
  "follow_up_questions": ["string", "string", "string"]
}"""

_REQUIRED_KEYS: frozenset[str] = frozenset({
    "answer", "reasoning", "confidence", "follow_up_questions"
})

_FALLBACK_RESPONSE = {
    "answer": "I couldn't generate an AI response right now. Please check that your API key is valid and try again.",
    "reasoning": "The AI provider returned an error or was unavailable.",
    "confidence": 0,
    "follow_up_questions": [
        "What are the top KPIs in this dataset?",
        "Are there any anomalies I should know about?",
        "What does the executive summary say?",
    ],
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CopilotService:
    """
    Answers natural-language business questions about a dataset using LLMs.

    Caller must supply a pre-built business_context dict (from existing
    services) plus the user's question.  This service owns only the
    prompt-building and LLM invocation — no business logic.
    """

    def __init__(self) -> None:
        self._client = LLMClient()

    async def answer(
        self,
        business_context: dict[str, Any],
        question: str,
    ) -> dict[str, Any]:
        """
        Generate a BI Consultant response to `question` grounded in
        `business_context`.  Never raises; returns a safe fallback on error.
        """
        payload = _build_prompt_payload(business_context, question)

        try:
            result = await self._client.complete_json(
                system_prompt=_SYSTEM_PROMPT,
                user_message=payload,
                required_keys=_REQUIRED_KEYS,
                max_tokens=_MAX_OUTPUT_TOKENS,
                temperature=_TEMPERATURE,
                timeout=_TIMEOUT,
                service_name="Copilot",
            )
            # Clamp confidence
            try:
                result["confidence"] = max(0, min(100, int(result["confidence"])))
            except (TypeError, ValueError):
                result["confidence"] = 50
            return result
        except Exception as exc:
            logger.info("Copilot: both LLM providers unavailable (%s) — returning fallback.", exc)
            return _FALLBACK_RESPONSE.copy()


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _build_prompt_payload(context: dict[str, Any], question: str) -> str:
    """
    Serialise the business context to a concise JSON string and append
    the user's question.  Raw data rows are never included.
    """
    return json.dumps(
        {
            "business_context": context,
            "user_question": question,
        },
        default=str,
        ensure_ascii=False,
    )
