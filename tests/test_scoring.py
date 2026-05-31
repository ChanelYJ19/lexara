from __future__ import annotations

import pytest

from lexara.models.scoring import ScoreConfidence
from lexara.scoring.registry import FrameworkRegistry
from lexara.services.scoring_service import (
    ScoringService,
    UnknownFrameworkError,
    UnscoreableTextError,
)

SIMPLE = "The cat sat on the mat. The dog ran fast. We had fun."
COMPLEX = (
    "The multifaceted ramifications of macroeconomic policy interventions "
    "necessitate comprehensive interdisciplinary analysis before implementation "
    "across heterogeneous institutional environments."
)


def test_all_frameworks_scored_by_default():
    result = ScoringService().score(SIMPLE, frameworks=None)
    names = {s.framework for s in result.scores}
    assert names == {
        "flesch_kincaid",
        "dale_chall",
        "atos_estimated",
        "lexile_estimated",
    }


def test_framework_aliases_resolve():
    result = ScoringService().score(SIMPLE, ["atos", "lexile"])
    names = {s.framework for s in result.scores}
    assert names == {"atos_estimated", "lexile_estimated"}


def test_complex_text_scores_higher_than_simple():
    service = ScoringService()
    simple = service.score(SIMPLE, ["flesch_kincaid"]).aggregate.estimated_grade_level
    complex_ = service.score(COMPLEX, ["flesch_kincaid"]).aggregate.estimated_grade_level
    assert complex_ > simple


def test_lexile_estimated_confidence():
    score = ScoringService().score(SIMPLE, ["lexile_estimated"]).scores[0]
    assert score.confidence == ScoreConfidence.estimated
    assert score.unit == "lexile"


def test_flesch_kincaid_is_exact():
    score = ScoringService().score(SIMPLE, ["flesch_kincaid"]).scores[0]
    assert score.confidence == ScoreConfidence.exact


def test_stats_metadata_present():
    result = ScoringService().score(SIMPLE, None)
    stats = result.stats
    assert stats.sentence_count > 0
    assert stats.word_count > 0
    assert stats.avg_sentence_length > 0
    assert stats.avg_word_length > 0
    assert stats.syllable_estimate > 0
    assert stats.difficult_word_count >= 0


def test_unknown_framework_raises():
    with pytest.raises(UnknownFrameworkError):
        ScoringService().score(SIMPLE, ["not_a_framework"])


def test_unscoreable_text_raises():
    with pytest.raises(UnscoreableTextError):
        ScoringService().score("12345 !!!", None)


def test_registry_is_pluggable():
    registry = FrameworkRegistry()
    assert "flesch_kincaid" in registry.names()
    assert len(registry.resolve(None)) == 4


def test_aggregate_fields_present():
    result = ScoringService().score(SIMPLE, None)
    agg = result.aggregate
    assert agg.frameworks_scored
    assert agg.grade_band
    assert agg.consensus_interpretation
    assert "exact" in agg.confidence_summary
