# Week 9 Phase 2.1R — final report
## The simple width-change control

1. **Ioan suggested** checking whether the way the melt-pool width changes over time carries Keyhole
   information.
2. **The simplest version of that** is the change between one analysis point and the next:
   `delta_W = W(i+1) - W(i)`. If the width is 20 µm at one point and 30 µm at the next, `delta_W = +10`;
   if it then goes 30 → 33 that is `+3`, and 33 → 31 is `-2`. A simulation's whole story becomes a short
   list like `[+10, +3, -2, ...]`.
3. **First question:** do big width jumps on their own separate Keyhole from Conduction?
4. **Second question:** does adding that information to the ordinary 4D process-input GPC
   (`[P, VX, LS, ST]`) make predictions better?
5. **Third question:** how do these models compare against **M3**, the current strong model
   (physics logistic mean on `log h` plus an ARD Matérn-3/2 discrepancy GP)?
6. **This is a predictive feature-value experiment, not a new active-learning acquisition experiment.**

## One thing to be strict about

The width series used here lives on the Phase 2 resampled grid. Its points are **consecutive resampled
analysis points**, not raw solver timesteps. The raw SPH monitors have about 75,000 steps per simulation
at dt ≈ 0.018 µs, where the step-to-step width change is boundary jitter (typical step ≈ 0.005 µm, and
the width *decreases* on about 51% of raw steps). A "largest raw one-step increase" would measure the
biggest numerical artifact in 75,000 steps, not melt-pool growth. At 201 analysis points
the gap is ≈ 6.8 µs and a 20 → 30 µm change is a real physical event. Because that resolution is a
choice, everything headline is recomputed at **51, 101 and 201** points and only called robust if it
survives all three.


## What we built

350 of 405 simulations have a usable transverse-width trace (70 Keyhole,
280 Conduction). Each contributes 200 consecutive-point transitions,
giving a transition-level table of 70,000 rows. That table is for feature building and pictures
only — **the label is a property of the simulation, not of a transition**, so every train/test split
stays grouped at the simulation level on the 100 frozen Week 8.5 folds.

| feature | what it is | worked example |
|---|---|---|
| `max_positive_delta_W` | largest increase in transverse width between two consecutive resampled analysis points | sequence [+10, +3, -2, +1] -> the biggest rise is +10, so max_positive_delta_W = 10 |
| `min_delta_W` | most negative transition, i.e. the largest single contraction | sequence [+10, +3, -2, +1] -> the most negative entry is -2, so min_delta_W = -2 |
| `median_positive_delta_W` | median of only the transitions where the width grew | positives are [+10, +3, +1]; their median is 3, so median_positive_delta_W = 3 |
| `fraction_positive_delta_W` | share of transitions in which the width increased | 3 of the 4 transitions are positive, so fraction_positive_delta_W = 0.75 |
| `total_positive_delta_W` | sum of every increase, i.e. total growth ignoring the shrinking steps | 10 + 3 + 1 = 14, so total_positive_delta_W = 14 |
| `max_positive_width_rate` | largest increase divided by the time gap it happened in (um per ms) | if the +10 um rise took 0.0068 ms then max_positive_width_rate = 10 / 0.0068 = 1471 um/ms |
| `median_positive_width_rate` | median of the positive rises after each is divided by its own time gap | the positive rises [+10, +3, +1] become rates, and we take the middle one |
| `fraction_positive_width_rate` | share of transitions with a positive rate -- identical to fraction_positive_delta_W because every time gap is positive, so dividing by it cannot flip a sign | 3 of 4 positive -> 0.75, exactly the same number as fraction_positive_delta_W |

`fraction_positive_width_rate` is mathematically identical to `fraction_positive_delta_W`: every time gap
is positive, so dividing by it can never flip a sign. It is reported once and not double-counted.

## Question 1 — do big width jumps separate the two regimes at all?

Whole-sample and descriptive (the leak-free version is the next section).

