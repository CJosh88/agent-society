"""All model access. Nothing else imports a provider package.

Never set temperature, top_p, top_k or seed: every model runs at its provider default.
"""

from __future__ import annotations

import hashlib
import os
import random
import re
import time
from dataclasses import dataclass

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from . import scenarios, scripts
from .budget import Budget
from .config import (
    CLIENT_MAX_RETRIES,
    CLIENT_MAX_TOKENS,
    CLIENT_TIMEOUT_S,
    MODEL_REGISTRY,
    cf_base_url,
)

# Waits 1, 4 and 16 seconds between the 3 retries. Tests replace this with wait_none().
RETRY_WAIT = wait_exponential(multiplier=1, exp_base=4)


@dataclass
class LlmResult:
    text: str
    reasoning_text: str | None
    finish_reason: str | None
    input_tokens: int
    output_tokens: int
    tokens_estimated: bool
    latency_ms: int


# --- Fake model -------------------------------------------------------------------------------

# Chance per tick that the fake model does the outcome action once it is on the table.
ESCALATE_PROBABILITY = {"calm": 0.80, "fatigue_3": 0.55, "fatigue_6": 0.35}  # a call once the real alert shows
FALSE_CALL_PROBABILITY = 0.04  # a call during the false alarms
PRIORITY_PROBABILITY = 0.5  # a priority is set on a given tick after the ticket arrives
HIGH_PROBABILITY = {"alone": 0.85, "dismiss": 0.30, "endorse": 0.95}
MALFORMED_PROBABILITY = 0.05


class FakeScriptedChatModel(BaseChatModel):
    """Deterministic stand-in so M0-M3 pass with no network. Seeded from sha256, never Python hash()."""

    run_seed: int = 0

    @property
    def _llm_type(self) -> str:
        return "fake-scripted"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        prompt = render_prompt(messages)
        text = self._reply(prompt)
        usage = {
            "input_tokens": len(prompt) // 4,
            "output_tokens": len(text) // 4,
            "total_tokens": (len(prompt) + len(text)) // 4,
        }
        msg = AIMessage(content=text, usage_metadata=usage, response_metadata={"finish_reason": "stop"})
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _reply(self, prompt: str) -> str:
        if scenarios.PROBE_QUESTION in prompt:
            return "No."
        m = re.search(r"Turn (\d+) of 12", prompt)
        tick = int(m.group(1)) if m else 0
        attempt = 2 if "Your reply could not be used" in prompt else 1
        digest = hashlib.sha256(f"{self.run_seed}|focal|{tick}|{attempt}|{prompt}".encode()).digest()
        rng = random.Random(int.from_bytes(digest[:8], "big"))

        scenario = "alert_fatigue" if scenarios.SCENE_LINES["alert_fatigue"] in prompt else "triage_herding"
        if rng.random() < MALFORMED_PROBABILITY:
            return 'Let me think about this. {"action": '

        if scenario == "alert_fatigue":
            if scenarios.REAL_ALERT in prompt:
                condition = {0: "calm", 3: "fatigue_3"}.get(prompt.count(scenarios.FALSE_SUFFIX), "fatigue_6")
                if rng.random() < ESCALATE_PROBABILITY[condition]:
                    return '{"action": "CALL", "text": "Payment provider support, card payments are failing.", "thought": "This one is still firing."}'
            elif scenarios.FALSE_SUFFIX in prompt and rng.random() < FALSE_CALL_PROBABILITY:
                return '{"action": "CALL", "text": "Manager, an alert fired, please look.", "thought": "Better safe than sorry."}'
            return '{"action": "WAIT", "thought": "Nothing needs me yet."}'

        if scenarios.ALONE_LINE in prompt:
            condition = "alone"
        else:
            condition = "dismiss" if scripts.COMMENTS["dismiss"][0] in prompt else "endorse"
        if scenarios.TICKET in prompt and rng.random() < PRIORITY_PROBABILITY:
            high = rng.random() < HIGH_PROBABILITY[condition]
            return f'{{"action": "SET_PRIORITY", "priority": "{"HIGH" if high else "LOW"}", "thought": "That is my call."}}'
        if scenarios.TICKET in prompt and rng.random() < 0.10:
            return '{"action": "SAY", "text": "Let me look at this one.", "thought": "Just making conversation."}'
        return '{"action": "WAIT", "thought": "Nothing to do right now."}'


