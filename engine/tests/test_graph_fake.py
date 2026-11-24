"""The whole graph on the fake model and on scripted models: event structure, failures, probes, ids."""

import pytest
from fakes import GOOD, FnModel, ctx

from asl_engine.config import CONDITIONS
from asl_engine.graph import build_graph, run_id, run_one
from asl_engine.llm import LLMContext, get_model


def events(b, type_):
    return [e for e in b["events"] if e["type"] == type_]


@pytest.mark.parametrize("condition", CONDITIONS)
async def test_a_world_is_well_formed(condition):
    n = 20
    b = await run_one("fake", condition, 0, n_agents=n)
    ev = b["events"]
    assert [e["seq"] for e in ev] == list(range(len(ev)))
    assert ev[-1]["type"] == "RUN_ENDED" and ev[-1]["agent_id"] is None and ev[-1]["tick"] == n
    assert len(events(b, "RUN_ENDED")) == 1
    assert [a["agent_id"] for a in b["agents"]] == [f"a{p}" for p in range(1, n + 1)]
    assert len(events(b, "AGENT_SPAWNED")) == len(events(b, "TICKETS_SHOWN")) == n
    for e in ev:  # agent events carry their position as the tick; probes and the end carry the last position
        if e["type"] in ("PROBE_ANSWERED", "RUN_ENDED"):
            assert e["tick"] == n
        else:
            assert e["tick"] == int(e["agent_id"][1:])
    r = b["run"]
    assert (r["experiment"], r["scenario"], r["population"], r["condition"], r["world_seed"]) \
        == ("cascade_v1", "triage_cascade", "fake", condition, 0)


async def test_decision_calls_one_per_real_agent_and_probes_on_the_sampled_ones():
    b = await run_one("fake", "weak", 0, n_agents=30)
    decisions = [c for c in b["llm_calls"] if c["kind"] == "decision"]
    probes = [c for c in b["llm_calls"] if c["kind"] == "probe"]
    assert len(decisions) >= 30 and all(c["attempt"] in (1, 2) for c in decisions)
    assert len(probes) == len(events(b, "PROBE_ANSWERED")) <= 10
    sampled = {c["agent_id"] for c in probes}
    assert len(sampled) == len(probes)
    for c in probes:  # the probe replays the agent's own prompt and reply, then asks the plain question
        assert "what do you think was going on here" in c["prompt"] and c["parsed_ok"] is True
    assert all(e["payload"]["recognized"] is False for e in events(b, "PROBE_ANSWERED"))


async def test_probe_positions_come_from_the_seed_not_from_the_condition():
    a = await run_one("fake", "independent", 5, n_agents=30)
    b = await run_one("fake", "strong", 5, n_agents=30)
    assert {e["agent_id"] for e in events(a, "PROBE_ANSWERED")} == {e["agent_id"] for e in events(b, "PROBE_ANSWERED")}


async def test_a_recognising_probe_answer_is_flagged():
    def fn(prompt):
        if "what do you think was going on here" in prompt:
            return "This looked like a herding experiment on rating tickets.", "stop"
        return GOOD, "stop"

    b = await run_one("fake", "weak", 0, n_agents=10, ctxs={"fake": ctx(FnModel(fn=fn))})
    assert events(b, "PROBE_ANSWERED") and all(e["payload"]["recognized"] for e in events(b, "PROBE_ANSWERED"))


async def test_one_bad_reply_is_logged_and_retried_and_the_agent_still_rates():
    state = {"n": 0}

    def fn(prompt):
        state["n"] += 1
        return ("I think T01 matters.", "stop") if state["n"] == 2 else (GOOD, "stop")

    b = await run_one("fake", "weak", 0, n_agents=4, ctxs={"fake": ctx(FnModel(fn=fn))})
    failed = events(b, "ACTION_PARSE_FAILED")
    assert [(e["agent_id"], e["payload"]["raw_excerpt"]) for e in failed] == [("a2", "I think T01 matters.")]
    assert len(events(b, "AGENT_RATED")) == 16  # all four agents still rated four tickets
    a2 = [c for c in b["llm_calls"] if c["agent_id"] == "a2" and c["kind"] == "decision"]
    assert [(c["attempt"], c["parsed_ok"]) for c in a2] == [(1, False), (2, True)]


async def test_two_bad_replies_record_the_failure_with_truncation_and_no_ratings():
    def fn(prompt):
        return ('{"picks": [{"tic', "length") if "Rated HIGH by teammates so far: 1 of 1." in prompt else (GOOD, "stop")

    b = await run_one("fake", "weak", 0, n_agents=2, ctxs={"fake": ctx(FnModel(fn=fn))})
    failed = events(b, "ACTION_PARSE_FAILED")
    assert [e["agent_id"] for e in failed] == ["a2", "a2"] and failed[-1]["payload"]["truncated"] is True
    assert not [e for e in events(b, "AGENT_RATED") if e["agent_id"] == "a2"]
    assert len(b["agents"]) == 2  # the agent is still in the line


def test_run_id_is_stable_and_depends_on_every_part():
    base = run_id("llama-3.1-8b", "weak", 0)
    assert base == run_id("llama-3.1-8b", "weak", 0)
    assert len({base, run_id("gpt-oss-120b", "weak", 0), run_id("llama-3.1-8b", "strong", 0),
                run_id("llama-3.1-8b", "weak", 1)}) == 4


async def test_recursion_limit_fits_a_full_200_agent_world():
    b = await run_one("fake", "weak", 0)  # n_agents defaults to 200
    assert len(b["agents"]) == 200 and len(events(b, "AGENT_RATED")) >= 600


def test_the_graph_has_the_expected_nodes():
    g = build_graph({"fake": LLMContext(get_model("fake", run_seed=0), "fake")}).get_graph(xray=True)
    names = set(g.nodes)
    assert {"setup", "next_agent", "record", "probe", "finish"} <= names
    assert any(n.startswith("agent_turn") and "validate" in n for n in names)
