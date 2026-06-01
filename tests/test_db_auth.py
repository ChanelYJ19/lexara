"""Confirm that a user created in the DB can authenticate against the API."""

from __future__ import annotations

import secrets

import pytest
from fastapi.testclient import TestClient

from lexara.db.models import User

TEXT = "The mitochondria is the powerhouse of the cell."


@pytest.fixture
def db(app):
    """Yield an open session against the app's in-memory DB, then close it."""
    Session = app.state.db_session_factory
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_db_user_api_key_authenticates(app, db):
    """A key stored only in the DB (not in LEXARA_API_KEYS) must pass auth."""
    key = secrets.token_hex(32)
    user = User(email="alpha@example.com", api_key=key)
    db.add(user)
    db.commit()

    client = TestClient(app)
    resp = client.post(
        "/v1/readability/score",
        json={"text": TEXT},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert resp.status_code == 200, resp.text


def test_db_user_wrong_key_is_rejected(app):
    """A key that exists neither in settings nor in the DB returns 401."""
    client = TestClient(app)
    resp = client.post(
        "/v1/readability/score",
        json={"text": TEXT},
        headers={"Authorization": "Bearer not-a-real-key"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"


def test_signup_creates_user_and_key_works(client, app):
    """POST /signup creates a user; the returned api_key authenticates."""
    resp = client.post("/signup", json={"email": "new@example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert "api_key" in body
    api_key = body["api_key"]

    score_resp = client.post(
        "/v1/readability/score",
        json={"text": TEXT},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert score_resp.status_code == 200


def test_signup_idempotent(client):
    """Signing up with the same email returns the same api_key."""
    r1 = client.post("/signup", json={"email": "repeat@example.com"})
    r2 = client.post("/signup", json={"email": "repeat@example.com"})
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["api_key"] == r2.json()["api_key"]
