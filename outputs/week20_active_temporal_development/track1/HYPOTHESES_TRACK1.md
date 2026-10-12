# Track 1 hypotheses and evaluation criteria (frozen before any Track 1 fit)

*Written 2026-10-12T19:56:23+00:00 from `manifest_track1.json` (sha256 in the attempt ledger).*

**Status.** Post-hoc DEV research on repeats 1–4. This is not confirmation, and C3 stays reserved.

**Numbers.** Numerical expectations are given only where existing evidence supports them: the historical Week 18 DEV caches and the Week 19 shared-path pilot.

## Hypotheses

- **T1-H0_fidelity.** Arms A and C reproduce the historical Week 18 DEV caches (phase3/depth3 E1; phase2 G3|mlii|margin) on repeats 1-4 at every grid budget <= 80: max |p_new - p_cache| <= 1e-4 (cache rounding is 5 significant digits). Otherwise they are reported as re-implementations with the discrepancy.
- **T1-H1_primary.** R3_NEW BA-AULC (grid 16..80 step 4), ACTIVE_E1_STRADDLE minus G3_MARGIN, is > 0. Supporting evidence: Week 19 shared-path pilot, B40 ACTIVE - G3 = +0.112 [-0.009, +0.212]; adaptive acquisition untested, so no magnitude is predicted.
- **T1-H2_ablation.** R3_NEW BA-AULC, ACTIVE minus WHOLE, is > 0 (shared-path pilot B40: +0.098 [+0.013, +0.185]). No magnitude predicted.
- **T1-H3_old.** R3_OLD: WHOLE minus G3 reproduces the historical DEV value (+0.0286 [+0.0117, +0.0518] on repeats 1-4 up to B80); ACTIVE minus WHOLE is small (|delta| < 0.01), because whole max and A separate OLD labels equally well (AUC 0.99996 both; 37/405 runs differ).
- **T1-H4_pooled.** R1_POOLED: WHOLE minus G3 reproduces the historical DEV value (+0.0028 [-0.0003, +0.0062]); ACTIVE minus G3 >= WHOLE minus G3 (A separates POOLED labels better: AUC 0.9987 vs 0.9958). No magnitude predicted.
- **T1-H5_threshold.** WHOLE E1 on R3_NEW reproduces the historical high thresholds (u >= 200 um in 6 of 20 folds of repeats 1-4: r1f5, r2f1, r3f1, r3f2, r4f1, r4f2). ACTIVE E1 never reaches u >= 200 um on R3_NEW (every NEW negative has A <= 131.2 um). Falsified by any ACTIVE R3_NEW step with u >= 200 um.
- **T1-H6_precedence.** In every WHOLE R3_NEW run with a u >= 200 um step, the late negative H-f4fc937e86 was paid before the first such step. This is temporal precedence only; causal attribution would need an isolated refit and is not claimed.
- **T1-H7_secondary.** No expectations are set for q20, short-K sensitivity, Brier or AUC; they are reported.

## Endpoints

- **Primary.** R3_NEW pooled-per-repeat BA AULC (trapezoid over 16..80 step 4 / width), ACTIVE_E1_STRADDLE - G3_MARGIN; per-repeat values and the Week 18 repeat bootstrap (4000, seed 0).
- **Response-definition ablation.** R3_NEW ACTIVE - WHOLE.
- **Secondary:**
  - R3_OLD and R1_POOLED (grid 16..80 step 8) for all contrasts;
  - q20 AULC (unchanged);
  - specificity, sensitivity, short-K sensitivity (fixed ten NEW positives; NEW and POOLED-NEW rows), Brier, AUC at B40/B80 and as AULC;
  - full per-step curves.
- **Query savings.** QTT (Week 18 qtt): first grid budget at which an arm's repeat-pooled BA reaches G3_MARGIN's repeat-1-4 mean BA at B40 and at B80 on the same task; unreached by B80 = 'not reached' (no extrapolation); means use B80 + one grid step for unreached (Week 18 qtt_reduction convention), always with the unreached count.
- **Mechanism.** learned thresholds per step from the ledgers; u >= 200 um episodes; paid composition before the first such step; late-negative timing as precedence only.

## Failure rules

- fit exception, non-finite prediction or non-finite acquisition score: the run stops there, status recorded, later budgets missing; no reseeding or repair.
- single-class usable response pairs for an E1 arm: run stops (the engine's 111 um fallback is never used); cannot arise in DEV 1-4 (checked: the A-unavailable run is in no startup set).
- logistic slope <= 0 or root outside the paid range: recorded, not repaired (historical behaviour).
- G3 Laplace fixed-point error > 1e-6: recorded as a Week 18 convergence violation, run continues (historical behaviour).
- no forced queries, no favourable-repeat selection; all 180 runs are reported.

**Resource limits:** {"track1_max_scalar_fits": 13500, "total_scalar_fits": 15000, "workers": 4, "threads_per_worker": 1, "max_memory_gib_total": 8, "max_elapsed_h_total": 8}; expected 180 runs x at most 73 fits = 13,140.
