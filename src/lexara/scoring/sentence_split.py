"""Sentence segmentation tuned for educational text.

Handles bullet lists, common abbreviations (Dr., U.S., e.g.), and malformed
punctuation without pulling in NLP dependencies.
"""

from __future__ import annotations

import re

# Periods in these tokens are not sentence boundaries.
_ABBREV_PATTERN = re.compile(
    r"\b(?:"
    r"Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St|Ste|Mt|Ave|Blvd|Rd"
    r"|vs|etc|e\.g|i\.e"
    r"|U\.S|U\.K|U\.N|E\.U"
    r"|Fig|Figs|Eq|Eqs|No|Nos"
    r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    r"|dept|govt|approx|avg|min|max|vol|pp|ed|eds"
    r"|Inc|Ltd|Corp|Co"
    r")\.",
    re.IGNORECASE,
)

_DOT = "\x00"
_BULLET_PREFIX = re.compile(r"^\s*(?:[-•*●▪►]|(?:\d+[.)]))\s+")
_REPEATED_PUNCT = re.compile(r"([.!?]){2,}")


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u2022", "-").replace("\u00b7", "-").replace("\r\n", "\n")
    text = re.sub(r"[^\S\n]+", " ", text)
    return text.strip()


def _protect_abbreviations(text: str) -> str:
    return _ABBREV_PATTERN.sub(lambda m: m.group(0).replace(".", _DOT), text)


def _restore(text: str) -> str:
    return text.replace(_DOT, ".")


def _split_line(line: str) -> list[str]:
    line = line.strip()
    if not line:
        return []

    line = _REPEATED_PUNCT.sub(r"\1", line)
    protected = _protect_abbreviations(line)

    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"\u201c\'(\[]|\d)', protected)
    if len(parts) == 1 and protected == line:
        parts = re.split(r"(?<=[.!?])\s+", protected)

    sentences: list[str] = []
    for part in parts:
        restored = _restore(part.strip())
        if restored:
            sentences.append(restored)

    if not sentences:
        restored = _restore(line)
        if restored:
            sentences.append(restored)
    return sentences


def split_sentences(text: str) -> list[str]:
    """Return sentence-like units from *text* (may be empty)."""
    text = normalize_text(text)
    if not text:
        return []

    sentences: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        line = _BULLET_PREFIX.sub("", line)
        sentences.extend(_split_line(line))

    return [s for s in sentences if s.strip()]
