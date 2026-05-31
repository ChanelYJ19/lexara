"""Live OpenAI contract test — skipped unless LEXARA_OPENAI_API_KEY is set.

Run explicitly:
    LEXARA_OPENAI_API_KEY=sk-... pytest -m integration
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


@pytest.fixture
def openai_provider():
    key = os.getenv("LEXARA_OPENAI_API_KEY")
    if not key:
        pytest.skip("LEXARA_OPENAI_API_KEY not set")
    return OpenAIProvider(api_key=key, max_retries=1, timeout_seconds=45.0)


def test_openai_rewrite_produces_simpler_text(openai_provider):
    service = RewriteService(openai_provider, ScoringService())
    result = service.rewrite(
        RewriteRequest(text=TEXT, target_grade=6, max_passes=2, tolerance=2.0)
    )
    assert result.rewritten_text.strip()
    assert result.rewritten_text != TEXT
    assert result.provider == "openai"
    assert result.delta.provider_passes_attempted >= 1
    assert result.delta.grade_level_after <= result.delta.grade_level_before + 1
    assert not result.degraded or result.warnings
