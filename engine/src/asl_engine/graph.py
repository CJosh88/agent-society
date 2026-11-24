"""The outer LangGraph loop over agent positions and the deterministic game master (`record`).

A world is `n_agents` agents acting one after another. Each sees the running HIGH counts of the agents before it
(unless the condition is `independent`), picks four tickets and rates each HIGH or LOW in one call.
"""

from __future__ import annotations

import operator
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from . import scenarios, world
from .agent import TurnState, build_agent_graph
from .config import ENGINE_VERSION, EXPERIMENT, MIX_PAIR, N_AGENTS, SCENARIO
from .llm import LLMContext, get_model, render_prompt
from .personas import load_personas
from .tickets import is_correct, ticket_ids


class RunState(TurnState, total=False):
    # run configuration
    population: str
    condition: str
    world_seed: int
    n_agents: int
    pair: dict
    pilot: bool
    started_at: str
    # the world
    personas: list
    scripted_k: int
    probe_set: list  # positions whose stored context the probe reuses
    pos: int  # the position being played
    counts: dict  # ticket id -> {"high": int, "total": int}, over the agents before `pos`
    scripted: bool
    transcripts: dict  # position -> {"system", "user", "reply", "model_key"}, for the probe sample only
    # outputs; seq is assigned only in `record`, `probe` and `finish`
    events: Annotated[list, operator.add]
    llm_calls: Annotated[list, operator.add]
    agents: Annotated[list, operator.add]
    bundle: dict


def run_id(population: str, condition: str, world_seed: int) -> str:
    key = f"{population}|{SCENARIO}|{condition}|{world_seed}|{scenarios.PROMPT_VERSION}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _events(state: RunState, items: list[tuple[int, str, str | None, dict]]) -> list[dict]:
    """items: (tick, type, agent_id, payload). seq continues from the events already in the state."""
    base = len(state.get("events", []))
    return [
        {"seq": base + i, "tick": tick, "type": t, "agent_id": agent, "payload": payload}
        for i, (tick, t, agent, payload) in enumerate(items)
    ]


def _share(c: dict) -> float:
    return c["high"] / c["total"] if c["total"] else 0.0


# --- nodes ------------------------------------------------------------------------------------


def setup(state: RunState) -> dict[str, Any]:
    n = state["n_agents"]
    seeded = state["condition"] == "seeded_wrong"
    return {
        "personas": load_personas(),
        "scripted_k": world.scripted_count(n) if seeded else 0,
        "probe_set": world.probe_positions(state["world_seed"], n),
        "pos": 0,
        "counts": {t: {"high": 0, "total": 0} for t in ticket_ids()},
        "transcripts": {},
        "started_at": _now(),
    }


def next_agent(state: RunState) -> dict[str, Any]:
    pos, seed, condition = state["pos"] + 1, state["world_seed"], state["condition"]
    persona = world.persona_for(seed, pos, state["personas"])
    order = world.ticket_order(seed, pos)
    counts = state["counts"]
    if condition == "strong":  # stable sort: ties keep this position's random order
        order = sorted(order, key=lambda t: -_share(counts[t]))
    shown = None if condition == "independent" else {t: dict(counts[t]) for t in order}
    model_key = world.model_for_position(state["population"], pos, state["n_agents"], state["pair"])
    scripted = pos <= state["scripted_k"]
    update: dict[str, Any] = {
        "pos": pos,
        "scripted": scripted,
        "action": None,
        "failed": False,
        "turn_calls": [],
        "view": {
            "agent_id": f"a{pos}", "position": pos, "model_key": model_key, "persona": persona.model_dump(),
            "order": order, "counts": shown, "sorted": condition == "strong",
        },
    }
    if scripted:
        update["action"] = {
            "picks": [{"ticket": t, "priority": p} for t, p in world.scripted_picks(seed, pos)], "thought": None,
        }
    return update


def route_after_next(state: RunState) -> str:
    return "record" if state["scripted"] else "agent_turn"


def record(state: RunState) -> dict[str, Any]:
    """The game master: apply the agent's picks, emit the events, code `correct` and update the counts."""
    v, pos, scripted = state["view"], state["pos"], state["scripted"]
    aid = v["agent_id"]
    items: list[tuple[int, str, str | None, dict]] = [
        (pos, "AGENT_SPAWNED", aid, {"position": pos, "model": "scripted" if scripted else v["model_key"]}),
        (pos, "TICKETS_SHOWN", aid, {"order": v["order"], "counts": v["counts"]}),
    ]
    for c in state.get("turn_calls", []):
        if not c["parsed_ok"]:
            items.append((pos, "ACTION_PARSE_FAILED", aid, {
                "raw_excerpt": c["response_text"][:200], "truncated": c["finish_reason"] == "length"}))
    counts = {t: dict(c) for t, c in state["counts"].items()}
    transcripts = state["transcripts"]
    a = state.get("action")
    if a and not state.get("failed"):
        items.append((pos, "AGENT_PICKED", aid, {
            "ticket_ids": [p["ticket"] for p in a["picks"]], "thought": a["thought"], "scripted": scripted}))
        for p in a["picks"]:
            ok = is_correct(p["ticket"], p["priority"])
            items.append((pos, "AGENT_RATED", aid, {"ticket_id": p["ticket"], "priority": p["priority"], "correct": ok}))
            counts[p["ticket"]]["total"] += 1
            counts[p["ticket"]]["high"] += p["priority"] == "HIGH"
        if not scripted and pos in state["probe_set"]:
            transcripts = {**transcripts, pos: {
                "system": state["system"], "user": state["user"], "reply": state["raw"], "model_key": v["model_key"]}}
    persona = v["persona"]
    return {
        "events": _events(state, items),
        "llm_calls": state.get("turn_calls", []),
        "agents": [{"agent_id": aid, "name": persona["name"], "role": "scripted" if scripted else "agent",
                    "persona": persona}],
        "counts": counts,
        "transcripts": transcripts,
        "turn_calls": [],
        "action": None,
        "failed": False,
    }


