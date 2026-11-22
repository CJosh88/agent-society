import pytest

from asl_engine.analysis import (
    build_report, fisher_greater, holm, mcnemar_greater, newcombe, run_tests, study_runs, wilson,
)


def test_wilson_matches_the_api_values_at_n_50():
    assert wilson(0, 50) == (0.0, pytest.approx(0.0713, abs=1e-4))
    lo, hi = wilson(25, 50)
    assert (lo, hi) == (pytest.approx(0.3664, abs=1e-4), pytest.approx(0.6336, abs=1e-4))
    assert wilson(50, 50) == (pytest.approx(0.9287, abs=1e-4), 1.0)


def test_newcombe_published_example():
    d, lo, hi = newcombe(56, 70, 48, 80)  # Newcombe (1998), method 10
    assert d == pytest.approx(0.2) and lo == pytest.approx(0.0524, abs=1e-3) and hi == pytest.approx(0.3339, abs=1e-3)


def test_fisher_known_p_values():
    assert fisher_greater(10, 10, 0, 10) == pytest.approx(1 / 184756)
    assert fisher_greater(3, 4, 1, 4) == pytest.approx(17 / 70)  # the tea-tasting table
    assert fisher_greater(1, 4, 3, 4) > 0.9  # the wrong direction is not significant


def test_holm_adjustment_and_order():
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm([0.5]) == [0.5]
    assert holm([0.4, 0.4]) == pytest.approx([0.8, 0.8])
    assert holm([0.3, 0.9]) == pytest.approx([0.6, 0.9])
    assert max(holm([0.2, 0.3, 0.9])) <= 1.0


def test_mcnemar_exact_one_sided():
    hi = {s: True for s in range(10)}
    lo = {s: (s >= 8) for s in range(10)}  # hi helped alone in 8 seeds, never the reverse
    b, c, p = mcnemar_greater(hi, lo)
    assert (b, c) == (8, 0) and p == pytest.approx(1 / 256)
    b, c, p = mcnemar_greater({s: s < 8 for s in range(10)}, {s: s >= 6 for s in range(10)})
    assert (b, c) == (6, 2) and p == pytest.approx(37 / 256)
    assert mcnemar_greater({0: True}, {0: True}) == (0, 0, 1.0)
    assert mcnemar_greater({0: True}, {1: False})[:2] == (0, 0)  # unpaired seeds are ignored


def run(scenario, model, condition, seed, helped, **kw):
    base = {"id": f"{scenario}{model}{condition}{seed}", "scenario": scenario, "condition": condition,
            "model": model, "seed": seed, "pilot": False, "focalHelped": helped, "earlyHelp": helped,
            "focalHelpTick": 4 if helped else None, "parseFailures": 0, "truncations": 0, "recognized": False}
    return {**base, **kw}


def cell(scenario, model, condition, helped, n=50, **kw):
    return [run(scenario, model, condition, s, s < helped, **kw) for s in range(n)]


def sample():
    runs = []
    for model in ("m1", "m2"):
        runs += cell("alert_fatigue", model, "calm", 44) + cell("alert_fatigue", model, "fatigue_6", 15)
        runs += cell("alert_fatigue", model, "fatigue_3", 30)
    return runs


def test_study_runs_drop_pilots_and_other_models():
    runs = [run("alert_fatigue", "m1", "calm", 0, True), run("alert_fatigue", "m1", "calm", 1, True, pilot=True),
            run("alert_fatigue", "fake", "calm", 2, True)]
    assert [r["seed"] for r in study_runs(runs, ["m1"])] == [0]


def test_run_tests_per_model_and_scenario_with_holm_over_all():
    rows = run_tests(sample(), ["m1", "m2"])
    assert len(rows) == 2  # alert_fatigue only: 2 models x H1
    h1 = next(r for r in rows if r["hypothesis"] == "H1" and r["model"] == "m1")
    assert (h1["x_hi"], h1["x_lo"], h1["n_hi"]) == (44, 15, 50)
    assert h1["p"] == pytest.approx(fisher_greater(44, 50, 15, 50))
    assert h1["p"] < 1e-6 and h1["p_holm"] < 0.001
    assert all(r["p_holm"] >= r["p"] for r in rows)
    assert h1["mcnemar_b"] == 29 and h1["mcnemar_c"] == 0  # seeds 15..43 escalated when calm but not after 6 false alarms


def test_tests_need_both_conditions():
    assert run_tests(cell("alert_fatigue", "m1", "calm", 30), ["m1"]) == []


def test_report_contains_cells_differences_tests_and_sensitivity():
    text = build_report(sample(), ["m1", "m2"])
    assert "### m1" in text and "### m2" in text and "## alert_fatigue" in text
    assert "| calm | 50 | 88% (76–94) |" in text
    assert "| fatigue_6 | 50 | 30% (19–44) |" in text
    assert "fatigue_6 − calm: −58 pp" in text and "fatigue_3 − calm: −28 pp" in text
    assert "## H1 (alert fatigue) and H2 (herding)" in text and "Fisher p (one-sided)" in text and "Holm p" in text
    assert "Without runs that had a parse failure or truncation (0 removed)" in text
    assert "recognised (0 removed)" in text


def test_sensitivity_sections_remove_flagged_runs():
    runs = sample()
    for r in runs[:10]:
        r["parseFailures"] = 1
    runs[60]["recognized"] = True
    text = build_report(runs, ["m1", "m2"])
    assert "parse failure or truncation (10 removed)" in text
    assert "recognised (1 removed)" in text


def test_report_is_the_same_for_the_same_data_and_never_pools_models():
    a = build_report(sample(), ["m1", "m2"], when=None)
    assert a.count("### m1") == 1
    only_m1 = build_report([r for r in sample() if r["model"] == "m1"], ["m1"])
    assert "### m2" not in only_m1


def test_h2_compares_alone_with_dismiss_and_holm_runs_over_both_scenarios():
    runs = sample() + cell("triage_herding", "m1", "alone", 45) + cell("triage_herding", "m1", "dismiss", 20)
    rows = run_tests(runs, ["m1", "m2"])
    assert [(r["scenario"], r["hypothesis"], r["hi"], r["lo"]) for r in rows] == [
        ("alert_fatigue", "H1", "calm", "fatigue_6"), ("alert_fatigue", "H1", "calm", "fatigue_6"),
        ("triage_herding", "H2", "alone", "dismiss")]
    h2 = rows[-1]
    assert (h2["x_hi"], h2["x_lo"]) == (45, 20) and h2["p_holm"] >= h2["p"]
    text = build_report(runs, ["m1", "m2"])
    assert "## triage_herding" in text and "dismiss − alone: −50 pp" in text
