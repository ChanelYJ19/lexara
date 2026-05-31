"""Token/cost logging hooks for LLM providers."""

from __future__ import annotations

from typing import Callable

from lexara.logging_config import get_logger
from lexara.rewriting.providers.base import ProviderResult, UsageLogger

logger = get_logger("lexara.llm")

# USD per 1M tokens (input, output) — update as pricing changes.
_MODEL_COST_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _MODEL_COST_PER_1M.get(model)
    if not rates:
        return 0.0
    in_rate, out_rate = rates
    return round(
        (prompt_tokens / 1_000_000) * in_rate
        + (completion_tokens / 1_000_000) * out_rate,
        6,
    )


def default_usage_logger(provider_name: str) -> UsageLogger:
    def _log(result: ProviderResult) -> None:
        u = result.usage
        logger.info(
            "llm_completion",
            extra={
                "extra": {
                    "provider": provider_name,
                    "model": result.model,
                    "prompt_tokens": u.prompt_tokens,
                    "completion_tokens": u.completion_tokens,
                    "total_tokens": u.total_tokens,
                    "estimated_cost_usd": u.estimated_cost_usd,
                }
            },
        )

    return _log


def attach_cost(result: ProviderResult) -> ProviderResult:
    if (
        result.model
        and result.usage.prompt_tokens is not None
        and result.usage.completion_tokens is not None
    ):
        result.usage.estimated_cost_usd = estimate_cost_usd(
            result.model,
            result.usage.prompt_tokens,
            result.usage.completion_tokens,
        )
    return result
