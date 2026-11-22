import pytest

from asl_engine import scenarios
from asl_engine.config import MAX_TICKS, SCENARIO_CONDITIONS, SCENARIOS
from asl_engine.scripts import COMMENTS, scripted_actions


def test_colleagues_speak_in_order_at_tick_three_in_the_group_conditions():
    for condition in ("dismiss", "endorse"):
        acts = scripted_actions("triage_herding", condition, 3)
        assert [(a.agent_id, a.text) for a in acts] == [(f"s{i}", t) for i, t in enumerate(COMMENTS[condition], 1)]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_nobody_speaks_anywhere_else(scenario):
    for condition in SCENARIO_CONDITIONS[scenario]:
        for tick in range(0, MAX_TICKS + 1):
            if scenario == "triage_herding" and condition != "alone" and tick == 3:
                continue
            assert scripted_actions(scenario, condition, tick) == []


def test_dismiss_says_low_and_endorse_says_high():
    assert all("low" in t.lower() for t in COMMENTS["dismiss"])
    assert all("high" in t.lower() for t in COMMENTS["endorse"])
    assert len(COMMENTS["dismiss"]) == len(COMMENTS["endorse"]) == 4


def test_the_alarm_schedule_by_condition():
    order = [3, 1, 4, 0, 5, 2]
    calm = scenarios.notice_schedule("alert_fatigue", "calm", order)
    three = scenarios.notice_schedule("alert_fatigue", "fatigue_3", order)
    six = scenarios.notice_schedule("alert_fatigue", "fatigue_6", order)
    assert list(calm) == [9] and list(three) == [3, 5, 7, 9] and list(six) == [3, 4, 5, 6, 7, 8, 9]
    for sched in (calm, three, six):
        assert sched[9]["real"] is True and sched[9]["text"] == scenarios.REAL_ALERT
        assert all(not n["real"] and n["text"].endswith(scenarios.FALSE_SUFFIX) for t, n in sched.items() if t != 9)
    # fatigue_3 uses the first three false alarms of fatigue_6, in the same order
    assert [three[t]["text"] for t in (3, 5, 7)] == [six[t]["text"] for t in (3, 4, 5)]
    assert six[3]["text"] == f"ALERT: {scenarios.FALSE_ALERTS[3]}{scenarios.FALSE_SUFFIX}"


def test_the_ticket_arrives_at_tick_three_in_every_condition():
    for condition in SCENARIO_CONDITIONS["triage_herding"]:
        sched = scenarios.notice_schedule("triage_herding", condition, [0, 1, 2, 3, 4, 5])
        assert list(sched) == [3] and sched[3] == {"kind": "ticket", "text": scenarios.TICKET, "real": True}
