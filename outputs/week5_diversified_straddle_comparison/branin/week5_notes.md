# Week 5 Notes: Thresholded Branin

## New method

`diversified_straddle` keeps the straddle score but adds a diversity term:

`(1-alpha) * normalized_straddle + alpha * normalized_min_distance_to_labelled_set`

The default alpha is `0.25`. Distances are computed in scaled
input coordinates. This is a simple heuristic, not a theoretically proven
acquisition function.

## Main result

- Diversified final global error: `0.064`.
- Diversified final q20 near-boundary error: `0.259`.
- Diversified final q30 near-boundary error: `0.197`.
- Diversified median query distance: `21.850675`.

## Comparison to original methods

- Improves global error over best original method: `False`.
- Improves q20 error over best original method: `False`.
- Improves q30 error over best original method: `False`.
- Queries closer than the closest-query original method: `False`.
- Reduces q20 uncertainty-region fraction versus best original uncertainty method: `False`.
- Reduces q30 uncertainty-region fraction versus best original uncertainty method: `False`.

## Caveats

Query distance measures sampling behavior, not predictive correctness. Near-boundary
distance is a function-value proxy, not Euclidean contour distance. The
uncertainty-region fractions use GP-regression latent uncertainty, not calibrated
class probability. Alpha sensitivity was not run to keep runtime manageable.
