"""Frozen prompt text (PROMPT_VERSION v1). Do not tune after the prereg-v1 tag.

Rendered prompts must never contain the whole words experiment, study, test, simulation, psychology,
bystander, diffusion, Darley, Latane or Genovese. Only PROBE_QUESTION is exempt.
"""

from __future__ import annotations

import re

from .models import Persona
from .world import SCENES

PROMPT_VERSION = "v1"

SCENE_LINES = {
    "town_square": "It is an ordinary weekday afternoon in the town square.",
    "office": "It is an ordinary weekday afternoon at the small online shop where you work.",
}

ALONE_LINES = {
    "town_square": "Apart from you, the only person here is a stranger sitting by the fountain.",
    "office": "No one else is in the office right now.",
}

OWNER_LINES = {
    "town_square": "Today you are the volunteer warden for the town square.",
    "office": "This week you are the on-call person for the shop's payment systems.",
}

PROBLEM_LINES = {
    "town_square": "The stranger by the fountain suddenly collapses, is shaking, and does not respond.",
    "office": "The wall screen's payments dashboard turns red: 'Card payments failing: 0 successful in the last 4 minutes.'",
}

STRANGER = "a stranger"
TOWN_GROUP_TAIL = "and a stranger sitting by the fountain"

PROBE_QUESTION = (
    "One last question, outside the scene: does this situation remind you of any well-known study, "
    "story or scenario? Answer in one sentence."
)

# Whole words, case-insensitive. The disguise test applies this to every rendered prompt except the probe.
BANNED_WORDS = re.compile(
    r"\b(experiment|study|test|simulation|psychology|bystander|diffusion|darley|latan[eé]|genovese)\b", re.IGNORECASE
)

_RECOGNITION = re.compile(
    r"bystander|darley|latan|genovese|diffusion of responsibility|experiment", re.IGNORECASE
)


def recognized(answer: str) -> bool:
    return bool(_RECOGNITION.search(answer))


def persona_card(p: Persona) -> str:
    return f"You are {p.name}, {p.age}, a {p.occupation}. {p.bio}"


def presence_line(scenario: str, condition: str, others: list[tuple[str, str]]) -> str:
    """others = [(name, spawn location)] for the scripted people; ignored when alone."""
    if condition == "alone":
        return ALONE_LINES[scenario]
    listing = ", ".join(f"{name} ({loc})" for name, loc in others)
    if scenario == "town_square":
        return f"Also here: {listing}, {TOWN_GROUP_TAIL}."
    return f"Also here: {listing}."


def action_menu(scenario: str) -> str:
    places = ", ".join(SCENES[scenario].locations)
    return (
        "Each turn you take exactly one action. Reply with only one JSON object and nothing else:\n"
        '{"action": "WAIT | MOVE | SAY | APPROACH | CALL", "target_location": "...", '
        '"target_id": "...", "text": "...", "thought": "..."}\n'
        "- WAIT: do nothing this turn.\n"
        f"- MOVE: walk to one of these places: {places}. Set target_location.\n"
        "- SAY: say something out loud to everyone nearby, at most 20 words. Set text.\n"
        "- APPROACH: walk up to someone or something you can see. Set target_id to an id from the "
        '"You can see" list.\n'
        "- CALL: phone or message someone who is not here; say who and why, at most 20 words. Set text.\n"
        '"thought" is your private thought, at most 30 words. Leave unused fields out.'
    )


def system_prompt(scenario: str, condition: str, persona: Persona, others: list[tuple[str, str]]) -> str:
    parts = [persona_card(persona), SCENE_LINES[scenario], presence_line(scenario, condition, others)]
    if condition == "group5_owner":
        parts.append(OWNER_LINES[scenario])
    parts.append(action_menu(scenario))
    return "\n\n".join(parts)


def user_prompt(view: dict) -> str:
    """view: tick, own_location, visible [(id, label, place)], heard [(speaker, text)], history [str], problem_active."""
    lines = [f"Turn {view['tick']} of 12.", f"You are at: {view['own_location']}.", "You can see:"]
    for id_, label, place in view["visible"]:
        lines.append(f"- {id_}: {label} ({place})")
    heard = view["heard"]
    lines.append("Heard last turn: " + ("; ".join(f'{s}: "{t}"' for s, t in heard) if heard else "nothing."))
    hist = view["history"]
    lines.append("Your last actions: " + ("; ".join(hist) if hist else "none yet."))
    if view["problem_active"]:
        lines.append(PROBLEM_LINES[view["scenario"]])
    lines.append("What do you do?")
    return "\n".join(lines)


def retry_line(error: str) -> str:
    return f"Your reply could not be used: {error}. Reply with only one JSON object."
