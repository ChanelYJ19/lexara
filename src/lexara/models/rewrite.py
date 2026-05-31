"""Request/response schemas for the rewrite endpoint — Lexara's core workflow."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, computed_field

from lexara.models.scoring import FrameworkScore


class Tone(str, Enum):
    neutral = "neutral"
    friendly = "friendly"
    formal = "formal"
    playful = "playful"
    academic = "academic"


class RewriteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50_000)
    target_grade: float = Field(
        ..., ge=1, le=16, description="Desired US grade level (1-16)."
    )
    preserve_meaning: bool = Field(
        default=True, description="Instruct the model to keep the original meaning."
    )
    tone: Tone = Tone.neutral
    max_passes: int = Field(
        default=3, ge=1, le=10, description="Max rewrite/rescore iterations."
    )
    frameworks: list[str] | None = Field(
        default=None,
        description="Frameworks used to judge progress toward the target (defaults all).",
    )
    tolerance: float = Field(
        default=1.0, ge=0, le=4, description="Grade levels within target counts as hit."
    )


class RewriteWarning(BaseModel):
    code: str
    message: str
    pass_number: int | None = None
    details: dict | None = None


class ReadabilitySnapshot(BaseModel):
    """Text plus multi-framework scores at a point in the rewrite workflow."""

    text: str
    aggregate_grade_level: float = Field(
        ..., description="Mean grade level across selected frameworks."
    )
    grade_band: str
    scores: list[FrameworkScore]


class RewriteTargetResult(BaseModel):
    grade: float
    tolerance: float
    hit_target: bool
    distance_from_target: float = Field(
        ..., description="Absolute grade levels away after rewrite."
    )
    target_grade_band: str


class RewriteImprovement(BaseModel):
    """Before/after grade movement relative to the target."""

    grade_level_before: float
    grade_level_after: float
    grade_level_change: float = Field(
        ..., description="after − before (negative means easier to read)."
    )
    target_grade: float
    moved_toward_target: bool
    summary: str = Field(..., description="Plain-language outcome for logs and UI.")


class RewritePipelineInfo(BaseModel):
    passes_used: int
    provider: str
    provider_passes_attempted: int
    provider_passes_failed: int = 0
    warnings: list[RewriteWarning] = Field(default_factory=list)
    degraded: bool = False


class RewriteDelta(BaseModel):
    """Compact delta block (mirrors ``improvement`` + pipeline pass counts)."""

    grade_level_before: float
    grade_level_after: float
    grade_level_change: float
    passes_used: int
    provider_passes_attempted: int
    provider_passes_failed: int = 0


class RewriteResponse(BaseModel):
    """Score → rewrite → rescore result with explicit before/after snapshots."""

    request_id: str | None = None

    # Primary workflow objects (use these in product UI)
    before: ReadabilitySnapshot
    after: ReadabilitySnapshot
    target: RewriteTargetResult
    improvement: RewriteImprovement
    pipeline: RewritePipelineInfo

    # Denormalized shortcuts for SDK ergonomics
    original_text: str
    rewritten_text: str
    target_grade: float
    hit_target: bool
    original_scores: list[FrameworkScore]
    rewritten_scores: list[FrameworkScore]
    provider: str
    warnings: list[RewriteWarning] = Field(default_factory=list)
    degraded: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def delta(self) -> RewriteDelta:
        return RewriteDelta(
            grade_level_before=self.improvement.grade_level_before,
            grade_level_after=self.improvement.grade_level_after,
            grade_level_change=self.improvement.grade_level_change,
            passes_used=self.pipeline.passes_used,
            provider_passes_attempted=self.pipeline.provider_passes_attempted,
            provider_passes_failed=self.pipeline.provider_passes_failed,
        )
