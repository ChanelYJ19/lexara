"""Canonical rewrite request/response examples stay valid against the schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lexara.models.rewrite import RewriteRequest, RewriteResponse

CANONICAL_DIR = Path(__file__).parent.parent / "examples" / "canonical"
CASES = [
    ("rewrite_hit_target.json", True, False),
    ("rewrite_improved_miss.json", False, False),
    ("rewrite_already_at_target.json", True, True),
]


@pytest.mark.parametrize("filename,expect_hit,expect_skipped", CASES)
def test_canonical_example_matches_schema(filename, expect_hit, expect_skipped):
    payload = json.loads((CANONICAL_DIR / filename).read_text())
    RewriteRequest.model_validate(payload["request"])
    response = RewriteResponse.model_validate(payload["response"])
    assert response.outcome.hit_target is expect_hit
    assert response.execution.skipped is expect_skipped
    assert response.outcome.summary
    assert response.input.text == payload["request"]["text"]
    if expect_skipped:
        assert response.output.text == response.input.text
        assert response.execution.passes_used == 0
    else:
        assert response.execution.passes_used >= 1 or expect_hit
