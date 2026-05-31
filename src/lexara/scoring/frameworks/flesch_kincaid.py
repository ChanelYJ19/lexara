"""Flesch-Kincaid Grade Level.

Faithful implementation of the standard formula:

    grade = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59

The only approximation is the syllable count (see ``text_stats``).
"""

from __future__ import annotations

from lexara.models.common import TextStats
from lexara.models.scoring import ScoreConfidence
from lexara.scoring.base import ReadabilityFramework


class FleschKincaidGrade(ReadabilityFramework):
    name = "flesch_kincaid"
    unit = "grade"
    confidence = ScoreConfidence.exact
    confidence_note = (
        "Standard Flesch-Kincaid Grade formula. Syllable counts are estimated "
        "separately in stats.syllable_estimate."
    )

    def raw_score(self, stats: TextStats) -> float:
        if stats.word_count == 0:
            return 0.0
        return (
            0.39 * stats.avg_sentence_length
            + 11.8 * stats.avg_syllables_per_word
            - 15.59
        )

    def to_grade_level(self, raw_score: float) -> float:
        # The raw score already *is* a US grade level.
        return max(0.0, raw_score)
