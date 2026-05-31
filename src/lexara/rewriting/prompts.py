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


def _sentence_structure_rules(target_grade: float) -> str:
    if target_grade <= 3:
        length_guidance = "Aim for sentences of 8–10 words on average."
    elif target_grade <= 6:
        length_guidance = "Aim for sentences of 12–15 words on average."
    elif target_grade <= 9:
        length_guidance = "Aim for sentences of 15–20 words on average."
    else:
        length_guidance = "Aim for sentences of 18–25 words on average."
    return (
        "Sentence structure rules:\n"
        f"- {length_guidance}\n"
        "- Split a sentence when it carries two or more separate ideas joined by "
        "a subordinate clause (because, although, which, when, before, after, while, who) "
        "or a heavy infinitive phrase. Split only where it genuinely aids comprehension — "
        "do not split if the result would sound choppy or unnatural.\n"
        "- After splitting when needed, combine closely related short sentences into "
        "one smooth sentence using simple connectors (and, but, so, then).\n"
        "- Do not repeat the same subject more than twice in consecutive sentences; "
        "vary sentence openings to maintain flow.\n"
        "- The rewritten text should sound like it was written by a human teacher, "
        "not a list of facts. Aim for natural, flowing prose at the target grade level.\n"
        "- After restructuring, simplify vocabulary: replace technical or multi-syllable "
        "words with shorter, common alternatives."
    )


def build_initial_prompt(
    text: str, target_grade: float, preserve_meaning: bool, tone: Tone
) -> str:
    return (
        f"Rewrite the text below for a US grade {target_grade:g} reading level.\n"
        f"Target US grade level: {target_grade:g}\n"
        f"{_sentence_structure_rules(target_grade)}\n"
        f"{_meaning_block(preserve_meaning)}\n"
        f"{_TONE_GUIDANCE[tone]}\n\n"
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
    extra = ""
    if current_grade > target_grade + 2:
        extra = (
            f" The text is still too complex. Simplify sentence structure where it "
            f"aids comprehension — break up sentences that carry multiple heavy ideas, "
            f"then simplify vocabulary. Keep the prose natural and flowing; "
            f"do not fragment sentences that are already short and clear."
        )
    return (
        f"The previous rewrite reads at about grade {current_grade:g}, but the "
        f"target is grade {target_grade:g}. Make it {direction}.{extra}\n"
        f"Target US grade level: {target_grade:g}\n"
        f"{_sentence_structure_rules(target_grade)}\n"
        f"{_meaning_block(preserve_meaning)}\n"
        f"{_TONE_GUIDANCE[tone]}\n\n"
        f"TEXT:\n{text}"
    )
