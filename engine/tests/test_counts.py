"""The running HIGH counts: what each agent is shown, how `strong` sorts, and what a failed agent leaves behind."""

from fakes import GOOD, FnModel, ctx

from asl_engine.graph import run_one
from asl_engine.tickets import ticket_ids

N = 12


def by_agent(bundle, type_):
    return {e["agent_id"]: e["payload"] for e in bundle["events"] if e["type"] == type_}


def ratings(bundle):
    out = {}
    for e in bundle["events"]:
        if e["type"] == "AGENT_RATED":
            out.setdefault(e["agent_id"], []).append(e["payload"])
    return out


async def test_each_agent_is_shown_exactly_the_tally_of_the_agents_before_it():
    b = await run_one("fake", "weak", 3, n_agents=N)
    shown, rated = by_agent(b, "TICKETS_SHOWN"), ratings(b)
    tally = {t: {"high": 0, "total": 0} for t in ticket_ids()}
    for pos in range(1, N + 1):
        assert shown[f"a{pos}"]["counts"] == tally
        for r in rated.get(f"a{pos}", []):
            tally[r["ticket_id"]]["total"] += 1
            tally[r["ticket_id"]]["high"] += r["priority"] == "HIGH"
    assert sum(c["total"] for c in tally.values()) == 4 * N


async def test_independent_never_shows_counts():
    b = await run_one("fake", "independent", 3, n_agents=N)
    assert all(p["counts"] is None for p in by_agent(b, "TICKETS_SHOWN").values())
    assert all("Rated HIGH by teammates" not in c["prompt"] for c in b["llm_calls"])


async def test_strong_sorts_by_prior_high_share_with_ties_in_the_agents_own_random_order():
    weak = by_agent(await run_one("fake", "weak", 3, n_agents=N), "TICKETS_SHOWN")
    b = await run_one("fake", "strong", 3, n_agents=N)
    for aid, p in by_agent(b, "TICKETS_SHOWN").items():
        shares = [(p["counts"][t]["high"] / p["counts"][t]["total"]) if p["counts"][t]["total"] else 0 for t in p["order"]]
        assert shares == sorted(shares, reverse=True), aid
    first = by_agent(b, "TICKETS_SHOWN")["a1"]  # nothing rated yet: all tied, so the random order survives
    assert first["order"] == weak["a1"]["order"]
    assert any(by_agent(b, "TICKETS_SHOWN")[a]["order"] != weak[a]["order"] for a in weak)


async def test_every_ticket_is_listed_once_and_the_order_is_a_permutation():
    b = await run_one("fake", "strong", 4, n_agents=N)
    for p in by_agent(b, "TICKETS_SHOWN").values():
        assert sorted(p["order"]) == ticket_ids() and sorted(p["counts"]) == ticket_ids()


async def test_an_agent_whose_two_replies_fail_adds_nothing_to_the_counts():
    """Position 3's agent never answers validly; the agents after it see tallies without it."""
    def fn(prompt):
        return ("no picks here", "stop") if "Rated HIGH by teammates so far: 1 of 1." in prompt else (GOOD, "stop")

    # Every agent answers GOOD (T01 and T02 HIGH, T13 and T14 LOW); once a ticket shows "1 of 1" the next agent fails.
    b = await run_one("fake", "weak", 0, n_agents=4, ctxs={"fake": ctx(FnModel(fn=fn))})
    shown, rated = by_agent(b, "TICKETS_SHOWN"), ratings(b)
    assert "a1" in rated and "a2" not in rated  # a2 saw "1 of 1" and failed twice
    assert shown["a3"]["counts"] == shown["a2"]["counts"]  # a2 added nothing
    failed = [e for e in b["events"] if e["type"] == "ACTION_PARSE_FAILED"]
    assert {e["agent_id"] for e in failed} >= {"a2"}
    assert not [e for e in b["events"] if e["type"] == "AGENT_PICKED" and e["agent_id"] == "a2"]
