"""Whole runs on the fake model: invariants of the event stream, pairing across cells, determinism."""

import itertools
import uuid

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from asl_engine import scenarios
from asl_engine.config import CONDITIONS, SCENARIOS
from asl_engine.graph import run_id, run_one
from asl_engine.llm import LLMContext

CELLS = list(itertools.product(SCENARIOS, CONDITIONS))
DECISIONS = {"AGENT_MOVED", "AGENT_SAID", "AGENT_WAITED", "AGENT_APPROACHED", "AGENT_CALLED", "ACTION_PARSE_FAILED"}


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
    assert len(ids & {"s1", "s2", "s3", "s4"}) == (0 if condition == "alone" else 4)
    assert ("victim" in ids) == (scenario == "town_square")

    spawns = [e for e in ev if e["type"] == "AGENT_SPAWNED"]
    assert {e["agent_id"] for e in spawns} == ids and all(e["tick"] == 0 for e in spawns)
    problems = [e for e in ev if e["type"] == "PROBLEM_STARTED"]
    assert len(problems) == 1 and problems[0]["tick"] == 3
    assert problems[0]["agent_id"] == ("victim" if scenario == "town_square" else None)

    helps = [e for e in ev if e["payload"].get("counts_as_help")]
    assert all(e["agent_id"] == "focal" and e["tick"] >= 3 for e in helps)
    assert all(e["type"] in ("AGENT_APPROACHED", "AGENT_CALLED") for e in helps)
    assert len(helps) <= 1  # the focal agent stops acting after it helps
    focal = [e for e in ev if e["agent_id"] == "focal" and e["type"] in DECISIONS]
    if helps:
        assert max(e["tick"] for e in focal) == helps[0]["tick"]
    assert len({e["tick"] for e in focal}) == len(focal)  # at most one decision event per tick
    for e in ev:
        if e["agent_id"] in ("s1", "s2", "s3", "s4") and e["type"] != "AGENT_SPAWNED":
            assert e["type"] in ("AGENT_SAID", "AGENT_MOVED") and e["payload"]["scripted"] is True
            assert e["payload"]["thought"] is None

    probes = [e for e in ev if e["type"] == "PROBE_ANSWERED"]
    assert len(probes) == 1 and probes[0]["payload"]["recognized"] is False
    decision_rows = [c for c in b["llm_calls"] if c["kind"] == "decision"]
    assert {c["tick"] for c in decision_rows} == {e["tick"] for e in focal}
    assert len([c for c in b["llm_calls"] if c["kind"] == "probe"]) == 1
    assert run["id"] == run_id("fake", scenario, condition, run["seed"])
    assert run["id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, f"fake|{scenario}|{condition}|{run['seed']}|v1"))


@pytest.mark.parametrize("scenario, condition", CELLS)
async def test_invariants_hold_for_several_seeds(scenario, condition):
    for seed in range(6):
        check_invariants(await play(scenario, condition, seed))


async def test_same_run_twice_is_identical_apart_from_timing():
    a, b = await play("town_square", "group5", 3), await play("town_square", "group5", 3)
    assert a["events"] == b["events"] and a["agents"] == b["agents"]
    assert [c["prompt"] for c in a["llm_calls"]] == [c["prompt"] for c in b["llm_calls"]]
    assert [c["response_text"] for c in a["llm_calls"]] == [c["response_text"] for c in b["llm_calls"]]


async def test_paired_seed_gives_the_same_people_and_spawn_spots_in_every_cell():
    for scenario in SCENARIOS:
        bundles = {c: await play(scenario, c, 4) for c in CONDITIONS}
        spawn = {c: {e["agent_id"]: e["payload"] for e in b["events"] if e["type"] == "AGENT_SPAWNED"}
                 for c, b in bundles.items()}
        persona = {c: {a["agent_id"]: a["persona"] for a in b["agents"]} for c, b in bundles.items()}
        for c in CONDITIONS:
            assert spawn[c]["focal"] == spawn["alone"]["focal"]
            assert persona[c]["focal"] == persona["alone"]["focal"]
        assert spawn["group5"] == spawn["group5_owner"] and persona["group5"] == persona["group5_owner"]
    t = await play("town_square", "alone", 4)
    o = await play("office", "alone", 4)
    assert [a["persona"] for a in t["agents"] if a["agent_id"] == "focal"] == \
           [a["persona"] for a in o["agents"] if a["agent_id"] == "focal"]


async def test_speech_is_heard_on_the_next_tick_only():
    b = await play("town_square", "group5", 0)
    prompts = {c["tick"]: c["prompt"] for c in b["llm_calls"] if c["kind"] == "decision" and c["attempt"] == 1}
    assert "Busy afternoon today." not in prompts[1]
    if 2 in prompts:
        assert 'Heard last turn: ' in prompts[2] and "Busy afternoon today." in prompts[2]
    if 3 in prompts:
        assert "Busy afternoon today." not in prompts[3]


async def test_owner_line_appears_only_in_the_owner_condition():
    for scenario in SCENARIOS:
        for condition in CONDITIONS:
            b = await play(scenario, condition, 1)
            first = b["llm_calls"][0]["prompt"]
            assert (scenarios.OWNER_LINES[scenario] in first) == (condition == "group5_owner")
            assert (scenarios.ALONE_LINES[scenario] in first) == (condition == "alone")


async def test_the_problem_line_is_only_shown_from_tick_3():
    b = await play("office", "alone", 2)
    for c in b["llm_calls"]:
        if c["kind"] == "decision":
            assert (scenarios.PROBLEM_LINES["office"] in c["prompt"]) == (c["tick"] >= 3)


class GarbageModel(BaseChatModel):
    @property
    def _llm_type(self):
        return "garbage"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        msg = AIMessage(content="I cannot answer in JSON.", response_metadata={"finish_reason": "length"})
        return ChatResult(generations=[ChatGeneration(message=msg)])


async def test_a_model_that_never_returns_json_gets_a_parse_failure_every_tick():
    ctx = LLMContext(GarbageModel(), "fake")
    b = await run_one("fake", "office", "alone", 0, ctx=ctx)
    check_failures = [e for e in b["events"] if e["type"] == "ACTION_PARSE_FAILED"]
    assert len(check_failures) == 12 and all(e["payload"]["truncated"] for e in check_failures)
    assert not [e for e in b["events"] if e["payload"].get("counts_as_help")]
    decision_rows = [c for c in b["llm_calls"] if c["kind"] == "decision"]
    assert len(decision_rows) == 24 and not any(c["parsed_ok"] for c in decision_rows)
    # tokens are estimated when the provider reports no usage
    assert all(c["tokens_estimated"] for c in b["llm_calls"])


async def test_help_rates_differ_by_condition_on_the_fake_model():
    rates = {}
    for cond in CONDITIONS:
        helped = 0
        for seed in range(40):
            b = await play("town_square", cond, seed)
            helped += any(e["payload"].get("counts_as_help") for e in b["events"])
        rates[cond] = helped / 40
    assert rates["alone"] > rates["group5"] and rates["group5_owner"] > rates["group5"]
