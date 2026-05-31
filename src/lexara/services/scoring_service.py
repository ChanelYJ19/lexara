"""Scoring orchestration: stats + per-framework scores + aggregate."""

from __future__ import annotations

from statistics import mean

from lexara.logging_config import get_logger
from lexara.models.scoring import (
    FrameworkScore,
    ScoreAggregate,
    ScoreResponse,
)
from lexara.scoring.interpret import (
    confidence_summary,
    consensus_interpretation,
    grade_band,
)
from lexara.scoring.registry import FrameworkRegistry, get_registry
from lexara.scoring.text_stats import compute_stats

logger = get_logger(__name__)


class UnknownFrameworkError(ValueError):
    def __init__(self, names: list[str]) -> None:
        self.names = names
        super().__init__(f"Unknown framework(s): {', '.join(names)}")


class UnscoreableTextError(ValueError):
    """Raised when input has no alphabetic words to score."""


class ScoringService:
    def __init__(self, registry: FrameworkRegistry | None = None) -> None:
        self._registry = registry or get_registry()

    def validate_frameworks(self, frameworks: list[str] | None) -> None:
        try:
            self._registry.resolve(frameworks)
        except KeyError as exc:
            raise UnknownFrameworkError(exc.args[0]) from exc

    def _prepare(self, text: str, frameworks: list[str] | None):
        self.validate_frameworks(frameworks)
        selected = self._registry.resolve(frameworks)
        stats = compute_stats(text)
        if stats.word_count == 0:
            raise UnscoreableTextError(
                "Text contains no scoreable words (letters required)."
            )
        return selected, stats

    def score_frameworks(
        self, text: str, frameworks: list[str] | None
    ) -> tuple[list[FrameworkScore], float]:
        selected, stats = self._prepare(text, frameworks)
        scores = [fw.score(stats) for fw in selected]
        agg_grade = round(mean(s.estimated_grade_level for s in scores), 1)
        return scores, agg_grade

    def score(self, text: str, frameworks: list[str] | None) -> ScoreResponse:
        selected, stats = self._prepare(text, frameworks)
        scores = [fw.score(stats) for fw in selected]
        agg_grade = round(mean(s.estimated_grade_level for s in scores), 1)

        logger.info(
            "scored text",
            extra={
                "extra": {
                    "frameworks": [s.framework for s in scores],
                    "word_count": stats.word_count,
                    "sentence_count": stats.sentence_count,
                }
            },
        )
        return ScoreResponse(
            stats=stats,
            scores=scores,
            aggregate=ScoreAggregate(
                estimated_grade_level=agg_grade,
                grade_band=grade_band(agg_grade),
                consensus_interpretation=consensus_interpretation(agg_grade),
                frameworks_scored=[s.framework for s in scores],
                confidence_summary=confidence_summary(scores),
            ),
        )
