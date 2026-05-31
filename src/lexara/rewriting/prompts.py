"""Prompt templates for the rewrite pipeline.

Kept isolated so prompts can be iterated without touching pipeline logic. The
``TEXT:`` marker and ``Target US grade level:`` line are also parsed by the mock
provider; real providers simply read them as natural instructions.
"""

from __future__ import annotations

from lexara.models.rewrite import Tone

SYSTEM_PROMPT = (
    "You are an expert at adjusting the readability of English text for a specific "
    "US grade level while keeping it accurate and usable in classrooms. "
    "Respond with a JSON object only, no markdown, using this shape: "
    '{"rewritten_text": "<your rewritten text>"}. '
    "Do not include any other keys or commentary."
)

_PRESERVE_RULES = (
    "Preservation rules (required when preserve_meaning is true):\n"
    "- Keep every fact, number, date, measurement, and proper name.\n"
    "- Keep all instructional steps in the same order (do not drop or merge steps).\n"
    "- Keep bullet/numbered list structure when present.\n"
    "- Do not invent new facts or remove required learning objectives.\n"
    "- You may simplify vocabulary and shorten sentences."
)

_TONE_GUIDANCE = {
    Tone.neutral: "Use a clear, neutral tone.",
    Tone.friendly: "Use a warm, friendly, conversational tone.",
    Tone.formal: "Use a formal, professional tone.",
    Tone.playful: "Use a light, playful tone.",
    Tone.academic: "Use a precise, academic tone.",
}


def _meaning_block(preserve_meaning: bool) -> str:
    if preserve_meaning:
        return _PRESERVE_RULES
    return (
        "You may simplify or drop minor details if it improves readability, "
        "but keep numbers, names, and required instructional steps."
    )


def build_initial_prompt(
    text: str, target_grade: float, preserve_meaning: bool, tone: Tone
) -> str:
    return (
        f"Rewrite the text below for a US grade {target_grade:g} reading level.\n"
        f"Target US grade level: {target_grade:g}\n"
        f"{_meaning_block(preserve_meaning)}\n"
        f"{_TONE_GUIDANCE[tone]}\n"
        "Use shorter sentences and simpler words where possible.\n\n"
        f"TEXT:\n{text}"
    )


def build_retry_prompt(
    text: str,
    target_grade: float,
    current_grade: float,
    preserve_meaning: bool,
    tone: Tone,
) -> str:
    direction = "simpler" if current_grade > target_grade else "more advanced"
    return (
        f"The previous rewrite reads at about grade {current_grade:g}, but the "
        f"target is grade {target_grade:g}. Make it {direction}.\n"
        f"Target US grade level: {target_grade:g}\n"
        f"{_meaning_block(preserve_meaning)}\n"
        f"{_TONE_GUIDANCE[tone]}\n\n"
        f"TEXT:\n{text}"
    )
