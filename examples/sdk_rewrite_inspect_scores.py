"""Rewrite and inspect before/after scores across frameworks."""

from __future__ import annotations

from lexara import LexaraClient

PASSAGE = (
    "The legislative branch is responsible for drafting, debating, and ratifying "
    "laws that govern the populace, while also exercising oversight of the "
    "executive branch through various institutional mechanisms."
)


def main() -> None:
    client = LexaraClient(api_key="dev-local-key")

    result = client.readability.rewrite(PASSAGE, target_grade=6, max_passes=5)

    print("=== rewrite + before/after scores ===")
    print(
        f"Grade: {result.input.estimated_grade_level} → "
        f"{result.output.estimated_grade_level} "
        f"(target {result.target.grade}, hit={result.hit_target})"
    )
    print(f"Delta: {result.outcome.grade_change}")
    print(f"Frameworks improved: {', '.join(result.outcome.frameworks_improved) or 'none'}")
    print()

    print("Before:")
    for fw in result.input.frameworks:
        print(f"  {fw.framework:<18} grade {fw.estimated_grade_level}")

    print("\nAfter:")
    for fw in result.output.frameworks:
        print(f"  {fw.framework:<18} grade {fw.estimated_grade_level}")

    print(f"\nOriginal:\n  {result.input.text[:100]}...")
    print(f"\nRewritten:\n  {result.output.text}")

    client.close()


if __name__ == "__main__":
    main()
