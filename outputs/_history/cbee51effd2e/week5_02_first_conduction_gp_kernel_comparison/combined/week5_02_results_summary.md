# Week 5 Experiment 02 — GP Kernel Comparison Results

## Data and protocol

- Clean dataset: 91 simulations.
- Broad dataset: 238 simulations.
- Excluded never-Conduction simulations: 3.
- Inputs: P, VX, LS, ST; standardized inside every LOO fold.
- Target: first observed Conduction raw timestep.
- GPR: normalize_y=True, alpha=1e-06 numerical jitter, fmin_l_bfgs_b, 1 extra restart, no WhiteKernel.

## Clean metrics (ordered by RMSE)

| kernel_label | MAE | median_absolute_error | RMSE | R2 | normalized_RMSE | mean_negative_log_predictive_density | empirical_95_interval_coverage | mean_95_interval_width | total_runtime_seconds | optimization_warning_count |
|---|---|---|---|---|---|---|---|---|---|---|
| Matérn 3/2 | 1,735.8 | 1,092.1 | 2,537.0 | 0.9171 | 0.2863 | 9.8156 | 0.9011 | 13,861.9 | 3.8854 | 0 |
| ARD RBF — Automatic Relevance Determination RBF | 2,035.5 | 1,291.4 | 3,255.0 | 0.8636 | 0.3673 | 9.9604 | 0.8571 | 8,736.3 | 15.9956 | 49 |
| Matérn 5/2 | 2,545.3 | 1,538.1 | 3,724.6 | 0.8214 | 0.4203 | 10.1396 | 0.9011 | 18,027.2 | 4.4465 | 0 |
| Isotropic RBF | 4,402.2 | 3,100.9 | 6,141.7 | 0.5142 | 0.6931 | 10.8160 | 0.9121 | 24,118.1 | 5.7899 | 0 |

## Broad metrics (ordered by RMSE)

| kernel_label | MAE | median_absolute_error | RMSE | R2 | normalized_RMSE | mean_negative_log_predictive_density | empirical_95_interval_coverage | mean_95_interval_width | total_runtime_seconds | optimization_warning_count |
|---|---|---|---|---|---|---|---|---|---|---|
| Matérn 3/2 | 11,616.9 | 7,414.2 | 16,256.3 | 0.4060 | 0.7691 | 11.0404 | 0.9286 | 58,070.3 | 55.0253 | 0 |
| Matérn 5/2 | 11,698.4 | 7,581.8 | 16,402.7 | 0.3952 | 0.7760 | 11.0322 | 0.9370 | 58,594.5 | 67.8181 | 0 |
| Isotropic RBF | 12,023.8 | 7,875.0 | 16,735.2 | 0.3705 | 0.7918 | 11.0402 | 0.9202 | 60,597.8 | 53.6230 | 0 |
| ARD RBF — Automatic Relevance Determination RBF | 12,982.0 | 8,231.9 | 18,597.1 | 0.2226 | 0.8799 | 11.3067 | 0.8908 | 58,098.2 | 289.5290 | 0 |

## Same-clean-points comparison

| kernel_label | clean_trained_MAE | clean_trained_RMSE | broad_trained_MAE | broad_trained_RMSE | clean_points_improved_by_broad_training | clean_points_worsened_by_broad_training | median_paired_improvement_clean_minus_broad |
|---|---|---|---|---|---|---|---|
| Isotropic RBF | 4,402.2 | 6,141.7 | 12,850.8 | 16,433.6 | 13 | 78 | -7,422.7 |
| ARD RBF — Automatic Relevance Determination RBF | 2,035.5 | 3,255.0 | 13,454.0 | 18,429.4 | 17 | 74 | -8,506.7 |
| Matérn 3/2 | 1,735.8 | 2,537.0 | 13,303.7 | 17,398.5 | 10 | 81 | -9,689.6 |
| Matérn 5/2 | 2,545.3 | 3,724.6 | 13,077.2 | 17,095.0 | 12 | 79 | -8,775.0 |