def route_after_record(state: RunState) -> str:
    return "next_agent" if state["pos"] < state["n_agents"] else "probe"


def build_graph(ctxs: dict[str, LLMContext]):
    async def probe(state: RunState) -> dict[str, Any]:
        """Ask each sampled agent, with its own stored context, what it thinks was going on."""
        items: list[tuple[int, str, str | None, dict]] = []
        rows = []
        n = state["n_agents"]
        for pos in state["probe_set"]:
            t = state["transcripts"].get(pos)
            if t is None:  # scripted, or its decision failed: nothing to ask about
                continue
            messages = [SystemMessage(t["system"]), HumanMessage(t["user"]), AIMessage(t["reply"]),
                        HumanMessage(scenarios.PROBE_QUESTION)]
            res = await ctxs[t["model_key"]].call(messages)
            answer = res.text.strip()
            rows.append({
                "agent_id": f"a{pos}", "tick": pos, "kind": "probe", "attempt": 1,
                "prompt": render_prompt(messages), "response_text": res.text, "reasoning_text": res.reasoning_text,
                "finish_reason": res.finish_reason, "input_tokens": res.input_tokens,
                "output_tokens": res.output_tokens, "tokens_estimated": res.tokens_estimated,
                "parsed_ok": bool(answer), "latency_ms": res.latency_ms,
            })
            items.append((n, "PROBE_ANSWERED", f"a{pos}", {"text": answer, "recognized": scenarios.recognized(answer)}))
        return {"events": _events(state, items), "llm_calls": rows}

    def finish(state: RunState) -> dict[str, Any]:
        ended = _events(state, [(state["n_agents"], "RUN_ENDED", None, {"reason": "all_agents_done"})])
        bundle = {
            "run": {
                "id": run_id(state["population"], state["condition"], state["world_seed"]),
                "experiment": EXPERIMENT, "scenario": SCENARIO, "condition": state["condition"],
                "population": state["population"], "world_seed": state["world_seed"],
                "prompt_version": scenarios.PROMPT_VERSION, "engine_version": ENGINE_VERSION,
                "pilot": state["pilot"], "started_at": state["started_at"], "ended_at": _now(),
            },
            "agents": state["agents"],
            "events": state["events"] + ended,
            "llm_calls": state["llm_calls"],
        }
        return {"events": ended, "bundle": bundle}

    g = StateGraph(RunState)
    g.add_node("setup", setup)
    g.add_node("next_agent", next_agent)
    g.add_node("agent_turn", build_agent_graph(ctxs))
    g.add_node("record", record)
    g.add_node("probe", probe)
    g.add_node("finish", finish)
    g.add_edge(START, "setup")
    g.add_edge("setup", "next_agent")
    g.add_conditional_edges("next_agent", route_after_next, {"agent_turn": "agent_turn", "record": "record"})
    g.add_edge("agent_turn", "record")
    g.add_conditional_edges("record", route_after_record, {"next_agent": "next_agent", "probe": "probe"})
    g.add_edge("probe", "finish")
    g.add_edge("finish", END)
    return g.compile()


async def run_one(population: str, condition: str, world_seed: int, *, n_agents: int = N_AGENTS, pilot: bool = False,
                  budget=None, ctxs: dict[str, LLMContext] | None = None, pair: dict[str, str] | None = None) -> dict:
    """Play one world and return its RunBundle (a dict matching contracts/run-bundle.schema.json).

    `ctxs` (model key -> context) and `pair` (weaker and stronger model keys for the mixed populations) let tests
    inject models; normal callers leave them out.
    """
    pair = pair or MIX_PAIR
    if ctxs is None:
        keys = {world.model_for_position(population, p, n_agents, pair) for p in range(1, n_agents + 1)}
        ctxs = {k: LLMContext(get_model(k, run_seed=world_seed), k, budget) for k in keys}
    graph = build_graph(ctxs)
    state = await graph.ainvoke(
        {"population": population, "condition": condition, "world_seed": world_seed, "n_agents": n_agents,
         "pair": pair, "pilot": pilot, "events": [], "llm_calls": [], "agents": []},
        config={
            "recursion_limit": max(1000, 3 * n_agents + 50),
            "run_name": f"{population}|{condition}|{world_seed}",
            "metadata": {"population": population, "condition": condition, "world_seed": world_seed},
        },
    )
    return state["bundle"]
