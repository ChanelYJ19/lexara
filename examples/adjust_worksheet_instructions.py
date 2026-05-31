"""Rewrite worksheet instructions to a lower grade — typical teacher workflow."""

from __future__ import annotations

from lexara import LexaraClient

INSTRUCTIONS = (
    "Students will subsequently utilize the provided manipulatives to demonstrate "
    "their comprehension of fractional equivalence, and they must obtain sufficient "
    "evidence before completing the assessment."
)


def main() -> None:
    client = LexaraClient(api_key="dev-local-key")

    result = client.readability.rewrite(
        INSTRUCTIONS,
        target_grade=4,
        tone="friendly",
        preserve_meaning=True,
        max_passes=4,
    )

    print("Worksheet instructions — grade adjustment")
    print(f"  {result.improvement.grade_level_before:g} → {result.improvement.grade_level_after:g} "
          f"(target {result.target_grade})")
    print(f"  {result.improvement.summary}\n")
    print(result.rewritten_text)

    client.close()


if __name__ == "__main__":
    main()
