"""The provider layer, without any network: result normalisation, retry policy and key checks."""

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from tenacity import wait_none

from asl_engine import llm
from asl_engine.llm import FakeScriptedChatModel, call_model, get_model, is_transient, to_result


class StatusError(Exception):
    def __init__(self, status):
        super().__init__(f"status {status}")
        self.status_code = status


class Flaky(BaseChatModel):
    """Raises the given errors in order, then answers."""

    errors: list
    calls: list = []

    @property
    def _llm_type(self):
        return "flaky"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(1)
        if len(self.calls) <= len(self.errors):
            raise self.errors[len(self.calls) - 1]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="ok"))])


def test_text_blocks_are_the_reply_and_thinking_is_kept_apart():
    msg = AIMessage(
        content=[{"type": "thinking", "thinking": "hmm"}, {"type": "text", "text": '{"action": "WAIT"}'}],
        usage_metadata={"input_tokens": 50, "output_tokens": 7, "total_tokens": 57},
        response_metadata={"stop_reason": "end_turn"},
    )
    r = to_result(msg, "prompt", 12)
    assert r.text == '{"action": "WAIT"}' and r.reasoning_text == "hmm"
    assert (r.input_tokens, r.output_tokens, r.tokens_estimated, r.finish_reason) == (50, 7, False, "stop")


def test_reasoning_field_from_an_openai_compatible_provider_is_saved():
    msg = AIMessage(content="answer", additional_kwargs={"reasoning_content": "step by step"},
                    response_metadata={"finish_reason": "length"})
    r = to_result(msg, "x" * 400, 5)
    assert r.reasoning_text == "step by step" and r.finish_reason == "length"


def test_missing_usage_is_estimated_from_characters():
    r = to_result(AIMessage(content="a" * 40), "p" * 400, 1)
    assert (r.input_tokens, r.output_tokens, r.tokens_estimated) == (100, 10, True)


def test_stop_reasons_are_normalised():
    for raw, want in [("stop", "stop"), ("end_turn", "stop"), ("length", "length"), ("max_tokens", "length"),
                      (None, None), ("tool_calls", "tool_calls")]:
        assert to_result(AIMessage(content="x", response_metadata={"finish_reason": raw}), "", 0).finish_reason == want


def test_which_errors_are_transient():
    assert is_transient(StatusError(429)) and is_transient(StatusError(500)) and is_transient(StatusError(503))
    assert not is_transient(StatusError(400)) and not is_transient(StatusError(401))
    assert is_transient(TimeoutError())
    assert not is_transient(ValueError("boom"))


async def test_transient_errors_are_retried_up_to_three_times(monkeypatch):
    monkeypatch.setattr(llm, "RETRY_WAIT", wait_none())
    m = Flaky(errors=[StatusError(429), StatusError(503), TimeoutError()], calls=[])
    assert (await call_model(m, [HumanMessage("hi")])).text == "ok"
    assert len(m.calls) == 4


async def test_a_fourth_transient_failure_is_raised(monkeypatch):
    monkeypatch.setattr(llm, "RETRY_WAIT", wait_none())
    m = Flaky(errors=[StatusError(500)] * 4, calls=[])
    with pytest.raises(StatusError):
        await call_model(m, [HumanMessage("hi")])
    assert len(m.calls) == 4


async def test_a_400_is_never_retried(monkeypatch):
    monkeypatch.setattr(llm, "RETRY_WAIT", wait_none())
    m = Flaky(errors=[StatusError(400)], calls=[])
    with pytest.raises(StatusError):
        await call_model(m, [HumanMessage("hi")])
    assert len(m.calls) == 1


def test_fake_needs_no_keys_and_real_models_name_what_is_missing(monkeypatch):
    assert isinstance(get_model("fake", run_seed=1), FakeScriptedChatModel)
    for var in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(RuntimeError, match="CLOUDFLARE_API_TOKEN"):
        get_model("llama-3.1-8b", run_seed=1)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_model("claude-haiku-5-5", run_seed=1)
