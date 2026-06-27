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

## Main findings

- Best final global error: `straddle` with mean `0.168`.
- Best final q10 near-boundary error: `randomized_straddle` with mean `0.451`.
- Best final q20 near-boundary error: `randomized_straddle`.
- Best final q30 near-boundary error: `randomized_straddle`.
- Closest median query distance: `smallest_abs_mu` with median `0.839807`.

## Caveats

Near-boundary distance is measured in function-value space, not Euclidean
distance to the geometric contour. The uncertainty-region fraction uses the
latent GP-regression mean and standard deviation; it is not calibrated class
probability. These metrics strengthen the evaluation, but they do not replace a
proper GP classifier or a geometric boundary-distance metric.
