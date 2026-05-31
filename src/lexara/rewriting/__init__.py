"""Rewrite pipeline: LLM providers and score → rewrite → rescore."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexara.rewriting.pipeline import RewriteOutcome
    from lexara.rewriting.providers.base import LLMProvider
    from lexara.rewriting.providers.mock import MockLLMProvider

__all__ = [
    "RewriteOutcome",
    "run_rewrite",
    "LLMProvider",
    "MockLLMProvider",
    "build_provider",
]


def __getattr__(name: str):
    if name == "RewriteOutcome":
        from lexara.rewriting.pipeline import RewriteOutcome

        return RewriteOutcome
    if name == "run_rewrite":
        from lexara.rewriting.pipeline import run_rewrite

        return run_rewrite
    if name == "LLMProvider":
        from lexara.rewriting.providers.base import LLMProvider

        return LLMProvider
    if name == "MockLLMProvider":
        from lexara.rewriting.providers.mock import MockLLMProvider

        return MockLLMProvider
    if name == "build_provider":
        from lexara.rewriting.providers import build_provider

        return build_provider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
