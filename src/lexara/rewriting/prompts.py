"""Prompt templates for the rewrite pipeline.

Kept isolated so prompts can be iterated without touching pipeline logic. The
``TEXT:`` marker and ``Target US grade level:`` line are also parsed by the mock
provider; real providers simply read them as natural instructions.
"""

from __future__ import annotations

from lexara.models.rewrite import Tone

SYSTEM_PROMPT = (
    "You are an expert at adjusting the readability of text for specific grade "
    "levels while keeping it natural and accurate. "
    "Respond with a JSON object only, no markdown, using this shape: "
    '{"rewritten_text": "<your rewritten text>"}. '
    "Do not include any other keys or commentary."
)

_TONE_GUIDANCE = {
    Tone.neutral: "Use a clear, neutral tone.",
    Tone.friendly: "Use a warm, friendly, conversational tone.",
    Tone.formal: "Use a formal, professional tone.",
    Tone.playful: "Use a light, playful tone.",
    Tone.academic: "Use a precise, academic tone.",
}


def build_initial_prompt(
    text: str, target_grade: float, preserve_meaning: bool, tone: Tone
) -> str:
    meaning = (
        "Preserve the original meaning and all key facts."
        if preserve_meaning
        else "You may simplify or drop minor details if it improves readability."
    )
    return (
        f"Rewrite the text below for a US grade {target_grade:g} reading level.\n"
        f"Target US grade level: {target_grade:g}\n"
        f"{meaning}\n"
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
    meaning = (
        "Keep the meaning intact."
        if preserve_meaning
        else "Minor detail loss is acceptable."
    )
    return (
        f"The previous rewrite reads at about grade {current_grade:g}, but the "
        f"target is grade {target_grade:g}. Make it {direction}.\n"
        f"Target US grade level: {target_grade:g}\n"
        f"{meaning}\n"
        f"{_TONE_GUIDANCE[tone]}\n\n"
        f"TEXT:\n{text}"
    )
