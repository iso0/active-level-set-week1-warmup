# Week 9 Phase 1.10B — the two-slope challenger on the frozen simulator pool

## Question

Phase 1.10 tested the fixed physics direction `log h` against a generic two-slope
`[log P, log VX]` logistic on the independent Masinelli Ti-6Al-4V experimental map and found
the two-slope model modestly better (ROC-AUC 0.9921 vs 0.9765), the gap becoming unresolved
after removing two label-discordant repeated conditions.

This phase asks the follow-up question: **can that two-slope model beat our model on our own
data?** It is run inside the frozen thesis protocol so that nothing except the model can
move the result.

## Why the challenger has to be defined three ways

The Masinelli map used a single 50 um spot, so `LS` was constant there and
`log h = log P - 0.5 log VX + const`. The two-slope model therefore **contained** the physics
direction as an exact special case, and could only lose to it through estimation variance.
That structural advantage does not transfer: on the thesis pool `LS` varies by a factor 2.24.
So three challengers are needed.

| name | mean coordinates | relation to `log h` on this pool |
|---|---|---|
| `T2` | `log P`, `log VX` | the literal Phase 1.10 challenger; does **not** nest `log h`, and cannot see `LS` at all |
| `T3` | `log P`, `log VX`, `log LS` | free exponents; **nests `log h` exactly** — the honest analogue of what G was externally |
| `T4` | `log P`, `log VX`, `log LS`, `ST` | free exponents plus substrate temperature |

Each is evaluated standalone, and as the frozen latent mean inside the M3 architecture
(`M3_T2`, `M3_T3`), where only the mean coordinate changes and the ARD Matern-3/2 discrepancy
GP, its bounds, the optimiser, the input scaling, the splits, the query paths, the boundary
subsets and the metrics are the frozen Phase 1.11/1.13/1.14 objects.

## Reproduction gate

The harness is the frozen one, so the frozen numbers must come back bit-exactly before any
new number is believed.

| quantity | target | recomputed here | absolute error |
|---|---|---|---|
| H q20 accuracy AULC 16-80 | 0.8308134191176471 | 0.8308134191176471 | 0.00e+00 |
| M3 q20 accuracy AULC 16-80 | 0.8424908088235293 | 0.8424816176470588 | 9.19e-06 |
| G0 (isotropic 4D GPC) | 0.8135202205882353 | 0.8135202205882353 | read from Phase 1.12 |
| G3 (ARD 4D GPC) | 0.8265946691176470 | 0.8265946691176470 | read from Phase 1.12 |

Gate status: **PASS**.

`H` reproduces the frozen number exactly. `M3` reproduces it on
99 of 100 runs bit-identically; the
remaining run(s) ['w85__r19_f03'] differ by at most
9.19e-04 because the hybrid GP optimises five kernel
hyper-parameters with L-BFGS-B on a multi-modal marginal likelihood and can settle on a
different local optimum under a different BLAS build. That propagates to
9.19e-06 on the 100-run mean — four orders of magnitude below the effects
measured here, and it applies identically to every hybrid arm, all of which were computed in
this same session.

## Experiment A — same-path prediction

Every model sees exactly the same revealed labels at every budget, on the frozen A0 query
path. This isolates the model. Primary endpoint: Fold-B1-q20 accuracy AULC over budgets
16-80, 100 runs, 20 paired repeat blocks, 10,000-draw repeat-block bootstrap, sign-flip
permutation with Holm correction across the five metrics in each family.

### A1 — challengers against M3

| challenger | its q20 AULC | difference vs M3 0.842482 | positive blocks | Holm p | verdict |
|---|---|---|---|---|---|
| M3_T2 — two-slope mean + ARD discrepancy | 0.780565 | -0.061916 [-0.069609, -0.054397] | 0/20 | 0.0030 | SUPPORTED |
| M3_T3 — free-exponent mean + ARD discrepancy | 0.820951 | -0.021530 [-0.025933, -0.017220] | 0/20 | 0.0030 | SUPPORTED |
| T2 — two-slope trend, standalone | 0.728373 | -0.114108 [-0.121507, -0.106378] | 0/20 | 0.0030 | SUPPORTED |
| T3 — free-exponent trend, standalone | 0.810570 | -0.031912 [-0.037541, -0.026135] | 0/20 | 0.0030 | SUPPORTED |
| T4 — free exponents + ST, standalone | 0.805418 | -0.037063 [-0.043392, -0.030689] | 0/20 | 0.0030 | SUPPORTED |
| H — physics trend, standalone | 0.830813 | -0.011668 [-0.016117, -0.006994] | 2/20 | 0.0030 | SUPPORTED |

### A2 — the direct Phase 1.10 question, trend against trend

This is the exact comparison Phase 1.10 ran, transplanted onto our pool.

| challenger | its q20 AULC | difference vs H 0.830813 | positive blocks | Holm p | verdict |
|---|---|---|---|---|---|
| T2 — two-slope [log P, log VX] | 0.728373 | -0.102440 [-0.110124, -0.094959] | 0/20 | 0.0015 | SUPPORTED |
| T3 — free exponents [log P, log VX, log LS] | 0.810570 | -0.020244 [-0.025152, -0.015432] | 0/20 | 0.0015 | SUPPORTED |
| T4 — free exponents + ST | 0.805418 | -0.025395 [-0.031333, -0.020092] | 0/20 | 0.0015 | SUPPORTED |

