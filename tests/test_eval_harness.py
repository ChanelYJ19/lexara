"""Tests for the rewrite effectiveness eval harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lexara.eval.harness import (
    DEFAULT_DATASET,
    evaluate_sample,
    format_summary_table,
    load_dataset,
    run_eval,
)
from lexara.eval.models import EvalDataset, EvalSample, PassageType
from lexara.rewriting.providers.mock import MockLLMProvider
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService

PASSAGE_TYPES = {
    PassageType.explanation,
    PassageType.instructions,
    PassageType.science,
    PassageType.social_studies,
    PassageType.worksheet,
}


@pytest.fixture
def scoring_service() -> ScoringService:
    return ScoringService()


@pytest.fixture
def rewrite_service(scoring_service) -> RewriteService:
    return RewriteService(MockLLMProvider(), scoring_service)


def test_default_dataset_loads_and_covers_passage_types():
    dataset = load_dataset()
    assert dataset.version >= 1
    assert len(dataset.samples) >= 8
    types = {s.passage_type for s in dataset.samples}
    assert types == PASSAGE_TYPES


def test_dataset_sample_ids_unique():
    dataset = load_dataset()
    ids = [s.source_id for s in dataset.samples]
    assert len(ids) == len(set(ids))


def test_evaluate_sample_returns_required_fields(rewrite_service, scoring_service):
    sample = load_dataset().samples[0]
    result = evaluate_sample(
        sample,
        rewrite_service=rewrite_service,
        scoring_service=scoring_service,
    )
    assert result.source_id == sample.source_id
    assert result.original_grade >= 0
    assert result.target_grade == sample.target_grade
    assert result.rewritten_grade >= 0
    assert isinstance(result.hit_target, bool)
    assert result.attempts_used >= 0
    assert result.delta == round(result.rewritten_grade - result.original_grade, 1)
    assert result.semantic_preservation_notes == ""
    assert isinstance(result.moved_toward_target, bool)
    assert isinstance(result.warnings, list)


def test_run_eval_summary_counts(rewrite_service):
    dataset = EvalDataset(
        samples=[
            EvalSample(
                source_id="tiny",
                passage_type=PassageType.science,
                source_grade_context=10,
                text=(
                    "Photosynthesis converts light energy into chemical energy "
                    "in chlorophyll-containing organisms."
                ),
                target_grade=6,
            )
        ]
    )
    summary = run_eval(dataset, provider=MockLLMProvider())
    assert summary.sample_count == 1
    assert summary.provider == "mock"
    assert len(summary.results) == 1
    assert summary.hit_target_count in (0, 1)
    assert summary.hit_target_rate == summary.hit_target_count / summary.sample_count
    assert summary.mean_abs_delta >= 0
    assert isinstance(summary.avg_grade_delta, float)
    assert isinstance(summary.grade_band_breakdown, dict)


def test_mock_provider_lowers_grade_on_hard_passages():
    summary = run_eval(load_dataset(), provider=MockLLMProvider())
    lowered = [r for r in summary.results if r.delta < 0]
    assert len(lowered) >= len(summary.results) // 2
    assert summary.moved_toward_target_count >= len(summary.results) // 2


def test_format_summary_table_includes_header():
    summary = run_eval(load_dataset(), provider=MockLLMProvider())
    table = format_summary_table(summary)
    assert "Rewrite effectiveness eval" in table
    assert summary.results[0].source_id in table


def test_eval_result_serializes_to_json():
    summary = run_eval(load_dataset(), provider=MockLLMProvider())
    payload = json.loads(json.dumps(summary.model_dump(mode="json")))
    row = payload["results"][0]
    for key in (
        "source_id",
        "original_grade",
        "target_grade",
        "rewritten_grade",
        "hit_target",
        "attempts_used",
        "delta",
        "warnings",
        "semantic_preservation_notes",
    ):
        assert key in row
    assert "hit_target_rate" in payload
    assert "avg_grade_delta" in payload
    assert "grade_band_breakdown" in payload


def test_runner_main_mock_provider(tmp_path, capsys):
    from lexara.eval.runner import main

    out = tmp_path / "eval.json"
    rc = main(
        [
            "--provider",
            "mock",
            "--format",
            "both",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["sample_count"] == len(load_dataset().samples)
    captured = capsys.readouterr()
    assert "Rewrite effectiveness eval" in captured.out


def test_custom_dataset_file(tmp_path):
    path = tmp_path / "mini.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "description": "mini",
                "samples": [
                    {
                        "source_id": "mini_science",
                        "passage_type": "science",
                        "source_grade_context": 9,
                        "text": "Mitochondria generate ATP through cellular respiration.",
                        "target_grade": 6,
                    }
                ],
            }
        )
    )
    dataset = load_dataset(path)
    assert dataset.samples[0].source_id == "mini_science"
    summary = run_eval(dataset, provider=MockLLMProvider())
    assert summary.sample_count == 1


def test_default_dataset_path_exists():
    assert DEFAULT_DATASET.is_file()
