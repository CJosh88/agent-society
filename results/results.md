# Results

Experiment `cascade_v1`, prompt version `c1`. 112 worlds.
Every number is per population and condition. Intervals are 95% percentile bootstraps over worlds.

## World accuracy

| Population | Condition | Worlds | Mean accuracy | 95% interval | Parse failures per agent | False-HIGH | Missed-HIGH | Serious share of picks |
|---|---|---|---|---|---|---|---|---|
| llama-3.1-8b | independent | 8 | 0.734 | 0.730 to 0.738 | 0.016 | 0.621 | 0.061 | 0.633 |
| llama-3.1-8b | weak | 8 | 0.740 | 0.711 to 0.769 | 0.012 | 0.828 | 0.022 | 0.705 |
| llama-3.1-8b | strong | 8 | 0.650 | 0.621 to 0.682 | 0.007 | 0.767 | 0.138 | 0.664 |
| llama-3.1-8b | seeded_wrong | 8 | 0.482 | 0.462 to 0.505 | 0.013 | 0.855 | 0.164 | 0.488 |
| gpt-oss-120b | independent | 8 | 0.859 | 0.852 to 0.868 | 0.000 | 0.730 | 0.028 | 0.839 |
| gpt-oss-120b | weak | 8 | 0.973 | 0.958 to 0.984 | 0.000 | 0.217 | 0.009 | 0.928 |
| gpt-oss-120b | strong | 8 | 0.980 | 0.971 to 0.987 | 0.000 | 0.181 | 0.014 | 0.961 |
| gpt-oss-120b | seeded_wrong | 8 | 0.697 | 0.675 to 0.713 | 0.000 | 0.820 | 0.094 | 0.712 |
| mix_early | independent | 8 | 0.773 | 0.765 to 0.779 | 0.012 | 0.635 | 0.046 | 0.692 |
| mix_early | weak | 8 | 0.872 | 0.857 to 0.885 | 0.009 | 0.689 | 0.019 | 0.838 |
| mix_early | strong | 8 | 0.814 | 0.778 to 0.850 | 0.007 | 0.674 | 0.106 | 0.868 |
| mix_late | independent | 8 | 0.766 | 0.759 to 0.771 | 0.011 | 0.655 | 0.049 | 0.695 |
| mix_late | weak | 8 | 0.778 | 0.760 to 0.798 | 0.007 | 0.777 | 0.020 | 0.734 |
| mix_late | strong | 8 | 0.727 | 0.684 to 0.778 | 0.005 | 0.754 | 0.109 | 0.751 |

## H1 and H2

One-sided Mann-Whitney U, Holm over a family of 8.

| Hypothesis | Population | Condition | Contrast | Worlds | Difference | 95% interval | p | Holm p |
|---|---|---|---|---|---|---|---|---|
| H1 | llama-3.1-8b | weak | weak below independent | 8 v 8 | 0.006 | -0.024 to 0.035 | 0.644 | 1.000 |
| H1 | llama-3.1-8b | strong | strong below independent | 8 v 8 | -0.084 | -0.114 to -0.052 | <0.001 | 0.006 |
| H1 | gpt-oss-120b | weak | weak below independent | 8 v 8 | 0.114 | 0.096 to 0.128 | 1.000 | 1.000 |
| H1 | gpt-oss-120b | strong | strong below independent | 8 v 8 | 0.120 | 0.108 to 0.131 | 1.000 | 1.000 |
| H2 | mix_early | weak | positions 61+ above all-llama-3.1-8b | 8 v 8 | 0.091 | 0.056 to 0.126 | <0.001 | 0.002 |
| H2 | mix_early | strong | positions 61+ above all-llama-3.1-8b | 8 v 8 | 0.117 | 0.064 to 0.169 | 0.002 | 0.012 |

## Sensitivity: without worlds with parse failures in over 5% of agents

One-sided Mann-Whitney U, Holm over a family of 8.

