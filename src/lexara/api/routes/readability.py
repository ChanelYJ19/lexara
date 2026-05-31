"""Readability endpoints — rewrite workflow first, score-only second."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from lexara.api.dependencies import (
    get_rewrite_service,
    get_scoring_service,
    require_api_key,
)
from lexara.api.errors import ValidationError
from lexara.models.rewrite import RewriteRequest, RewriteResponse
from lexara.models.scoring import ScoreRequest, ScoreResponse
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import (
    ScoringService,
    UnknownFrameworkError,
    UnscoreableTextError,
)

router = APIRouter(
    prefix="/v1/readability",
    tags=["readability"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "/rewrite",
    response_model=RewriteResponse,
    summary="Score → rewrite → rescore until target grade",
    description=(
        "Lexara's core workflow. Scores your text across multiple frameworks, "
        "rewrites it toward a target grade level, rescoring after each pass until "
        "the target is met or max_passes is reached. Returns explicit before/after "
        "snapshots with improvement summary."
    ),
)
def rewrite(
    payload: RewriteRequest,
    request: Request,
    service: RewriteService = Depends(get_rewrite_service),
) -> RewriteResponse:
    try:
        result = service.rewrite(payload)
    except UnknownFrameworkError as exc:
        raise ValidationError(str(exc), {"unknown_frameworks": exc.names}) from exc
    result.request_id = getattr(request.state, "request_id", None)
    return result


@router.post(
    "/score",
    response_model=ScoreResponse,
    summary="Multi-framework score only",
    description=(
        "Score text against multiple readability frameworks in one call. "
        "For grade-targeted rewriting with before/after scores, use POST /rewrite."
    ),
)
def score(
    payload: ScoreRequest,
    request: Request,
    service: ScoringService = Depends(get_scoring_service),
) -> ScoreResponse:
    try:
        result = service.score(payload.text, payload.frameworks)
    except UnknownFrameworkError as exc:
        raise ValidationError(str(exc), {"unknown_frameworks": exc.names}) from exc
    except UnscoreableTextError as exc:
        raise ValidationError(str(exc), {"code": "unscoreable_text"}) from exc
    result.request_id = getattr(request.state, "request_id", None)
    return result
