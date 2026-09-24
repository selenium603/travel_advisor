"""LLM factory for OpenRouter or direct Gemini access."""

from crewai import LLM
from backend.config.settings import settings


def create_gemini_llm() -> LLM:
    """Create the configured travel-planning LLM."""
    if settings.openrouter_api_key:
        model = f"openrouter/{settings.openrouter_model.removeprefix('openrouter/')}"
    else:
        model = "gemini/gemini-2.0-flash"
    return LLM(
        model=model,
        max_retries=10,
        timeout=300,
    )
