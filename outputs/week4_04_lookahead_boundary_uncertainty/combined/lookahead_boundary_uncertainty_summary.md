# Week 4 Experiment 04 Lookahead Boundary-Uncertainty Summary

`lookahead_boundary_uncertainty_reduction` uses shortlist size `30`.
Reference set: current unlabelled pool, including the candidate.
Fantasy refit: fixed current kernel hyperparameters; posterior refit only.
Lookahead shortlist sensitivity was skipped to keep runtime manageable.

| Benchmark | Global vs best original | Global vs straddle | Global vs gated | q20 vs best original | q20 vs straddle | q20 vs gated | q30 vs best original | q30 vs randomized | q30 vs gated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Thresholded Branin | True | True | True | True | True | True | True | True | True |
| Thresholded 4D Ackley | False | False | False | False | False | False | False | False | False |

## Interpretation

Negative differences in `lookahead_vs_baselines_table.csv` are better for error, uncertainty, and query-distance metrics.
For query distance, smaller means closer to the true threshold in function-value space, but this is sampling behavior rather than predictive correctness.
If lookahead improves, this suggests expected aggregate boundary-uncertainty reduction is more aligned with active level-set estimation than local-only acquisition rules.
If lookahead does not improve, likely causes include uncalibrated fantasy probabilities, imperfect alignment between latent uncertainty and true boundary correctness, shortlist sensitivity, and the need for a GP classifier or better boundary-specific objective.
