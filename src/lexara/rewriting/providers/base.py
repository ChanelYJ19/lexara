"""LLM provider abstraction for the rewrite step."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from lexara.rewriting.providers.errors import ProviderError


@dataclass
class RewriteInstruction:
    system_prompt: str
    user_prompt: str


@dataclass
class ProviderUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None


@dataclass
class ProviderResult:
    text: str
    model: str | None = None
    usage: ProviderUsage = field(default_factory=ProviderUsage)
    raw_content: str | None = None


UsageLogger = Callable[[ProviderResult], None]


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, instruction: RewriteInstruction) -> ProviderResult:
        """Return rewritten text and optional usage metadata."""

    def complete_safe(self, instruction: RewriteInstruction) -> ProviderResult:
        """Like ``complete`` but wraps unexpected errors as :class:`ProviderError`."""
        try:
            return self.complete(instruction)
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — boundary for provider impls
            raise ProviderError(
                f"{self.name} provider failed: {exc}",
                code="provider_error",
                details={"exception": type(exc).__name__},
            ) from exc
