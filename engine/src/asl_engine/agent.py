"""The focal agent's turn as a compiled LangGraph subgraph: perceive -> decide -> validate, one retry."""

from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from . import scenarios
from .llm import LLMContext, render_prompt
from .models import Persona, extract_action


class TurnState(TypedDict, total=False):
    view: dict  # everything the agent perceives this tick (built by the outer graph)
    system: str
    user: str
    attempt: int
    error: str | None
    pending: dict | None  # the llm_calls row from `decide`, finished by `validate`
    raw: str
    finish: str | None
    action: dict | None
    failed: bool
    truncated: bool
    turn_calls: list  # plain list, not a reducer: a subgraph that shares a reduced key would re-add its history


def perceive(state: TurnState) -> dict[str, Any]:
    v = state["view"]
    system = scenarios.system_prompt(
        v["scenario"], v["condition"], Persona.model_validate(v["persona"]), v["others"]
    )
    return {
        "system": system,
        "user": scenarios.user_prompt(v),
        "attempt": 1,
        "error": None,
        "action": None,
        "failed": False,
        "truncated": False,
        "turn_calls": [],
    }


def semantic_error(action, view: dict) -> str | None:
    """None if the action is usable in this scenario, otherwise the message shown to the model."""
    if action.action not in view["valid_actions"]:
        return f"action {action.action!r} is not one of: {', '.join(view['valid_actions'])}"
    if action.action in ("SAY", "CALL") and not (action.text or "").strip():
        return f"{action.action} needs non-empty text"
    if action.action == "SET_PRIORITY" and action.priority is None:
        return "SET_PRIORITY needs priority set to HIGH or LOW"
    return None


def build_agent_graph(ctx: LLMContext):
    async def decide(state: TurnState) -> dict[str, Any]:
        user = state["user"]
        if state.get("error"):
            user = f"{user}\n\n{scenarios.retry_line(state['error'])}"
        messages = [SystemMessage(state["system"]), HumanMessage(user)]
        res = await ctx.call(messages)
        pending = {
            "agent_id": "focal",
            "tick": state["view"]["tick"],
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
        action = extract_action(state["raw"])
        error = "no valid JSON action found" if action is None else semantic_error(action, state["view"])
        calls = state["turn_calls"] + [{**state["pending"], "parsed_ok": error is None}]
        if error is None:
            return {"turn_calls": calls, "action": action.model_dump(), "error": None}
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
