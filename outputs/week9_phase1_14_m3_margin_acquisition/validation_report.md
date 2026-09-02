# Phase 1.14 validation

Status: **PASS**
Checks: **56 / 56 PASS**

| Check | Status | Detail |
|---|---|---|
| exact_phase113_parent_base | PASS | fbe76352f86580818659ab87fa23ec29a74c7f59 |
| phase113_decision | PASS | HYBRID_GAIN_SUPPORTED |
| population_405_73_332 | PASS | 405/73/332 |
| h_formula_unchanged | PASS | P/sqrt(VX*LS^3) inherited |
| exact_100_outer_runs | PASS | 100 |
| exact_20x5 | PASS | 20x5 |
| exact_B16_80 | PASS | 65 budgets |
| exact_initial_designs | PASS | 100/100 |
| P0_frozen_AULC | PASS | 0.8424908088235293 |
| evaluation_fold_never_queried | PASS | all paths |
| q20_absent_acquisition | PASS | selection clean |
| q30_absent_acquisition | PASS | selection clean |
| B1_absent_acquisition | PASS | selector clean |
| unrevealed_labels_absent_selector | PASS | probabilities only |
| one_query_per_step | PASS | 64 after B16 |
| no_duplicate_query | PASS | 100 paths |
| historical_margin_semantics | PASS | exact |
| deterministic_tie_break | PASS | exact |
| stage1_logh_only | PASS | exact Phase 1.13 |
| stage1_revealed_only | PASS | prefix |
| stage1_frozen_before_residual | PASS | ordered |
| M3_residual_inputs_exact | PASS | ('P', 'VX', 'LS', 'ST') |
| logh_absent_residual_coordinate | PASS | 4D only |
| ARD_matern_nu_1_5 | PASS | 1.5 |
| four_ARD_lengths | PASS | 4 |
| amplitude_bounds_unchanged | PASS | (0.05, 1.0) |
| primary_length_bounds | PASS | (0.01, 100.0) |
| optimizer_restarts_unchanged | PASS | frozen |
| P1_trajectories_complete | PASS | 100x80 |
| P1_predictions_complete | PASS | 526500 |
| same_M3_evaluator | PASS | path only |
| paired_20_repeat_blocks | PASS | 20 |
| bootstrap_10000 | PASS | 10000 |
| early_exact | PASS | B16-40 |
| late_exact | PASS | B41-80 |
| q30_complete | PASS | secondary |
| full81_complete | PASS | P0/P1/delta x budgets x metrics |
| thresholds_predeclared | PASS | (0.8, 0.82, 0.84) |
| path_overlap_retrospective | PASS | post hoc only |
| sensitivity_subset_predeclared | PASS | one per repeat |
| no_causal_ARD_claim | PASS | safe |
| no_universal_acquisition_claim | PASS | safe |
| no_theoretical_sample_complexity_claim | PASS | safe |
| B16_predictions_identical | PASS | 1.1102230246251565e-16 |
| selection_after_current_evaluation | PASS | evaluate then select |
| current_prefix_budget_exact | PASS | no off-by-one |
| candidate_pool_training_only | PASS | outer train |
| query_labels_marked_after_selection | PASS | explicit |
| fit_diagnostics_complete | PASS | 6500 |
| sensitivity_diagnostics_complete | PASS | 1300 |
| notebook_executed | PASS | 9 cells |
| figure_hashes | PASS | 5 |
| no_unresolved_placeholders | PASS | none |
| historical_outputs_unchanged | PASS | [] |
| red_team_language | PASS | explicit |
| decision_declared | PASS | LATE_ACQUISITION_GAIN_ONLY |
