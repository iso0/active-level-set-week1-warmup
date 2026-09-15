# Week 6 Phase 3 — model-and-target robustness

## Outcome

Phase 3 tested whether the learned-nugget GP remains useful relative to simple regressions, alternative isotropic kernels, and five reasonable target variants. The tables below separate point-model parsimony, GP uncertainty, and physical target choice; they are not collapsed into a single score.

## Immutable inputs and populations

- Branch start: `codex/week6-phase3-model-target-robustness` at `b112f6b22898976f77410190614cb4fb218d38f9`.
- Phase 1 revision: `0e859b748fdbc8454f66e58e101e333ac0479d42`.
- Phase 1 ledger SHA-256: `10DEF11AB64D62444AC14FED506266BEB748EEB5BF892ACDC12E7F0F6DDCF4FF`.
- Phase 2.5 decision: `B_preferred_for_depth`.
- Features: exactly `P, VX, LS, ST`; targets converted only from metres to micrometres.

| target | population_size | excluded_count | target_min_um | target_median_um | target_max_um |
| --- | --- | --- | --- | --- | --- |
| width | 241 | 0 | 86.3089 | 159.0052 | 256.7670 |
| length | 241 | 0 | 116.1617 | 341.3759 | 543.7264 |
| depth | 230 | 11 | 18.7786 | 54.7223 | 94.3651 |

## Phase 3A — simple models

| target | model | mae_um | median_absolute_error_um | rmse_um | r2 | nrmse |
| --- | --- | --- | --- | --- | --- | --- |
| depth | linear_ridge | 3.3523 | 2.7104 | 4.6324 | 0.9103 | 0.0613 |
| depth | matern32_learned_nugget | 1.8023 | 1.3398 | 2.7289 | 0.9689 | 0.0361 |
| depth | polynomial_ridge_degree2 | 2.5859 | 1.8376 | 3.8885 | 0.9368 | 0.0514 |
| depth | training_mean | 12.6845 | 10.9619 | 15.5353 | -0.0088 | 0.2055 |
| length | linear_ridge | 25.8879 | 21.8223 | 35.8303 | 0.8431 | 0.0838 |
| length | matern32_learned_nugget | 10.6228 | 5.3481 | 19.3891 | 0.9541 | 0.0453 |
| length | polynomial_ridge_degree2 | 18.1006 | 14.8879 | 25.6630 | 0.9195 | 0.0600 |
| length | training_mean | 77.9757 | 78.8049 | 90.8420 | -0.0084 | 0.2125 |
| width | linear_ridge | 6.9047 | 4.7864 | 9.5514 | 0.9349 | 0.0560 |
| width | matern32_learned_nugget | 3.2745 | 1.9077 | 6.6964 | 0.9680 | 0.0393 |
| width | polynomial_ridge_degree2 | 3.3877 | 2.0921 | 6.7253 | 0.9677 | 0.0395 |
| width | training_mean | 30.6635 | 26.3623 | 37.5933 | -0.0084 | 0.2205 |

A simple model is called competitive when the paired RMSE confidence interval includes zero, its RMSE difference falls inside the predeclared practical threshold, or it robustly improves on the GP. This avoids claiming that GP complexity is necessary on a numerical difference alone.

| target | candidate_model | observed_mae_difference_um | mae_difference_ci95_lower_um | mae_difference_ci95_upper_um | observed_rmse_difference_um | rmse_difference_ci95_lower_um | rmse_difference_ci95_upper_um | simple_model_competitive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| depth | linear_ridge | 1.5500 | 1.2087 | 1.8947 | 1.9035 | 1.4310 | 2.3401 | False |
| depth | polynomial_ridge_degree2 | 0.7836 | 0.5216 | 1.0463 | 1.1596 | 0.7096 | 1.5701 | False |
| length | linear_ridge | 15.2651 | 12.6779 | 17.9255 | 16.4413 | 11.4827 | 21.4797 | False |
| length | polynomial_ridge_degree2 | 7.4778 | 6.1142 | 8.8618 | 6.2740 | 3.9694 | 8.5963 | False |
| width | linear_ridge | 3.6302 | 3.0547 | 4.2140 | 2.8551 | 1.2856 | 4.5685 | False |
| width | polynomial_ridge_degree2 | 0.1132 | -0.0706 | 0.3004 | 0.0290 | -0.1439 | 0.1923 | True |

## Phase 3B — kernel and nugget robustness

