"""Analysis plan: per model and scenario, never pooled. Writes results/results.md.

Rates carry 95% Wilson intervals, differences 95% Newcombe intervals. H1 and H2 use one-sided Fisher exact
tests (the condition expected to be higher goes first) with Holm correction, and exact one-sided McNemar tests
on the paired seeds as a secondary check. H3 and H4 are descriptive only.
"""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone

import httpx
from scipy.stats import binomtest, fisher_exact

from .config import SCENARIO_CONDITIONS, SCENARIOS, api_url

Z = 1.959963984540054
# scenario -> (hypothesis, condition expected to be higher, condition expected to be lower)
HYPOTHESES = {"alert_fatigue": ("H1", "calm", "fatigue_6"), "triage_herding": ("H2", "alone", "dismiss")}


# --- statistics -------------------------------------------------------------------------------


def wilson(x: int, n: int) -> tuple[float, float]:
    p = x / n
    z2 = Z * Z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = Z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return (0.0 if x == 0 else max(0.0, centre - half), 1.0 if x == n else min(1.0, centre + half))


def newcombe(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float, float]:
    """p1 - p2 with its 95% hybrid-score interval (Newcombe method 10)."""
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    d = p1 - p2
    return d, max(-1.0, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)), min(1.0, d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def fisher_greater(x_hi: int, n_hi: int, x_lo: int, n_lo: int) -> float:
    """One-sided Fisher exact test that the first group's rate is higher: table [[helped, not], [helped, not]]."""
    return float(fisher_exact([[x_hi, n_hi - x_hi], [x_lo, n_lo - x_lo]], alternative="greater").pvalue)


def holm(pvalues: list[float]) -> list[float]:
    """Holm-adjusted p-values, in the input order."""
    m = len(pvalues)
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(sorted(range(m), key=lambda k: pvalues[k])):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def mcnemar_greater(hi: dict[int, bool], lo: dict[int, bool]) -> tuple[int, int, float]:
    """Exact one-sided McNemar on seeds present in both conditions: (b, c, p). b = hi helped and lo did not."""
    seeds = hi.keys() & lo.keys()
    b = sum(1 for s in seeds if hi[s] and not lo[s])
    c = sum(1 for s in seeds if lo[s] and not hi[s])
    return b, c, 1.0 if b + c == 0 else float(binomtest(b, b + c, 0.5, alternative="greater").pvalue)


# --- data -------------------------------------------------------------------------------------


def fetch_runs(base: str | None = None) -> list[dict]:
    """All run summaries from GET /api/runs, 100 per page."""
    base = base or api_url()
    runs, page = [], 0
    with httpx.Client(timeout=30) as client:
        while True:
            r = client.get(f"{base}/api/runs", params={"page": page, "size": 100})
            r.raise_for_status()
            data = r.json()
            runs += data["content"]
            page += 1
            if page >= data["page"]["totalPages"]:
                return runs


def study_runs(runs: list[dict], models: list[str]) -> list[dict]:
    """Pilots and models outside the study list are excluded."""
    return [r for r in runs if not r["pilot"] and r["model"] in models]


def _cell(runs: list[dict], scenario: str, model: str, condition: str) -> list[dict]:
    return [r for r in runs if r["scenario"] == scenario and r["model"] == model and r["condition"] == condition]


def _helped(cell: list[dict]) -> int:
    return sum(r["focalHelped"] for r in cell)


# --- tests ------------------------------------------------------------------------------------


def run_tests(runs: list[dict], models: list[str]) -> list[dict]:
    """H1 and H2 for every scenario and model that has both conditions, with Holm over all of them."""
    rows = []
    for scenario in SCENARIOS:
        name, hi, lo = HYPOTHESES[scenario]
        for model in models:
            a, b = _cell(runs, scenario, model, hi), _cell(runs, scenario, model, lo)
            if not a or not b:
                continue
            mc_b, mc_c, mc_p = mcnemar_greater({r["seed"]: r["focalHelped"] for r in a},
                                               {r["seed"]: r["focalHelped"] for r in b})
            rows.append({
                "scenario": scenario, "model": model, "hypothesis": name, "hi": hi, "lo": lo,
                "x_hi": _helped(a), "n_hi": len(a), "x_lo": _helped(b), "n_lo": len(b),
                "p": fisher_greater(_helped(a), len(a), _helped(b), len(b)),
                "mcnemar_b": mc_b, "mcnemar_c": mc_c, "mcnemar_p": mc_p,
            })
    for row, adj in zip(rows, holm([r["p"] for r in rows])):
        row["p_holm"] = adj
    return rows


# --- markdown ---------------------------------------------------------------------------------


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def _rate(x: int, n: int) -> str:
    lo, hi = wilson(x, n)
    return f"{_pct(x / n)} ({round(lo * 100)}–{round(hi * 100)})"


def _pp(x: float) -> str:
    return f"{'−' if x < 0 else '+'}{abs(round(x * 100))}"


def _p(x: float) -> str:
    return "<0.001" if x < 0.001 else f"{x:.3f}"


def _tests_table(rows: list[dict]) -> list[str]:
    if not rows:
        return ["No scenario and model has both conditions yet.", ""]
    out = ["| Scenario | Model | Test | Higher expected | Lower expected | Fisher p (one-sided) | Holm p | McNemar b / c | McNemar p |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        out.append(f"| {r['scenario']} | {r['model']} | {r['hypothesis']} | {r['hi']} {r['x_hi']}/{r['n_hi']} | "
                   f"{r['lo']} {r['x_lo']}/{r['n_lo']} | {_p(r['p'])} | {_p(r['p_holm'])} | "
                   f"{r['mcnemar_b']} / {r['mcnemar_c']} | {_p(r['mcnemar_p'])} |")
    return out + [""]


def build_report(runs: list[dict], models: list[str], when: datetime | None = None) -> str:
    runs = study_runs(runs, models)
    when = when or datetime.now(timezone.utc)
    out = ["# Results", "",
           f"Generated {when.strftime('%Y-%m-%d %H:%M')} UTC from {len(runs)} study runs "
           f"(pilots excluded; models: {', '.join(models)}). Models are analysed separately, never pooled.", ""]

    for scenario in SCENARIOS:
        out += [f"## {scenario}", ""]
        for model in models:
            conditions = SCENARIO_CONDITIONS[scenario]
            cells = {c: _cell(runs, scenario, model, c) for c in conditions}
            if not any(cells.values()):
                continue
            out += [f"### {model}", "",
                    "| Condition | n | Outcome (95% Wilson) | Within 2 ticks of onset | Median outcome tick | "
                    "Runs with a parse failure | Runs with a truncation | Recognised |",
                    "| --- | --- | --- | --- | --- | --- | --- | --- |"]
            for c, cell in cells.items():
                if not cell:
                    continue
                n = len(cell)
                ticks = [r["focalHelpTick"] for r in cell if r["focalHelped"]]
                probed = [r for r in cell if r["recognized"] is not None]
                out.append(
                    f"| {c} | {n} | {_rate(_helped(cell), n)} | {_pct(sum(r['earlyHelp'] for r in cell) / n)} | "
                    f"{statistics.median(ticks) if ticks else '–'} | {_pct(sum(r['parseFailures'] > 0 for r in cell) / n)} | "
                    f"{_pct(sum(r['truncations'] > 0 for r in cell) / n)} | "
                    f"{_pct(sum(bool(r['recognized']) for r in probed) / len(probed)) if probed else '–'} |")
            out.append("")
            base = conditions[0]
            for c in conditions[1:]:
                if cells[c] and cells[base]:
                    d, lo_ci, hi_ci = newcombe(_helped(cells[c]), len(cells[c]), _helped(cells[base]), len(cells[base]))
                    out.append(f"- {c} − {base}: {_pp(d)} pp (95% Newcombe {_pp(lo_ci)} to {_pp(hi_ci)})")
            out.append("")

    out += ["## H1 (alert fatigue) and H2 (herding): one-sided Fisher exact tests", "",
            "Holm correction runs over all tests listed (6 when every model and scenario has both conditions). "
            "McNemar is the exact paired check on shared seeds.", ""]
    out += _tests_table(run_tests(runs, models))

    clean = [r for r in runs if r["parseFailures"] == 0 and r["truncations"] == 0]
    unrecognised = [r for r in runs if not r["recognized"]]
    out += ["## Sensitivity checks", "",
            f"### Without runs that had a parse failure or truncation ({len(runs) - len(clean)} removed)", ""]
    out += _tests_table(run_tests(clean, models))
    out += [f"### Without runs the probe flagged as recognised ({len(runs) - len(unrecognised)} removed)", ""]
    out += _tests_table(run_tests(unrecognised, models))
    out += ["## Notes", "",
            "H3 (latency) and H4 (differences by model, scenario and Agreeableness) are descriptive: see the median "
            "outcome ticks above. Power is limited: at 50 runs per cell, drops smaller than about 90% to 60% are "
            "underpowered.", ""]
    return "\n".join(out)
