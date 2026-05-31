#!/usr/bin/env python3
"""Demo showcase — three rewrite scenarios for customer calls or Show HN.

Run with the API up (lexara-api) or against the in-process mock via local install.

    python examples/demo_showcase.py
"""

from __future__ import annotations

from lexara import LexaraClient, Tone

DEMO_A_SCIENCE = (
    "Photosynthesis is the biochemical process by which chlorophyll-containing "
    "organisms convert light energy into chemical energy, subsequently producing "
    "glucose and releasing oxygen as a byproduct of cellular metabolism."
)

DEMO_B_WORKSHEET = (
    "Students will subsequently utilize the provided manipulatives to demonstrate "
    "their comprehension of fractional equivalence, and they must obtain sufficient "
    "evidence before completing the assessment."
)

DEMO_C_ALREADY = (
    "Photosynthesis lets plants make food from sunlight. "
    "Plants need sun and water to grow."
)


def _banner(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def demo_a_science(client: LexaraClient) -> None:
    _banner("Demo A — Science passage: simplify to grade 6")
    r = client.readability.rewrite(
        DEMO_A_SCIENCE,
        target_grade=6,
        max_passes=5,
        tolerance=1.5,
    )
    print(f"Grade:  {r.input.estimated_grade_level} → {r.output.estimated_grade_level} (target {r.target.grade})")
    print(f"Hit:    {r.hit_target}")
    print(f"Proof:  {', '.join(r.outcome.frameworks_improved) or 'none'}")
    print(f"\n{r.outcome.summary}")
    print(f"\nRewritten:\n{r.output.text}")


def demo_b_worksheet(client: LexaraClient) -> None:
    _banner("Demo B — Worksheet instructions: friendly grade 4")
    r = client.readability.rewrite(
        DEMO_B_WORKSHEET,
        target_grade=4,
        tone=Tone.friendly,
        preserve_meaning=True,
        max_passes=4,
    )
    print(f"Grade:  {r.input.estimated_grade_level} → {r.output.estimated_grade_level}")
    print(f"Hit:    {r.hit_target}  Passes: {r.execution.passes_used}")
    print(f"\n{r.outcome.summary}")
    print(f"\nRewritten:\n{r.output.text}")


def demo_c_already_at_target(client: LexaraClient) -> None:
    _banner("Demo C — Already at target: skip rewrite")
    r = client.readability.rewrite(
        DEMO_C_ALREADY,
        target_grade=5,
        tolerance=1.0,
    )
    print(f"Skipped: {r.execution.skipped}  Passes: {r.execution.passes_used}")
    print(f"Hit:     {r.hit_target}")
    print(f"\n{r.outcome.summary}")


def main() -> None:
    client = LexaraClient(api_key="dev-local-key", base_url="http://localhost:8000")
    try:
        demo_a_science(client)
        demo_b_worksheet(client)
        demo_c_already_at_target(client)
    finally:
        client.close()
    print("\nDone. See README → Demo script for talk track.\n")


if __name__ == "__main__":
    main()
