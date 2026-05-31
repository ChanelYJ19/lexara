"""Deterministic LLM stand-in for local dev and tests."""

from __future__ import annotations

import json
import re

from lexara.rewriting.providers.base import (
    LLMProvider,
    ProviderResult,
    RewriteInstruction,
)
from lexara.rewriting.providers.parsing import parse_rewrite_text

_SIMPLER_WORDS = {
    "utilize": "use",
    "approximately": "about",
    "demonstrate": "show",
    "subsequently": "later",
    "facilitate": "help",
    "numerous": "many",
    "additional": "more",
    "purchase": "buy",
    "assistance": "help",
    "comprehend": "get",
    "sufficient": "enough",
    "individuals": "people",
    "commence": "start",
    "terminate": "end",
    "endeavor": "try",
    "obtain": "get",
    "require": "need",
    "construct": "build",
    "fundamental": "basic",
    "consequently": "so",
    "however": "but",
    "therefore": "so",
    "regarding": "about",
    "prior": "before",
    "comprehension": "understanding",
    "manipulatives": "tools",
    "equivalence": "same value",
    "biochemical": "chemical",
    "chlorophyll": "green plant parts",
    "organisms": "living things",
    "metabolism": "life processes",
    "heterogeneous": "different",
    "institutional": "school",
    "interventions": "actions",
    "ramifications": "effects",
    "multifaceted": "many",
    "comprehensive": "full",
    "interdisciplinary": "cross-topic",
    "assessment": "test",
    "vocabulary": "words",
    "precipitation": "rain",
    "evaporation": "drying",
    "identify": "name",
    "describe": "tell about",
    "appropriate": "right",
    "components": "parts",
    "fractional": "fraction",
    "evidence": "proof",
    "byproduct": "extra product",
    "cellular": "cell",
}

_TARGET_RE = re.compile(r"target us grade level:\s*([\d.]+)", re.IGNORECASE)
_SPLIT_RE = re.compile(r"\s*(?:,?\s+(?:and|but|so|because|which|while))\s+", re.I)


class MockLLMProvider(LLMProvider):
    name = "mock"

    def complete(self, instruction: RewriteInstruction) -> ProviderResult:
        text, target = _extract_text_and_target(instruction.user_prompt)
        rewritten = _simplify(text, target)
        payload = json.dumps({"rewritten_text": rewritten})
        return ProviderResult(
            text=parse_rewrite_text(payload),
            model="mock",
            raw_content=payload,
        )


def _extract_text_and_target(user_prompt: str) -> tuple[str, float]:
    match = _TARGET_RE.search(user_prompt)
    target = float(match.group(1)) if match else 5.0
    marker = "TEXT:\n"
    idx = user_prompt.find(marker)
    text = user_prompt[idx + len(marker) :].strip() if idx != -1 else user_prompt
    return text, target


def _simplify(text: str, target: float) -> str:
    for hard, simple in _SIMPLER_WORDS.items():
        text = re.sub(rf"\b{hard}\b", simple, text, flags=re.IGNORECASE)

    if target <= 8:
        # Break very long single sentences that lack conjunction split points.
        sentences = re.split(r"(?<=[.!?])\s+", text)
        expanded: list[str] = []
        for sentence in sentences:
            words = tokenize_words_simple(sentence)
            if len(words) > 18 and not _SPLIT_RE.search(sentence):
                mid = len(words) // 2
                first = " ".join(words[:mid]).rstrip(",;")
                second = " ".join(words[mid:]).lstrip(",;")
                expanded.append(f"{first}. {second[0].upper()}{second[1:] if len(second)>1 else ''}")
            else:
                expanded.append(sentence)
        text = " ".join(expanded)

        sentences = re.split(r"(?<=[.!?])\s+", text)
        rebuilt: list[str] = []
        for sentence in sentences:
            parts = [p.strip() for p in _SPLIT_RE.split(sentence) if p.strip()]
            for part in parts:
                if not part.endswith((".", "!", "?")):
                    part += "."
                rebuilt.append(part[0].upper() + part[1:] if part else part)
        text = " ".join(rebuilt)

    return text.strip()


def tokenize_words_simple(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)
