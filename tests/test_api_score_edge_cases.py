"""API tests for scoring edge cases."""

from __future__ import annotations

TEXT = "The cat sat on the mat. The dog ran fast in the park."


def test_score_unscoreable_text(client, auth_headers):
    resp = client.post(
        "/v1/readability/score",
        json={"text": "... !!!"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["details"]["code"] == "unscoreable_text"
