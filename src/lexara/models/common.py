"""Shared models used across scoring and rewrite responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TextStats(BaseModel):
    """Surface-level statistics returned with every score response."""

    sentence_count: int
    word_count: int
    avg_sentence_length: float = Field(..., description="Words per sentence.")
    avg_word_length: float = Field(..., description="Mean characters per word.")
    syllable_estimate: int = Field(
        ..., description="Total syllables (vowel-group heuristic, not dictionary-backed)."
    )
    difficult_word_count: int = Field(
        ...,
        description="Words not on the approximate Dale-Chall familiar-word list.",
    )
    # Additional stats useful for formulas and debugging.
    character_count: int = Field(..., description="Letters in words (no whitespace).")
    complex_word_count: int = Field(
        ..., description="Words with >= 3 estimated syllables."
    )
    avg_syllables_per_word: float
