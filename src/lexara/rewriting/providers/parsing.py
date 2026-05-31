"""Parse LLM rewrite responses (JSON-first, plain-text fallback)."""

from __future__ import annotations

import json
import re

from lexara.rewriting.providers.errors import ProviderParseError

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


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

    stripped = content.strip()
    fence = _FENCE_RE.match(stripped)
    if fence:
        stripped = fence.group(1).strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        if strict_json:
            raise ProviderParseError(
                "Expected JSON object with rewritten_text.",
                details={"preview": stripped[:200]},
            ) from None
        return stripped

    if not isinstance(data, dict):
        if strict_json:
            raise ProviderParseError(
                "JSON root must be an object.",
                details={"type": type(data).__name__},
            )
        return stripped

    for key in ("rewritten_text", "text", "rewrite", "output"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    if strict_json:
        raise ProviderParseError(
            "JSON object missing rewritten_text field.",
            details={"keys": list(data.keys())},
        )
    return stripped
