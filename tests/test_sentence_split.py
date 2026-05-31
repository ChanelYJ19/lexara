from __future__ import annotations

import pytest

from lexara.scoring.sentence_split import split_sentences


def test_basic_sentences():
    text = "The cat sat. It ran away! Did it?"
    assert len(split_sentences(text)) == 3


def test_abbreviations_do_not_split():
    text = "Dr. Smith visited the U.S. embassy. He returned home."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert "Dr. Smith" in sentences[0]
    assert "U.S." in sentences[0]


def test_bullet_points():
    text = """
- Plants need sunlight.
- They also need water.
2. Roots absorb nutrients.
"""
    sentences = split_sentences(text)
    assert len(sentences) == 3
    assert sentences[0].startswith("Plants")


def test_malformed_punctuation():
    text = "Wait.. What happened??? No way!"
    sentences = split_sentences(text)
    assert len(sentences) >= 2


def test_missing_terminal_punctuation():
    text = "First sentence without ending\nSecond line also open"
    sentences = split_sentences(text)
    assert len(sentences) == 2


def test_empty_text():
    assert split_sentences("") == []
    assert split_sentences("   \n\t  ") == []


def test_very_short_text():
    assert split_sentences("Hi.") == ["Hi."]


def test_eg_ie_abbreviations():
    text = "Use tools, e.g. rulers and protractors. That helps."
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert "e.g." in sentences[0]
