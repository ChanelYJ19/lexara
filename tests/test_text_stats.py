from __future__ import annotations

import pytest

from lexara.scoring.text_stats import (
    compute_stats,
    count_syllables,
    tokenize_words,
)
from lexara.scoring.sentence_split import split_sentences


@pytest.mark.parametrize(
    "word,expected",
    [
        ("cat", 1),
        ("apple", 2),
        ("table", 2),
        ("make", 1),
        ("beautiful", 3),
        ("computer", 3),
        ("", 0),
    ],
)
def test_count_syllables(word, expected):
    assert count_syllables(word) == expected


def test_tokenize_and_sentences():
    text = "The cat sat. It ran away! Did it?"
    assert tokenize_words(text) == [
        "The", "cat", "sat", "It", "ran", "away", "Did", "it",
    ]
    assert len(split_sentences(text)) == 3


def test_compute_stats_basic():
    stats = compute_stats("The cat sat on the mat. The dog ran.")
    assert stats.word_count == 9
    assert stats.sentence_count == 2
    assert stats.avg_sentence_length == pytest.approx(4.5)
    assert stats.avg_word_length > 0
    assert stats.syllable_estimate >= stats.word_count


def test_empty_text_stats():
    stats = compute_stats("")
    assert stats.word_count == 0
    assert stats.sentence_count == 0
    assert stats.avg_sentence_length == 0.0
    assert stats.syllable_estimate == 0


def test_punctuation_only_has_no_words():
    stats = compute_stats("... !!! ???")
    assert stats.word_count == 0
    assert stats.sentence_count == 0


def test_bullet_list_stats():
    text = "- Cats are mammals.\n- Dogs are mammals."
    stats = compute_stats(text)
    assert stats.sentence_count == 2
    assert stats.word_count == 6
