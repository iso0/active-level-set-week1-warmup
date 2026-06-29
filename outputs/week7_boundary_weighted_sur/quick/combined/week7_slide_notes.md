# Week 7 Slide Notes

## Question

Can a boundary-weighted global uncertainty-reduction rule beat pointwise rules such as straddle and randomized straddle?

## Methods

- `gpr_boundary_weighted_ivr`: straddle-gated posterior variance reduction weighted by Bernoulli membership uncertainty.
- `gpr_bernoulli_sur_refit`: expected reduction in integrated `p(1-p)` after fantasy `+1/-1` updates.
- `gpc_bernoulli_sur_refit`: same idea with fixed GP-classifier probabilities, run in limited mode if needed.

## Best final rows

- branin global_error: `gpr_fixed_or_existing` / `smallest_abs_mu` = `0.132`.
- branin near_boundary_error_q20: `gpr_fixed_or_existing` / `boundary_gated_diversified_straddle` = `0.350`.
- branin near_boundary_error_q30: `gpr_fixed_or_existing` / `boundary_gated_diversified_straddle` = `0.278`.
- ackley global_error: `gpr_fixed_or_existing` / `smallest_abs_mu` = `0.414`.
- ackley near_boundary_error_q20: `gpr_fixed_or_existing` / `gpr_bernoulli_sur_refit` = `0.444`.
- ackley near_boundary_error_q30: `gpr_fixed_or_existing` / `gpr_bernoulli_sur_refit` = `0.471`.
- hartmann4 global_error: `gpr_fixed_or_existing` / `expected_feasibility` = `0.253`.
- hartmann4 near_boundary_error_q20: `gpc_fixed_iso` / `classifier_uncertainty_repulsion` = `0.412`.
- hartmann4 near_boundary_error_q30: `gpr_fixed_or_existing` / `randomized_straddle` = `0.429`.

## Message

Use q20/q30 as the main boundary-estimation metrics. Do not claim novelty beyond a literature-inspired SUR/IVR benchmark. If uncertainty falls without q20/q30 improvement, describe objective-surrogate misalignment rather than success.
