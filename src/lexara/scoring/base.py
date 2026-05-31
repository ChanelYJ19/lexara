"""Pluggable readability framework interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from lexara.models.common import TextStats
from lexara.models.scoring import FrameworkScore, ScoreConfidence


class ReadabilityFramework(ABC):
    name: str
    unit: str = "grade"
    confidence: ScoreConfidence = ScoreConfidence.exact
    confidence_note: str | None = None

    @abstractmethod
    def raw_score(self, stats: TextStats) -> float:
        """Return the framework's native score from text statistics."""

    @abstractmethod
    def to_grade_level(self, raw_score: float) -> float:
        """Normalize the raw score to a single US grade level for aggregation."""

    def score(self, stats: TextStats) -> FrameworkScore:
        from lexara.scoring.interpret import grade_band, interpret_grade

        raw = round(self.raw_score(stats), 2)
        grade = round(self.to_grade_level(raw), 1)
        return FrameworkScore(
            framework=self.name,
            raw_score=raw,
            estimated_grade_level=grade,
            grade_band=grade_band(grade),
            interpretation=interpret_grade(self.name, grade, self.confidence),
            confidence=self.confidence,
            confidence_note=self.confidence_note,
            unit=self.unit,
        )
