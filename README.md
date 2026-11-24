# Agent Society Lab

Can a line of LLM agents triaging support tickets talk itself into mistakes, and does a stronger agent placed early pull the others back toward the truth? Agents work one after another on the same ticket queue. Each sees how many earlier agents rated each ticket HIGH, so every decision becomes part of the next agent's input. Every ticket has a known correct priority.

Design: [docs/designs/design.md](docs/designs/design.md) (v0.4). Prior-art check: [docs/prior-art.md](docs/prior-art.md).

## Status

Built so far (milestones C0–C3): the contract and fixtures, the Spring API, the Python engine with a fake model, and the results and replay pages. No real model has been run yet. Pilots, calibration and pre-registration (C4), the Stage 1 batch and analysis (C5) and the RL stage (C6) are next. The earlier study (alert fatigue and herding in triage, v0.3) is preserved on the branch `v0.3-alert-fatigue-herding`.

## How to run it (fake model, no keys)

```bash
docker compose -f deploy/docker-compose.dev.yml up -d          # Postgres
cd api && ./mvnw spring-boot:run                               # API and pages on :8080
cd engine && uv run pytest                                     # engine tests
ASL_API_URL=http://localhost:8080 ASL_ADMIN_KEY=dev-admin-key-change-me-00000000   uv run asl batch --models fake --runs 2 --seed 0 --agents 20   # 8 small worlds
```

Then open `http://localhost:8080/`. `cd api && ./mvnw -B verify` needs Docker running (Testcontainers).

## Hypotheses (frozen before the batch runs)

- **H1 — influence lowers accuracy:** for each single-model population, world accuracy under `weak` and under `strong` influence is lower than under `independent`.
- **H2 — an early strong agent helps:** in `mix_early`, the weaker model's agents are more accurate than the same positions in the all-weaker world.
- **H3 — descriptive:** divergence from independent judgment, unpredictability across worlds, early-mover correlation and self-correction against the truth.
- **H4 — exploratory:** recovery after wrong seeding, selection effects, and persona Agreeableness.

The measures follow Hashemi et al., arXiv 2610.30769 (a preprint), adapted to a task with a ground truth.