| Hypothesis | Population | Condition | Contrast | Worlds | Difference | 95% interval | p | Holm p |
|---|---|---|---|---|---|---|---|---|
| H1 | llama-3.1-8b | weak | weak below independent | 8 v 8 | 0.006 | -0.024 to 0.035 | 0.644 | 1.000 |
| H1 | llama-3.1-8b | strong | strong below independent | 8 v 8 | -0.084 | -0.114 to -0.052 | <0.001 | 0.006 |
| H1 | gpt-oss-120b | weak | weak below independent | 8 v 8 | 0.114 | 0.096 to 0.128 | 1.000 | 1.000 |
| H1 | gpt-oss-120b | strong | strong below independent | 8 v 8 | 0.120 | 0.108 to 0.131 | 1.000 | 1.000 |
| H2 | mix_early | weak | positions 61+ above all-llama-3.1-8b | 8 v 8 | 0.091 | 0.056 to 0.126 | <0.001 | 0.002 |
| H2 | mix_early | strong | positions 61+ above all-llama-3.1-8b | 8 v 8 | 0.117 | 0.064 to 0.169 | 0.002 | 0.012 |

## Sensitivity: without worlds where the probe flagged recognition

One-sided Mann-Whitney U, Holm over a family of 8.

| Hypothesis | Population | Condition | Contrast | Worlds | Difference | 95% interval | p | Holm p |
|---|---|---|---|---|---|---|---|---|
| H1 | llama-3.1-8b | weak | weak below independent | 7 v 8 | 0.005 | -0.026 to 0.035 | 0.614 | 1.000 |
| H1 | llama-3.1-8b | strong | strong below independent | 7 v 7 | -0.087 | -0.120 to -0.049 | 0.002 | 0.011 |
| H1 | gpt-oss-120b | weak | weak below independent | 3 v 4 | 0.121 | 0.109 to 0.132 | 1.000 | 1.000 |
| H1 | gpt-oss-120b | strong | strong below independent | 3 v 5 | 0.120 | 0.105 to 0.134 | 1.000 | 1.000 |
| H2 | mix_early | weak | positions 61+ above all-llama-3.1-8b | 7 v 8 | 0.091 | 0.052 to 0.127 | <0.001 | 0.005 |
| H2 | mix_early | strong | positions 61+ above all-llama-3.1-8b | 8 v 7 | 0.120 | 0.062 to 0.173 | 0.002 | 0.014 |

## H3: measures from Hashemi et al.

| Population | Condition | KL from independent | Unpredictability | Early-mover correlation | Self-correction | Harmful revision | Beneficial revision |
|---|---|---|---|---|---|---|---|
| llama-3.1-8b | independent | 0.015 | 0.004 | 0.942 | -0.031 | n/a | n/a |
| llama-3.1-8b | weak | 0.130 | 0.012 | 0.896 | -0.013 | 0.006 | 0.002 |
| llama-3.1-8b | strong | 0.216 | 0.013 | 0.837 | -0.099 | 0.021 | 0.016 |
| llama-3.1-8b | seeded_wrong | 0.398 | 0.012 | -0.128 | 0.475 | 0.033 | 0.003 |
| gpt-oss-120b | independent | 0.013 | 0.005 | 0.920 | 0.037 | n/a | n/a |
| gpt-oss-120b | weak | 0.271 | 0.011 | 0.893 | 0.050 | 0.004 | 0.019 |
| gpt-oss-120b | strong | 0.430 | 0.025 | 0.914 | 0.051 | 0.005 | 0.018 |
| gpt-oss-120b | seeded_wrong | 0.558 | 0.023 | -0.050 | 0.485 | 0.035 | 0.021 |
| mix_early | independent | 0.015 | 0.005 | 0.903 | -0.238 | n/a | n/a |
| mix_early | weak | 0.175 | 0.011 | 0.942 | -0.164 | 0.002 | 0.014 |
| mix_early | strong | 0.295 | 0.020 | 0.725 | -0.219 | 0.012 | 0.009 |
| mix_late | independent | 0.012 | 0.004 | 0.922 | 0.244 | n/a | n/a |
| mix_late | weak | 0.176 | 0.010 | 0.868 | 0.151 | 0.006 | 0.003 |
| mix_late | strong | 0.269 | 0.015 | 0.812 | 0.080 | 0.031 | 0.015 |

