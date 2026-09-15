# Week 4 Experiment 01 Boundary Metric Summary

This summary compares the Week 2 Branin and Week 3 Ackley evaluations
using boundary-focused metrics in addition to global test error.

| Benchmark | Best global | Best q10 boundary | Best q20 boundary | Best q30 boundary | Closest median query distance | Conclusion |
| --- | --- | --- | --- | --- | --- | --- |
| Thresholded Branin | randomized_straddle | straddle | smallest_abs_mu | randomized_straddle | smallest_abs_mu | At least one near-boundary ranking differs from the global-error ranking. |
| Thresholded 4D Ackley | straddle | randomized_straddle | randomized_straddle | randomized_straddle | smallest_abs_mu | At least one near-boundary ranking differs from the global-error ranking. |

## Caveats

- Near-boundary subsets use `abs(f(x)-threshold)` percentiles, not Euclidean contour distance.
- The recommended query-distance-over-budget plot uses median and q25/q75 bands; the older mean/std plot is kept for continuity.
- The GP uncertainty-region metric is latent-regression uncertainty, not calibrated class probability.
