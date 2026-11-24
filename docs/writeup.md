# Can a line of LLM agents talk itself into mistakes?

Stage 1 results. Every number below comes from `results/results.md`, which `asl analyze` generated from the 112 study worlds. The run is `cascade_v1`, prompt version `c1`, pre-registered in the tag `prereg-c1`.

**Short answer.** Mostly no. Showing earlier ratings hurt the weaker model only when the list was sorted by votes, and it made the stronger model much better. What did do damage was wrong ratings planted at the front of the line. A strong model at the front helped the weaker agents after it.

## Question

A line of 200 agents works through a 24-ticket support queue one after another. Twelve tickets are serious and twelve are routine, and the truth is known. Each agent sees how many earlier agents rated each ticket HIGH, picks 4 tickets and rates each HIGH or LOW. Does seeing the counts lower the line's accuracy? Does a strong model at the start of a mixed line help the weaker agents after it?

## Design

- **Conditions:** `independent` (no counts), `weak` (counts shown), `strong` (counts shown, list sorted by HIGH share) and `seeded_wrong` (the first 20 agents are scripted to be wrong).
- **Populations:** Llama 3.1 8B, gpt-oss-120b, `mix_early` (gpt-oss-120b for the first 60 agents, Llama for the rest) and `mix_late` (the reverse). Claude Haiku was not run, because no Anthropic key was loaded.
- **Worlds:** 8 per cell with world seeds 0–7 shared by every cell, so conditions differ only in the information shown. That is 112 worlds, about 22,400 agent turns.
- **Measures:** world accuracy is the primary outcome. The rest follow Hashemi et al. (arXiv 2610.30769), plus harmful and beneficial revision.
- **Tests:** H1 and H2 are one-sided Mann–Whitney tests on world accuracy, 8 worlds against 8, with Holm correction over a family of 8.
- **Calibration:** ticket wording was tuned on `independent` pilots only, to put baseline accuracy between 55% and 95%. Prior art and what is not new: `docs/prior-art.md`.

## Results

### World accuracy

The `seeded_wrong` column counts every rating in the world, including the 20 scripted agents' deliberately wrong ones (10% of all ratings), so it understates accuracy for the real agents. The recovery numbers under H4 leave the scripted block out.

| Population | independent | weak | strong | seeded_wrong |
|---|---|---|---|---|
| Llama 3.1 8B | 73.4% | 74.0% | 65.0% | 48.2% |
| gpt-oss-120b | 85.9% | 97.3% | 98.0% | 69.7% |
| `mix_early` | 77.3% | 87.2% | 81.4% | not run |
| `mix_late` | 76.6% | 77.8% | 72.7% | not run |

### H1: influence lowers accuracy (mostly not supported)

| Population | Condition | Change from `independent` | Holm p |
|---|---|---|---|
| Llama | `weak` | +0.6 points | 1.0 |
| Llama | `strong` | −8.4 points (interval −11.4 to −5.2) | 0.006 |
| gpt-oss-120b | `weak` | +11.4 points | 1.0 |
| gpt-oss-120b | `strong` | +12.0 points | 1.0 |

H1 had 4 tests, not 6, because Haiku was not run. Only Llama under `strong` fell. For gpt-oss-120b the p-values of 1.0 only mean the test, which looks for a drop, found none. Accuracy rose by about 11–12 points with intervals well above zero.

**Why gpt-oss-120b improves.** Alone, it rates 73% of routine tickets HIGH. With counts, that falls to 22% (`weak`) and 18% (`strong`), and the share of its picks that are serious rises from 84% to 93% and 96%. It reads a low count as evidence that a ticket is not serious. I read this as sensible use of information, not herding.

### H2: an early strong agent helps (supported)

In `mix_early`, the Llama agents at positions 61–200 were more accurate than the same positions in the all-Llama world: +9.1 points under `weak` (Holm p = 0.002) and +11.7 points under `strong` (Holm p = 0.012). The matching `mix_late` contrast is reported but not tested.

### H3: the Hashemi measures

