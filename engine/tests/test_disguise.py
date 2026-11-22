"""Rendered prompts must never contain the banned words. The recognition probe question is checked too."""

import pytest

from asl_engine import scenarios
from asl_engine.config import SCENARIO_CONDITIONS, SCENARIOS
from asl_engine.personas import load_personas
from asl_engine.scripts import COMMENTS

PERSONAS = load_personas()
CELLS = [(s, c) for s in SCENARIOS for c in SCENARIO_CONDITIONS[s]]


def _view(scenario: str, tick: int) -> dict:
    notices = [(t, n["text"]) for t, n in scenarios.notice_schedule(scenario, SCENARIO_CONDITIONS[scenario][-1], [0, 1, 2, 3, 4, 5]).items() if t <= tick]
    return {
        "scenario": scenario, "tick": tick, "notices": notices,
        "chat": [("Tom Reyes", COMMENTS["dismiss"][0])] if scenario == "triage_herding" else [],
        "history": ["WAIT", 'SAY "hi"'],
    }


@pytest.mark.parametrize("scenario, condition", CELLS)
def test_no_banned_word_in_any_rendered_prompt(scenario, condition):
    others = [p.name for p in PERSONAS[1:5]] if condition in ("dismiss", "endorse") else []
    for persona in PERSONAS:
        text = scenarios.system_prompt(scenario, condition, persona, others)
        assert not scenarios.BANNED_WORDS.search(text), (persona.persona_id, scenarios.BANNED_WORDS.search(text))
    for tick in range(1, 13):
        text = scenarios.user_prompt(_view(scenario, tick)) + scenarios.retry_line("no valid JSON action found")
        assert not scenarios.BANNED_WORDS.search(text)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_fixed_text_is_clean(scenario):
    texts = [scenarios.SCENE_LINES[scenario], scenarios.action_menu(scenario), scenarios.PROBE_QUESTION,
             scenarios.probe_context(scenario), scenarios.ALONE_LINE]
    texts += [n["text"] for c in SCENARIO_CONDITIONS[scenario]
              for n in scenarios.notice_schedule(scenario, c, [0, 1, 2, 3, 4, 5]).values()]
    texts += list(scenarios.FALSE_ALERTS) + [t for cs in COMMENTS.values() for t in cs]
    for t in texts:
        assert not scenarios.BANNED_WORDS.search(t), t


def test_the_probe_question_does_not_hint_at_studies():
    assert not scenarios.BANNED_WORDS.search(scenarios.PROBE_QUESTION)
    assert "study" not in scenarios.PROBE_QUESTION.lower() and "story" not in scenarios.PROBE_QUESTION.lower()


@pytest.mark.parametrize("word", ["experiment", "Study", "TEST", "simulation", "psychology", "bystander",
                                  "Diffusion", "Darley", "Latané", "Latane", "Genovese", "Asch", "Conformity",
                                  "herd", "Herding", "fatigue"])
def test_the_pattern_catches_each_banned_word_whole(word):
    assert scenarios.BANNED_WORDS.search(f"this is a {word} here")


def test_whole_words_only():
    assert not scenarios.BANNED_WORDS.search("A student on a contested attestation, shepherding the herders' fatigued.")


def test_recognition_matching():
    assert scenarios.recognized("This resembles the Asch conformity experiment.")
    assert scenarios.recognized("It sounds like alert fatigue, the boy who cried wolf.")
    assert scenarios.recognized("A case of herding: everyone followed the group.")
    assert not scenarios.recognized("No.")
    assert not scenarios.recognized("Customers were charged twice during a provider incident.")
