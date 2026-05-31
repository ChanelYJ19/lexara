"""Request/response schemas for score-only diagnostics.

Use POST /v1/readability/rewrite when you need to act on scores — rewrite to a
target grade and get before/after proof in one call.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

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
    """Score-only diagnostics. Pair with POST /rewrite to adjust text to a target grade."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": "The cat sat on the mat.",
                    "frameworks": ["flesch_kincaid", "lexile_estimated"],
                }
            ]
        }
    )

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
    """Multi-framework readability snapshot for one passage — verification without rewrite."""

    request_id: str | None = None
    stats: TextStats
    scores: list[FrameworkScore]
    aggregate: ScoreAggregate
