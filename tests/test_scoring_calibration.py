"""Regression tests against calibrated score bands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lexara.models.scoring import ScoreConfidence
from lexara.services.scoring_service import ScoringService

FIXTURE = Path(__file__).parent / "fixtures" / "scoring_calibration.json"
DATA = json.loads(FIXTURE.read_text())
CASES = {c["id"]: c for c in DATA["cases"]}


@pytest.fixture
def service() -> ScoringService:
    return ScoringService()


@pytest.mark.parametrize("case_id", [c["id"] for c in DATA["cases"]])
def test_calibration_bands(service: ScoringService, case_id: str):
    case = CASES[case_id]
    result = service.score(case["text"], None)
    by_fw = {s.framework: s for s in result.scores}

    for fw, bands in case["frameworks"].items():
        score = by_fw[fw]
        lo, hi = bands["estimated_grade_level"]
        assert lo <= score.estimated_grade_level <= hi, (
            f"{case_id}/{fw} grade {score.estimated_grade_level} not in [{lo}, {hi}]"
        )
        rlo, rhi = bands["raw_score"]
        assert rlo <= score.raw_score <= rhi, (
            f"{case_id}/{fw} raw {score.raw_score} not in [{rlo}, {rhi}]"
        )

    agg_lo, agg_hi = case["aggregate_grade"]
    assert agg_lo <= result.aggregate.estimated_grade_level <= agg_hi


def test_calibration_ordering(service: ScoringService):
    ordering = DATA["ordering"]
    fw = ordering["framework"]
    simple = service.score(CASES[ordering["simple_id"]]["text"], [fw])
    complex_ = service.score(CASES[ordering["complex_id"]]["text"], [fw])
    assert (
        complex_.scores[0].estimated_grade_level
        > simple.scores[0].estimated_grade_level
    )


def test_confidence_labels(service: ScoringService):
    result = service.score(CASES["simple_elementary"]["text"], None)
    conf = {s.framework: s.confidence for s in result.scores}
    assert conf["flesch_kincaid"] == ScoreConfidence.exact
    assert conf["dale_chall"] == ScoreConfidence.estimated
    assert conf["atos_estimated"] == ScoreConfidence.estimated
    assert conf["lexile_estimated"] == ScoreConfidence.estimated
    assert all(s.confidence_note for s in result.scores if s.confidence == ScoreConfidence.estimated)
    assert "exact: flesch_kincaid" in result.aggregate.confidence_summary
