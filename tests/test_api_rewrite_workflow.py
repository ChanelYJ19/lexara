"""Rewrite workflow evals for API layer."""

from __future__ import annotations

from lexara.eval.harness import load_dataset

SCIENCE = next(
    s for s in load_dataset().samples if s.source_id == "g5_science_photosynthesis"
)


def test_rewrite_response_includes_input_output_blocks(client, auth_headers):
    resp = client.post(
        "/v1/readability/rewrite",
        json={
            "text": SCIENCE.text,
            "target_grade": SCIENCE.target_grade,
            "max_passes": SCIENCE.max_passes,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["input"]["text"] == SCIENCE.text
    assert body["output"]["text"] == body["rewritten_text"]
    assert body["input"]["estimated_grade_level"] > body["output"]["estimated_grade_level"]
    assert body["outcome"]["grade_change"] < 0
    assert body["outcome"]["summary"]
    assert body["target"]["grade"] == SCIENCE.target_grade
    assert "hit_target" in body["outcome"]
    assert body["execution"]["provider"] == "mock"


def test_rewrite_maps_to_same_endpoint_as_sdk(client, auth_headers):
    resp = client.post(
        "/v1/readability/rewrite",
        json={"text": SCIENCE.text, "target_grade": 6, "max_passes": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["outcome"]["moved_toward_target"] is True
