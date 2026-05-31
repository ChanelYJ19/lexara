"""Minimal end-to-end SDK example — rewrite workflow first."""

from __future__ import annotations

from lexara import LexaraClient, Tone

PASSAGE = (
    "The mitochondrion is frequently described as the powerhouse of the cell "
    "because it generates the majority of the adenosine triphosphate that "
    "subsequently fuels numerous biochemical reactions."
)


def main() -> None:
    client = LexaraClient(api_key="dev-local-key", base_url="http://localhost:8000")

    result = client.readability.rewrite(
        PASSAGE,
        target_grade=5,
        tone=Tone.neutral,
        max_passes=5,
    )

    print("=== rewrite to target grade ===")
    print(result.outcome.summary)
    print(f"\nInput (grade {result.input.estimated_grade_level}):")
    print(f"  {result.input.text[:100]}...")
    print(f"\nOutput (grade {result.output.estimated_grade_level}):")
    print(f"  {result.output.text}")
    print(f"\nHit target: {result.hit_target}")

    scored = client.readability.score(PASSAGE, frameworks=["flesch_kincaid"])
    print(f"\nScore-only FK grade: {scored.scores[0].estimated_grade_level}")

    client.close()


if __name__ == "__main__":
    main()
