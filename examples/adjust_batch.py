"""Batch-adjust multiple passages — score + rewrite loop per item."""

from __future__ import annotations

from lexara import LexaraClient

PASSAGES = [
    (
        "The committee will subsequently utilize numerous additional resources "
        "to facilitate the comprehensive demonstration.",
        5,
    ),
    (
        "- Define photosynthesis.\n- Explain how plants utilize sunlight.\n"
        "- Describe the role of chlorophyll.",
        5,
    ),
]


def main() -> None:
    client = LexaraClient(api_key="dev-local-key")

    for i, (text, target) in enumerate(PASSAGES, 1):
        r = client.readability.adjust(text, target_grade=target, max_passes=4)
        print(f"[{i}] target grade {target} | hit={r.hit_target} | "
              f"{r.improvement.grade_level_before:g}→{r.improvement.grade_level_after:g}")
        print(f"    {r.improvement.summary}\n")

    client.close()


if __name__ == "__main__":
    main()
