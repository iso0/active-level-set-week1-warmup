# EA stage 1, amendment 1: three further diagnostics

Dated 2026-10-26, about 14:40 UTC. Registered after the stage-1 ladder results and before any of these diagnostics is computed.

## Why

The ladder (`diagnosis/DIAGNOSIS.json`) gives three findings.

1. **Early bottleneck: depth.**
   - Gap to the true-depth oracle +0.040 BA. Of this, +0.022 is attainable from the inputs with an unlimited-data emulator and +0.018 is not.
   - Classifier family and representation are not limiting: R5 − R3 ≈ 0 and R4 − R3 < 0.
2. **Late: the current system is close to its input-only ceiling.** R0_L 0.955 vs R3u 0.961. Most remaining errors sit in a small set of runs whose label is not explained even by the true depth: 13 of the 15 opposite-label (z_h, true a) neighbours, 87 % in the fast-scan corner.
3. **Design diagnostic** (full pool, evaluator-side, never used by a learner):
   - log depth is R² 0.89 linear in z_h and 0.99 with a 4-D GP;
   - for n ≤ 12 random training runs, a linear-in-z_h model has a lower depth RMSE than the 4-D GP.

Two questions decide the design.
- **(a)** Is the early emulator loss a hyperparameter-estimation problem (fixable by structure / priors) or an information limit of b paid depths?
- **(b)** Does margin waste queries in the region where even unlimited input-only emulation does not resolve the label? This is the measured-defect test that the instruction requires before any selector change.

## Diagnostics

| | name | status | definition |
|---|---|---|---|
| D2 | hyperparameter oracle | evaluator-only | HA_LEAN's emulator and stacking, but with the depth-GP hyperparameters FIXED at their full-pool ML-II values, conditioned only on the b paid depths (honest K = 10 OOF and full fit with the same fixed values). Same classifier. |
| D3 | linear-in-z_h emulator | deployable variant | OLS of the paid log depths on z_h (good records); honest K = 10 OOF and full fit; the same classifier. |
| D4 | corner-capped margin | evaluator-defined region, diagnostic only | Own HA_LEAN margin path from the same startup, where fast-scan-corner candidates (RC21 definition VX > 0.85 m/s and P > 330 W) are removed once 4 corner runs are paid. 4 is the corner's proportional share of 52 queries: 7 % × 52 ≈ 3.6, fixed a priori. |

D4 compares BA curves and target attainment against the recorded margin path. It measures whether queries beyond the proportional share in that region have value. It is NOT a candidate, because the region definition was found with labels.

**Data:** STD repeats 83–122 (the same recorded paths and startups, 200 learners). Budgets as the ladder for D2 / D3; D4 every budget 8..60.

## What follows

- **If D2 ≫ R0_L early:** hyperparameter estimation is a material part of the early loss, and the emulator's small-n inference is the design target.
- **If D2 ≈ R0_L:** b paid depths are the limit. No emulator re-parameterisation is expected to help; HA_TREND's gain is near what structure gives.
- **If D4 beats margin in early BA-AULC or in attainment / spend to 0.93 / 0.95:** a selector change has a measured justification. A legitimate, paid-data-only mechanism would then be registered separately.
- **If D4 does not beat margin:** margin stays and the selector is not changed.