| feature | Conduction median | Keyhole median | difference [95% CI] | Cliff's δ | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|
| `max_positive_delta_W` | 29.82 | 29.27 | -0.5445 [-2.886, +0.6716] | -0.204 | 0.398 | 0.168 |
| `min_delta_W` | -6.504 | -4.323 | +2.181 [+1.278, +3.081] | +0.159 | 0.580 | 0.245 |
| `median_positive_delta_W` | 0.4989 | 0.4578 | -0.04115 [-0.0799, +0.01738] | -0.086 | 0.457 | 0.201 |
| `fraction_positive_delta_W` | 0.5375 | 0.5325 | -0.005 [-0.0175, +0.02] | +0.000 | 0.500 | 0.215 |
| `total_positive_delta_W` | 220.1 | 207.7 | -12.44 [-22.28, +11.3] | +0.001 | 0.500 | 0.230 |
| `max_positive_width_rate` | 4682 | 3551 | -1131 [-1588, -446.4] | -0.300 | 0.350 | 0.156 |
| `median_positive_width_rate` | 75.44 | 65.92 | -9.526 [-15.04, -4.941] | -0.244 | 0.378 | 0.167 |
| `fraction_positive_width_rate` | 0.5375 | 0.5325 | -0.005 [-0.02, +0.02] | +0.000 | 0.500 | 0.215 |

**`max_positive_delta_W`: 29.27 µm for Keyhole against
29.82 µm for Conduction, Cliff's δ = -0.204,
ROC-AUC = 0.398.**

## Question 2 — does a simple threshold rule work?

The rule is literally `if max_positive_delta_W > threshold: predict Keyhole`. The threshold is chosen to
maximise balanced accuracy **on the training simulations of each fold**, then frozen and applied to the
held-out simulations. No global threshold is ever tuned on all labels.

| feature | region | learned threshold, median [IQR] | balanced accuracy | Keyhole recall | feature ROC-AUC | feature PR-AUC |
|---|---|---|---|---|---|---|
| `max_positive_delta_W` | full | 32.41 [32.41, 32.41] | 0.6239 ± 0.0083 | 0.9218 | 0.6013 | 0.3156 |
| `max_positive_delta_W` | q20 | 32.41 [32.41, 32.41] | 0.5643 ± 0.0247 | 0.8661 | 0.4768 | 0.4545 |
| `max_positive_delta_W` | q30 | 32.41 [32.41, 32.41] | 0.5714 ± 0.0190 | 0.8795 | 0.4806 | 0.3819 |
| `max_positive_width_rate` | full | 3846 [3556, 4556] | 0.5815 ± 0.0166 | 0.5253 | 0.6493 | 0.3992 |
| `max_positive_width_rate` | q20 | 3846 [3556, 4556] | 0.4334 ± 0.0420 | 0.3644 | 0.4417 | 0.4770 |
| `max_positive_width_rate` | q30 | 3846 [3556, 4556] | 0.4439 ± 0.0377 | 0.3717 | 0.4397 | 0.4111 |

## Question 3 — does dividing by the real time gap change anything?

Raw `delta_W` gives Cliff's δ = -0.204; the time-normalised
`max_positive_width_rate` gives -0.300. On the q20 band the leak-free threshold
rule scores 0.564 on raw ΔW and
0.433 on the rate. Note *why* the two are so close: on this grid
the gap between consecutive analysis points is constant **within** a simulation (duration ÷
200), so dividing by it rescales a whole simulation by one number and only changes
how simulations compare **to each other**, never the shape inside one.

## Question 4 — does simple width change help the 4D GPC?

Every model below is the Phase 1.12 winner, ARD Matérn-3/2 GPC, on `StandardScaler`-scaled inputs fitted
inside each training fold. Only the feature list changes.

| model | features | bal. acc | accuracy | Keyhole recall | ROC-AUC | PR-AUC | Brier | full-set bal. acc |
|---|---|---|---|---|---|---|---|---|
| `gpc_4d` | 4 | 0.8739 | 0.8836 | 0.8288 | 0.9244 | 0.8769 | 0.1009 | 0.9531 |
| `gpc_4d_plus_max_delta_W` | 5 | 0.8830 | 0.8889 | 0.8555 | 0.9325 | 0.8914 | 0.0989 | 0.9571 |
| `gpc_4d_plus_max_width_rate` | 5 | 0.8646 | 0.8692 | 0.8425 | 0.9240 | 0.8789 | 0.1039 | 0.9522 |
| `gpc_4d_plus_simple_delta_block` | 7 | 0.8773 | 0.8844 | 0.8453 | 0.9313 | 0.8926 | 0.1000 | 0.9548 |
| `gpc_4d_plus_simple_rate_block` | 7 | 0.8611 | 0.8659 | 0.8389 | 0.9223 | 0.8818 | 0.1057 | 0.9517 |
| `gpc_4d_plus_old_shape3` | 7 | 0.8808 | 0.8869 | 0.8524 | 0.9334 | 0.8986 | 0.0994 | 0.9570 |
| `gpc_4d_plus_old_full8` | 12 | 0.8626 | 0.8700 | 0.8276 | 0.9268 | 0.8921 | 0.1059 | 0.9482 |
| `m3` | 4 | 0.8464 | 0.8647 | 0.7618 | 0.9157 | 0.8247 | 0.1095 | 0.9362 |
| `m3_plus_max_delta_W` | 5 | 0.8656 | 0.8798 | 0.7991 | 0.9295 | 0.8367 | 0.1003 | 0.9436 |

