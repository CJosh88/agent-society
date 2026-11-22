import os
import subprocess
import sys

from langchain_core.messages import HumanMessage, SystemMessage

from asl_engine import scenarios
from asl_engine.llm import FakeScriptedChatModel
from asl_engine.models import extract_action
from asl_engine.personas import load_personas

PERSONA = load_personas()[0]


def messages(scenario="office", condition="group5", tick=5):
    others = [(p.name, "cafe") for p in load_personas()[1:5]] if condition != "alone" else []
    view = {"scenario": scenario, "tick": tick, "own_location": "desk_area at (4, 4)", "visible": [],
            "heard": [], "history": [], "problem_active": tick >= 3}
    return [SystemMessage(scenarios.system_prompt(scenario, condition, PERSONA, others)),
            HumanMessage(scenarios.user_prompt(view))]


def reply(seed, **kw):
    return FakeScriptedChatModel(run_seed=seed).invoke(messages(**kw)).content


def test_same_seed_and_prompt_give_the_same_reply():
    assert reply(7) == reply(7)


def test_different_seeds_give_different_replies_somewhere():
    assert len({reply(s) for s in range(40)}) > 1


def test_independent_of_python_hash_randomisation():
    code = ("import sys; sys.path.insert(0, 'tests'); from test_fake_determinism import reply; "
            "print(''.join(reply(s) for s in range(30)))")
    outs = []
    for hashseed in ("1", "2"):
        env = {**os.environ, "PYTHONHASHSEED": hashseed}
        outs.append(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env,
                                   check=True).stdout)
    assert outs[0] == outs[1] and outs[0].strip()


def test_usage_and_finish_reason_are_reported():
    msg = FakeScriptedChatModel(run_seed=1).invoke(messages())
    assert msg.usage_metadata["input_tokens"] > 0 and msg.usage_metadata["output_tokens"] > 0
    assert msg.response_metadata["finish_reason"] == "stop"


def test_probe_answer_is_no():
    msgs = [SystemMessage("x"), HumanMessage(scenarios.PROBE_QUESTION)]
    assert FakeScriptedChatModel(run_seed=1).invoke(msgs).content == "No."


def test_help_rates_follow_the_design_and_about_five_percent_are_malformed():
    n = 600
    rates, malformed = {}, 0
    for cond in ("alone", "group5", "group5_owner"):
        helped = 0
        for s in range(n):
            out = reply(s, scenario="town_square", condition=cond)
            a = extract_action(out)
            if a is None:
                malformed += 1
            elif a.action in ("APPROACH", "CALL"):
                helped += 1
        rates[cond] = helped / n
    assert abs(rates["alone"] - 0.30 * 0.95) < 0.07
    assert abs(rates["group5"] - 0.08 * 0.95) < 0.05
    assert abs(rates["group5_owner"] - 0.25 * 0.95) < 0.07
    assert rates["alone"] > rates["group5_owner"] > rates["group5"]
    assert 0.02 < malformed / (3 * n) < 0.09


def test_no_helping_before_the_problem_starts():
    for s in range(200):
        a = extract_action(reply(s, tick=2, condition="alone"))
        assert a is None or a.action not in ("APPROACH", "CALL")