- **Divergence from independent judgment** (KL) grows once counts appear: Llama 0.015 (`independent`), 0.130 (`weak`), 0.216 (`strong`), 0.398 (`seeded_wrong`). gpt-oss-120b: 0.013, 0.271, 0.430 and 0.558.
- **Unpredictability across worlds** is small everywhere (0.004 to 0.025), highest for gpt-oss-120b under `strong` and `seeded_wrong`.
- **Early-mover correlation** is about 0.9 even with no counts, because ticket content drives it, so it does not separate the conditions. It turns negative under `seeded_wrong` (−0.13 for Llama, −0.05 for gpt-oss-120b): later agents disagree with the wrong early ratings.
- **Self-correction** is strongly positive under `seeded_wrong` (+0.48 for both), which means later agents move toward the truth.
- **Harmful and beneficial revision** are small: for gpt-oss-120b under `weak`, 0.4% harmful against 1.9% beneficial. For Llama under `strong`, 2.1% against 1.6%.

### H4: exploratory

- **Recovery after wrong seeding.** Looking only at the agents after the 20 planted ones, accuracy stays below the unseeded worlds. Llama: 53.6% against 73.4% in `independent` and 73.8% in `weak`. gpt-oss-120b: 77.4% against 85.9% in `independent` and 97.6% in `weak`. Later agents do move toward the truth (self-correction +0.48), but not all the way back. For gpt-oss-120b, the wrong early ratings cost about 20 points against the same condition with honest early ratings, and even fall below working alone.
- **Selection** moves together with rating: the serious share of picks changes in the same direction as accuracy.
- **Agreeableness** shows no visible effect. Agents with low and high Agreeableness are within about 1 point everywhere. The persona set only has low and high levels.

### Sensitivity

Dropping worlds with parse failures in over 5% of agents changes nothing, because no world is that high. Dropping worlds where the probe flagged recognition leaves all conclusions unchanged.

## Limits

- **8 worlds per cell.** Differences of about 3 points or more are detectable if the spread between worlds stays near the pilot's (about 1.5 points). Smaller effects would be missed (see the power note in `docs/designs/decisions.md`).
- **Haiku was not run,** so there are two single-model populations and 4 H1 tests.
- **The recognition probe over-counts.** It flagged 29 of 1,000 sampled answers. Nine were the word "cascade" in its ordinary sense ("a cascade of problems") and 20 were agents calling the task a "simulated support-desk exercise", mostly gpt-oss-120b and also in worlds with no counts shown. None named herding, conformity or the role of the counts. The flagged answers are in `results/flagged-probes.json`. The matcher is part of the frozen code and was not changed.
- **No floor for the revision rates.** Each cell has one run per world seed, so there are no repeats to measure run-to-run disagreement.
- **Network drops interrupted the batch twice.** It was resumed; I fixed retries for dropped connections and made `asl batch` skip worlds the API already holds. Both changes came after the tag and touched no prompts, tickets, personas or pairing (`docs/designs/decisions.md`). The failure logs are `results/failures-attempt1.jsonl` and `results/failures-attempt2.jsonl`.
- **Providers' default sampling,** so reruns are not identical. Every prompt and response is stored for audit.
- **One task, one ticket catalogue, one prompt version.** Persona wording and ticket text were chosen by me.
- **Planted errors are artificial.** The `seeded_wrong` worlds show what wrong early ratings do. They do not show how often such errors arise naturally. Whole-world accuracy in those worlds includes the scripted agents' wrong ratings, so use the after-the-block numbers.
- **Local results only.** The public site on the VPS still holds the older data until it is redeployed.

## What surprised me

The pre-registered hypothesis was that visible ratings pull agents toward each other and lower accuracy. For the stronger model the opposite happened: it was less accurate working alone, because it over-rated routine tickets as HIGH, and the counts corrected that. The H1 test was one-sided, so the p-values of 1.0 for gpt-oss-120b hide an 11–12 point gain. The interval on the difference shows it.

The other surprise was how much the front of the line matters. Twenty wrong ratings at the front of 200 cost the agents after them about 20 points under counts (gpt-oss-120b: 98% with honest early ratings, 77% after the planted block). A strong model at the front lifted the weaker agents after it by 9 to 12 points.