## ARD full-data diagnostics

| dataset | input | standardized_space_lengthscale | full_fit_anisotropy_ratio_max_over_min |
|---|---|---|---|
| clean | P | 0.7642 | 376.4951 |
| clean | VX | 0.2656 | 376.4951 |
| clean | LS | 100.0000 | 376.4951 |
| clean | ST | 1.7332 | 376.4951 |
| broad | P | 0.9449 | 5.9849 |
| broad | VX | 0.4045 | 5.9849 |
| broad | LS | 0.8201 | 5.9849 |
| broad | ST | 0.1579 | 5.9849 |

## Interpretation

- The RMSE winner is shared, but the remaining kernel ordering changes.
- ARD RBF changes RMSE relative to isotropic RBF by +47.00% on clean data and -11.13% on broad data (positive means ARD reduces RMSE).
- Broad training reduces RMSE on the same 91 clean points for 0 of 4 kernels.
- Total recorded optimization warnings: 50; failures: 0.
- Summed LOO fold runtime: 496.1 s; full-data fit runtime: 1.9 s.

## Next decision

Review the highest-error LOO simulations for clean-best Matérn 3/2 and broad-best Matérn 3/2, cross-reference Screenshot Bug and ambiguity diagnostics, and clarify the subgroup interpretation under the already fixed broad-inclusion policy before any active-learning or level-set work.

These results concern GP regression on a provisional point target. They do not prove physical transition-time accuracy, causal input importance, or the correctness of bug-affected labels.

## Subsequent supervisor context and final Week 5 diagnostics

**Added 2026-07-22. This context was received after the Phase 2 numerical experiment; the metrics above are unchanged.**

Ioan clarified that the original annotator may have labelled only the first empty image as Initial Emptiness and later empty images as Screenshot Bug. Screenshot Bug therefore does not necessarily mean corrupted simulation data. He also suggested that laser spot radius might relate to when empty images appeared. Consequently, “clean” is retained only as an operational name for the 91 simulations without any Screenshot Bug label, not as a verified data-quality category.

The follow-up stored-label analysis found 150 Bug-containing simulations. None begins with Initial Emptiness in the CSV and none shows the strict Initial-Emptiness-then-Bug order, but all 147 simulations with pre-Conduction Bug frames keep those frames inside the initial contiguous empty-like block. This supports the broader repeated-empty-image explanation without confirming the literal label order or the underlying physical state.

Bug and no-Bug simulations differ in more than one recorded dimension. Median LS is 66.48 µm versus 59.86 µm, while P, VX, ST, the initial empty-like duration and especially the target distribution also differ. A deterministic logistic diagnostic is weak: LS-only out-of-fold ROC AUC is 0.5952 and the four-input AUC is 0.5926. The Phase 2 same-clean-points degradation is therefore interpreted as consistent with subgroup/design heterogeneity and missing batch variables, not as proof that broad observations are invalid.

The largest-error review does not show Bug enrichment: 55% of the top 20 broad Matérn 3/2 errors contain Bug labels versus 61.8% of all broad observations. Instead, 15/20 are in the earliest or latest target quartile, their median LS is 75.77 µm, and 15/20 fall outside the nominal 95% interval.

The subsequent optimizer-family comparison gives practically identical Matérn 3/2 LOO predictions for L-BFGS-B, SLSQP and Powell, with zero failures, warnings or parameter-bound hits. L-BFGS-B is retained because no alternative materially improves held-out prediction and it avoids custom-optimizer complexity. Matérn 3/2 remains the point-prediction recommendation; the earlier broad Matérn 5/2 NLPD/coverage advantage remains a separate calibration caveat.

The fixed target and data policy did not change: the broad dataset includes Screenshot Bug simulations, the response is the first actually observed Conduction raw timestep, and the three never-Conduction simulations remain excluded. Active learning and level-set estimation were not started.
