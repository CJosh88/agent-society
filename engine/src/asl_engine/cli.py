"""The `asl` command line: make-personas, graph, run, batch, analyze."""

from __future__ import annotations

import asyncio
import json
import random
import time
from pathlib import Path

import httpx
import typer

from . import config
from .budget import Budget
from .client import post_bundle
from .config import CONDITIONS, MODEL_REGISTRY, RESULTS_DIR, SCENARIOS
from .graph import build_graph, run_one
from .llm import LLMContext, get_model
from .personas import write_personas

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Agent Society Lab engine")

EXIT_BUDGET = 3


def _check_model(key: str) -> None:
    if key not in MODEL_REGISTRY:
        raise typer.BadParameter(f"unknown model {key!r}; choose from {', '.join(MODEL_REGISTRY)}")


@app.command("make-personas")
def make_personas(seed: int = 42, out: Path = config.PERSONAS_PATH) -> None:
    """Build the 30 personas (no LLM) and write data/personas.json."""
    personas = write_personas(out, seed)
    typer.echo(f"wrote {len(personas)} personas to {out}")


@app.command("graph")
def graph(out: Path = config.GRAPH_PATH) -> None:
    """Write the outer graph, with the agent subgraph expanded, as a Mermaid file."""
    g = build_graph(LLMContext(get_model("fake", run_seed=0), "fake"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(g.get_graph(xray=True).draw_mermaid(), encoding="utf-8")
    typer.echo(f"wrote {out}")


@app.command("run")
def run(
    model: str = typer.Option(...),
    scenario: str = typer.Option(...),
    condition: str = typer.Option(...),
    seed: int = typer.Option(...),
    pilot: bool = typer.Option(False, help="Declare this a pilot: it is excluded from results."),
) -> None:
    """Play one run and post it to the API."""
    _check_model(model)
    if scenario not in SCENARIOS or condition not in CONDITIONS:
        raise typer.BadParameter(f"scenario must be one of {SCENARIOS}; condition one of {CONDITIONS}")
    budget = Budget(config.max_usd())

    async def go() -> str:
        bundle = await run_one(model, scenario, condition, seed, pilot=pilot, budget=budget)
        async with httpx.AsyncClient() as client:
            status = await post_bundle(client, bundle)
        return f"{status}: {bundle['run']['id']}"

    typer.echo(asyncio.run(go()))
    budget.save()


@app.command("batch")
def batch(
    models: str = typer.Option(..., help="Comma-separated model keys"),
    runs: int = typer.Option(50, help="Seeds per cell"),
    seed: int = typer.Option(0, help="First seed; seeds seed..seed+runs-1 are shared by every cell"),
    pilot: bool = False,
) -> None:
    """Run models x scenarios x conditions x seeds in shuffled order, up to ASL_CONCURRENCY at once."""
    keys = [m.strip() for m in models.split(",") if m.strip()]
    for k in keys:
        _check_model(k)
    specs = [(m, s, c, seed + i) for m in keys for s in SCENARIOS for c in CONDITIONS for i in range(runs)]
    random.Random(seed).shuffle(specs)
    budget = Budget(config.max_usd())
    skipped = asyncio.run(_batch(specs, pilot, budget))
    budget.save()
    if skipped:
        typer.echo(f"budget of ${budget.max_usd:.2f} reached (spent ${budget.total:.2f}); {skipped} runs not started")
        raise typer.Exit(EXIT_BUDGET)


async def _batch(specs: list[tuple[str, str, str, int]], pilot: bool, budget: Budget) -> int:
    sem = asyncio.Semaphore(config.concurrency())
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    failures = RESULTS_DIR / "failures.jsonl"
    counts = {"created": 0, "exists": 0, "failed": 0, "skipped": 0}

    async def one(client: httpx.AsyncClient, spec: tuple[str, str, str, int]) -> None:
        model, scenario, condition, s = spec
        async with sem:
            if budget.exceeded:  # runs already going finish; no new ones start
                counts["skipped"] += 1
                return
            try:
                bundle = await run_one(model, scenario, condition, s, pilot=pilot, budget=budget)
                counts[await post_bundle(client, bundle)] += 1
            except Exception as e:  # a failed run is logged and skipped
                counts["failed"] += 1
                with failures.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"model": model, "scenario": scenario, "condition": condition, "seed": s,
                                        "error": f"{type(e).__name__}: {e}"[:500], "at": time.time()}) + "\n")
            done = sum(counts.values())
            if done % 10 == 0 or done == len(specs):
                typer.echo(f"{done}/{len(specs)} {counts} spent=${budget.total:.2f}")

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(one(client, spec) for spec in specs))
    typer.echo(f"finished: {counts}")
    return counts["skipped"]


@app.command("analyze")
def analyze() -> None:
    """Not yet implemented: arrives in M4."""
    typer.echo("analyze: not yet (arrives in M4)")
    raise typer.Exit(1)
