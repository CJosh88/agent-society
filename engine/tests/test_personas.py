import json
from collections import Counter

from asl_engine.config import PERSONAS_PATH
from asl_engine.personas import TRAITS, make_personas


def test_thirty_balanced_personas():
    ps = make_personas(42)
    assert len(ps) == 30 and len({p["name"] for p in ps}) == 30 and len({p["persona_id"] for p in ps}) == 30
    for t in TRAITS:
        assert Counter(p["big5"][t] for p in ps) == {"high": 15, "low": 15}
    assert all(22 <= p["age"] <= 68 for p in ps)
    assert Counter(p["occupation"] for p in ps).most_common(1)[0][1] == 2


def test_the_committed_file_is_exactly_make_personas_42():
    """personas.json is frozen by the prereg-c1 tag; regenerate it only on purpose."""
    assert json.loads(PERSONAS_PATH.read_text(encoding="utf-8")) == make_personas(42)
