# Prior art check (milestone C0)

Run 2026-11-23, before building. Its job is to say how far the design doc's novelty claims can go. It is a handful of targeted searches plus reading the closest papers, not a literature review. Search tool coverage was US-only.

## Verdict

| Claim in the design | Verdict |
| --- | --- |
| Endogenous counts and parallel worlds with LLM agents | **Not new.** Hashemi et al. (2610.30769) did it on a taste task. This study adapts their design and measures. |
| Conformity to scripted peers with a known truth | **Not new.** Qu et al. (2606.01637), KAIROS (2508.18321) and Epistemic Context Learning (2601.21742) all use a ground truth, on question-answering tasks. |
| Mixed-model groups with a stronger model in a particular role | **Partly covered.** Han et al. (2601.05606) vary the hub model in 7-agent topologies, and ECL has one strong peer in a mixed group. Neither varies where a stronger agent sits in a long sequential line. |
| A long sequential line (200 agents) with endogenous counts, a known truth and a mixed line with controlled position, on ticket triage | **Not found** in these searches. A lead, not a proven gap. |
| Wrong seeding with a recovery measure against the truth | **Not found** as a recovery measure. All-wrong peers (Qu et al.) are the nearest condition. |
| RL training to resist social pressure | **Not new.** KAIROS (GRPO) and ECL (RL with an auxiliary reward) both do it. Stage 2 claims only a world-level, sequential, multi-seed evaluation. |
| LLM alert fatigue | **Not found.** Results were about human SOC and clinical alert fatigue and vendor claims about AI triage. Out of scope for this study. |

## Queries run

1. LLM agents sequential decisions information cascade ground truth heterogeneous models herding.
2. LLM alert fatigue, cry wolf, habituation, false alarms, escalation.
3. LLM triage anchoring on peer ratings, unanimous scripted colleagues, priority conformity.
4. Mixed-model multi-agent LLM population, stronger model early position, cascade correction.
5. Reinforcement learning, GRPO, train an LLM to resist conformity and social influence.

Earlier, in the research report (`reports/LLM agent game theory sandbox.md`), five survey tracks covered game-theory benchmarks, agent societies, cognitive psychology of LLMs, RL with LLM agents, and tooling.

## Papers opened

| Paper | Read | What it gave this design |
| --- | --- | --- |
| Hashemi, Ji, Chen, Macy, arXiv 2610.30769 (Oct 2026, preprint) | Full text (PDF text extracted; figures not seen) | The design pattern and the measures: KL divergence, unpredictability, early-mover correlation, self-correction. Its own limits: single-model populations, no communication or incentives, no recognition check. |
| Qu, Fu, Hu, arXiv 2606.01637 (Jun 2026, preprint) | Abstract and HTML v2; PDF not readable | Harmful and beneficial revision as a measure. All-wrong peers raise harmful revision from 15.6% to 62.9% against 32.7% to 51.5% for beneficial revision under all-correct peers, on four 7–9B open models. Peers are scripted, six at once, not sequential. |
| KAIROS, Song et al., arXiv 2508.18321 (v3 Dec 2025, preprint) | Abstract and about half the HTML | GRPO and SFT on Qwen2.5 (3B–14B) and Llama (3B, 8B) against scripted peers. Reports "robustness" as the change in accuracy between the original and peer-influenced settings, plus utility (wrong to right) and resistance (right to right). GRPO improved accuracy but did not always improve robustness. |
| Epistemic Context Learning, Zhou et al., arXiv 2601.21742 (Jan 2026, preprint) | Abstract and about 80% of the HTML | RL with a peer-recognition auxiliary reward on Qwen3-4B and 8B; the naive version of the auxiliary reward was hacked. Test sets are small (90 and 40 questions) and no variance is reported. |
| Han et al., arXiv 2601.05606 (Jan 2026, preprint) | Abstract and the first part of the HTML; the rest through a model summary | Seven agents, mixed GPT-3.5, GPT-4o and Llama groups. A stronger hub helps, and denser connectivity raises the risk of confident wrong consensus. |

## Seen only as search results (not opened)

- Jain and Krishnamurthy, arXiv 2411.01271: Bayesian social learning among LLM agents gives herding and information cascades in theory.
- Arghal et al., "Steering the Herd", arXiv 2504.02648: an LLM as information mediator in social learning.
- "Talk Isn't Always Cheap", arXiv 2509.05396: a weaker agent disrupts a stronger one in heterogeneous debate.
- Weng et al. (ICLR 2025), Zhu et al. (ACL 2025), Cho et al. (2025), Bellina et al. (2026), Hussain and Nielbo (2026): peer-answer conformity, cited second-hand in Hashemi et al.
- A news item reporting herding cascades in LLM multi-agent systems, with figures I could not trace to a paper. Not used.

## What this changed in the design

- The novelty paragraph in the Overview and the "Reading of the gap" paragraph were narrowed.
- The prior-art table gained Han, Qu, KAIROS, ECL and Jain and Krishnamurthy.
- A **harmful and beneficial revision** measure was added, adapted from Qu et al. and KAIROS and made possible by the paired world seeds.
- The Stage 2 section now states the overlap with KAIROS and ECL, reports robustness as the accuracy change under influence, and requires at least 3 training seeds.
- A risk row was added for the Stage 2 overlap.

## Still open

- Hashemi et al. figures were not seen, so per-model KL and unpredictability values are unconfirmed.
- Half of KAIROS and the rest of Han et al. were read through summaries.
- Whether the Hashemi et al. preprint is revised or published later is unknown. Cite it as a preprint.
