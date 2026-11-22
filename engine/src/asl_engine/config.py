"""Constants, the model registry and environment settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENGINE_VERSION = "0.1.0"
EXPERIMENT = "agent_society_v1"

STUDY_MODELS = ("llama-3.1-8b", "gpt-oss-120b", "claude-haiku-5-5")
SCENARIOS = ("town_square", "office")
CONDITIONS = ("alone", "group5", "group5_owner")

MAX_TICKS = 12
PROBLEM_TICK = 3
EARLY_HELP_TICK = 6

# Repo layout: <root>/engine/src/asl_engine/config.py
ENGINE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = ENGINE_DIR.parent
PERSONAS_PATH = ENGINE_DIR / "data" / "personas.json"
RESULTS_DIR = ROOT_DIR / "results"
GRAPH_PATH = ROOT_DIR / "docs" / "graph.mmd"
SCHEMA_PATH = ROOT_DIR / "contracts" / "run-bundle.schema.json"


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
        "llama-3.1-8b", "workers_ai", "@cf/meta/llama-3.1-8b-instruct-fp8", 0.152, 0.287,
        ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"),
    ),
    "gpt-oss-120b": ModelSpec(
        "gpt-oss-120b", "workers_ai", "@cf/openai/gpt-oss-120b", 0.35, 0.75,
        ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"),
        extra=(("reasoning_effort", "low"),),
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
