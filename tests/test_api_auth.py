"""Auth enforcement tests for the Lexara API."""

from __future__ import annotations

TEXT = "Photosynthesis converts sunlight into chemical energy stored in glucose."


# ---------------------------------------------------------------------------
# /v1/readability/rewrite — protected
# ---------------------------------------------------------------------------

def test_rewrite_returns_401_with_no_key(client):
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": TEXT, "target_grade": 6},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"] == "unauthorized"
    assert "API key required" in body["message"]


def test_rewrite_returns_401_with_invalid_key(client):
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": TEXT, "target_grade": 6},
        headers={"Authorization": "Bearer not-a-real-key"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"


def test_rewrite_returns_200_with_valid_key(client, auth_headers):
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": TEXT, "target_grade": 6},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "input" in body
    assert "output" in body
    assert "outcome" in body


# ---------------------------------------------------------------------------
# Open endpoints — no auth needed
# ---------------------------------------------------------------------------

def test_health_is_open(client):
    assert client.get("/health").status_code == 200


def test_signup_get_is_open(client):
    assert client.get("/signup").status_code == 200


def test_signup_post_is_open(client):
    resp = client.post("/signup", json={"email": "test@example.com"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_usage_is_open_with_no_key(client):
    resp = client.get("/v1/usage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["requests_today"] == 0
    assert body["requests_total"] == 0


def test_usage_returns_key_suffix_with_valid_key(client, auth_headers):
    resp = client.get("/v1/usage", headers=auth_headers)
    assert resp.status_code == 200
    assert "api_key_suffix" in resp.json()
