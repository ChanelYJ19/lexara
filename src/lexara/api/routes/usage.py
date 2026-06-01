"""Usage endpoint — no auth required; returns 0 when no key is provided."""

from __future__ import annotations

from fastapi import APIRouter, Request

from lexara.api.dependencies import _extract_key
from lexara.config import Settings

router = APIRouter(prefix="/v1", tags=["usage"])


@router.get("/usage", summary="Request usage for the provided API key")
def usage(request: Request) -> dict:
    settings: Settings = request.app.state.settings
    api_key = _extract_key(request)

    if not api_key or api_key not in settings.api_keys:
        return {"requests_today": 0, "requests_total": 0}

    # Placeholder — wire to a real usage store when available.
    return {"requests_today": 0, "requests_total": 0, "api_key_suffix": api_key[-4:]}
