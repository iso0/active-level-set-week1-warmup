# PHYS_AUX — does x-predicted physics help the classifier at the same budget?

**Status: REGISTERED BEFORE ANY PHYS_AUX OUTCOME.** This is the follow-up within the physical-auxiliary prototype (owner request of 2026-10-16, items 2.3–2.4: "show whether it actually works").
- **Code:** `src/jdl_phys_aux.py`.
- **Manifest:** `PHYS_AUX_MANIFEST.json`.

## Mechanism and motivation (from pilot B, DEV)

- KE_T0 and the velocity spike size are learnable from x (R²_oof 0.74 / 0.87).
- Their out-of-fold predictions rank corner Keyhole above chance (AUC 0.77 / 0.67) when all pool runs are revealed. Every label model so far reaches 0.5–0.64 in the corner.
- A paid simulation reveals its monitors together with its label, at no extra simulation cost. A continuous physical response may therefore give the classifier a better representation of x.

## Arms

- **PHYS_AUX (candidate).**
  - At each budget, two GP regressions are fitted on the **paid runs only**: log KE_T0 and the velocity spike log-ratio (Matérn 3/2 ARD + white nugget, `normalize_y`, no restarts). QC-unavailable values are skipped and logged.
  - **Classifier features:** the 4 standardized log inputs plus the 2 auxiliary predictions, z-scored.
  - **Feature consistency:** paid runs get closed-form leave-one-out predictive means (same hyperparameters). Unpaid and test runs get full-fit means. Training and test features are therefore both predictions, never true monitor values. The monitors of new or test runs are never read.
  - **Classifier:** `GaussianProcessClassifier` (C·RBF ARD). **Acquisition:** margin, ties by simulation ID.
- **GPC_X (decisive control):** the same classifier and acquisition on the 4 inputs only. It isolates the auxiliary effect.
- **References:** G3_MARGIN and ACTIVE E1_STRADDLE from the pilot A cache, with the same starts, budget and one-class rule.
- **Design:** NEW DEV repeats 3–4, the frozen feature-only B16 starts, B16–B40, and pilot A's one-class rule (frozen-path continuation).
- **Cost accounting:** the monitors come with each paid simulation (no extra simulation). The extra compute is 2 GP regressions per step, reported in seconds.

## Endpoints (fixed)

- **Measures:** BA-AULC B16–B40, pooled per repeat (trapezoid). At B40: BA, both recalls, q20, short-K caught/total, AUC, Brier, and corner AUC (evaluator-only).
- **Contrasts:**
  - PHYS_AUX − GPC_X (the auxiliary effect);
  - PHYS_AUX − G3_MARGIN and PHYS_AUX − E1_STRADDLE;
  - GPC_X − G3_MARGIN (descriptive).
  - All use the class-stratified simulation-cluster bootstrap (2000 draws).
- **Verdict "PRACTICALLY BETTER"** iff all of the following hold:
  - BA-AULC ≥ +0.04;
  - the 95% interval is above 0;
  - both repeats are positive;
  - short-K caught at B40 is ≥ 7/10 in each repeat (absolute protection);
  - short-K caught is not more than 2 of 20 below the comparator.
  - A gain that fails only the short-K conditions is a **TRADE-OFF**. Otherwise the verdict is **NO PRACTICAL DIFFERENCE**.
- **Savings:** none are claimed unless the target (BA ≥ 0.75, short-K ≥ 0.70, q20 ≥ 0.70, sustained) is reached before the reference.

## Validation (PASS 6/6) and one harness correction

- **Checks passed:**
  - closed-form LOO equals direct conditioning (to 5e-10);
  - auxiliary table complete;
  - unit runs;
  - corrupting hidden labels **and** hidden monitor values leaves path and predictions unchanged;
  - one-class rule identical to pilot A;
  - references available.
- **Harness correction:** the first validation run failed its LOO check. The reference refitted the GP on 24 points, which re-normalizes the targets, so it was not the same model. The reference was corrected to direct conditioning with the same kernel and normalization; the formula was not changed. The failed log is kept as `logs/validate_v1_FAIL_reference_normalisation.log`.

## Budget

20 units of about 2–3 s each, on one worker.

## Limits

This is DEV on inspected NEW runs, with two repeats and 23 corner runs per repeat.
