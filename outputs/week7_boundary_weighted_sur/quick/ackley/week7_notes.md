# Week 7 Notes: Thresholded 4D Ackley

## Setup

- Domain: `[-5,5]^4`.
- Threshold: `10.33220251` (50th percentile, seed `3027`, sample size `100000`).
- Pool/test/initial/budget: `360` / `800` / `12` / `16`.
- Reference size requested for IVR/SUR: `1500`.
- SUR shortlist size requested: `40`.

## Best final methods

- Global: `gpr_fixed_or_existing` / `smallest_abs_mu` = `0.414`.
- q20: `gpr_fixed_or_existing` / `gpr_bernoulli_sur_refit` = `0.444`.
- q30: `gpr_fixed_or_existing` / `gpr_bernoulli_sur_refit` = `0.471`.

## New GP-regressor methods

- `gpr_boundary_weighted_ivr`: global/q20/q30 = `0.435` / `0.512` / `0.529`.
- `gpr_bernoulli_sur_refit`: global/q20/q30 = `0.426` / `0.444` / `0.471`.
- Best new GP-regressor method beats `randomized_straddle` on q20: `True`.
- Best new GP-regressor method beats `randomized_straddle` on q30: `True`.

## Caveats

- The GP-regressor membership probability is `Phi(mu / sigma)`, a heuristic latent probability rather than calibrated class probability.
- The GP-regressor SUR fantasy update keeps the current kernel hyperparameters fixed and uses an exact rank-one posterior update.
- q20/q30 are the primary boundary metrics; q10 is retained as a noisy diagnostic.
- Query distance and uncertainty-region fraction are diagnostics, not success criteria.
- Lower integrated Bernoulli uncertainty can still mean confident wrongness if the surrogate is miscalibrated.
