"""Rewrite pipeline: rewrite -> rescore -> retry until target met or passes run out."""

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

Scorer = Callable[[str], tuple[list[FrameworkScore], float]]


@dataclass
class RewriteOutcome:
    rewritten_text: str
    original_scores: list[FrameworkScore]
    rewritten_scores: list[FrameworkScore]
    original_grade: float
    rewritten_grade: float
    passes_used: int
    hit_target: bool
    provider_name: str
    warnings: list[RewriteWarning] = field(default_factory=list)
    provider_passes_attempted: int = 0
    provider_passes_failed: int = 0
    degraded: bool = False
    history: list[dict] = field(default_factory=list)


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
    original_scores, original_grade = scorer(text)

    best_text = text
    best_scores = original_scores
    best_grade = original_grade
    warnings: list[RewriteWarning] = []
    history: list[dict] = []

    current_text = text
    current_grade = original_grade
    passes_used = 0
    provider_attempts = 0
    provider_failures = 0
    any_successful_rewrite = False

    for attempt in range(1, max_passes + 1):
        if attempt == 1:
            prompt = build_initial_prompt(
                current_text, target_grade, preserve_meaning, tone
            )
        else:
            prompt = build_retry_prompt(
                current_text, target_grade, current_grade, preserve_meaning, tone
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
            history.append({"pass": attempt, "status": "provider_error", "code": exc.code})
            continue

        passes_used = attempt

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

        cand_scores, cand_grade = scorer(candidate)
        history.append(
            {
                "pass": attempt,
                "grade": cand_grade,
                "chars": len(candidate),
                "status": "ok",
            }
        )

        if abs(cand_grade - target_grade) < abs(best_grade - target_grade):
            best_text, best_scores, best_grade = candidate, cand_scores, cand_grade

        current_text, current_grade = candidate, cand_grade
        if abs(cand_grade - target_grade) <= tolerance:
            break

    hit_target = abs(best_grade - target_grade) <= tolerance
    degraded = bool(warnings) or (provider_attempts > 0 and not any_successful_rewrite)

    return RewriteOutcome(
        rewritten_text=best_text,
        original_scores=original_scores,
        rewritten_scores=best_scores,
        original_grade=original_grade,
        rewritten_grade=best_grade,
        passes_used=passes_used,
        hit_target=hit_target,
        provider_name=provider.name,
        warnings=warnings,
        provider_passes_attempted=provider_attempts,
        provider_passes_failed=provider_failures,
        degraded=degraded,
        history=history,
    )
