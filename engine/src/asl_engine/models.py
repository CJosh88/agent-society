"""Pydantic models and reply parsing."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ValidationError, field_validator


class Pick(BaseModel):
    ticket: str
    priority: Literal["HIGH", "LOW"]

    @field_validator("ticket", "priority", mode="before")
    @classmethod
    def _clean(cls, v):
        return v.strip().upper() if isinstance(v, str) else v


class AgentPicks(BaseModel):
    """What an agent's LLM call must return: its picks and a private thought. Counts are checked in `semantic_error`."""

    picks: list[Pick]
    thought: str = ""


class Persona(BaseModel):
    persona_id: str
    name: str
    age: int
    occupation: str
    big5: dict[str, Literal["high", "low"]]
    bio: str


def extract_picks(text: str) -> AgentPicks | None:
    """Try raw_decode at every '{' and return the LAST candidate that validates as AgentPicks."""
    decoder = json.JSONDecoder()
    found: AgentPicks | None = None
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        try:
            found = AgentPicks.model_validate(obj)
        except ValidationError:
            continue
    return found
