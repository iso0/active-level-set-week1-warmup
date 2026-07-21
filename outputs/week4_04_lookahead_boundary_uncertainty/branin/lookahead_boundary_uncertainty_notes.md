# Week 4 Experiment 04 Lookahead Notes: Thresholded Branin

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

- Lookahead final global error: `0.056`.
- Lookahead final q20 near-boundary error: `0.235`.
- Lookahead final q30 near-boundary error: `0.175`.
- Lookahead median query distance: `20.954706`.
- Lookahead global uncertainty-region fraction: `0.284`.
- Lookahead q20 uncertainty-region fraction: `0.478`.
- Lookahead q30 uncertainty-region fraction: `0.417`.
- Boundary-gated global error: `0.063`.
- Diversified global error: `0.064`.

## Comparison

- Improves global error over best original method: `True`.
- Improves global error over `straddle`: `True`.
- Improves global error over `randomized_straddle`: `True`.
- Improves global error over `diversified_straddle`: `True`.
- Improves global error over `boundary_gated_diversified_straddle`: `True`.
- Improves q20 error over best original method: `True`.
- Improves q20 error over `straddle`: `True`.
- Improves q20 error over `randomized_straddle`: `True`.
- Improves q20 error over `diversified_straddle`: `True`.
- Improves q20 error over `boundary_gated_diversified_straddle`: `True`.
- Improves q30 error over best original method: `True`.
- Improves q30 error over `straddle`: `True`.
- Improves q30 error over `randomized_straddle`: `True`.
- Improves q30 error over `diversified_straddle`: `True`.
- Improves q30 error over `boundary_gated_diversified_straddle`: `True`.
- Queries closer than `diversified_straddle`: `True`.
- Queries closer than `straddle`: `False`.
- Queries closer than `randomized_straddle`: `False`.
- Queries closer than `boundary_gated_diversified_straddle`: `False`.
- Reduces q20 uncertainty-region fraction versus `diversified_straddle`: `True`.
- Reduces q30 uncertainty-region fraction versus `diversified_straddle`: `True`.

## Interpretation

The result suggests that directly optimizing expected reduction in aggregate boundary uncertainty can improve sample efficiency. This is more aligned with active level-set estimation than local-only acquisition rules. Still, the method is heuristic because it uses GP-regression fantasy probabilities, not a calibrated GP classifier.

## Caveats

Query distance measures sampling behavior, not predictive correctness. Near-boundary
distance is a function-value proxy, not Euclidean contour distance. The
uncertainty-region fractions use GP-regression latent uncertainty, not calibrated
class probability. The fantasy label probabilities use
`Phi(mu / max(sigma, 1e-9))`, which is not calibrated GP-classifier probability.
Lookahead shortlist sensitivity was skipped to keep runtime manageable.
