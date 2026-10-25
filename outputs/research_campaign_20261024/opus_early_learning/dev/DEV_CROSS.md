# EL DEV stage: crossing selector and predictor on the recorded paths

Dated 2026-10-25. This is DEV evidence for mechanism and candidate choice, not a claim.

**Protocol:** `PROTOCOL_EL_OBJECTIVES.md` §7, registered and pushed in d13b70d5 before any result. Code: `src/el_cross.py` (job), `src/el_dev.py` (analysis), `src/el_eval.py` (metrics). Numbers: `DEV_CROSS.json`; tables: `*.csv`.

**Data:**
- STD repeats 51–58, 67–74, 75–82: 24 repeat clusters, 120 learners.
- k = 5 blocks with startups 1–24: 120 learners; 96 have a two-class test set.
- k = 4 blocks with startups 1–8: 32 learners.

**Computation:** `el-cross`, 464 units, 0 failed, 20:21–20:42 UTC, 3 single-thread workers.
- C (HA_TREND selects, HA_LEAN predicts) at every budget.
- D (HA_LEAN selects, HA_TREND predicts) on its missing budgets.
- A and B are the recorded own paths, not refitted.

**Checks:**
- C(8) = A(8) and D(8) = B(8) hold exactly (max |Δp| = 0.0).
- The recomputed D(12) equals the existing record exactly.
- An end-to-end rerun of both forward paths on STD r75 f1 reproduces the recorded paid IDs and all four prediction sets bit-exactly.

## 1. STD, individual learners

The primary view is individual learners; pooled values are shown beside them.

| system | BA-AULC B8–B24 (pooled) | B8–B60 (pooled) | BA at b = 8 / 12 / 16 / 24 / 40 / 60 | log loss B8–B60 | Brier |
|---|---|---|---|---|---|
| A: HA_LEAN selects / HA_LEAN predicts | 0.9338 (0.9334) | 0.9474 (0.9472) | 0.900 / 0.925 / 0.939 / 0.946 / 0.954 / 0.956 | 0.1452 | 0.0400 |
| B: HA_TREND selects / HA_TREND predicts | 0.9396 (0.9386) | 0.9488 (0.9483) | 0.915 / 0.940 / 0.942 / 0.947 / 0.954 / 0.958 | 0.1512 | 0.0406 |
| C: HA_TREND selects / HA_LEAN predicts | 0.9327 (0.9318) | 0.9478 (0.9474) | 0.900 / 0.933 / 0.938 / 0.946 / 0.956 / 0.960 | 0.1500 | 0.0410 |
| D: HA_LEAN selects / HA_TREND predicts | 0.9391 (0.9389) | 0.9482 (0.9480) | 0.915 / 0.936 / 0.942 / 0.945 / 0.953 / 0.955 | 0.1502 | 0.0406 |

### Targets, 120 learners

- **Attained:** confirmed at b and b + 4.
- **Spend:** b + 4, counting the 8 startup simulations.
- **RMS:** restricted-mean spend at horizon 60, with a non-attainer counted as 61. It is not a cost and not a bound.
- **Kept:** attained, and BA(60) ≥ target.

| system | 0.93 attained | 0.93 RMS | 0.93 kept | 0.95 attained | 0.95 RMS | 0.95 kept | 0.95 maintenance | 0.95 median spend |
|---|---|---|---|---|---|---|---|---|
| A | 119 | 17.12 | 108 | 100 | 28.43 | 79 | 0.773 | 21 |
| B | 119 | 17.06 | 112 | 94 | 29.84 | 78 | 0.793 | 18 |
| C | 119 | 18.18 | 111 | 104 | 28.24 | 88 | 0.771 | 21 |
| D | 120 | 16.38 | 105 | 102 | 27.47 | 78 | 0.731 | 20 |

### Paired against A

Mean over 24 repeat clusters, with one-sided 95 % bounds [LCB, UCB]. "+" means better than A; for RMS, + means fewer simulations.

| X − A | ΔBA-AULC B8–B24 | ΔBA-AULC B8–B60 | RMS saving 0.93 | RMS saving 0.95 | Δattain 0.95 | Δkept 0.95 | Δlog loss |
|---|---|---|---|---|---|---|---|
| B | +0.0058 [+0.0030, +0.0085], 17/24 | +0.0014 [+0.0002, +0.0026] | +0.07 [−1.62, +1.76] | −1.42 [−3.38, +0.54] | −0.050 [−0.097, −0.003] | −0.008 [−0.084, +0.067] | +0.0060 |
| C | −0.0011 [−0.0045, +0.0023] | +0.0004 | −1.06 [−2.44, +0.33] | +0.18 [−1.43, +1.80] | +0.033 [−0.006, +0.073] | +0.075 [−0.004, +0.154] | +0.0048 |
| D | +0.0053 [+0.0040, +0.0067], 22/24 | +0.0008 [+0.0001, +0.0014] | +0.75 [+0.03, +1.47] | +0.96 [−1.15, +3.07] | +0.017 [−0.024, +0.057] | −0.008 [−0.061, +0.044] | +0.0050 |

- **Attainment tables at 0.95** (both / X only / A only / neither): B 91 / 3 / 9 / 17; C 98 / 6 / 2 / 14; D 97 / 5 / 3 / 15.
- **Cumulative attainment of 0.95 by b = 16 / 24 / 40 / 60:**
  - A: 0.37 / 0.58 / 0.78 / 0.83;
  - B: 0.44 / 0.58 / 0.70 / 0.78;
  - C: 0.31 / 0.56 / 0.78 / 0.87;
  - D: 0.40 / 0.58 / 0.78 / 0.85.
