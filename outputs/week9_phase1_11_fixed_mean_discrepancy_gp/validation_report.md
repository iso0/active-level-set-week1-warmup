# Phase 1.11 validation

Status: **PASS**
Checks: **36 / 36 PASS**

| Check | Status | Detail |
|---|---|---|
| correct_start_sha | PASS | e33cca4f81b865d330577ef9a8140c4bbe306e5a |
| historical_phase1x_unchanged | PASS | [] |
| canonical_h_formula | PASS | numeric P/sqrt(VX*LS^3) verification |
| stage1_only_log_h | PASS | log(h) only |
| stage1_scaler_revealed_only | PASS | revealed indices |
| stage1_labels_prefix_only | PASS | current A0 prefix |
| physics_mean_is_latent_logit | PASS | latent passed to GP |
| physics_mean_frozen_stage2 | PASS | fixed mean values |
| residual_only_four_inputs | PASS | ('P', 'VX', 'LS', 'ST') |
| residual_excludes_log_h | PASS | kernel gets standardized x4 |
| no_external_exponent | PASS | canonical h only |
| no_masinelli_labels | PASS | SPH only |
| no_boundary_inputs_in_fit | PASS | evaluation flags only |
| exact_A0_path | PASS | Phase 1.8 tracked query_paths.csv.gz |
| exact_initial16 | PASS | load_inputs executable equality against frozen manifest and initial_design |
| M0_baseline | PASS | 0.8135202205882353 |
| M1_A0_baseline | PASS | 0.8299724264705881 |
| no_new_acquisition | PASS | A0 replay only |
| zero_mean_parity | PASS | 0.0 |
| same_inference_equations | PASS | one class, m=0 or supplied m |
| matern_nu_exact | PASS | 1.5 |
| residual_sd_bounds_exact | PASS | (0.05, 1.0) |
| length_scale_bounds_exact | PASS | (0.25, 4.0) |
| train_only_4d_scaling | PASS | outer training pool feature-only |
| prediction_completeness | PASS | all new split/budget/subsets |
| twenty_repeat_blocks | PASS | 20 |
| bootstrap_draws | PASS | 10000 |
| M2_M0_contrast | PASS | q20/q30 |
| M2_M1_contrast | PASS | q20/q30 |
| M2_MH_contrast | PASS | q20/q30 |
| bound_hits_deterministic | PASS | np.isclose fixed tolerance |
| matched_A0_diagnostics | PASS | M2 6500; M1 reused matched Y10 |
| no_fold_independence_claim | PASS | repeat-block inference |
| notebook_executed | PASS | 7 code cells |
| figure_hashes | PASS | 4 |
| claim_language_red_team | PASS | safe |
