# Week 4 Experiment 08 Notes: Thresholded Branin

## Setup

- Domain: `x1 in [-5,10], x2 in [0,15]`.
- Threshold: `29.12126111` (45th percentile, seed `2026`, sample size `20000`).
- Pool/test/initial/budget: `260` / `600` / `6` / `10`.
- Reference size requested for IVR/SUR: `1500`.
- SUR shortlist size requested: `40`.

## Best final methods

- Global: `gpr_fixed_or_existing` / `smallest_abs_mu` = `0.132`.
- q20: `gpr_fixed_or_existing` / `boundary_gated_diversified_straddle` = `0.350`.
- q30: `gpr_fixed_or_existing` / `boundary_gated_diversified_straddle` = `0.278`.

## New GP-regressor methods

- `gpr_boundary_weighted_ivr`: global/q20/q30 = `0.170` / `0.375` / `0.311`.
- `gpr_bernoulli_sur_refit`: global/q20/q30 = `0.273` / `0.375` / `0.289`.
- Best new GP-regressor method beats `randomized_straddle` on q20: `False`.
- Best new GP-regressor method beats `randomized_straddle` on q30: `False`.

## Caveats

- The GP-regressor membership probability is `Phi(mu / sigma)`, a heuristic latent probability rather than calibrated class probability.
- The GP-regressor SUR fantasy update keeps the current kernel hyperparameters fixed and uses an exact rank-one posterior update.
- q20/q30 are the primary boundary metrics; q10 is retained as a noisy diagnostic.
- Query distance and uncertainty-region fraction are diagnostics, not success criteria.
- Lower integrated Bernoulli uncertainty can still mean confident wrongness if the surrogate is miscalibrated.
