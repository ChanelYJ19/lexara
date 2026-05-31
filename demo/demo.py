#!/usr/bin/env python3
# Passages verified against real OpenAI eval run 2026-05-31. Do not swap passages without re-verifying output.
"""Lexara live demo — three scenarios in sequence.

Prerequisites:
    lexara-api running at http://localhost:8000
    LEXARA_LLM_PROVIDER=openai
    LEXARA_OPENAI_API_KEY=sk-...

Run:
    source .venv/bin/activate
    python demo/demo.py
"""

from __future__ import annotations

import sys

from lexara import LexaraClient, Tone
from lexara.config import get_settings

# ---------------------------------------------------------------------------
# Verified passages — do not swap without re-running lexara-eval and checking
# hit_target and rewritten_text against a fresh OpenAI run.
# ---------------------------------------------------------------------------

DEMO_A_PASSAGE = (
    "Photosynthesis is the biochemical process by which chlorophyll-containing "
    "organisms convert light energy into chemical energy, subsequently producing "
    "glucose and releasing oxygen as a byproduct of cellular metabolism."
)
# Verified output 2026-05-31: grade 18.3 → 7.4, target 6.0, hit_target=True

DEMO_B_PASSAGE = (
    "Students will subsequently utilize the provided manipulatives to demonstrate "
    "their comprehension of fractional equivalence, and they must obtain sufficient "
    "evidence before completing the assessment."
)
# Verified output 2026-05-31: grade 17.5 → ~4–7 (borderline — check hit_target at runtime)

DEMO_C_PASSAGE = (
    "Photosynthesis lets plants make food from sunlight. "
    "Plants need sun and water to grow."
)
# Verified: already at ~grade 5, skipped=True, passes_used=0


def _check_provider() -> None:
    provider = get_settings().llm_provider.lower()
    if provider != "openai":
        print(
            "\n"
            "╔══════════════════════════════════════════════════════════════════╗\n"
            "║  ERROR: LEXARA_LLM_PROVIDER is not set to 'openai'.             ║\n"
            "║  This demo requires a real LLM — mock output is not             ║\n"
            "║  representative and must not be used in customer-facing demos.  ║\n"
            "║                                                                  ║\n"
            "║  Fix:                                                            ║\n"
            "║    export LEXARA_LLM_PROVIDER=openai                            ║\n"
            "║    export LEXARA_OPENAI_API_KEY=sk-...                          ║\n"
            "║    lexara-api   # restart the API server                        ║\n"
            "╚══════════════════════════════════════════════════════════════════╝\n",
            file=sys.stderr,
        )
        sys.exit(1)


def _header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _result_lines(
    r: object,
    *,
    show_skip: bool = False,
) -> None:
    print(f"  Before : grade {r.input.estimated_grade_level:.1f}")
    print(f"  After  : grade {r.output.estimated_grade_level:.1f}  (target {r.target.grade:g})")
    print(f"  Hit    : {r.hit_target}")
    if show_skip:
        print(f"  Skipped: {r.execution.skipped}  Passes used: {r.execution.passes_used}")
    else:
        print(f"  Passes : {r.execution.passes_used}")
    if r.execution.warnings:
        print(f"  Warnings: {[w.message for w in r.execution.warnings]}")
    print(f"\n  Summary: {r.outcome.summary}")
    if not r.execution.skipped:
        print(f"\n  Rewritten text:\n  {r.output.text}")


def demo_a(client: LexaraClient) -> None:
    _header("DEMO A: Science Passage  —  college → grade 6")
    print(f"\n  Original (grade ~18):\n  {DEMO_A_PASSAGE}\n")
    r = client.readability.rewrite(
        DEMO_A_PASSAGE,
        target_grade=6,
        max_passes=5,
        tolerance=1.5,
    )
    _result_lines(r)
    print(f"\n  Frameworks improved: {', '.join(r.outcome.frameworks_improved) or 'none'}")


def demo_b(client: LexaraClient) -> None:
    _header("DEMO B: Worksheet Instructions  —  grade 4, preserve meaning")
    print(f"\n  Original (grade ~17):\n  {DEMO_B_PASSAGE}\n")
    r = client.readability.rewrite(
        DEMO_B_PASSAGE,
        target_grade=4,
        tone=Tone.friendly,
        preserve_meaning=True,
        max_passes=4,
    )
    _result_lines(r)
    if not r.hit_target:
        print(
            "\n  NOTE: hit_target=False on this passage — borderline result."
            "\n  Show outcome.summary to the audience as the honest signal."
        )


def demo_c(client: LexaraClient) -> None:
    _header("DEMO C: Already at Target  —  no LLM call, no token cost")
    print(f"\n  Passage (grade ~5):\n  {DEMO_C_PASSAGE}\n")
    r = client.readability.rewrite(
        DEMO_C_PASSAGE,
        target_grade=5,
        tolerance=1.0,
    )
    _result_lines(r, show_skip=True)


def main() -> None:
    _check_provider()

    client = LexaraClient(api_key="dev-local-key", base_url="http://localhost:8000")
    try:
        demo_a(client)
        demo_b(client)
        demo_c(client)
    finally:
        client.close()

    print(f"\n{'=' * 60}")
    print("  Done. Talk track: demo/demo_script.md")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
