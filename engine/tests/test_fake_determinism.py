import os
import subprocess
import sys

from langchain_core.messages import HumanMessage, SystemMessage

from asl_engine import scenarios
from asl_engine.llm import FakeScriptedChatModel
from asl_engine.models import extract_action
from asl_engine.personas import load_personas
from asl_engine.scripts import COMMENTS

PERSONA = load_personas()[0]


def messages(scenario="alert_fatigue", condition="fatigue_6", tick=10):
    others = [p.name for p in load_personas()[1:5]] if condition in ("dismiss", "endorse") else []
    schedule = scenarios.notice_schedule(scenario, condition, [0, 1, 2, 3, 4, 5])
    chat = [("Tom", t) for t in COMMENTS[condition]] if tick >= 3 and condition in COMMENTS else []
    view = {"scenario": scenario, "tick": tick, "notices": [(t, n["text"]) for t, n in schedule.items() if t <= tick],
            "chat": chat, "history": []}
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


def test_call_rates_follow_the_design_and_about_five_percent_are_malformed():
    n = 600
    want = {"calm": 0.80, "fatigue_3": 0.55, "fatigue_6": 0.35}
    rates, malformed = {}, 0
    for cond in want:
        calls = 0
        for s in range(n):
            a = extract_action(reply(s, condition=cond))
            if a is None:
                malformed += 1
            elif a.action == "CALL":
                calls += 1
        rates[cond] = calls / n
        assert abs(rates[cond] - want[cond] * 0.95) < 0.07, (cond, rates[cond])
    assert rates["calm"] > rates["fatigue_3"] > rates["fatigue_6"]
    assert 0.02 < malformed / (3 * n) < 0.09


def test_high_priority_rates_follow_the_design():
    n = 800
    want = {"alone": 0.85, "dismiss": 0.30, "endorse": 0.95}
    highs = {}
    for cond in want:
        acts = [extract_action(reply(s, scenario="triage_herding", condition=cond, tick=4)) for s in range(n)]
        picked = [a for a in acts if a is not None and a.action == "SET_PRIORITY"]
        assert 0.4 < len(picked) / n < 0.55  # 0.5 per tick, less the malformed replies
        highs[cond] = sum(a.priority == "HIGH" for a in picked) / len(picked)
        assert abs(highs[cond] - want[cond]) < 0.07, (cond, highs[cond])


def test_no_calls_before_the_real_alert_beyond_the_rare_false_one():
    n = 400
    calls = sum(1 for s in range(n)
                if (a := extract_action(reply(s, condition="fatigue_6", tick=8))) is not None and a.action == "CALL")
    assert calls / n < 0.10
    assert all((a := extract_action(reply(s, condition="calm", tick=5))) is None or a.action == "WAIT"
               for s in range(200))


def test_the_fake_only_uses_verbs_on_the_menu():
    for s in range(200):
        a = extract_action(reply(s, scenario="triage_herding", condition="dismiss", tick=5))
        assert a is None or a.action in scenarios.MENU_VERBS["triage_herding"]
        b = extract_action(reply(s, scenario="alert_fatigue", condition="calm", tick=10))
        assert b is None or b.action in scenarios.MENU_VERBS["alert_fatigue"]