| target | gp_configuration | mae_um | rmse_um | mean_nlpd | latent_95_coverage | total_95_coverage | optimizer_warning_folds | any_bound_hit_folds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| depth | matern32_learned_nugget | 1.8023 | 2.7289 | 2.4404 | 0.8783 | 0.9522 | 1 | 0 |
| depth | matern32_no_nugget | 2.0892 | 3.0369 | 2.7125 | 0.9174 | — | 3 | 0 |
| depth | matern52_learned_nugget | 1.7883 | 2.7170 | 2.4399 | 0.8217 | 0.9478 | 0 | 0 |
| depth | matern52_no_nugget | 2.4135 | 3.4975 | 2.9524 | 0.9217 | — | 0 | 0 |
| depth | rbf_learned_nugget | 1.8255 | 2.7698 | 2.4630 | 0.7348 | 0.9565 | 0 | 0 |
| depth | rbf_no_nugget | 3.4025 | 4.8582 | 3.2567 | 0.9217 | — | 0 | 0 |
| length | matern32_learned_nugget | 10.6228 | 19.3891 | 4.4721 | 0.8838 | 0.9544 | 1 | 0 |
| length | matern32_no_nugget | 15.0739 | 25.7390 | 5.3775 | 0.9336 | — | 0 | 0 |
| length | matern52_learned_nugget | 10.3620 | 18.9402 | 4.4378 | 0.8714 | 0.9544 | 1 | 0 |
| length | matern52_no_nugget | 18.8971 | 30.7526 | 5.9243 | 0.9419 | — | 0 | 0 |
| length | rbf_learned_nugget | 10.4736 | 18.6937 | 4.4140 | 0.8091 | 0.9502 | 2 | 0 |
| length | rbf_no_nugget | 31.7370 | 47.7089 | 8.9339 | 0.9585 | — | 0 | 0 |
| width | matern32_learned_nugget | 3.2745 | 6.6964 | 3.5737 | 0.8755 | 0.9627 | 5 | 0 |
| width | matern32_no_nugget | 4.5216 | 8.0375 | 3.7422 | 0.9336 | — | 0 | 0 |
| width | matern52_learned_nugget | 3.3383 | 6.7462 | 3.5786 | 0.7884 | 0.9627 | 3 | 0 |
| width | matern52_no_nugget | 5.4196 | 8.9469 | 3.8727 | 0.9170 | — | 1 | 0 |
| width | rbf_learned_nugget | 3.3860 | 6.7592 | 3.5621 | 0.7178 | 0.9627 | 0 | 0 |
| width | rbf_no_nugget | 8.5350 | 12.4265 | 4.2063 | 0.8963 | — | 0 | 0 |

| target | selected_provisional_gp_configuration | another_kernel_replaces_current | selected_rmse_um | selected_mean_nlpd | selected_evaluation_95_coverage |
| --- | --- | --- | --- | --- | --- |
| width | matern32_learned_nugget | False | 6.6964 | 3.5737 | 0.9627 |
| length | matern52_learned_nugget | True | 18.9402 | 4.4378 | 0.9544 |
| depth | matern32_learned_nugget | False | 2.7289 | 2.4404 | 0.9522 |

## Phase 3C — target-definition sensitivity

| target | target_definition | pearson_correlation_with_t0 | spearman_correlation_with_t0 | median_absolute_difference_from_t0_um | q95_absolute_difference_from_t0_um | fraction_absolute_difference_exceeds_current_learned_nugget_std |
| --- | --- | --- | --- | --- | --- | --- |
| depth | T0 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| depth | T1 | 0.9945 | 0.9956 | 0.1004 | 3.7803 | 0.3217 |
| depth | T2 | 0.9961 | 0.9979 | 0.0415 | 3.7016 | 0.1609 |
| depth | T3 | 0.9961 | 0.9976 | 0.0109 | 3.6545 | 0.1261 |
| depth | T4 | 0.9958 | 0.9960 | 0.0179 | 3.7913 | 0.2391 |
| depth | T5 | 0.6260 | 0.6266 | 7.9953 | 58.7970 | 0.6478 |
| length | T0 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| length | T1 | 0.9985 | 0.9978 | 2.8290 | 9.5067 | 0.0041 |
| length | T2 | 0.9991 | 0.9988 | 2.4450 | 8.9297 | 0.0000 |
| length | T3 | 0.9993 | 0.9988 | 0.2477 | 6.1859 | 0.0041 |
| length | T4 | 0.9989 | 0.9986 | 0.0773 | 10.0323 | 0.0041 |
| length | T5 | 0.0599 | 0.0501 | 20.4939 | 485.6823 | 0.5560 |
| width | T0 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| width | T1 | 0.9983 | 0.9973 | 0.2572 | 3.4503 | 0.0041 |
| width | T2 | 0.9996 | 0.9996 | 0.1792 | 2.2814 | 0.0041 |
| width | T3 | 0.9997 | 0.9997 | 0.0487 | 2.4259 | 0.0000 |
| width | T4 | 0.9997 | 0.9993 | 0.0381 | 2.5788 | 0.0000 |
| width | T5 | 0.7725 | 0.7946 | 7.4403 | 143.8667 | 0.5021 |

