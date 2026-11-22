"""The outer LangGraph loop over ticks 1-12 and the deterministic game master (`resolve`)."""

from __future__ import annotations

import operator
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from . import scenarios
from .agent import TurnState, build_agent_graph
from .config import ENGINE_VERSION, EXPERIMENT, MAX_TICKS, PROBLEM_TICK
from .llm import LLMContext, get_model, render_prompt
from .personas import load_personas, pick_cast
from .scripts import destinations, scripted_actions
from .world import SCENES, World, choose_spawns

SCRIPTED_IDS = ["s1", "s2", "s3", "s4"]
HELP_WINDOW = 2  # ticks after approaching the problem target in which a SAY counts as help


class RunState(TurnState, total=False):
    # run configuration
    scenario: str
    condition: str
    seed: int
    model_key: str
    pilot: bool
    started_at: str
    # scene
    cast: dict
    world: World
    tick: int
    focal_active: bool
    scripted: list
    heard: list  # [(speaker, text)] spoken in the previous tick
    history: list  # the focal agent's own last actions, as short strings
    approach_tick: int | None  # tick of the focal agent's last APPROACH of the problem target
    # outputs; seq is assigned only in setup, tick_start, resolve, probe and finish
    events: Annotated[list, operator.add]
    llm_calls: Annotated[list, operator.add]
    bundle: dict


