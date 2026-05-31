"""Rewrite orchestration: score → rewrite → rescore until target grade."""

from __future__ import annotations

from lexara.logging_config import get_logger
from lexara.models.rewrite import RewriteRequest, RewriteResponse
from lexara.rewriting.pipeline import run_rewrite
from lexara.rewriting.providers.base import LLMProvider
from lexara.services.rewrite_response import build_rewrite_response
from lexara.services.scoring_service import ScoringService

logger = get_logger(__name__)


class RewriteService:
    def __init__(
        self, provider: LLMProvider, scoring_service: ScoringService
    ) -> None:
        self._provider = provider
        self._scoring = scoring_service

    def rewrite(self, req: RewriteRequest) -> RewriteResponse:
        self._scoring.validate_frameworks(req.frameworks)

        def scorer(text: str):
            return self._scoring.score_frameworks(text, req.frameworks)

        outcome = run_rewrite(
            text=req.text,
            target_grade=req.target_grade,
            preserve_meaning=req.preserve_meaning,
            tone=req.tone,
            max_passes=req.max_passes,
            tolerance=req.tolerance,
            provider=self._provider,
            scorer=scorer,
        )

        response = build_rewrite_response(req, req.text, outcome)

        logger.info(
            "rewrite workflow complete",
            extra={
                "extra": {
                    "target_grade": req.target_grade,
                    "hit_target": outcome.hit_target,
                    "grade_before": outcome.original_grade,
                    "grade_after": outcome.rewritten_grade,
                    "passes_used": outcome.passes_used,
                    "provider": outcome.provider_name,
                    "degraded": outcome.degraded,
                }
            },
        )
        return response
