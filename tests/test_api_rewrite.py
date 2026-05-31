from __future__ import annotations

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
    assert body["target_grade"] == 5
    assert body["before"]["scores"] and body["after"]["scores"]
    assert body["improvement"]["grade_level_after"] <= body["improvement"]["grade_level_before"]
    assert body["improvement"]["summary"]
    assert body["pipeline"]["provider"] == "mock"


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
