from __future__ import annotations

import pytest

from lexara.models.rewrite import RewriteRequest, Tone
from lexara.rewriting.providers.base import LLMProvider, ProviderResult, RewriteInstruction
from lexara.rewriting.providers.mock import MockLLMProvider
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService

COMPLEX = (
    "The committee will subsequently utilize numerous additional resources to "
    "facilitate the comprehensive demonstration, and they will require "
    "approximately seven days to obtain sufficient data because the analysis is "
    "fundamentally complex."
)


def _service() -> RewriteService:
    return RewriteService(MockLLMProvider(), ScoringService())


def test_mock_rewrite_lowers_grade_level():
    req = RewriteRequest(text=COMPLEX, target_grade=5, max_passes=4)
    result = _service().rewrite(req)
    assert result.outcome.estimated_grade_to < result.outcome.estimated_grade_from
    assert result.execution.provider == "mock"
    assert result.outcome.summary


def test_rewrite_reports_target_and_passes():
    req = RewriteRequest(text=COMPLEX, target_grade=5, max_passes=3, tolerance=1.5)
    result = _service().rewrite(req)
    assert result.target.grade == 5
    assert 1 <= result.execution.passes_used <= 3
    assert isinstance(result.hit_target, bool)


def test_input_output_snapshots():
    result = _service().rewrite(RewriteRequest(text=COMPLEX, target_grade=5))
    assert result.input.text == COMPLEX
    assert result.output.text == result.rewritten_text
    assert len(result.input.frameworks) == len(result.output.frameworks)


def test_pipeline_stops_at_max_passes():
    class _NoopProvider(LLMProvider):
        name = "noop"

        def complete(self, instruction: RewriteInstruction) -> ProviderResult:
            text = instruction.user_prompt.split("TEXT:\n")[-1]
            return ProviderResult(text=text, model="noop")

    service = RewriteService(_NoopProvider(), ScoringService())
    req = RewriteRequest(text=COMPLEX, target_grade=2, max_passes=2, tolerance=0.5)
    result = service.rewrite(req)
    assert result.execution.passes_used == 2


def test_tone_enum_accepted():
    req = RewriteRequest(text=COMPLEX, target_grade=6, tone=Tone.friendly)
    result = _service().rewrite(req)
    assert result.rewritten_text
