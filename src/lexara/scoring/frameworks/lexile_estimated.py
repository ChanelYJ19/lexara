"""Lexile-equivalent estimate (proprietary MetaMetrics measure approximation)."""

from __future__ import annotations

from lexara.models.common import TextStats
from lexara.models.scoring import ScoreConfidence
from lexara.scoring.base import ReadabilityFramework

_GRADE_TO_LEXILE: list[tuple[float, float]] = [
    (1, 200),
    (2, 400),
    (3, 550),
    (4, 700),
    (5, 800),
    (6, 900),
    (7, 970),
    (8, 1010),
    (9, 1060),
    (10, 1100),
    (11, 1150),
    (12, 1185),
    (16, 1300),
]


def _grade_from_signals(stats: TextStats) -> float:
    if stats.word_count == 0:
        return 0.0
    grade = (
        0.39 * stats.avg_sentence_length
        + 11.8 * stats.avg_syllables_per_word
        - 15.59
    )
    return max(0.0, grade)


def _interp(grade: float) -> float:
    pts = _GRADE_TO_LEXILE
    if grade <= pts[0][0]:
        return pts[0][1]
    if grade >= pts[-1][0]:
        return pts[-1][1]
    for (g0, l0), (g1, l1) in zip(pts, pts[1:]):
        if g0 <= grade <= g1:
            ratio = (grade - g0) / (g1 - g0)
            return l0 + ratio * (l1 - l0)
    return pts[-1][1]


class LexileEstimated(ReadabilityFramework):
    name = "lexile_estimated"
    unit = "lexile"
    confidence = ScoreConfidence.estimated
    confidence_note = (
        "Lexile is a registered MetaMetrics measure; this is a Lexile-equivalent "
        "estimate on the L scale, not an official Lexile score."
    )

    def raw_score(self, stats: TextStats) -> float:
        return round(_interp(_grade_from_signals(stats)) / 10) * 10

    def to_grade_level(self, raw_score: float) -> float:
        pts = _GRADE_TO_LEXILE
        if raw_score <= pts[0][1]:
            return pts[0][0]
        if raw_score >= pts[-1][1]:
            return pts[-1][0]
        for (g0, l0), (g1, l1) in zip(pts, pts[1:]):
            if l0 <= raw_score <= l1:
                ratio = (raw_score - l0) / (l1 - l0)
                return g0 + ratio * (g1 - g0)
        return pts[-1][0]
