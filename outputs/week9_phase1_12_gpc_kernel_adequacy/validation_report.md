# Phase 1.12 validation

Status: **PASS**
Checks: **45 / 45 PASS**

| Check | Status | Detail |
|---|---|---|
| exact_start_sha | PASS | 5a21e5dce37fc6d4c58fa40bb7a6711920fec94e |
| historical_phase1x_unchanged | PASS | [] |
| population_405_73_332 | PASS | 405/73/332 |
| exact_100_A0_paths | PASS | 100 |
| exact_initial_B16 | PASS | 100/100 |
| exact_budget_grid | PASS | 16-80 |
| frozen_H_reproduced | PASS | 0.8308134191176471 |
| frozen_G0_reproduced | PASS | 0.8135202205882353 |
| no_new_acquisition | PASS | A0 replay |
| same_revealed_prefix | PASS | exact prefix |
| test_labels_not_fit | PASS | revealed only |
| boundary_flags_evaluation_only | PASS | q flags added after prediction |
| GPC_inputs_exact | PASS | ('P', 'VX', 'LS', 'ST') |
| scaler_outer_pool | PASS | label-free outer pool |
| G0_matern32 | PASS | G0 |
| G1_isotropic_RBF | PASS | G1 |
| G2_ARD_RBF | PASS | four lengths |
| G3_ARD_matern32 | PASS | G3 |
| G4_isotropic_matern52 | PASS | G4 |
| common_amplitude_bounds | PASS | (0.001, 1000.0) |
| common_length_bounds | PASS | (0.01, 100.0) |
| same_optimizer_restarts | PASS | 0 restarts |
| no_external_exponent | PASS | none |
| no_h_in_GPC_inputs | PASS | ('P', 'VX', 'LS', 'ST') |
| no_week5_target | PASS | classification only |
| new_prediction_completeness | PASS | all G1-G4 predictions |
| twenty_repeat_blocks | PASS | 20 |
| bootstrap_10000 | PASS | 10000 |
| primary_G3_G0 | PASS | q20/q30 |
| key_G3_H | PASS | q20/q30 |
| secondary_contrasts | PASS | complete |
| ARD_fields_complete | PASS | four labeled lengths |
| ARD_labels_correct | PASS | P,VX,LS,ST |
| no_causal_ARD_wording | PASS | claim-safe |
| descriptive_best_not_inferred | PASS | explicit |
| oracle_non_deployable | PASS | explicit |
| notebook_executed | PASS | 6 code cells |
| figure_hashes | PASS | 4/4 |
| historical_outputs_unchanged_again | PASS | git diff gate |
| red_team_claim_language | PASS | safe |
| exact_six_models | PASS | ['G0', 'G1', 'G2', 'G3', 'G4', 'H'] |
| G3_primary_frozen | PASS | G3 |
| fit_diagnostic_count | PASS | 26000 |
| fallback_disclosed | PASS | yes |
| decision_declared | PASS | KERNEL_GAP_CLOSED |
