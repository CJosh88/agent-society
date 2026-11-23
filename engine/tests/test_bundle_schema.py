"""Every bundle the engine produces must satisfy contracts/run-bundle.schema.json, as must both fixtures."""

import copy
import json

import jsonschema
import pytest

from asl_engine.config import ROOT_DIR, SCENARIO_CONDITIONS, SCENARIOS
from asl_engine.graph import run_one

SCHEMA = json.loads((ROOT_DIR / "contracts" / "run-bundle.schema.json").read_text(encoding="utf-8"))
FIXTURES = sorted((ROOT_DIR / "contracts" / "fixtures").glob("*.json"))
CELLS = [(s, c) for s in SCENARIOS for c in SCENARIO_CONDITIONS[s]]


def validate(bundle):
    jsonschema.Draft202012Validator(SCHEMA).validate(bundle)


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_fixtures_are_valid(path):
    validate(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("scenario, condition", CELLS)
async def test_engine_output_is_valid(scenario, condition):
    for seed in range(5):
        validate(await run_one("fake", scenario, condition, seed))


async def test_the_schema_actually_rejects_broken_bundles():
    good = await run_one("fake", "triage_herding", "dismiss", 0)
    validate(good)
    for mutate in (
        lambda b: b["run"].update(scenario="moon"),
        lambda b: b["run"].update(condition="calm"),  # a condition from the other scenario
        lambda b: b["run"].update(started_at="2026-11-22 10:00:00"),
        lambda b: b["events"][-1].update(tick=11),
        lambda b: b["events"][0]["payload"].pop("seat"),
        lambda b: b["events"].append({"seq": 99, "tick": 1, "type": "AGENT_DANCED", "agent_id": "focal", "payload": {}}),
        lambda b: b["events"].append({"seq": 99, "tick": 1, "type": "AGENT_PRIORITY_SET", "agent_id": "focal",
                                      "payload": {"priority": "MEDIUM", "thought": "", "counts_as_help": False}}),
        lambda b: b["llm_calls"][0].update(attempt=3),
        lambda b: b.update(extra=1),
    ):
        bad = copy.deepcopy(good)
        mutate(bad)
        with pytest.raises(jsonschema.ValidationError):
            validate(bad)
