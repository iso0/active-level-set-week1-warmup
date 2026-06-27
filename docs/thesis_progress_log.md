# Thesis Progress Log

## Thesis Project

- Title: Sample-Efficient Active Level-Set Estimation, with an Application to Melt-Pool Regime Boundaries.
- Supervisor: Ioan.
- Examiner: not yet recorded in this repository.
- Start date: not yet recorded in this repository.
- Due date: not yet recorded in this repository.
- Main research goal: develop and evaluate sample-efficient active-learning methods for estimating threshold boundaries, with the longer-term application to melt-pool regime boundaries in a four-dimensional laser-metal process-parameter space.

## Week 1

- Built a `make_moons` sanity check to verify that the active-learning loop visibly contracts an uncertain boundary region.
- Built a thresholded-Branin active level-set experiment with deterministic exact labels.
- Used `GaussianProcessRegressor` on `{-1,+1}` labels as a plumbing stand-in, not as the final GP classifier.
- Used the simple acquisition rule `argmin |mu(x)|`.
- Branin threshold: 45th percentile over a reproducible 20,000-point sample.
- Branin settings: three seeds, pool size 1,500, test size 4,000, initial labelled size 6, final budget 50.
- Main Branin result: mean test error decreased from about 0.337 to about 0.061, and all three seeds finished below their initial error.
- Main caveat: the metric was global test-label misclassification error, not a boundary-specific metric.

## Week 2

- Compared acquisition rules on thresholded Branin using the same pool, test set, initial labelled points, GP model, threshold, and budget per seed.
- Methods: `random`, `smallest_abs_mu`, `straddle`, `randomized_straddle`, and `expected_feasibility`.
- Settings: five seeds, pool size 1,500, test size 4,000, initial labelled size 6, final budget 50.
- Main final mean global errors:
  - `random`: 0.119400
  - `smallest_abs_mu`: 0.065900
  - `straddle`: 0.062000
  - `randomized_straddle`: 0.060200
  - `expected_feasibility`: 0.066350
- Best global method: `randomized_straddle`.
- Fixed 8% test-error tolerance result: `randomized_straddle` reached the tolerance fastest on the mean curve at n=32; `straddle` reached n=35; `expected_feasibility` reached n=37; `smallest_abs_mu` reached n=39; `random` did not reach it.
- Main caveat: the evaluation was still mostly global classification error.

## Week 3

- Moved from 2D Branin to a four-dimensional benchmark because the target melt-pool process-parameter space is 4D.
- Initially implemented a controlled synthetic 4D boundary function. It was useful for software plumbing but was replaced as the main Week 3 result because Ioan asked for named 4D datasets or benchmarks.
- Selected thresholded 4D Ackley as the main named benchmark.
- Ackley domain: `[-5,5]^4`, with GP inputs scaled to `[0,1]^4`.
- Threshold: 50th percentile over a reproducible 100,000-point sample.
- Settings: five seeds, pool size 4,000, test size 10,000, initial labelled size 12, final budget 80.
- Added visual diagnostics: value distribution, pairwise label projections, exact 2D slices, query-location projections, and model boundary slice snapshots.
- Main final mean global errors:
  - `random`: 0.282660
  - `smallest_abs_mu`: 0.236240
  - `straddle`: 0.168400
  - `randomized_straddle`: 0.175380
  - `expected_feasibility`: 0.189820
- Best global method: `straddle`.
- Tolerance result: the mean curve reached 0.20 for `straddle` and `randomized_straddle` at n=58, and for `expected_feasibility` at n=75. No mean curve reached 0.16 or stricter tolerances by n=80.
- Main caveat: 2D projections and slices are diagnostics only; they do not show the full 4D boundary.

## Week 4

- Added boundary-focused metrics because global test-label error is not enough for a level-set estimation thesis.
- New metric 1: near-boundary error on the closest 10%, 20%, and 30% of test points by `abs(f(x) - threshold)`.
- New metric 2: query distance to true boundary, `abs(f(x_query) - threshold)`, for every acquired point.
- New metric 3: latent uncertainty-region fraction, the fraction of test points satisfying `abs(mu(x)) <= 1.96 * sigma(x)`.
- Kept global test-label error for comparison.
- Branin Week 4 findings:
  - Best final global error: `randomized_straddle`, mean 0.060.
  - Best final q10 near-boundary error: `straddle`, mean 0.358.
  - Best final q20 near-boundary error: `smallest_abs_mu`.
  - Best final q30 near-boundary error: `randomized_straddle`.
  - Closest median query distance: `smallest_abs_mu`, median 12.038580 in Branin function-value units.
- Ackley Week 4 findings:
  - Best final global error: `straddle`, mean 0.168.
  - Best final q10 near-boundary error: `randomized_straddle`, mean 0.451.
  - Best final q20 and q30 near-boundary errors: `randomized_straddle`.
  - Closest median query distance: `smallest_abs_mu`, median 0.839807 in Ackley function-value units.
- Main interpretation: boundary-focused metrics partially change the ranking. For Branin, the global winner remains competitive but q10 and q20 boundary rankings differ. For Ackley, randomized straddle is best near the boundary even though straddle is best globally.
- Main caveats:
  - Boundary distance is measured in function-value space, not Euclidean distance to the geometric contour.
  - The uncertainty-region fraction uses GP-regression latent uncertainty, not calibrated class probability.
  - The model is still a GP regressor stand-in, not the final GP classifier.
  - Runtime is about 5-6 minutes because the script computes GP mean and standard deviation on full test sets at every budget.

## Open Next Steps

- Implement a lookahead or boundary-uncertainty acquisition rule after the evaluation metrics are stable.
- Add additional named 4D benchmarks such as thresholded Rosenbrock and Rastrigin.
- Build a real laser-data loader skeleton and document expected columns, units, labels, and preprocessing.
- Transition from `GaussianProcessRegressor` on `{-1,+1}` labels to a proper GP classifier or a more defensible surrogate.
- Investigate a geometric boundary-distance metric if feasible, especially for 2D Branin and controlled 2D/4D slices.
