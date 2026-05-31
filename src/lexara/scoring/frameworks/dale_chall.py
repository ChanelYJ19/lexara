"""New Dale-Chall readability.

Faithful implementation of the formula:

    raw = 0.1579 * (difficult_words/words * 100) + 0.0496 * (words/sentences)
    if pct_difficult > 5%: raw += 3.6365

The score is then mapped to a US grade band per Dale-Chall's published table.

APPROXIMATION: "difficult words" are computed against an approximate familiar-
word list (see ``familiar_words``), not the official 3,000-word list.
"""

from __future__ import annotations

from lexara.models.common import TextStats
from lexara.models.scoring import ScoreConfidence
from lexara.scoring.base import ReadabilityFramework


class DaleChall(ReadabilityFramework):
    name = "dale_chall"
    unit = "dale_chall"
    confidence = ScoreConfidence.estimated
    confidence_note = (
        "Uses the published Dale-Chall formula and grade mapping, but "
        "'difficult words' are measured against an approximate familiar-word "
        "list, not the official licensed 3,000-word list."
    )

    def raw_score(self, stats: TextStats) -> float:
        if stats.word_count == 0:
            return 0.0
        pct_difficult = stats.difficult_word_count / stats.word_count * 100
        raw = 0.1579 * pct_difficult + 0.0496 * stats.avg_sentence_length
        if pct_difficult > 5:
            raw += 3.6365
        return raw

    def to_grade_level(self, raw_score: float) -> float:
        # Dale-Chall's published cleaned-score -> grade mapping.
        if raw_score <= 4.9:
            return 4.0  # grade 4 and below
        if raw_score <= 5.9:
            return 5.5  # grades 5-6
        if raw_score <= 6.9:
            return 7.5  # grades 7-8
        if raw_score <= 7.9:
            return 9.5  # grades 9-10
        if raw_score <= 8.9:
            return 11.5  # grades 11-12
        return 14.0  # college