### The primary contrast: `gpc_4d_plus_max_delta_W - gpc_4d` on q20

| metric | direction | mean difference [95% CI] | sign-flip p | Holm p | verdict |
|---|---|---|---|---|---|
| accuracy | higher is better | +0.0053 [-0.0039, +0.0139] | 0.2266 | 0.2372 | **NO DETECTABLE DIFFERENCE** |
| balanced accuracy | higher is better | +0.0091 [-0.0016, +0.0197] | 0.1186 | 0.2372 | **NO DETECTABLE DIFFERENCE** |
| keyhole recall | higher is better | +0.0267 [+0.0083, +0.0448] | 0.0152 | 0.0608 | **NO DETECTABLE DIFFERENCE** |
| brier score | lower is better | -0.0020 [-0.0036, -0.0003] | 0.0392 | 0.1177 | **NO DETECTABLE DIFFERENCE** |
| pr auc | higher is better | +0.0145 [+0.0093, +0.0200] | 0.0000 | 0.0003 | **IMPROVES** |
| roc auc | higher is better | +0.0081 [+0.0047, +0.0117] | 0.0002 | 0.0010 | **IMPROVES** |

**Hard classification: NOT SUPPORTED. Ranking / probability: SUPPORTED.**

### What the helpful feature actually is

Before reading too much into that gain, look at *where* in each trace the biggest jump happens.
**95.4% of simulations have their largest ΔW inside the first 5% of the trace**,
and the median position is 0.000 — the very first transition. So
`max_positive_delta_W` is not detecting a keyhole event partway along the track. It is measuring **how
quickly the melt pool widens as it forms**, in the first few microseconds. Every trace starts from about
the same width (median 4 µm in both classes), so this is not an artifact of different starting points.

Read that together with the sign: Keyhole simulations widen *more slowly* at startup. That is physically
sensible — at high power the pool deepens into a keyhole rather than spreading sideways — but it means
the honest description of this feature is "early pool-formation speed", not "width dynamics during the
track". Any monitoring interpretation would have to watch the first few microseconds.

Two of the three ARD lengthscales in the small block sit pinned at their upper bound in ≥96% of folds
(`median_positive_delta_W`, `fraction_positive_delta_W`), meaning the kernel effectively ignores them —
which is why the three-feature block performs like the single feature rather than better.

### The other q20 contrasts

