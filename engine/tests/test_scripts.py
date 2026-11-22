from asl_engine.config import MAX_TICKS, SCENARIOS
from asl_engine.scripts import destinations, scripted_actions
from asl_engine.world import SCENES

EXPECTED = {
    "town_square": {1: ("s1", "SAY", "Busy afternoon today."), 2: ("s3", "MOVE", "bus_stop"),
                    4: ("s2", "SAY", "Hm."), 7: ("s3", "SAY", "The bus is late again."),
                    8: ("s2", "MOVE", "bench"), 10: ("s4", "SAY", "Looks like rain later.")},
    "office": {1: ("s1", "SAY", "Anyone want coffee?"), 2: ("s3", "MOVE", "kitchen"),
               4: ("s2", "SAY", "Hm."), 7: ("s3", "SAY", "That sync meeting ran long."),
               8: ("s2", "MOVE", "meeting_room"), 10: ("s4", "SAY", "Nearly Friday.")},
}


def test_scripts_match_the_design_table():
    for scenario in SCENARIOS:
        for tick in range(1, MAX_TICKS + 1):
            acts = [(a.agent_id, a.action, a.arg) for a in scripted_actions(scenario, tick)]
            want = [EXPECTED[scenario][tick]] if tick in EXPECTED[scenario] else []
            assert acts == want, (scenario, tick)


def test_nobody_scripted_ever_approaches_or_calls():
    for scenario in SCENARIOS:
        for tick in range(0, MAX_TICKS + 1):
            assert all(a.action in ("SAY", "MOVE") for a in scripted_actions(scenario, tick))


def test_move_targets_are_real_locations_and_destinations_map():
    for scenario in SCENARIOS:
        for tick in range(1, MAX_TICKS + 1):
            for a in scripted_actions(scenario, tick):
                if a.action == "MOVE":
                    assert a.arg in SCENES[scenario].locations
    assert destinations("town_square") == {"s3": "bus_stop", "s2": "bench"}
    assert destinations("office") == {"s3": "kitchen", "s2": "meeting_room"}