def run_id(model: str, scenario: str, condition: str, seed: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{model}|{scenario}|{condition}|{seed}|{scenarios.PROMPT_VERSION}"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _events(state: RunState, tick: int, items: list[tuple[str, str | None, dict]]) -> list[dict]:
    base = len(state.get("events", []))
    return [
        {"seq": base + i, "tick": tick, "type": t, "agent_id": agent, "payload": payload}
        for i, (t, agent, payload) in enumerate(items)
    ]


def _names(state: RunState) -> dict[str, str]:
    cast = state["cast"]
    names = {"focal": cast["focal"].name, "victim": scenarios.STRANGER}
    if state["condition"] != "alone":
        names.update({k: p.name for k, p in cast["scripted"].items()})
    return names


def _others(state: RunState) -> list[tuple[str, str]]:
    """(name, spawn location) of the scripted people, for the system prompt's presence line."""
    if state["condition"] == "alone":
        return []
    return [(state["cast"]["scripted"][i].name, state["cast"]["spawns"][i]) for i in SCRIPTED_IDS]


def _view(state: RunState) -> dict:
    scene = SCENES[state["scenario"]]
    world, names, tick = state["world"], _names(state), state["tick"]
    visible = []
    if state["condition"] != "alone":
        visible += [(i, names[i], world.location_of(i)) for i in SCRIPTED_IDS]
    if scene.target_is_agent:
        visible.append(("victim", scenarios.STRANGER, world.location_of("victim")))
    else:
        visible.append((scene.target_id, "the payments dashboard", f"on the {scene.centre}"))
    p = world.placements["focal"]
    return {
        "scenario": state["scenario"],
        "condition": state["condition"],
        "persona": state["cast"]["focal"].model_dump(),
        "others": _others(state),
        "tick": tick,
        "own_location": f"{p.location} at ({p.x}, {p.y})",
        "visible": visible,
        "heard": [(s, t) for s, t in state["heard"] if s != names["focal"]],
        "history": state["history"][-3:],
        "problem_active": tick >= PROBLEM_TICK,
        "valid_locations": list(scene.locations),
        "valid_targets": [v[0] for v in visible],
    }


# --- nodes ------------------------------------------------------------------------------------


def setup(state: RunState) -> dict[str, Any]:
    scenario, condition = state["scenario"], state["condition"]
    scene = SCENES[scenario]
    cast = pick_cast(state["seed"], load_personas())
    cast["spawns"] = choose_spawns(scene, cast["spawn_draws"], destinations(scenario))
    world = World(scene)
    ids = ["focal"] + (SCRIPTED_IDS if condition != "alone" else [])
    items = []
    for i in ids:
        p = world.place(i, cast["spawns"][i])
        items.append(("AGENT_SPAWNED", i, {"x": p.x, "y": p.y, "location": p.location}))
    v = world.spawn_target()
    if v is not None:
        items.append(("AGENT_SPAWNED", "victim", {"x": v.x, "y": v.y, "location": v.location}))
    return {
        "cast": cast, "world": world, "tick": 0, "focal_active": True, "heard": [], "history": [], "approach_tick": None,
        "started_at": _now(), "events": _events(state, 0, items),
    }


def tick_start(state: RunState) -> dict[str, Any]:
    tick = state["tick"] + 1
    update: dict[str, Any] = {"tick": tick}
    if tick == PROBLEM_TICK:
        scene = SCENES[state["scenario"]]
        update["events"] = _events(
            state, tick,
            [("PROBLEM_STARTED", "victim" if scene.target_is_agent else None, {
                "scenario": state["scenario"], "target_id": scene.target_id,
                "description": scenarios.PROBLEM_LINES[state["scenario"]]})],
        )
    update["view"] = _view({**state, "tick": tick})
    return update


def route_after_tick_start(state: RunState) -> str:
    return "focal_turn" if state["focal_active"] else "scripted_turns"


def scripted_turns(state: RunState) -> dict[str, Any]:
    acts = scripted_actions(state["scenario"], state["tick"]) if state["condition"] != "alone" else []
    return {"scripted": acts}


def resolve(state: RunState) -> dict[str, Any]:
    """The game master: apply the focal action first, then s1-s4; emit events and code counts_as_help."""
    scene, world, tick = SCENES[state["scenario"]], state["world"], state["tick"]
    names = _names(state)
    items: list[tuple[str, str | None, dict]] = []
    spoken: list[tuple[str, str]] = []
    history = list(state["history"])
    focal_active = state["focal_active"]
    approach_tick = state.get("approach_tick")

    if focal_active:
        if state.get("failed"):
            raw = state["raw"]
            items.append(("ACTION_PARSE_FAILED", "focal", {"raw_excerpt": raw[:200], "truncated": state["truncated"]}))
            history.append("(no usable action)")
        else:
            a = state["action"]
            thought, verb = a["thought"], a["action"]
            if verb == "WAIT":
                items.append(("AGENT_WAITED", "focal", {"thought": thought, "scripted": False}))
                history.append("WAIT")
            elif verb == "MOVE":
                prev = world.location_of("focal")
                p = world.place("focal", a["target_location"])
                items.append(("AGENT_MOVED", "focal", {
                    "from": prev, "to": p.location, "x": p.x, "y": p.y, "thought": thought, "scripted": False}))
                history.append(f"MOVE to {p.location}")
            elif verb == "SAY":
                # speaking within HELP_WINDOW ticks after approaching the problem target is what counts as help
                helps = approach_tick is not None and tick - approach_tick <= HELP_WINDOW
                items.append(("AGENT_SAID", "focal", {
                    "text": a["text"], "thought": thought, "scripted": False, "counts_as_help": helps}))
                spoken.append((names["focal"], a["text"]))
                history.append(f'SAY "{a["text"]}"')
                focal_active = focal_active and not helps
            elif verb == "APPROACH":
                p = world.approach("focal", a["target_id"])
                if tick >= PROBLEM_TICK and a["target_id"] == scene.target_id:
                    approach_tick = tick
                items.append(("AGENT_APPROACHED", "focal", {
                    "target_id": a["target_id"], "x": p.x, "y": p.y, "thought": thought, "counts_as_help": False}))
                history.append(f"APPROACH {a['target_id']}")
            elif verb == "CALL":
                helps = tick >= PROBLEM_TICK
                items.append(("AGENT_CALLED", "focal", {"text": a["text"], "thought": thought, "counts_as_help": helps}))
                history.append(f'CALL "{a["text"]}"')
                focal_active = focal_active and not helps

    for s in sorted(state["scripted"], key=lambda x: x.agent_id):  # scripted WAITs emit no event
        if s.action == "SAY":
            items.append(("AGENT_SAID", s.agent_id, {"text": s.arg, "thought": None, "scripted": True}))
            spoken.append((names[s.agent_id], s.arg))
        elif s.action == "MOVE":
            prev = world.location_of(s.agent_id)
            p = world.place(s.agent_id, s.arg)
            items.append(("AGENT_MOVED", s.agent_id, {
                "from": prev, "to": p.location, "x": p.x, "y": p.y, "thought": None, "scripted": True}))

    return {
        "events": _events(state, tick, items),
        "llm_calls": state.get("turn_calls", []),
        "turn_calls": [],
        "action": None,
        "failed": False,
        "heard": spoken,
        "history": history,
        "focal_active": focal_active,
        "approach_tick": approach_tick,
    }


def route_after_resolve(state: RunState) -> str:
    return "tick_start" if state["tick"] < MAX_TICKS else "probe"


def build_graph(ctx: LLMContext):
    async def probe(state: RunState) -> dict[str, Any]:
        system = scenarios.system_prompt(
            state["scenario"], state["condition"], state["cast"]["focal"], _others(state))
        problem = scenarios.PROBLEM_LINES[state["scenario"]]
        messages = [SystemMessage(system), HumanMessage(f"{problem}\n\n{scenarios.PROBE_QUESTION}")]
        res = await ctx.call(messages)
        answer = res.text.strip()
        row = {
            "agent_id": "focal", "tick": MAX_TICKS, "kind": "probe", "attempt": 1,
            "prompt": render_prompt(messages), "response_text": res.text, "reasoning_text": res.reasoning_text,
            "finish_reason": res.finish_reason, "input_tokens": res.input_tokens, "output_tokens": res.output_tokens,
            "tokens_estimated": res.tokens_estimated, "parsed_ok": bool(answer), "latency_ms": res.latency_ms,
        }
        ev = _events(state, MAX_TICKS, [("PROBE_ANSWERED", "focal", {
            "text": answer, "recognized": scenarios.recognized(answer)})])
        return {"events": ev, "llm_calls": [row]}

    def finish(state: RunState) -> dict[str, Any]:
        ended = _events(state, MAX_TICKS, [("RUN_ENDED", None, {"reason": "max_ticks"})])
        events = state["events"] + ended
        names = _names(state)
        cast = state["cast"]
        agents = [{"agent_id": "focal", "name": names["focal"], "role": "focal", "persona": cast["focal"].model_dump()}]
        if state["condition"] != "alone":
            agents += [{"agent_id": i, "name": names[i], "role": "scripted", "persona": cast["scripted"][i].model_dump()}
                       for i in SCRIPTED_IDS]
        if SCENES[state["scenario"]].target_is_agent:
            agents.append({"agent_id": "victim", "name": scenarios.STRANGER, "role": "victim", "persona": {}})
        bundle = {
            "run": {
                "id": run_id(state["model_key"], state["scenario"], state["condition"], state["seed"]),
                "experiment": EXPERIMENT, "scenario": state["scenario"], "condition": state["condition"],
                "model": state["model_key"], "seed": state["seed"], "prompt_version": scenarios.PROMPT_VERSION,
                "engine_version": ENGINE_VERSION, "pilot": state["pilot"],
                "started_at": state["started_at"], "ended_at": _now(),
            },
            "agents": agents,
            "events": events,
            "llm_calls": state["llm_calls"],
        }
        return {"events": ended, "bundle": bundle}

    g = StateGraph(RunState)
    g.add_node("setup", setup)
    g.add_node("tick_start", tick_start)
    g.add_node("focal_turn", build_agent_graph(ctx))
    g.add_node("scripted_turns", scripted_turns)
    g.add_node("resolve", resolve)
    g.add_node("probe", probe)
    g.add_node("finish", finish)
    g.add_edge(START, "setup")
    g.add_edge("setup", "tick_start")
    g.add_conditional_edges(
        "tick_start", route_after_tick_start, {"focal_turn": "focal_turn", "scripted_turns": "scripted_turns"})
    g.add_edge("focal_turn", "scripted_turns")
    g.add_edge("scripted_turns", "resolve")
    g.add_conditional_edges("resolve", route_after_resolve, {"tick_start": "tick_start", "probe": "probe"})
    g.add_edge("probe", "finish")
    g.add_edge("finish", END)
    return g.compile()


async def run_one(model_key: str, scenario: str, condition: str, seed: int, *, pilot: bool = False, budget=None,
                  ctx: LLMContext | None = None) -> dict:
    """Play one run and return its RunBundle (a dict matching contracts/run-bundle.schema.json).

    `ctx` lets tests inject a model; normal callers leave it out and get `get_model(model_key)`.
    """
    ctx = ctx or LLMContext(get_model(model_key, run_seed=seed), model_key, budget)
    graph = build_graph(ctx)
    state = await graph.ainvoke(
        {"scenario": scenario, "condition": condition, "seed": seed, "model_key": model_key, "pilot": pilot,
         "events": [], "llm_calls": []},
        config={
            "recursion_limit": 200,
            "run_name": f"{model_key}|{scenario}|{condition}|{seed}",
            "metadata": {"scenario": scenario, "condition": condition, "model": model_key, "seed": seed},
        },
    )
    return state["bundle"]
