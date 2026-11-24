"""Spend tracking. Cost comes from token usage; the total persists in results/spend.json across batches."""

from __future__ import annotations

import json
from pathlib import Path

from .config import MODEL_REGISTRY, RESULTS_DIR


class Budget:
    def __init__(self, max_usd: float, path: Path | None = None):
        self.max_usd = max_usd
        self.path = path if path is not None else RESULTS_DIR / "spend.json"
        self.total = 0.0
        self.by_model: dict[str, float] = {}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.total = float(data.get("total_usd", 0.0))
            self.by_model = {k: float(v) for k, v in data.get("by_model", {}).items()}

    @staticmethod
    def cost(model_key: str, input_tokens: int, output_tokens: int) -> float:
        spec = MODEL_REGISTRY[model_key]
        return (input_tokens * spec.price_in + output_tokens * spec.price_out) / 1_000_000

    def add(self, model_key: str, input_tokens: int, output_tokens: int) -> float:
        c = self.cost(model_key, input_tokens, output_tokens)
        self.total += c
        self.by_model[model_key] = self.by_model.get(model_key, 0.0) + c
        return c

    @property
    def exceeded(self) -> bool:
        return self.total >= self.max_usd

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"total_usd": round(self.total, 6), "by_model": {k: round(v, 6) for k, v in self.by_model.items()}}, indent=2)
            + "\n",
            encoding="utf-8",
        )
