from __future__ import annotations

import pytest

from lexara.models.common import TextStats
from lexara.scoring.frameworks.atos_estimated import AtosEstimated
from lexara.scoring.frameworks.dale_chall import DaleChall
from lexara.scoring.frameworks.flesch_kincaid import FleschKincaidGrade
from lexara.scoring.frameworks.lexile_estimated import LexileEstimated
from lexara.models.scoring import ScoreConfidence


def _stats(**kwargs) -> TextStats:
    defaults = dict(
        sentence_count=2,
        word_count=10,
        avg_sentence_length=5.0,
        avg_word_length=4.0,
        syllable_estimate=13,
        difficult_word_count=2,
        character_count=40,
        complex_word_count=1,
        avg_syllables_per_word=1.3,
    )
    defaults.update(kwargs)
    return TextStats(**defaults)


def test_flesch_kincaid_formula():
    # 0.39 * 5 + 11.8 * 1.3 - 15.59 = 1.95 + 15.34 - 15.59 = 1.7
    fw = FleschKincaidGrade()
    assert fw.raw_score(_stats()) == pytest.approx(1.7, abs=0.01)
    assert fw.confidence == ScoreConfidence.exact


def test_flesch_kincaid_zero_words():
    fw = FleschKincaidGrade()
    assert fw.raw_score(_stats(word_count=0, avg_sentence_length=0, avg_syllables_per_word=0)) == 0.0


def test_dale_chall_formula_without_difficult_words():
    fw = DaleChall()
    raw = fw.raw_score(_stats(difficult_word_count=0, avg_sentence_length=5.0))
    assert raw == pytest.approx(0.248, abs=0.01)


def test_dale_chall_bonus_above_five_percent():
    fw = DaleChall()
    raw = fw.raw_score(_stats(difficult_word_count=1, avg_sentence_length=5.0))
    # 10% difficult -> base + 3.6365 bonus
    assert raw > 3.6


def test_dale_chall_grade_mapping():
    fw = DaleChall()
    assert fw.to_grade_level(4.5) == 4.0
    assert fw.to_grade_level(5.5) == 5.5
    assert fw.to_grade_level(10.0) == 14.0


def test_atos_estimated_increases_with_complexity():
    fw = AtosEstimated()
    simple = fw.raw_score(_stats(avg_sentence_length=5.0, difficult_word_count=0, character_count=30))
    complex_ = fw.raw_score(_stats(avg_sentence_length=20.0, difficult_word_count=8, character_count=120))
    assert complex_ > simple
    assert fw.confidence == ScoreConfidence.estimated


def test_lexile_estimated_returns_lexile_band():
    fw = LexileEstimated()
    score = fw.score(_stats(avg_sentence_length=5.0, avg_syllables_per_word=1.0))
    assert score.unit == "lexile"
    assert score.raw_score % 10 == 0
    assert score.framework == "lexile_estimated"
