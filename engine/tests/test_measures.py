"""Fixed ratings in, known measure values out."""

import math

import numpy as np
import pytest

from asl_engine import analysis as an
from asl_engine.analysis import Rating, World

IDS = [f"T{i:02d}" for i in range(1, 25)]  # T01-T12 serious, T13-T24 routine


def world(rows, n=4, pop="p", cond="independent", seed=0, **kw):
    """rows: (position, ticket, 'H' or 'L'); correctness comes from the truth."""
    rs = [Rating(pos, t, pr == "H", (pr == "H") == (int(t[1:]) <= 12)) for pos, t, pr in rows]
    return World(pop, cond, seed, n, rs, **kw)


def test_accuracy_counts_correct_ratings_over_a_position_range():
    w = world([(1, "T01", "H"), (1, "T13", "H"), (2, "T02", "H"), (2, "T14", "L")])
    assert an.accuracy(w) == 0.75
    assert an.accuracy(w, 2, 2) == 1.0


def test_false_and_missed_high_rates():
    w = world([(1, "T01", "L"), (1, "T02", "H"), (1, "T13", "H"), (1, "T14", "L")])
    assert an.missed_high_rate(w) == 0.5
    assert an.false_high_rate(w) == 0.5
    assert an.serious_pick_share(w) == 0.5


def test_market_shares_sum_to_one_and_follow_high_counts():
    w = world([(1, "T01", "H"), (2, "T01", "H"), (3, "T02", "H"), (4, "T13", "L")])
    s = an.market_shares(w)
    assert s.sum() == pytest.approx(1)
    assert s[0] == pytest.approx(2 / 3) and s[1] == pytest.approx(1 / 3)


def test_kl_is_zero_against_itself_and_positive_otherwise():
    a = world([(1, "T01", "H"), (2, "T01", "H")])
    b = world([(1, "T05", "H"), (2, "T05", "H")])
    assert an.kl_from_pooled(a, [a]) == pytest.approx(0)
    # smoothed shares: T01 2.5/14 against 0.5/14, T05 the reverse, so KL = (2/14) * ln 5
    assert an.kl_from_pooled(a, [b]) == pytest.approx(2 / 14 * math.log(5))


def test_unpredictability_is_zero_for_identical_worlds_and_positive_for_different():
    a = world([(1, "T01", "H")])
    assert an.unpredictability([a, a]) == 0
    b = world([(1, "T02", "H")])
    # shares differ by 1 on two of 24 tickets in every pair: mean abs difference 2/24
    assert an.unpredictability([a, b]) == pytest.approx(2 / 24)
    assert math.isnan(an.unpredictability([a]))


def test_early_mover_correlation_is_one_when_late_agents_copy_the_first_thirty():
    rows = []
    for t, hi in (("T01", "H"), ("T02", "L"), ("T03", "H"), ("T04", "L")):
        rows += [(1, t, hi), (31, t, hi)]
    w = world(rows, n=40)
    assert an.early_mover_correlation([w]) == pytest.approx(1)


def test_early_mover_correlation_is_nan_with_too_few_tickets():
    w = world([(1, "T01", "H"), (31, "T01", "H")], n=40)
    assert math.isnan(an.early_mover_correlation([w]))


def test_self_correction_is_positive_when_the_second_half_tracks_the_truth():
    first = [(1, "T01", "L"), (1, "T13", "H"), (2, "T02", "H"), (2, "T14", "H")]  # first half is mostly wrong
    second = [(3, t, "H") for t in IDS[:12]] + [(4, t, "L") for t in IDS[12:]]  # second half is perfect
    w = world(first + second, n=4)
    assert an.self_correction(w) > 0


def test_revisions_compare_with_the_independent_world_at_the_same_position_and_ticket():
    ind = world([(1, "T01", "H"), (1, "T02", "L"), (2, "T13", "L"), (2, "T14", "H")])
    now = world([(1, "T01", "L"), (1, "T02", "H"), (2, "T13", "L"), (2, "T15", "H")], cond="weak")
    harmful, beneficial = an.revisions(now, ind)
    # shared pairs: (1,T01) right then wrong; (1,T02) wrong then right; (2,T13) right then right
    assert harmful == pytest.approx(1 / 3)
    assert beneficial == pytest.approx(1 / 3)


def test_holm_matches_the_textbook_step_down_with_untested_family_members():
    adj = an.holm([0.001, 0.01, 0.04], m=8)
    assert adj == pytest.approx([0.008, 0.07, 0.24])
    assert an.holm([0.9], m=8) == [pytest.approx(1.0)]


def test_holm_is_monotone_in_the_sorted_order():
    adj = an.holm([0.04, 0.001, 0.01], m=8)
    assert adj == pytest.approx([0.24, 0.008, 0.07])


def test_bootstrap_difference_is_the_difference_of_means_with_an_interval_around_it():
    d, lo, hi = an.bootstrap_difference([0.9, 0.9, 0.8, 0.8], [0.7, 0.7, 0.6, 0.6])
    assert d == pytest.approx(0.2)
    assert lo <= d <= hi and 0.1 < lo and hi < 0.3
    assert np.isfinite([lo, hi]).all()
