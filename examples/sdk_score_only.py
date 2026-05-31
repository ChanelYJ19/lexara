"""Score-only — check grade before deciding to rewrite."""

from __future__ import annotations

from lexara import LexaraClient

PASSAGE = (
    "Photosynthesis is the biochemical process by which chlorophyll-containing "
    "organisms convert light energy into chemical energy."
)


def main() -> None:
    client = LexaraClient(api_key="dev-local-key")

    scored = client.readability.score(
        PASSAGE,
        frameworks=["flesch_kincaid", "lexile"],
    )

    print("=== score-only ===")
    print(f"Aggregate grade: {scored.aggregate.estimated_grade_level}")
    print(f"Grade band:      {scored.aggregate.grade_band}")
    for fw in scored.scores:
        print(f"  {fw.framework}: {fw.estimated_grade_level}")

    client.close()


if __name__ == "__main__":
    main()