No floor for the revision rates is reported: each cell has one run per world seed, so the independent worlds have no repeats to disagree with. Provider-default sampling makes the rates noisy.

## H4: exploratory

Recovery after wrong seeding: mean accuracy of positions after the scripted block.

| Population | Condition | Accuracy after the scripted block |
|---|---|---|
| llama-3.1-8b | independent | 0.734 |
| llama-3.1-8b | weak | 0.738 |
| llama-3.1-8b | strong | 0.643 |
| llama-3.1-8b | seeded_wrong | 0.536 |
| gpt-oss-120b | independent | 0.859 |
| gpt-oss-120b | weak | 0.976 |
| gpt-oss-120b | strong | 0.982 |
| gpt-oss-120b | seeded_wrong | 0.774 |

Accuracy by the persona's Agreeableness level, per condition (effect = condition minus independent).

| Population | Condition | Agreeableness | Accuracy | Effect |
|---|---|---|---|---|
| llama-3.1-8b | independent | low | 0.741 | n/a |
| llama-3.1-8b | independent | medium | n/a | n/a |
| llama-3.1-8b | independent | high | 0.727 | n/a |
| llama-3.1-8b | weak | low | 0.747 | 0.006 |
| llama-3.1-8b | weak | medium | n/a | n/a |
| llama-3.1-8b | weak | high | 0.733 | 0.006 |
| llama-3.1-8b | strong | low | 0.649 | -0.092 |
| llama-3.1-8b | strong | medium | n/a | n/a |
| llama-3.1-8b | strong | high | 0.651 | -0.076 |
| llama-3.1-8b | seeded_wrong | low | 0.477 | -0.263 |
| llama-3.1-8b | seeded_wrong | medium | n/a | n/a |
| llama-3.1-8b | seeded_wrong | high | 0.486 | -0.241 |
| gpt-oss-120b | independent | low | 0.857 | n/a |
| gpt-oss-120b | independent | medium | n/a | n/a |
| gpt-oss-120b | independent | high | 0.861 | n/a |
| gpt-oss-120b | weak | low | 0.973 | 0.116 |
| gpt-oss-120b | weak | medium | n/a | n/a |
| gpt-oss-120b | weak | high | 0.974 | 0.113 |
| gpt-oss-120b | strong | low | 0.981 | 0.124 |
| gpt-oss-120b | strong | medium | n/a | n/a |
| gpt-oss-120b | strong | high | 0.978 | 0.117 |
| gpt-oss-120b | seeded_wrong | low | 0.680 | -0.177 |
| gpt-oss-120b | seeded_wrong | medium | n/a | n/a |
| gpt-oss-120b | seeded_wrong | high | 0.712 | -0.149 |
| mix_early | independent | low | 0.780 | n/a |
| mix_early | independent | medium | n/a | n/a |
| mix_early | independent | high | 0.766 | n/a |
| mix_early | weak | low | 0.873 | 0.092 |
| mix_early | weak | medium | n/a | n/a |
| mix_early | weak | high | 0.871 | 0.105 |
| mix_early | strong | low | 0.812 | 0.032 |
| mix_early | strong | medium | n/a | n/a |
| mix_early | strong | high | 0.816 | 0.051 |
| mix_late | independent | low | 0.777 | n/a |
| mix_late | independent | medium | n/a | n/a |
| mix_late | independent | high | 0.756 | n/a |
| mix_late | weak | low | 0.787 | 0.010 |
| mix_late | weak | medium | n/a | n/a |
| mix_late | weak | high | 0.771 | 0.015 |
| mix_late | strong | low | 0.729 | -0.048 |
| mix_late | strong | medium | n/a | n/a |
| mix_late | strong | high | 0.725 | -0.031 |
