"""Rendered prompts never contain a banned word, in any condition. The probe question is checked too."""

import pytest

from asl_engine import scenarios
from asl_engine.config import CONDITIONS
from asl_engine.graph import run_one
from asl_engine.personas import load_personas
from asl_engine.scenarios import BANNED_WORDS


def test_the_matcher_catches_whole_words_only():
    for w in ("experiment", "Study", "TEST", "simulation", "herding", "Fatigue", "cascade", "popularity", "majority",
              "Asch", "Latané", "Latane", "bystander", "conformity"):
        assert BANNED_WORDS.search(f"this is {w} here"), w
    for ok in ("tested", "latest", "stud", "majorities", "contest", "fatigued"):
        assert not BANNED_WORDS.search(f"this is {ok} here"), ok


def test_fixed_prompt_text_is_clean():
    for text in (scenarios.SCENE_LINE, scenarios.MENU, scenarios.SORTED_LINE, scenarios.PROBE_QUESTION,
                 scenarios.retry_line("the four tickets must be different")):
        assert BANNED_WORDS.search(text) is None, text


def test_every_persona_card_is_clean():
    assert [p.name for p in load_personas() if BANNED_WORDS.search(scenarios.persona_card(p))] == []


@pytest.mark.parametrize("condition", CONDITIONS)
async def test_every_prompt_a_world_sends_is_clean(condition):
    b = await run_one("fake", condition, 0, n_agents=20)
    bad = [c["prompt"] for c in b["llm_calls"] if BANNED_WORDS.search(c["prompt"])]
    assert bad == []
    assert any(c["kind"] == "probe" for c in b["llm_calls"])


def test_recognition_matcher_flags_naming_the_effect_and_not_plain_descriptions():
    assert scenarios.recognized("This looked like a herding experiment.")
    assert scenarios.recognized("People just follow the crowd, classic bandwagon.")
    assert not scenarios.recognized("I was sorting a support queue and rating tickets by urgency.")
