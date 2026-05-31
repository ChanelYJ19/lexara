"""CLI entrypoint for local rewrite effectiveness evals."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from lexara.config import get_settings
from lexara.eval.harness import (
    DEFAULT_DATASET,
    format_summary_table,
    load_dataset,
    run_eval,
)
from lexara.eval.models import EvalRunSummary
from lexara.rewriting.providers import build_provider

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _default_output(provider: str) -> Path:
    today = date.today().isoformat()
    return _PROJECT_ROOT / "eval" / "results" / f"rewrite_eval_{provider}_{today}.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run Lexara rewrite effectiveness evals: score → rewrite → rescore "
            "on a representative K-12 dataset."
        )
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Path to eval dataset JSON (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Write JSON results to this path "
            "(default: eval/results/rewrite_eval_{provider}_{date}.json)"
        ),
    )
    parser.add_argument(
        "--format",
        choices=("json", "table", "both"),
        default="table",
        help="Console output format (default: table)",
    )
    parser.add_argument(
        "--provider",
        choices=("mock", "openai"),
        default=None,
        help="LLM provider override (default: LEXARA_LLM_PROVIDER env)",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.provider:
        settings = settings.model_copy(update={"llm_provider": args.provider})

    dataset = load_dataset(args.dataset)
    provider = build_provider(settings)
    summary = run_eval(dataset, provider=provider)

    payload = summary.model_dump(mode="json")
    out_path = args.output or _default_output(summary.provider)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    if not args.output:
        print(f"Results written to {out_path}", file=sys.stderr)

    if args.format in ("json", "both"):
        print(json.dumps(payload, indent=2))
    if args.format in ("table", "both"):
        if args.format == "both":
            print("\n", file=sys.stderr)
        print(format_summary_table(summary))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
