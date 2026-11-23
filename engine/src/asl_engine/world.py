"""Everything a world seed fixes: who sits at each position, in what order they see the tickets, who is scripted,
and which positions are probed. Pure functions of (world_seed, position), so conditions and populations are paired
and a smaller world (`--agents 20`) is a prefix-compatible slice of a larger one.
"""

from __future__ import annotations

import hashlib
import random

from .config import (
    MAX_SCRIPTED, MIX_BLOCK_SHARE, MIX_PAIR, MIXED_POPULATIONS, PICKS, PROBE_SAMPLE, SCRIPTED_SHARE,
)
from .models import Persona
from .tickets import is_serious, ticket_ids


def _rng(world_seed: int, position: int, stream: str) -> random.Random:
    digest = hashlib.sha256(f"{world_seed}|{position}|{stream}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def persona_for(world_seed: int, position: int, personas: list[Persona]) -> Persona:
    return personas[_rng(world_seed, position, "persona").randrange(len(personas))]


def ticket_order(world_seed: int, position: int) -> list[str]:
    order = ticket_ids()
    _rng(world_seed, position, "order").shuffle(order)
    return order


def scripted_count(n_agents: int) -> int:
    return min(MAX_SCRIPTED, max(1, round(n_agents * SCRIPTED_SHARE)))


def scripted_picks(world_seed: int, position: int) -> list[tuple[str, str]]:
    """Four tickets and, for each, the rating that is wrong against the truth (seeded_wrong's opening agents)."""
    ids = _rng(world_seed, position, "scripted").sample(ticket_ids(), PICKS)
    return [(t, "LOW" if is_serious(t) else "HIGH") for t in ids]


def probe_positions(world_seed: int, n_agents: int) -> list[int]:
    return sorted(_rng(world_seed, 0, "probe").sample(range(1, n_agents + 1), min(PROBE_SAMPLE, n_agents)))


def model_for_position(population: str, position: int, n_agents: int, pair: dict[str, str] | None = None) -> str:
    """The model key that answers at this position. Single-model populations are their own key."""
    pair = pair or MIX_PAIR
    block = round(n_agents * MIX_BLOCK_SHARE)
    if population == "mix_early":
        return pair["stronger"] if position <= block else pair["weaker"]
    if population == "mix_late":
        return pair["stronger"] if position > n_agents - block else pair["weaker"]
    return population


def model_keys(population: str, pair: dict[str, str] | None = None) -> list[str]:
    pair = pair or MIX_PAIR
    return [pair["weaker"], pair["stronger"]] if population in MIXED_POPULATIONS else [population]
