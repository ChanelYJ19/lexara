"""Parse LLM rewrite responses (JSON-first, plain-text fallback)."""

from __future__ import annotations

import json
import re

from lexara.rewriting.providers.errors import ProviderParseError

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)
_JSON_FIELD_KEYS = ("rewritten_text", "text", "rewrite", "output", "content", "result")


def _strip_wrappers(content: str) -> str:
    stripped = content.strip().lstrip("\ufeff")
    fence = _FENCE_RE.match(stripped)
    if fence:
        return fence.group(1).strip()
    return stripped


def _load_json_object(stripped: str) -> dict | None:
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            data = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return None

    return data if isinstance(data, dict) else None


def _text_from_json_object(data: dict) -> str | None:
    for key in _JSON_FIELD_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def parse_rewrite_text(content: str, *, strict_json: bool = False) -> str:
    """Extract rewritten text from provider output.

    Expected primary shape: ``{"rewritten_text": "..."}``.
    Falls back to plain text unless ``strict_json`` is True.
    """
    if not content or not content.strip():
        raise ProviderParseError(
            "Provider returned empty content.",
            details={"content_length": 0},
        )

    stripped = _strip_wrappers(content)
    data = _load_json_object(stripped)
    if data is not None:
        text = _text_from_json_object(data)
        if text:
            return text
        if strict_json:
            raise ProviderParseError(
                "JSON object missing rewritten_text field.",
                details={"keys": list(data.keys())},
            )

    if strict_json:
        raise ProviderParseError(
            "Expected JSON object with rewritten_text.",
            details={"preview": stripped[:200]},
        )
    return stripped
