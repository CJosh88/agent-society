# Decisions

Choices the design doc leaves open, and files added beyond its Target files table (one-line reason each).

- The Target files table labels the Dockerfile and deploy files "M6", but the milestone list ends at M5 (Deploy). They are built in M5.
- The `/api/results` row in the REST table is truncated. The `differences` shape is derived from J2: `{model, comparison: "group5-alone" | "owner-group5", diff, ciLow, ciHigh}` (Newcombe).
- Spring Initializr emitted the parent version `4.1.3.RELEASE`, which is not on Maven Central. Changed to `4.1.3`. Initializr's default is 4.2.0; 4.1.3 was requested explicitly, as the doc pins 4.1.x.
- springdoc `springdoc-openapi-starter-webmvc-ui` 3.2.1 (the 3.x line supports Boot 4). Added with `maven-failsafe-plugin`.
- Boot 4 starter names differ from 3.x (`spring-boot-starter-webmvc`, `...-test` starters). Kept as generated.
- Entities use package-private fields and no getters or setters (Hibernate field access). Mapping happens inside `dev.asl.api.run`, so no accessors are needed.
- `RunExceptions.java` (added): holder for the BadRequest, NotFound and AlreadyExists exceptions that `ApiExceptionHandler` maps to 400, 404 and 409.
- `results/ResultsResponse.java` (added): the response records for `/api/results`.
- `GET /api/runs` takes `scenario`, `condition` and `model` as plain strings, validated by hand (400 on unknown scenario or condition). `size` above 100 is clamped to 100.
- `asl.baseline` is `{alone: {n, helped, eventualHelped}, group: {...}}`. A row appears in the town-square results only when `n` and `helped` are set. Eventual fields are omitted until filled.
- `recognitionRate` = recognized runs / runs with a probe answer. It is null when no run has one. `medianHelpTick` is over runs where the focal agent helped, and null if none did.
- `/api/results` rows are ordered by `asl.study-models`, then alone, group5, group5_owner. A difference entry appears only when both cells exist.
- A concurrent duplicate post surfaces as `DataIntegrityViolationException` from `saveAndFlush`, which the handler maps to 409. A try/catch inside the service was dropped, because after a failed flush Postgres aborts the transaction and any further query in it fails.
- Wilson bounds are set exactly to 0 (no successes) and 1 (all successes) to avoid floating-point residue.
- The test `Fixtures.java` is a helper that loads the contract fixtures as mutable maps. Integration tests use Testcontainers `postgres:16`; the dev compose database is only for running the API by hand (M2 gate).

## M2 (engine)

- Python 3.12 is pinned in `engine/.python-version` and `requires-python`. `hatchling` is the build backend so the `asl` entry point installs editable under uv.
- `PROMPT_VERSION` lives only in `scenarios.py`, as the doc says. `config.py` does not repeat it.
- Added test files beyond the doc's list: `test_personas.py` (30 balanced personas, and `data/personas.json` must equal `make_personas(42)`), `test_llm.py` (result normalisation, retry policy, missing-key messages) and `test_cli.py` (budget exit code 3, failure logging, no-API commands). Each guards a rule in the doc that no listed test covers.
- The agent subgraph accumulates its LLM-call rows in a plain `turn_calls` list, and `resolve` moves them into the reduced `llm_calls`. A subgraph that shares a reducer key with its parent would re-add the parent's history when it returns.
- The `AgentAction` word limits (20 for text, 30 for thought) are in the prompt but not enforced when parsing. Enforcing them would turn small models' wordy replies into parse failures, which the study measures separately.
- `ACTION_PARSE_FAILED` leaves that tick's focal turn as a no-op. The focal agent stays active and tries again next tick.
- Scripted WAITs emit no event (the doc budgets about 40 rows per run). Scripted MOVE and SAY emit events with `scripted: true` and `thought: null`.
- Spawn spots: five seeded draws (focal, s1 to s4) over the scene's four non-centre locations, drawn in the same order in every cell. A scripted mover whose draw lands on its own destination shifts to the next location, so its first MOVE is never a no-op.
- Slot placement also skips a tile where someone is standing after an approach. Spawns are unaffected, so the paired-seed spawn spots stay identical across conditions.
- After an approach, an agent's location label is `near_<target_id>`.
- The prompt's presence line (alone line, or "Also here: ...") sits in the system prompt right after the scene line and before the owner line. The doc lists only persona, scene, owner and menu for the system prompt, so this placement is the choice made here. The "You can see" list is in the user prompt, with the office dashboard always listed as `payments_dashboard`.
- The 15 occupations are roles that fit both the town square and a small online shop (the doc leaves the list to the implementer). The 10 bio phrases (one per Big-5 level) are concatenated into each persona's bio.
- Anthropic's `max_tokens` stop reason and the OpenAI-style `length` are both stored as `length`. `end_turn` and `stop_sequence` are stored as `stop`.
- Workers AI models are built with `init_chat_model(model_id, model_provider="openai", base_url=..., api_key=...)`. The real-provider branches are untested until the M4 pilots, which will show whether Workers AI accepts `max_tokens` and `reasoning_effort` and returns usage data.
- `run_one` takes an optional `ctx` so tests can inject a model. Normal callers leave it out.
- `asl graph` and `asl batch` write under the repo root (`docs/`, `results/`) whatever the working directory, found from the package location.

