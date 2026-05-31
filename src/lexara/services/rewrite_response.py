"""Helpers for building rewrite response objects."""

from __future__ import annotations

from lexara.models.rewrite import (
    PassageSnapshot,
    RewriteExecution,
    RewriteOutcome,
    RewriteRequest,
    RewriteResponse,
    RewriteTarget,
)
from lexara.models.scoring import FrameworkScore
from lexara.rewriting.pipeline import PipelineOutcome
from lexara.scoring.interpret import grade_band


def snapshot(text: str, scores: list[FrameworkScore], grade: float) -> PassageSnapshot:
    return PassageSnapshot(
        text=text,
        estimated_grade_level=grade,
        grade_band=grade_band(grade),
        frameworks=scores,
    )


def frameworks_improved(
    before: list[FrameworkScore],
    after: list[FrameworkScore],
    target_grade: float,
) -> list[str]:
    after_by_fw = {score.framework: score for score in after}
    improved: list[str] = []
    for before_score in before:
        after_score = after_by_fw.get(before_score.framework)
        if after_score is None:
            continue
        before_distance = abs(before_score.estimated_grade_level - target_grade)
        after_distance = abs(after_score.estimated_grade_level - target_grade)
        if after_distance < before_distance - 0.05:
            improved.append(before_score.framework)
    return improved


def outcome_summary(
    *,
    grade_from: float,
    grade_to: float,
    target_grade: float,
    hit_target: bool,
    tolerance: float,
    skipped: bool,
    skip_reason: str | None,
) -> str:
    if skipped and skip_reason == "already_at_target":
        return (
            f"Already at grade {grade_from:g} (target {target_grade:g}, within ±{tolerance:g}). "
            "No rewrite needed."
        )

    change = grade_to - grade_from
    if hit_target:
        if abs(change) < 0.05:
            return (
                f"Met target at grade {grade_to:g} (target {target_grade:g}, "
                f"within ±{tolerance:g})."
            )
        direction = "Lowered" if change < 0 else "Raised"
        return (
            f"{direction} from grade {grade_from:g} to {grade_to:g} "
            f"(target {target_grade:g}, within ±{tolerance:g})."
        )

    if abs(grade_to - target_grade) < abs(grade_from - target_grade):
        return (
            f"Improved from grade {grade_from:g} toward target {target_grade:g} "
            f"(now {grade_to:g}). Target not met — try more passes or wider tolerance."
        )

    direction = "lower" if change < 0 else "higher" if change > 0 else "unchanged"
    return (
        f"Reading level went {direction} (grade {grade_from:g} → {grade_to:g}); "
        f"target {target_grade:g} not reached."
    )


def build_rewrite_response(
    req: RewriteRequest, original_text: str, outcome: PipelineOutcome
) -> RewriteResponse:
    distance = round(abs(outcome.rewritten_grade - req.target_grade), 1)
    moved_toward = (
        outcome.skipped_rewrite
        or distance < abs(outcome.original_grade - req.target_grade)
    )
    improved = frameworks_improved(
        outcome.original_scores, outcome.rewritten_scores, req.target_grade
    )

    input_snapshot = snapshot(original_text, outcome.original_scores, outcome.original_grade)
    output_snapshot = snapshot(
        outcome.rewritten_text, outcome.rewritten_scores, outcome.rewritten_grade
    )

    target = RewriteTarget(
        grade=req.target_grade,
        tolerance=req.tolerance,
        grade_band=grade_band(req.target_grade),
    )

    rewrite_outcome = RewriteOutcome(
        estimated_grade_from=outcome.original_grade,
        estimated_grade_to=outcome.rewritten_grade,
        grade_change=round(outcome.rewritten_grade - outcome.original_grade, 1),
        target_grade=req.target_grade,
        hit_target=outcome.hit_target,
        distance_from_target=distance,
        moved_toward_target=moved_toward,
        frameworks_improved=improved,
        summary=outcome_summary(
            grade_from=outcome.original_grade,
            grade_to=outcome.rewritten_grade,
            target_grade=req.target_grade,
            hit_target=outcome.hit_target,
            tolerance=req.tolerance,
            skipped=outcome.skipped_rewrite,
            skip_reason=outcome.skip_reason,
        ),
    )

    execution = RewriteExecution(
        passes_used=outcome.passes_used,
        provider=outcome.provider_name,
        skipped=outcome.skipped_rewrite,
        skip_reason=outcome.skip_reason,
        provider_calls_attempted=outcome.provider_passes_attempted,
        provider_calls_failed=outcome.provider_passes_failed,
        warnings=outcome.warnings,
        degraded=outcome.degraded,
    )

    return RewriteResponse(
        input=input_snapshot,
        output=output_snapshot,
        target=target,
        outcome=rewrite_outcome,
        execution=execution,
    )
