# FR step 1: gain-area diagnosis. Registered before any number is computed

Written 2026-10-29 around 14:00 UTC, before the analysis code exists or has run, and committed before the first result. **Evidence label: DEV.** Every record used here was already evaluated in EA, C1C or C1S. No new run is opened.

## Data: identical paid prefixes

Pairs of C1 and HA_LEAN (A) probabilities at the same paid prefix, budgets 8–60.

| condition | records (exports) | paths |
|---|---|---|
| STD | EA validation 163–202; C1C main 203–282 | A's path (A_own, C1_on_A) and C1's path (C1_own, A_on_C1) |
| K5 (k-means 5 regions; test = one whole region) | EA cand-DEV 33–40 (A's path only); EA validation 41–48 (both paths) | as listed |
| K4 (k-means 4 regions) | EA cand-DEV 17–24 (A's path only); EA validation 25–32 (both paths) | as listed |

The block test regions are the same for every startup. Startups differ only in their paid paths. Startups of one design are therefore not independent test sets; the uncertainty they show is path variability.

## Quantities

Decisions are taken at the fixed threshold 0.5. For every learner-path, budget b and test run j, j falls in one of four classes:
- R: C1 wrong, A right;
- L: C1 right, A wrong;
- W: both wrong (always on the same side);
- OK: both right.

Each test run carries its BA weight: 1 / (2 n₁) for Keyhole, 1 / (2 n₀) for conduction.

- **Gain area** GA(b) = Σ_R weight = BA_oracle(b) − BA_C1(b).
  - BA_oracle takes the correct model wherever the two disagree. This is the best any input-dependent convex weight w(x) can reach at threshold 0.5.
  - It is an **oracle upper bound only**. It needs the test label, is not a method, and is never given to a learner.
- W = 1 − BA_oracle. This is the part of the error no convex combination can fix.
- The fixable share of C1's error is GA / (1 − BA_C1).

**Windows:** B8–B24, B25–B60, B8–B60.

**Conditions:**
- STD: individual learners.
- K5 and K4: per region, as in EA (the mean over a startup's defined blocks).
- Geometric: the K5 and K4 startup clusters together.

**Evaluator-only descriptors (reported):**
- short-Keyhole NEW recall and NEW conduction specificity;
- the fast-scan corner (VX > 0.85, P > 330);
- distance to the paid set.

## Realisability checks

| check | role | definition |
|---|---|---|
| AVG | the fixed-weight control | p = (p_C1 + p_A) / 2 |
| META | **label-informed diagnostic, not a method** | see below |

META is a leave-cluster-out logistic "which model is right on a disagreement point" model.
- **Features** (all label-free at test time):
  - logit p_C1 and logit p_A, clipped to [1e-4, 1 − 1e-4];
  - |p_C1 − p_A|;
  - log b;
  - log nearest-paid distance, in the task's public standardisation (`src.rc19_pool.zstd`);
  - log of that distance divided by the paid set's median nearest-neighbour spacing.
- **Fit:** L2 logistic with C = 1 and BA class weights. Scaling is fitted inside the training folds. GroupKFold(10) over (condition, cluster). It is fitted on the STD, K5 and K4 disagreement points together.
- **Decision:** choose A where the predicted P(A right) > 0.5. Elsewhere use the common decision.
- **Its labels are DEV test labels of other learners.** In this one finite pool those runs overlap the fresh test runs, so META can never be frozen into a method. It only asks whether the disagreement winner is predictable at all from features a learner could compute.

## Rule to continue (fixed now)

**Proceed to development only if both hold:**
- **G1 (room):** mean geometric GA over B8–B60 is at least 0.030, three times the practical target of 0.010.
- **G2 (predictable without the oracle):**
  - META − C1 in geometric per-region BA-AULC B8–B60 is at least +0.010, with a cluster lower bound above 0;
  - and META − C1 in STD BA-AULC B8–B24 is at least −0.003 (mean).

**Otherwise close the task:**
- G1 fails: the gain area is too small.
- G1 holds and G2 fails: the gain appears only under the oracle selection.

AVG is reported and does not enter the rule.

**Statistics:** cluster means, one-sided 95 % t-bounds (`src.el_eval.tstats`) over clusters (STD repeats; geometric startup clusters).

**Resource limit (fixed now)**
- Development, if reached: at most 75 min wall time with at most 3 workers.
- The fresh test is launched only if both hold:
  - its projected wall time plus 60 min (evaluation, exports, recomputation, reports, records, push) ends before 19:31:37 UTC;
  - it starts no later than 16:45 UTC.
- If either fails, the task closes with the DEV result and no fresh test.
