# Week 12 strict OLD→NEW model transfer

This is post-hoc developmental evidence. Models and scalers were fitted on OLD-405 only; NEW-136 labels were used only for evaluation.

| Subset | Model | Fit status | ROC AUC | PR AUC Keyhole | Balanced accuracy | Brier |
|---|---|---|---:|---:|---:|---:|
| full | G0 | optimized_primary | 0.9247 | 0.9921 | 0.7043 | 0.0539 |
| q20 | G0 | optimized_primary | 0.8278 | 0.8836 | 0.7500 | 0.1600 |
| q30 | G0 | optimized_primary | 0.8455 | 0.9389 | 0.7273 | 0.1333 |
| full | G3 | optimized_primary | 0.9241 | 0.9915 | 0.7003 | 0.0506 |
| q20 | G3 | optimized_primary | 0.8333 | 0.8928 | 0.7500 | 0.1574 |
| q30 | G3 | optimized_primary | 0.8394 | 0.9313 | 0.7106 | 0.1299 |
| full | H | historical_h_logistic | 0.8569 | 0.9753 | 0.5000 | 0.0736 |
| q20 | H | historical_h_logistic | 0.7611 | 0.8187 | 0.5000 | 0.2810 |
| q30 | H | historical_h_logistic | 0.7727 | 0.8872 | 0.5000 | 0.2159 |
| full | M3 | historical_m3_fixed_mean_ard | 0.8797 | 0.9783 | 0.5793 | 0.0579 |
| q20 | M3 | historical_m3_fixed_mean_ard | 0.7722 | 0.8248 | 0.6000 | 0.1933 |
| q30 | M3 | historical_m3_fixed_mean_ard | 0.7879 | 0.8927 | 0.5909 | 0.1573 |
| full | empirical_prior | fixed_old_training_prevalence | 0.5000 | 0.9118 | 0.5000 | 0.6156 |
| q20 | empirical_prior | fixed_old_training_prevalence | 0.5000 | 0.6429 | 0.5000 | 0.4436 |
| q30 | empirical_prior | fixed_old_training_prevalence | 0.5000 | 0.7317 | 0.5000 | 0.5004 |

The empirical prior is the OLD-405 Keyhole prevalence. ARD length scales are standardized-space geometry diagnostics, not causal feature importance. The class-stratified bootstrap and calibration bands are descriptive uncertainty conditional on these fixed predictions and cohort class counts; they are not independent-campaign intervals. Leave-one-negative-out results expose fragility from the 12 NEW non-keyholes and do not refit models.
