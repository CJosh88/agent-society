"""Whole runs on the fake model: invariants of the event stream, pairing across cells, determinism."""

import uuid

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from asl_engine import scenarios
from asl_engine.config import SCENARIO_CONDITIONS, SCENARIOS
from asl_engine.graph import run_id, run_one
from asl_engine.llm import LLMContext
from asl_engine.scripts import COMMENTS

CELLS = [(s, c) for s in SCENARIOS for c in SCENARIO_CONDITIONS[s]]
DECISIONS = {"AGENT_SAID", "AGENT_WAITED", "AGENT_CALLED", "AGENT_PRIORITY_SET", "ACTION_PARSE_FAILED"}
FALSE_ALARMS = {"calm": 0, "fatigue_3": 3, "fatigue_6": 6}


async def play(scenario, condition, seed):
    return await run_one("fake", scenario, condition, seed)


def check_invariants(b):
    ev, run = b["events"], b["run"]
    scenario, condition = run["scenario"], run["condition"]
    assert [e["seq"] for e in ev] == list(range(len(ev)))
    assert [e["tick"] for e in ev] == sorted(e["tick"] for e in ev)
    assert [e for e in ev if e["type"] == "RUN_ENDED"] == [ev[-1]] and ev[-1]["tick"] == 12
    ids = {a["agent_id"] for a in b["agents"]}
    assert {e["agent_id"] for e in ev if e["agent_id"]} <= ids
    assert len(ids & {"s1", "s2", "s3", "s4"}) == (4 if condition in ("dismiss", "endorse") else 0)
    assert all(a["role"] == ("focal" if a["agent_id"] == "focal" else "scripted") for a in b["agents"])

    spawns = [e for e in ev if e["type"] == "AGENT_SPAWNED"]
    assert {e["agent_id"] for e in spawns} == ids and all(e["tick"] == 0 for e in spawns)
    assert sorted(e["payload"]["seat"] for e in spawns) == list(range(len(ids)))

    notices = [e for e in ev if e["type"] == "NOTICE_SHOWN"]
    assert all(e["agent_id"] is None for e in notices)
    real = [e for e in notices if e["payload"]["real"]]
    if scenario == "alert_fatigue":
        assert [e["tick"] for e in real] == [9] and real[0]["payload"]["text"] == scenarios.REAL_ALERT
        assert len(notices) - 1 == FALSE_ALARMS[condition]
    else:
        assert [e["tick"] for e in notices] == [3] and notices[0]["payload"]["kind"] == "ticket"

    helps = [e for e in ev if e["payload"].get("counts_as_help")]
    assert len(helps) <= 1  # the focal agent stops acting once it has counted
    for e in helps:
        assert e["agent_id"] == "focal"
        if scenario == "alert_fatigue":
            assert e["type"] == "AGENT_CALLED" and e["tick"] >= 9
        else:
            assert e["type"] == "AGENT_PRIORITY_SET" and e["payload"]["priority"] == "HIGH" and e["tick"] >= 3
    focal = [e for e in ev if e["agent_id"] == "focal" and e["type"] in DECISIONS]
    if helps:
        assert max(e["tick"] for e in focal) == helps[0]["tick"]
    assert len({e["tick"] for e in focal}) == len(focal)  # at most one decision event per tick
    assert len([e for e in focal if e["type"] == "AGENT_PRIORITY_SET"]) <= 1
    for e in ev:
        if e["agent_id"] in ("s1", "s2", "s3", "s4") and e["type"] != "AGENT_SPAWNED":
            assert e["type"] == "AGENT_SAID" and e["tick"] == 3 and e["payload"]["scripted"] is True
            assert e["payload"]["thought"] is None
    if condition in ("dismiss", "endorse"):
        said = [e["payload"]["text"] for e in ev if e["agent_id"] in ("s1", "s2", "s3", "s4") and e["type"] == "AGENT_SAID"]
        assert said == list(COMMENTS[condition])

    probes = [e for e in ev if e["type"] == "PROBE_ANSWERED"]
    assert len(probes) == 1 and probes[0]["payload"]["recognized"] is False
    decision_rows = [c for c in b["llm_calls"] if c["kind"] == "decision"]
    assert {c["tick"] for c in decision_rows} == {e["tick"] for e in focal}
    assert len([c for c in b["llm_calls"] if c["kind"] == "probe"]) == 1
    assert run["id"] == run_id("fake", scenario, condition, run["seed"])
    assert run["id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, f"fake|{scenario}|{condition}|{run['seed']}|v2"))


@pytest.mark.parametrize("scenario, condition", CELLS)
async def test_invariants_hold_for_several_seeds(scenario, condition):
    for seed in range(6):
        check_invariants(await play(scenario, condition, seed))


async def test_same_run_twice_is_identical_apart_from_timing():
    a, b = await play("triage_herding", "dismiss", 3), await play("triage_herding", "dismiss", 3)
    assert a["events"] == b["events"] and a["agents"] == b["agents"]
    assert [c["prompt"] for c in a["llm_calls"]] == [c["prompt"] for c in b["llm_calls"]]
    assert [c["response_text"] for c in a["llm_calls"]] == [c["response_text"] for c in b["llm_calls"]]


async def test_paired_seed_gives_the_same_people_and_alarm_order_in_every_cell():
    bundles = {c: await play("triage_herding", c, 4) for c in SCENARIO_CONDITIONS["triage_herding"]}
    persona = {c: {a["agent_id"]: a["persona"] for a in b["agents"]} for c, b in bundles.items()}
    assert persona["alone"]["focal"] == persona["dismiss"]["focal"] == persona["endorse"]["focal"]
    assert persona["dismiss"] == persona["endorse"]

    fatigue = {c: await play("alert_fatigue", c, 4) for c in SCENARIO_CONDITIONS["alert_fatigue"]}
    texts = {c: [e["payload"]["text"] for e in b["events"] if e["type"] == "NOTICE_SHOWN" and not e["payload"]["real"]]
             for c, b in fatigue.items()}
    assert texts["fatigue_3"] == texts["fatigue_6"][:3]
    focal = [[a["persona"] for a in b["agents"] if a["agent_id"] == "focal"] for b in (*bundles.values(), *fatigue.values())]
    assert all(f == focal[0] for f in focal)


async def test_colleagues_comments_are_in_the_prompt_in_the_same_tick_and_stay_there():
    b = await play("triage_herding", "dismiss", 0)
    prompts = {c["tick"]: c["prompt"] for c in b["llm_calls"] if c["kind"] == "decision" and c["attempt"] == 1}
    assert COMMENTS["dismiss"][0] in prompts[3] and COMMENTS["dismiss"][3] in prompts[3]
    for tick, text in prompts.items():
        if tick > 3:
            assert COMMENTS["dismiss"][0] in text
    alone = await play("triage_herding", "alone", 0)
    assert "Team chat: nothing yet." in alone["llm_calls"][0]["prompt"]
    assert scenarios.ALONE_LINE in alone["llm_calls"][0]["prompt"]


async def test_notices_appear_in_the_prompt_only_from_the_tick_they_arrive():
    b = await play("alert_fatigue", "fatigue_6", 2)
    for c in b["llm_calls"]:
        if c["kind"] == "decision":
            assert (scenarios.REAL_ALERT in c["prompt"]) == (c["tick"] >= 9)
            assert c["prompt"].count(scenarios.FALSE_SUFFIX) == min(max(c["tick"] - 2, 0), 6)


class GarbageModel(BaseChatModel):
    @property
    def _llm_type(self):
        return "garbage"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        msg = AIMessage(content="I cannot answer in JSON.", response_metadata={"finish_reason": "length"})
        return ChatResult(generations=[ChatGeneration(message=msg)])


async def test_a_model_that_never_returns_json_gets_a_parse_failure_every_tick():
    ctx = LLMContext(GarbageModel(), "fake")
    b = await run_one("fake", "alert_fatigue", "calm", 0, ctx=ctx)
    failures = [e for e in b["events"] if e["type"] == "ACTION_PARSE_FAILED"]
    assert len(failures) == 12 and all(e["payload"]["truncated"] for e in failures)
    assert not [e for e in b["events"] if e["payload"].get("counts_as_help")]
    decision_rows = [c for c in b["llm_calls"] if c["kind"] == "decision"]
    assert len(decision_rows) == 24 and not any(c["parsed_ok"] for c in decision_rows)
    assert all(c["tokens_estimated"] for c in b["llm_calls"])  # no usage reported by the provider


async def rate(scenario, condition, n=40):
    helped = 0
    for s in range(n):
        bundle = await play(scenario, condition, s)
        helped += any(e["payload"].get("counts_as_help") for e in bundle["events"])
    return helped / n


async def test_outcome_rates_differ_by_condition_on_the_fake_model():
    assert await rate("alert_fatigue", "calm") > await rate("alert_fatigue", "fatigue_6")
    alone, dismiss, endorse = [await rate("triage_herding", c) for c in ("alone", "dismiss", "endorse")]
    assert alone > dismiss and endorse > dismiss
