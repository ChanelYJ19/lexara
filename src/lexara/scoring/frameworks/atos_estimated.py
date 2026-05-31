"""ATOS-style readability estimate (proprietary formula approximation)."""

from __future__ import annotations

from lexara.models.common import TextStats
from lexara.models.scoring import ScoreConfidence
from lexara.scoring.base import ReadabilityFramework


class AtosEstimated(ReadabilityFramework):
    name = "atos_estimated"
    unit = "grade"
    confidence = ScoreConfidence.estimated
    confidence_note = (
        "ATOS is proprietary; this is an ATOS-style estimate from sentence "
        "length, word length, and word difficulty — not an official AR level."
    )

    def raw_score(self, stats: TextStats) -> float:
        if stats.word_count == 0:
            return 0.0
        avg_word_chars = stats.character_count / stats.word_count
        pct_difficult = stats.difficult_word_count / stats.word_count
        grade = (
            0.45 * stats.avg_sentence_length
            + 2.0 * avg_word_chars
            + 4.0 * pct_difficult
            - 9.0
        )
        return max(0.0, grade)

    def to_grade_level(self, raw_score: float) -> float:
        return max(0.0, raw_score)
