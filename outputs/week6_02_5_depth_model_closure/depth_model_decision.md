# Week 6 Phase 2.5 depth-model decision

## Why the closure was required

Phase 2 compared depth Methods B and C on all 241 simulations, but only C was
rerun after removing the 11 unstable-window simulations. Phase 2.5 closes that
single fairness gap. Width and length were not reopened because their learned-
nugget preference was already robust and the requested ambiguity concerns only
depth.

## Matched protocol

Both methods used the same 230 stable simulation IDs, ascending fold order, 229
training rows per exact LOO fold, training-only X/y scaling, the same Phase 2
fold seed, the same isotropic Matérn 3/2 kernel bounds, L-BFGS-B, and one
deterministic restart. Only the observation treatment differs.

- **B** learns one common WhiteKernel effective nugget per fold. It is a model-
  discrepancy term and not stochastic simulator noise.
- **C** uses existing simulation-specific moving-block-bootstrap variances of
  the selected-window median. They are target-summary uncertainty proxies and
  not measurement noise.

## Stable-only metrics

| Method | MAE µm | Median AE µm | RMSE µm | R² | nRMSE | Mean NLPD | Latent cov. | Total/oracle cov. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B | 1.802271 | 1.339809 | 2.728943 | 0.968873 | 0.036104 | 2.440425 | 0.8783 | 0.9522 |
| C | 2.076667 | 1.551698 | 3.013798 | 0.962036 | 0.039872 | 2.703817 | 0.9130 | 0.9130 |

B's NLPD/observation coverage use total variance including the learned nugget.
C's corresponding values use the held-out simulation's retrospective oracle
variance. The C oracle interval is not available for a genuinely unseen
simulation and is therefore not a deployable uncertainty interval.

## Paired result

- B improved `134` simulations; C improved
  `96`; ties `0`.
- `MAE_C − MAE_B = +0.274396 µm`,
  paired-bootstrap 95% CI
  `[+0.134941,
  +0.422091]`.
- `RMSE_C − RMSE_B = +0.284855 µm`,
  paired-bootstrap 95% CI
  `[+0.048306,
  +0.549011]`.

Negative differences favor C and positive differences favor B. A confidence
interval crossing zero does not support a robust superiority claim.

## Influence of unstable training simulations

- `B_learned_nugget`: full-population trained on the same stable held-outs `3.382290 µm`; stable-only refit `2.728943 µm`; change `-19.317%`; descriptive materiality `True`.
- `C_heteroskedastic`: full-population trained on the same stable held-outs `3.517802 µm`; stable-only refit `3.013798 µm`; change `-14.327%`; descriptive materiality `True`.

The 5% rule is a descriptive threshold, not a statistical test.

## Observation-treatment scale

- B median learned effective-nugget standard deviation:
  `1.776750 µm`; median fraction of fold training-target
  standard deviation:
  `0.114805`.
- C median stable target-summary bootstrap standard deviation:
  `0.007317 µm`; q95 `0.474441 µm`;
  maximum `1.149503 µm`.

These scales are not interchangeable: B can absorb unresolved variables and
fixed-kernel discrepancy, whereas C measures within-window median stability.

## Decision

**B is preferred for stable-window penetration depth.**

The paired point-prediction evidence is considered first. Calibration/NLPD,
training-set sensitivity, optimizer behavior, deployability, interpretation,
and runtime are secondary evidence. This decision does not prove causal input
effects and does not validate C's oracle interval for unseen simulations.
