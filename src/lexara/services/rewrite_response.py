"""Helpers for building rewrite response objects."""

from __future__ import annotations

from lexara.models.rewrite import (
    ReadabilitySnapshot,
    RewriteImprovement,
    RewritePipelineInfo,
    RewriteRequest,
    RewriteResponse,
    RewriteTargetResult,
)
from lexara.models.scoring import FrameworkScore
from lexara.rewriting.pipeline import RewriteOutcome
from lexara.scoring.interpret import grade_band


def snapshot(text: str, scores: list[FrameworkScore], grade: float) -> ReadabilitySnapshot:
    return ReadabilitySnapshot(
        text=text,
        aggregate_grade_level=grade,
        grade_band=grade_band(grade),
        scores=scores,
    )


def improvement_summary(
    *,
    before_grade: float,
    after_grade: float,
    target_grade: float,
    hit_target: bool,
    tolerance: float,
) -> str:
    change = after_grade - before_grade
    if hit_target:
        verb = "Lowered" if change < 0 else "Raised" if change > 0 else "Adjusted"
        return (
            f"{verb} reading level from grade {before_grade:g} to {after_grade:g} "
            f"(target grade {target_grade:g}). Target met within ±{tolerance:g} grade levels."
        )

    moved_closer = abs(after_grade - target_grade) < abs(before_grade - target_grade)
    if moved_closer:
        return (
            f"Moved reading level from grade {before_grade:g} toward target {target_grade:g} "
            f"(now grade {after_grade:g}). Target not fully met — try more passes or wider tolerance."
        )

    direction = "lower" if change < 0 else "higher" if change > 0 else "unchanged"
    return (
        f"Reading level went {direction} (grade {before_grade:g} → {after_grade:g}); "
        f"target grade {target_grade:g} not reached."
    )


def build_rewrite_response(
    req: RewriteRequest, original_text: str, outcome: RewriteOutcome
) -> RewriteResponse:
    distance = round(abs(outcome.rewritten_grade - req.target_grade), 1)
    moved_toward = distance < abs(outcome.original_grade - req.target_grade)

    before = snapshot(original_text, outcome.original_scores, outcome.original_grade)
    after = snapshot(outcome.rewritten_text, outcome.rewritten_scores, outcome.rewritten_grade)

    target = RewriteTargetResult(
        grade=req.target_grade,
        tolerance=req.tolerance,
        hit_target=outcome.hit_target,
        distance_from_target=distance,
        target_grade_band=grade_band(req.target_grade),
    )

    improvement = RewriteImprovement(
        grade_level_before=outcome.original_grade,
        grade_level_after=outcome.rewritten_grade,
        grade_level_change=round(outcome.rewritten_grade - outcome.original_grade, 1),
        target_grade=req.target_grade,
        moved_toward_target=moved_toward,
        summary=improvement_summary(
            before_grade=outcome.original_grade,
            after_grade=outcome.rewritten_grade,
            target_grade=req.target_grade,
            hit_target=outcome.hit_target,
            tolerance=req.tolerance,
        ),
    )

    pipeline = RewritePipelineInfo(
        passes_used=outcome.passes_used,
        provider=outcome.provider_name,
        provider_passes_attempted=outcome.provider_passes_attempted,
        provider_passes_failed=outcome.provider_passes_failed,
        warnings=outcome.warnings,
        degraded=outcome.degraded,
    )

    return RewriteResponse(
        before=before,
        after=after,
        target=target,
        improvement=improvement,
        pipeline=pipeline,
        original_text=original_text,
        rewritten_text=outcome.rewritten_text,
        target_grade=req.target_grade,
        hit_target=outcome.hit_target,
        original_scores=outcome.original_scores,
        rewritten_scores=outcome.rewritten_scores,
        provider=outcome.provider_name,
        warnings=outcome.warnings,
        degraded=outcome.degraded,
    )
