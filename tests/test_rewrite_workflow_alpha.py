"""Alpha-readiness tests for the rewrite + rescore workflow."""

from __future__ import annotations

import pytest

from lexara.models.rewrite import RewriteRequest
from lexara.rewriting.providers.base import LLMProvider, ProviderResult, RewriteInstruction
from lexara.rewriting.providers.errors import ProviderError, ProviderParseError
from lexara.rewriting.providers.mock import MockLLMProvider
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService

COMPLEX = (
    "The committee will subsequently utilize numerous additional resources to "
    "facilitate the comprehensive demonstration, and they will require "
    "approximately seven days to obtain sufficient data because the analysis is "
    "fundamentally complex."
)

ALREADY_AT_TARGET = (
    "Photosynthesis lets plants make food from sunlight. "
    "Plants need sun and water to grow."
)


def _service(provider: LLMProvider | None = None) -> RewriteService:
    return RewriteService(provider or MockLLMProvider(), ScoringService())


def test_already_at_target_skips_rewrite():
    result = _service().rewrite(
        RewriteRequest(text=ALREADY_AT_TARGET, target_grade=5, tolerance=1.0, max_passes=5)
    )
    assert result.execution.skipped is True
    assert result.execution.skip_reason == "already_at_target"
    assert result.hit_target is True
    assert result.execution.passes_used == 0
    assert result.execution.provider_calls_attempted == 0
    assert result.output.text == ALREADY_AT_TARGET
    assert result.input.frameworks == result.output.frameworks
    assert result.outcome.grade_change == 0.0
    assert "Already at grade" in result.outcome.summary
    assert result.execution.warnings == []


def test_one_pass_success_with_wide_tolerance():
    result = _service().rewrite(
        RewriteRequest(text=COMPLEX, target_grade=5, max_passes=1, tolerance=3.0)
    )
    assert result.execution.passes_used == 1
    assert result.outcome.estimated_grade_to < result.outcome.estimated_grade_from
    assert result.input.frameworks and result.output.frameworks
    assert result.target.grade == 5


def test_multi_pass_improves_without_hit():
    class _GradualProvider(LLMProvider):
        name = "gradual"
        calls = 0

        def complete(self, instruction: RewriteInstruction) -> ProviderResult:
            _GradualProvider.calls += 1
            text = instruction.user_prompt.split("TEXT:\n")[-1]
            if _GradualProvider.calls == 1:
                simplified = text.replace("subsequently", "later").replace(
                    "approximately", "about"
                )
            else:
                simplified = text.replace("utilize", "use").replace(
                    "facilitate", "help"
                )
            return ProviderResult(text=simplified, model="gradual")

    _GradualProvider.calls = 0
    result = _service(_GradualProvider()).rewrite(
        RewriteRequest(text=COMPLEX, target_grade=2, max_passes=3, tolerance=0.5)
    )
    assert result.execution.passes_used == 3
    assert result.hit_target is False
    assert result.outcome.moved_toward_target is True
    assert result.outcome.estimated_grade_to < result.outcome.estimated_grade_from
    assert "toward target" in result.outcome.summary


def test_provider_failure_degrades_gracefully():
    class _FailingProvider(LLMProvider):
        name = "failing"

        def complete(self, instruction: RewriteInstruction) -> ProviderResult:
            raise ProviderError("Simulated outage", code="provider_error")

    result = _service(_FailingProvider()).rewrite(
        RewriteRequest(text=COMPLEX, target_grade=5, max_passes=2)
    )
    assert result.execution.degraded is True
    assert len(result.execution.warnings) == 2
    assert result.execution.warnings[0].code == "provider_error"
    assert result.output.text == COMPLEX
    assert result.execution.passes_used == 0
    assert result.input.frameworks
    assert result.hit_target is False


def test_malformed_provider_output_emits_parse_warning():
    class _MalformedProvider(LLMProvider):
        name = "malformed"

        def complete(self, instruction: RewriteInstruction) -> ProviderResult:
            raise ProviderParseError(
                "Expected JSON object with rewritten_text.",
                details={"preview": "not-json-at-all"},
            )

    result = _service(_MalformedProvider()).rewrite(
        RewriteRequest(text=COMPLEX, target_grade=5, max_passes=2)
    )
    assert any(w.code == "provider_parse_error" for w in result.execution.warnings)
    assert result.execution.degraded is True
    assert result.execution.passes_used == 0


def test_unscoreable_rewrite_output_keeps_best_so_far():
    class _BadRewriteProvider(LLMProvider):
        name = "bad_rewrite"

        def complete(self, instruction: RewriteInstruction) -> ProviderResult:
            return ProviderResult(text="... !!!", model="bad_rewrite")

    result = _service(_BadRewriteProvider()).rewrite(
        RewriteRequest(text=COMPLEX, target_grade=5, max_passes=1)
    )
    assert any(w.code == "unscoreable_text" for w in result.execution.warnings)
    assert result.output.text == COMPLEX
    assert result.execution.passes_used == 0


def test_response_exposes_required_workflow_fields():
    result = _service().rewrite(RewriteRequest(text=COMPLEX, target_grade=5, max_passes=2))
    assert result.input.frameworks
    assert result.output.frameworks
    assert result.target.grade == 5
    assert isinstance(result.hit_target, bool)
    assert result.execution.passes_used >= 0
    assert result.outcome.summary
    assert result.outcome.frameworks_improved
