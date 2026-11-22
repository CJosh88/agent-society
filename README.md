# Agent Society Lab

Does an LLM agent stop acting on a problem when passive bystanders are present, and does a named owner role restore action? One focal LLM agent shares a scene with 4 scripted, always-passive people, in a town square (a person collapses) or an office (a payments dashboard turns red).

Design: [docs/designs/design.md](docs/designs/design.md)

## Hypotheses (frozen before the batch runs)

- **H1 — diffusion:** the focal agent helps less often in `group5` than `alone`.
- **H2 — ownership:** the focal agent helps more often in `group5_owner` than in `group5`.
- **H3 — latency (descriptive):** among runs where the focal agent helps, it helps later in `group5` than `alone`.
- **H4 — exploratory:** effects differ by model, by scenario and by the persona's Agreeableness level.

Status: M0 (contracts and skeleton). More sections arrive in M3 and M4.
