"""Constants, the model registry and environment settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ENGINE_VERSION = "0.4.0"
EXPERIMENT = "cascade_v1"
SCENARIO = "triage_cascade"

STUDY_POPULATIONS = ("llama-3.1-8b", "gpt-oss-120b", "claude-haiku-5-5", "mix_early", "mix_late")
SINGLE_POPULATIONS = ("llama-3.1-8b", "gpt-oss-120b", "claude-haiku-5-5")
MIXED_POPULATIONS = ("mix_early", "mix_late")
# The first condition is the baseline: the one every other condition is compared with.
CONDITIONS = ("independent", "weak", "strong", "seeded_wrong")

# The mixed populations: which model is the weaker and which the stronger (confirmed in the C4 pilots).
MIX_PAIR = {"weaker": "llama-3.1-8b", "stronger": "gpt-oss-120b"}
MIX_BLOCK_SHARE = 0.3  # the stronger model's block: 60 of 200 positions
SCRIPTED_SHARE = 0.1  # seeded_wrong scripts the first 20 of 200 positions
MAX_SCRIPTED = 20
PROBE_SAMPLE = 10
N_AGENTS = 200
PICKS = 4

# Repo layout: <root>/engine/src/asl_engine/config.py
ENGINE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = ENGINE_DIR.parent
PERSONAS_PATH = ENGINE_DIR / "data" / "personas.json"
TICKETS_PATH = ENGINE_DIR / "data" / "tickets.json"
RESULTS_DIR = ROOT_DIR / "results"
GRAPH_PATH = ROOT_DIR / "docs" / "graph.mmd"
SCHEMA_PATH = ROOT_DIR / "contracts" / "run-bundle.schema.json"


def load_env(path: Path | None = None) -> bool:
    """Load engine/.env if it exists. Variables already set in the shell win over the file."""
    return load_dotenv(path or ENGINE_DIR / ".env", override=False)


@dataclass(frozen=True)
class ModelSpec:
    key: str
    provider: str  # "fake" | "workers_ai" | "anthropic"
    model_id: str
    price_in: float  # USD per million input tokens
    price_out: float  # USD per million output tokens
    env_vars: tuple[str, ...]
    extra: tuple[tuple[str, object], ...] = ()


MODEL_REGISTRY: dict[str, ModelSpec] = {
    "fake": ModelSpec("fake", "fake", "fake", 0.0, 0.0, ()),
    "llama-3.1-8b": ModelSpec(
        "llama-3.1-8b", "workers_ai", "@cf/meta/llama-3.1-8b-instruct-fast", 0.152, 0.287,
        ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"),
    ),
    "gpt-oss-120b": ModelSpec(
        "gpt-oss-120b", "workers_ai", "@cf/openai/gpt-oss-120b", 0.35, 0.75,
        ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"),
        extra=(("reasoning_effort", "low"),),
    ),
    "gpt-oss-20b": ModelSpec(
        "gpt-oss-20b", "workers_ai", "@cf/openai/gpt-oss-20b", 0.2, 0.3,
        ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"),
        extra=(("reasoning_effort", "low"),),
    ),
    "granite-4-micro": ModelSpec(  # Workers AI lists no price; this is a placeholder for the budget guard
        "granite-4-micro", "workers_ai", "@cf/ibm-granite/granite-4.0-h-micro", 0.1, 0.1,
        ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"),
    ),
    "apertus-8b": ModelSpec(  # Workers AI lists no price; placeholder for the budget guard
        "apertus-8b", "workers_ai", "@cf/swiss-ai/apertus-v1.5-8b", 0.1, 0.1,
        ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"),
    ),
    "glm-4.7-flash": ModelSpec(
        "glm-4.7-flash", "workers_ai", "@cf/zai-org/glm-4.7-flash", 0.0605, 0.4,
        ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"),
    ),
    "claude-haiku-5-5": ModelSpec(
        "claude-haiku-5-5", "anthropic", "claude-haiku-5-5", 0.10, 0.50,
        ("ANTHROPIC_API_KEY",),
        extra=(("thinking", {"type": "disabled"}),),
    ),
}

# Applied to every real client. Sampling parameters (temperature, top_p, top_k, seed) are never set.
CLIENT_MAX_RETRIES = 0
CLIENT_TIMEOUT_S = 60
CLIENT_MAX_TOKENS = 1500


def cf_base_url() -> str:
    return f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CLOUDFLARE_ACCOUNT_ID']}/ai/v1"


def api_url() -> str:
    return os.environ.get("ASL_API_URL", "http://localhost:8080").rstrip("/")


def admin_key() -> str:
    return os.environ.get("ASL_ADMIN_KEY", "dev-admin-key-change-me-00000000")


def concurrency() -> int:
    return int(os.environ.get("ASL_CONCURRENCY", "8"))


def max_usd() -> float:
    return float(os.environ.get("ASL_MAX_USD", "8"))


POPULATIONS = STUDY_POPULATIONS + ("fake",)


def conditions_for(population: str) -> tuple[str, ...]:
    """seeded_wrong is defined for single-model populations only (the fake model counts as single)."""
    return tuple(c for c in CONDITIONS if not (c == "seeded_wrong" and population in MIXED_POPULATIONS))
