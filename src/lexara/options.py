"""Typed options for SDK readability methods."""

from __future__ import annotations

from dataclasses import dataclass

from lexara.models.rewrite import Tone


@dataclass
class RewriteOptions:
    """Options for ``Readability.rewrite()`` — rewrite to target grade with verification."""

    preserve_meaning: bool = True
    tone: Tone | str = Tone.neutral
    max_passes: int = 3
    frameworks: list[str] | None = None
    tolerance: float = 1.0

    def to_payload_fields(self) -> dict:
        tone = self.tone.value if isinstance(self.tone, Tone) else self.tone
        return {
            "preserve_meaning": self.preserve_meaning,
            "tone": tone,
            "max_passes": self.max_passes,
            "frameworks": self.frameworks,
            "tolerance": self.tolerance,
        }
