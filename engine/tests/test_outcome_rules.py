"""The game master's outcome coding, driven by a scripted model that replies per tick."""

import re

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from asl_engine import scenarios
from asl_engine.graph import run_one
from asl_engine.llm import LLMContext

WAIT = '{"action": "WAIT"}'
CALL = '{"action": "CALL", "text": "Manager, something is wrong, please look."}'
SAY = '{"action": "SAY", "text": "Hmm."}'
HIGH = '{"action": "SET_PRIORITY", "priority": "HIGH"}'
LOW = '{"action": "SET_PRIORITY", "priority": "LOW"}'


class Script(BaseChatModel):
    plan: dict
    default: str = WAIT
    probe_reply: str = "Some trouble with payments."

    @property
    def _llm_type(self):
        return "script"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        text = messages[-1].content
        if scenarios.PROBE_QUESTION in text:
            reply = self.probe_reply
        else:
            reply = self.plan.get(int(re.search(r"Turn (\d+) of 12", text).group(1)), self.default)
        msg = AIMessage(content=reply, response_metadata={"finish_reason": "stop"})
        return ChatResult(generations=[ChatGeneration(message=msg)])


async def play(scenario, condition, plan, default=WAIT, **kw):
    return await run_one("fake", scenario, condition, 0, ctx=LLMContext(Script(plan=plan, default=default, **kw), "fake"))


def focal(b, *types):
    return [e for e in b["events"] if e["agent_id"] == "focal" and (not types or e["type"] in types)]


def helps(b):
    return [e for e in b["events"] if e["payload"].get("counts_as_help")]


def decision_rows(b):
    return [c for c in b["llm_calls"] if c["kind"] == "decision"]


@pytest.mark.parametrize("condition", ["calm", "fatigue_3", "fatigue_6"])
async def test_a_call_when_the_real_alert_shows_counts_and_ends_the_agent(condition):
    b = await play("alert_fatigue", condition, {9: CALL, 10: CALL, 11: CALL})
    assert [(e["tick"], e["type"]) for e in helps(b)] == [(9, "AGENT_CALLED")]
    assert len(decision_rows(b)) == 9  # inactive from tick 10 on


async def test_a_call_before_the_real_alert_is_a_false_escalation():
    b = await play("alert_fatigue", "fatigue_6", {4: CALL, 8: CALL, 10: CALL})
    calls = focal(b, "AGENT_CALLED")
    assert [(e["tick"], e["payload"]["counts_as_help"]) for e in calls] == [(4, False), (8, False), (10, True)]
    assert len(decision_rows(b)) == 10  # still active until a call counted


async def test_a_call_in_the_calm_condition_before_any_alert_does_not_count():
    b = await play("alert_fatigue", "calm", {3: CALL})
    assert helps(b) == [] and len(focal(b, "AGENT_CALLED")) == 1


async def test_waiting_through_the_real_alert_is_no_outcome():
    b = await play("alert_fatigue", "fatigue_6", {})
    assert helps(b) == [] and len(focal(b, "AGENT_WAITED")) == 12


async def test_only_the_menu_verbs_are_accepted_in_alert_fatigue():
    b = await play("alert_fatigue", "calm", {}, default=SAY)
    assert focal(b, "AGENT_SAID") == [] and len(focal(b, "ACTION_PARSE_FAILED")) == 12 and helps(b) == []


@pytest.mark.parametrize("condition", ["alone", "dismiss", "endorse"])
async def test_a_high_priority_counts_and_ends_the_agent(condition):
    b = await play("triage_herding", condition, {5: HIGH, 6: HIGH})
    assert [(e["tick"], e["type"], e["payload"]["priority"]) for e in helps(b)] == [(5, "AGENT_PRIORITY_SET", "HIGH")]
    assert len(focal(b, "AGENT_PRIORITY_SET")) == 1


async def test_a_low_priority_does_not_count_and_still_ends_the_agent():
    b = await play("triage_herding", "dismiss", {4: LOW, 6: HIGH})
    assert helps(b) == []
    assert [(e["tick"], e["payload"]["priority"]) for e in focal(b, "AGENT_PRIORITY_SET")] == [(4, "LOW")]
    assert len(decision_rows(b)) == 4


async def test_saying_something_never_counts_and_the_agent_stays_active():
    b = await play("triage_herding", "alone", {}, default=SAY)
    assert helps(b) == [] and len(focal(b, "AGENT_SAID")) == 12


async def test_call_is_not_on_the_triage_menu():
    b = await play("triage_herding", "alone", {}, default=CALL)
    assert focal(b, "AGENT_CALLED") == [] and len(focal(b, "ACTION_PARSE_FAILED")) == 12


async def test_the_outcome_tick_is_the_tick_of_the_event():
    b = await play("triage_herding", "endorse", {3: HIGH})
    assert helps(b)[0]["tick"] == 3


async def test_the_probe_is_about_the_real_alert_or_the_ticket_and_is_clean():
    for scenario, condition, needle in (("alert_fatigue", "calm", scenarios.REAL_ALERT),
                                         ("triage_herding", "dismiss", scenarios.TICKET)):
        b = await play(scenario, condition, {})
        probe = [c for c in b["llm_calls"] if c["kind"] == "probe"][0]
        assert needle in probe["prompt"] and scenarios.PROBE_QUESTION in probe["prompt"]
        assert not scenarios.BANNED_WORDS.search(probe["prompt"])


async def test_recognition_fires_only_on_volunteered_names():
    plain = await play("triage_herding", "alone", {})
    named = await play("triage_herding", "alone", {}, probe_reply="This looks like the Asch conformity experiment.")

    def flag(b):
        return [e for e in b["events"] if e["type"] == "PROBE_ANSWERED"][0]["payload"]["recognized"]

    assert flag(plain) is False and flag(named) is True
