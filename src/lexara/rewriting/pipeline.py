"""Rewrite pipeline: score → rewrite → rescore until target met or passes run out."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from lexara.models.rewrite import RewriteWarning, Tone
from lexara.models.scoring import FrameworkScore
from lexara.rewriting.prompts import (
    SYSTEM_PROMPT,
    build_initial_prompt,
    build_retry_prompt,
)
from lexara.rewriting.providers.base import LLMProvider, RewriteInstruction
from lexara.rewriting.providers.errors import ProviderError
from lexara.services.scoring_service import UnscoreableTextError

Scorer = Callable[[str], tuple[list[FrameworkScore], float]]


@dataclass
class RewriteOutcome:
    rewritten_text: str
    original_scores: list[FrameworkScore]
    rewritten_scores: list[FrameworkScore]
    original_grade: float
    rewritten_grade: float
    passes_used: int
    attempts_used: int
    hit_target: bool
    provider_name: str
    skipped_rewrite: bool = False
    skip_reason: str | None = None
    warnings: list[RewriteWarning] = field(default_factory=list)
    provider_passes_attempted: int = 0
    provider_passes_failed: int = 0
    degraded: bool = False
    history: list[dict] = field(default_factory=list)


def _within_target(grade: float, target: float, tolerance: float) -> bool:
    return abs(grade - target) <= tolerance


def _score_text(
    scorer: Scorer,
    text: str,
    *,
    warnings: list[RewriteWarning],
    pass_number: int | None,
) -> tuple[list[FrameworkScore], float] | None:
    try:
        return scorer(text)
    except UnscoreableTextError as exc:
        warnings.append(
            RewriteWarning(
                code="unscoreable_text",
                message=str(exc),
                pass_number=pass_number,
                details={"phase": "rescore"},
            )
        )
        return None
    except Exception as exc:  # noqa: BLE001 — rescore must not abort the workflow
        warnings.append(
            RewriteWarning(
                code="scoring_failed",
                message=f"Scoring failed: {exc}",
                pass_number=pass_number,
                details={"exception": type(exc).__name__},
            )
        )
        return None


def run_rewrite(
    *,
    text: str,
    target_grade: float,
    preserve_meaning: bool,
    tone: Tone,
    max_passes: int,
    tolerance: float,
    provider: LLMProvider,
    scorer: Scorer,
) -> RewriteOutcome:
    warnings: list[RewriteWarning] = []
    history: list[dict] = []

    original = _score_text(scorer, text, warnings=warnings, pass_number=None)
    if original is None:
        return RewriteOutcome(
            rewritten_text=text,
            original_scores=[],
            rewritten_scores=[],
            original_grade=0.0,
            rewritten_grade=0.0,
            passes_used=0,
            attempts_used=0,
            hit_target=False,
            provider_name=provider.name,
            degraded=True,
            warnings=warnings,
            history=[{"status": "scoring_failed", "phase": "original"}],
        )

    original_scores, original_grade = original

    # Already at target — skip LLM, return scored original unchanged.
    if _within_target(original_grade, target_grade, tolerance):
        history.append(
            {
                "status": "skipped",
                "reason": "already_at_target",
                "grade": original_grade,
                "target": target_grade,
            }
        )
        return RewriteOutcome(
            rewritten_text=text,
            original_scores=original_scores,
            rewritten_scores=original_scores,
            original_grade=original_grade,
            rewritten_grade=original_grade,
            passes_used=0,
            attempts_used=0,
            hit_target=True,
            provider_name=provider.name,
            skipped_rewrite=True,
            skip_reason="already_at_target",
            warnings=warnings,
            history=history,
        )

    best_text = text
    best_scores = original_scores
    best_grade = original_grade

    current_text = text
    current_grade = original_grade
    passes_used = 0
    provider_attempts = 0
    provider_failures = 0
    any_successful_rewrite = False

    for attempt in range(1, max_passes + 1):
        prompt = (
            build_initial_prompt(current_text, target_grade, preserve_meaning, tone)
            if attempt == 1
            else build_retry_prompt(
                current_text, target_grade, current_grade, preserve_meaning, tone
            )
        )

        provider_attempts += 1
        try:
            result = provider.complete_safe(
                RewriteInstruction(system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
            )
            candidate = result.text
        except ProviderError as exc:
            provider_failures += 1
            warnings.append(
                RewriteWarning(
                    code=exc.code,
                    message=exc.message,
                    pass_number=attempt,
                    details=exc.details or None,
                )
            )
            history.append(
                {"pass": attempt, "status": "provider_error", "code": exc.code}
            )
            continue

        if not candidate.strip():
            warnings.append(
                RewriteWarning(
                    code="empty_response",
                    message="Provider returned empty text; kept previous version.",
                    pass_number=attempt,
                )
            )
            candidate = current_text
        else:
            any_successful_rewrite = True

        scored = _score_text(
            scorer, candidate, warnings=warnings, pass_number=attempt
        )
        if scored is None:
            history.append({"pass": attempt, "status": "rescore_failed"})
            continue

        cand_scores, cand_grade = scored
        passes_used = attempt

        history.append(
            {
                "pass": attempt,
                "grade": cand_grade,
                "target": target_grade,
                "distance": round(abs(cand_grade - target_grade), 1),
                "chars": len(candidate),
                "status": "ok",
            }
        )

        if abs(cand_grade - target_grade) < abs(best_grade - target_grade):
            best_text, best_scores, best_grade = candidate, cand_scores, cand_grade

        current_text, current_grade = candidate, cand_grade
        if _within_target(cand_grade, target_grade, tolerance):
            break

    hit_target = _within_target(best_grade, target_grade, tolerance)
    degraded = bool(warnings) or (
        provider_attempts > 0 and not any_successful_rewrite and not hit_target
    )

    return RewriteOutcome(
        rewritten_text=best_text,
        original_scores=original_scores,
        rewritten_scores=best_scores,
        original_grade=original_grade,
        rewritten_grade=best_grade,
        passes_used=passes_used,
        attempts_used=passes_used,
        hit_target=hit_target,
        provider_name=provider.name,
        warnings=warnings,
        provider_passes_attempted=provider_attempts,
        provider_passes_failed=provider_failures,
        degraded=degraded,
        history=history,
    )
