"""One agent's turn as a compiled LangGraph subgraph: perceive -> decide -> validate, one retry."""

from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from . import scenarios
from .config import PICKS
from .llm import LLMContext, render_prompt
from .models import AgentPicks, Persona, extract_picks
from .tickets import ticket_ids


class TurnState(TypedDict, total=False):
    view: dict  # everything this agent perceives (built by the outer graph)
    system: str
    user: str
    attempt: int
    error: str | None
    pending: dict | None  # the llm_calls row from `decide`, finished by `validate`
    raw: str
    finish: str | None
    action: dict | None  # the validated AgentPicks as a dict
    failed: bool
    truncated: bool
    turn_calls: list  # plain list, not a reducer: a subgraph that shares a reduced key would re-add its history


def perceive(state: TurnState) -> dict[str, Any]:
    v = state["view"]
    return {
        "system": scenarios.system_prompt(Persona.model_validate(v["persona"])),
        "user": scenarios.user_prompt(v),
        "attempt": 1,
        "error": None,
        "action": None,
        "failed": False,
        "truncated": False,
        "turn_calls": [],
    }


def semantic_error(picks: AgentPicks) -> str | None:
    """None if the picks are usable, otherwise the message shown to the model on the retry."""
    if len(picks.picks) != PICKS:
        return f"you must pick exactly {PICKS} tickets, but {len(picks.picks)} were given"
    tickets = [p.ticket for p in picks.picks]
    if len(set(tickets)) != PICKS:
        return "the four tickets must be different"
    unknown = [t for t in tickets if t not in ticket_ids()]
    if unknown:
        return f"{', '.join(unknown)} is not a ticket on the list"
    return None


def build_agent_graph(ctxs: dict[str, LLMContext]):
    """`ctxs` maps a model key to its context; the turn uses the one named in its view."""

    async def decide(state: TurnState) -> dict[str, Any]:
        view = state["view"]
        user = state["user"]
        if state.get("error"):
            user = f"{user}\n\n{scenarios.retry_line(state['error'])}"
        messages = [SystemMessage(state["system"]), HumanMessage(user)]
        res = await ctxs[view["model_key"]].call(messages)
        pending = {
            "agent_id": view["agent_id"],
            "tick": view["position"],
            "kind": "decision",
            "attempt": state["attempt"],
            "prompt": render_prompt(messages),
            "response_text": res.text,
            "reasoning_text": res.reasoning_text,
            "finish_reason": res.finish_reason,
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "tokens_estimated": res.tokens_estimated,
            "latency_ms": res.latency_ms,
        }
        return {"pending": pending, "raw": res.text, "finish": res.finish_reason}

    def validate(state: TurnState) -> dict[str, Any]:
        picks = extract_picks(state["raw"])
        error = "no valid JSON object with four picks found" if picks is None else semantic_error(picks)
        calls = state["turn_calls"] + [{**state["pending"], "parsed_ok": error is None}]
        if error is None:
            return {"turn_calls": calls, "action": picks.model_dump(), "error": None}
        if state["attempt"] == 1:
            return {"turn_calls": calls, "error": error, "attempt": 2}
        return {"turn_calls": calls, "failed": True, "error": error, "truncated": state["finish"] == "length"}

    def route(state: TurnState) -> str:
        return END if state.get("action") or state.get("failed") else "decide"

    g = StateGraph(TurnState)
    g.add_node("perceive", perceive)
    g.add_node("decide", decide)
    g.add_node("validate", validate)
    g.add_edge(START, "perceive")
    g.add_edge("perceive", "decide")
    g.add_edge("decide", "validate")
    g.add_conditional_edges("validate", route, {END: END, "decide": "decide"})
    return g.compile()
