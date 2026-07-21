# Week 4 Experiment 06 GP-Classifier Surrogate Summary

Week 4 Experiment 06 switches from GP regression on {-1,+1} labels to `GaussianProcessClassifier` with classifier-native probability acquisitions.
The GP-regressor rows are reference rows from existing outputs, not methods rerun inside this Week 4 Experiment 06 script.

| Benchmark | Best classifier global | Best classifier q20 | Best classifier q30 | Beats regressor global | Beats regressor q20 | Beats regressor q30 |
| --- | --- | --- | --- | --- | --- | --- |
| Thresholded Branin | classifier_uncertainty_repulsion (0.080) | classifier_uncertainty_repulsion (0.261) | classifier_uncertainty_repulsion (0.198) | False | False | False |
| Thresholded 4D Ackley | classifier_uncertainty_repulsion (0.176) | classifier_uncertainty_repulsion (0.417) | classifier_uncertainty_repulsion (0.380) | False | False | False |

## Interpretation

A GP classifier is more appropriate for binary observations because it models class probabilities directly instead of regressing on {-1,+1} labels.
This run does not prove that classifier surrogates are automatically better; kernel choice, probability calibration, pool geometry, and acquisition design still matter.
Binary entropy and margin are monotone-equivalent in binary classification, so they may be redundant.
Fixed-kernel GP classification is used as a practical approximation for runtime stability.
Lower classifier uncertainty-region fraction does not automatically imply correct boundary learning.
q10/q20/q30 subsets are evaluation diagnostics only and are not used by acquisition rules.
