"""SDK tests. The client's HTTP layer is pointed at the in-process app via an
httpx MockTransport that forwards to the FastAPI TestClient - no real socket.
"""

from __future__ import annotations

import httpx
import pytest

from lexara import (
    AuthenticationError,
    LexaraClient,
    LexaraConnectionError,
    LexaraTimeoutError,
    RewriteOptions,
    Tone,
    ValidationError,
)

COMPLEX = (
    "The organization will subsequently utilize numerous additional resources "
    "to facilitate the comprehensive demonstration."
)


@pytest.fixture
def sdk(client):  # `client` is the FastAPI TestClient from conftest
    def handler(request: httpx.Request) -> httpx.Response:
        resp = client.request(
            request.method,
            request.url.path,
            content=request.content,
            headers={k: v for k, v in request.headers.items()},
        )
        return httpx.Response(resp.status_code, content=resp.content)

    return LexaraClient(
        api_key="test-key", transport=httpx.MockTransport(handler)
    )


def test_sdk_health(sdk):
    assert sdk.health()["status"] == "ok"


def test_sdk_score_returns_typed_model(sdk):
    result = sdk.readability.score("The cat sat.", frameworks=["flesch_kincaid"])
    assert result.scores[0].framework == "flesch_kincaid"
    assert result.stats.word_count == 3


def test_sdk_rewrite_returns_typed_model(sdk):
    result = sdk.readability.rewrite(COMPLEX, target_grade=5, max_passes=3)
    assert result.target.grade == 5
    assert result.rewritten_text
    assert result.input.text == COMPLEX
    assert result.outcome.summary
    assert result.output.frameworks


def test_sdk_rewrite_accepts_tone_and_options(sdk):
    opts = RewriteOptions(
        preserve_meaning=True,
        tone=Tone.friendly,
        max_passes=2,
        tolerance=1.5,
        frameworks=["flesch_kincaid"],
    )
    result = sdk.readability.rewrite(COMPLEX, target_grade=5, options=opts)
    assert result.execution.passes_used <= 2


def test_sdk_adjust_aliases_rewrite(sdk):
    rewrite = sdk.readability.rewrite(COMPLEX, target_grade=5, max_passes=2)
    adjust = sdk.readability.adjust(COMPLEX, target_grade=5, max_passes=2)
    assert rewrite.outcome.estimated_grade_to == adjust.outcome.estimated_grade_to


def test_sdk_raises_authentication_error(client):
    def handler(request: httpx.Request) -> httpx.Response:
        resp = client.request(
            request.method,
            request.url.path,
            content=request.content,
            headers={k: v for k, v in request.headers.items()},
        )
        return httpx.Response(resp.status_code, content=resp.content)

    bad = LexaraClient(api_key="nope", transport=httpx.MockTransport(handler))
    with pytest.raises(AuthenticationError) as exc:
        bad.readability.score("hello world")
    assert exc.value.status_code == 401


def test_sdk_raises_validation_error(client, auth_headers):
    def handler(request: httpx.Request) -> httpx.Response:
        resp = client.request(
            request.method,
            request.url.path,
            content=request.content,
            headers={k: v for k, v in request.headers.items()},
        )
        return httpx.Response(resp.status_code, content=resp.content)

    sdk = LexaraClient(api_key="test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(ValidationError):
        sdk.readability.rewrite(COMPLEX, target_grade=99)


def test_sdk_retries_transient_503(client):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"error": {"code": "unavailable", "message": "busy"}})
        resp = client.request(
            request.method,
            request.url.path,
            content=request.content,
            headers={k: v for k, v in request.headers.items()},
        )
        return httpx.Response(resp.status_code, content=resp.content)

    sdk = LexaraClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        max_retries=1,
    )
    result = sdk.readability.score("The cat sat.")
    assert result.stats.word_count == 3
    assert calls["n"] == 2


def test_sdk_timeout_raises(client):
    class _TimeoutTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

    sdk = LexaraClient(
        api_key="test-key",
        transport=_TimeoutTransport(),
        max_retries=0,
    )
    with pytest.raises(LexaraTimeoutError):
        sdk.readability.rewrite(COMPLEX, target_grade=5)


def test_sdk_connection_error_raises():
    class _FailTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

    sdk = LexaraClient(
        api_key="test-key",
        transport=_FailTransport(),
        max_retries=0,
    )
    with pytest.raises(LexaraConnectionError):
        sdk.readability.score("hello")


def test_sdk_context_manager(client):
    def handler(request: httpx.Request) -> httpx.Response:
        resp = client.request(
            request.method,
            request.url.path,
            content=request.content,
            headers={k: v for k, v in request.headers.items()},
        )
        return httpx.Response(resp.status_code, content=resp.content)

    with LexaraClient(api_key="test-key", transport=httpx.MockTransport(handler)) as sdk:
        assert sdk.health()["status"] == "ok"


def test_sdk_requires_api_key():
    with pytest.raises(ValueError, match="api_key"):
        LexaraClient(api_key="")