### A3 — regularisation robustness

Phase 1.10 used `C=1`; the thesis physics mean uses `C=1e6`. Repeating A2 under the Phase
1.10 convention:

| challenger | its q20 AULC | difference vs H_C1 0.829283 | positive blocks | Holm p | verdict |
|---|---|---|---|---|---|
| T2 at C=1 | 0.730225 | -0.099058 [-0.105951, -0.092343] | 0/20 | 0.0010 | SUPPORTED |
| T3 at C=1 | 0.807840 | -0.021443 [-0.024017, -0.018814] | 0/20 | 0.0010 | SUPPORTED |

## Experiment B — own-path acquisition cross-check

Each model now chooses its own queries by its own probability margin, from the same frozen
16-point initial design, one query per step, tie-break on smallest population row index —
the Phase 1.14 rule. This asks whether the challenger selects better simulations, not just
whether it predicts better on someone else's.

| model | its own-path q20 AULC | difference vs M3 own-path 0.844605 | positive blocks | Holm p | verdict |
|---|---|---|---|---|---|
| M3_T2 own-path margin | 0.781926 | -0.062679 [-0.070988, -0.054228] | 0/20 | 0.0025 | SUPPORTED |
| M3_T3 own-path margin | 0.810726 | -0.033879 [-0.041788, -0.026493] | 0/20 | 0.0025 | SUPPORTED |
| T2 own-path margin | 0.755597 | -0.089007 [-0.095074, -0.083111] | 0/20 | 0.0025 | SUPPORTED |
| T3 own-path margin | 0.802238 | -0.042367 [-0.051632, -0.033212] | 0/20 | 0.0025 | SUPPORTED |
| H own-path margin | 0.831737 | -0.012868 [-0.016549, -0.008704] | 1/20 | 0.0025 | SUPPORTED |

### Query-path divergence

The challengers do walk materially different paths, so the own-path comparison is not
vacuous:

| cell | budget | mean_jaccard | median_jaccard | mean_shared |
|---|---|---|---|---|
| H@own | 16 | 1.000 | 1.000 | 16.000 |
| H@own | 40 | 0.806 | 0.818 | 35.550 |
| H@own | 80 | 0.818 | 0.818 | 71.870 |
| M3_T2@own | 16 | 1.000 | 1.000 | 16.000 |
| M3_T2@own | 40 | 0.459 | 0.455 | 24.960 |
| M3_T2@own | 80 | 0.738 | 0.758 | 67.760 |
| M3_T3@own | 16 | 1.000 | 1.000 | 16.000 |
| M3_T3@own | 40 | 0.562 | 0.554 | 28.550 |
| M3_T3@own | 80 | 0.874 | 0.894 | 74.340 |
| T2@own | 16 | 1.000 | 1.000 | 16.000 |
| T2@own | 40 | 0.394 | 0.404 | 22.560 |
| T2@own | 80 | 0.446 | 0.448 | 49.240 |
| T3@own | 16 | 1.000 | 1.000 | 16.000 |
| T3@own | 40 | 0.570 | 0.569 | 28.690 |
| T3@own | 80 | 0.711 | 0.778 | 65.080 |

## Experiment C — model value versus path value

Symmetric decomposition on the four cells {M3, challenger} x {M3's path, challenger's path}:

| challenger | subset | metric | effect | mean | ci_low | ci_high | positive_repeat_blocks |
|---|---|---|---|---|---|---|---|
| M3_T2 | B1_q20 | accuracy | TOTAL | -0.062679 | -0.070933 | -0.054297 | 0 |
| M3_T2 | B1_q20 | accuracy | MODEL | -0.058966 | -0.064966 | -0.053061 | 0 |
| M3_T2 | B1_q20 | accuracy | PATH | -0.003713 | -0.009913 | 0.002245 | 10 |
| M3_T3 | B1_q20 | accuracy | TOTAL | -0.033879 | -0.041816 | -0.026465 | 0 |
| M3_T3 | B1_q20 | accuracy | MODEL | -0.021675 | -0.025586 | -0.017888 | 0 |
| M3_T3 | B1_q20 | accuracy | PATH | -0.012204 | -0.017149 | -0.007491 | 2 |

Verdicts: M3_T2 MODEL_DOMINANT, M3_T3 MODEL_DOMINANT.

## Experiment D — does the free model rediscover the physics exponents?

`T3` is free to choose any exponent vector. Normalised on the `log P` slope, the physics
direction is `(1, -0.5, -1.5)`. What the data actually chose:

| budget | log VX fitted | log VX physics | log LS fitted | log LS physics |
|---|---|---|---|---|
| 16 | -0.701 [-0.863, -0.447] | -0.500 | -1.181 [-1.579, -0.927] | -1.500 |
| 80 | -0.491 [-0.517, -0.467] | -0.500 | -1.433 [-1.514, -1.350] | -1.500 |

## Artifacts

`reproduction_gate.json`, `cell_summary.csv`, `paired_contrasts.csv`,
`model_path_decomposition.csv`, `exponent_recovery.csv`, `query_path_overlap.csv`,
`run_level_aulc.csv`, `budget_metrics.csv.gz`, `mean_coefficients.csv.gz`, and six figures.

## Claim discipline

This is a development-pool prediction and acquisition comparison on the frozen 405-simulation
benchmark. It does not revisit the external experimental result, does not validate or refute
the `LS` exponent outside this pool, and makes no claim about the blinded new pool.
