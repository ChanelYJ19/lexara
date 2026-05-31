"""Generate a manual review Markdown table from eval results.

Usage:
    python scripts/generate_review_table.py [path/to/rewrite_eval_*.json]

If no path is given, the most recent file in eval/results/ is used.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_RESULTS_DIR = _PROJECT_ROOT / "eval" / "results"
_REVIEW_DIR = _PROJECT_ROOT / "eval" / "review"
_SNIPPET_LEN = 150


def _snippet(text: str, length: int = _SNIPPET_LEN) -> str:
    text = text.replace("\n", " ").strip()
    return text[:length].rstrip() + "…" if len(text) > length else text


def _most_recent_results() -> Path:
    files = sorted(_RESULTS_DIR.glob("rewrite_eval_*.json"))
    if not files:
        sys.exit(f"No eval results found in {_RESULTS_DIR}")
    return files[-1]


def _select_samples(results: list[dict]) -> list[dict]:
    selected: list[dict] = []
    used_ids: set[str] = set()

    def pick(pool: list[dict], n: int) -> list[dict]:
        candidates = [r for r in pool if r["source_id"] not in used_ids]
        chosen = candidates[:n]
        for r in chosen:
            used_ids.add(r["source_id"])
        return chosen

    # 2 low→lower: original ≤ 4, target ≤ 3
    low_to_lower = [
        r for r in results
        if r["original_grade"] <= 4 and r["target_grade"] <= 3
    ]
    selected += pick(low_to_lower, 2)

    # 2 high→mid: original ≥ 10, target 6–7
    high_to_mid = [
        r for r in results
        if r["original_grade"] >= 10 and 6 <= r["target_grade"] <= 7
    ]
    selected += pick(high_to_mid, 2)

    # 2 worst misses (hit_target=false, sorted by distance from target descending)
    misses = sorted(
        [r for r in results if not r["hit_target"]],
        key=lambda r: abs(r["rewritten_grade"] - r["target_grade"]),
        reverse=True,
    )
    selected += pick(misses, 2)

    # 2 best successes (hit_target=true, sorted by smallest abs delta)
    hits = sorted(
        [r for r in results if r["hit_target"]],
        key=lambda r: abs(r["rewritten_grade"] - r["target_grade"]),
    )
    selected += pick(hits, 2)

    # 2 random from grade 5–8 range
    mid_range = [
        r for r in results
        if 5 <= r["original_grade"] <= 8
    ]
    random.seed(42)
    random.shuffle(mid_range)
    selected += pick(mid_range, 2)

    # If any bucket was under-filled, pad with remaining results up to 10
    remaining = [r for r in results if r["source_id"] not in used_ids]
    while len(selected) < 10 and remaining:
        selected.append(remaining.pop(0))

    return selected[:10]


def _md_row(r: dict) -> str:
    cols = [
        r["source_id"],
        _snippet(r.get("original_text", "")),
        f"{r['original_grade']:.1f}",
        f"{r['target_grade']:.1f}",
        _snippet(r.get("rewritten_text", "")),
        f"{r['rewritten_grade']:.1f}",
        "yes" if r["hit_target"] else "no",
        "",
    ]
    return "| " + " | ".join(cols) + " |"


def build_table(results_path: Path) -> str:
    data = json.loads(results_path.read_text())
    provider = data.get("provider", "unknown")
    run_at = data.get("run_at", "")
    summary_line = (
        f"**Provider:** {provider} | "
        f"**Run at:** {run_at} | "
        f"**hit_target_rate:** {data.get('hit_target_rate', 'n/a')} | "
        f"**avg_grade_delta:** {data.get('avg_grade_delta', 'n/a')}"
    )

    samples = _select_samples(data["results"])

    header = (
        "| source_id | original_text_snippet | original_grade | target_grade "
        "| rewritten_text_snippet | rewritten_grade | hit_target | human_notes |"
    )
    sep = (
        "| --- | --- | ---: | ---: | --- | ---: | :---: | --- |"
    )
    rows = [_md_row(r) for r in samples]

    lines = [
        f"# Lexara Rewrite Quality — Manual Review",
        "",
        summary_line,
        "",
        header,
        sep,
        *rows,
        "",
        "> Fill in **human_notes** after reading each rewrite. "
        "Check: meaning preserved? fluency? appropriate difficulty?",
    ]
    return "\n".join(lines)


def main() -> None:
    results_path = Path(sys.argv[1]) if len(sys.argv) > 1 else _most_recent_results()
    if not results_path.exists():
        sys.exit(f"Results file not found: {results_path}")

    table = build_table(results_path)

    # Derive provider name from filename or data for the output filename
    stem = results_path.stem  # e.g. rewrite_eval_openai_2026-05-31
    parts = stem.split("_")
    provider = parts[2] if len(parts) >= 3 else "unknown"
    today = date.today().isoformat()
    out_path = _REVIEW_DIR / f"manual_review_{provider}_{today}.md"
    _REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(table + "\n")
    print(f"Review table written to {out_path}", file=sys.stderr)

    print(table)


if __name__ == "__main__":
    main()