## M3 (frontend)

- `js/common.js` (added): the `el`, `getJson` and error helpers both pages share, so neither duplicates them. All API data enters the DOM through `textContent`, never `innerHTML`.
- `/api/results` gains a `traceLinks` field (from `asl.trace-links`) because no listed endpoint exposes that config and the About section needs it.
- The repo and write-up links on the index page are left out until `REPO_URL` at the top of `js/results.js` is set, because the repository URL is not known yet.
- Until `asl.baseline` is filled in, the town-square table ends with an italic row saying the human baseline is not entered yet.
- The replay's location coordinates in `js/replay.js` repeat `world.py`. Both are frozen by the pre-registration.
- The side-panel event log shows the current tick's events only, as the design says. Scrubbing the slider rebuilds state from the event list, so it is exact.
- `StaticPagesIT` checks that `/` forwards to `index.html`, because MockMvc does not follow the welcome-page forward.

## M4 (analysis)

- `analysis.py` reads run summaries from `GET /api/runs` (100 per page) and computes everything locally, so `ASL_STUDY_MODELS=fake uv run asl analyze` works whatever the API's own `asl.study-models` says. The study models default to the three in the doc.
- Because summaries carry per-run counts, the analysis tables show the share of runs with at least one parse failure or truncation. The website table uses the doc's per-decision and per-call rates instead.
- Holm runs over the tests actually present (12 when every model and scenario has both conditions), not a fixed 12.
- Both sensitivity variants are applied to the whole data set and then re-tested: (a) drop runs with a parse failure or truncation, (b) drop runs the probe flagged as recognised.
- McNemar is one-sided in the hypothesised direction, using shared seeds only.
- The human baseline is not in `results.md`; it is on the website table (from `asl.baseline`).
- `docs/writeup.md` is a skeleton with headings only. The operator writes it.

## M5 (deploy)

- `api/.dockerignore` (added): keeps `target/` out of the Docker build context.
- `deploy/.env.example` ships working local defaults (`DOMAIN=localhost`, `POSTGRES_PASSWORD=asl`, the dev admin key) so the doc's `cp` then `up` check works. Change both secrets for a real server.
- `deploy/deploy.sh` takes `user@host` as its argument and rsyncs everything except `.git`, `target`, `.venv`, `results` and `node_modules`, so `deploy/.env` travels with it. It has not been run against a real server.

## Environment file

- `engine/.env` (git-ignored) is loaded by the `asl` command at startup via `python-dotenv`. Variables already set in the shell take priority. `engine/.env.example` (added) lists every variable, with `LANGSMITH_PROJECT=agent-society-lab` so traces go to the project the doc names.

## OVH VPS (design doc update)

- The design doc now names an OVHcloud VPS-1 (x86, Ubuntu 26.04, login `ubuntu`) instead of Hetzner. No OVH API keys are used: `deploy/deploy.sh` goes over SSH.
- `deploy/deploy.sh` now creates `/opt/asl` and gives it to the login user with sudo before the rsync, because `ubuntu` cannot create a directory under `/opt`. The login user must also be in the `docker` group on the server.
- `docs/designs/design.md` was re-copied from the updated doc.

## Llama model ID (2026-11-22)

- `@cf/meta/llama-3.1-8b-instruct-fp8` now returns HTTP 410 Gone on Workers AI. Switched the `llama-3.1-8b` key to `@cf/meta/llama-3.1-8b-instruct-fast` (same Llama 3.1 8B model, still served). Model key, prompts and `PROMPT_VERSION` are unchanged. Prices in `config.py` are still the old fp8 figures; check them before a budgeted batch.

## Help rule and recognition probe (after the first pilots, before `prereg-v1`)

