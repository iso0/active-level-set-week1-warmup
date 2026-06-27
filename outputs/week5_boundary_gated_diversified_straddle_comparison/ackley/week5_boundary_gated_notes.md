# Week 5 Boundary-Gated Notes: Thresholded 4D Ackley

## New method

The previous `diversified_straddle` is preserved. It mixes straddle and generic
input-space diversity over the whole unlabelled pool:

`(1-alpha) * normalized_straddle + alpha * normalized_min_distance_to_labelled_set`

The new `boundary_gated_diversified_straddle` first keeps only the top
`0.10` fraction of unlabelled candidates by
`1.96 * sigma(x) - abs(mu(x))`, with a minimum shortlist size of
`25` when possible. Inside that shortlist it
uses:

`(1-beta) * normalized_straddle + beta * normalized_min_distance_to_labelled_set`

The default beta is `0.5`. Distances are computed in scaled
input coordinates. This is a heuristic, not a theoretically proven acquisition
function.

## Main result

- Boundary-gated final global error: `0.184`.
- Boundary-gated final q20 near-boundary error: `0.413`.
- Boundary-gated final q30 near-boundary error: `0.376`.
- Boundary-gated median query distance: `1.274541`.
- Boundary-gated q20 uncertainty-region fraction: `0.872`.
- Boundary-gated q30 uncertainty-region fraction: `0.865`.
- Previous diversified final global error: `0.182`.

## Comparison

- Improves global error over best original method: `False`.
- Improves global error over `straddle`: `False`.
- Improves global error over `randomized_straddle`: `False`.
- Improves global error over `diversified_straddle`: `False`.
- Improves q20 error over best original method: `False`.
- Improves q20 error over `straddle`: `True`.
- Improves q20 error over `randomized_straddle`: `False`.
- Improves q20 error over `diversified_straddle`: `True`.
- Improves q30 error over best original method: `False`.
- Improves q30 error over `straddle`: `False`.
- Improves q30 error over `randomized_straddle`: `False`.
- Improves q30 error over `diversified_straddle`: `True`.
- Queries closer than `diversified_straddle`: `True`.
- Queries closer than `straddle`: `True`.
- Queries closer than `randomized_straddle`: `False`.
- Reduces q20 uncertainty-region fraction versus `diversified_straddle`: `True`.
- Reduces q30 uncertainty-region fraction versus `diversified_straddle`: `True`.

## Interpretation

The result suggests that diversity can help when it is restricted to boundary-relevant candidates. This supports the hypothesis that boundary coverage matters, but only after candidate points are filtered by boundary/uncertainty relevance.

## Caveats

Query distance measures sampling behavior, not predictive correctness. Near-boundary
distance is a function-value proxy, not Euclidean contour distance. The
uncertainty-region fractions use GP-regression latent uncertainty, not calibrated
class probability. Gate/beta sensitivity was not run to keep runtime manageable.
