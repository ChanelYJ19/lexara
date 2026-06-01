"""Dependency-injection wiring and the API-key auth dependency.

Services are constructed once and cached on ``app.state`` (set in ``app.py``);
these providers just hand them to route functions. Keeping the wiring here makes
routes trivial to test with overrides.
"""

from __future__ import annotations

from fastapi import Request

from lexara.api.errors import AuthenticationError
from lexara.config import Settings
from lexara.db.models import User
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService


def get_settings_from_app(request: Request) -> Settings:
    return request.app.state.settings


def get_scoring_service(request: Request) -> ScoringService:
    return request.app.state.scoring_service


def get_rewrite_service(request: Request) -> RewriteService:
    return request.app.state.rewrite_service


def require_api_key(request: Request) -> str:
    """Authenticate via Bearer token or x-api-key header.

    Checks in order:
    1. LEXARA_API_KEYS in settings (env / .env file — always works for local dev).
    2. api_key column in the users table (DB-registered keys).
    """
    settings: Settings = request.app.state.settings
    api_key = _extract_key(request)
    if not api_key:
        raise AuthenticationError("API key required. Get yours free at /signup")

    if api_key in settings.api_keys:
        request.state.api_key = api_key
        return api_key

    db = request.app.state.db_session_factory()
    try:
        user = db.query(User).filter(User.api_key == api_key).first()
    finally:
        db.close()

    if user is None:
        raise AuthenticationError("API key required. Get yours free at /signup")

    request.state.api_key = api_key
    return api_key


def _extract_key(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key")
