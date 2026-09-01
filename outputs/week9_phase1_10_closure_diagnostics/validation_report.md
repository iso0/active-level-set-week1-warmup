# Phase 1.10 closure validation

Status: **PASS**

Checks: **28 / 28 PASS**

| Check | Status | Detail |
|---|---|---|
| start_sha_correct | PASS | 45e2677b7a57ed3aa5ad5154459100a9b5d2d436 |
| original_phase1_10_artifacts_unchanged | PASS | [] |
| original_populations_reproduced | PASS | Ti64 60/34; 316L 60/23 |
| raw_coefficient_conversion_algebra | PASS | (3.0, -1.0, -0.3333333333333333) |
| alpha_uses_raw_beta_ratio | PASS | verified every fit |
| standardized_ratio_not_used | PASS | synthetic guard distinguishes raw and standardized ratios |
| theory_reference_exact | PASS | -0.5 |
| one_hundred_main_fits_per_alloy | PASS | {'316L': 100, 'Ti64': 100} |
| folds_averaged_within_repeat | PASS | 20 repeat rows after five-fold averaging |
| exactly_twenty_repeat_blocks | PASS | repeat-block inference |
| bootstrap_at_least_10000 | PASS | 10000 |
| beta_P_instability_checked | PASS | invalid=1 |
| strict_dataset_only_C_K | PASS | ['C', 'K'] |
| no_transition_rows_survive | PASS | T/CT/TK absent |
| strict_counts_verified | PASS | {('316L', 'C'): 37, ('316L', 'K'): 11, ('Ti64', 'C'): 26, ('Ti64', 'K'): 22} |
| strict_exact_condition_grouping | PASS | condition lock |
| strict_no_replicate_leakage | PASS | one held-out fold per bundle |
| no_optical_predictors | PASS | log process inputs only |
| no_internal_boundary_inputs | PASS | external conventional metrics |
| R1_exact_C1 | PASS | {'C': 1.0, 'penalty': 'default_l2', 'status': 'AVAILABLE', 'role': 'frozen_main'} |
| R2_exact_C1e6 | PASS | {'C': 1000000.0, 'penalty': 'default_l2', 'status': 'AVAILABLE', 'role': 'weak_regularization'} |
| R3_only_if_clean_supported | PASS | R3_UNAVAILABLE |
| train_only_scaling | PASS | fit on training matrix |
| original_primary_verdict_not_overwritten | PASS | frozen verdict stated |
| notebook_executed | PASS | 7 code cells |
| figures_hashed | PASS | 2 figures |
| raw_external_data_not_committed | PASS | ignored cache only |
| historical_phase1x_outputs_unchanged | PASS | [] |
