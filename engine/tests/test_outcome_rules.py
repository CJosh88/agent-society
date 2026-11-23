"""The game master's rules and the world seed's guarantees: coding, scripted agents, pairing, mixed lines."""

import pytest
from fakes import GOOD, FnModel, ctx

from asl_engine import world
from asl_engine.graph import run_one
from asl_engine.personas import load_personas
from asl_engine.tickets import is_correct, is_serious


def events(b, type_):
    return [e for e in b["events"] if e["type"] == type_]


def accuracy(b):
    r = events(b, "AGENT_RATED")
    return sum(e["payload"]["correct"] for e in r) / len(r)


async def test_correct_is_stored_on_every_rating_and_matches_the_truth():
    b = await run_one("fake", "weak", 1, n_agents=10)
    r = events(b, "AGENT_RATED")
    assert r and all(e["payload"]["correct"] == is_correct(e["payload"]["ticket_id"], e["payload"]["priority"]) for e in r)


async def test_each_picking_agent_rates_exactly_its_four_picks():
    b = await run_one("fake", "weak", 1, n_agents=10)
    for pick in events(b, "AGENT_PICKED"):
        rated = [e["payload"]["ticket_id"] for e in events(b, "AGENT_RATED") if e["agent_id"] == pick["agent_id"]]
        assert rated == pick["payload"]["ticket_ids"] and len(set(rated)) == 4


def test_scripted_count_is_ten_percent_capped_at_twenty():
    assert (world.scripted_count(200), world.scripted_count(20), world.scripted_count(6), world.scripted_count(1000)) \
        == (20, 2, 1, 20)


def test_scripted_picks_are_four_distinct_tickets_all_rated_against_the_truth():
    for pos in range(1, 30):
        picks = world.scripted_picks(5, pos)
        assert len({t for t, _ in picks}) == 4
        assert all(is_correct(t, p) is False for t, p in picks)
        assert all(p == ("LOW" if is_serious(t) else "HIGH") for t, p in picks)


async def test_seeded_wrong_scripts_the_first_agents_and_they_are_always_wrong():
    b = await run_one("fake", "seeded_wrong", 2, n_agents=20)
    k = world.scripted_count(20)
    roles = {a["agent_id"]: a["role"] for a in b["agents"]}
    assert [roles[f"a{p}"] for p in range(1, 21)] == ["scripted"] * k + ["agent"] * (20 - k)
    for e in events(b, "AGENT_RATED"):
        if roles[e["agent_id"]] == "scripted":
            assert e["payload"]["correct"] is False
    assert all(p["payload"]["scripted"] for p in events(b, "AGENT_PICKED") if roles[p["agent_id"]] == "scripted")
    scripted_calls = [c for c in b["llm_calls"] if roles[c["agent_id"]] == "scripted"]
    assert scripted_calls == []  # no model call for a scripted agent
    spawned = {e["agent_id"]: e["payload"]["model"] for e in events(b, "AGENT_SPAWNED")}
    assert spawned["a1"] == "scripted" and spawned[f"a{k + 1}"] == "fake"


async def test_other_conditions_have_no_scripted_agents():
    for c in ("independent", "weak", "strong"):
        b = await run_one("fake", c, 2, n_agents=20)
        assert {a["role"] for a in b["agents"]} == {"agent"}


async def test_seeded_wrong_lowers_accuracy_below_weak_with_the_fake_model():
    weak = [accuracy(await run_one("fake", "weak", s, n_agents=40)) for s in range(4)]
    seeded = [accuracy(await run_one("fake", "seeded_wrong", s, n_agents=40)) for s in range(4)]
    assert sum(seeded) / 4 < sum(weak) / 4


def test_the_world_seed_fixes_personas_and_orders_independently_of_world_size():
    ps = load_personas()
    assert [world.persona_for(7, p, ps) for p in range(1, 11)] == [world.persona_for(7, p, ps) for p in range(1, 11)]
    assert world.ticket_order(7, 3) == world.ticket_order(7, 3) != world.ticket_order(8, 3)
    assert world.ticket_order(7, 3) != world.ticket_order(7, 4)
    assert world.probe_positions(7, 200) == world.probe_positions(7, 200)
    assert len(world.probe_positions(7, 200)) == 10 and len(world.probe_positions(7, 6)) == 6


async def test_conditions_and_populations_share_each_positions_persona_and_order():
    indep = await run_one("fake", "independent", 4, n_agents=8)
    weak = await run_one("fake", "weak", 4, n_agents=8)
    assert [a["name"] for a in indep["agents"]] == [a["name"] for a in weak["agents"]]
    order = lambda b: [e["payload"]["order"] for e in events(b, "TICKETS_SHOWN")]
    assert order(indep) == order(weak)
    mixed = await run_one("mix_early", "weak", 4, n_agents=8, pair={"weaker": "fake", "stronger": "fake"})
    assert [a["name"] for a in mixed["agents"]] == [a["name"] for a in weak["agents"]]
    assert order(mixed) == order(weak)


@pytest.mark.parametrize("population, stronger_positions", [
    ("mix_early", set(range(1, 61))),
    ("mix_late", set(range(141, 201))),
    ("gpt-oss-120b", set()),
])
def test_mixed_lines_put_the_stronger_model_in_the_first_or_last_sixty(population, stronger_positions):
    pair = {"weaker": "w", "stronger": "s"}
    got = {p for p in range(1, 201) if world.model_for_position(population, p, 200, pair) == "s"}
    assert got == stronger_positions
    if population == "gpt-oss-120b":
        assert {world.model_for_position(population, p, 200) for p in range(1, 201)} == {"gpt-oss-120b"}


def test_a_small_mixed_world_keeps_the_same_share():
    pair = {"weaker": "w", "stronger": "s"}
    assert [world.model_for_position("mix_early", p, 20, pair) for p in range(1, 21)].count("s") == 6
    assert [world.model_for_position("mix_late", p, 20, pair)  for p in range(1, 21)][-6:] == ["s"] * 6


async def test_a_mixed_world_asks_the_right_model_at_each_position():
    weak_model = FnModel(fn=lambda prompt: (GOOD, "stop"))
    strong_model = FnModel(fn=lambda prompt: (GOOD, "stop"))
    ctxs = {"w": ctx(weak_model, "w"), "s": ctx(strong_model, "s")}
    b = await run_one("mix_early", "weak", 0, n_agents=10, ctxs=ctxs, pair={"weaker": "w", "stronger": "s"})
    spawned = {e["agent_id"]: e["payload"]["model"] for e in events(b, "AGENT_SPAWNED")}
    assert [spawned[f"a{p}"] for p in range(1, 11)] == ["s"] * 3 + ["w"] * 7
    assert strong_model._n >= 3 and weak_model._n >= 7  # probes reuse each agent's own model too
