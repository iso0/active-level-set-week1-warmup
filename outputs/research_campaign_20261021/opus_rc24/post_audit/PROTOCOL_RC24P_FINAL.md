# RC24 post-audit: final comparison protocol

Registered 2026-10-22, before any of the final comparison's outcomes. It runs in the same RC24 window, which is not restarted.

Frozen code and data (manifest `freeze/RC24P_FINAL_MANIFEST.json`):
- `src/rc24p_final.py` (units);
- `src/rc24p_models.py` (clean trend family);
- `src/rc24p_eval.py` (metrics and decision);
- `src/rc24p_audit.py` (independent metric code);
- unchanged RC23 / RC24 code: `rc23_common`, `rc24_pac`, `rc24_pilot`, `rc22_common`, `rc21_phr`, `rc20_attr`, `rc18_gp` and `rc18_campaign`;
- the pooled manifest.

## 1. Why this comparison is needed

The RC24 Stage C decision (CONFIRMED) is kept as recorded. The dated addendum `post_audit/ADDENDUM_RC24_DECISION.md` shows what that decision did NOT establish:
- **Pooled vs per-region.** The pooled block gain of HA_TREND (+0.0112) comes almost entirely from majority-class conduction in one region (block 5). Measured per region, HA_TREND is below HA_LEAN: 0.689 vs 0.723 over the defined blocks, B8–B60.
- **Spend.** For spend to BA ≥ 0.95, "no MORE verdict" was counted as a pass. Non-inferiority was not shown: one more non-attainment, and a one-sided 95 % upper bound of +9.3 simulations.
- **Physics specificity.** The physics-specificity control (PAC_GEN) changed more than the trend.
- **Geometry.** The Stage C "block seeds" were new startups on the SAME five regions.

This final comparison applies the corrected criteria, fixed here, on fresh data of the same pool.

## 2. Arms (margin −|p − ½|, standard 8-point label-free maximin startup counted, budgets 8–60)

| arm | model |
|---|---|
| F_HA_LEAN (reference) | RC23 D1: depth emulator without trend (TR_NONE) + honest K = 10 stacking + learned-regularisation classifier on [z_h, Â] |
| F_HA_TREND (candidate) | the same with the physics-direction trend θ z_h, θ ~ N(0, 3²) integrated (TR_PHYS) |
| F_HONLY | the same classifier on z_h only |
| F_TR_GEN15 (control) | the same as F_HA_LEAN with a generic linear trend in the four standardised log inputs, θ_k ~ N(0, 1.5²) |

- **Why TR_GEN15 and not TR_GEN3.** TR_GEN15's prior variance of the trend function, averaged over the pool, equals TR_PHYS's: 4 × 1.5² = 3². This was fixed by that argument, before any matched result was inspected. TR_GEN3 (per-coefficient b = 3) appears in the matched evaluation only.
- **Exact identities** (verified bit-for-bit): TR_NONE ≡ HA_LEAN and TR_PHYS ≡ HA_TREND.

## 3. Conditions (all on the same 541-run pool; none is independent physical data)

| condition | definition |
|---|---|
| STD (primary use condition) | fresh random-split repeats 75–82 × 5 folds; learning from scratch on the pool, with random held-out runs |
| BLOCK_A | the RC22 k-means partition (k = 5, seed 2222), the SAME five regions as RC23 and RC24; new startups 17–24. This is a re-test on the same regions, not new geometry |
| BLOCK_B | a NEW partition: k-means k = 4 (n_init 20, seed 2222) on the same public standardised log inputs; startups 1–8. It gives new extrapolation regions of the same pool. k = 4 was fixed so that the partition cannot coincide with k = 5; its class counts are recorded after the run and accepted whatever they are |

**Matched evaluation (f-match).** On every F_HA_LEAN path, the following are evaluated at budgets 8–60, step 4: TR_NONE, TR_PHYS, TR_GEN3, TR_GEN15 and HONLY_LR.

## 4. Metrics (src/rc24p_audit; independent of the RC22 metric code)

- **BA-AULC** (B8–B24, B8–B60):
  - pooled: the 5 (or 4) learners of a repeat or startup concatenated;
  - individual / per region: one learner. BA is undefined (NaN, never imputed) on a one-class test set; that block's present-class recall is reported instead.
- **Both recalls.**
- **Log loss.** Pooled AULC of the mean log loss of the pooled predictions; per learner as well.
- **Attainment for 0.80, 0.90, 0.93 and 0.95.** Reported:
  - first budget;
  - confirmation at b and b + 4;
  - spend = b + 4, counting ALL paid simulations including the 8 startup runs;
  - maintenance after confirmation;
  - BA held at B60;
  - number of attainers;
  - spend among attainers;
  - the paired both-attained difference with its one-sided 95 % bound.
  - The "lower-bound imputation" (non-attaining = 61) is reported only as a lower bound, never as a cost.
- **Minority classes per region.** Hit counts with exact Clopper–Pearson intervals. A minority of 1–4 runs is called anecdotal.

## 5. Decision (src/rc24p_eval.py::decide). Margins not loosened: BA 0.010, LL 0.010, spend 2 simulations

**In-distribution components (STD), HA_TREND against HA_LEAN:**

| component | PASS iff |
|---|---|
| BA B8–B24 | one-sided 95 % lower bound of the paired difference (8 repeats) ≥ −0.010 |
| BA B8–B60 | the same |
| LL | one-sided 95 % UPPER bound of the paired log-loss difference ≤ +0.010 |
| spend to BA ≥ 0.93 | attainers(HA_TREND) ≥ attainers(HA_LEAN), at least 6 both-attained pairs, and the one-sided 95 % upper bound of the both-attained difference ≤ +2 simulations |
| spend to BA ≥ 0.95 | the same |

- A spend component FAILs if HA_TREND has 2 or more extra non-attainers, or a both-attained mean ≥ +2 with lower bound > 0.
- A spend component is NOT_SHOWN otherwise. **NOT_SHOWN does not count as PASS.**

**Positive reasons** (at least one is required to replace the reference):
- **Extrapolation benefit**, required in BOTH BLOCK_A and BLOCK_B:
  - pooled B8–B60 lower bound > 0, AND
  - per-region mean BA-AULC over the defined blocks (paired by startup), lower bound ≥ −0.010.
- **Early superiority:** STD B8–B24 lower bound > 0.

**Choice:**
1. HA_TREND + margin, if every in-distribution component PASSes AND a positive reason holds.
2. Otherwise HA_LEAN + margin: the simpler system, with no extra modelling assumption.
3. HONLY + margin replaces HA_LEAN only if it PASSes every in-distribution component against HA_LEAN.

**Physics specificity** (reported label; it does not change the choice). "Shown" iff any one of these holds:
- HA_TREND − TR_GEN15 STD B8–B24 lower bound > 0;
- pooled lower bound > 0 in both block partitions;
- per-region lower bound > 0 in both block partitions.

**Fixed now; nothing above changes after the final results.** A reported superiority is a DEV result on one pool. Fixed-block results are not new geometry.
