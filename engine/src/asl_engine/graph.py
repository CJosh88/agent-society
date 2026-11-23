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
from .config import ENGINE_VERSION, EXPERIMENT, MAX_TICKS, ONSET_TICK
from .llm import LLMContext, get_model, render_prompt
from .personas import load_personas, pick_cast
from .scripts import scripted_actions

SCRIPTED_IDS = ["s1", "s2", "s3", "s4"]


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
    schedule: dict  # tick -> notice, from scenarios.notice_schedule
    tick: int
    focal_active: bool
    notices: list  # [(tick, text)] shown so far
    chat: list  # [(speaker, text)] said so far, in order
    history: list  # the focal agent's own last actions, as short strings
    # outputs; seq is assigned only in setup, tick_start, scripted_turns, resolve, probe and finish
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


def _has_colleagues(state: RunState) -> bool:
    return state["condition"] in ("dismiss", "endorse")


def _names(state: RunState) -> dict[str, str]:
    cast = state["cast"]
    names = {"focal": cast["focal"].name}
    if _has_colleagues(state):
        names.update({k: p.name for k, p in cast["scripted"].items()})
    return names


def _others(state: RunState) -> list[str]:
    """The scripted colleagues' names, for the system prompt's presence line."""
    return [state["cast"]["scripted"][i].name for i in SCRIPTED_IDS] if _has_colleagues(state) else []


def _view(state: RunState, tick: int, chat: list) -> dict:
    return {
        "scenario": state["scenario"],
        "condition": state["condition"],
        "persona": state["cast"]["focal"].model_dump(),
        "others": _others(state),
        "tick": tick,
        "notices": state["notices"],
        "chat": chat,
        "history": state["history"][-3:],
        "valid_actions": list(scenarios.MENU_VERBS[state["scenario"]]),
    }


# --- nodes ------------------------------------------------------------------------------------


def setup(state: RunState) -> dict[str, Any]:
    cast = pick_cast(state["seed"], load_personas())
    ids = ["focal"] + (SCRIPTED_IDS if _has_colleagues(state) else [])
    items = [("AGENT_SPAWNED", i, {"seat": seat}) for seat, i in enumerate(ids)]
    return {
        "cast": cast,
        "schedule": scenarios.notice_schedule(state["scenario"], state["condition"], cast["alarm_order"]),
        "tick": 0, "focal_active": True, "notices": [], "chat": [], "history": [],
        "started_at": _now(), "events": _events(state, 0, items),
    }


def tick_start(state: RunState) -> dict[str, Any]:
    tick = state["tick"] + 1
    notice = state["schedule"].get(tick)
    update: dict[str, Any] = {"tick": tick}
    if notice:
        update["notices"] = state["notices"] + [(tick, notice["text"])]
        update["events"] = _events(state, tick, [("NOTICE_SHOWN", None, notice)])
    return update


def scripted_turns(state: RunState) -> dict[str, Any]:
    """Colleagues speak at the start of the tick, so the focal agent sees what they said in the same tick."""
    tick, names = state["tick"], _names(state)
    chat = list(state["chat"])
    items = []
    for a in scripted_actions(state["scenario"], state["condition"], tick):
        items.append(("AGENT_SAID", a.agent_id, {"text": a.text, "thought": None, "scripted": True}))
        chat.append((names[a.agent_id], a.text))
    return {"events": _events(state, tick, items), "chat": chat, "view": _view(state, tick, chat)}


def route_after_scripted(state: RunState) -> str:
    return "focal_turn" if state["focal_active"] else "resolve"


def resolve(state: RunState) -> dict[str, Any]:
    """The game master: apply the focal action, emit its event and code counts_as_help."""
    scenario, tick = state["scenario"], state["tick"]
    items: list[tuple[str, str | None, dict]] = []
    history = list(state["history"])
    chat = list(state["chat"])
    focal_active = state["focal_active"]

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
            elif verb == "SAY":
                items.append(("AGENT_SAID", "focal", {"text": a["text"], "thought": thought, "scripted": False}))
                chat.append(("You", a["text"]))
                history.append(f'SAY "{a["text"]}"')
            elif verb == "CALL":
                # a call before the real alert is a false escalation: logged, not counted, and the agent stays active
                helps = scenario == "alert_fatigue" and tick >= ONSET_TICK[scenario]
                items.append(("AGENT_CALLED", "focal", {"text": a["text"], "thought": thought, "counts_as_help": helps}))
                history.append(f'CALL "{a["text"]}"')
                focal_active = not helps
            elif verb == "SET_PRIORITY":
                items.append(("AGENT_PRIORITY_SET", "focal", {
                    "priority": a["priority"], "thought": thought, "counts_as_help": a["priority"] == "HIGH"}))
                history.append(f"SET_PRIORITY {a['priority']}")
                focal_active = False  # a priority, once set, is the agent's answer

    return {
        "events": _events(state, tick, items),
        "llm_calls": state.get("turn_calls", []),
        "turn_calls": [],
        "action": None,
        "failed": False,
        "chat": chat,
        "history": history,
        "focal_active": focal_active,
    }


def route_after_resolve(state: RunState) -> str:
    return "tick_start" if state["tick"] < MAX_TICKS else "probe"


def build_graph(ctx: LLMContext):
    async def probe(state: RunState) -> dict[str, Any]:
        system = scenarios.system_prompt(state["scenario"], state["condition"], state["cast"]["focal"], _others(state))
        problem = scenarios.probe_context(state["scenario"])
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
        if _has_colleagues(state):
            agents += [{"agent_id": i, "name": names[i], "role": "scripted", "persona": cast["scripted"][i].model_dump()}
                       for i in SCRIPTED_IDS]
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
    g.add_node("scripted_turns", scripted_turns)
    g.add_node("focal_turn", build_agent_graph(ctx))
    g.add_node("resolve", resolve)
    g.add_node("probe", probe)
    g.add_node("finish", finish)
    g.add_edge(START, "setup")
    g.add_edge("setup", "tick_start")
    g.add_edge("tick_start", "scripted_turns")
    g.add_conditional_edges("scripted_turns", route_after_scripted, {"focal_turn": "focal_turn", "resolve": "resolve"})
    g.add_edge("focal_turn", "resolve")
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
