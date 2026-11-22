# Agent Society Lab

Can the context an LLM agent works in make it under-react to something that matters? One focal LLM agent works in a small shop in two scenarios. **Alert fatigue:** after 0, 3 or 6 false alarms, does the on-call agent still escalate a real payment alert? **Herding in triage:** when four scripted colleagues have all called a serious ticket low priority (or all high), does the agent follow them?

Design: [docs/designs/design.md](docs/designs/design.md)

## Hypotheses (frozen before the batch runs)

- **H1 — alert fatigue:** the focal agent escalates the real alert (a `CALL` at tick 9 or later) less often in `fatigue_6` than in `calm`.
- **H2 — herding:** the focal agent rates the ticket HIGH less often in `dismiss` than in `alone`.
- **H3 — latency (descriptive):** among runs with the outcome, it happens later in the condition expected to suppress it.
- **H4 — exploratory:** `fatigue_3` (dose), `endorse` against `alone`, false escalations, and differences by model, scenario and the persona's Agreeableness level.


## How it works

An outer LangGraph loop runs ticks 1 to 12. The focal agent's turn is a subgraph that perceives, decides (one LLM call), validates, and retries once if the reply is unusable. A deterministic game master applies every action and codes `counts_as_help`. Regenerate the diagram with `uv run asl graph`.

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	setup(setup)
	tick_start(tick_start)
	scripted_turns(scripted_turns)
	resolve(resolve)
	probe(probe)
	finish(finish)
	__end__([<p>__end__</p>]):::last
	__start__ --> setup;
	focal_turn\3a__end__ --> scripted_turns;
	probe --> finish;
	resolve -.-> probe;
	resolve -.-> tick_start;
	scripted_turns --> resolve;
	setup --> tick_start;
	tick_start -.-> focal_turn\3aperceive;
	tick_start -.-> scripted_turns;
	finish --> __end__;
	subgraph focal_turn
	focal_turn\3aperceive(perceive)
	focal_turn\3adecide(decide)
	focal_turn\3avalidate(validate)
	focal_turn\3a__end__(<p>__end__</p>)
	focal_turn\3adecide --> focal_turn\3avalidate;
	focal_turn\3aperceive --> focal_turn\3adecide;
	focal_turn\3avalidate -.-> focal_turn\3a__end__;
	focal_turn\3avalidate -.-> focal_turn\3adecide;
	end
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

## Architecture

```
laptop                                   VPS (Docker Compose)
------                                   --------------------
asl CLI (Python 3.12, LangGraph)         caddy -> api (Spring Boot 4.1, Java 21) -> postgres 16
   |  one RunBundle per run  --POST-->      |  static pages: index.html, replay.html (Phaser 3.90.0)
   |  LLM calls: Workers AI, Anthropic      |  read-only REST: /api/runs, /api/results
```

`contracts/run-bundle.schema.json` is the single contract between the two runtimes. Visitors never trigger LLM calls: the site only replays stored runs.

## Run it locally (no keys needed)

```bash
docker compose -f deploy/docker-compose.dev.yml up -d
cd api && ./mvnw -B verify && ./mvnw spring-boot:run      # API and pages on :8080
cd engine && uv run pytest
uv run asl batch --models fake --runs 3 --seed 0           # 18 fake runs
```

Open http://localhost:8080 and follow a run's Replay link. Fake runs are excluded from the results tables.

## Deploy

```bash
cp deploy/.env.example deploy/.env      # set DOMAIN, POSTGRES_PASSWORD and a 32+ character ASL_ADMIN_KEY
docker compose -f deploy/docker-compose.yml up -d --build     # locally, or on the server via:
deploy/deploy.sh user@host              # rsync to /opt/asl, then docker compose up -d --build
```

Caddy terminates HTTPS and proxies to the API; Postgres is never published. Certificates persist in the `caddy_data` volume.

## Credits

Replay sprites are Kenney's [Tiny Town](https://kenney.nl/assets/tiny-town) and [Tiny Dungeon](https://kenney.nl/assets/tiny-dungeon), released under CC0 (see `api/src/main/resources/static/img/CREDITS.txt`).
