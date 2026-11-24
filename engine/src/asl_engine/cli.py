"""The `asl` command line: make-personas, graph, run, batch. (`analyze` arrives in C5.)"""

from __future__ import annotations

import asyncio
import json
import random
import time
from pathlib import Path

import httpx
import typer

from . import analysis, config
from .budget import Budget
from .client import post_bundle
from .config import CONDITIONS, MODEL_REGISTRY, N_AGENTS, POPULATIONS, RESULTS_DIR, conditions_for
from .graph import build_graph, run_one
from .llm import LLMContext, get_model
from .personas import write_personas

app = typer.Typer(add_completion=False, no_args_is_help=True)

EXIT_BUDGET = 3


@app.callback()
def main() -> None:
    """Agent Society Lab engine."""
    config.load_env()


def _check_population(key: str) -> None:
    if key not in POPULATIONS:
        raise typer.BadParameter(f"unknown population {key!r}; choose from {', '.join(POPULATIONS)}")


@app.command("make-personas")
def make_personas(seed: int = 42, out: Path = config.PERSONAS_PATH) -> None:
    """Build the 30 personas (no LLM) and write data/personas.json."""
    personas = write_personas(out, seed)
    typer.echo(f"wrote {len(personas)} personas to {out}")


@app.command("graph")
def graph(out: Path = config.GRAPH_PATH) -> None:
    """Write the outer graph, with the agent subgraph expanded, as a Mermaid file."""
    g = build_graph({"fake": LLMContext(get_model("fake", run_seed=0), "fake")})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(g.get_graph(xray=True).draw_mermaid(), encoding="utf-8")
    typer.echo(f"wrote {out}")


@app.command("run")
def run(
    population: str = typer.Option(...),
    condition: str = typer.Option(...),
    world_seed: int = typer.Option(...),
    agents: int = typer.Option(N_AGENTS, help="Agents in the world; 200 for the study, fewer for smoke runs."),
    pilot: bool = typer.Option(False, help="Declare this a pilot: it is excluded from results."),
) -> None:
    """Play one world and post it to the API."""
    _check_population(population)
    if condition not in conditions_for(population):
        raise typer.BadParameter(f"conditions for {population}: {', '.join(conditions_for(population))}")
    budget = Budget(config.max_usd())

    async def go() -> str:
        bundle = await run_one(population, condition, world_seed, n_agents=agents, pilot=pilot, budget=budget)
        async with httpx.AsyncClient() as client:
            status = await post_bundle(client, bundle)
        return f"{status}: {bundle['run']['id']}"

    typer.echo(asyncio.run(go()))
    budget.save()


@app.command("batch")
def batch(
    models: str = typer.Option(..., help="Comma-separated populations (single models, mix_early, mix_late, fake)"),
    runs: int = typer.Option(8, help="Worlds per cell"),
    seed: int = typer.Option(0, help="First world seed; seeds seed..seed+runs-1 are shared by every cell"),
    agents: int = typer.Option(N_AGENTS, help="Agents per world"),
    conditions: str = typer.Option("", help="Comma-separated conditions to run; default is every condition"),
    pilot: bool = False,
) -> None:
    """Run populations x conditions x world seeds in shuffled order, up to ASL_CONCURRENCY worlds at once."""
    keys = [m.strip() for m in models.split(",") if m.strip()]
    for k in keys:
        _check_population(k)
    wanted = [c.strip() for c in conditions.split(",") if c.strip()]
    bad = [c for c in wanted if c not in CONDITIONS]
    if bad:
        raise typer.BadParameter(f"unknown condition(s) {', '.join(bad)}; choose from {', '.join(CONDITIONS)}")
    specs = [(pop, c, seed + i) for pop in keys for c in conditions_for(pop) if not wanted or c in wanted
             for i in range(runs)]
    random.Random(seed).shuffle(specs)
    budget = Budget(config.max_usd())
    skipped = asyncio.run(_batch(specs, agents, pilot, budget))
    budget.save()
    if skipped:
        typer.echo(f"budget of ${budget.max_usd:.2f} reached (spent ${budget.total:.2f}); {skipped} runs not started")
        raise typer.Exit(EXIT_BUDGET)


async def _batch(specs: list[tuple[str, str, int]], agents: int, pilot: bool, budget: Budget) -> int:
    sem = asyncio.Semaphore(config.concurrency())
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    failures = RESULTS_DIR / "failures.jsonl"
    counts = {"created": 0, "exists": 0, "failed": 0, "skipped": 0}

    async def one(client: httpx.AsyncClient, spec: tuple[str, str, int]) -> None:
        population, condition, w = spec
        async with sem:
            if budget.exceeded:  # worlds already going finish; no new ones start
                counts["skipped"] += 1
                return
            try:
                bundle = await run_one(population, condition, w, n_agents=agents, pilot=pilot, budget=budget)
                counts[await post_bundle(client, bundle)] += 1
            except Exception as e:  # a failed world is logged and skipped
                counts["failed"] += 1
                with failures.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"population": population, "condition": condition, "world_seed": w,
                                        "error": f"{type(e).__name__}: {e}"[:500], "at": time.time()}) + "\n")
            done = sum(counts.values())
            if done % 10 == 0 or done == len(specs):
                typer.echo(f"{done}/{len(specs)} {counts} spent=${budget.total:.2f}")

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(one(client, spec) for spec in specs))
    typer.echo(f"finished: {counts}")
    return counts["skipped"]


@app.command("analyze")
def analyze(out: Path = typer.Option(None, help="Where to write the report; default results/results.md")) -> None:
    """Read the study worlds from the API and write the results report."""
    out = out or RESULTS_DIR / "results.md"
    worlds = analysis.load_worlds()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(analysis.render(worlds), encoding="utf-8", newline="")
    typer.echo(f"{len(worlds)} worlds analysed -> {out}")
