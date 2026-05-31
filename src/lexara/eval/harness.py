"""Rewrite effectiveness eval harness — score, rewrite, rescore, summarize."""

from __future__ import annotations

import json
from pathlib import Path

from lexara.eval.models import EvalDataset, EvalResult, EvalRunSummary, EvalSample
from lexara.models.rewrite import RewriteRequest
from lexara.rewriting.providers.base import LLMProvider
from lexara.services.rewrite_service import RewriteService
from lexara.services.scoring_service import ScoringService

DEFAULT_DATASET = Path(__file__).parent / "data" / "rewrite_effectiveness.json"


def load_dataset(path: Path | str | None = None) -> EvalDataset:
    dataset_path = Path(path) if path else DEFAULT_DATASET
    return EvalDataset.model_validate(json.loads(dataset_path.read_text()))


def evaluate_sample(
    sample: EvalSample,
    *,
    rewrite_service: RewriteService,
    scoring_service: ScoringService,
) -> EvalResult:
    """Score original text, rewrite to target grade, return structured eval row."""
    original = scoring_service.score(sample.text, frameworks=None)
    source_grade = original.aggregate.estimated_grade_level

    rewrite = rewrite_service.rewrite(
        RewriteRequest(
            text=sample.text,
            target_grade=sample.target_grade,
            max_passes=sample.max_passes,
            tolerance=sample.tolerance,
            preserve_meaning=True,
        )
    )

    rewritten_grade = rewrite.outcome.estimated_grade_to
    delta = round(rewritten_grade - source_grade, 1)

    return EvalResult(
        source_id=sample.source_id,
        passage_type=sample.passage_type,
        original_grade=source_grade,
        target_grade=sample.target_grade,
        rewritten_grade=rewritten_grade,
        hit_target=rewrite.hit_target,
        attempts_used=rewrite.execution.passes_used,
        delta=delta,
        moved_toward_target=rewrite.outcome.moved_toward_target,
        warnings=[],
        original_text=sample.text,
        rewritten_text=rewrite.output.text,
        semantic_preservation_notes="",
    )


def run_eval(
    dataset: EvalDataset,
    *,
    provider: LLMProvider,
    scoring_service: ScoringService | None = None,
) -> EvalRunSummary:
    scoring = scoring_service or ScoringService()
    rewrite_service = RewriteService(provider, scoring)
    results = [
        evaluate_sample(sample, rewrite_service=rewrite_service, scoring_service=scoring)
        for sample in dataset.samples
    ]
    return EvalRunSummary.from_results(
        provider=provider.name,
        dataset_version=dataset.version,
        results=results,
    )


def format_summary_table(summary: EvalRunSummary) -> str:
    header = (
        f"Rewrite effectiveness eval — provider={summary.provider} "
        f"samples={summary.sample_count} "
        f"hit={summary.hit_target_count} "
        f"moved_toward={summary.moved_toward_target_count} "
        f"mean_|delta|={summary.mean_abs_delta}"
    )
    lines = [header, ""]
    lines.append(
        f"{'source_id':<32} {'type':<14} {'src':>5} {'tgt':>5} {'out':>5} "
        f"{'delta':>6} {'hit':>4} {'pass':>4}"
    )
    lines.append("-" * 88)
    for row in summary.results:
        lines.append(
            f"{row.source_id:<32} {row.passage_type.value:<14} "
            f"{row.original_grade:>5.1f} {row.target_grade:>5.1f} "
            f"{row.rewritten_grade:>5.1f} {row.delta:>+6.1f} "
            f"{'yes' if row.hit_target else 'no':>4} {row.attempts_used:>4}"
        )
    lines.append("")
    lines.append(
        "Fill semantic_preservation_notes in JSON output after manual review for demos."
    )
    return "\n".join(lines)
