"""The fake model is a pure function of its seed and prompt, so a world repeats exactly (apart from timestamps)."""

import copy

from asl_engine.graph import run_one
from asl_engine.llm import FakeScriptedChatModel


def strip_times(bundle):
    b = copy.deepcopy(bundle)
    b["run"].pop("started_at"), b["run"].pop("ended_at")
    for c in b["llm_calls"]:
        c.pop("latency_ms")
    return b


async def test_the_same_world_repeats_exactly():
    a = await run_one("fake", "weak", 7, n_agents=15)
    b = await run_one("fake", "weak", 7, n_agents=15)
    assert strip_times(a) == strip_times(b)


async def test_another_seed_or_condition_gives_another_world():
    a = await run_one("fake", "weak", 7, n_agents=15)
    assert strip_times(a) != strip_times(await run_one("fake", "weak", 8, n_agents=15))
    assert strip_times(a)["events"] != strip_times(await run_one("fake", "strong", 7, n_agents=15))["events"]


def test_a_reply_depends_only_on_seed_prompt_and_attempt():
    prompt = "Open tickets:\n- T01: a\n- T02: b\n- T03: c\n- T04: d\n- T05: e"
    m = FakeScriptedChatModel(run_seed=1)
    assert m._reply(prompt) == m._reply(prompt) == FakeScriptedChatModel(run_seed=1)._reply(prompt)
    assert m._reply(prompt) != FakeScriptedChatModel(run_seed=2)._reply(prompt + " ")


async def test_independent_accuracy_sits_in_a_plausible_band():
    accs = []
    for s in range(3):
        b = await run_one("fake", "independent", s, n_agents=40)
        r = [e["payload"]["correct"] for e in b["events"] if e["type"] == "AGENT_RATED"]
        accs.append(sum(r) / len(r))
    assert 0.7 < sum(accs) / 3 < 0.95
