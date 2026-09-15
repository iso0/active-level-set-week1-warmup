# Week 4 Experiment 08 Boundary-Weighted SUR Summary

Week 4 Experiment 08 tests boundary-weighted integrated variance reduction and Bernoulli stepwise uncertainty reduction on Branin, 4D Ackley, and 4D Hartmann.

## Run settings

- Quick mode: `False`.
- Reference size: `1500`.
- SUR shortlist size: `40`.
- GPC SUR shortlist size: `15`.
- GPC SUR limitation: Full mode limits expensive GPC SUR to Branin and Hartmann4 for seed 0 only, with classifier SUR shortlist capped at 15; GPR methods and GPC baselines run fully.
- Total elapsed runtime for this script invocation: `1735.1` seconds.

## Best final methods

| Benchmark | Global | q20 | q30 |
| --- | --- | --- | --- |
| Thresholded Branin | `gpr_fixed_or_existing` / `randomized_straddle` (0.060) | `gpr_fixed_or_existing` / `smallest_abs_mu` (0.247) | `gpr_fixed_or_existing` / `randomized_straddle` (0.186) |
| Thresholded 4D Ackley | `gpr_fixed_or_existing` / `straddle` (0.168) | `gpr_fixed_or_existing` / `randomized_straddle` (0.408) | `gpr_fixed_or_existing` / `randomized_straddle` (0.368) |
| Thresholded 4D Hartmann | `gpc_fixed_iso` / `classifier_uncertainty_repulsion` (0.124) | `gpr_fixed_or_existing` / `expected_feasibility` (0.380) | `gpr_fixed_or_existing` / `expected_feasibility` (0.326) |

## Interpretation Questions

### Thresholded Branin
1. Best new GPR SUR/IVR beats `randomized_straddle` on q20/q30: `False` / `False`.
2. `gpr_bernoulli_sur_refit` improves over cheap IVR on q20/q30: `False` / `False`.
3. Classifier SUR beats `classifier_uncertainty_repulsion` on q20/q30: `True` / `True`.
6. Integrated Bernoulli uncertainty correlation with q20/q30 error over all curves: `0.324121` / `0.340811`.
7. Cheap IVR reduces integrated uncertainty while worsening q20 versus randomized straddle: `True`.

### Thresholded 4D Ackley
1. Best new GPR SUR/IVR beats `randomized_straddle` on q20/q30: `False` / `False`.
2. `gpr_bernoulli_sur_refit` improves over cheap IVR on q20/q30: `False` / `False`.
3. Classifier SUR was not run for this benchmark in the configured limited mode.
6. Integrated Bernoulli uncertainty correlation with q20/q30 error over all curves: `0.278372` / `0.313117`.
7. Cheap IVR reduces integrated uncertainty while worsening q20 versus randomized straddle: `False`.

### Thresholded 4D Hartmann
1. Best new GPR SUR/IVR beats `randomized_straddle` on q20/q30: `True` / `True`.
2. `gpr_bernoulli_sur_refit` improves over cheap IVR on q20/q30: `False` / `False`.
3. Classifier SUR beats `classifier_uncertainty_repulsion` on q20/q30: `True` / `True`.
6. Integrated Bernoulli uncertainty correlation with q20/q30 error over all curves: `0.314729` / `0.317398`.
7. Cheap IVR reduces integrated uncertainty while worsening q20 versus randomized straddle: `False`.

## Cross-benchmark answer

Do not overclaim: this is a benchmark result for the current sklearn GP surrogates. If the new methods win on Branin/Hartmann but fail on Ackley, the correct thesis interpretation is that the acquisition objective may be useful but the harder Ackley geometry or surrogate calibration remains the bottleneck. If they reduce integrated uncertainty without improving q20/q30, the objective is misaligned under this surrogate.

q20/q30 remain the primary thesis metrics. Query distance, uncertainty-region fraction, and integrated Bernoulli uncertainty are diagnostics for explaining behavior, not standalone success criteria.
