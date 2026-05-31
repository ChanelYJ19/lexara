"""Request/response schemas for the scoring endpoint."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from lexara.models.common import TextStats

SUPPORTED_FRAMEWORKS = (
    "flesch_kincaid",
    "dale_chall",
    "atos_estimated",
    "lexile_estimated",
)

# Backward-compatible aliases accepted in requests.
FRAMEWORK_ALIASES: dict[str, str] = {
    "atos": "atos_estimated",
    "lexile": "lexile_estimated",
}


class ScoreConfidence(str, Enum):
    """Score fidelity label exposed to API consumers."""

    exact = "exact"
    estimated = "estimated"


class ScoreRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50_000)
    frameworks: list[str] | None = Field(
        default=None,
        description=(
            "Frameworks to score against. Omit or send null to score all: "
            f"{', '.join(SUPPORTED_FRAMEWORKS)}."
        ),
    )


class FrameworkScore(BaseModel):
    framework: str
    raw_score: float
    grade_band: str = Field(..., description="Normalized US grade band, e.g. '4-5'.")
    estimated_grade_level: float = Field(
        ..., description="Single normalized grade level for aggregation."
    )
    confidence: ScoreConfidence
    confidence_note: str | None = None
    interpretation: str
    unit: str


class ScoreAggregate(BaseModel):
    estimated_grade_level: float
    grade_band: str
    consensus_interpretation: str
    frameworks_scored: list[str]
    confidence_summary: str


class ScoreResponse(BaseModel):
    request_id: str | None = None
    stats: TextStats
    scores: list[FrameworkScore]
    aggregate: ScoreAggregate
