"""Rewrite effectiveness evals on canonical K-12 dataset."""

from __future__ import annotations

import pytest

from lexara.eval.harness import load_dataset
from lexara.eval.models import EvalSample
from lexara.models.rewrite import RewriteRequest
from lexara.rewriting.providers.mock import MockLLMProvider
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService

DATASET = load_dataset()
EVAL_CASES = [s for s in DATASET.samples if s.min_grade_reduction is not None]


@pytest.fixture
def rewrite_service() -> RewriteService:
    return RewriteService(MockLLMProvider(), ScoringService())


def _sample(source_id: str) -> EvalSample:
    return next(s for s in DATASET.samples if s.source_id == source_id)


@pytest.mark.parametrize("case", EVAL_CASES, ids=[c.source_id for c in EVAL_CASES])
def test_rewrite_lowers_grade_on_educational_text(rewrite_service, case):
    req = RewriteRequest(
        text=case.text,
        target_grade=case.target_grade,
        max_passes=case.max_passes,
        tolerance=case.tolerance,
    )
    result = rewrite_service.rewrite(req)

    reduction = (
        result.outcome.estimated_grade_from - result.outcome.estimated_grade_to
    )
    assert case.min_grade_reduction is not None
    assert reduction >= case.min_grade_reduction, (
        f"{case.source_id}: expected ≥{case.min_grade_reduction} grade levels easier, "
        f"got {reduction}"
    )


@pytest.mark.parametrize("case", EVAL_CASES, ids=[c.source_id for c in EVAL_CASES])
def test_rewrite_response_shows_input_output_workflow(rewrite_service, case):
    result = rewrite_service.rewrite(
        RewriteRequest(
            text=case.text,
            target_grade=case.target_grade,
            max_passes=case.max_passes,
            tolerance=case.tolerance,
        )
    )

    assert result.input.text == case.text
    assert result.output.text == result.rewritten_text
    assert result.input.frameworks
    assert result.output.frameworks
    assert result.input.estimated_grade_level == result.outcome.estimated_grade_from
    assert result.output.estimated_grade_level == result.outcome.estimated_grade_to
    assert result.target.grade == case.target_grade
    assert result.outcome.summary
    assert result.outcome.grade_change == round(
        result.outcome.estimated_grade_to - result.outcome.estimated_grade_from, 1
    )


def test_rewrite_moved_toward_target(rewrite_service):
    case = _sample("g6_science_photosynthesis")
    result = rewrite_service.rewrite(
        RewriteRequest(
            text=case.text,
            target_grade=case.target_grade,
            max_passes=case.max_passes,
            tolerance=case.tolerance,
        )
    )
    assert result.outcome.moved_toward_target is True
    assert result.outcome.distance_from_target < abs(
        result.outcome.estimated_grade_from - case.target_grade
    )


def test_history_passage_moves_toward_target(rewrite_service):
    case = _sample("g5_social_studies_economics")
    result = rewrite_service.rewrite(
        RewriteRequest(
            text=case.text,
            target_grade=case.target_grade,
            max_passes=case.max_passes,
            tolerance=case.tolerance,
        )
    )
    assert result.outcome.moved_toward_target is True
    assert result.outcome.estimated_grade_to < result.outcome.estimated_grade_from


def test_multi_framework_scores_present_input_and_output(rewrite_service):
    case = _sample("g6_science_photosynthesis")
    result = rewrite_service.rewrite(
        RewriteRequest(text=case.text, target_grade=5, max_passes=4, frameworks=None)
    )
    assert len(result.input.frameworks) == 4
    assert len(result.output.frameworks) == 4
    frameworks = {s.framework for s in result.input.frameworks}
    assert frameworks == {
        "flesch_kincaid",
        "dale_chall",
        "atos_estimated",
        "lexile_estimated",
    }
