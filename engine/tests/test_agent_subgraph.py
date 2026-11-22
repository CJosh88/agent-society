import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

from asl_engine.agent import build_agent_graph
from asl_engine.llm import LLMContext
from asl_engine.personas import load_personas


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
        msg = AIMessage(content=text, usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
                        response_metadata={"finish_reason": finish})
        return ChatResult(generations=[ChatGeneration(message=msg)])


def view():
    return {
        "scenario": "town_square", "condition": "group5", "persona": load_personas()[0].model_dump(),
        "others": [(p.name, "cafe") for p in load_personas()[1:5]], "tick": 4, "own_location": "bench at (4, 11)",
        "visible": [("s1", "Tom", "cafe"), ("victim", "a stranger", "fountain")], "heard": [], "history": [],
        "problem_active": True, "valid_locations": ["bus_stop", "cafe", "fountain", "bench", "market_stall"],
        "valid_targets": ["s1", "victim"],
    }


async def run(replies):
    model = QueueModel(replies=replies)
    out = await build_agent_graph(LLMContext(model, "fake")).ainvoke({"view": view()})
    return out, model


OK = ('{"action": "APPROACH", "target_id": "victim", "thought": "go"}', "stop")


async def test_valid_first_reply_ends_after_one_call():
    out, model = await run([OK])
    assert out["action"]["action"] == "APPROACH" and not out["failed"]
    assert len(out["turn_calls"]) == 1 and out["turn_calls"][0]["parsed_ok"] is True
    assert out["turn_calls"][0]["attempt"] == 1 and out["turn_calls"][0]["kind"] == "decision"
    assert model._i == 1


async def test_unparseable_reply_is_retried_once_with_the_error_line():
    out, model = await run([("I would help!", "stop"), OK])
    assert out["action"]["action"] == "APPROACH"
    calls = out["turn_calls"]
    assert [c["attempt"] for c in calls] == [1, 2] and [c["parsed_ok"] for c in calls] == [False, True]
    assert "Your reply could not be used: no valid JSON action found. Reply with only one JSON object." \
        in model._seen[1][1]
    assert "could not be used" not in model._seen[0][1]


async def test_two_failures_end_in_a_parse_failure():
    out, _ = await run([("nope", "stop"), ("still nope", "stop")])
    assert out["failed"] is True and out["action"] is None and out["truncated"] is False
    assert [c["parsed_ok"] for c in out["turn_calls"]] == [False, False]


async def test_truncation_is_recorded_when_the_last_reply_hit_the_length_limit():
    out, _ = await run([("nope", "stop"), ('{"action": "WA', "length")])
    assert out["failed"] is True and out["truncated"] is True
    assert out["turn_calls"][1]["finish_reason"] == "length"


@pytest.mark.parametrize("bad, fragment", [
    ('{"action": "MOVE", "target_location": "moon"}', "target_location 'moon' is not one of"),
    ('{"action": "APPROACH", "target_id": "s9"}', "target_id 's9' is not in the You can see list"),
    ('{"action": "SAY"}', "SAY needs non-empty text"),
    ('{"action": "CALL", "text": "  "}', "CALL needs non-empty text"),
])
async def test_scene_checks_trigger_a_retry(bad, fragment):
    out, model = await run([(bad, "stop"), OK])
    assert out["action"]["action"] == "APPROACH"
    assert fragment in model._seen[1][1]
    assert out["turn_calls"][0]["parsed_ok"] is False


async def test_reasoning_free_reply_and_usage_are_recorded():
    out, _ = await run([OK])
    c = out["turn_calls"][0]
    assert c["input_tokens"] == 100 and c["output_tokens"] == 10 and c["tokens_estimated"] is False
    assert c["finish_reason"] == "stop" and c["reasoning_text"] is None
