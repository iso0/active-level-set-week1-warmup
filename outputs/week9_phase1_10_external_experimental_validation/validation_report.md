# Phase 1.10 validation report

Status: **PASS**

Checks: **30 / 30 PASS**

| Check | Status | Detail |
|---|---|---|
| exact_external_source_provenance | PASS | two pinned GitHub workbooks and original open-access paper match declared SHA256 |
| ti64_row_count | PASS | observed 60 |
| ti64_unique_condition_count | PASS | observed 38 |
| ti64_class_counts | PASS | 34 Keyhole / 26 Conduction |
| ss316_row_count | PASS | observed 60 |
| ss316_unique_condition_count | PASS | observed 38 |
| ss316_class_counts | PASS | 23 Keyhole / 37 Conduction |
| spot_diameter_50_um | PASS | pinned paper semantics |
| thesis_radius_25_um | PASS | diameter divided by two |
| mm_s_to_m_s_conversion | PASS | numerically verified for all rows |
| exact_h_formula | PASS | SI formula verified for all rows |
| ls_constant | PASS | constant radius; exponent not testable |
| no_optical_predictor | PASS | {'H': [3, 1], 'G': [3, 2], 'GPC': [3, 2]} |
| H_only_log_h | PASS | one predictor |
| G_only_logP_logVX | PASS | two free predictors |
| no_fixed_exponent_in_G | PASS | G receives raw log VX, not fixed scaled h |
| condition_groups_never_cross_folds | PASS | exact group lock |
| one_oof_prediction_per_bundle_repeat_model | PASS | complete unique OOF coverage |
| both_classes_in_each_complete_oof_repeat | PASS | all complete vectors contain both classes |
| no_internal_B1_q20_q30 | PASS | external endpoint uses conventional full OOF metrics |
| twenty_repeat_blocks | PASS | 20 repeats per alloy |
| paired_repeat_contrast | PASS | H-G paired within repeat |
| discordant_conditions_exact | PASS | Ti64=2; 316L=0 |
| alloys_never_pooled_for_fitting | PASS | separate 60-row OOF vectors |
| PCA_fit_label_free | PASS | labels applied after PCA fit |
| external_raw_data_not_committed | PASS | cache ignored; raw ZIP absent |
| historical_phase1x_outputs_unchanged | PASS | [] |
| notebook_executed_and_stored | PASS | 11 executed code cells |
| figure_hashes_match | PASS | 4 figures |
| claim_language_red_team | PASS | primary negative comparison is stated; proof claims rejected |
