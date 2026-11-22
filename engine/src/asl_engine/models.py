"""Pydantic models and reply parsing."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ValidationError, field_validator

Verb = Literal["WAIT", "SAY", "CALL", "SET_PRIORITY"]


class AgentAction(BaseModel):
    """What the focal agent's LLM call must return. Word limits are in the prompt, not enforced here."""

    action: Verb
    priority: Literal["HIGH", "LOW"] | None = None
    text: str | None = None
    thought: str = ""

    @field_validator("priority", mode="before")
    @classmethod
    def _upper(cls, v):
        return v.strip().upper() if isinstance(v, str) else v


class Persona(BaseModel):
    persona_id: str
    name: str
    age: int
    occupation: str
    big5: dict[str, Literal["high", "low"]]
    bio: str


def extract_action(text: str) -> AgentAction | None:
    """Try raw_decode at every '{' and return the LAST candidate that validates as an AgentAction."""
    decoder = json.JSONDecoder()
    found: AgentAction | None = None
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
            found = AgentAction.model_validate(obj)
        except ValidationError:
            continue
    return found
