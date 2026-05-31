"""Provider factory."""

from __future__ import annotations

from lexara.config import Settings
from lexara.rewriting.providers.base import LLMProvider, RewriteInstruction
from lexara.rewriting.providers.mock import MockLLMProvider


def build_provider(settings: Settings) -> LLMProvider:
    name = settings.llm_provider.lower()
    if name == "mock":
        return MockLLMProvider()
    if name == "openai":
        from lexara.rewriting.providers.openai import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.openai_api_key or "",
            model=settings.openai_model,
            timeout_seconds=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
            max_completion_tokens=settings.openai_max_completion_tokens,
        )
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider!r}")


__all__ = [
    "LLMProvider",
    "RewriteInstruction",
    "MockLLMProvider",
    "build_provider",
]
