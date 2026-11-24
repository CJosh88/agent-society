"""The frozen ticket catalogue: 24 tickets with a known truth (12 serious, 12 routine). Text is a draft until C4."""

from __future__ import annotations

import json
from functools import lru_cache

from pydantic import BaseModel

from .config import TICKETS_PATH


class Ticket(BaseModel):
    id: str
    text: str
    truth: str  # "serious" | "routine"


@lru_cache(maxsize=1)
def load_tickets() -> tuple[Ticket, ...]:
    return tuple(Ticket.model_validate(t) for t in json.loads(TICKETS_PATH.read_text(encoding="utf-8")))


def ticket_ids() -> list[str]:
    return [t.id for t in load_tickets()]


def is_serious(ticket_id: str) -> bool:
    return next(t for t in load_tickets() if t.id == ticket_id).truth == "serious"


def is_correct(ticket_id: str, priority: str) -> bool:
    """HIGH is correct for a serious ticket and LOW for a routine one."""
    return (priority == "HIGH") == is_serious(ticket_id)
