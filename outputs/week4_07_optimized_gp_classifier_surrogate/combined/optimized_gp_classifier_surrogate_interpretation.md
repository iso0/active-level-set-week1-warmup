# Week 4 Experiment 07 Interpretation

This run compares fixed-kernel and optimized-kernel `GaussianProcessClassifier` surrogates on thresholded Branin and thresholded 4D Ackley. Acquisition functions use classifier probabilities only; true function values and boundary masks are evaluation-only diagnostics.

## Runtime settings

- `n_restarts_optimizer`: `2`.
- `optimize_every`: `1`.
- Runtime reduction used: `False`.

## Answers

### ackley
- global_error: fixed `classifier_uncertainty_repulsion` = `0.176`, optimized iso `random` = `0.198`, optimized ARD `classifier_entropy` = `0.248`.
- near_boundary_error_q20: fixed `classifier_uncertainty_repulsion` = `0.417`, optimized iso `random` = `0.424`, optimized ARD `classifier_entropy` = `0.448`.
- near_boundary_error_q30: fixed `classifier_uncertainty_repulsion` = `0.380`, optimized iso `random` = `0.381`, optimized ARD `classifier_uncertainty_repulsion` = `0.421`.
- Did optimized isotropic GPC improve over fixed isotropic GPC? `no` on at least one primary metric.
- Did optimized ARD GPC improve over optimized isotropic GPC? `no` on at least one primary metric.
- Did optimized GPC beat the previous fixed Week 4 Experiment 06 classifier output? `no` on at least one primary metric.
- Did optimized GPC beat the previous GP-regressor reference on global error? `no`.
- Did optimized GPC beat the previous GP-regressor reference on q20/q30 error? `no`.
- Learned length-scale bound-hit fraction during optimized fits: `0.763`.
- Learned constant bound-hit fraction during optimized fits: `0.504`.
- Some hyperparameters frequently sit near bounds, so the optimized classifier should be treated as diagnostic rather than final.

### branin
- global_error: fixed `classifier_uncertainty_repulsion` = `0.080`, optimized iso `classifier_margin` = `0.043`, optimized ARD `classifier_gated_diversity` = `0.035`.
- near_boundary_error_q20: fixed `classifier_uncertainty_repulsion` = `0.261`, optimized iso `classifier_margin` = `0.182`, optimized ARD `classifier_gated_diversity` = `0.164`.
- near_boundary_error_q30: fixed `classifier_uncertainty_repulsion` = `0.198`, optimized iso `classifier_margin` = `0.128`, optimized ARD `classifier_gated_diversity` = `0.114`.
- Did optimized isotropic GPC improve over fixed isotropic GPC? `yes` on at least one primary metric.
- Did optimized ARD GPC improve over optimized isotropic GPC? `yes` on at least one primary metric.
- Did optimized GPC beat the previous fixed Week 4 Experiment 06 classifier output? `yes` on at least one primary metric.
- Did optimized GPC beat the previous GP-regressor reference on global error? `yes`.
- Did optimized GPC beat the previous GP-regressor reference on q20/q30 error? `yes`.
- Learned length-scale bound-hit fraction during optimized fits: `0.425`.
- Learned constant bound-hit fraction during optimized fits: `0.885`.
- Some hyperparameters frequently sit near bounds, so the optimized classifier should be treated as diagnostic rather than final.

ARD helped more on Ackley than Branin: `no` by mean optimized-iso minus optimized-ARD error across global/q20/q30.

## Runtime cost

Total benchmark runtime represented in the runtime summary is `516.3` seconds across benchmark-method-seed runs.
The runtime cost is partly justified where optimized classification improves primary metrics, especially boundary metrics.

## Thesis-level conclusion

The optimized classifier gives a strong positive result on Branin, including q20/q30 improvements over the available GP-regressor references. It does not dominate on thresholded 4D Ackley, where the fixed Week 4 Experiment 06 classifier and previous GP-regression references remain better. The thesis-level conclusion is diagnostic: classifier-native surrogates remain worth pursuing, while kernel optimization alone is not enough on the harder 4D named benchmark.

q10 is very close to the exact threshold and is unstable across seeds; q20/q30 are more reliable for comparing acquisition behavior.
