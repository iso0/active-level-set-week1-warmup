# Week 4 Boundary Metrics: Thresholded 4D Ackley

## What changed

This evaluation keeps the same pool-based active-learning runs, GP-regression
stand-in, thresholds, seeds, and acquisition rules. It adds boundary-focused
metrics to complement global test-label misclassification error.

## Metrics

- Global error: fraction of all exact test labels predicted incorrectly.
- Near-boundary error q10/q20/q30: error restricted to the closest 10%, 20%,
  and 30% of test points by `abs(f(x) - threshold)`.
- Query distance: `abs(f(x_query) - threshold)` for each newly acquired point.
- Uncertainty-region fraction: fraction of test points with
  `abs(mu(x)) <= 1.96 * sigma(x)`.
- Near-boundary uncertainty-region fraction: the same uncertainty proxy
  restricted to q10/q20/q30 near-boundary test subsets.

## Main findings

- Best final global error: `straddle` with mean `0.168`.
- Best final q10 near-boundary error: `randomized_straddle` with mean `0.451`.
- Best final q20 near-boundary error: `randomized_straddle`.
- Best final q30 near-boundary error: `randomized_straddle`.
- Closest median query distance: `smallest_abs_mu` with median `0.839807`.

## Interpretation guidance

- q10 is the hardest and noisiest near-boundary diagnostic because it contains
  only the points closest to the true threshold.
- q20 is a good primary near-boundary metric for comparing methods.
- q30 is a more stable boundary-region confirmation metric.
- Query distance measures sampling behavior, not predictive correctness.
- A small query distance does not guarantee a good model.
- Latent uncertainty-region fraction measures model uncertainty, not
  correctness.
- A method can become confidently wrong, so uncertainty shrinkage alone is not
  proof that the true boundary is learned.
- The recommended query-distance plot is
  `query_distance_to_boundary_over_budget_median_iqr.png`; the mean/std version
  is kept for continuity but is harder to read on a log scale.

## Caveats

Near-boundary distance is measured in function-value space, not Euclidean
distance to the geometric contour. The uncertainty-region fraction uses the
latent GP-regression mean and standard deviation; it is not calibrated class
probability. These metrics strengthen the evaluation, but they do not replace a
proper GP classifier or a geometric boundary-distance metric.
