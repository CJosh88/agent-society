"""The pre-registered tests and the report, on small synthetic worlds."""

import zlib

import numpy as np

from asl_engine import analysis as an
from asl_engine.analysis import Rating, World

IDS = [f"T{i:02d}" for i in range(1, 25)]


def make(pop, cond, seed, acc, n=200, **kw):
    """A world whose first `n * acc` positions rate all 4 of their tickets correctly and the rest wrongly."""
    rng = np.random.default_rng(seed + zlib.crc32(f"{pop}|{cond}".encode()) % 1000)
    rs = []
    for pos in range(1, n + 1):
        right = rng.random() < acc
        for t in rng.choice(IDS, 4, replace=False):
            serious = int(t[1:]) <= 12
            high = serious if right else not serious
            rs.append(Rating(pos, str(t), bool(high), right))
    return World(pop, cond, seed, n, rs, agreeableness={p: "low" for p in range(1, n + 1)}, **kw)


def study():
    worlds = []
    for seed in range(8):
        worlds.append(make("llama-3.1-8b", "independent", seed, 0.90))
        worlds.append(make("llama-3.1-8b", "weak", seed, 0.70))
        worlds.append(make("llama-3.1-8b", "strong", seed, 0.90))
        worlds.append(make("mix_early", "weak", seed, 0.95))
        worlds.append(make("llama-3.1-8b", "seeded_wrong", seed, 0.80, scripted=set(range(1, 21))))
    return worlds


def test_h1_flags_the_condition_that_lowers_accuracy_and_not_the_one_that_does_not():
    rows = {(r.population, r.condition): r for r in an.run_tests(study()) if r.hypothesis == "H1"}
    weak, strong = rows[("llama-3.1-8b", "weak")], rows[("llama-3.1-8b", "strong")]
    assert weak.p < 0.001 and weak.p_holm < 0.05
    assert weak.difference < -0.1 and weak.high < 0  # influenced minus independent, so negative
    assert strong.p_holm > 0.05


def test_h2_compares_positions_after_the_strong_block_with_the_all_weaker_world():
    rows = [r for r in an.run_tests(study()) if r.hypothesis == "H2"]
    assert [(r.population, r.condition) for r in rows] == [("mix_early", "weak")]
    assert rows[0].difference > 0.1 and rows[0].p < 0.001


def test_a_missing_population_gives_no_rows_and_does_not_crash():
    assert an.run_tests([w for w in study() if w.population != "mix_early"])
    assert an.run_tests([]) == []


def test_sensitivity_drops_worlds_with_many_parse_failures_or_recognition():
    ws = [make("llama-3.1-8b", "independent", 0, 0.9, parse_failures=30),
          make("llama-3.1-8b", "independent", 1, 0.9, recognised=1),
          make("llama-3.1-8b", "independent", 2, 0.9)]
    parse, recog = an.sensitivity_sets(ws).values()
    assert [w.seed for w in parse] == [1, 2]
    assert [w.seed for w in recog] == [0, 2]


def test_render_has_every_section_and_one_row_per_cell():
    text = an.render(study())
    for heading in ("## World accuracy", "## H1 and H2", "## Sensitivity", "## H3", "## H4"):
        assert heading in text
    assert text.count("| llama-3.1-8b | weak | 8 |") == 1
    assert "| mix_early | weak | 8 |" in text
    assert "nan" not in text.lower().replace("n/a", "")


def test_render_of_no_worlds_still_works():
    assert "no tests could be run" in an.render([])


def test_world_from_reads_agents_events_and_run_block():
    detail = {"run": {"population": "fake", "condition": "weak", "worldSeed": 3, "parseFailures": 2,
                      "probeCount": 10, "recognisedSample": 1},
              "agents": [{"agentId": "a1", "role": "scripted", "persona": {"big5": {"A": "low"}}},
                         {"agentId": "a2", "role": "agent", "persona": {"big5": {"A": "high"}}}]}
    events = [{"type": "AGENT_RATED", "tick": 2, "payload": {"ticket_id": "T01", "priority": "HIGH", "correct": True}},
              {"type": "AGENT_PICKED", "tick": 2, "payload": {}}]
    w = an._world_from(detail, events)
    assert (w.population, w.condition, w.seed, w.n_agents) == ("fake", "weak", 3, 2)
    assert w.scripted == {1} and w.agreeableness == {1: "low", 2: "high"}
    assert w.ratings == [Rating(2, "T01", True, True)] and (w.parse_failures, w.recognised) == (2, 1)
