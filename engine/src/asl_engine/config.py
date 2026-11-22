"""Constants, the model registry and environment settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ENGINE_VERSION = "0.2.0"
EXPERIMENT = "agent_society_v2"

STUDY_MODELS = ("llama-3.1-8b", "gpt-oss-120b", "claude-haiku-5-5")
SCENARIOS = ("alert_fatigue", "triage_herding")
# The first condition of each scenario is its baseline: the one every other condition is compared with.
SCENARIO_CONDITIONS = {
    "alert_fatigue": ("calm", "fatigue_3", "fatigue_6"),
    "triage_herding": ("alone", "dismiss", "endorse"),
}
ONSET_TICK = {"alert_fatigue": 9, "triage_herding": 3}  # when the real alert or the ticket arrives

MAX_TICKS = 12

# Repo layout: <root>/engine/src/asl_engine/config.py
ENGINE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = ENGINE_DIR.parent
PERSONAS_PATH = ENGINE_DIR / "data" / "personas.json"
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
