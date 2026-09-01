# Phase 1.13 validation

Status: **PASS**
Checks: **60 / 60 PASS**

| Check | Status | Detail |
|---|---|---|
| phase112_parent_sha | PASS | 161453983996b763824f2d262b5ce9d63332da16 |
| phase112_placeholder_gone | PASS | {future} absent |
| historical_phase1x_unchanged | PASS | [] |
| population_405_73_332 | PASS | 405/73/332 |
| exact_A0_paths | PASS | 100 |
| exact_budget_grid | PASS | B16-80 |
| frozen_H | PASS | 0.8308134191176471 |
| frozen_G0 | PASS | 0.8135202205882353 |
| frozen_G3 | PASS | 0.826594669117647 |
| frozen_M2 | PASS | 0.8302297794117648 |
| no_new_acquisition | PASS | A0 replay |
| identical_revealed_prefixes | PASS | one physics fit per budget |
| stage1_only_log_h | PASS | Phase 1.11 implementation |
| stage1_revealed_labels_only | PASS | prefix only |
| stage1_mean_frozen | PASS | fixed values |
| latent_logit_mean | PASS | latent logit values passed as GP mean |
| M3_inputs_exact | PASS | ('P', 'VX', 'LS', 'ST') |
| logh_excluded_residual | PASS | 4D kernel only |
| no_external_exponent | PASS | none |
| no_masinelli_data | PASS | simulator only |
| boundary_evaluation_only | PASS | fit path clean |
| matern_nu_1_5 | PASS | 1.5 |
| M3_four_lengths | PASS | 4 |
| residual_sd_bounds | PASS | (0.05, 1.0) |
| M3_primary_bounds | PASS | (0.01, 100.0) |
| M2W_same_bounds | PASS | same |
| M2W_isotropic | PASS | scalar |
| M3_ARD | PASS | four |
| same_amplitude_bounds | PASS | (0.05, 1.0) |
| same_optimizer_restarts | PASS | zero restarts |
| ARD_zero_mean_parity | PASS | 0.0 |
| M2W_predictions_complete | PASS | 526500 |
| M3_predictions_complete | PASS | 526500 |
| L1000_only_checkpoints | PASS | B16/B40/B80 |
| twenty_repeat_blocks | PASS | 20 |
| bootstrap_draws | PASS | 10000 |
| primary_M3_H | PASS | q20 |
| mechanistic_M3_M2W | PASS | q20 |
| M3_M2 | PASS | q20 |
| M3_G3 | PASS | q20 |
| early_exact | PASS | 16-40 |
| late_exact | PASS | 41-80 |
| q30_secondary | PASS | complete |
| full81_checkpoints | PASS | 5x3x7 |
| ARD_dimension_labels | PASS | P/VX/LS/ST |
| bound_hits_deterministic | PASS | fixed atol |
| residual_role_complete | PASS | checkpoints/subsets |
| changed_decision_fractions_coherent | PASS | beneficial + harmful = 1 |
| no_orthogonality_claim | PASS | safe |
| no_causal_ARD_claim | PASS | safe |
| no_acquisition_superiority | PASS | safe |
| upper_sensitivity_complete | PASS | 3 budgets |
| notebook_executed | PASS | 10 code cells |
| figure_hashes | PASS | 5 |
| no_unresolved_templates | PASS | none |
| historical_outputs_unchanged_again | PASS | git diff |
| red_team_language | PASS | explicit |
| M2W_M3_diagnostic_counts | PASS | 6500 each |
| physics_shared_complete | PASS | one per prefix |
| decision_declared | PASS | HYBRID_GAIN_SUPPORTED |
