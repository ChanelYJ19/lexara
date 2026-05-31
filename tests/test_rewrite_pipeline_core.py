"""Direct pipeline and response-builder unit tests."""

from __future__ import annotations

import pytest

from lexara.models.rewrite import RewriteRequest, Tone
from lexara.models.scoring import FrameworkScore, ScoreConfidence
from lexara.rewriting.pipeline import PipelineOutcome, run_rewrite
from lexara.rewriting.providers.base import LLMProvider, ProviderResult, RewriteInstruction
from lexara.rewriting.providers.mock import MockLLMProvider
from lexara.services.rewrite_response import (
    build_rewrite_response,
    frameworks_improved,
    outcome_summary,
)
from lexara.services.scoring_service import ScoringService

COMPLEX = (
    "The committee will subsequently utilize numerous additional resources to "
    "facilitate the comprehensive demonstration, and they will require "
    "approximately seven days to obtain sufficient data because the analysis is "
    "fundamentally complex."
)


def _score(scorer_service: ScoringService):
    def scorer(text: str):
        return scorer_service.score_frameworks(text, None)

    return scorer


def test_run_rewrite_keeps_best_text_when_later_pass_overshoots():
    class _OvershootProvider(LLMProvider):
        name = "overshoot"
        calls = 0

        def complete(self, instruction: RewriteInstruction) -> ProviderResult:
            _OvershootProvider.calls += 1
            text = instruction.user_prompt.split("TEXT:\n")[-1]
            if _OvershootProvider.calls == 1:
                return ProviderResult(text=text.replace("utilize", "use"), model="overshoot")
            return ProviderResult(text="The cat sat.", model="overshoot")

    _OvershootProvider.calls = 0
    scoring = ScoringService()
    outcome = run_rewrite(
        text=COMPLEX,
        target_grade=5,
        preserve_meaning=True,
        tone=Tone.neutral,
        max_passes=2,
        tolerance=1.0,
        provider=_OvershootProvider(),
        scorer=_score(scoring),
    )
    assert outcome.passes_used == 2
    assert abs(outcome.rewritten_grade - 5) <= abs(outcome.original_grade - 5)


def test_run_rewrite_original_scoring_failure_is_degraded():
    def failing_scorer(text: str):
        raise ValueError("boom")

    outcome = run_rewrite(
        text=COMPLEX,
        target_grade=5,
        preserve_meaning=True,
        tone=Tone.neutral,
        max_passes=1,
        tolerance=1.0,
        provider=MockLLMProvider(),
        scorer=failing_scorer,
    )
    assert isinstance(outcome, PipelineOutcome)
    assert outcome.degraded is True
    assert outcome.original_scores == []
    assert any(w.code == "scoring_failed" for w in outcome.warnings)


def test_outcome_summary_already_at_target():
    summary = outcome_summary(
        grade_from=5.1,
        grade_to=5.1,
        target_grade=5.0,
        hit_target=True,
        tolerance=1.0,
        skipped=True,
        skip_reason="already_at_target",
    )
    assert "Already at grade" in summary
    assert "No rewrite needed" in summary


def test_frameworks_improved_detects_closer_frameworks():
    before = [
        FrameworkScore(
            framework="flesch_kincaid",
            raw_score=20.0,
            grade_band="College+",
            estimated_grade_level=20.0,
            confidence=ScoreConfidence.exact,
            interpretation="",
            unit="grade",
        )
    ]
    after = [
        FrameworkScore(
            framework="flesch_kincaid",
            raw_score=8.0,
            grade_band="6-8",
            estimated_grade_level=8.0,
            confidence=ScoreConfidence.exact,
            interpretation="",
            unit="grade",
        )
    ]
    assert frameworks_improved(before, after, target_grade=6.0) == ["flesch_kincaid"]


def test_build_rewrite_response_from_pipeline_outcome():
    scoring = ScoringService()
    pipeline_outcome = run_rewrite(
        text=COMPLEX,
        target_grade=5,
        preserve_meaning=True,
        tone=Tone.neutral,
        max_passes=2,
        tolerance=2.0,
        provider=MockLLMProvider(),
        scorer=_score(scoring),
    )
    response = build_rewrite_response(
        RewriteRequest(text=COMPLEX, target_grade=5, max_passes=2, tolerance=2.0),
        COMPLEX,
        pipeline_outcome,
    )
    assert response.input.text == COMPLEX
    assert response.outcome.estimated_grade_from == response.input.estimated_grade_level
    assert response.outcome.estimated_grade_to == response.output.estimated_grade_level
