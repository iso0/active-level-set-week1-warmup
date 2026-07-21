# Week 4 Experiment 08 Notes: Thresholded 4D Hartmann

## Setup

- Domain: `[0,1]^4`.
- Threshold: `-0.97797833` (50th percentile, seed `2026`, sample size `100000`).
- Pool/test/initial/budget: `4000` / `10000` / `12` / `80`.
- Reference size requested for IVR/SUR: `1500`.
- SUR shortlist size requested: `40`.

## Best final methods

- Global: `gpc_fixed_iso` / `classifier_uncertainty_repulsion` = `0.124`.
- q20: `gpr_fixed_or_existing` / `expected_feasibility` = `0.380`.
- q30: `gpr_fixed_or_existing` / `expected_feasibility` = `0.326`.

## New GP-regressor methods

- `gpr_boundary_weighted_ivr`: global/q20/q30 = `0.128` / `0.381` / `0.328`.
- `gpr_bernoulli_sur_refit`: global/q20/q30 = `0.133` / `0.393` / `0.339`.
- Best new GP-regressor method beats `randomized_straddle` on q20: `True`.
- Best new GP-regressor method beats `randomized_straddle` on q30: `True`.

## Caveats

- The GP-regressor membership probability is `Phi(mu / sigma)`, a heuristic latent probability rather than calibrated class probability.
- The GP-regressor SUR fantasy update keeps the current kernel hyperparameters fixed and uses an exact rank-one posterior update.
- q20/q30 are the primary boundary metrics; q10 is retained as a noisy diagnostic.
- Query distance and uncertainty-region fraction are diagnostics, not success criteria.
- Lower integrated Bernoulli uncertainty can still mean confident wrongness if the surrogate is miscalibrated.
