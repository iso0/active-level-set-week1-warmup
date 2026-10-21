# RC24 synthetic benchmark: test-family pre-registration

Registered before any test-family world is run.

**Development evidence used.** The development families D1–D6 (seeds 1–4) were run and evaluated in `S-DEV.md`. They were used for two things only:
- to check that the pipeline runs end to end;
- to fix the block-selection rule. A test block must have at least 15 runs of each class; the block whose positive rate is closest to the world's rate is chosen.

Effects on the development families were small and noisy (per-family standard errors of 0.005–0.04 in BA-AULC). The test families therefore use **10 seeds (101–110)**.

**Test families.** T1–T8, defined in `src/rc24_synth.py::FAMILIES`. Their parameter values differ from those of every development family.

**Arms.** HONLY_MARGIN, HA_LEAN_MARGIN, HA_TREND_MARGIN, PAC_MARGIN.

**Splits.**
- std: random 80/20 split.
- block: k-means geometry block.

**Metric.** BA-AULC over B8–B60 and B8–B24 per world and split. One learner is fitted per world. The comparison is the paired difference over the 10 seeds: mean, standard error and number of positive seeds.

## Hypotheses (directional; descriptive labels, not used to change any real-data claim)

| ID | families | prediction | supported if |
|---|---|---|---|
| S1 | T1 (anchor right), T2 (anchor 25° off) | the physics anchor helps under extrapolation | block split, B8–B60: HA_TREND − HA_LEAN mean > 0 in ≥ 7/10 seeds, in both families |
| S2 | T3 (anchor 70° off), T4 (anchor useless) | an estimated anchor costs little when it is wrong or useless | std and block, B8–B60: HA_TREND − HA_LEAN mean ≥ −0.010 in both families |
| S3 | T5 (depth irrelevant to the label) | complexity does not pay | std, B8–B60: HONLY − HA_LEAN mean ≥ −0.005 (h-only at least as good) |
| S4 | T6 (label structure beyond h and depth), T7 (balanced, noisy) | no general ranking reversal | HA_TREND − HA_LEAN within ±0.010 in std, B8–B60 |
| S5 | T8 (aleatoric corner, anchor 45° off) | margin wastes queries in the corner for every learner | reported only: the share of queries in the corner region per arm |

All results are reported, whatever their direction.
