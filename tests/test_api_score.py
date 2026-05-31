from __future__ import annotations

TEXT = "The cat sat on the mat. The dog ran fast in the park."


def test_health_is_public(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_score_requires_api_key(client):
    resp = client.post("/v1/readability/score", json={"text": TEXT})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_score_rejects_bad_key(client):
    resp = client.post(
        "/v1/readability/score",
        json={"text": TEXT},
        headers={"Authorization": "Bearer wrong"},
    )
    assert resp.status_code == 401


def test_score_happy_path(client, auth_headers):
    resp = client.post(
        "/v1/readability/score",
        json={"text": TEXT, "frameworks": ["flesch_kincaid", "lexile"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {s["framework"] for s in body["scores"]} == {
        "flesch_kincaid",
        "lexile_estimated",
    }
    assert body["stats"]["word_count"] > 0
    assert body["aggregate"]["grade_band"]
    assert body["request_id"]
    assert resp.headers["x-request-id"]


def test_score_unknown_framework_returns_422(client, auth_headers):
    resp = client.post(
        "/v1/readability/score",
        json={"text": TEXT, "frameworks": ["nope"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_score_empty_text_is_validation_error(client, auth_headers):
    resp = client.post(
        "/v1/readability/score", json={"text": ""}, headers=auth_headers
    )
    assert resp.status_code == 422
