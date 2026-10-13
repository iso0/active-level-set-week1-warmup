# Track 1 extension: hypotheses and decision rule (frozen before any extension fit)

*Written 2026-10-13T08:48:17+00:00; methods in `manifest_track1_ext.json`. Post-hoc DEV research, not confirmation.*

## Hypotheses

- **X-H0_fidelity.** Arms A and C reproduce the Week 18 DEV caches (phase3/depth3 E1; phase2 G3|mlii|margin) on repeats 5-8 at every grid budget <= 80: max |p_new - p_cache| <= 1e-4. Their contrasts then equal the historical values listed under historical_expectations.
- **X-H1_primary_replication.** R3_NEW BA-AULC (grid 16..80 step 4), ACTIVE_E1_STRADDLE minus G3_MARGIN, on repeats 5-8 is > 0 (repeat-bootstrap mean). Basis: repeats 1-4 +0.057 [-0.007, +0.115] (per repeat +0.062, -0.032, +0.067, +0.132). No magnitude predicted.
- **X-H2_target_ablation.** R3_NEW BA-AULC, ACTIVE minus WHOLE, on repeats 5-8 is > 0. Basis: repeats 1-4 +0.070 [+0.030, +0.110]. No magnitude predicted.
- **X-H3a_guard_identity.** In every run in which arm A has no non-positive-slope step, arm D (WHOLE + guard) is identical to arm A: the same paid sequence and the same test probabilities (max |dp| = 0). A code-level check of the ablation.
- **X-H3b_guard_effect.** R3_NEW BA-AULC, WHOLE + guard minus WHOLE, on repeats 5-8 is > 0. Basis: the reversed-slope trap (only paid negative = the late negative, whole 312 um) caused all six long WHOLE episodes on repeats 1-4, and the historical WHOLE threshold reached 200 um in 7 of 20 R3_NEW folds of repeats 5-8 (historical_expectations). No magnitude predicted.
- **X-H3c_remaining_target_effect.** R3_NEW BA-AULC, ACTIVE minus (WHOLE + guard): the part of the ACTIVE-WHOLE difference not removed by the guard. No directional expectation.
- **X-H4_old_pooled.** R3_OLD: |ACTIVE - WHOLE| < 0.01 and ACTIVE - G3 > 0 (repeats 1-4: +0.001 and +0.030). R1_POOLED: ACTIVE - G3 >= WHOLE - G3 (repeats 1-4: +0.005 vs +0.003).
- **X-H5_threshold_mechanism.** ACTIVE E1 never reaches u >= 200 um on R3_NEW (repeats 1-4 maximum 188.9 um); falsified by any such step. In every WHOLE R3_NEW run with a u >= 200 um step, the late negative was paid before the first such step (temporal precedence only).
- **X-H6_eight_repeat_summary.** Descriptive: ACTIVE - G3 and ACTIVE - WHOLE on R3_NEW over DEV repeats 1-8 (repeat bootstrap, 8 repeats). No expectation on whether the interval excludes 0.
- **X-H7_secondary.** q20, specificity, sensitivity, short-K sensitivity, Brier, AUC and QTT are reported without expectations.

## Decision rule

- C3 protocol draft: written (NOT executed) only if X-H1 holds (repeats 5-8 point estimate > 0) AND the repeats 1-8 point estimate of R3_NEW ACTIVE - G3 BA-AULC is > 0; otherwise HOLD (no C3 protocol). Spending C3 remains the owner's decision.

## Historical expectations (Week 18 caches, grid budgets <= 80)

- WHOLE - G3 BA-AULC, R1_POOLED: +0.0033 [-0.0038, +0.0105] (4 repeats)
- WHOLE - G3 BA-AULC, R3_NEW: -0.0284 [-0.1195, +0.0846] (4 repeats)
- WHOLE - G3 BA-AULC, R3_OLD: +0.0210 [+0.0183, +0.0237] (4 repeats)
- R3_NEW folds where the historical WHOLE threshold reached 200 um: r5f3, r5f4, r6f1, r7f1, r7f3, r7f5, r8f2
