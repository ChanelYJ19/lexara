"""Dependency-injection wiring and the API-key auth dependency.

Services are constructed once and cached on ``app.state`` (set in ``app.py``);
these providers just hand them to route functions. Keeping the wiring here makes
routes trivial to test with overrides.
"""

from __future__ import annotations

from fastapi import Request

from lexara.api.errors import AuthenticationError
from lexara.config import Settings
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService


def get_settings_from_app(request: Request) -> Settings:
    return request.app.state.settings


def get_scoring_service(request: Request) -> ScoringService:
    return request.app.state.scoring_service


def get_rewrite_service(request: Request) -> RewriteService:
    return request.app.state.rewrite_service


def require_api_key(request: Request) -> str:
    """API-key auth (v1 stub).

    Accepts ``Authorization: Bearer <key>`` or ``x-api-key: <key>`` and checks
    membership against the configured key list. Swap this for a real key store /
    rate limiter later without touching routes.
    """
    settings: Settings = request.app.state.settings
    api_key = _extract_key(request)
    if not api_key or api_key not in settings.api_keys:
        raise AuthenticationError(
            "API key required. Get yours free at /signup"
        )
    request.state.api_key = api_key
    return api_key


def _extract_key(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key")
