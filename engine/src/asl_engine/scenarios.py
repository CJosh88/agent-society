"""Frozen prompt text (PROMPT_VERSION c1). Do not tune after the prereg-c1 tag.

Rendered prompts must never contain the whole words experiment, study, test, simulation, psychology, bystander,
diffusion, Darley, Latane, Genovese, Asch, conformity, herd, herding, fatigue, cascade, popularity or majority.
PROBE_QUESTION is checked too; there is no exemption.
"""

from __future__ import annotations

import re

from .config import PICKS
from .models import Persona
from .tickets import load_tickets

PROMPT_VERSION = "c1"

SCENE_LINE = (
    "It is an ordinary weekday afternoon on the support desk of a small online shop. Each ticket needs a priority, "
    "HIGH or LOW, before it is picked up. Pick four tickets and set a priority for each."
)

MENU = (
    "Reply with only one JSON object and nothing else:\n"
    '{"picks": [{"ticket": "T07", "priority": "HIGH | LOW"}], "thought": "..."}\n'
    "- picks: exactly four different tickets from the list, each with a priority of HIGH or LOW.\n"
    '- "thought" is your private thought, at most 30 words.'
)

SORTED_LINE = "The list is sorted by how many teammates rated each ticket HIGH so far, highest first."

PROBE_QUESTION = (
    "One last question, outside the scene: in a sentence or two, what do you think was going on here? "
    "Answer in plain sentences, not JSON."
)

# Whole words, case-insensitive. The disguise test applies this to every rendered prompt, the probe question included.
BANNED_WORDS = re.compile(
    r"\b(experiment|study|test|simulation|psychology|bystander|diffusion|darley|latan[eé]|genovese"
    r"|asch|conformity|herd|herding|fatigue|cascade|popularity|majority)\b",
    re.IGNORECASE,
)

_RECOGNITION = re.compile(
    r"experiment|asch|conformity|herding|herd mentality|social proof|peer pressure|bandwagon|cascade|majority influence"
    r"|anchoring|groupthink|simulation|simulated",
    re.IGNORECASE,
)


def recognized(answer: str) -> bool:
    return bool(_RECOGNITION.search(answer))


def persona_card(p: Persona) -> str:
    return f"You are {p.name}, {p.age}, a {p.occupation}. {p.bio}"


def system_prompt(persona: Persona) -> str:
    return "\n\n".join([persona_card(persona), SCENE_LINE, MENU])


def user_prompt(view: dict) -> str:
    """view: order (24 ticket ids, already sorted for `strong`), counts (None or {id: {high, total}}), sorted (bool)."""
    text = {t.id: t.text for t in load_tickets()}
    lines = ["Open tickets:"]
    if view["sorted"]:
        lines.append(SORTED_LINE)
    for tid in view["order"]:
        lines.append(f"- {tid}: {text[tid]}")
        if view["counts"] is not None:
            c = view["counts"][tid]
            lines.append(f"  Rated HIGH by teammates so far: {c['high']} of {c['total']}.")
    lines.append(f"Pick {['zero', 'one', 'two', 'three', 'four'][PICKS]} tickets and set a priority for each.")
    return "\n".join(lines)


def retry_line(error: str) -> str:
    return f"Your reply could not be used: {error}. Reply with only one JSON object."
