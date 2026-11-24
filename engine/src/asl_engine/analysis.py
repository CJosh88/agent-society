"""Stage 1 analysis: world accuracy, the pre-registered tests, and Hashemi et al.'s measures.

Everything is computed per population and condition, never pooled. The pure functions take `World` objects, so
tests can use small hand-made worlds. `load_worlds` reads finished runs from the API, and `render` writes the
markdown report.
"""

from __future__ import annotations

import itertools
import math
import os
from dataclasses import dataclass, field

import httpx
import numpy as np
from scipy.stats import mannwhitneyu, spearmanr

from .config import CONDITIONS, EXPERIMENT, MIX_BLOCK_SHARE, MIX_PAIR, STUDY_POPULATIONS, api_url
from .scenarios import PROMPT_VERSION
from .tickets import load_tickets

BOOTSTRAP_SAMPLES = 4000
BOOTSTRAP_SEED = 20261123  # the same seed the API uses for its results page
FAMILY_SIZE = 8  # pre-registered: 6 tests for H1 and 2 for H2, Holm over all 8
EARLY_AGENTS = 30
PARSE_FAILURE_LIMIT = 0.05
SINGLE_POPULATIONS = ("llama-3.1-8b", "gpt-oss-120b", "claude-haiku-5-5")


@dataclass
class Rating:
    position: int
    ticket: str
    high: bool
    correct: bool


@dataclass
class World:
    population: str
    condition: str
    seed: int
    n_agents: int
    ratings: list[Rating]
    scripted: set[int] = field(default_factory=set)
    agreeableness: dict[int, str] = field(default_factory=dict)  # position -> low / medium / high
    parse_failures: int = 0
    probe_count: int = 0
    recognised: int = 0


def truth_vector() -> dict[str, int]:
    return {t.id: int(t.truth == "serious") for t in load_tickets()}


# ---- accuracy and rates ----


def accuracy(world: World, lo: int = 1, hi: int | None = None) -> float:
    """Correct ratings over all ratings made by positions lo..hi."""
    hi = hi or world.n_agents
    rs = [r for r in world.ratings if lo <= r.position <= hi]
    return sum(r.correct for r in rs) / len(rs) if rs else math.nan


def false_high_rate(world: World) -> float:
    truth = truth_vector()
    rs = [r for r in world.ratings if not truth[r.ticket]]
    return sum(r.high for r in rs) / len(rs) if rs else math.nan


def missed_high_rate(world: World) -> float:
    truth = truth_vector()
    rs = [r for r in world.ratings if truth[r.ticket]]
    return sum(not r.high for r in rs) / len(rs) if rs else math.nan


def serious_pick_share(world: World) -> float:
    """Share of picked tickets that are serious. Picks equal ratings, so this is the selection measure."""
    truth = truth_vector()
    return sum(truth[r.ticket] for r in world.ratings) / len(world.ratings) if world.ratings else math.nan


# ---- Hashemi et al.'s measures ----


def high_counts(world: World, lo: int = 1, hi: int | None = None) -> np.ndarray:
    ids = list(truth_vector())
    idx = {t: i for i, t in enumerate(ids)}
    out = np.zeros(len(ids))
    for r in world.ratings:
        if r.high and lo <= r.position <= (hi or world.n_agents):
            out[idx[r.ticket]] += 1
    return out


def market_shares(world: World) -> np.ndarray:
    """Each ticket's share of all HIGH ratings in the world."""
    c = high_counts(world)
    return c / c.sum() if c.sum() else np.full(len(c), 1 / len(c))


def kl_from_pooled(world: World, baseline: list[World]) -> float:
    """KL(world's market shares || pooled shares of the baseline worlds), Jeffreys smoothing (0.5)."""
    p = high_counts(world) + 0.5
    q = sum(high_counts(w) for w in baseline) + 0.5
    p, q = p / p.sum(), q / q.sum()
    return float(np.sum(p * np.log(p / q)))


def unpredictability(worlds: list[World]) -> float:
    """Mean absolute difference in a ticket's market share across all pairs of worlds, averaged over tickets."""
    if len(worlds) < 2:
        return math.nan
    s = np.array([market_shares(w) for w in worlds])
    return float(np.mean([np.abs(a - b).mean() for a, b in itertools.combinations(s, 2)]))


