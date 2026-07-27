"""
InsightPilot AI — shared LLM client.

Provides a single Gemini → OpenRouter provider chain used by all services
that call an LLM.  Eliminates the copy-pasted retry/parse logic that
previously lived in chart_insights.py, copilot.py, and llm_business_context.py.

Usage
-----
    from services.llm_client import LLMClient

    _client = LLMClient()

    result = await _client.complete_json(
        system_prompt=MY_SYSTEM_PROMPT,
        user_message=payload,
        required_keys=frozenset({"answer", "confidence"}),
        max_tokens=512,
        temperature=0.15,
        service_name="MyService",
    )
    # result is a validated dict — raises RuntimeError only when BOTH providers
    # fail after retries; callers are responsible for catching and falling back.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
from google import genai
from google.genai import errors as genai_errors

from services.config import (
    GEMINI_MODEL,
    OPENROUTER_MODEL,
    OPENROUTER_URL,
    OPENROUTER_HEADERS_BASE,
)

logger = logging.getLogger(__name__)

_RETRY_ATTEMPTS = 2


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def strip_markdown_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences from LLM output."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    stripped = stripped.lstrip("`")
    if stripped.startswith("json"):
        stripped = stripped[4:]
    if "```" in stripped:
        stripped = stripped[: stripped.rfind("```")]
    return stripped.strip()


def parse_json(text: str, required_keys: frozenset[str]) -> dict[str, Any]:
    """
    Parse raw LLM output as JSON and assert all required keys are present.
    Strips markdown code fences before parsing.

    Raises
    ------
    ValueError
        On malformed JSON or missing required keys.
    """
    try:
        data: dict[str, Any] = json.loads(strip_markdown_fences(text))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON decode error: {exc}") from exc

    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"LLM response missing required keys: {sorted(missing)}")

    return data


# ---------------------------------------------------------------------------
# LLMClient
# ---------------------------------------------------------------------------


class LLMClient:
    """
    Shared Gemini → OpenRouter provider chain.

    - Gemini client is initialised lazily (one instance per LLMClient).
    - complete_json() tries Gemini, then OpenRouter, with up to
      _RETRY_ATTEMPTS parse retries per provider.
    - Raises RuntimeError only when both providers fail; callers decide
      the fallback strategy.
    """

    def __init__(self) -> None:
        self._gemini_client: genai.Client | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete_json(
        self,
        system_prompt: str,
        user_message: str,
        required_keys: frozenset[str],
        max_tokens: int,
        temperature: float,
        timeout: float = 30.0,
        service_name: str = "LLM",
    ) -> dict[str, Any]:
        """
        Call Gemini (then OpenRouter on failure) and return a validated JSON dict.

        Parameters
        ----------
        system_prompt   : LLM system instruction
        user_message    : User-turn payload (typically serialised JSON)
        required_keys   : Keys that must be present in the parsed response
        max_tokens      : Maximum output tokens
        temperature     : Sampling temperature
        timeout         : HTTP timeout for OpenRouter requests (seconds)
        service_name    : Short label used in log messages (e.g. "ChartInsights")

        Raises
        ------
        RuntimeError
            When both providers fail after all retry attempts.
        """
        # --- 1. Gemini ---
        if os.getenv("GEMINI_API_KEY"):
            try:
                return await self._with_retry(
                    self._call_gemini,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    required_keys=required_keys,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout,
                    service_name=service_name,
                    provider="Gemini",
                )
            except genai_errors.APIError as exc:
                logger.warning("%s Gemini API error (%s) — trying OpenRouter.", service_name, exc)
            except Exception as exc:
                logger.warning("%s Gemini failed (%s) — trying OpenRouter.", service_name, exc)
        else:
            logger.debug("GEMINI_API_KEY not set — skipping Gemini for %s.", service_name)

        # --- 2. OpenRouter ---
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                return await self._with_retry(
                    self._call_openrouter,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    required_keys=required_keys,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout,
                    service_name=service_name,
                    provider="OpenRouter",
                )
            except Exception as exc:
                raise RuntimeError(
                    f"{service_name}: OpenRouter failed after {_RETRY_ATTEMPTS} attempts: {exc}"
                ) from exc
        else:
            logger.debug("OPENROUTER_API_KEY not set — skipping OpenRouter for %s.", service_name)

        raise RuntimeError(
            f"{service_name}: No LLM provider available (both GEMINI_API_KEY and "
            "OPENROUTER_API_KEY are unset)."
        )

    # ------------------------------------------------------------------
    # Internal — retry wrapper
    # ------------------------------------------------------------------

    async def _with_retry(
        self,
        call_fn,
        *,
        system_prompt: str,
        user_message: str,
        required_keys: frozenset[str],
        max_tokens: int,
        temperature: float,
        timeout: float,
        service_name: str,
        provider: str,
    ) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(_RETRY_ATTEMPTS):
            raw = await call_fn(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            try:
                return parse_json(raw, required_keys)
            except ValueError as exc:
                last_exc = exc
                if attempt == 0:
                    logger.warning(
                        "%s %s JSON invalid (attempt 1: %s) — retrying.",
                        service_name, provider, exc,
                    )
        raise RuntimeError(
            f"{service_name}: {provider} returned invalid JSON after "
            f"{_RETRY_ATTEMPTS} attempts: {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------
    # Internal — Gemini
    # ------------------------------------------------------------------

    def _get_gemini_client(self) -> genai.Client:
        if self._gemini_client is None:
            self._gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        return self._gemini_client

    async def _call_gemini(
        self,
        *,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float,
        timeout: float,  # unused by Gemini SDK but kept for uniform signature
    ) -> str:
        response = await self._get_gemini_client().aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        return response.text

    # ------------------------------------------------------------------
    # Internal — OpenRouter
    # ------------------------------------------------------------------

    async def _call_openrouter(
        self,
        *,
        system_prompt: str,
        user_message: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> str:
        headers = {
            **OPENROUTER_HEADERS_BASE,
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        }
        body = {
            "model": OPENROUTER_MODEL,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(OPENROUTER_URL, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]