- **D − A by budget:**
  - b = 8: +0.015;
  - b = 12: +0.011;
  - b = 16: +0.003;
  - b = 24 / 40 / 60: −0.001 / −0.001 / −0.001 (not different from 0).
  - The gain is concentrated in the first 8–16 simulations.

## 2. Model effect and path effect (2×2 on identical startups)

| effect | ΔBA-AULC B8–B24 | RMS saving 0.93 | RMS saving 0.95 |
|---|---|---|---|
| model on the HA_LEAN path (D − A) | +0.0053 [+0.0040, +0.0067], 22/24 | +0.75 [+0.03, +1.47] | +0.96 [−1.15, +3.07] |
| model on the HA_TREND path (B − C) | +0.0069 [+0.0046, +0.0092], 23/24 | +1.12 [+0.08, +2.17] | −1.60 [−3.12, −0.08] |
| path for the HA_LEAN predictor (C − A) | −0.0011 [−0.0045, +0.0023] | −1.06 [−2.44, +0.33] | +0.18 [−1.43, +1.80] |
| path for the HA_TREND predictor (B − D) | +0.0004 [−0.0024, +0.0033] | −0.68 [−2.13, +0.76] | −2.38 [−4.90, +0.15] |
| interaction (B − C) − (D − A) | +0.0015 [−0.0011, +0.0042] | +0.38 [−0.77, +1.52] | −2.56 [−5.08, −0.04] |

**Reading:**
- The early gain is a prediction (model) effect: on either path, the HA_TREND predictor is better in the first 8–24 simulations.
- The query path adds nothing early.
- For the 0.95 target, the HA_TREND-selected path is worse for the HA_TREND predictor (−2.4 simulations, interaction −2.6). B therefore loses at 0.95 what its predictor gains early, while D keeps the predictor and the HA_LEAN path.

**Paths:**
- **Divergence:** the two selectors choose a different simulation already at the first query (query 9) in every learner.
- **Overlap:** 12.8 of the first 24 runs are shared (8 of them the startup), and 51.5 of the first 60.
- **Corner:** both put about 42–45 % of their queries in the 7 % label-interleaved corner (RC21 definition, evaluator-only): HA_LEAN 45 %, HA_TREND 42 %.

**CPU per step** (process seconds, STD):

| system | cost |
|---|---|
| A | 0.20 |
| B | 0.25 |
| C (HA_TREND fit for the choice + HA_LEAN fit for the prediction) | 0.43 |
| D (HA_LEAN fit + HA_TREND fit) | 0.36, i.e. 1.8 × A |

## 3. Robustness: reported, not part of any rule

**Blocks.** Pooled BA-AULC B8–B60 against A:
- k = 5: B +0.012, D +0.011, C −0.002;
- k = 4: B +0.025, D +0.022, C −0.003.

Per region (mean over the two-class blocks, per startup) against A:

| per-region BA-AULC B8–B60 | k = 5 (24 startups) | k = 4 (8 startups) |
|---|---|---|
| B | −0.035 [LCB −0.047] | +0.031 [LCB +0.010] |
| C | −0.001 | +0.008 |
| D | −0.043 [LCB −0.053], **warning level** | +0.036 [LCB +0.013] |

- This is the partition-dependent pattern of the RC24 post-audit.
- On the old five regions, kept(0.95) falls for B and D: 10/96 and 6/96 against 24/96. Most block learners never reach 0.95: their minorities hold 1–17 runs.

**Short-Keyhole hard group** (pooled, RC24 definition, evaluator-only): BA_hard at B60:

| A | B | C | D |
|---|---|---|---|
| 0.642 | 0.628 | 0.649 | 0.625 |

No system resolves the hard group.

## 4. Registered candidate rule

**Candidate choice:**
- The largest ΔBA-AULC B8–B24 is B's (+0.0058).
- D is within 0.001 (+0.0053), so the 0.95 restricted-mean saving decides: D +0.96 against B −1.42.
- **Candidate: D, "HA_LEAN selects, HA_TREND predicts".**

**"The fixed crossing is enough"** (point estimates): it holds.

| condition | D | A | result |
|---|---|---|---|
| early gain | +0.0053 | – | > 0 ✓ |
| RMS savings at 0.93 / 0.95 | +0.75 / +0.96 | – | both > 0 ✓ |
| attainment(0.95) | 0.850 | 0.833 | not lower by > 0.025 ✓ |
| kept(0.95) | 0.650 | 0.658 | not lower by > 0.025 ✓ |

**Consequence:** stage 2 (a new mechanism) is not entered, as registered. No new mechanism was built or tried.
- A natural idea was noted and not pursued: since D's gain is early and A is equal or slightly better from b = 24 on, a paid-data-weighted combination of the two predictors.
- Pursuing it would have required stage 2, which the registered rule did not open.

**D against B** (secondary):
- early −0.0004 [−0.0033, +0.0024];
- RMS saving at 0.95 +2.38 [−0.15, +4.90];
- attainment(0.95) +0.067 [+0.027, +0.106].

At equal early BA, D reaches 0.95 in more learners than B.

## 5. What this DEV stage supports, and what it does not

**Supports:**
- In random splits of this pool, the early-learning gain of HA_TREND comes from its predictions, not from its query choices.
- Keeping HA_LEAN as the selector and reporting HA_TREND's predictions keeps the early gain. On DEV it turns it into a small single-learner saving at 0.93 (+0.75 simulations, LCB +0.03) and a possible one at 0.95 (+0.96, wide interval).

**Does not support:**
- a large saving;
- a better kept / maintenance rate (D 0.731 against A 0.773);
- any benefit within the old five regions under geometric extrapolation.

The forward test on fresh repeats (`PROTOCOL_EL_FINAL.md`) decides.
