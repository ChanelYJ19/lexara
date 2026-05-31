"""Rewrite effectiveness evals on representative educational text."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lexara.models.rewrite import RewriteRequest
from lexara.rewriting.providers.mock import MockLLMProvider
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService

FIXTURE = Path(__file__).parent / "fixtures" / "rewrite_eval_cases.json"
CASES = json.loads(FIXTURE.read_text())["cases"]


@pytest.fixture
def rewrite_service() -> RewriteService:
    return RewriteService(MockLLMProvider(), ScoringService())


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_rewrite_lowers_grade_on_educational_text(rewrite_service, case):
    req = RewriteRequest(
        text=case["text"],
        target_grade=case["target_grade"],
        max_passes=case.get("max_passes", 4),
        tolerance=case.get("tolerance", 1.5),
    )
    result = rewrite_service.rewrite(req)

    reduction = result.improvement.grade_level_before - result.improvement.grade_level_after
    assert reduction >= case["min_grade_reduction"], (
        f"{case['id']}: expected ≥{case['min_grade_reduction']} grade levels easier, "
        f"got {reduction}"
    )


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_rewrite_response_shows_before_after_workflow(rewrite_service, case):
    result = rewrite_service.rewrite(
        RewriteRequest(text=case["text"], target_grade=case["target_grade"], max_passes=4)
    )

    assert result.before.text == case["text"]
    assert result.after.text == result.rewritten_text
    assert result.before.scores
    assert result.after.scores
    assert result.before.aggregate_grade_level == result.improvement.grade_level_before
    assert result.after.aggregate_grade_level == result.improvement.grade_level_after
    assert result.target.grade == case["target_grade"]
    assert result.improvement.summary
    assert result.delta.grade_level_change == result.improvement.grade_level_change


def test_rewrite_moved_toward_target(rewrite_service):
    case = next(c for c in CASES if c["id"] == "science_passage")
    result = rewrite_service.rewrite(
        RewriteRequest(text=case["text"], target_grade=case["target_grade"], max_passes=5)
    )
    assert result.improvement.moved_toward_target is True
    assert result.target.distance_from_target < abs(
        result.improvement.grade_level_before - case["target_grade"]
    )


def test_history_passage_moves_toward_target(rewrite_service):
    case = next(c for c in CASES if c["id"] == "history_excerpt")
    result = rewrite_service.rewrite(
        RewriteRequest(
            text=case["text"],
            target_grade=case["target_grade"],
            max_passes=case.get("max_passes", 5),
            tolerance=case.get("tolerance", 2.0),
        )
    )
    assert result.improvement.moved_toward_target is True
    assert result.improvement.grade_level_after < result.improvement.grade_level_before


def test_multi_framework_scores_present_before_and_after(rewrite_service):
    text = CASES[0]["text"]
    result = rewrite_service.rewrite(
        RewriteRequest(text=text, target_grade=5, max_passes=4, frameworks=None)
    )
    assert len(result.before.scores) == 4
    assert len(result.after.scores) == 4
    frameworks = {s.framework for s in result.before.scores}
    assert frameworks == {
        "flesch_kincaid",
        "dale_chall",
        "atos_estimated",
        "lexile_estimated",
    }
