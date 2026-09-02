# Phase 1.17A validation

Status: **PASS**
Checks: **27 / 27 PASS**

| Check | Status | Detail |
|---|---|---|
| exact_parent_sha | PASS | 746b19153f377bb0b7219d1c113bab672e306b19 |
| exact_phase16_paths | PASS | 600x80 |
| no_new_trajectory | PASS | diagnostic only |
| exact_scaler_recovery | PASS | 4.440892098500626e-16 |
| standardized_gradient_formula | PASS | chain rule |
| gradient_at_selected_candidate | PASS | local |
| ST_gradient_zero | PASS | exact zero |
| nearest_original_euclidean | PASS | standardized Euclidean |
| orthogonal_decomposition | PASS | 9.992007221626409e-16 |
| reconstruction_identity | PASS | 2.3551386880256624e-16 |
| energy_identity | PASS | 2.275957200481571e-15 |
| fraction_sum | PASS | 8.881784197001252e-16 |
| zero_distance_reported | PASS | 0 |
| no_ARD_metric | PASS | none |
| labels_absent_geometry | PASS | absent |
| B1_q_absent_geometry | PASS | absent |
| freeze_before_join | PASS | frozen |
| exact_arms | PASS | ['M3_MARGIN', 'REP_C025', 'REP_C050', 'REP_C100', 'REP_C200', 'REP_C400'] |
| exact_budgets_lengths | PASS | 38400 |
| train_test_integrity | PASS | all |
| repeat_block_inference | PASS | 20 blocks |
| bootstrap_10000 | PASS | 10000 |
| notebook_executed | PASS | 7 |
| figure_hashes | PASS | 5 |
| historical_outputs_unchanged | PASS | [] |
| no_placeholders | PASS | none |
| decision_valid | PASS | MIXED_GEOMETRIC_MECHANISM |
