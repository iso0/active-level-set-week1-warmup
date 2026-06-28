# Week 6.1 Slide Notes

## Question

Does optimizing GP-classifier kernel hyperparameters improve active level-set estimation on Branin and 4D Ackley?

## Setup

- Surrogates: fixed isotropic GPC, optimized isotropic GPC, optimized ARD GPC.
- Acquisitions: random, classifier margin, classifier entropy, gated diversity, uncertainty repulsion.
- Primary metrics: global error, q20 near-boundary error, q30 near-boundary error, query distance, uncertainty-region fraction.

## Best Week 6.1 rows

- branin global_error: `optimized_ard_gpc` / `classifier_gated_diversity` = `0.035`.
- branin near_boundary_error_q20: `optimized_ard_gpc` / `classifier_gated_diversity` = `0.164`.
- branin near_boundary_error_q30: `optimized_ard_gpc` / `classifier_gated_diversity` = `0.114`.
- ackley global_error: `fixed_iso_gpc` / `classifier_uncertainty_repulsion` = `0.176`.
- ackley near_boundary_error_q20: `fixed_iso_gpc` / `classifier_uncertainty_repulsion` = `0.417`.
- ackley near_boundary_error_q30: `fixed_iso_gpc` / `classifier_uncertainty_repulsion` = `0.380`.

## Fixed vs optimized

- branin global_error: best optimized beats fixed = `True`.
- branin near_boundary_error_q20: best optimized beats fixed = `True`.
- branin near_boundary_error_q30: best optimized beats fixed = `True`.
- ackley global_error: best optimized beats fixed = `False`.
- ackley near_boundary_error_q20: best optimized beats fixed = `False`.
- ackley near_boundary_error_q30: best optimized beats fixed = `False`.

## Regressor reference

- branin global_error: optimized classifier beats reference = `True`.
- branin near_boundary_error_q20: optimized classifier beats reference = `True`.
- branin near_boundary_error_q30: optimized classifier beats reference = `True`.
- ackley global_error: optimized classifier beats reference = `False`.
- ackley near_boundary_error_q20: optimized classifier beats reference = `False`.
- ackley near_boundary_error_q30: optimized classifier beats reference = `False`.

## Message

Do not overclaim. Kernel learning should be described through the empirical global/q20/q30 results and the hyperparameter traces, not as theoretically better just because labels are binary.
