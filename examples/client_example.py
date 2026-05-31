"""Minimal end-to-end SDK example — rewrite workflow first."""

from __future__ import annotations

from lexara import LexaraClient

PASSAGE = (
    "The mitochondrion is frequently described as the powerhouse of the cell "
    "because it generates the majority of the adenosine triphosphate that "
    "subsequently fuels numerous biochemical reactions."
)


def main() -> None:
    client = LexaraClient(api_key="dev-local-key", base_url="http://localhost:8000")

    # Core workflow: score → rewrite → rescore
    result = client.readability.adjust(PASSAGE, target_grade=5, max_passes=5)

    print("=== adjust() — Lexara core workflow ===")
    print(result.improvement.summary)
    print(f"\nBefore (grade {result.before.aggregate_grade_level}):")
    print(f"  {result.before.text[:100]}...")
    print(f"\nAfter (grade {result.after.aggregate_grade_level}):")
    print(f"  {result.after.text}")
    print(f"\nTarget met: {result.hit_target}")

    # Score-only when you just need diagnostics
    scored = client.readability.score(PASSAGE, frameworks=["flesch_kincaid"])
    print(f"\nScore-only FK grade: {scored.scores[0].estimated_grade_level}")

    client.close()


if __name__ == "__main__":
    main()