def early_mover_correlation(worlds: list[World]) -> float:
    """Pearson correlation of per-ticket HIGH rates among the first 30 agents and among all later agents."""
    xs: list[float] = []
    ys: list[float] = []
    ids = list(truth_vector())
    for w in worlds:
        for t in ids:
            early = [r.high for r in w.ratings if r.ticket == t and r.position <= EARLY_AGENTS]
            late = [r.high for r in w.ratings if r.ticket == t and r.position > EARLY_AGENTS]
            if early and late:
                xs.append(sum(early) / len(early))
                ys.append(sum(late) / len(late))
    if len(xs) < 3 or np.std(xs) == 0 or np.std(ys) == 0:
        return math.nan
    return float(np.corrcoef(xs, ys)[0, 1])


def self_correction(world: World) -> float:
    """Spearman(HIGH counts, truth) in the second half minus the first half. Positive means later agents did better."""
    truth = np.array(list(truth_vector().values()))
    half = world.n_agents // 2
    rho = []
    for lo, hi in ((1, half), (half + 1, world.n_agents)):
        c = high_counts(world, lo, hi)
        rho.append(math.nan if np.std(c) == 0 else float(spearmanr(c, truth).statistic))
    return rho[1] - rho[0]


def revisions(world: World, independent: World) -> tuple[float, float]:
    """Harmful and beneficial revision rates against the independent world with the same seed.

    Over (position, ticket) pairs rated in both worlds: harmful = right when independent and wrong now,
    beneficial = the reverse.
    """
    ind = {(r.position, r.ticket): r.correct for r in independent.ratings}
    both = [(ind[(r.position, r.ticket)], r.correct) for r in world.ratings if (r.position, r.ticket) in ind]
    if not both:
        return math.nan, math.nan
    return (sum(a and not b for a, b in both) / len(both), sum(b and not a for a, b in both) / len(both))


# ---- tests ----


def holm(pvalues: list[float], m: int = FAMILY_SIZE) -> list[float]:
    """Holm-adjusted p-values for a family of m tests, of which only `pvalues` were run (the rest count as p = 1)."""
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    adj = [math.nan] * len(pvalues)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adj[i] = running
    return adj


def bootstrap_difference(a: list[float], b: list[float]) -> tuple[float, float, float]:
    """Mean(a) - mean(b) with a 95% percentile interval, resampling worlds within each group."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    a_, b_ = np.array(a), np.array(b)
    draws = np.array(
        [rng.choice(a_, len(a_)).mean() - rng.choice(b_, len(b_)).mean() for _ in range(BOOTSTRAP_SAMPLES)]
    )
    draws.sort()
    n = len(draws)
    return float(a_.mean() - b_.mean()), float(draws[math.floor(0.025 * (n - 1))]), float(
        draws[min(n - 1, math.ceil(0.975 * (n - 1)))]
    )


def bootstrap_mean(values: list[float]) -> tuple[float, float, float]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    v = np.array(values)
    draws = np.sort([rng.choice(v, len(v)).mean() for _ in range(BOOTSTRAP_SAMPLES)])
    n = len(draws)
    return float(v.mean()), float(draws[math.floor(0.025 * (n - 1))]), float(draws[min(n - 1, math.ceil(0.975 * (n - 1)))])


@dataclass
class TestRow:
    hypothesis: str
    population: str
    condition: str
    contrast: str
    n_a: int
    n_b: int
    difference: float
    low: float
    high: float
    p: float
    p_holm: float = math.nan


def cell(worlds: list[World], population: str, condition: str) -> list[World]:
    return sorted((w for w in worlds if w.population == population and w.condition == condition), key=lambda w: w.seed)


def run_tests(worlds: list[World]) -> list[TestRow]:
    """H1: independent beats weak / strong per single population. H2: mix_early's weaker-model positions beat all-weaker."""
    rows: list[TestRow] = []

    def add(h: str, pop: str, cond: str, contrast: str, hi: list[float], lo: list[float], hi_first: bool) -> None:
        """Tests hi > lo. The difference is reported as hi - lo if hi_first, otherwise lo - hi."""
        if len(hi) < 2 or len(lo) < 2:
            return
        p = float(mannwhitneyu(hi, lo, alternative="greater").pvalue)
        d, lo_ci, hi_ci = bootstrap_difference(hi, lo) if hi_first else bootstrap_difference(lo, hi)
        rows.append(TestRow(h, pop, cond, contrast, len(hi), len(lo), d, lo_ci, hi_ci, p))

    for pop in SINGLE_POPULATIONS:
        ref = [accuracy(w) for w in cell(worlds, pop, "independent")]
        for cond in ("weak", "strong"):
            add("H1", pop, cond, f"{cond} below independent", ref, [accuracy(w) for w in cell(worlds, pop, cond)], False)
    block = round(MIX_BLOCK_SHARE * 200)
    for cond in ("weak", "strong"):
        mixed = [accuracy(w, block + 1, w.n_agents) for w in cell(worlds, "mix_early", cond)]
        weaker = [accuracy(w, block + 1, w.n_agents) for w in cell(worlds, MIX_PAIR["weaker"], cond)]
        add("H2", "mix_early", cond, f"positions {block + 1}+ above all-{MIX_PAIR['weaker']}", mixed, weaker, True)
    for row, adj in zip(rows, holm([r.p for r in rows])):
        row.p_holm = adj
    return rows


