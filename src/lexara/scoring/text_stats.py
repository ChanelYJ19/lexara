"""Tokenization and surface statistics for readability formulas."""

from __future__ import annotations

import re

from lexara.models.common import TextStats
from lexara.scoring.familiar_words import DALE_CHALL_FAMILIAR
from lexara.scoring.sentence_split import split_sentences

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def tokenize_words(text: str) -> list[str]:
    return _WORD_RE.findall(text)


def count_syllables(word: str) -> int:
    """Estimate syllables via vowel-group heuristics (see README)."""
    word = word.lower()
    if not word:
        return 0

    groups = _VOWEL_GROUP_RE.findall(word)
    count = len(groups)

    if word.endswith("e") and not word.endswith("le") and count > 1:
        count -= 1
    if word.endswith(("es", "ed")) and count > 1 and not _ends_in_voiced(word):
        count -= 1

    return max(1, count)


def _ends_in_voiced(word: str) -> bool:
    stem = word[:-2]
    return bool(stem) and stem[-1] in "tdszx"


def is_difficult(word: str) -> bool:
    return word.lower() not in DALE_CHALL_FAMILIAR


def compute_stats(text: str) -> TextStats:
    words = tokenize_words(text)
    raw_sentences = split_sentences(text)
    sentences = [s for s in raw_sentences if tokenize_words(s)]

    word_count = len(words)
    sentence_count = len(sentences)
    syllables = [count_syllables(w) for w in words]
    total_syllables = sum(syllables)
    char_count = sum(len(w) for w in words)

    # Guard div-by-zero for empty or punctuation-only input.
    effective_sentences = max(sentence_count, 1) if word_count else 0
    avg_sent = (
        round(word_count / effective_sentences, 3) if word_count else 0.0
    )
    avg_word_len = round(char_count / word_count, 3) if word_count else 0.0
    avg_syll = round(total_syllables / word_count, 3) if word_count else 0.0

    return TextStats(
        sentence_count=sentence_count,
        word_count=word_count,
        avg_sentence_length=avg_sent,
        avg_word_length=avg_word_len,
        syllable_estimate=total_syllables,
        difficult_word_count=sum(1 for w in words if is_difficult(w)),
        character_count=char_count,
        complex_word_count=sum(1 for s in syllables if s >= 3),
        avg_syllables_per_word=avg_syll,
    )
