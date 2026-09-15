# Week 4 Experiment 04 Lookahead Notes: Thresholded 4D Ackley

## New method

The previous Week 4 Experiments 02–03 methods are preserved:

- `diversified_straddle`
- `boundary_gated_diversified_straddle`

The new `lookahead_boundary_uncertainty_reduction` first shortlists the top
`30` unlabelled candidates by straddle score:

`1.96 * sigma(x) - abs(mu(x))`

For each shortlisted candidate it creates fantasy `+1` and `-1` labelled
datasets, refits the GP posterior with the current fitted kernel held fixed,
and estimates expected reduction in:

`mean(max(0, 1.96 * sigma(x) - abs(mu(x))))`

over the current unlabelled pool. The current unlabelled pool, including the
candidate, is used as the acquisition reference set. No true function values,
true labels, true boundary distances, test labels, or q10/q20/q30 masks are
used during acquisition.

## Main result

- Lookahead final global error: `0.229`.
- Lookahead final q20 near-boundary error: `0.444`.
- Lookahead final q30 near-boundary error: `0.408`.
- Lookahead median query distance: `0.888686`.
- Lookahead global uncertainty-region fraction: `0.850`.
- Lookahead q20 uncertainty-region fraction: `0.917`.
- Lookahead q30 uncertainty-region fraction: `0.912`.
- Boundary-gated global error: `0.184`.
- Diversified global error: `0.182`.

## Comparison

- Improves global error over best original method: `False`.
- Improves global error over `straddle`: `False`.
- Improves global error over `randomized_straddle`: `False`.
- Improves global error over `diversified_straddle`: `False`.
- Improves global error over `boundary_gated_diversified_straddle`: `False`.
- Improves q20 error over best original method: `False`.
- Improves q20 error over `straddle`: `False`.
- Improves q20 error over `randomized_straddle`: `False`.
- Improves q20 error over `diversified_straddle`: `False`.
- Improves q20 error over `boundary_gated_diversified_straddle`: `False`.
- Improves q30 error over best original method: `False`.
- Improves q30 error over `straddle`: `False`.
- Improves q30 error over `randomized_straddle`: `False`.
- Improves q30 error over `diversified_straddle`: `False`.
- Improves q30 error over `boundary_gated_diversified_straddle`: `False`.
- Queries closer than `diversified_straddle`: `True`.
- Queries closer than `straddle`: `True`.
- Queries closer than `randomized_straddle`: `True`.
- Queries closer than `boundary_gated_diversified_straddle`: `True`.
- Reduces q20 uncertainty-region fraction versus `diversified_straddle`: `False`.
- Reduces q30 uncertainty-region fraction versus `diversified_straddle`: `False`.

## Interpretation

The result suggests that under the current GP-regression surrogate, one-step aggregate uncertainty reduction does not dominate simpler straddle variants. Possible reasons are that fantasy probabilities are not calibrated, aggregate uncertainty reduction may not align with true boundary correctness, shortlist candidates may be too restrictive or too broad, the GP classifier transition may be needed, or a geometric boundary-distance metric and better boundary-specific objective may be needed.

## Caveats

Query distance measures sampling behavior, not predictive correctness. Near-boundary
distance is a function-value proxy, not Euclidean contour distance. The
uncertainty-region fractions use GP-regression latent uncertainty, not calibrated
class probability. The fantasy label probabilities use
`Phi(mu / max(sigma, 1e-9))`, which is not calibrated GP-classifier probability.
Lookahead shortlist sensitivity was skipped to keep runtime manageable.
