# Agent Society Lab

Can a line of LLM agents triaging support tickets talk itself into mistakes, and does a stronger agent placed early pull the others back toward the truth? Agents work one after another on the same ticket queue. Each sees how many earlier agents rated each ticket HIGH, so every decision becomes part of the next agent's input. Every ticket has a known correct priority.

Design: [docs/designs/design.md](docs/designs/design.md) (v0.4, draft, not yet built).

## Statuss

`main` holds the v0.4 design and nothing else. The earlier study (alert fatigue and herding in triage, v0.3) is preserved with its code, replay viewer and API on the branch `v0.3-alert-fatigue-herding`. Milestones C0–C6 in the design doc rebuild the engine and API from that branch.

## Hypotheses (frozen before the batch runs)

- **H1 — influence lowers accuracy:** for each single-model population, world accuracy under `weak` and under `strong` influence is lower than under `independent`.
- **H2 — an early strong agent helps:** in `mix_early`, the weaker model's agents are more accurate than the same positions in the all-weaker world.
- **H3 — descriptive:** divergence from independent judgment, unpredictability across worlds, early-mover correlation and self-correction against the truth.
- **H4 — exploratory:** recovery after wrong seeding, selection effects, and persona Agreeableness.

The measures follow Hashemi et al., arXiv 2610.30769 (a preprint), adapted to a task with a ground truth.
