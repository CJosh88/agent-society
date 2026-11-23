"""Every bundle the engine produces must satisfy contracts/run-bundle.schema.json, as must both fixtures."""

import copy
import json

import jsonschema
import pytest

from asl_engine.config import CONDITIONS, ROOT_DIR
from asl_engine.graph import run_one

SCHEMA = json.loads((ROOT_DIR / "contracts" / "run-bundle.schema.json").read_text(encoding="utf-8"))
FIXTURES = sorted((ROOT_DIR / "contracts" / "fixtures").glob("*.json"))


def validate(bundle):
    jsonschema.Draft202012Validator(SCHEMA).validate(bundle)


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_fixtures_are_valid(path):
    validate(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("condition", CONDITIONS)
async def test_engine_output_is_valid(condition):
    for seed in range(3):
        validate(await run_one("fake", condition, seed, n_agents=20))


async def test_a_mixed_world_is_valid():
    validate(await run_one("mix_late", "strong", 1, n_agents=20, pair={"weaker": "fake", "stronger": "fake"}))


async def test_a_full_size_world_is_valid():
    validate(await run_one("fake", "weak", 0))


async def test_the_schema_actually_rejects_broken_bundles():
    good = await run_one("fake", "weak", 0, n_agents=8)
    validate(good)

    def first(b, type_):
        return next(e for e in b["events"] if e["type"] == type_)

    for mutate in (
        lambda b: b["run"].update(scenario="moon"),
        lambda b: b["run"].update(condition="calm"),
        lambda b: b["run"].update(population="granite"),
        lambda b: b["run"].update(started_at="2026-11-22 10:00:00"),
        lambda b: b["run"].pop("world_seed"),
        lambda b: b["events"][-1].update(tick=201),
        lambda b: b["agents"][0].update(agent_id="a201"),
        lambda b: first(b, "AGENT_SPAWNED")["payload"].pop("position"),
        lambda b: first(b, "TICKETS_SHOWN")["payload"].update(order=first(b, "TICKETS_SHOWN")["payload"]["order"][:23]),
        lambda b: first(b, "AGENT_PICKED")["payload"].update(ticket_ids=["T01", "T01", "T02", "T03"]),
        lambda b: first(b, "AGENT_PICKED")["payload"].update(ticket_ids=["T01", "T02", "T03", "T25"]),
        lambda b: first(b, "AGENT_RATED")["payload"].update(priority="MEDIUM"),
        lambda b: b["events"].append({"seq": 99, "tick": 1, "type": "AGENT_DANCED", "agent_id": "a1", "payload": {}}),
        lambda b: b["llm_calls"][0].update(attempt=3),
        lambda b: b.update(extra=1),
    ):
        bad = copy.deepcopy(good)
        mutate(bad)
        with pytest.raises(jsonschema.ValidationError):
            validate(bad)

    mixed_seeded = copy.deepcopy(good)
    mixed_seeded["run"].update(condition="seeded_wrong", population="mix_early")
    with pytest.raises(jsonschema.ValidationError):
        validate(mixed_seeded)
