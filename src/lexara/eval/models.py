"""Pydantic models for the rewrite effectiveness eval harness."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class PassageType(str, Enum):
    explanation = "explanation"
    instructions = "instructions"
    science = "science"
    social_studies = "social_studies"
    worksheet = "worksheet"


class EvalSample(BaseModel):
    source_id: str
    passage_type: PassageType
    source_grade_context: float = Field(
        ..., description="Approximate grade band the source passage was written for."
    )
    text: str = Field(..., min_length=1)
    target_grade: float = Field(..., ge=1, le=16)
    tolerance: float = Field(default=1.0, ge=0, le=4)
    max_passes: int = Field(default=4, ge=1, le=10)
    min_grade_reduction: float | None = Field(
        default=None,
        description="Optional mock-eval threshold: minimum grade levels easier after rewrite.",
    )
    expect_moved_toward_target: bool = True


class EvalDataset(BaseModel):
    version: int = 1
    description: str = ""
    samples: list[EvalSample] = Field(..., min_length=1)


class EvalResult(BaseModel):
    source_id: str
    passage_type: PassageType
    original_grade: float
    target_grade: float
    rewritten_grade: float
    hit_target: bool
    attempts_used: int
    delta: float = Field(..., description="rewritten_grade − original_grade")
    moved_toward_target: bool
    warnings: list[str] = Field(default_factory=list)
    original_text: str = ""
    rewritten_text: str = ""
    semantic_preservation_notes: str = Field(
        default="",
        description="Manual review: facts, steps, and meaning preserved?",
    )


def _grade_band(grade: float) -> str:
    if grade <= 3:
        return "K-3"
    elif grade <= 6:
        return "4-6"
    elif grade <= 8:
        return "7-8"
    else:
        return "9-12"


class GradeBandStats(BaseModel):
    sample_count: int
    hit_target_count: int
    hit_target_rate: float


class EvalRunSummary(BaseModel):
    run_at: str
    provider: str
    dataset_version: int
    sample_count: int
    hit_target_count: int
    hit_target_rate: float
    moved_toward_target_count: int
    mean_abs_delta: float
    avg_grade_delta: float
    grade_band_breakdown: dict[str, GradeBandStats]
    results: list[EvalResult]

    @classmethod
    def from_results(
        cls,
        *,
        provider: str,
        dataset_version: int,
        results: list[EvalResult],
    ) -> EvalRunSummary:
        n = len(results)
        abs_deltas = [abs(r.delta) for r in results]
        mean_abs = round(sum(abs_deltas) / n, 1) if n else 0.0
        avg_delta = round(sum(r.delta for r in results) / n, 1) if n else 0.0
        hit_count = sum(1 for r in results if r.hit_target)

        bands: dict[str, list[EvalResult]] = {}
        for r in results:
            band = _grade_band(r.original_grade)
            bands.setdefault(band, []).append(r)

        breakdown = {
            band: GradeBandStats(
                sample_count=len(rows),
                hit_target_count=sum(1 for r in rows if r.hit_target),
                hit_target_rate=round(
                    sum(1 for r in rows if r.hit_target) / len(rows), 3
                ),
            )
            for band, rows in bands.items()
        }

        return cls(
            run_at=datetime.now(timezone.utc).isoformat(),
            provider=provider,
            dataset_version=dataset_version,
            sample_count=n,
            hit_target_count=hit_count,
            hit_target_rate=round(hit_count / n, 3) if n else 0.0,
            moved_toward_target_count=sum(1 for r in results if r.moved_toward_target),
            mean_abs_delta=mean_abs,
            avg_grade_delta=avg_delta,
            grade_band_breakdown=breakdown,
            results=results,
        )


Format = Literal["json", "table"]
