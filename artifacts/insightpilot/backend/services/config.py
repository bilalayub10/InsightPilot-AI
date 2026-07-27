"""
InsightPilot AI — shared LLM configuration constants.

All services that call Gemini or OpenRouter import from here so that
environment-variable names and default values are defined exactly once.
"""

import os

# Model selection
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

# OpenRouter endpoint
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Request headers shared by every OpenRouter call
OPENROUTER_HEADERS_BASE: dict[str, str] = {
    "Content-Type": "application/json",
    "HTTP-Referer": "https://insightpilot.app",
    "X-Title": "InsightPilot AI",
}
