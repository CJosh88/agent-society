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
