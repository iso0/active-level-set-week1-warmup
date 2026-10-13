# C3 confirmation protocol — DRAFT (not frozen, not executed)

*Written 2026-10-13T09:00:23+00:00.*
- **Why it exists:** the Track 1 extension's frozen decision rule returned "C3 PROTOCOL DRAFT" (`track1_ext/decision.json`).
- **What it touches:** nothing in C3. No C3 split, label or prediction was used to write it.
- **When it becomes a freeze:** only if the owner approves it and it is committed before any C3 run.

## Candidate and reference
- **Candidate:** ACTIVE E1 + straddle, the frozen Track 1 arm B with no guard.
- **Reference:** G3 + margin, arm C.
- **Ablation:** WHOLE E1 + straddle is reported but is not decisive.
- **Code:** the frozen runner `src/week20_track1_al.py`, through `src/week20_track1_ext.py` with repeats 17–20, at 1 BLAS thread per worker.

## Data (used once)
- **Block:** C3 = repeats 17–20, 5 folds each.
- **Tasks:** R3_NEW (primary), R3_OLD and R1_POOLED.
- **Type:** split confirmation on the same 541 runs.

## Locked decision rule (contrasts ACTIVE − G3; repeat bootstrap, 4,000 resamples, seed 0)
- **Q3a (primary):** R3_NEW BA-AULC ≥ +0.02 **and** its 95 % interval > 0.
- **Q3b (no loss):** R3_OLD and R1_POOLED BA-AULC ≥ -0.01 (point estimates).
- **Interpretation, fixed in advance:**
  - Q3a and Q3b → **confirmed**: ACTIVE E1 + straddle improves on G3 + margin on NEW, without loss on OLD and POOLED.
  - Q3a without Q3b → improvement on NEW with a loss elsewhere.
  - Q3a fails but the point estimate is > 0 → not confirmed at the frozen bar.
  - Point estimate ≤ 0 → does not replicate.
- **Reported, not decisive:** q20, specificity, sensitivity, short-K, Brier, AUC, ACTIVE − WHOLE, QTT and the threshold mechanism.

## Predictions from DEV (repeats 1–8)

| Task | Per-repeat ACTIVE − G3 BA-AULC |
|---|---|
| R3_NEW | +0.062, -0.032, +0.067, +0.132, +0.004, +0.029, +0.176, +0.013 (mean +0.056, SD 0.069) |
| R3_OLD | +0.009, +0.062, +0.021, +0.028, +0.010, +0.012, +0.023, +0.017 |
| R1_POOLED | +0.003, +0.008, +0.008, +0.000, +0.003, +0.018, -0.002, +0.006 |

- **Method:** 4 of the 8 DEV values were drawn with replacement, 20,000 times, and the rule was applied to each draw.
- **Q3a:** the point-estimate bar is met in 87% of draws, the interval excludes 0 in 62%, and both hold in **60%**.
- **Q3b:** expected to pass, since every DEV value except one POOLED repeat at −0.002 is ≥ 0.

## Caveats
- A was defined after the Week 19 audit had seen every NEW label, so C3 tests the procedure on new splits and seeds; it does not test a target chosen blind to the labels.
- C1 and C2 were spent in Week 18 on WHOLE E1; C3 is the last unused block.
- With four repeats, the repeat bootstrap is coarse.

**Budget if run:** 180 runs, at most 13,140 scalar fits.
