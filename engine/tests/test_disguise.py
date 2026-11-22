"""Rendered prompts must never contain the banned words. Only the recognition probe is exempt."""

import pytest

from asl_engine import scenarios
from asl_engine.config import CONDITIONS, SCENARIOS
from asl_engine.personas import load_personas
from asl_engine.scripts import scripted_actions
from asl_engine.world import SCENES

PERSONAS = load_personas()


def _view(scenario: str, tick: int) -> dict:
    scene = SCENES[scenario]
    return {
        "scenario": scenario, "tick": tick, "own_location": "bench at (4, 11)",
        "visible": [("s1", "Tom Reyes", "cafe"), ("victim" if scene.target_is_agent else scene.target_id,
                                                    "a stranger", scene.centre)],
        "heard": [("Tom Reyes", "Busy afternoon today.")], "history": ["WAIT", 'SAY "hi"'],
        "problem_active": tick >= 3,
    }


@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("condition", CONDITIONS)
def test_no_banned_word_in_any_rendered_prompt(scenario, condition):
    others = [(p.name, "cafe") for p in PERSONAS[1:5]]
    for persona in PERSONAS:
        text = scenarios.system_prompt(scenario, condition, persona, others if condition != "alone" else [])
        assert not scenarios.BANNED_WORDS.search(text), (persona.persona_id, scenarios.BANNED_WORDS.search(text))
    for tick in range(1, 13):
        text = scenarios.user_prompt(_view(scenario, tick)) + scenarios.retry_line("no valid JSON action found")
        assert not scenarios.BANNED_WORDS.search(text)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_scripted_lines_and_fixed_text_are_clean(scenario):
    texts = [scenarios.SCENE_LINES[scenario], scenarios.ALONE_LINES[scenario], scenarios.OWNER_LINES[scenario],
             scenarios.PROBLEM_LINES[scenario], scenarios.action_menu(scenario)]
    texts += [a.arg for t in range(1, 13) for a in scripted_actions(scenario, t)]
    for t in texts:
        assert not scenarios.BANNED_WORDS.search(t), t


def test_the_probe_is_the_only_exempt_prompt():
    assert scenarios.BANNED_WORDS.search(scenarios.PROBE_QUESTION)


@pytest.mark.parametrize("word", ["experiment", "Study", "TEST", "simulation", "psychology", "bystander",
                                  "Diffusion", "Darley", "Latané", "Latane", "Genovese"])
def test_the_pattern_catches_each_banned_word_whole(word):
    assert scenarios.BANNED_WORDS.search(f"this is a {word} here")


def test_whole_words_only():
    assert not scenarios.BANNED_WORDS.search("A student on a contested attestation.")


def test_recognition_matching():
    assert scenarios.recognized("This resembles the Darley and Latané bystander effect.")
    assert scenarios.recognized("It sounds like a diffusion of responsibility study.")
    assert not scenarios.recognized("No.")
    assert not scenarios.recognized("It feels like an ordinary emergency in a public place.")
