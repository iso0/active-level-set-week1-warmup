# Week 4 Experiment 08 Boundary-Weighted SUR Summary

Week 4 Experiment 08 tests boundary-weighted integrated variance reduction and Bernoulli stepwise uncertainty reduction on Branin, 4D Ackley, and 4D Hartmann.

## Run settings

- Quick mode: `True`.
- Reference size: `1500`.
- SUR shortlist size: `40`.
- GPC SUR shortlist size: `10`.
- GPC SUR limitation: Quick mode runs GPC SUR on all quick benchmarks with classifier SUR shortlist capped at 10.
- Total elapsed runtime for this script invocation: `66.4` seconds.

## Best final methods

| Benchmark | Global | q20 | q30 |
| --- | --- | --- | --- |
| Thresholded Branin | `gpr_fixed_or_existing` / `smallest_abs_mu` (0.132) | `gpr_fixed_or_existing` / `boundary_gated_diversified_straddle` (0.350) | `gpr_fixed_or_existing` / `boundary_gated_diversified_straddle` (0.278) |
| Thresholded 4D Ackley | `gpr_fixed_or_existing` / `smallest_abs_mu` (0.414) | `gpr_fixed_or_existing` / `gpr_bernoulli_sur_refit` (0.444) | `gpr_fixed_or_existing` / `gpr_bernoulli_sur_refit` (0.471) |
| Thresholded 4D Hartmann | `gpr_fixed_or_existing` / `expected_feasibility` (0.253) | `gpc_fixed_iso` / `classifier_uncertainty_repulsion` (0.412) | `gpr_fixed_or_existing` / `randomized_straddle` (0.429) |

## Interpretation Questions

### Thresholded Branin
1. Best new GPR SUR/IVR beats `randomized_straddle` on q20/q30: `False` / `False`.
2. `gpr_bernoulli_sur_refit` improves over cheap IVR on q20/q30: `False` / `True`.
3. Classifier SUR beats `classifier_uncertainty_repulsion` on q20/q30: `True` / `True`.
6. Integrated Bernoulli uncertainty correlation with q20/q30 error over all curves: `0.507727` / `0.563761`.
7. Cheap IVR reduces integrated uncertainty while worsening q20 versus randomized straddle: `False`.

### Thresholded 4D Ackley
1. Best new GPR SUR/IVR beats `randomized_straddle` on q20/q30: `True` / `True`.
2. `gpr_bernoulli_sur_refit` improves over cheap IVR on q20/q30: `True` / `True`.
3. Classifier SUR beats `classifier_uncertainty_repulsion` on q20/q30: `False` / `False`.
6. Integrated Bernoulli uncertainty correlation with q20/q30 error over all curves: `-0.184964` / `-0.131502`.
7. Cheap IVR reduces integrated uncertainty while worsening q20 versus randomized straddle: `False`.

### Thresholded 4D Hartmann
1. Best new GPR SUR/IVR beats `randomized_straddle` on q20/q30: `False` / `False`.
2. `gpr_bernoulli_sur_refit` improves over cheap IVR on q20/q30: `True` / `True`.
3. Classifier SUR beats `classifier_uncertainty_repulsion` on q20/q30: `False` / `False`.
6. Integrated Bernoulli uncertainty correlation with q20/q30 error over all curves: `-0.026642` / `0.028919`.
7. Cheap IVR reduces integrated uncertainty while worsening q20 versus randomized straddle: `True`.

## Cross-benchmark answer

Do not overclaim: this is a benchmark result for the current sklearn GP surrogates. If the new methods win on Branin/Hartmann but fail on Ackley, the correct thesis interpretation is that the acquisition objective may be useful but the harder Ackley geometry or surrogate calibration remains the bottleneck. If they reduce integrated uncertainty without improving q20/q30, the objective is misaligned under this surrogate.

q20/q30 remain the primary thesis metrics. Query distance, uncertainty-region fraction, and integrated Bernoulli uncertainty are diagnostics for explaining behavior, not standalone success criteria.
