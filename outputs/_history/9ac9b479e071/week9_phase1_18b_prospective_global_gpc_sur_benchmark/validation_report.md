# Phase 1.18B validation

Status: **PASS**
Checks: **44 / 44 PASS**

| Check | Status | Detail |
|---|---|---|
| exact_parent_sha | PASS | 1e34b4759037d5f3d107781791524853a406a526 |
| population_405_73_332 | PASS | 405/73/332 |
| exact_100_outer_runs | PASS | 100 |
| exact_20x5 | PASS | 20x5 |
| same_folds_all_arms | PASS | 100 each |
| same_B16_initialization | PASS | 300/300 |
| P0_path_exact | PASS | 100/100 |
| P0_metric_exact | PASS | published q20 |
| no_duplicate_queries | PASS | 300 paths |
| training_pool_only | PASS | all |
| heldout_never_queried | PASS | all |
| no_q20_q30_B1_acquisition | PASS | flags evaluation-only |
| hypothetical_both_labels | PASS | y0/y1 |
| current_posterior_weighting | PASS | exact |
| current_U_uses_complete_Rn | PASS | complete current pool |
| future_U_excludes_candidate | PASS | remaining pool |
| common_current_U_n | PASS | common over R_n |
| P1_physics_fixed | PASS | exact-fixed |
| P1_physics_numeric_freeze | PASS | all candidates/outcomes |
| P1_scaler_fixed | PASS | fixed |
| P1_P2_kernel_fixed | PASS | fixed current kernel |
| P2_physics_refit | PASS | revealed+hypothetical |
| P2_physics_numeric_change | PASS | observed |
| normal_actual_next_fit | PASS | normal M3 |
| FAST_never_used | PASS | absent from execution engine |
| PA_TVR_never_used | PASS | absent from execution engine |
| no_acquisition_tuning | PASS | frozen |
| deterministic_tie_break | PASS | smallest index |
| primary_q20_unchanged | PASS | q20 |
| repeat_block_inference | PASS | 20 blocks |
| bootstrap_at_least_10000 | PASS | 20000 |
| Holm_two_primary | PASS | 2 |
| q30_secondary | PASS | secondary contrasts |
| threshold_sign_explicit | PASS | explicit |
| fallback_disclosed | PASS | 0 |
| all_scores_finite | PASS | 3539200 |
| selected_truth_revealed_after | PASS | explicit |
| P0_B16_probability_equal | PASS | P0=P1 |
| P1_P2_B16_probability_equal | PASS | P1=P2 |
| notebook_executed | PASS | 7 |
| figure_hashes | PASS | 7 |
| historical_outputs_unchanged | PASS | [] |
| no_novelty_claim | PASS | safe |
| label_saving_claim_guarded | PASS | LABEL_SAVING_NOT_SUPPORTED |
