"""FastAPI application factory and service wiring."""

from __future__ import annotations

from fastapi import FastAPI

from lexara.api.errors import register_exception_handlers
from lexara.api.middleware import RequestContextMiddleware
from lexara.api.routes import health, readability, signup, usage
from lexara.config import Settings, get_settings
from lexara.logging_config import configure_logging, get_logger
from lexara.rewriting.providers import build_provider
from lexara.scoring.registry import get_registry
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService

logger = get_logger(__name__)


def _validate_provider_settings(settings: Settings) -> None:
    if settings.llm_provider.lower() != "mock":
        return
    if settings.env.lower() == "production" and not settings.allow_mock_provider:
        raise RuntimeError(
            "LEXARA_LLM_PROVIDER=mock is not allowed when LEXARA_ENV=production "
            "and LEXARA_ALLOW_MOCK_PROVIDER=false. Use openai for external alpha."
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    _validate_provider_settings(settings)
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Lexara — Rewrite to Target Grade API",
        version="0.1.0",
        description=(
            "Edtech developer infrastructure: **rewrite text to the right grade and prove it**. "
            "POST /v1/readability/rewrite scores your passage, rewrites toward a target grade, "
            "and returns input/output snapshots with multi-framework verification. "
            "POST /v1/readability/score is available for score-only diagnostics."
        ),
    )

    # Singletons live on app.state and are injected via dependencies.
    scoring_service = ScoringService(registry=get_registry())
    provider = build_provider(settings)
    app.state.settings = settings
    app.state.scoring_service = scoring_service
    app.state.rewrite_service = RewriteService(provider, scoring_service)

    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(signup.router)
    app.include_router(usage.router)
    app.include_router(readability.router)

    logger.info(
        "app initialized",
        extra={"extra": {"provider": provider.name}},
    )
    return app


app = create_app()


def run() -> None:  # console-script entrypoint: `lexara-api`
    import uvicorn

    uvicorn.run("lexara.api.app:app", host="0.0.0.0", port=8000, reload=False)
