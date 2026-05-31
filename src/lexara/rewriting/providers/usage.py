"""Token/cost logging hooks for LLM providers."""

from __future__ import annotations

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


def log_provider_failure(
    provider_name: str,
    *,
    model: str | None,
    attempt: int,
    error: BaseException,
) -> None:
    logger.warning(
        "llm_completion_failed",
        extra={
            "extra": {
                "provider": provider_name,
                "model": model,
                "attempt": attempt,
                "error_type": type(error).__name__,
                "error": str(error)[:300],
            }
        },
    )


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