| contrast | metric | mean difference [95% CI] | Holm p | verdict |
|---|---|---|---|---|
| `gpc_4d_plus_max_width_rate - gpc_4d` | balanced accuracy | -0.0093 [-0.0202, +0.0015] | 0.4630 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_max_width_rate - gpc_4d` | keyhole recall | +0.0137 [-0.0030, +0.0300] | 0.4630 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_max_width_rate - gpc_4d` | pr auc | +0.0020 [-0.0066, +0.0106] | 1.0000 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_max_width_rate - gpc_4d` | roc auc | -0.0004 [-0.0051, +0.0043] | 1.0000 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_old_full8 - gpc_4d` | balanced accuracy | -0.0113 [-0.0216, -0.0006] | 0.1626 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_old_full8 - gpc_4d` | keyhole recall | -0.0012 [-0.0203, +0.0165] | 0.9752 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_old_full8 - gpc_4d` | pr auc | +0.0152 [+0.0097, +0.0212] | 0.0006 | IMPROVES |
| `gpc_4d_plus_old_full8 - gpc_4d` | roc auc | +0.0024 [-0.0016, +0.0064] | 0.5167 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_old_shape3 - gpc_4d` | balanced accuracy | +0.0069 [-0.0030, +0.0169] | 0.5050 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_old_shape3 - gpc_4d` | keyhole recall | +0.0236 [+0.0054, +0.0421] | 0.1052 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_old_shape3 - gpc_4d` | pr auc | +0.0217 [+0.0161, +0.0278] | 0.0003 | IMPROVES |
| `gpc_4d_plus_old_shape3 - gpc_4d` | roc auc | +0.0090 [+0.0054, +0.0130] | 0.0017 | IMPROVES |
| `gpc_4d_plus_simple_delta_block - gpc_4d` | balanced accuracy | +0.0034 [-0.0057, +0.0119] | 1.0000 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_simple_delta_block - gpc_4d` | keyhole recall | +0.0165 [+0.0001, +0.0325] | 0.2796 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_simple_delta_block - gpc_4d` | pr auc | +0.0157 [+0.0108, +0.0208] | 0.0003 | IMPROVES |
| `gpc_4d_plus_simple_delta_block - gpc_4d` | roc auc | +0.0069 [+0.0034, +0.0108] | 0.0082 | IMPROVES |
| `gpc_4d_plus_simple_delta_block - m3` | balanced accuracy | +0.0309 [+0.0153, +0.0463] | 0.0033 | IMPROVES |
| `gpc_4d_plus_simple_delta_block - m3` | keyhole recall | +0.0834 [+0.0570, +0.1093] | 0.0004 | IMPROVES |
| `gpc_4d_plus_simple_delta_block - m3` | pr auc | +0.0679 [+0.0552, +0.0813] | 0.0003 | IMPROVES |
| `gpc_4d_plus_simple_delta_block - m3` | roc auc | +0.0156 [+0.0093, +0.0216] | 0.0006 | IMPROVES |
| `gpc_4d_plus_simple_rate_block - gpc_4d` | balanced accuracy | -0.0128 [-0.0234, -0.0022] | 0.1432 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_simple_rate_block - gpc_4d` | keyhole recall | +0.0101 [-0.0061, +0.0266] | 0.7264 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_simple_rate_block - gpc_4d` | pr auc | +0.0050 [-0.0029, +0.0124] | 0.7264 | NO DETECTABLE DIFFERENCE |
| `gpc_4d_plus_simple_rate_block - gpc_4d` | roc auc | -0.0022 [-0.0071, +0.0024] | 0.7264 | NO DETECTABLE DIFFERENCE |
| `m3 - gpc_4d` | balanced accuracy | -0.0275 [-0.0403, -0.0146] | 0.0033 | DEGRADES |
| `m3 - gpc_4d` | keyhole recall | -0.0670 [-0.0878, -0.0470] | 0.0003 | DEGRADES |
| `m3 - gpc_4d` | pr auc | -0.0522 [-0.0628, -0.0412] | 0.0003 | DEGRADES |
| `m3 - gpc_4d` | roc auc | -0.0087 [-0.0132, -0.0043] | 0.0033 | DEGRADES |
| `m3_plus_max_delta_W - m3` | balanced accuracy | +0.0192 [+0.0124, +0.0262] | 0.0005 | IMPROVES |
| `m3_plus_max_delta_W - m3` | keyhole recall | +0.0372 [+0.0234, +0.0512] | 0.0006 | IMPROVES |
| `m3_plus_max_delta_W - m3` | pr auc | +0.0120 [+0.0072, +0.0171] | 0.0006 | IMPROVES |
| `m3_plus_max_delta_W - m3` | roc auc | +0.0137 [+0.0112, +0.0164] | 0.0005 | IMPROVES |

## Question 5 — how does this compare with M3?

M3 is reproduced here exactly as specified in Week 9 Phase 1.13: a logistic mean on `log h` fitted on the
training simulations, frozen, plus a `FixedMeanLaplaceGPC` discrepancy with an ARD Matérn-3/2 kernel over
the scaled 4D inputs. `m3_plus_max_delta_W` keeps that structure completely intact and only widens the
**discrepancy** GP by one input dimension — the physics mean still sees `log h` and nothing else, so the
meaning of M3 is not distorted.

* 4D GPC q20 balanced accuracy **0.8739**
* best simple-ΔW GPC **0.8830**
* M3 **0.8464**
* M3 + max ΔW **0.8656**

M3 versus plain 4D: hard NOT SUPPORTED, ranking NOT SUPPORTED.
Simple-ΔW block versus M3: hard SUPPORTED, ranking SUPPORTED.
Adding ΔW to M3 itself: hard SUPPORTED, ranking SUPPORTED.

## Is the answer an artifact of the grid resolution?

| feature | δ @51 | δ @101 | δ @201 | ROC @51 | ROC @101 | ROC @201 | robust? |
|---|---|---|---|---|---|---|---|
| `max_positive_delta_W` | -0.312 | -0.162 | -0.204 | 0.344 | 0.419 | 0.398 | no |
| `min_delta_W` | -0.233 | -0.002 | +0.159 | 0.383 | 0.499 | 0.580 | no |
| `median_positive_delta_W` | -0.139 | -0.135 | -0.086 | 0.431 | 0.433 | 0.457 | no |
| `fraction_positive_delta_W` | -0.213 | -0.127 | +0.000 | 0.394 | 0.437 | 0.500 | no |
| `total_positive_delta_W` | +0.133 | +0.073 | +0.001 | 0.567 | 0.537 | 0.500 | no |
| `max_positive_width_rate` | -0.333 | -0.232 | -0.300 | 0.333 | 0.384 | 0.350 | yes |
| `median_positive_width_rate` | -0.231 | -0.257 | -0.244 | 0.385 | 0.371 | 0.378 | yes |
| `fraction_positive_width_rate` | -0.213 | -0.127 | +0.000 | 0.394 | 0.437 | 0.500 | no |

Several members of the small family are **not** resolution-stable — `min_delta_W`,
`fraction_positive_delta_W` and `total_positive_delta_W` change sign between 51 and 201 points. Those are
artifacts of the grid choice and are reported as such rather than interpreted. The rate features are the
most stable marginally; `max_positive_delta_W` keeps its direction at all three resolutions but its
magnitude moves by about a factor of two.

Marginal stability is not the same as model stability, so the headline gain is re-tested directly: the
same GPC on the same folds, with `max_positive_delta_W` rebuilt on each grid.

| grid used to build max ΔW | q20 PR-AUC gain over 4D-only | verdict |
|---|---|---|
| 51 analysis points | +0.0119 | IMPROVES |
| 101 analysis points | +0.0207 | IMPROVES |
| 201 analysis points | +0.0145 | IMPROVES |

## Secondary and historical: the demoted Phase 2.1 engineered block

Phase 2.1 summarised the width trace using engineered shape and derivative descriptors. Phase 2.1R
instead asks the simpler question: what happens between consecutive resampled analysis points? The old
blocks are kept only as context, and are now run under GPC rather than logistic regression.

### Derivative ablation, starting from 4D + shape3

| model | q20 bal. acc | difference vs 4D+shape3 [95% CI] | Holm p | verdict |
|---|---|---|---|---|
| + robust_early_dWdt_20_um_per_ms | 0.8777 | -0.0031 [-0.0089, +0.0026] | 0.5912 | NO DETECTABLE DIFFERENCE |
| + robust_early_dWdt_40_um_per_ms | 0.8741 | -0.0068 [-0.0124, -0.0013] | 0.1368 | NO DETECTABLE DIFFERENCE |
| + robust_max_positive_dWdt_um_per_ms | 0.8788 | -0.0020 [-0.0096, +0.0048] | 1.0000 | NO DETECTABLE DIFFERENCE |
| + robust_median_positive_dWdt_um_per_ms | 0.8794 | -0.0014 [-0.0036, +0.0000] | 1.0000 | NO DETECTABLE DIFFERENCE |
| + robust_time_of_max_dWdt_tau | 0.8728 | -0.0080 [-0.0106, -0.0053] | 0.0009 | DEGRADES |
| gpc_4d_plus_old_full8 | 0.8626 | -0.0183 [-0.0276, -0.0089] | 0.0095 | DEGRADES |

## Corrections to the Phase 2.1 write-up

| previous statement | verdict | correction |
|---|---|---|
| "nothing anywhere survives the Holm adjustment" | **WRONG** | Within the six-metric Holm family, 2 results survive at the 0.05 level: q30 pr_auc +0.01043 (Holm p=0.0095); q30 brier_score -0.00463 (Holm p=0.0030). The q20 region alone showed no surviving effect. |
| "width adds no value beyond the 4D process inputs" | **OVERSTATED** | Safe wording: the full eight-feature width block did not show a supported q20 improvement over 4D, while a secondary three-feature shape subset showed a positive development signal (q20 balanced accuracy +0.0203 [+0.0094, +0.0313]). |
| "width dynamics is redundant because R-squared = 0.58" | **CAUSALLY OVERSTATED** | Safe wording: several width-derived features are substantially predictable from the process inputs (median R-squared 0.58, range 0.03-0.86). This is an association, not a demonstrated cause of the null result. |
| "the engineered eight-feature block is the width story" | **SUPERSEDED** | Phase 2.1 summarised the width trace using engineered shape and derivative descriptors. Phase 2.1R instead asks the simpler question: what happens between consecutive resampled analysis points? |

## Claim ledger

| claim | status | guardrail |
|---|---|---|
| Keyhole simulations show larger maximum width increases between consecutive resampled analysis points than Conduction simulations | NOT SUPPORTED | descriptive, whole sample: medians 29.27 vs 29.82 µm, Cliff's δ = -0.204, ROC-AUC = 0.398 |
| The MODEL-level gain from max_positive_delta_W survives changing the grid resolution (51 / 101 / 201 points) | SUPPORTED | same GPC, same folds, only the grid used to build the feature changes; q20 PR-AUC gain +0.0119 / +0.0207 / +0.0145 |
| That separation is robust to the choice of grid resolution (51 / 101 / 201 points) | QUALIFIED | Cliff's δ = -0.312 / -0.162 / -0.204 at 51 / 101 / 201 analysis points |
| A simple leak-free threshold on max_positive_delta_W classifies better than chance on the q20 boundary band | SUPPORTED | threshold learned on training folds only; q20 balanced accuracy 0.564 ± 0.025, Keyhole recall 0.866 |
| Dividing by the actual time gap (ΔW/Δt) changes the conclusion versus raw ΔW | QUALIFIED | Cliff's δ -0.204 (raw ΔW) vs -0.300 (rate); q20 threshold balanced accuracy 0.564 vs 0.433 |
| PRIMARY — adding max_positive_delta_W to the 4D GPC improves hard classification on q20 | NOT SUPPORTED | q20 balanced accuracy 0.8739 → 0.8830; Holm over six metrics within the contrast |
| PRIMARY — the same addition improves ranking / probability quality on q20 | SUPPORTED | q20 ROC-AUC / PR-AUC / Brier, read separately from the hard metrics |
| The biggest width jump is a melt-pool STARTUP quantity, not a Keyhole-onset signal | SUPPORTED | 95.4% of simulations have their largest jump inside the first 5% of the trace (median position 0.000); whatever predictive value it carries is about how the pool forms, not about a later transition |
| The small three-feature simple ΔW block improves the 4D GPC on q20 | SUPPORTED | hard NOT SUPPORTED, ranking SUPPORTED; q20 balanced accuracy 0.8773 |
| The rate block behaves differently from the raw ΔW block | QUALIFIED | 4D+rate hard NOT SUPPORTED / ranking NOT SUPPORTED versus 4D+ΔW hard NOT SUPPORTED / ranking SUPPORTED |
| M3 outperforms the plain 4D GPC on this usable subset | NOT SUPPORTED | q20 balanced accuracy 0.8739 (4D) vs 0.8464 (M3); predictive comparison, not an acquisition comparison |
| The best simple-width GPC beats M3 | SUPPORTED | 4D+simple ΔW block − M3 on q20: hard SUPPORTED, ranking SUPPORTED |
| Adding max_positive_delta_W to M3 itself improves M3 | SUPPORTED | physics mean untouched; only the discrepancy GP gains one input dimension. q20 balanced accuracy 0.8464 → 0.8656 |
| SECONDARY (historical) — the old three-feature shape subset still helps once the model is GPC rather than logistic regression | SUPPORTED | q20 balanced accuracy 0.8808 vs 4D 0.8739; Phase 2.1 saw this under logistic regression |
| SECONDARY (historical) — the old full eight-feature block helps | QUALIFIED | q20 balanced accuracy 0.8626 |
| A single robust-derivative feature is responsible for diluting the shape3 signal | QUALIFIED | worst single addition is old_shape3 (-0.0080 q20 balanced accuracy, DEGRADES); five one-at-a-time additions tested |
| These results describe raw SPH solver timesteps | NOT SUPPORTED | every ΔW here is between consecutive RESAMPLED analysis points on the Phase 2 grid; raw solver steps (~75k per simulation, dt ≈ 0.018 µs) were not used |
| Results generalise to simulations with no usable width trace | NOT SUPPORTED | every model is trained and scored only on the usable subset |
| This phase says anything about in-process monitoring hardware or about acquisition | NOT SUPPORTED | predictive feature-value experiment on frozen folds; no camera, no new active-learning path |

## What is corrected for, and what is not

The Holm adjustment is applied **within each contrast, across the six predeclared metrics**
(balanced accuracy, accuracy, Keyhole recall, ROC-AUC, PR-AUC, Brier). It is applied to every contrast,
including the secondary and historical ones, so a secondary result cannot look stronger than the primary
one simply by escaping multiplicity control. **Not** corrected for: the number of contrasts, the three
evaluation regions (q20 / q30 / full), and the three grid resolutions. Wherever a nominal reading is
quoted below, it is labelled nominal.

## Methods

**Population and folds.** Frozen canonical population: 405 simulations, 73 Keyhole, via
`week8_5_frozen_sample_efficiency_confirmation.load_population`. Inputs `P` (laser power), `VX` (scan
speed), `LS` (Gaussian laser spot *radius*), `ST` (*substrate temperature*, never layer thickness).
Evaluation uses the 100 frozen Week 8.5 grouped outer folds (20 repeats × 5 stratified group folds);
fold membership is computed on the full 405-row population and then intersected with the usable subset,
so no new split is invented. `B1` q20/q30 are computed on the full frozen test fold and used purely as
evaluation masks.

**Width.** Transverse `W(t) = Ymax − Ymin = ΔY`, µm, read from pinned Phase 2 commit
`da913797d14b171bec55d3708f96aa87f09a4f94` with `git show`. Nothing is re-extracted and longitudinal ΔX is never used.

**Transitions.** For each simulation, every consecutive pair of resampled analysis points contributes one
row: `W_i`, `W_(i+1)`, `delta_t`, `delta_W = W_(i+1) − W_i`, `width_rate = delta_W / delta_t`. The label
is simulation-level, so the 70,000 transition rows are never treated as independent labelled
experiments.

**Classifier.** The primary family is GPC, using the Phase 1.12 supported winner G3: ARD Matérn-3/2,
`ConstantKernel(1.0, (1e-3, 1e3)) * Matern(length_scale=ones(d), length_scale_bounds=(1e-2, 1e2),
nu=1.5)`, `optimizer='fmin_l_bfgs_b'`, `n_restarts_optimizer=0`, `max_iter_predict=100`, on
`StandardScaler`-scaled inputs fitted inside the training fold. `kernel_parity_audit.csv` proves the
builders here reproduce the frozen Phase 1.12 and Phase 1.13 kernel specifications character for
character. Logistic regression is used nowhere as a headline model.

**M3.** Exactly the Phase 1.13 construction: `fit_physics_mean` (logistic on scaled `log h`, `C=1e6`)
fitted on the training simulations and frozen, then `FixedMeanLaplaceGPC` with
`ConstantKernel(0.09, (0.0025, 1.0))
* Matern(ARD, bounds (0.01, 100.0), nu=1.5)` on the scaled inputs.

**Uncertainty.** Repeat-block bootstrap over the 20 repeats (the five folds of a repeat stay together),
5000 draws, paired differences; plus a paired sign-flip permutation p-value
(20000 draws); plus Holm within each contrast across the six predeclared metrics.

## Figures
- `figures/01_delta_W_construction.png`
- `figures/02_example_trace_and_delta.png`
- `figures/03_max_positive_delta_W_distribution.png`
- `figures/04_max_positive_width_rate_distribution.png`
- `figures/05_threshold_classifier.png`
- `figures/06_model_comparison_gpc_m3.png`
- `figures/07_q20_paired_contrasts.png`
- `figures/08_derivative_ablation.png`
- `figures/09_claim_status.png`
- `figures/10_resolution_sweep.png`

## Interactive artifacts
- `interactive/view1_drop_ST.html`
- `interactive/view2_drop_LS.html`
- `interactive/view3_drop_VX.html`
- `interactive/view4_drop_P.html`
- `interactive_3d_index.html`

Open `interactive_3d_index.html` first: it links the four views. Each drops one process input from the
axes and keeps it as a colour mode and hover field, so every input gets a turn being the hidden one. All
405 simulations appear in every view; all four work offline with no libraries and no network.