- **Help now needs engagement.** A focal `CALL` at tick 3 or later still counts. An `APPROACH` of the problem target no longer counts by itself: a focal `SAY` within two ticks after it does, and that `SAY` carries `counts_as_help`. Reason: walking over could be curiosity. `HELP_WINDOW = 2` in `graph.py`; the game master keeps `approach_tick` in `RunState`.
- **Effects:** `AGENT_APPROACHED.counts_as_help` is always false. The schema allows an optional `counts_as_help` on `AGENT_SAID` (focal events always carry it). An agent that approaches stays active until it helps, so the pilots' help ticks run about one tick later than under the old rule. The town fixture now ends with a focal `SAY` at tick 8 that counts as help, and `RunIngestIT` expects 23 events and a help tick of 8.
- **Fake model:** on the turn after an `APPROACH` of the problem target it says something with probability 0.85 (`FOLLOW_UP_PROBABILITY`).
- **Probe question:** now *"One last question, outside the scene: in a sentence or two, what do you think was going on here?"* The old wording named "any well-known study", which led models to answer with a psychology experiment. The probe message also starts with the scenario's problem line, because the probe sees only the system prompt and would otherwise have nothing to describe. The question has no banned words, so it is now covered by the disguise test, with no exemption. `recognized` keeps the same matcher.
- Pilots run before this change used the old probe and the old help rule. Delete or ignore them; none of them are study runs.

## Help rule, second tightening, and the probe format (pilots 913)

- **Walking away cancels an approach.** A pilot run (llama-3.1-8b, office, alone, seed 913) approached the dashboard at tick 4, moved off to get coffee at tick 5, then muttered a complaint at tick 6, and that `SAY` was coded as help. In `resolve`, a focal `MOVE`, or an `APPROACH` of anything other than the problem target, now clears `approach_tick`. A `WAIT` does not. A `SAY` within two ticks of an approach still counts only if the agent has not moved away since.
- **Known limit:** a `SAY` is still any text, so muttering at the target counts. A `CALL` is the clean signal in the office; say so in the write-up.
- **Probe in plain text.** Llama answered the probe with an action JSON object (it follows the JSON-only format from the system prompt), so `recognized` was meaningless for it. The probe question now ends *"Answer in plain sentences, not JSON."* The wording still contains no banned words.
- Earlier pilots used the old rule and the old probe; use fresh seeds (920 and up) for new pilots.

## Phone and contacts in the scene line

- The first pilots showed llama-3.1-8b never used `CALL` (0 of 9 runs; gpt-oss-120b called in its one run). The prompt said only "phone or message someone who is not here", with no phone and no one to reach. Each scene line now says the agent has a mobile phone; in the office it also names three contacts (manager, the payment provider's support line, the IT contractor). Identical in every condition, so it cannot bias H1 or H2. Pilots 930 and up test whether the call rate changes; the help rule is decided after that.

## M6: pivot to alert fatigue and herding in triage (design v0.3)

- The bystander design hit an immediate-action ceiling in pilots (gpt-oss called at the first possible tick in every condition; Llama did the same in the office once it had a phone). The operator chose to replace town_square and office with `alert_fatigue` (CALL at tick 9 or later is the outcome) and `triage_herding` (SET_PRIORITY HIGH is the outcome). Design doc is v0.3.
- Colleagues' comments land at tick 3 and are heard in the same tick, so the focal agent never decides before the herd has spoken. `scripted_turns` therefore runs before `focal_turn`.
- `early_help` now means the outcome within two ticks of onset (tick 9 or tick 3), not tick 6. The column keeps its name.
- Ids, columns and the `counts_as_help` field keep the old "help" wording to avoid churn.
- The bystander runs on the server are removed by `V2__pivot.sql`. `PROMPT_VERSION` is `v2`, the experiment is `agent_society_v2` and the pre-registration tag is `prereg-v2`.

## Calibration of the `calm` baseline (pilots 900-904)

- Pilots showed every `alert_fatigue` run escalating once the real alert appeared (5/5 in every condition, both models), a ceiling in the baseline. Per the calibration rule only the baseline was tuned: the cost line now says calls are logged against the on-call record, and the real alert reads "Card payment success rate down to 62% over the last 10 minutes" instead of "0 successful in the last 4 minutes". The effect cells were not used. `triage_herding` was left unchanged.
- The 62% wording still gave 8/8 escalations in `calm` for both models (gpt-oss always at tick 9). The real alert now reads "down to 91%", a smaller dip that is still serious. Baseline cells only were used. Target: 30-80% escalation in `calm`.
- Study list kept as llama-3.1-8b, gpt-oss-120b, claude-haiku-5-5. Baseline pilots on `calm` (91% alert) escalated 8/8 for gpt-oss-120b, gpt-oss-20b and granite-4-micro, 5/5 for glm-4.7-flash, 6/8 for llama-3.1-8b; apertus-8b returned 403 (not enabled on the account). gpt-oss-20b, granite-4-micro, apertus-8b and glm-4.7-flash stay in the registry as pilot-only keys. Granite made 4-8 calls per run before any alert. The write-up reports the ceiling.