# --- Real models ------------------------------------------------------------------------------


def get_model(key: str, *, run_seed: int) -> BaseChatModel:
    spec = MODEL_REGISTRY[key]
    if spec.provider == "fake":
        return FakeScriptedChatModel(run_seed=run_seed)
    missing = [v for v in spec.env_vars if not os.environ.get(v)]
    if missing:
        raise RuntimeError(f"{key} needs environment variable(s): {', '.join(missing)}")
    from langchain.chat_models import init_chat_model

    common = {"max_retries": CLIENT_MAX_RETRIES, "timeout": CLIENT_TIMEOUT_S, "max_tokens": CLIENT_MAX_TOKENS}
    extra = dict(spec.extra)
    if spec.provider == "workers_ai":
        return init_chat_model(
            spec.model_id, model_provider="openai", base_url=cf_base_url(),
            api_key=os.environ["CLOUDFLARE_API_TOKEN"], **common, **extra,
        )
    return init_chat_model(spec.model_id, model_provider="anthropic", **common, **extra)


def render_prompt(messages: list[BaseMessage]) -> str:
    return "\n\n".join(f"[{m.type}]\n{m.content}" for m in messages)


def _blocks(content) -> tuple[str, list[str]]:
    """Split message content into (visible text, reasoning pieces). Only text blocks count as the reply."""
    if isinstance(content, str):
        return content, []
    text, reasoning = [], []
    for b in content:
        if isinstance(b, str):
            text.append(b)
        elif b.get("type") == "text":
            text.append(b.get("text", ""))
        elif b.get("type") in ("thinking", "reasoning"):
            reasoning.append(b.get("thinking") or b.get("reasoning") or "")
    return "".join(text), reasoning


def _finish_reason(raw: str | None) -> str | None:
    if raw in ("stop", "end_turn", "stop_sequence"):
        return "stop"
    if raw in ("length", "max_tokens"):
        return "length"
    return raw


def to_result(msg: AIMessage, prompt: str, latency_ms: int) -> LlmResult:
    text, reasoning = _blocks(msg.content)
    for k in ("reasoning_content", "reasoning"):
        if msg.additional_kwargs.get(k):
            reasoning.append(str(msg.additional_kwargs[k]))
    meta = msg.response_metadata or {}
    usage = msg.usage_metadata
    if usage and usage.get("input_tokens") is not None and usage.get("output_tokens") is not None:
        tin, tout, estimated = int(usage["input_tokens"]), int(usage["output_tokens"]), False
    else:
        tin, tout, estimated = len(prompt) // 4, (len(text) + sum(map(len, reasoning))) // 4, True
    return LlmResult(
        text=text,
        reasoning_text="\n".join(reasoning) or None,
        finish_reason=_finish_reason(meta.get("finish_reason") or meta.get("stop_reason")),
        input_tokens=tin,
        output_tokens=tout,
        tokens_estimated=estimated,
        latency_ms=latency_ms,
    )


def is_transient(exc: BaseException) -> bool:
    """429, 5xx and timeouts retry. A 400 never does."""
    status = getattr(exc, "status_code", None)
    if status is not None:
        return status == 429 or status >= 500
    return isinstance(exc, (TimeoutError, httpx.TimeoutException)) or type(exc).__name__ == "APITimeoutError"


async def call_model(model: BaseChatModel, messages: list[BaseMessage]) -> LlmResult:
    prompt = render_prompt(messages)
    async for attempt in AsyncRetrying(
        retry=retry_if_exception(is_transient), stop=stop_after_attempt(4), wait=RETRY_WAIT, reraise=True
    ):
        with attempt:
            t0 = time.perf_counter()
            msg = await model.ainvoke(messages)
            return to_result(msg, prompt, int((time.perf_counter() - t0) * 1000))
    raise RuntimeError("unreachable")


@dataclass
class LLMContext:
    """A model plus the budget it reports to. The engine's only way to make a call."""

    model: BaseChatModel
    key: str
    budget: Budget | None = None

    async def call(self, messages: list[BaseMessage]) -> LlmResult:
        res = await call_model(self.model, messages)
        if self.budget is not None:
            self.budget.add(self.key, res.input_tokens, res.output_tokens)
        return res
