import pytest

from asl_engine.world import OFFICE, SCENES, TOWN, World, choose_spawns


def test_five_locations_and_target_position():
    for scene in SCENES.values():
        assert len(scene.locations) == 5
        assert scene.centre in scene.locations
        assert set(scene.spawn_locations) == set(scene.locations) - {scene.centre}
    assert TOWN.locations["bus_stop"] == (3, 3)
    assert OFFICE.locations["printer"] == (15, 11)


def test_slots_fill_in_order_and_free_up():
    w = World(TOWN)
    got = [w.place(f"a{i}", "cafe") for i in range(4)]
    assert [(p.x, p.y) for p in got] == [(16, 3), (17, 3), (15, 3), (16, 2)]
    w.place("a1", "bench")  # leaves the cafe, freeing slot 1
    assert (w.place("late", "cafe").x, w.place("late", "cafe").y) == (17, 3)


def test_victim_is_placed_in_town_but_the_dashboard_is_not():
    t, o = World(TOWN), World(OFFICE)
    assert (t.spawn_target().x, t.spawn_target().y) == (10, 8)
    assert o.spawn_target() is None
    assert "payments_dashboard" not in o.placements


def test_approach_problem_target_stands_at_11_8():
    for scene in (TOWN, OFFICE):
        w = World(scene)
        w.place("focal", scene.spawn_locations[0])
        w.spawn_target()
        p = w.approach("focal", scene.target_id)
        assert (p.x, p.y) == (11, 8)


def test_approach_a_person_lands_on_a_free_tile_beside_them():
    w = World(TOWN)
    w.place("focal", "bench")
    s = w.place("s1", "cafe")
    p = w.approach("focal", "s1")
    assert abs(p.x - s.x) + abs(p.y - s.y) == 1
    w.place("s2", "cafe")  # slot 1 is (17, 3), where the focal agent now stands, so s2 takes the next free tile
    others = {(q.x, q.y) for k, q in w.placements.items() if k != "focal"}
    assert (p.x, p.y) not in others
    p2 = w.approach("focal", "s1")
    assert (p2.x, p2.y) not in {(q.x, q.y) for k, q in w.placements.items() if k != "focal"}


def test_choose_spawns_is_deterministic_and_movers_do_not_spawn_at_their_destination():
    dest = {"s3": "bus_stop", "s2": "bench"}
    for draws in ([0, 0, 0, 0, 0], [3, 2, 2, 0, 1], [0, 1, 2, 0, 3]):
        a = choose_spawns(TOWN, draws, dest)
        assert a == choose_spawns(TOWN, draws, dest)
        assert a["s3"] != "bus_stop" and a["s2"] != "bench"
        assert set(a) == {"focal", "s1", "s2", "s3", "s4"}


def test_no_free_slot_raises():
    w = World(TOWN)
    for i in range(6):
        w.place(f"a{i}", "cafe")
    with pytest.raises(ValueError):
        w.place("one_too_many", "cafe")
