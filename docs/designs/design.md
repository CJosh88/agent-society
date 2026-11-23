# Agent Society Lab — Design Doc (EGM draft v0.4)

Nov 23, 2026 · @Josh C · Status: draft for review. The code is not built yet; v0.3's code is on the branch `v0.3-alert-fatigue-herding`.

## Overview

Agent Society Lab asks whether a line of LLM agents triaging support tickets can talk itself into mistakes, and whether a more capable agent in the line pulls the others back toward the truth. Agents work one after another on the same ticket queue. Each sees how many earlier agents rated each ticket HIGH or LOW, so every agent's decision becomes part of the next agent's input. Every ticket has a known correct priority, so errors can be measured against the truth and not only against a baseline.

**Why it matters.** Multi-agent business systems pass labels, scores and counts from one agent to the next. If early mistakes propagate, a pipeline of individually reasonable agents can be collectively wrong. If a strong agent early in the line can correct the rest, that is a usable design rule.

**What it builds on.**

- **v0.3 (alert fatigue and herding in triage)** designed a 900-run study with one LLM agent and scripted colleagues, and was piloted but never run at scale. The pilots showed ceilings: gpt-oss-120b and most other Workers AI models escalated the real alert in every `calm` run, and only Llama showed a condition effect in herding. The code and design are preserved on the git branch `v0.3-alert-fatigue-herding`. The `prereg-v2` tag was never created.
- **This repo's `main` was reset to start from this doc.** The new design reuses the v0.3 engine modules, API ingest and results patterns, and replay structure. They are copied back from the branch with `git checkout v0.3-alert-fatigue-herding -- <path>` and then changed (see Target files).
- **The Music Lab design as adapted by Hashemi et al. (arXiv 2610.30769, 22 Oct 2026, preprint).** I read the full text. It supplies the design pattern (parallel worlds, an independent baseline, a signal built from earlier agents' choices) and the measures (KL divergence, unpredictability, early-mover correlation, self-correction by half-split). It tested single-model populations on a taste task with no right answer, and names mixed-model teams, communication and incentives as untested.

**What is new here (claimed with care).** The pipeline is mixed-model as well as single-model, the task has a ground truth, and a condition seeds the first agents with wrong ratings to test recovery. See Prior art for how far that claim can go. A literature check on the novelty claim is milestone C0.

**Stage 2 (RL).** After Stage 1 results, a small open model is trained with LoRA and GRPO inside this environment to be robust to wrong early signals, and evaluated with the same metrics on held-out seeds. Stage 2 has its own design freeze (see RL stage).

**How to use this doc.** It follows the Elephant-Goldfish Model and the Zero-Decision Rule: if something is not specified here, the implementer follows the Default rules in Target files and records the choice in `docs/designs/decisions.md`. Where a number is my estimate and not a measurement, it says so.

**Constraints.** Replay only on the public site, served by the existing VPS deployment. A one-off token budget of about $15 for Stage 1 (an estimate), and about $100 at most for Stage 2 GPU rental (an extrapolation, see Budget).

## Goals and non-goals

Stage 1 is done when a reader can open one URL, replay a world, see how the ratings cascaded, and read per-model results with the paper's measures, plus a short write-up that says what was and was not found.

**Goals**

1. Run a ticket-triage pipeline with 200 agents per world and 8 worlds per cell, in 4 information conditions and 5 populations (3 single-model, 2 mixed). 144 worlds in total.
2. Measure accuracy against a known truth, divergence from independent judgment, unpredictability across replicate worlds, early-mover dependence and self-correction.
3. Test whether a stronger model placed early in a mixed line raises the weaker model's accuracy.
4. Reuse the Agent Society Lab engine, ingest API, fake model and replay structure.
5. Stage 2: train a small open model to resist wrong early signals, and evaluate it against the same baselines.

**Non-goals**

- No new claims about human psychology, and no pooled results across models.
- No agent-to-agent messaging. The only signal is the running count. (The paper lists communication and incentives as untested. That is a later extension, not this study.)
- No live LLM calls from visitors.
- No further work on the v0.3 scenarios. Their code and results stay on the branch `v0.3-alert-fatigue-herding`.

## Research design

Each run is one **world**: a sequence of 200 agents who each triage once. Models are compared with themselves across conditions, never pooled, except in the mixed populations, which are their own populations.

**The queue.** A fixed catalogue of 24 tickets, each with a short text and a hidden truth: 12 are `serious` (the correct priority is HIGH) and 12 are `routine` (the correct priority is LOW). Evidence in the ticket text is clear but not labelled, as in v0.3's double-charge ticket. Four of the routine tickets use alarming wording and four of the serious tickets use calm wording, so wording alone does not give the answer. The catalogue is written once, frozen at pre-registration, and calibrated on the independent baseline only (see Calibration rule).

**An agent's turn.** One LLM call per agent. The agent sees all 24 tickets in an order fixed by its seed (random), a persona, and, in influence conditions, a count for each ticket (how many earlier agents in the same world rated it HIGH, and how many rated it at all). It picks exactly 4 tickets and sets a priority, HIGH or LOW, for each. The reply is one JSON object. The agent then stops. Tickets it did not pick receive nothing from it.

**Influence conditions** (what the agent sees; everything else is identical)

| Condition | What the agent sees |
| --- | --- |
| `independent` | Tickets in random order, no counts. |
| `weak` | Tickets in random order, with counts. |
| `strong` | Tickets sorted by the share of earlier ratings that were HIGH (ties random), with counts. The prompt says the list is sorted that way. |
| `seeded_wrong` | As `weak`, but the first 20 positions are scripted agents who rate every ticket they pick against the truth. Real agents start at position 21. Single-model populations only. |

**Populations**

| Population | Who acts |
| --- | --- |
| `llama`, `gpt-oss`, `haiku` | All 200 agents use that model. |
| `mix_early` | The first 60 agents use the stronger model, the other 140 the weaker. |
| `mix_late` | The last 60 agents use the stronger model, the first 140 the weaker. |

The default pair for the mixed populations is weaker = `llama-3.1-8b` and stronger = `gpt-oss-120b`, to be confirmed in the pilots (see Open questions). The pairing is fixed at pre-registration.

**Design**

| Factor | Levels |
| --- | --- |
| Condition | `independent`, `weak`, `strong` for every population. `seeded_wrong` for single-model populations only. |
| Population | `llama-3.1-8b`, `gpt-oss-120b`, `claude-haiku-5-5`, `mix_early`, `mix_late` |
| Worlds per cell | 8, with world seeds 0–7 shared by every cell (paired). |
| Agents per world | 200 |
| Runs | 3 populations × 4 conditions × 8 + 2 mixed × 3 conditions × 8 = 144 worlds, 28,800 agent calls |

**Pairing.** World seed *w* fixes, for each agent position, the persona and the ticket order. It is the same in every condition and population, so conditions differ only in the information shown, and mixed worlds differ from single-model worlds only in which model answers.

**Hypotheses** (frozen in the README and tagged before the batch runs)

- **H1: influence lowers accuracy.** For each single-model population, the world accuracy under `weak` is lower than under `independent`, and the same under `strong`. Six tests.
- **H2: an early strong agent helps.** In `mix_early`, the weaker model's agents (positions 61–200) are more accurate than the same positions in the all-weaker world, in `weak` and in `strong`. Two tests. A matching contrast for `mix_late` (positions 1–140) is reported, not tested.
- **H3: descriptive.** Divergence from independent judgment, unpredictability across worlds, early-mover correlation and self-correction (below), per population and condition.
- **H4: exploratory.** Recovery after wrong seeding (`seeded_wrong` against `weak`), whether selection (which tickets get picked) shifts as much as rating, and the share of the effect in the persona's Agreeableness level.

**Outcome coding.** The game master, in Python, marks each rating as correct when HIGH matches `serious` or LOW matches `routine`, and stores `correct` on the rating event.

**Measures** (adapted from Hashemi et al.; all computed per population and condition, never pooled)

- **World accuracy** `A_w`: correct ratings divided by all ratings in world `w`. This is the primary outcome.
- **Market share** `p_w(i)`: the share of all HIGH ratings in world `w` that went to ticket `i`.
- **Divergence** `KL_w`: KL divergence of the world's market shares from the pooled shares of the 8 independent worlds, with Jeffreys smoothing (pseudocount 0.5). Reported as the mean over the 8 worlds.
- **Unpredictability** `U`: the mean absolute difference in a ticket's market share across all 28 pairs of the 8 worlds, averaged over the 24 tickets. The independent baseline uses the 28 pairs of the 8 independent worlds.
- **Early-mover correlation:** the Pearson correlation between per-ticket HIGH shares among the first 30 agents and among all later agents in the same world, pooled over worlds.
- **Self-correction against truth:** split each world's chronological ratings into two halves, take the Spearman correlation between per-ticket HIGH counts in each half and the truth (serious = 1, routine = 0, ties handled by average ranks), and report `Δρ = ρ₂ − ρ₁`. Positive means later agents moved toward the truth. This changes the paper's measure, which used the independent-world shares as the reference.
- **Secondary:** selection shares (which tickets get picked), false-HIGH and missed-HIGH rates, and the parse-failure rate.

**Analysis** (`analysis.py`)

- H1 and H2: one-sided Mann–Whitney U tests on world accuracy, 8 worlds against 8 worlds. The smallest attainable one-sided p-value with 8 against 8 is about 8 × 10⁻⁵, so Holm correction across all 8 tests (6 for H1, 2 for H2) at α = 0.05 is attainable. Also report the difference in mean world accuracy with a bootstrap 95% interval over worlds.
- H3 and H4: descriptive. With only three single-model populations, no capability regression is run; the paper's capability association is cited, not reproduced.
- Sensitivity checks: rerun H1 and H2 (a) without worlds where more than 5% of agents had a parse failure and (b) with the worlds whose agents the probe flagged as recognised removed (see Validity controls).
- **Power:** not yet computed. A simulation of the Mann–Whitney tests at 8 against 8 worlds, given the pilot variance, is part of milestone C4. The doc will state which differences are detectable before the tag. 8 worlds is the paper's number, and the paper used 720 agents per world, so effects at 200 agents per world may be noisier.

**Calibration rule.** If the `independent` accuracy in any single-model pilot population is at a ceiling (above 95%) or a floor (below 55%), the ticket texts may be tuned on pilot world seeds (100 and up) using `independent` cells only, never on any influence condition. The levers are how clear the evidence is and the alarming or calm wording. The result is frozen at the tag. If a baseline stays at a ceiling or floor, that is reported as a finding. (The target is 60–90%, which is my assumption of a range where an influence effect can show in either direction.)

**Validity controls**

- **Disguise:** rendered prompts never contain the whole words experiment, study, test, simulation, psychology, bystander, diffusion, Darley, Latané, Genovese, Asch, conformity, herd, herding, fatigue, cascade, popularity or majority (case-insensitive). `test_disguise.py` checks every condition and population.
- **Neutral framing:** an ordinary afternoon on a support desk. The counts are labelled as the team's ratings so far. No instruction mentions accuracy beyond the ordinary job of setting priorities correctly.
- **Recognition probe:** after the last agent in a world, one extra call to a sample of 10 agents' stored contexts (positions drawn by the seed) asks, in plain sentences and without mentioning studies, what the agent thinks was going on. Answers that name the effect or the experiment flag the agent as recognised. This is a cheap spot check: the paper did not test for recognition at all, and PIMMUR (arXiv 2509.18052, abstract read only) reports frontier models identified the underlying experiment in 65.2% of cases in published simulations.
- **Position:** the `strong` condition sorts by prior ratings, so list position and counts move together. The paper notes this confound and proposes, without running, a check that sorts in increasing order. This study adds that check as an exploratory condition `strong_reversed` for single-model populations in a later extension only, unless the pilots show a clear `strong` effect (see Open questions).
- **Pre-registration:** hypotheses, this analysis plan, the ticket catalogue, the pairings, `PROMPT_VERSION = "c1"` and the calibrated difficulty are committed and a signed tag `prereg-c1` is pushed before the batch. Pilots are declared as pilots and excluded.
- **Auditability, not reproducibility:** sampling stays at provider defaults. Every prompt and response is stored.

## Prior art and what it does and does not cover

Verification status is stated because several sources were seen only as search snippets or cited second-hand.

| Work | What it covers | How it was checked |
| --- | --- | --- |
| Hashemi, Ji, Chen, Macy, arXiv 2610.30769 (Oct 2026, preprint) | 13 single-model populations, Music Lab-style parallel worlds, endogenous counts, KL, unpredictability, early movers, self-correction. Finds LLM populations herd more than humans and correct less, with stronger models less affected. | Full text read |
| Weng et al. (ICLR 2025); Zhu et al. (ACL 2025); Cho et al. (2025); Bellina et al. (2026); Qu et al. (2026); Hussain and Nielbo (2026) | Peer-answer conformity on question-answering tasks, including unanimous confederates and the role of confidence and group size. | Named and described in Hashemi's related work only; not opened |
| Zhong et al. (EMNLP Findings 2025); Peng et al. (2026); Wu et al. (ACL Findings 2025) | Sequential ratings with accumulating signals, popularity cues, endogenous counts on a Q&A platform. | Same; not opened |
| Akata et al. (Nature Human Behaviour 2025), Huynh et al. (arXiv 2601.19082), Gao et al. (arXiv 2410.19599) and others | Behaviour in repeated games is conditional on payoff scale, language, framing and model. | Opened in the research report; see `reports/LLM agent game theory sandbox.md` |
| Piche et al. (arXiv 2511.19405) | Naive multi-agent GRPO collapses to defection in social dilemmas; advantage alignment learns tit-for-tat. | Snippet-level; not opened |
| SPIRAL (arXiv 2506.24119), MARSHAL (arXiv 2510.15414) | Self-play RL on small models, gains on reasoning benchmarks. | Abstracts read |

**Reading of the gap.** Unanimous scripted peers on Q&A tasks, and endogenous counts on a taste task, are documented. This design differs in three ways: a ground truth for every item, mixed-model lines with a controlled position for the stronger model, and an explicit wrong-seeding condition. The searches behind "I found no study of mixed-model sequential triage with known truth" were shallow, so it is a lead and not a claim until milestone C0 is done.

## Architecture

A copy of the v0.3 architecture with one structural change: the unit of work is a world of 200 sequential agents, not one focal agent among scripted colleagues.

**Python engine** (`engine/src/asl_engine/`, Python 3.12, uv, LangGraph). The outer graph loops over agent positions: `setup` → `next_agent` → `agent_turn` → `record` (repeat until 200), then `probe` and `finish`. `agent_turn` is the v0.3 subgraph (`perceive` → `decide` → `validate`, one retry). The running counts live in `RunState`. The scripted seeded agents in `seeded_wrong` are produced in `next_agent` without a model call. `RunState.events` and `llm_calls` keep the `operator.add` reducers, and `recursion_limit` is raised to fit 200 positions (about 1,000). `seq` is assigned only in `setup`, `record`, `probe` and `finish`.

**Spring Boot API** (`api/`, Java 21, Maven wrapper, Postgres 16, Flyway). The same pattern as v0.3: one `RunBundle` per world posted by the engine, a read-only REST API and static pages. The same database and Flyway history as v0.3: `V1` and `V2` come from the branch and `V3__cascade.sql` deletes the v0.3 runs and swaps the CHECK constraints, as `V2` did for v0.2.

**Game master.** Deterministic Python. It applies each agent's picks, updates counts, and computes `correct`. It never uses a model.

**Data volume.** A world has 200 agents, about 200 decision events plus about 800 rating events, and 200 LLM-call rows. 144 worlds give about 30,000 agents rows and about 29,000 LLM-call rows, which Postgres handles without special care.

**LLM access.** Through `llm.get_model(key, *, run_seed)` as in v0.3. A mixed world asks for a model per position, so the world builds a small `{key: model}` map once and picks by position.

**Replay.** A static viewer in the same plain-ES-modules style, with no build step. It draws the queue as a board of 24 rounded cards. A card's bar fills with the HIGH share as the world advances, a scrubber moves through agent positions 1–200, and each card is marked serious or routine only in a "reveal truth" toggle. Agents are plain discs along a strip, coloured by model. Plain shapes only, no sprite art.

## Contracts

`contracts/run-bundle.schema.json` is the single source of truth between engine and API, as in v0.3, with these differences. Everything is snake_case in bundles and camelCase in REST responses.

- `experiment` const `cascade_v1`. `scenario` enum `triage_cascade`.
- `condition` enum `independent`, `weak`, `strong`, `seeded_wrong`. A run-level check ties each to the scenario.
- `population` (string) replaces the single model: one of `llama-3.1-8b`, `gpt-oss-120b`, `claude-haiku-5-5`, `mix_early`, `mix_late`, or `fake`. The API keeps a `model` column for the population label.
- `world_seed` replaces `seed` in the bundle; the database column stays `seed`.
- Agent roles: `agent` and `scripted`. `agent_id` pattern `^a[0-9]{1,3}$`, positions 1–200.
- Event types: `AGENT_SPAWNED{position, model}`, `TICKETS_SHOWN{order, counts}` (every agent, `counts` is null in `independent`), `AGENT_PICKED{ticket_ids, thought, scripted}`, `AGENT_RATED{ticket_id, priority, correct}`, `ACTION_PARSE_FAILED{raw_excerpt, truncated}`, `PROBE_ANSWERED{text, recognized}`, `RUN_ENDED{reason}`. Agent events carry `tick` = the agent's position (1–200). `PROBE_ANSWERED` and `RUN_ENDED` carry the last position.
- Derived fields stored on `runs` at ingest: `accuracy`, `rated_count`, `parse_failures`, `recognised_sample`.

Ingest is one `@Transactional` method, `Run` and `Agent` implement `Persistable`, and a repeated post returns 409 (treated as done by the client). The run id is `uuid5` of `population|scenario|condition|world_seed|prompt_version`.

Two hand-written fixtures replace the v0.3 ones in this fork: a short `weak` world with 6 agents, and a `seeded_wrong` world with 6 agents. Both validate against the schema.

`/api/results` counts only runs with `pilot = false`, `experiment = cascade_v1`, the configured prompt version and a population in `asl.study-populations`. It returns, per population and condition, mean world accuracy with a bootstrap interval over worlds, and the measures above. `llm_calls` is never exposed publicly.

## Data model

Same tables as v0.3 (`runs`, `agents`, `events`, `llm_calls`). Changes: `runs.model` holds the population label; `runs.seed` is the world seed; `runs.accuracy`, `runs.rated_count` and `runs.parse_failures` are new; the CHECK constraints use the enums above. `agents.persona` stays JSON. Indexes follow v0.3 on `(experiment, scenario, condition, model)`.

## LLM provider layer

Unchanged from v0.3: Cloudflare Workers AI for `llama-3.1-8b` and `gpt-oss-120b`, Anthropic for `claude-haiku-5-5`, clients at `max_retries=0`, `timeout=60`, `max_tokens=1500`, retries only through tenacity (429, 5xx, timeouts), no temperature, top_p, top_k or seed, parsing of the last valid JSON object, character-based token estimates flagged when a provider returns no usage. One addition: the budget guard reads `ASL_MAX_USD` (set to 20 for this batch) and the engine runs worlds in parallel with `ASL_CONCURRENCY` (default 8, set lower on the free Workers AI tier), but agents inside a world always run one after another.

## Simulation engine

**Seeds.** World seed *w* fixes the persona sequence (200 personas drawn from the same 30-persona file), the ticket order per position, and the 10 positions probed.

**Prompt text** (frozen at `prereg-c1`; held in `scenarios.py`): a persona card; "It is an ordinary weekday afternoon on the support desk of a small online shop. Each ticket needs a priority, HIGH or LOW, before it is picked up. Pick four tickets and set a priority for each."; the 24 tickets; in influence conditions a line per ticket "Rated HIGH by teammates so far: *n* of *m*."; the JSON menu `{"picks": [{"ticket": "T07", "priority": "HIGH | LOW"}], "thought": "..."}`. Disguise rules apply to all of it.

**Validation.** Exactly four distinct tickets with HIGH or LOW. A failure triggers one retry that states the problem. A second failure records `ACTION_PARSE_FAILED` and the agent contributes no ratings.

**Probe.** Run after the last position, for a sample of 10 positions. It uses the stored prompt and reply of each sampled agent plus the plain-sentence question. It costs about 10 extra calls per world, which are included in the budget.

**Fake model.** Seeded from sha256, never Python `hash()`. It rates each ticket HIGH with a probability that depends on the truth and, in influence conditions, on the shown HIGH share, so tests can check that influence conditions move accuracy. It lets C0–C3 pass with no network or keys.

**Personas.** `engine/data/personas.json` is copied from v0.3 and frozen at the tag.

## Frontend replay

Two pages as in v0.3, `index.html` (results and run list) and `replay.html`, plain ES modules, Phaser 3.90.0 pinned from a CDN, no build step.

- **Results page:** per population and condition, mean accuracy with its interval, plus small tables for the measures. An optional plain-SVG bar chart per population compares conditions.
- **Replay:** the queue board and the agent strip described under Architecture, a scrubber over positions 1–200, speed controls, a "show thoughts" toggle, and a "reveal truth" toggle that is off by default so the first look is the same as the agents' view. The log lists each agent's picks and ratings with `correct` shown only when the truth is revealed.

## RL stage (Stage 2)

Stage 2 starts only after Stage 1 results are in, and it has its own short design addendum, `docs/designs/rl-stage.md`, frozen before any training run. What is decided here:

- **Environment:** a thin Gym-style wrapper over the game master, exposing one world as an episode in which the learner sits at a fixed position and sees the counts the earlier agents produced. Earlier agents are replayed from stored Stage 1 worlds, not generated live, so training is cheap and deterministic.
- **Learner:** a small open model (Qwen, 1.5B–3B) with LoRA, first supervised on valid-format replies, then GRPO.
- **Reward:** the fraction of the learner's four ratings that are correct, with a penalty for parse failures. To block reward hacking by always rating HIGH, the catalogue is balanced (12 serious, 12 routine) and the held-out evaluation reports false-HIGH and missed-HIGH rates separately.
- **Splits:** training and evaluation use disjoint world seeds, disjoint tickets (the 24-ticket catalogue is split by a second, frozen catalogue for evaluation), and disjoint personas.
- **Evaluation:** the Stage 1 measures on held-out worlds, including `seeded_wrong`, comparing the base model, the supervised model and the GRPO model against the frozen API models.
- **Compute:** one rented 24 GB Linux GPU, since the TRL and vLLM tooling is Linux-first (inferred, not verified here). The engine and viewer stay on Windows. A first short pilot run measures real GPU time before any budget is committed.
- **Isolation:** Stage 2 runs are posted with `experiment = cascade_rl_v1` so they never enter Stage 1 results.

## Alternatives considered

Nothing in this table may come back without changing this section first.

| Alternative | Why not (for now) |
| --- | --- |
| Keep scripted colleagues and train an RL agent on v0.3's office | Smaller change, but misses the paper's endogenous-feedback design and the mixed-line question |
| Two-stage prompts like Hashemi (select, then evaluate) | Doubles calls and cost for little gain; one call that picks and rates keeps the attention bottleneck |
| One independent world of 400 agents (the paper's shortcut) | 8 independent worlds of 200 allow tests and cost one third more on that condition only |
| Free-form agent messaging | The paper lists communication as untested, but it multiplies cost and breaks the clean count signal; a later extension |
| Persona or strategy bandit layer (research report slice B) | No GPU, but a weaker training signal |
| Exploitability and cross-play harness (research report slice C) | A larger harness; revisit after Stage 2 |
| Pool all models into one analysis | Behaviour is conditional on model; per-model analysis is the project's rule |
| Start a new database | The deployed v0.3 database holds only pilot runs; `V3` clears them like `V2` cleared v0.2, so the volume carries over |

## Target files

The monorepo is `agent-society-lab/` (this repo). `main` starts from this doc alone. Java files live under `api/src/main/java/dev/asl/api/` (shown as `…/`) and Python files under `engine/src/asl_engine/`, the same packages as v0.3.

**Default rules for the implementer**

- These files need no listing: `__init__.py`, `conftest.py`, `uv.lock`, Maven wrapper files, test fixtures, and the response DTO records in `…/*/dto/`.
- Any other file not listed here is allowed only if it is recorded with a one-line reason in `docs/designs/decisions.md`.
- The same file records any choice this doc leaves open.
- Copy before you change: start each file from the branch (`git checkout v0.3-alert-fatigue-herding -- <path>`), commit the copy, then change it, so the history shows what the redesign altered.

| Path | Purpose | Milestone |
| --- | --- | --- |
| `README.md` | Pitch, hypotheses, graph, results, how to run | C0 stub, C3, C5 |
| `docs/designs/design.md`, `decisions.md`, `blockers.md`, `rl-stage.md` | This doc; the decision log; blockers; the Stage 2 addendum | C0, C6 |
| `docs/prior-art.md` | The novelty check: queries run, papers opened, verdict | C0 |
| `docs/graph.mmd` | Output of `asl graph` | C2 |
| `docs/writeup.md` | Skeleton (Question, Design, Results, Limits, What surprised me) | C5 |
| `.github/workflows/ci.yml` | `api` job: `./mvnw -B verify`; `engine` job: `uv run pytest` | C1, C2 |
| `contracts/run-bundle.schema.json`, `fixtures/bundle-weak-small.json`, `fixtures/bundle-seeded-wrong-small.json` | Contract and two handwritten fixtures | C0 |
| `contracts/openapi.yaml` | Written by `OpenApiExportIT` | C1 |
| `api/pom.xml`, `…/AslApplication.java`, `…/config/*`, `…/run/*`, `…/results/*`, `…/web/*` | Copied from v0.3 and changed for the new contract; results add the bootstrap interval and the measures | C1 |
| `api/src/main/resources/db/migration/V1__init.sql`, `V2__pivot.sql`, `V3__cascade.sql` | V1 and V2 from the branch; V3 clears v0.3 runs and swaps the CHECK constraints for the contract above | C1 |
| `api/src/main/resources/application.yml` | As v0.3, with `asl.study-populations` and `asl.prompt-version: c1` | C1 |
| `api/src/main/resources/static/index.html`, `replay.html`, `css/app.css`, `js/common.js`, `js/results.js`, `js/replay.js` | Frontend | C3 |
| `api/src/test/java/dev/asl/api/RunIngestIT.java`, `AdminKeyIT.java`, `ResultsIT.java`, `OpenApiExportIT.java`, `StaticPagesIT.java` | Integration tests (pilot and fake runs must be excluded from results) | C1, C3 |
| `engine/pyproject.toml` | uv project with an `asl` entry point | C2 |
| `cli.py` | `make-personas`, `graph`, `run`, `batch`, `analyze` | C2 |
| `config.py`, `llm.py`, `models.py`, `scenarios.py`, `tickets.py`, `personas.py`, `agent.py`, `graph.py`, `client.py`, `budget.py` | Engine modules; `tickets.py` holds the frozen catalogue and truths | C2 |
| `analysis.py` | World accuracy, Mann–Whitney, Holm, bootstrap, KL, unpredictability, early movers, self-correction, sensitivity checks → `results/results.md` | C5 |
| `engine/data/personas.json`, `engine/data/tickets.json` | Frozen inputs | C2, C4 |
| `engine/tests/test_tickets.py`, `test_counts.py`, `test_outcome_rules.py`, `test_agent_subgraph.py`, `test_graph_fake.py`, `test_disguise.py`, `test_bundle_schema.py`, `test_parse.py`, `test_budget.py`, `test_fake_determinism.py` | pytest suite with no network calls | C2 |
| `engine/tests/test_analysis.py`, `test_measures.py` | Fixed counts → known measure values | C5 |
| `engine/src/asl_engine/rl_env.py`, `engine/rl/train_grpo.py`, `engine/rl/eval.py` | Stage 2 environment, training and evaluation | C6 |
| `results/results.md`, `results/spend.json`, `results/failures.jsonl` | Generated and committed | C5 |
| `deploy/docker-compose.dev.yml`, `docker-compose.yml`, `Caddyfile`, `.env.example`, `deploy.sh`, `api/Dockerfile` | Copied from the branch unchanged | C1, C5 |

## Milestones

Run in order. Each ends with commands Claude Code runs itself. C0–C3 need no API keys. Commit after each one as `C<n>: <title>`.

1. **C0 — Novelty check and contracts.** `docs/prior-art.md` with the queries run, the papers opened (the six conformity papers listed above are opened or replaced), and a verdict on the three claimed differences. The schema, two fixtures, the README stub with the hypotheses, an empty `decisions.md`.
   - Done when: `uv run --with jsonschema python -c "import json,jsonschema; s=json.load(open('contracts/run-bundle.schema.json')); [jsonschema.validate(json.load(open(f)), s) for f in ('contracts/fixtures/bundle-weak-small.json','contracts/fixtures/bundle-seeded-wrong-small.json')]"` exits 0, and `docs/prior-art.md` records a verdict.
2. **C1 — Spring API, dev database and CI.** Copy and adapt the v0.3 API.
   - Done when: `docker compose -f deploy/docker-compose.dev.yml up -d`, then `cd api && ./mvnw -B verify` passes, the failsafe reports list RunIngestIT, AdminKeyIT, ResultsIT and OpenApiExportIT, and `contracts/openapi.yaml` exists.
3. **C2 — Engine with the fake model.** All engine modules, `tickets.json` (draft), `personas.json`, the agent subgraph, `docs/graph.mmd`.
   - Done when: `cd engine && uv run pytest` passes. With the API running, `uv run asl batch --models fake --runs 2 --seed 0 --agents 20` exits 0 and `curl -s localhost:8080/api/runs | jq .page.totalElements` prints 8 (the `fake` population: 4 conditions × 2 worlds, with a smaller world of 20 agents; `--agents` defaults to 200), and a rerun leaves the count unchanged. The mixed populations are covered by unit tests with the fake model, which assign `fake` to both roles.
4. **C3 — Replay frontend and README.** Both pages with plain shapes.
   - Done when: `StaticPagesIT` passes and the operator opens a fake world at `localhost:8080/replay.html?run=<id>` with no console errors.
5. **C4 — Pilots, calibration and pre-registration.** Pilot each single-model population on `independent` (world seeds 100 and up, `--pilot`), apply the calibration rule, run the power simulation, fix the mixed pairing, freeze `tickets.json`, then tag.
   - Done when: each single-model `independent` pilot has parse failures under 5% and accuracy inside 55–95%, `docs/designs/decisions.md` records the power note and the pairing, and the operator has pushed the signed tag `prereg-c1`.
6. **C5 — Stage 1 batch and analysis.** `analysis.py`, `test_analysis.py`, the batch, the write-up skeleton.
   - Done when: `test_analysis.py` passes; `ASL_MAX_USD=20 uv run asl batch --models llama-3.1-8b,gpt-oss-120b,claude-haiku-5-5 --runs 8 --seed 0` completes 144 worlds; `uv run asl analyze` writes `results/results.md`.
7. **C6 — Stage 2 RL.** Write `rl-stage.md` first and freeze it. Then the environment wrapper, supervised start, one short GPU pilot to measure time and cost, then the GRPO run and evaluation.
   - Done when: `rl-stage.md` is committed before any training; the evaluation table compares the base, supervised and GRPO models on held-out worlds with the Stage 1 measures; the false-HIGH and missed-HIGH rates are reported.

**If a milestone fails 3 times in a row,** write what failed to `docs/designs/blockers.md` and move on to the next milestone that doesn't depend on it.

## Deployment and budget

Stage 1 tokens are a one-off cost. These are my estimates, using the per-turn assumptions from the research report: about 1,500 input and 150 output tokens per agent call (the 24-ticket prompt with counts may run 10–30% longer), one call per agent, and a probe of 10 calls per world.

| Item | Turns | Estimate (USD) |
| --- | --- | --- |
| Single-model populations, 3 conditions × 8 worlds × 200 agents × 3 models | 14,400 | about 7 |
| `seeded_wrong`, 8 worlds × 200 agents × 3 models | 4,800 | about 2.3 |
| Mixed populations, 2 × 3 conditions × 8 worlds × 200 | 9,600 | about 4.5 |
| Probes and retries (about 10%) | about 2,900 | about 1.4 |
| **Stage 1 total** | about 31,700 | **about 15** |

Per 1,000 turns: Llama 3.1 8B about $0.55, gpt-oss-120b about $0.64 (more if reasoning tokens count), Haiku 5.5 about $0.23 (maybe +30% for the newer tokenizer). Set `ASL_MAX_USD=20`. The free Workers AI tier (10,000 neurons a day) covers only about 200 Llama turns a day, so Workers Paid ($5 a month) is needed, as it is for v0.3. Workers AI throttles hard on the free tier, so keep `ASL_CONCURRENCY` low.

**Stage 2:** about 5–20 GPU-hours per training run on a rented 24 GB card, at about $0.34–$0.89 an hour on RunPod's list prices as read on 2026-11-23, so about $2–$20 per run and under about $100 in total. No source reports GPU-hours for a multi-turn text game, so this is an extrapolation; the C6 pilot replaces it with a measurement.

**Wall clock:** agents in a world run in sequence, at about 2–5 seconds per call, so a 200-agent world takes about 7–17 minutes. Worlds run in parallel.

**Server:** the public site is the existing VPS deployment (Docker Compose, Caddy), redeployed with `bash deploy/deploy.sh ubuntu@148.113.251.161` after C5. The `V3` migration deletes the v0.3 pilot runs on the server. The experiment itself runs on the operator's laptop.

**Human-only checklist**

- [ ] Run the C0 novelty check and record the verdict.
- [ ] Confirm Cloudflare Workers Paid and keep the Anthropic spend limit.
- [ ] Run the C4 pilots, then push `git tag -s prereg-c1 && git push origin prereg-c1`.
- [ ] Rent a Linux GPU pod for C6 and run the short pilot first.
- [ ] Run the batch and `asl analyze`, spot-check thoughts in about 10 worlds, pick featured worlds, write `docs/writeup.md`.

## Risks and open questions

**Risks**

| Risk | Effect | Mitigation |
| --- | --- | --- |
| The baseline accuracy is at a ceiling or floor | No influence effect can show | The calibration rule on `independent` only, then report it as a finding |
| 8 worlds per cell is too few at 200 agents per world | A real effect goes undetected | A power simulation before the tag, and the exact detectable difference is stated |
| The `strong` condition confounds counts with list position | Part of the effect may be position | The paper notes this; `strong_reversed` is an optional later check |
| Models recognise the setting | Recall of textbook effects, not behaviour | Neutral wording, banned words and the probe on a sample, plus a sensitivity analysis |
| Sequential worlds are slow | The batch takes hours | Worlds in parallel, a lower concurrency on the free tier, the resumable 409 behaviour |
| Mixed-population result is null | H2 fails | Reported as a null; the design still yields the single-model results |
| Reward hacking in Stage 2 (always HIGH) | A meaningless RL result | Balanced catalogue, separate false-HIGH and missed-HIGH rates, held-out tickets |
| A preprint's numbers change | The cited context shifts | Cite it as a preprint and avoid relying on its exact figures |
| Windows install trouble for TRL and vLLM | Stage 2 cannot train locally | Train on a rented Linux pod; keep Windows for the engine and viewer |
| Public thoughts include unsuitable text | A reputational problem | A thoughts toggle and a spot-check of featured worlds |

**Open questions** (each has a default that applies if nobody answers before handoff)

- [ ] Which pair should the mixed populations use? *Default:* weaker `llama-3.1-8b`, stronger `gpt-oss-120b`, confirmed or swapped for `claude-haiku-5-5` in the C4 pilots on `independent` accuracy only.
- [ ] Should a `strong_reversed` condition be added to remove the position confound? *Default:* no for the first batch; add it only if the pilots show a clear `strong` effect.
- [ ] Should the worlds be 200 agents or 100? *Default:* 200, falling back to 100 (about half the cost) only if the budget guard stops the pilots.
- [ ] Should `seeded_wrong` also be run on the mixed populations? *Default:* no.
- [ ] Should the probe run on every agent? *Default:* no, a sample of 10 per world.

## Revision log

| Change | Why | Source |
| --- | --- | --- |
| v0.4 (2026-11-23): `main` is reset to this design and the v0.3 code is kept on the branch `v0.3-alert-fatigue-herding`; a sequential ticket-triage pipeline (200 agents per world, 8 worlds per cell), endogenous counts, a known truth, mixed-model populations and a wrong-seeding condition; Hashemi-style measures; a Stage 2 RL addendum | The v0.3 pilots hit ceilings in most models. The research survey and the Hashemi et al. full text show that mixed-model sequential feedback with a ground truth is thin, and an RL stage needs a clean environment and a published evaluation protocol | Operator, after the research survey in `reports/LLM agent game theory sandbox.md` and a full read of arXiv 2610.30769; the operator chose to keep the name Agent Society Lab and replace the repo's contents |
