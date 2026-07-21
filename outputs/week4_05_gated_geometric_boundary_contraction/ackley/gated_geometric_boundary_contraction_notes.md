# Week 4 Experiment 05 Gated GBC Notes: Thresholded 4D Ackley

## New method

The previous Week 4 Experiments 02–03 methods are preserved:

- `diversified_straddle`
- `boundary_gated_diversified_straddle`

The new `gated_geometric_boundary_contraction` first keeps the top
`200` unlabelled candidates by straddle score:

`1.96 * sigma(x) - abs(mu(x))`

Inside this boundary-relevant shortlist it computes:

`normalized_curvature * normalized_uncertainty * boundary_weight * repulsion`

Curvature is a finite-difference diagonal-Hessian proxy of the GP posterior
mean in scaled coordinates. The boundary weight uses
`Phi(mu / sqrt(1 + sigma^2))` as a GP-regression latent probability heuristic,
then maps it to `1 - 2 * abs(p - 0.5)`. Repulsion uses distance to the nearest
currently labelled point with fixed bandwidth `0.15`.

## Main result

- GBC final global error: `0.200`.
- GBC final q20 near-boundary error: `0.422`.
- GBC final q30 near-boundary error: `0.385`.
- GBC median query distance: `1.292692`.
- GBC global uncertainty-region fraction: `0.713`.
- GBC q20 uncertainty-region fraction: `0.838`.
- GBC q30 uncertainty-region fraction: `0.834`.
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
- Queries closer than `straddle`: `False`.
- Queries closer than `randomized_straddle`: `False`.
- Queries closer than `boundary_gated_diversified_straddle`: `False`.
- Reduces q20 uncertainty-region fraction versus `diversified_straddle`: `True`.
- Reduces q30 uncertainty-region fraction versus `diversified_straddle`: `True`.

## Interpretation

The result suggests that finite-difference curvature under the current GP-regression surrogate is not reliably aligned with true boundary classification accuracy. Possible reasons are noisy curvature estimates, a crude diagonal Hessian approximation, a GP regressor surrogate that does not represent the boundary well enough, input-space curvature that does not match useful boundary information, or the need to transition to a GP classifier.

## Caveats

Query distance measures sampling behavior, not predictive correctness. Near-boundary
distance is a function-value proxy, not Euclidean contour distance. The
uncertainty-region fractions use GP-regression latent uncertainty, not calibrated
class probability. GBC is heuristic; curvature is estimated from the GP
posterior mean, not from the true function. The finite-difference Hessian uses
only diagonal terms for speed. Curvature is evaluated only inside a
straddle-gated shortlist. A lower uncertainty-region fraction does not
necessarily imply correctness.
