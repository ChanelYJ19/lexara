"""Live OpenAI contract test — skipped unless LEXARA_OPENAI_API_KEY is set.

Run explicitly (never in default CI):
    pip install -e '.[openai,dev]'
    LEXARA_OPENAI_API_KEY=sk-... pytest -m integration -v
"""

from __future__ import annotations

import os

import pytest

from lexara.models.rewrite import RewriteRequest
from lexara.rewriting.providers.openai import OpenAIProvider
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService

pytestmark = pytest.mark.integration

TEXT = (
    "The organization will subsequently utilize numerous additional resources "
    "to facilitate the comprehensive demonstration."
)


def _require_openai_key() -> str:
    key = os.getenv("LEXARA_OPENAI_API_KEY", "").strip()
    if not key:
        pytest.skip("LEXARA_OPENAI_API_KEY not set — skipping live provider test")
    return key


@pytest.fixture
def openai_provider():
    return OpenAIProvider(
        api_key=_require_openai_key(),
        max_retries=1,
        timeout_seconds=45.0,
        max_completion_tokens=2048,
    )


def test_openai_rewrite_produces_simpler_text(openai_provider):
    service = RewriteService(openai_provider, ScoringService())
    result = service.rewrite(
        RewriteRequest(text=TEXT, target_grade=6, max_passes=2, tolerance=2.0)
    )

    assert result.rewritten_text.strip()
    assert result.rewritten_text != TEXT
    assert result.execution.provider == "openai"
    assert result.execution.provider_calls_attempted >= 1
    assert result.outcome.estimated_grade_to <= result.outcome.estimated_grade_from + 1
    assert result.outcome.moved_toward_target or result.hit_target
    assert result.input.frameworks and result.output.frameworks
    assert result.outcome.summary
    assert not result.execution.degraded or result.execution.warnings


def test_openai_provider_failure_returns_structured_warnings(auth_headers):
    """Rewrite endpoint must not 500 when the LLM provider fails."""
    from fastapi.testclient import TestClient

    from lexara.api.app import create_app
    from lexara.config import Settings

    app = create_app(
        Settings(
            api_keys=["test-key"],
            llm_provider="openai",
            openai_api_key="sk-invalid-for-test",
            openai_max_retries=0,
            openai_timeout_seconds=5.0,
            log_level="WARNING",
        )
    )
    live_client = TestClient(app)
    resp = live_client.post(
        "/v1/readability/rewrite",
        json={"text": TEXT, "target_grade": 6, "max_passes": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["execution"]["warnings"]
    assert body["output"]["text"] == TEXT
    assert body["execution"]["degraded"] is True
