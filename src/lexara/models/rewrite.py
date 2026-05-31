"""Request/response schemas for rewrite-to-target-grade — Lexara's core workflow."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from lexara.models.scoring import FrameworkScore


class Tone(str, Enum):
    neutral = "neutral"
    friendly = "friendly"
    formal = "formal"
    playful = "playful"
    academic = "academic"


class RewriteRequest(BaseModel):
    """Rewrite a passage to a target US grade level; multi-framework scores verify each pass."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": (
                        "Photosynthesis is the biochemical process by which chlorophyll-containing "
                        "organisms convert light energy into chemical energy."
                    ),
                    "target_grade": 6,
                    "preserve_meaning": True,
                    "max_passes": 5,
                }
            ]
        }
    )

    text: str = Field(..., min_length=1, max_length=50_000, description="Passage to rewrite.")
    target_grade: float = Field(
        ..., ge=1, le=16, description="Desired US grade level (1–16)."
    )
    preserve_meaning: bool = Field(
        default=True, description="Keep facts, numbers, names, and steps intact."
    )
    tone: Tone = Tone.neutral
    max_passes: int = Field(
        default=3, ge=1, le=10, description="Max rewrite → rescore iterations."
    )
    frameworks: list[str] | None = Field(
        default=None,
        description="Frameworks used to judge progress (defaults to all supported).",
    )
    tolerance: float = Field(
        default=1.0, ge=0, le=4, description="Grade levels within target counts as a hit."
    )


class RewriteWarning(BaseModel):
    code: str
    message: str
    pass_number: int | None = None
    details: dict | None = None


class PassageSnapshot(BaseModel):
    """One side of the rewrite transformation, with per-framework verification scores."""

    text: str
    estimated_grade_level: float = Field(
        ..., description="Mean grade level across selected frameworks."
    )
    grade_band: str
    frameworks: list[FrameworkScore] = Field(
        ..., description="Per-framework scores proving readability at this step."
    )


class RewriteTarget(BaseModel):
    """Grade goal the rewrite was aimed at."""

    grade: float
    tolerance: float
    grade_band: str


class RewriteOutcome(BaseModel):
    """Verification layer — did the rewrite reach the target grade?"""

    estimated_grade_from: float = Field(
        ..., description="Aggregate grade before rewrite (same as input.estimated_grade_level)."
    )
    estimated_grade_to: float = Field(
        ..., description="Aggregate grade after rewrite (same as output.estimated_grade_level)."
    )
    grade_change: float = Field(
        ..., description="estimated_grade_to − estimated_grade_from (negative = easier)."
    )
    target_grade: float
    hit_target: bool
    distance_from_target: float = Field(
        ..., description="Absolute grade levels away from target after rewrite."
    )
    moved_toward_target: bool
    frameworks_improved: list[str] = Field(
        default_factory=list,
        description="Frameworks whose grade estimate moved closer to the target.",
    )
    summary: str = Field(..., description="Plain-language before → after outcome.")


class RewriteExecution(BaseModel):
    """How the rewrite pipeline ran (provider, passes, warnings)."""

    passes_used: int = Field(
        ..., description="Rewrite → rescore loops that completed (0 if skipped)."
    )
    provider: str
    skipped: bool = Field(
        default=False, description="True when input was already at target — no LLM call."
    )
    skip_reason: str | None = Field(
        default=None, description="e.g. already_at_target when rewrite was not needed."
    )
    provider_calls_attempted: int = Field(
        ..., description="LLM calls attempted (includes failures)."
    )
    provider_calls_failed: int = 0
    warnings: list[RewriteWarning] = Field(default_factory=list)
    degraded: bool = False


class RewriteResponse(BaseModel):
    """Rewrite-to-target-grade result: input passage, rewritten output, and scored proof."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "Primary Lexara response. Read input → output for the transformation; "
                "read outcome for hit/miss and frameworks_improved; read execution for pipeline details."
            )
        }
    )

    request_id: str | None = None
    input: PassageSnapshot
    output: PassageSnapshot
    target: RewriteTarget
    outcome: RewriteOutcome
    execution: RewriteExecution

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rewritten_text(self) -> str:
        """Shortcut: rewritten passage (same as output.text)."""
        return self.output.text

    @computed_field  # type: ignore[prop-decorator]
    @property
    def hit_target(self) -> bool:
        """Shortcut: whether the target grade was met (same as outcome.hit_target)."""
        return self.outcome.hit_target
