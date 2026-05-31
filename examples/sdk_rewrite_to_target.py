"""Rewrite to target grade — Lexara's primary SDK workflow."""

from __future__ import annotations

from lexara import LexaraClient, Tone

PASSAGE = (
    "Students will subsequently utilize the provided manipulatives to demonstrate "
    "their comprehension of fractional equivalence."
)


def main() -> None:
    client = LexaraClient(api_key="dev-local-key")

    result = client.readability.rewrite(
        PASSAGE,
        target_grade=4,
        preserve_meaning=True,
        tone=Tone.friendly,
        max_passes=4,
    )

    print("=== rewrite to target grade ===")
    print(result.outcome.summary)
    print(f"Hit target: {result.hit_target}")
    print(f"Passes:     {result.execution.passes_used}")
    print(f"\nRewritten:\n{result.output.text}")

    client.close()


if __name__ == "__main__":
    main()
