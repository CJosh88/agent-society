"""Small stand-in chat models for tests. No network."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

from asl_engine.llm import LLMContext, render_prompt


def result(text: str, finish: str = "stop") -> ChatResult:
    msg = AIMessage(content=text, usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
                    response_metadata={"finish_reason": finish})
    return ChatResult(generations=[ChatGeneration(message=msg)])


class QueueModel(BaseChatModel):
    """Replies with queued (text, finish_reason) pairs and remembers every prompt it saw."""

    replies: list
    _i: int = PrivateAttr(0)
    _seen: list = PrivateAttr(default_factory=list)

    @property
    def _llm_type(self):
        return "queue"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        text, finish = self.replies[self._i]
        self._i += 1
        self._seen.append([m.content for m in messages])
        return result(text, finish)


class FnModel(BaseChatModel):
    """Replies with fn(prompt) -> (text, finish_reason), so a test can decide per prompt."""

    fn: Any
    _n: int = PrivateAttr(0)

    @property
    def _llm_type(self):
        return "fn"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._n += 1
        return result(*self.fn(render_prompt(messages)))


def ctx(model: BaseChatModel, key: str = "fake") -> LLMContext:
    return LLMContext(model, key)


def picks_json(*pairs: tuple[str, str], thought: str = "ok") -> str:
    return json.dumps({"picks": [{"ticket": t, "priority": p} for t, p in pairs], "thought": thought})


GOOD = picks_json(("T01", "HIGH"), ("T02", "HIGH"), ("T13", "LOW"), ("T14", "LOW"))
