# Week 6 GP-Classifier Notes: Thresholded 4D Ackley

## What changed

Weeks 1-5 used `GaussianProcessRegressor` on `{-1,+1}` labels as a warm-up
surrogate. Week 6 uses `GaussianProcessClassifier` and classifier-native
acquisition rules based on `predict_proba`.

The GP classifier uses a fixed RBF kernel with length scale `0.25`
and `optimizer=None` for runtime stability and reproducibility. This is a
practical approximation, not a final modelling choice.

## Classifier acquisitions

- `random`: random pool point.
- `classifier_margin`: largest `1 - 2*abs(p_plus - 0.5)`.
- `classifier_entropy`: largest binary entropy. For binary classification this
  is monotone-equivalent to margin, so it may select the same points.
- `classifier_gated_diversity`: top classifier-margin shortlist, then
  uncertainty/diversity mixture.
- `classifier_uncertainty_repulsion`: top classifier-margin shortlist, then
  uncertainty times repulsion from labelled points.

## Main result

- Best classifier global method: `classifier_uncertainty_repulsion` with error `0.176`.
- Best classifier q20 method: `classifier_uncertainty_repulsion` with error `0.417`.
- Best classifier q30 method: `classifier_uncertainty_repulsion` with error `0.380`.
- GP-regressor reference source: `week5_3_gated_geometric_boundary_contraction`.
- Classifier beats GP-regressor global reference: `False`.
- Classifier beats GP-regressor q20 reference: `False`.
- Classifier beats GP-regressor q30 reference: `False`.

## Interpretation

The GP-classifier surrogate did not clearly improve the boundary metrics under this implementation. This suggests that surrogate choice alone is not sufficient; kernel choice, calibration, pool geometry, and acquisition design remain important.

## Caveats

GaussianProcessClassifier probabilities are not the same as GP-regressor latent
mean/std. Binary entropy and margin are monotone-equivalent in theory. Fixed
kernel GP classification is a runtime-stable approximation. Lower classifier
uncertainty-region fraction does not automatically prove correctness. The q10,
q20, and q30 near-boundary subsets use true function-value distances only for
evaluation, never acquisition.
