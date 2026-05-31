"""Rewrite workflow evals for API layer."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "rewrite_eval_cases.json"
SCIENCE = next(c for c in json.loads(FIXTURE.read_text())["cases"] if c["id"] == "science_passage")


def test_rewrite_response_includes_input_output_blocks(client, auth_headers):
    resp = client.post(
        "/v1/readability/rewrite",
        json={
            "text": SCIENCE["text"],
            "target_grade": SCIENCE["target_grade"],
            "max_passes": 4,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["input"]["text"] == SCIENCE["text"]
    assert body["output"]["text"] == body["rewritten_text"]
    assert body["input"]["estimated_grade_level"] > body["output"]["estimated_grade_level"]
    assert body["outcome"]["grade_change"] < 0
    assert body["outcome"]["summary"]
    assert body["target"]["grade"] == SCIENCE["target_grade"]
    assert "hit_target" in body["outcome"]
    assert body["execution"]["provider"] == "mock"


def test_sdk_adjust_alias(client, auth_headers):
    """SDK adjust() maps to the same rewrite endpoint."""
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": SCIENCE["text"], "target_grade": 6, "max_passes": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["outcome"]["moved_toward_target"] is True
