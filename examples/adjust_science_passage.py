"""Lexara core workflow demo — adjust reading level with before/after scores."""

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
    print(f"Target: grade {result.target.grade} ({result.target.target_grade_band})")
    print(f"Hit target: {result.hit_target}")
    print(f"\nBefore: grade {result.before.aggregate_grade_level} ({result.before.grade_band})")
    print(f"After:  grade {result.after.aggregate_grade_level} ({result.after.grade_band})")
    print(f"\n{result.improvement.summary}")
    print(f"\nOriginal:\n  {result.before.text[:120]}...")
    print(f"\nRewritten:\n  {result.after.text}")

    client.close()


if __name__ == "__main__":
    main()