def sensitivity_sets(worlds: list[World]) -> dict[str, list[World]]:
    return {
        f"without worlds with parse failures in over {PARSE_FAILURE_LIMIT:.0%} of agents": [
            w for w in worlds if w.parse_failures / w.n_agents <= PARSE_FAILURE_LIMIT
        ],
        "without worlds where the probe flagged recognition": [w for w in worlds if w.recognised == 0],
    }


# ---- loading ----


def study_populations() -> tuple[str, ...]:
    raw = os.environ.get("ASL_STUDY_POPULATIONS", "")
    return tuple(p.strip() for p in raw.split(",") if p.strip()) or STUDY_POPULATIONS


def _world_from(detail: dict, events: list[dict]) -> World:
    run = detail["run"]
    scripted, agree = set(), {}
    for a in detail["agents"]:
        pos = int(a["agentId"][1:])
        if a.get("role") == "scripted":
            scripted.add(pos)
        big5 = (a.get("persona") or {}).get("big5") or {}
        if "A" in big5:
            agree[pos] = big5["A"]
    ratings = [
        Rating(e["tick"], e["payload"]["ticket_id"], e["payload"]["priority"] == "HIGH", bool(e["payload"]["correct"]))
        for e in events
        if e["type"] == "AGENT_RATED"
    ]
    return World(
        run["population"], run["condition"], run["worldSeed"], len(detail["agents"]), ratings, scripted, agree,
        run.get("parseFailures", 0), run.get("probeCount", 0), run.get("recognisedSample", 0),
    )


def load_worlds(base: str | None = None, populations: tuple[str, ...] | None = None) -> list[World]:
    """Study worlds only: no pilots, this experiment and prompt version, populations in the study set."""
    base = base or api_url()
    populations = populations or study_populations()
    worlds: list[World] = []
    with httpx.Client(timeout=60) as c:
        page = 0
        while True:
            body = c.get(f"{base}/api/runs", params={"page": page, "size": 100}).raise_for_status().json()
            for s in body["content"]:
                if s["pilot"] or s["population"] not in populations:
                    continue
                detail = c.get(f"{base}/api/runs/{s['id']}").raise_for_status().json()
                if detail["run"]["experiment"] != EXPERIMENT or detail["run"]["promptVersion"] != PROMPT_VERSION:
                    continue
                # the detail's run block has no parse-failure count; the summary does
                detail["run"].setdefault("parseFailures", s.get("parseFailures", 0))
                events = c.get(f"{base}/api/runs/{s['id']}/events").raise_for_status().json()
                worlds.append(_world_from(detail, events))
            page += 1
            if page >= body["page"]["totalPages"]:
                return worlds


# ---- report ----


def _f(x: float, digits: int = 3) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{digits}f}"


def _p(x: float) -> str:
    return "n/a" if math.isnan(x) else ("<0.001" if x < 0.001 else f"{x:.3f}")


def _mean(xs: list[float]) -> float:
    xs = [x for x in xs if not math.isnan(x)]
    return float(np.mean(xs)) if xs else math.nan


