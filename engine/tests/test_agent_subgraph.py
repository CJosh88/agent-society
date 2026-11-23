import pytest
from fakes import GOOD, QueueModel, ctx, picks_json

from asl_engine import world
from asl_engine.agent import build_agent_graph
from asl_engine.personas import load_personas


def view(condition="weak"):
    order = world.ticket_order(0, 1)
    counts = None if condition == "independent" else {t: {"high": 1, "total": 2} for t in order}
    return {
        "agent_id": "a1", "position": 1, "model_key": "fake", "persona": load_personas()[0].model_dump(),
        "order": order, "counts": counts, "sorted": condition == "strong",
    }


async def run(replies, condition="weak"):
    model = QueueModel(replies=replies)
    out = await build_agent_graph({"fake": ctx(model)}).ainvoke({"view": view(condition)})
    return out, model


async def test_valid_first_reply_ends_after_one_call():
    out, model = await run([(GOOD, "stop")])
    assert [p["ticket"] for p in out["action"]["picks"]] == ["T01", "T02", "T13", "T14"] and not out["failed"]
    assert len(out["turn_calls"]) == 1 and out["turn_calls"][0]["parsed_ok"] is True
    c = out["turn_calls"][0]
    assert (c["attempt"], c["kind"], c["agent_id"], c["tick"]) == (1, "decision", "a1", 1)
    assert model._i == 1


async def test_unparseable_reply_is_retried_once_with_the_error_line():
    out, model = await run([("I would pick T01!", "stop"), (GOOD, "stop")])
    assert out["action"] is not None
    calls = out["turn_calls"]
    assert [c["attempt"] for c in calls] == [1, 2] and [c["parsed_ok"] for c in calls] == [False, True]
    assert "Your reply could not be used: no valid JSON object with four picks found. " \
           "Reply with only one JSON object." in model._seen[1][1]
    assert "could not be used" not in model._seen[0][1]


async def test_two_failures_end_in_a_parse_failure():
    out, _ = await run([("nope", "stop"), ("still nope", "stop")])
    assert out["failed"] is True and out["action"] is None and out["truncated"] is False
    assert [c["parsed_ok"] for c in out["turn_calls"]] == [False, False]


async def test_truncation_is_recorded_when_the_last_reply_hit_the_length_limit():
    out, _ = await run([("nope", "stop"), ('{"picks": [{"tic', "length")])
    assert out["failed"] is True and out["truncated"] is True
    assert out["turn_calls"][1]["finish_reason"] == "length"


@pytest.mark.parametrize("bad, fragment", [
    (picks_json(("T01", "HIGH"), ("T02", "HIGH"), ("T03", "LOW")), "you must pick exactly 4 tickets, but 3 were given"),
    (picks_json(("T01", "HIGH"), ("T02", "HIGH"), ("T03", "LOW"), ("T04", "LOW"), ("T05", "LOW")),
     "you must pick exactly 4 tickets, but 5 were given"),
    (picks_json(("T01", "HIGH"), ("T01", "LOW"), ("T03", "LOW"), ("T04", "LOW")), "the four tickets must be different"),
    (picks_json(("T01", "HIGH"), ("T02", "HIGH"), ("T03", "LOW"), ("T99", "LOW")), "T99 is not a ticket on the list"),
    ('{"picks": [{"ticket": "T01", "priority": "MEDIUM"}]}', "no valid JSON object with four picks found"),
])
async def test_pick_checks_trigger_a_retry(bad, fragment):
    out, model = await run([(bad, "stop"), (GOOD, "stop")])
    assert out["action"] is not None
    assert fragment in model._seen[1][1]
    assert out["turn_calls"][0]["parsed_ok"] is False


async def test_priority_and_ticket_are_case_insensitive():
    lower = picks_json(("t01", "high"), ("t02", "low"), ("t13", "low"), ("t14", "high"))
    out, _ = await run([(lower, "stop")])
    assert [(p["ticket"], p["priority"]) for p in out["action"]["picks"]][:2] == [("T01", "HIGH"), ("T02", "LOW")]
    assert len(out["turn_calls"]) == 1


async def test_usage_is_recorded_and_the_prompt_shows_counts_only_when_given():
    out, model = await run([(GOOD, "stop")], "weak")
    c = out["turn_calls"][0]
    assert c["input_tokens"] == 100 and c["output_tokens"] == 10 and c["tokens_estimated"] is False
    assert "Rated HIGH by teammates so far: 1 of 2." in model._seen[0][1]
    out, model = await run([(GOOD, "stop")], "independent")
    assert "Rated HIGH by teammates" not in model._seen[0][1] and "sorted by" not in model._seen[0][1]
    out, model = await run([(GOOD, "stop")], "strong")
    assert "sorted by how many teammates rated each ticket HIGH so far" in model._seen[0][1]
