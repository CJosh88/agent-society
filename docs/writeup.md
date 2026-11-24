# Can a line of LLM agents talk itself into mistakes?

_Skeleton. Fill in after the Stage 1 batch; every number comes from `results/results.md`._

## Question

A line of 200 agents works through a 24-ticket support queue one after another. Each agent sees how many earlier agents rated each ticket HIGH, picks 4 tickets and rates them. The truth is known (12 serious, 12 routine). Does seeing the counts lower the line's accuracy, and does a stronger model at the start of the line help the weaker ones after it?

## Design

- Conditions: `independent`, `weak`, `strong`, `seeded_wrong`. Populations: Llama 3.1 8B, gpt-oss-120b, Claude Haiku 5.5 (if run), `mix_early`, `mix_late`.
- 8 paired worlds per cell, 144 in total. Pre-registered in the signed tag `prereg-c1`.
- Measures from Hashemi et al. (arXiv 2610.30769), plus harmful and beneficial revision.
- Prior art and what is not new: `docs/prior-art.md`.

## Results

_H1 (influence lowers accuracy), per population:_ TODO

_H2 (an early strong agent helps the weaker agents after it):_ TODO

_H3 (divergence, unpredictability, early-mover correlation, self-correction):_ TODO

_H4 (recovery after wrong seeding, selection, Agreeableness):_ TODO

_Sensitivity (parse failures, recognition):_ TODO

## Limits

- 8 worlds per cell: only large effects are detectable (see the power note in `docs/designs/decisions.md`).
- Providers' default sampling, so reruns are not identical; every prompt and response is stored for audit.
- Scripted persona text and ticket wording were tuned on `independent` pilots only.
- One task, one ticket catalogue, one prompt version.
- Haiku: _state whether it was run_.

## What surprised me

TODO