def render(worlds: list[World]) -> str:
    out = ["# Results", "", f"Experiment `{EXPERIMENT}`, prompt version `{PROMPT_VERSION}`. {len(worlds)} worlds."]
    out += ["Every number is per population and condition. Intervals are 95% percentile bootstraps over worlds.", ""]

    out += ["## World accuracy", "", "| Population | Condition | Worlds | Mean accuracy | 95% interval | Parse failures per agent | "
            "False-HIGH | Missed-HIGH | Serious share of picks |", "|---|---|---|---|---|---|---|---|---|"]
    for pop in STUDY_POPULATIONS + ("fake",):
        for cond in CONDITIONS:
            ws = cell(worlds, pop, cond)
            if not ws:
                continue
            m, lo, hi = bootstrap_mean([accuracy(w) for w in ws])
            out.append(
                f"| {pop} | {cond} | {len(ws)} | {_f(m)} | {_f(lo)} to {_f(hi)} | "
                f"{_f(_mean([w.parse_failures / w.n_agents for w in ws]))} | {_f(_mean([false_high_rate(w) for w in ws]))} | "
                f"{_f(_mean([missed_high_rate(w) for w in ws]))} | {_f(_mean([serious_pick_share(w) for w in ws]))} |"
            )

    def tests_table(title: str, rows: list[TestRow]) -> list[str]:
        t = ["", f"## {title}", "", f"One-sided Mann-Whitney U, Holm over a family of {FAMILY_SIZE}.", "",
             "| Hypothesis | Population | Condition | Contrast | Worlds | Difference | 95% interval | p | Holm p |",
             "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            t.append(f"| {r.hypothesis} | {r.population} | {r.condition} | {r.contrast} | {r.n_a} v {r.n_b} | "
                     f"{_f(r.difference)} | {_f(r.low)} to {_f(r.high)} | {_p(r.p)} | {_p(r.p_holm)} |")
        if not rows:
            t.append("| (no tests could be run) | | | | | | | | |")
        return t

    out += tests_table("H1 and H2", run_tests(worlds))
    for name, subset in sensitivity_sets(worlds).items():
        out += tests_table(f"Sensitivity: {name}", run_tests(subset))

    out += ["", "## H3: measures from Hashemi et al.", "",
            "| Population | Condition | KL from independent | Unpredictability | Early-mover correlation | Self-correction | "
            "Harmful revision | Beneficial revision |", "|---|---|---|---|---|---|---|---|"]
    for pop in STUDY_POPULATIONS + ("fake",):
        base = cell(worlds, pop, "independent")
        for cond in CONDITIONS:
            ws = cell(worlds, pop, cond)
            if not ws or not base:
                continue
            harm = ben = math.nan
            if cond != "independent":
                by_seed = {w.seed: w for w in base}
                pairs = [revisions(w, by_seed[w.seed]) for w in ws if w.seed in by_seed]
                harm, ben = _mean([h for h, _ in pairs]), _mean([b for _, b in pairs])
            out.append(
                f"| {pop} | {cond} | {_f(_mean([kl_from_pooled(w, base) for w in ws]))} | {_f(unpredictability(ws))} | "
                f"{_f(early_mover_correlation(ws))} | {_f(_mean([self_correction(w) for w in ws]))} | {_f(harm)} | {_f(ben)} |"
            )
    out += ["", "No floor for the revision rates is reported: each cell has one run per world seed, so the "
            "independent worlds have no repeats to disagree with. Provider-default sampling makes the rates noisy.", ""]

    out += ["## H4: exploratory", "", "Recovery after wrong seeding: mean accuracy of positions after the scripted block.", "",
            "| Population | Condition | Accuracy after the scripted block |", "|---|---|---|"]
    for pop in SINGLE_POPULATIONS + ("fake",):
        sw = cell(worlds, pop, "seeded_wrong")
        if not sw:
            continue
        k = max(max(w.scripted) for w in sw if w.scripted)
        for cond in ("independent", "weak", "strong", "seeded_wrong"):
            ws = cell(worlds, pop, cond)
            if ws:
                out.append(f"| {pop} | {cond} | {_f(_mean([accuracy(w, k + 1) for w in ws]))} |")
    out += ["", "Accuracy by the persona's Agreeableness level, per condition (effect = condition minus independent).", "",
            "| Population | Condition | Agreeableness | Accuracy | Effect |", "|---|---|---|---|---|"]
    for pop in STUDY_POPULATIONS + ("fake",):
        base = cell(worlds, pop, "independent")
        if not base:
            continue
        for cond in CONDITIONS:
            for level in ("low", "medium", "high"):
                def acc(ws: list[World]) -> float:
                    vals = [r.correct for w in ws for r in w.ratings if w.agreeableness.get(r.position) == level]
                    return sum(vals) / len(vals) if vals else math.nan
                ws = cell(worlds, pop, cond)
                if ws:
                    out.append(f"| {pop} | {cond} | {level} | {_f(acc(ws))} | {_f(acc(ws) - acc(base)) if cond != 'independent' else 'n/a'} |")
    return "\n".join(out) + "\n"
