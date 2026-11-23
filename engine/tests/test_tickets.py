import json
from collections import Counter

from asl_engine.config import TICKETS_PATH
from asl_engine.scenarios import BANNED_WORDS
from asl_engine.tickets import is_correct, is_serious, load_tickets, ticket_ids


def test_catalogue_is_24_balanced_tickets_with_stable_ids():
    ts = load_tickets()
    assert [t.id for t in ts] == [f"T{i:02d}" for i in range(1, 25)]
    assert Counter(t.truth for t in ts) == {"serious": 12, "routine": 12}
    assert len({t.text for t in ts}) == 24


def test_the_file_has_exactly_id_text_truth():
    rows = json.loads(TICKETS_PATH.read_text(encoding="utf-8"))
    assert all(set(r) == {"id", "text", "truth"} for r in rows)


def test_ticket_text_never_uses_a_banned_word():
    assert [t.id for t in load_tickets() if BANNED_WORDS.search(t.text)] == []


def test_correct_means_high_for_serious_and_low_for_routine():
    assert is_serious("T01") and not is_serious("T24")
    assert is_correct("T01", "HIGH") and not is_correct("T01", "LOW")
    assert is_correct("T24", "LOW") and not is_correct("T24", "HIGH")


def test_ticket_ids_is_a_fresh_list_each_time():
    ids = ticket_ids()
    ids.reverse()
    assert ticket_ids()[0] == "T01"


def test_the_replay_pages_ticket_text_matches_the_catalogue_and_carries_no_truth():
    """api/.../static/tickets.json is a text-only copy for the replay; the truth must never be served."""
    from asl_engine.config import ROOT_DIR

    path = ROOT_DIR / "api" / "src" / "main" / "resources" / "static" / "tickets.json"
    served = json.loads(path.read_text(encoding="utf-8"))
    assert served == [{"id": t.id, "text": t.text} for t in load_tickets()]
