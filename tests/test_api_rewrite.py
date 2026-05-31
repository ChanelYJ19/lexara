from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lexara.api.app import create_app
from lexara.config import Settings
from lexara.rewriting.providers.base import LLMProvider, ProviderResult, RewriteInstruction
from lexara.rewriting.providers.errors import ProviderError
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService

COMPLEX = (
    "The organization will subsequently utilize numerous additional resources "
    "to facilitate the comprehensive demonstration because the requirements are "
    "fundamentally complex."
)


def test_rewrite_happy_path(client, auth_headers):
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": COMPLEX, "target_grade": 5, "max_passes": 4},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rewritten_text"]
    assert body["target"]["grade"] == 5
    assert body["input"]["frameworks"] and body["output"]["frameworks"]
    assert body["outcome"]["estimated_grade_to"] <= body["outcome"]["estimated_grade_from"]
    assert body["outcome"]["summary"]
    assert body["execution"]["provider"] == "mock"


def test_rewrite_requires_api_key(client):
    resp = client.post(
        "/v1/readability/rewrite", json={"text": COMPLEX, "target_grade": 5}
    )
    assert resp.status_code == 401


def test_rewrite_validates_target_grade(client, auth_headers):
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": COMPLEX, "target_grade": 99},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_rewrite_unknown_framework_returns_422(client, auth_headers):
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": COMPLEX, "target_grade": 5, "frameworks": ["nope"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_rewrite_empty_text_is_validation_error(client, auth_headers):
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": "", "target_grade": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_rewrite_returns_request_id(client, auth_headers):
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": COMPLEX, "target_grade": 5, "max_passes": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["request_id"]
    assert resp.headers["x-request-id"]


def test_rewrite_partial_success_with_warnings_not_degraded(auth_headers):
    class _RecoveringProvider(LLMProvider):
        name = "recovering"
        calls = 0

        def complete(self, instruction: RewriteInstruction) -> ProviderResult:
            _RecoveringProvider.calls += 1
            if _RecoveringProvider.calls == 1:
                raise ProviderError("First pass failed", code="provider_transient_error")
            return ProviderResult(
                text="The group will use help. They will show the plan.",
                model="recovering",
            )

    _RecoveringProvider.calls = 0
    app = create_app(Settings(api_keys=["test-key"], llm_provider="mock", log_level="WARNING"))
    app.state.rewrite_service = RewriteService(_RecoveringProvider(), ScoringService())

    resp = TestClient(app).post(
        "/v1/readability/rewrite",
        json={"text": COMPLEX, "target_grade": 5, "max_passes": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["execution"]["warnings"]
    assert body["execution"]["degraded"] is False
    assert body["output"]["text"] != COMPLEX


def test_production_rejects_mock_without_allow_flag():
    with pytest.raises(RuntimeError, match="mock is not allowed"):
        create_app(
            Settings(
                api_keys=["test-key"],
                llm_provider="mock",
                env="production",
                allow_mock_provider=False,
                log_level="WARNING",
            )
        )
