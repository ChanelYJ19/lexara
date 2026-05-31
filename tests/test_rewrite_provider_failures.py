"""Rewrite pipeline behavior when the LLM provider fails."""

from __future__ import annotations

from lexara.models.rewrite import RewriteRequest
from lexara.rewriting.providers.base import LLMProvider, ProviderResult, RewriteInstruction
from lexara.rewriting.providers.errors import ProviderError
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService

TEXT = (
    "The committee will subsequently utilize numerous additional resources to "
    "facilitate the comprehensive demonstration."
)


class _FailingProvider(LLMProvider):
    name = "failing"

    def complete(self, instruction: RewriteInstruction) -> ProviderResult:
        raise ProviderError("Simulated outage", code="provider_error")


class _EmptyProvider(LLMProvider):
    name = "empty"

    def complete(self, instruction: RewriteInstruction) -> ProviderResult:
        return ProviderResult(text="   ", model="empty")


class _RecoveringProvider(LLMProvider):
    name = "recovering"
    calls = 0

    def complete(self, instruction: RewriteInstruction) -> ProviderResult:
        _RecoveringProvider.calls += 1
        if _RecoveringProvider.calls == 1:
            raise ProviderError("First pass failed", code="provider_transient_error")
        return ProviderResult(
            text="The group will use help. They will show the plan.",
            model="recovering",
        )


def test_all_provider_failures_return_original_with_warnings():
    result = RewriteService(_FailingProvider(), ScoringService()).rewrite(
        RewriteRequest(text=TEXT, target_grade=5, max_passes=2)
    )
    assert result.rewritten_text == TEXT
    assert result.input.text == TEXT
    assert result.execution.degraded is True
    assert len(result.execution.warnings) == 2
    assert result.execution.provider_calls_failed == 2
    assert result.execution.passes_used == 0


def test_empty_response_emits_warning_and_keeps_text():
    result = RewriteService(_EmptyProvider(), ScoringService()).rewrite(
        RewriteRequest(text=TEXT, target_grade=5, max_passes=1)
    )
    assert any(w.code == "empty_response" for w in result.execution.warnings)
    assert result.execution.degraded is True


def test_recovers_after_transient_failure():
    _RecoveringProvider.calls = 0
    result = RewriteService(_RecoveringProvider(), ScoringService()).rewrite(
        RewriteRequest(text=TEXT, target_grade=5, max_passes=2)
    )
    assert result.execution.warnings[0].code == "provider_transient_error"
    assert result.rewritten_text != TEXT
    assert result.execution.degraded is False
    assert result.execution.provider_calls_failed == 1
    assert result.execution.passes_used >= 1
    assert result.execution.provider_calls_attempted == 2
