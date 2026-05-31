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


class EvalDataset(BaseModel):
    version: int = 1
    description: str = ""
    samples: list[EvalSample] = Field(..., min_length=1)


class EvalResult(BaseModel):
    source_id: str
    passage_type: PassageType
    source_grade_estimate: float
    target_grade: float
    rewritten_grade_estimate: float
    hit_target: bool
    attempts_used: int
    delta: float = Field(..., description="rewritten_grade_estimate − source_grade_estimate")
    moved_toward_target: bool
    semantic_preservation_notes: str = Field(
        default="",
        description="Manual review: facts, steps, and meaning preserved?",
    )


class EvalRunSummary(BaseModel):
    run_at: str
    provider: str
    dataset_version: int
    sample_count: int
    hit_target_count: int
    moved_toward_target_count: int
    mean_abs_delta: float
    results: list[EvalResult]

    @classmethod
    def from_results(
        cls,
        *,
        provider: str,
        dataset_version: int,
        results: list[EvalResult],
    ) -> EvalRunSummary:
        deltas = [abs(r.delta) for r in results]
        mean_abs = round(sum(deltas) / len(deltas), 1) if deltas else 0.0
        return cls(
            run_at=datetime.now(timezone.utc).isoformat(),
            provider=provider,
            dataset_version=dataset_version,
            sample_count=len(results),
            hit_target_count=sum(1 for r in results if r.hit_target),
            moved_toward_target_count=sum(1 for r in results if r.moved_toward_target),
            mean_abs_delta=mean_abs,
            results=results,
        )


Format = Literal["json", "table"]
