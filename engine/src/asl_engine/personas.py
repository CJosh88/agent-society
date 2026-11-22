"""30 personas built without an LLM. Frozen by the prereg-v1 tag."""

from __future__ import annotations

import json
import random
from pathlib import Path

from .config import PERSONAS_PATH
from .models import Persona

# 15 women and 15 men, spread across cultures. Names are unique, so a cast never repeats a name.
NAMES = [
    "Maya Okafor", "Tom Reyes", "Li Wei", "Ana Souza", "Omar Haddad", "Priya Raman", "Lars Eriksson",
    "Fatima Zahra", "Daniel Kim", "Sofia Rossi", "Kwame Mensah", "Yuki Tanaka", "Carlos Mendes",
    "Aisha Khan", "Ivan Petrov", "Hannah Cohen", "Mateo Alvarez", "Nia Johnson", "Arjun Mehta",
    "Chloe Dubois", "Tariq Aziz", "Elena Popescu", "Samuel Bekele", "Mei Lin Chen", "Jonas Becker",
    "Amara Diallo", "Liam O'Connor", "Noor Hassan", "Diego Torres", "Sana Malik",
]

# Roles that make sense both in a town square and at a small online shop. Each is used twice.
OCCUPATIONS = [
    "customer support agent", "warehouse coordinator", "marketing assistant", "accountant", "web developer",
    "graphic designer", "bookkeeper", "operations assistant", "sales associate", "copywriter",
    "product photographer", "IT technician", "logistics planner", "office manager", "data analyst",
]

TRAITS = ["O", "C", "E", "A", "N"]

# One phrase per trait level.
BIO_PHRASES = {
    ("O", "high"): "You enjoy trying new things and unusual ideas.",
    ("O", "low"): "You prefer familiar routines and proven ways of doing things.",
    ("C", "high"): "You are organised and follow through on what you start.",
    ("C", "low"): "You are easygoing and tend to improvise.",
    ("E", "high"): "You are outgoing and talk easily with strangers.",
    ("E", "low"): "You are quiet and keep to yourself in public.",
    ("A", "high"): "You are warm and quick to look after other people.",
    ("A", "low"): "You are blunt and mostly focused on your own business.",
    ("N", "high"): "You tend to worry and feel tense when something unexpected happens.",
    ("N", "low"): "You stay calm and steady under pressure.",
}


def make_personas(seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    n = len(NAMES)
    occupations = OCCUPATIONS * 2
    rng.shuffle(occupations)
    levels: dict[str, list[str]] = {}
    for t in TRAITS:  # each trait is high in exactly half of the personas
        lv = ["high"] * (n // 2) + ["low"] * (n - n // 2)
        rng.shuffle(lv)
        levels[t] = lv
    out = []
    for i, name in enumerate(NAMES):
        big5 = {t: levels[t][i] for t in TRAITS}
        out.append(
            {
                "persona_id": f"p{i + 1:02d}",
                "name": name,
                "age": rng.randint(22, 68),
                "occupation": occupations[i],
                "big5": big5,
                "bio": " ".join(BIO_PHRASES[(t, big5[t])] for t in TRAITS),
            }
        )
    return out


def write_personas(path: Path = PERSONAS_PATH, seed: int = 42) -> list[dict]:
    personas = make_personas(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(personas, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return personas


def load_personas(path: Path = PERSONAS_PATH) -> list[Persona]:
    return [Persona.model_validate(p) for p in json.loads(path.read_text(encoding="utf-8"))]


def pick_cast(seed: int, personas: list[Persona]) -> dict:
    """Seed -> the focal persona, 4 distinct scripted personas and 5 spawn draws (each 0-3).

    The draw order never depends on scenario or condition, so seed s gives the same people in every cell.
    """
    rng = random.Random(seed)
    idx = rng.sample(range(len(personas)), 5)
    spawn_draws = [rng.randrange(4) for _ in range(5)]  # focal, s1, s2, s3, s4
    return {
        "focal": personas[idx[0]],
        "scripted": {f"s{i}": personas[idx[i]] for i in range(1, 5)},
        "spawn_draws": spawn_draws,
    }
