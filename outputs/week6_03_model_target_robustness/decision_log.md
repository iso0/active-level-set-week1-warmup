# Week 6 Phase 3 decision log

## Why these tests were run

Simple models were tested because a Gaussian process is not justified merely by being flexible. Ridge supplies a transparent linear baseline, and degree-2 Polynomial Ridge adds all squares and pairwise interactions without opening an unrestricted high-degree search. Degree 2 is the maximum because higher degrees would rapidly expand complexity, become harder to interpret, and create a new tuning study outside Phase 3.

ARD was excluded so that kernel comparisons change only smoothness and nugget treatment. All GP lengthscales remain isotropic. The ConstantKernel multiplies the base covariance and controls vertical signal variance; it does not add a constant prediction to the mean. WhiteKernel is compared inside every family to test whether a learned effective nugget remains useful under RBF, Matérn 3/2, and Matérn 5/2.

Target definitions were changed one factor at a time: window duration, domain cutoff, or the final-50 aggregation. T5 is a reference rather than an automatic candidate because it is not domain controlled and can include shutdown or post-exit behaviour. A between-definition shift changes the measured target; a GP nugget describes unresolved effective variation under a fixed target/model. Comparing their scales is therefore descriptive, not an identity.

## Phase 3A — simple-model evidence

### Melt-pool width

- linear_ridge: candidate − current-GP RMSE +2.8551 µm, 95% CI [+1.2856, +4.5685] µm; competitive=False.
- polynomial_ridge_degree2: candidate − current-GP RMSE +0.0290 µm, 95% CI [-0.1439, +0.1923] µm; competitive=True.
- Final point-model decision: `polynomial_ridge_degree2`.
- Reason: polynomial_ridge_degree2 is statistically or practically competitive with the provisional GP. The simpler point model is selected for parsimony; it does not supply GP-style predictive intervals.

### Melt-pool length

- linear_ridge: candidate − current-GP RMSE +16.4413 µm, 95% CI [+11.4827, +21.4797] µm; competitive=False.
- polynomial_ridge_degree2: candidate − current-GP RMSE +6.2740 µm, 95% CI [+3.9694, +8.5963] µm; competitive=False.
- Final point-model decision: `matern52_learned_nugget`.
- Reason: Neither Ridge baseline is statistically or practically competitive with the provisional robust GP; retain the GP.

### Penetration depth below original surface

- linear_ridge: candidate − current-GP RMSE +1.9035 µm, 95% CI [+1.4310, +2.3401] µm; competitive=False.
- polynomial_ridge_degree2: candidate − current-GP RMSE +1.1596 µm, 95% CI [+0.7096, +1.5701] µm; competitive=False.
- Final point-model decision: `matern32_learned_nugget`.
- Reason: Neither Ridge baseline is statistically or practically competitive with the provisional robust GP; retain the GP.

## Phase 3B — kernel and nugget evidence

### Melt-pool width

- RBF, learned nugget − no nugget: RMSE -5.6674 µm, 95% CI [-8.2989, -3.2602] µm; learned nugget robustly improves MAE and RMSE.
- Matérn 3/2, learned nugget − no nugget: RMSE -1.3411 µm, 95% CI [-2.6882, -0.4199] µm; learned nugget robustly improves MAE and RMSE.
- Matérn 5/2, learned nugget − no nugget: RMSE -2.2006 µm, 95% CI [-4.0314, -0.8642] µm; learned nugget robustly improves MAE and RMSE.
- Provisional robust GP: `matern32_learned_nugget`.
- Replacement of Matérn 3/2 + nugget: False.
- Reason: No alternative jointly showed robust MAE and RMSE gains, acceptable calibration, and stable optimization; retain Matérn 3/2 + learned nugget for parsimony and continuity.

### Melt-pool length

- RBF, learned nugget − no nugget: RMSE -29.0153 µm, 95% CI [-39.5305, -20.7168] µm; learned nugget robustly improves MAE and RMSE.
- Matérn 3/2, learned nugget − no nugget: RMSE -6.3499 µm, 95% CI [-9.8468, -3.6399] µm; learned nugget robustly improves MAE and RMSE.
- Matérn 5/2, learned nugget − no nugget: RMSE -11.8124 µm, 95% CI [-17.2678, -7.5712] µm; learned nugget robustly improves MAE and RMSE.
- Provisional robust GP: `matern52_learned_nugget`.
- Replacement of Matérn 3/2 + nugget: True.
- Reason: matern52_learned_nugget satisfies the predeclared replacement rule and has the lowest RMSE among eligible robust replacements.

### Penetration depth below original surface

- RBF, learned nugget − no nugget: RMSE -2.0884 µm, 95% CI [-2.8386, -1.3699] µm; learned nugget robustly improves MAE and RMSE.
- Matérn 3/2, learned nugget − no nugget: RMSE -0.3079 µm, 95% CI [-0.5759, -0.0657] µm; learned nugget robustly improves MAE and RMSE.
- Matérn 5/2, learned nugget − no nugget: RMSE -0.7805 µm, 95% CI [-1.1962, -0.4068] µm; learned nugget robustly improves MAE and RMSE.
- Provisional robust GP: `matern32_learned_nugget`.
- Replacement of Matérn 3/2 + nugget: False.
- Reason: No alternative jointly showed robust MAE and RMSE gains, acceptable calibration, and stable optimization; retain Matérn 3/2 + learned nugget for parsimony and continuity.

## Phase 3C — target-definition evidence

### Melt-pool width

- Largest median absolute shift is T5: 7.4403 µm (q95 143.8667 µm).
- Selected definition: `T0`.
- Sensitivity substantial: True.
- Reason: No alternative jointly improves physical interpretation, temporal stability, availability, paired predictability, and domain-exit control. T0 is retained; large shifts, if present, are reported as target-definition uncertainty.
- Physical quantity change: None; retain the current late-active T0 quantity.

### Melt-pool length

- Largest median absolute shift is T5: 20.4939 µm (q95 485.6823 µm).
- Selected definition: `T3`.
- Sensitivity substantial: True.
- Reason: T3 uniquely satisfies the physical, stability, availability, paired-predictability, contamination, and optimization criteria.
- Physical quantity change: The selected target is the late-active response at an earlier 85% +X-domain cutoff rather than at the current 90% cutoff.

### Penetration depth below original surface

- Largest median absolute shift is T5: 7.9953 µm (q95 58.7970 µm).
- Selected definition: `T0`.
- Sensitivity substantial: True.
- Reason: No alternative jointly improves physical interpretation, temporal stability, availability, paired predictability, and domain-exit control. T0 is retained; large shifts, if present, are reported as target-definition uncertainty.
- Physical quantity change: None; retain the current late-active T0 quantity.

## Remaining limitations and deferred work

- Exact LOO measures interpolation/generalization across these simulation settings; it does not establish causal feature effects.
- A learned nugget can absorb target-definition variability, omitted structure, kernel mismatch, and numerical/model discrepancy. It is not evidence of stochastic simulator noise.
- Phase 3C intentionally holds one GP configuration fixed per response; it does not re-search kernels for every alternative target.
- Target physical validity still depends on the monitor geometry and the active-domain control assumptions validated in Phase 1.
- Feature effects, ARD, kinetic energy, total height, active learning, and level-set estimation remain deferred to later explicitly scoped phases.
