# Phase 1.16 validation

Status: **PASS**
Checks: **31 / 31 PASS**

| Check | Status | Detail |
|---|---|---|
| exact_parent_sha | PASS | a8eafbbb814f5d5c9fe71a985746d6d1c4cb76eb |
| population_405_73_332 | PASS | 405/73/332 |
| exact_100_outer_runs | PASS | 100 |
| exact_initial_designs | PASS | 100x6 |
| historical_M3_margin_reproduced | PASS | exact |
| exact_M3_architecture | PASS | frozen |
| exact_h_formula | PASS | inherited |
| residual_inputs_exact | PASS | ('P', 'VX', 'LS', 'ST') |
| logh_absent_residual | PASS | 4D residual |
| scores_pre_reveal | PASS | ordered |
| labels_absent_selector | PASS | geometry+probability only |
| B1_q_absent_selector | PASS | absent |
| geometry_only_distance | PASS | feature geometry |
| scaler_information_flow | PASS | outer train features |
| exact_c_grid | PASS | (0.25, 0.5, 1.0, 2.0, 4.0) |
| no_posthoc_scales | PASS | frozen |
| deterministic_tie_break | PASS | exact |
| one_query_per_step | PASS | 64 |
| no_train_test_overlap | PASS | all |
| no_duplicate_query | PASS | all |
| B16_equal_all_arms | PASS | 1.1102230246251565e-16 |
| all_paths_length_80 | PASS | 600x80 |
| repeat_block_inference | PASS | 20 blocks |
| bootstrap_10000 | PASS | 10000 |
| multiplicity_present | PASS | Holm |
| q20_q30_unchanged | PASS | ['B1_q20', 'B1_q30', 'full81'] |
| historical_outputs_unchanged | PASS | [] |
| notebook_executed | PASS | 7 |
| figure_hashes | PASS | 6 |
| no_placeholders | PASS | none |
| decision_rule_exact | PASS | REPULSION_MECHANISM_ONLY |
