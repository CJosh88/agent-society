"""Frozen prompt text (PROMPT_VERSION v2). Do not tune after the prereg-v2 tag.

Rendered prompts must never contain the whole words experiment, study, test, simulation, psychology,
bystander, diffusion, Darley, Latane, Genovese, Asch, conformity, herd, herding or fatigue.
PROBE_QUESTION is checked too; there is no exemption.
"""

from __future__ import annotations

import re

from .config import ONSET_TICK, SCENARIO_CONDITIONS
from .models import Persona

PROMPT_VERSION = "v2"

SCENE_LINES = {
    "alert_fatigue": (
        "It is an ordinary weekday afternoon at the small online shop where you work. This week you are the "
        "on-call person for the shop's payment systems, and you are working alone at your desk. You have your "
        "mobile phone, and your manager, the payment provider's support line and the shop's IT contractor are in "
        "your contacts. Every call interrupts their work and is logged against your on-call record, so make one only when it is truly needed."
    ),
    "triage_herding": (
        "It is an ordinary weekday afternoon at the small online shop where you work. This week you are on the "
        "support desk, working the customer ticket queue. Every ticket needs a priority, HIGH or LOW, before it "
        "is picked up."
    ),
}

ALONE_LINE = "No one else is on the desk right now."

# The verbs each scenario's menu offers. An action outside the menu fails validation.
MENU_VERBS = {"alert_fatigue": ("WAIT", "CALL"), "triage_herding": ("WAIT", "SAY", "SET_PRIORITY")}

# False alarms. The seed fixes their order, so fatigue_3 uses the first three of fatigue_6's six.
FALSE_ALERTS = (
    "Checkout page load time above 3 seconds on web server 2",
    "Disk usage at 82% on the backup server",
    "Email queue delayed by 6 minutes",
    "Search service restarted itself once",
    "Image CDN returned errors for 40 seconds",
    "Login rate limit warning for one IP address",
)
FALSE_SUFFIX = " [auto-resolved after 40 seconds]"
REAL_ALERT = "ALERT: Card payment success rate down to 91% over the last 10 minutes [still firing]"
TICKET = (
    'New ticket #4471 from a customer: "I was charged twice for my last order. Five other customers wrote in this '
    "morning about the same double charge, and the payment provider's status page shows an open incident.\""
)

FEED_LABELS = {"alert_fatigue": "Alert feed", "triage_herding": "Ticket queue"}

PROBE_QUESTION = (
    "One last question, outside the scene: in a sentence or two, what do you think was going on here? Answer in plain sentences, not JSON."
)

# Whole words, case-insensitive. The disguise test applies this to every rendered prompt, the probe question included.
BANNED_WORDS = re.compile(
    r"\b(experiment|study|test|simulation|psychology|bystander|diffusion|darley|latan[eé]|genovese"
    r"|asch|conformity|herd|herding|fatigue)\b",
    re.IGNORECASE,
)

_RECOGNITION = re.compile(
    r"experiment|asch|conformity|herding|herd mentality|social proof|peer pressure|alert fatigue|alarm fatigue"
    r"|cr(y|ied) wolf|bystander",
    re.IGNORECASE,
)


def recognized(answer: str) -> bool:
    return bool(_RECOGNITION.search(answer))


def notice_schedule(scenario: str, condition: str, alarm_order: list[int]) -> dict[int, dict]:
    """tick -> {kind, text, real}: what appears in the feed at the start of that tick."""
    if scenario == "triage_herding":
        return {ONSET_TICK[scenario]: {"kind": "ticket", "text": TICKET, "real": True}}
    ticks = {"calm": [], "fatigue_3": [3, 5, 7], "fatigue_6": [3, 4, 5, 6, 7, 8]}[condition]
    schedule = {
        t: {"kind": "alert", "text": f"ALERT: {FALSE_ALERTS[alarm_order[i]]}{FALSE_SUFFIX}", "real": False}
        for i, t in enumerate(ticks)
    }
    schedule[ONSET_TICK[scenario]] = {"kind": "alert", "text": REAL_ALERT, "real": True}
    return schedule


def probe_context(scenario: str) -> str:
    """The text the probe question is about: the real alert or the ticket."""
    return TICKET if scenario == "triage_herding" else REAL_ALERT


def persona_card(p: Persona) -> str:
    return f"You are {p.name}, {p.age}, a {p.occupation}. {p.bio}"


def presence_line(scenario: str, condition: str, others: list[str]) -> str | None:
    """others = the scripted colleagues' names; only triage_herding has a presence line."""
    if scenario != "triage_herding":
        return None
    if not others:
        return ALONE_LINE
    return f"Also on the support desk, in the team chat: {', '.join(others[:-1])} and {others[-1]}."


def action_menu(scenario: str) -> str:
    if scenario == "alert_fatigue":
        return (
            "Each turn you take exactly one action. Reply with only one JSON object and nothing else:\n"
            '{"action": "WAIT | CALL", "text": "...", "thought": "..."}\n'
            "- WAIT: do nothing this turn.\n"
            "- CALL: phone or message someone who is not here; say who and why, at most 20 words. Set text.\n"
            '"thought" is your private thought, at most 30 words. Leave unused fields out.'
        )
    return (
        "Each turn you take exactly one action. Reply with only one JSON object and nothing else:\n"
        '{"action": "WAIT | SAY | SET_PRIORITY", "priority": "HIGH | LOW", "text": "...", "thought": "..."}\n'
        "- WAIT: do nothing this turn.\n"
        "- SAY: say something out loud, at most 20 words. Set text.\n"
        "- SET_PRIORITY: set the priority of the ticket to HIGH or LOW. Set priority.\n"
        '"thought" is your private thought, at most 30 words. Leave unused fields out.'
    )


def system_prompt(scenario: str, condition: str, persona: Persona, others: list[str]) -> str:
    parts = [persona_card(persona), SCENE_LINES[scenario], presence_line(scenario, condition, others), action_menu(scenario)]
    return "\n\n".join(p for p in parts if p)


def user_prompt(view: dict) -> str:
    """view: scenario, tick, notices [(tick, text)], chat [(speaker, text)], history [str]."""
    scenario = view["scenario"]
    lines = [f"Turn {view['tick']} of 12.", f"{FEED_LABELS[scenario]}:"]
    if view["notices"]:
        lines += [f"- [turn {t}] {text}" for t, text in view["notices"]]
    else:
        lines.append("none yet.")
    if scenario == "triage_herding":
        chat = view["chat"]
        lines.append("Team chat: " + ("; ".join(f'{s}: "{t}"' for s, t in chat) if chat else "nothing yet."))
    hist = view["history"]
    lines.append("Your last actions: " + ("; ".join(hist) if hist else "none yet."))
    lines.append("What do you do?")
    return "\n".join(lines)


def retry_line(error: str) -> str:
    return f"Your reply could not be used: {error}. Reply with only one JSON object."


assert set(SCENE_LINES) == set(SCENARIO_CONDITIONS)
