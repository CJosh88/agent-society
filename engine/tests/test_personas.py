import json
from collections import Counter

from asl_engine.config import PERSONAS_PATH
from asl_engine.personas import TRAITS, load_personas, make_personas, pick_cast


def test_thirty_balanced_personas():
    ps = make_personas(42)
    assert len(ps) == 30 and len({p["name"] for p in ps}) == 30 and len({p["persona_id"] for p in ps}) == 30
    for t in TRAITS:
        assert Counter(p["big5"][t] for p in ps) == {"high": 15, "low": 15}
    assert all(22 <= p["age"] <= 68 for p in ps)
    assert Counter(p["occupation"] for p in ps).most_common(1)[0][1] == 2


def test_the_committed_file_is_exactly_make_personas_42():
    """personas.json is frozen by the prereg-v1 tag; regenerate it only on purpose."""
    assert json.loads(PERSONAS_PATH.read_text(encoding="utf-8")) == make_personas(42)


def test_cast_is_a_pure_function_of_the_seed():
    ps = load_personas()
    a, b = pick_cast(7, ps), pick_cast(7, ps)
    assert a == b
    chosen = [a["focal"].persona_id] + [p.persona_id for p in a["scripted"].values()]
    assert len(set(chosen)) == 5
    assert pick_cast(8, ps) != a
    assert len(a["spawn_draws"]) == 5 and all(0 <= d < 4 for d in a["spawn_draws"])
