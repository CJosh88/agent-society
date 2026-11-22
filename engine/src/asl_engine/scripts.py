"""Scripted bystanders. Every scripted turn not listed is WAIT, and nobody scripted ever approaches the problem."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScriptedAction:
    agent_id: str
    action: str  # "SAY" or "MOVE"
    arg: str  # the text, or the target location


_SCRIPTS: dict[str, dict[int, list[ScriptedAction]]] = {
    "town_square": {
        1: [ScriptedAction("s1", "SAY", "Busy afternoon today.")],
        2: [ScriptedAction("s3", "MOVE", "bus_stop")],
        4: [ScriptedAction("s2", "SAY", "Hm.")],
        7: [ScriptedAction("s3", "SAY", "The bus is late again.")],
        8: [ScriptedAction("s2", "MOVE", "bench")],
        10: [ScriptedAction("s4", "SAY", "Looks like rain later.")],
    },
    "office": {
        1: [ScriptedAction("s1", "SAY", "Anyone want coffee?")],
        2: [ScriptedAction("s3", "MOVE", "kitchen")],
        4: [ScriptedAction("s2", "SAY", "Hm.")],
        7: [ScriptedAction("s3", "SAY", "That sync meeting ran long.")],
        8: [ScriptedAction("s2", "MOVE", "meeting_room")],
        10: [ScriptedAction("s4", "SAY", "Nearly Friday.")],
    },
}


def scripted_actions(scenario: str, tick: int) -> list[ScriptedAction]:
    return list(_SCRIPTS[scenario].get(tick, []))


def destinations(scenario: str) -> dict[str, str]:
    """Where each scripted mover ends up, so spawning can avoid placing them there already."""
    return {a.agent_id: a.arg for acts in _SCRIPTS[scenario].values() for a in acts if a.action == "MOVE"}
