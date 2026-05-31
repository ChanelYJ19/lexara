"""Health check (unauthenticated)."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["system"])


@router.get("/health")
def health(request: Request) -> dict:
    body: dict = {"status": "ok", "service": "lexara", "version": "0.1.0"}
    settings = getattr(request.app.state, "settings", None)
    if settings is not None:
        body["llm_provider"] = settings.llm_provider
        body["env"] = settings.env
    return body
