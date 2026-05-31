"""SDK tests. The client's HTTP layer is pointed at the in-process app via an
httpx MockTransport that forwards to the FastAPI TestClient - no real socket.
"""

from __future__ import annotations

import httpx
import pytest

from lexara import LexaraClient, LexaraError

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
    result = sdk.readability.adjust(COMPLEX, target_grade=5, max_passes=3)
    assert result.target.grade == 5
    assert result.rewritten_text
    assert result.input.text
    assert result.outcome.summary


def test_sdk_raises_on_bad_key(client):
    def handler(request: httpx.Request) -> httpx.Response:
        resp = client.request(
            request.method,
            request.url.path,
            content=request.content,
            headers={k: v for k, v in request.headers.items()},
        )
        return httpx.Response(resp.status_code, content=resp.content)

    bad = LexaraClient(api_key="nope", transport=httpx.MockTransport(handler))
    with pytest.raises(LexaraError) as exc:
        bad.readability.score("hello world")
    assert exc.value.status_code == 401