Target-definition shifts and learned nugget sizes are conceptually different. Their scale comparison is descriptive only.

| target | target_definition | gp_configuration | mae_um | rmse_um | r2 | nrmse | mean_nlpd | evaluation_95_coverage | learned_nugget_std_um_median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| depth | T0 | matern32_learned_nugget | 1.8023 | 2.7289 | 0.9689 | 0.0361 | 2.4404 | 0.9522 | 1.7768 |
| depth | T1 | matern32_learned_nugget | 1.8539 | 2.8454 | 0.9653 | 0.0397 | 2.4671 | 0.9304 | 1.8685 |
| depth | T2 | matern32_learned_nugget | 1.6859 | 2.4733 | 0.9754 | 0.0322 | 2.3545 | 0.9522 | 1.5051 |
| depth | T3 | matern32_learned_nugget | 1.6476 | 2.5158 | 0.9742 | 0.0333 | 2.3716 | 0.9565 | 1.5462 |
| depth | T4 | matern32_learned_nugget | 1.9732 | 3.0341 | 0.9618 | 0.0401 | 2.5344 | 0.9565 | 1.9158 |
| depth | T5 | matern32_learned_nugget | 6.4792 | 11.1728 | 0.8560 | 0.1289 | 3.8761 | 0.9435 | 9.0130 |
| length | T0 | matern52_learned_nugget | 10.3620 | 18.9402 | 0.9562 | 0.0443 | 4.4378 | 0.9544 | 16.5962 |
| length | T1 | matern52_learned_nugget | 10.6184 | 19.3815 | 0.9546 | 0.0451 | 4.4474 | 0.9544 | 16.4641 |
| length | T2 | matern52_learned_nugget | 10.3515 | 19.2204 | 0.9544 | 0.0457 | 4.4554 | 0.9627 | 17.0755 |
| length | T3 | matern52_learned_nugget | 9.9170 | 18.3366 | 0.9577 | 0.0445 | 4.4191 | 0.9710 | 16.3547 |
| length | T4 | matern52_learned_nugget | 10.8600 | 19.7251 | 0.9535 | 0.0455 | 4.4616 | 0.9627 | 16.6858 |
| length | T5 | matern52_learned_nugget | 104.0935 | 223.6408 | 0.3080 | 0.1571 | 7.1111 | 0.9502 | 160.7841 |
| width | T0 | matern32_learned_nugget | 3.2745 | 6.6964 | 0.9680 | 0.0393 | 3.5737 | 0.9627 | 6.1849 |
| width | T1 | matern32_learned_nugget | 3.5418 | 7.0801 | 0.9651 | 0.0412 | 3.5604 | 0.9585 | 6.3450 |
| width | T2 | matern32_learned_nugget | 3.3546 | 6.9628 | 0.9648 | 0.0412 | 3.6801 | 0.9668 | 6.4489 |
| width | T3 | matern32_learned_nugget | 3.3080 | 6.7168 | 0.9675 | 0.0394 | 3.5757 | 0.9668 | 6.2091 |
| width | T4 | matern32_learned_nugget | 3.2869 | 6.6663 | 0.9688 | 0.0391 | 3.5754 | 0.9627 | 6.1464 |
| width | T5 | matern32_learned_nugget | 12.5463 | 21.0150 | 0.9379 | 0.0822 | 4.5264 | 0.9544 | 17.4170 |

## Final decisions

| target | selected_final_model | selected_provisional_gp | simple_models_competitive | learned_nugget_robustly_helps_selected_gp_family |
| --- | --- | --- | --- | --- |
| width | polynomial_ridge_degree2 | matern32_learned_nugget | ["polynomial_ridge_degree2"] | True |
| length | matern52_learned_nugget | matern52_learned_nugget | [] | True |
| depth | matern32_learned_nugget | matern32_learned_nugget | [] | True |

| target | selected_target_definition | t0_retained | target_definition_sensitivity_substantial | fixed_gp_performance_or_nugget_materially_sensitive |
| --- | --- | --- | --- | --- |
| width | T0 | True | True | True |
| length | T3 | False | True | True |
| depth | T0 | True | True | True |

## Runtime, validation, and repository state

- Full invocation wall time recorded so far: 156.35 s.
- Cache events: 43 reused, 10 computed.
- Validation: 51/51 PASS.
- The notebook is executed separately inside the deterministic rebuild and final validation confirms zero error outputs.
- No commit or push is part of Phase 3.
- The original dirty worktree is fingerprinted before and after the run.
