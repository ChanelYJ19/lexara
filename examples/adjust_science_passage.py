"""Lexara core workflow demo — rewrite to target grade with scored proof."""

from __future__ import annotations

from lexara import LexaraClient

PASSAGE = (
    "Photosynthesis is the biochemical process by which chlorophyll-containing "
    "organisms convert light energy into chemical energy, subsequently producing "
    "glucose and releasing oxygen as a byproduct of cellular metabolism."
)


def main() -> None:
    client = LexaraClient(api_key="dev-local-key", base_url="http://localhost:8000")

    result = client.readability.adjust(PASSAGE, target_grade=6, max_passes=5)

    print("=== Lexara adjust workflow ===")
    print(f"Target: grade {result.target.grade} ({result.target.grade_band})")
    print(f"Hit target: {result.hit_target}")
    print(f"\nInput:  grade {result.input.estimated_grade_level} ({result.input.grade_band})")
    print(f"Output: grade {result.output.estimated_grade_level} ({result.output.grade_band})")
    print(f"\n{result.outcome.summary}")
    print(f"Frameworks improved: {', '.join(result.outcome.frameworks_improved)}")
    print(f"\nOriginal:\n  {result.input.text[:120]}...")
    print(f"\nRewritten:\n  {result.output.text}")

    client.close()


if __name__ == "__main__":
    main()
