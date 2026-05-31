"""Grade-level normalization and plain-language interpretation helpers."""

from __future__ import annotations

from lexara.models.scoring import ScoreConfidence

_BANDS: list[tuple[float, str]] = [
    (1, "K-1"),
    (3, "2-3"),
    (5, "4-5"),
    (8, "6-8"),
    (12, "9-12"),
    (16, "College"),
]

_CONFIDENCE_PREFIX = {
    ScoreConfidence.exact: "",
    ScoreConfidence.estimated: "Estimated ",
}


def grade_band(grade_level: float) -> str:
    for upper, label in _BANDS:
        if grade_level <= upper:
            return label
    return "College+"


def interpret_grade(
    framework: str, grade_level: float, confidence: ScoreConfidence
) -> str:
    if grade_level <= 3:
        audience = "early elementary readers"
    elif grade_level <= 5:
        audience = "upper elementary readers"
    elif grade_level <= 8:
        audience = "middle-school readers"
    elif grade_level <= 12:
        audience = "high-school readers"
    else:
        audience = "college-level readers"

    prefix = _CONFIDENCE_PREFIX[confidence]
    return (
        f"{prefix}reading level ~grade {grade_level:g}; "
        f"comfortable for {audience}."
    )


def consensus_interpretation(mean_grade: float) -> str:
    band = grade_band(mean_grade)
    return (
        f"Across frameworks the text reads at about grade {mean_grade:g} "
        f"(band {band})."
    )


def confidence_summary(scores: list) -> str:
    exact = [s.framework for s in scores if s.confidence == ScoreConfidence.exact]
    estimated = [s.framework for s in scores if s.confidence == ScoreConfidence.estimated]
    parts: list[str] = []
    if exact:
        parts.append(f"exact: {', '.join(exact)}")
    if estimated:
        parts.append(f"estimated: {', '.join(estimated)}")
    return "; ".join(parts) if parts else "mixed confidence levels"
