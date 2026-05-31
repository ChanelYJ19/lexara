"""Rewrite workflow evals for API layer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "rewrite_eval_cases.json"
SCIENCE = next(c for c in json.loads(FIXTURE.read_text())["cases"] if c["id"] == "science_passage")


def test_rewrite_response_includes_before_after_blocks(client, auth_headers):
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

    assert body["before"]["text"] == SCIENCE["text"]
    assert body["after"]["text"] == body["rewritten_text"]
    assert body["before"]["aggregate_grade_level"] > body["after"]["aggregate_grade_level"]
    assert body["improvement"]["grade_level_change"] < 0
    assert body["improvement"]["summary"]
    assert body["target"]["grade"] == SCIENCE["target_grade"]
    assert "hit_target" in body["target"]
    assert body["pipeline"]["provider"] == "mock"


def test_sdk_adjust_alias(client, auth_headers):
    """SDK adjust() maps to the same rewrite endpoint."""
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": SCIENCE["text"], "target_grade": 6, "max_passes": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["improvement"]["moved_toward_target"] is True
