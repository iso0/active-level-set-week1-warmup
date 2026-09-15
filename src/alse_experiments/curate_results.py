"""Copy the curated evidence shortlist from the archive into results/.

The shortlist is the archive inventory's section 7.1 (primary evidence: decision
files, ledgers, protocol JSONs, headline tables and figures). Regenerable caches
(section 7.2: checkpoints, bundles, per-candidate dumps, prediction histories,
parquet, large split manifests) are never copied; results/MANIFEST.csv lists
them with status 'referenced' (bytes and sha256 of the archive file). Files keep
their archive names and their path below the archive experiment directory.

    python experiments/curate_results.py --dry-run
    python experiments/curate_results.py [--clean] [--max-file-mb 8]
"""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alse.config import ARCHIVE_ROOT, OUTPUTS_DIR, RESULTS_DIR, archive_file  # noqa: E402
from alse.io import sha256_file, sha256_text_lf, write_csv  # noqa: E402

TOTAL_CAP_BYTES = 50_000_000
TEXT_SUFFIXES = {".csv", ".json", ".md", ".txt", ".sha256"}
COLUMNS = ["source", "destination", "bytes", "sha256_raw", "sha256_lf", "status"]
# Builder/validator scaffolding dropped from glob matches (inventory 7.2).
SCAFFOLDING = ("figure_manifest.csv", "output_manifest.csv", "requirement_checklist*", "validation_results.csv",
               "runtime_summary.json", "execution_history.json", "codex_run_report.md", "*_slide_notes.md", "*.log")
# Phase 1.18B finished at archive commit 2552078; the working-tree snapshot predates it (49 result
# files missing, analysis_specification.json stale), so tracked files under it are read from git HEAD.
P118B = "outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark"


def figs(*numbers: str) -> str:
    return " ".join(f"figures/{n}_*.png" for n in numbers)


# (destination under results/, archive directory, whitespace-separated files or globs below it).
# IDs follow docs/experiments.md; X/W entries are superseded or diagnostic phases kept for the appendix.
SHORTLIST: list[tuple[str, str, str]] = [
    # --- synthetic S1-S6 ---
    ("synthetic/X1_branin_week1", "outputs/branin_week1", "summary.json error_vs_evaluations.png"),
    ("synthetic/S1_branin_gpr_rules", "outputs/week2_acquisition_comparison",
     "method_summary_table.csv selected_budget_table.csv summary.json error_curves_all_methods.png"),
    ("synthetic/S2_ackley4_gpr_rules", "outputs/week3_4d_named_benchmark_comparison",
     "method_summary_table.csv selected_budget_table.csv tolerance_reach_table.csv tolerance_reach_table.md summary.json "
     "error_curves_all_methods.png exact_boundary_2d_slices.png"),
    ("synthetic/S3_boundary_metrics", "outputs/week4_01_boundary_metrics",
     "combined/* */final_boundary_metrics_table.csv */boundary_metric_summary_table.csv"),
    *[(f"synthetic/{dest}", f"outputs/{base}", "combined/* */final_metrics_table.csv") for dest, base in (
        ("X3_diversified_straddle", "week4_02_diversified_straddle"),
        ("X4_gated_diversified_straddle", "week4_03_boundary_gated_diversified_straddle"),
        ("S4_lookahead", "week4_04_lookahead_boundary_uncertainty"),
        ("X5_geometric_contraction", "week4_05_gated_geometric_boundary_contraction"),
        ("S5_fixed_gpc_rules", "week4_06_gp_classifier_surrogate"))],
    ("synthetic/X6_optimized_gpc", "outputs/week4_07_optimized_gp_classifier_surrogate",
     "combined/fixed_vs_optimized_classifier_comparison.csv combined/best_method_by_metric.csv "
     "combined/regressor_reference_comparison.csv combined/optimized_gp_classifier_surrogate_interpretation.md "
     "*/final_metrics_table.csv"),
    ("synthetic/X7_boundary_weighted_sur", "outputs/week4_08_boundary_weighted_sur",
     "combined/best_method_by_metric.csv combined/new_methods_vs_baselines.csv combined/surrogate_comparison.csv "
     "combined/boundary_weighted_sur_summary.md combined/hartmann4_benchmark_notes.md */final_metrics_table.csv"),
    ("synthetic/S6_gpc_bernoulli_sur", "outputs/week4_09_gpc_bernoulli_sur_validation",
     "combined/* */final_metrics_table.csv */fairness_checks.json */summary.json"),
    # --- data: Week 5/6 protocol origins, D1-D3 sph_v2 audit, targets and proxies ---
    ("data/W5_1_first_conduction_audit", "outputs/week5_01_first_conduction_data_audit",
     "data_audit_summary.json simulation_level_audit.csv right_censored_simulations.csv"),
    ("data/W5_2_kernel_comparison", "outputs/week5_02_first_conduction_gp_kernel_comparison",
     "clean/clean_kernel_metrics.csv broad/broad_kernel_metrics.csv same_clean_points/same_clean_points_metrics.csv "
     "combined/kernel_specification.csv combined/kernel_comparison_summary.json combined/week5_02_results_summary.md "
     "clean/clean_kernel_metric_comparison.png broad/broad_kernel_metric_comparison.png"),
    ("data/W5_3_bug_ls_analysis", "outputs/week5_03_bug_initial_emptiness_ls_analysis",
     "bug_ls_analysis_summary.json bug_sequence_pattern_summary.csv bug_logistic_regression_summary.csv"),
    ("data/W5_4_optimizer_comparison", "outputs/week5_04_matern32_optimizer_comparison",
     "optimizer_pairwise_comparison.csv week5_04_results_summary.md"),
    ("data/W5_5_ard_matern32", "outputs/week5_05_ard_matern32_extension",
     "matern32_isotropic_vs_ard_metrics.csv matern32_paired_bootstrap_summary.csv ard_matern32_lengthscale_summary.csv "
     "week5_05_results_summary.md"),
    ("data/W6_1_melt_pool_audit", "outputs/week6_01_melt_pool_data_audit",
     "week6_phase1_simulation_level_responses.csv results_summary.md listing_failure_root_cause.md "
     "scalar_target_candidate_comparison.csv summary.json original_worktree_baseline.json"),
    ("data/W6_2_response_noise", "outputs/week6_02_gp_response_noise_comparison",
     "results_summary.md all_model_metrics.csv preferred_method_selection.csv paired_bootstrap_summary.csv "
     "phase2_model_configuration.json phase2_decision_log.md"),
    ("data/W6_2_5_depth_model_closure", "outputs/week6_02_5_depth_model_closure",
     "depth_model_decision.md stable_depth_model_metrics.csv stable_depth_paired_bootstrap_summary.csv"),
    ("data/W6_3_model_target_robustness", "outputs/week6_03_model_target_robustness",
     "simple_baseline_metrics.csv gp_kernel_noise_metrics.csv phase3_final_model_decision.csv phase3_final_target_decision.csv "
     "provisional_kernel_decision.csv within_kernel_nugget_comparisons.csv results_summary.md decision_log.md"),
    ("data/W6_3_5_regime_target_design", "outputs/week6_03_5_regime_target_design",
     "results_summary.md decision_log.md phase3_5_final_target_recommendation.csv phase3_5_candidate_decision_matrix.csv "
     "regime_target_candidate_definitions.csv regime_target_candidates.csv simulation_level_candidate_label_metrics.csv "
     "label_population_audit.csv phase3_5_configuration.json"),
    ("data/W6_4_new_outputs_feature_effects", "outputs/week6_04_new_outputs_feature_effects",
     "phase4_model_metrics.csv phase4_selected_model_decisions.csv phase4_simulation_level_targets.csv "
     "phase4_spearman_correlations.csv phase4_standardized_ridge_coefficients.csv results_summary.md decision_log.md"),
    ("data/D1_sph_v2_audit", "outputs/week7_01_sph_v2_audit",
     "experiment_registry.csv experiment_label_sequences.csv keyhole_episodes.csv label_distribution.csv "
     "ioan_reference_comparison.csv parameter_bounds_shift.csv new_data_domain_membership.csv missing_unexpected_files.csv "
     "partition_summary.csv dataset_provenance.json summary.json results_summary.md annotator_provenance_audit.csv "
     + figs("06", "07", "08")),
    ("data/D2_target_extraction", "outputs/week7_02_sph_v2_target_extraction",
     "sph_v2_simulation_level_targets.csv summary.json results_summary.md new_data_readiness_summary.csv "
     "exact_old_new_target_comparison_summary.csv sentinel_audit.csv supervisor_correction_before_after.csv "
     "week6_exact_identifier_map.csv monitor_source_plan.csv domain_mapping_compatibility.csv week6_definition_traceability.csv "
     "t0_extreme_event_diagnostics.csv flagged_depth_ambiguity.csv depth_visual_review_notes.csv " + figs("10", "11")),
    ("data/X8_new_data_model_stability", "outputs/week7_03_new_data_physical_model_stability",
     "model_metric_table.csv model_selection_decisions.csv stability_conclusion_table.csv week6_vs_new_data_comparison.csv "
     "results_summary.md"),
    ("data/X9_depth_diagnostics", "outputs/week7_04_new_data_feature_effects_depth_diagnostics",
     "depth_consensus_hard_cases.csv depth_feature_trend_consensus.csv depth_error_diagnosis_summary.csv "
     "depth_error_by_keyhole_context.csv results_summary.md " + figs("15")),
    ("data/D3_keyhole_proxy", "outputs/week7_05_keyhole_physical_proxy_analysis",
     "results_summary.md physical_proxy_candidate_scorecard.csv phase5_target_formulation_decision.csv "
     "t0_vs_max_vs_g3_vs_r3_decision.csv physical_proxy_candidate_definitions.csv label_provenance.md"),
    ("data/D3_g3_transfer", "outputs/week7_05_5_g3_robustness_transfer_analysis",
     "current_revision_simulation_level_targets.csv physical_proxy_population_reference.csv results_summary.md "
     "phase55_scorecard.csv g3_vs_r3_vs_max_vs_t0_transfer_decision.csv phase55_boundary_formulation_recommendation.csv "
     "threshold_cross_population_transfer_summary.csv population_readiness_by_partition.csv hf_change_audit.json "
     "current_revision_target_refresh_audit.csv"),
    # --- real data R1-R4 (X11 = the superseded Week 8 consolidation, kept with its stale-wording note) ---
    ("real/R1_phase6_active_arms", "outputs/week7_06_real_data_boundary_active_level_set",
     "results_summary.md phase6_final_decision.csv phase6_formulation_scorecard.csv active_learning_aulc_summary.csv "
     "active_paired_bootstrap_intervals.csv active_paired_method_comparisons.csv static_model_summary.csv "
     "domain_transfer_model_summary.csv empirical_boundary_subset_summary.csv max_depth_semantic_summary.csv "
     "max_depth_vs_g3_summary.csv online_threshold_bootstrap_summary.csv active_initialization_audit.csv "
     "input_provenance.json summary.json " + figs("02", "04", "19", "31", "36", "38", "47", "49", "56", "61", "77", "78")),
    ("real/R2_phase7_hybrids", "outputs/week7_07_final_boundary_hybrid_benchmark",
     "results_summary.md phase7_final_decision.csv phase7_preregistered_decision_rule.json "
     "phase7_preregistered_decision_rule.sha256 phase7_preregistered_rule_outcome.csv phase7_aulc_summary.csv "
     "phase7_method_scorecard.csv phase7_method_definitions.csv boundary_metric_definitions.csv boundary_metric_correlations.csv "
     "phase7_paired_bootstrap_intervals.csv phase7_runtime_comparison.csv phase7_keyhole_discovery_summary.csv "
     "phase6_run_reuse_audit.csv phase6_reproduction_check.csv summary.json "
     + figs("15", "16", "17", "19", "27", "30", "32", "34", "37", "50")),
    ("real/X11_sample_efficiency", "outputs/week8_01_final_sample_efficiency",
     "headline_results.md headline_results.csv random_equivalent_budget.csv boundary_accuracy_learning_curves.csv "
     "predictive_confidence_summary.csv predictive_calibration_summary.csv phase8_01_preflight.json query_savings_summary.csv "
     + figs("01", "03", "05", "06", "08", "10")),
    ("real/X11_thesis_consolidation", "outputs/week8_02_thesis_consolidation",
     "*.csv *.md final_thesis_figures/*.png final_thesis_tables/*"),
    ("real/R3_frozen_protocol", "outputs/week8_5_frozen_confirmation",
     "preregistered_protocol.json protocol_sha256.txt decision_ledger.csv bootstrap_or_hierarchical_ci.csv "
     "hierarchical_bootstrap_summary.json query_savings_summary.csv repulsion_ablation_summary.csv "
     "repulsion_mechanism_summary.csv adaptive_horizon_decision.json repeat_level_metrics.csv run_level_metrics.csv "
     "random_continuation_summary.csv run_manifest.json postrun_provenance_addendum.json runtime_compute_report.json "
     "final_results_narrative.md agent_handoffs/04_critic_audit.md agent_handoffs/05_supervisor_decision.md "
     "initial_design_manifest.csv figures/*.png"),
    ("real/R4_h320_closure", "outputs/week9_phase1_close_week8",
     "query_saving_claim_decision.json crossing_by_horizon.csv terminal_accuracy_answers.csv final_q1_q9_answers.json "
     "final_q1_q9_answers.md summary.json claim_ledger.md claim_ledger.csv supervisor_summary.md final_results_narrative.md "
     "terminal_metric_summary.csv learning_curve_summary_16_80.csv pca_summary.json discriminative_update/claim_ledger.csv "
     "discriminative_update/feature_discrimination.csv " + figs("01", "02", "03", "04")),
    # --- physics P1-P7 (X14-X20 diagnostics: decision objects and one page each) ---
    ("physics/P1_h_coordinate", "outputs/week9_phase1_5_h_physics_confirmation",
     "FINAL_PHASE1_5_REPORT.md SUPERVISOR_PHASE1_5_ONE_PAGE.md claim_ledger.md active_AULC_contrasts.csv "
     "empirical_exponent_summary.csv screening_zone_summary.csv static_model_summary.csv h_coordinates.csv "
     "gpc_kernel_bound_diagnostics.csv active_learning_curve_summary.csv baseline_reproduction_gate.json "
     + figs("01", "03", "04", "06", "08")),
    ("physics/P2_physics_ridge_residual", "outputs/week9_phase1_7_physics_ridge_residual_gp",
     "primary_decision.json FINAL_PHASE1_7_REPORT.md FINAL_RED_TEAM_REPORT.md SUPERVISOR_PHASE1_7_ONE_PAGE.md claim_ledger.md "
     "baseline_gate.json tables/primary_AULC_summary.csv tables/active_information_flow.csv.gz "
     "tables/active_per_budget_metrics.csv.gz tables/active_learning_curve_summary.csv tables/repeat_level_delta_AULC.csv "
     "tables/static_model_summary.csv tables/historical_context_AULC.csv " + figs("01", "02", "03")),
    ("physics/P3_model_path_decomposition", "outputs/week9_phase1_8_model_path_decomposition",
     "primary_decomposition.csv four_way_AULC_summary.csv regularization_sensitivity.csv path_audit.json "
     "learning_curve_four_way.csv baseline_gate.json FINAL_PHASE1_8_REPORT.md claim_ledger.md tables/query_paths.csv.gz "
     "tables/four_way_metrics_per_budget.csv.gz " + figs("01", "02")),
    ("physics/P4_physics_specificity", "outputs/week9_phase1_9_physics_specificity_control",
     "primary_AULC_summary.csv hyperparameter_diagnostics.csv static_model_summary.csv learning_curve_summary.csv "
     "baseline_gate.json FINAL_PHASE1_9_REPORT.md claim_ledger.md " + figs("01", "02")),
    ("physics/X14_external_ti64_validation", "outputs/week9_phase1_10_external_experimental_validation",
     "*.md *.csv *.json figures/*.png"),
    ("physics/X15_external_closure", "outputs/week9_phase1_10_closure_diagnostics",
     "exponent_summary.csv regularization_sensitivity.csv strict_ck_model_summary.csv strict_ck_paired_contrasts.csv "
     "FINAL_PHASE1_10_CLOSURE_REPORT.md SUPERVISOR_PHASE1_10_CLOSURE_ONE_PAGE.md claim_ledger.md figures/*.png"),
    ("physics/P5_model_chain/M2_fixed_mean", "outputs/week9_phase1_11_fixed_mean_discrepancy_gp",
     "model_summary.csv paired_contrasts.csv residual_stability_summary.csv budget16_contrasts.csv budget16_summary.csv "
     "implementation_parity_report.json baseline_gate.json run_manifest.json FINAL_PHASE1_11_REPORT.md claim_ledger.md "
     "figures/*.png"),
    ("physics/P5_model_chain/G0_G4_kernels", "outputs/week9_phase1_12_gpc_kernel_adequacy",
     "model_summary.csv paired_contrasts.csv budget16_summary.csv bound_hit_summary.csv ard_lengthscale_summary.csv "
     "kernel_specification.json g0_checkpoint_metrics.csv baseline_gate.json run_manifest.json FINAL_PHASE1_12_REPORT.md "
     "claim_ledger.md figures/*.png"),
    ("physics/P5_model_chain/M3_fixed_physics_ard", "outputs/week9_phase1_13_fixed_physics_ard_discrepancy",
     "model_summary.csv paired_contrasts.csv early_late_contrasts.csv checkpoint16_40_80_summary.csv "
     "residual_amplitude_summary.csv ard_lengthscale_summary.csv residual_role_summary.csv upper_bound_sensitivity.csv "
     "kernel_specification.json ard_parity_report.json baseline_gate.json run_manifest.json FINAL_PHASE1_13_REPORT.md "
     "claim_ledger.md m3_fit_diagnostics.csv.gz m2w_fit_diagnostics.csv.gz physics_mean_fit_diagnostics.csv.gz figures/*.png"),
    ("physics/P6_m3_margin_acquisition", "outputs/week9_phase1_14_m3_margin_acquisition",
     "m3_margin_paths.csv.gz m3_margin_queries.csv.gz outer_run_metrics.csv.gz m3_active_fit_diagnostics.csv.gz "
     "acquisition_specification.json paired_contrasts.csv early_late_contrasts.csv learning_curve_summary.csv "
     "sample_efficiency_thresholds.csv run_manifest.json baseline_gate.json FINAL_PHASE1_14_REPORT.md claim_ledger.md "
     + figs("01", "02", "03")),
    ("physics/X16_residual_signal_audit", "outputs/week9_phase1_15a_physics_residual_signal_audit",
     "repeat_block_inference.csv correction_signal_summary.csv component_reconstruction_audit.csv "
     "analysis_specification.json FINAL_PHASE1_15A_REPORT.md claim_ledger.md figures/*.png"),
    ("physics/X17_repulsion_scale_audit", "outputs/week9_phase1_16_m3_repulsion_scale_audit",
     "repulsion_scale_response.csv multiplicity_summary.csv query_paths.csv.gz diversity_diagnostics.csv "
     "repeat_block_inference.csv early_late_summary.csv sample_efficiency_thresholds.csv analysis_specification.json "
     "FINAL_PHASE1_16_REPORT.md claim_ledger.md figures/*.png"),
    ("physics/X18_contour_geometry_audit", "outputs/week9_phase1_17a_physics_contour_geometry_audit",
     "mechanism_decision.json scale_response_geometry.csv geometry_component_summary.csv repeat_block_inference.csv "
     "analysis_specification.json FINAL_PHASE1_17A_REPORT.md claim_ledger.md figures/*.png"),
    ("physics/X19_level_set_compatibility", "outputs/week9_phase1_18a_level_set_acquisition_compatibility_audit",
     "margin_collapse_decisions.csv method_decisions.csv pa_tvr_decision.json runtime_benchmark.csv "
     "ranking_pairwise_summary.csv topk_overlap_summary.csv candidate_scores_sha256.json analysis_specification.json "
     "FINAL_PHASE1_18A_REPORT.md claim_ledger.md figures/*.png"),
    ("physics/X20_fast_sur_validation", "outputs/week9_phase1_18b0_fast_gpc_sur_update_validation",
     "primary_decision.json refit_effect_decision.json sur_score_fidelity_overall.csv runtime_benchmark.csv "
     "selection_fidelity_summary.csv posterior_fidelity_summary.csv analysis_specification.json "
     "FINAL_PHASE1_18B0_REPORT.md claim_ledger.md figures/*.png"),
    ("physics/P7_exact_gpc_sur", P118B,
     "primary_decision.json physics_refit_decision.json sample_efficiency_decision.json q20_primary_contrasts.csv "
     "q20_budget_region_contrasts.csv q30_aulc_contrasts.csv model_aulc_summary.csv learning_curve_summary.csv "
     "multiplicity_adjustment.csv sample_efficiency_contrasts.csv sample_efficiency_thresholds.csv q20_repeat_metrics.csv "
     "q20_aulc_by_run.csv checkpoint_metrics.csv model_fit_summary.csv fullheldout_diagnostics.csv "
     "b40_keyhole_diagnostics.csv path_overlap_summary.csv runtime_summary.csv sur_protocol.md analysis_specification.json "
     "baseline_gate.json run_manifest.json claim_ledger.md FINAL_PHASE1_18B_REPORT.md FINAL_RED_TEAM_REPORT.md "
     "SUPERVISOR_PHASE1_18B_ONE_PAGE.md figures/*.png"),
    # --- audits and the archived written record ---
    ("reports", "reports", "*.md external_validation/*"),
    ("archive_docs", "docs", "*.md"),
]

# Regenerable caches (inventory 7.2) and oversized tables: listed by path and sha256, never copied.
REFERENCED: list[tuple[str, str]] = [
    ("outputs/week7_06_real_data_boundary_active_level_set",  # primary_common_population.csv == data/population.csv
     "primary_common_population.csv outer_split_manifest.csv active_query_history.csv active_prediction_history.csv "
     "online_threshold_history.csv active_learning_curve_summary.csv static_model_fold_predictions.csv "
     "boundary_surface_data.csv"),
    ("outputs/week7_07_final_boundary_hybrid_benchmark",
     "phase7_all_method_prediction_checkpoints.csv hybrid_prediction_history.csv phase7_supported_boundary_surfaces.csv "
     "phase7_all_method_query_history.csv phase7_boundary_metric_learning_curves.csv phase7_learning_curve_summary.csv "
     "hybrid_query_history.csv"),
    ("outputs/week8_5_frozen_confirmation",
     "split_manifest.csv grouped_split_manifest.csv checkpoint_metrics.csv crossing_censoring.csv query_crossings.csv "
     "repulsion_mechanism_diagnostics.csv hierarchical_bootstrap_draws.csv week8_5_checkpoint_bundle.tar.gz "
     "week8_5_large_machine_readable_artifacts.tar.gz"),
    ("outputs/week9_phase1_close_week8",
     "week9_phase1_h320_checkpoint_bundle.tar.gz terminal_hierarchical_bootstrap_draws.csv.gz terminal_predictions.csv.gz "
     "week9_fit_seed_registry.csv terminal_path_metrics.csv"),
    ("outputs", "week7_01_sph_v2_audit/repository_file_inventory.parquet "
     "week7_02_sph_v2_target_extraction/sph_v2_simulation_level_targets.parquet "
     "week7_03_new_data_physical_model_stability/residual_diagnostics.csv "
     "week7_03_new_data_physical_model_stability/fold_level_predictions.csv "
     "week7_05_5_g3_robustness_transfer_analysis/current_revision_simulation_level_targets.parquet "
     "week6_03_5_regime_target_design/label_aligned_geometry_time_series.parquet "
     "week6_03_5_regime_target_design/regime_geometry_time_series.parquet/* "
     "week6_03_model_target_robustness/*_loo_predictions.csv week6_04_new_outputs_feature_effects/phase4_loo_predictions.csv "
     "week9_phase1_5_h_physics_confirmation/active_checkpoints_H160.tar.gz "
     "week9_phase1_5_h_physics_confirmation/active_per_budget_metrics.csv.gz "
     "week9_phase1_5_h_physics_confirmation/static_oof_predictions.csv.gz "
     "week9_phase1_11_fixed_mean_discrepancy_gp/h_only_a0_predictions.csv.gz "
     "week9_phase1_11_fixed_mean_discrepancy_gp/fixed_mean_oof_predictions.csv.gz "
     "week9_phase1_12_gpc_kernel_adequacy/new_kernel_predictions.csv.gz "
     "week9_phase1_13_fixed_physics_ard_discrepancy/new_predictions.csv.gz "
     "week9_phase1_14_m3_margin_acquisition/new_predictions.csv.gz "
     "week9_phase1_15a_physics_residual_signal_audit/component_candidate_*.csv.gz "
     "week9_phase1_16_m3_repulsion_scale_audit/fit_diagnostics.csv.gz "
     "week9_phase1_17a_physics_contour_geometry_audit/query_geometry_components.csv.gz "
     "week9_phase1_18a_level_set_acquisition_compatibility_audit/candidate_scores_pre_reveal.csv.gz "
     "week9_phase1_18b0_fast_gpc_sur_update_validation/candidate_level_update_results.csv.gz"),
    (P118B, "sequential_predictions.csv.gz model_fit_diagnostics.csv.gz sur_step_diagnostics.csv.gz "
     "physics_refit_step_diagnostics.csv.gz checkpoints/*/*.json.gz"),
]


def tracked_at_head() -> set[str]:
    out = subprocess.run(["git", "-C", str(ARCHIVE_ROOT), "ls-tree", "-r", "--name-only", "HEAD"],
                         capture_output=True, text=True, check=True).stdout
    return set(out.split("\n")) - {""}


def expand(pattern: str, tracked: set[str]) -> list[str]:
    """Archive-relative files matching a path or glob, on disk or tracked at HEAD (scaffolding dropped)."""
    if not any(ch in pattern for ch in "*?["):
        return [pattern]
    found = {p.relative_to(ARCHIVE_ROOT).as_posix() for p in ARCHIVE_ROOT.glob(pattern) if p.is_file()}
    found |= {t for t in tracked if PurePosixPath(t).full_match(pattern)}
    kept = sorted(f for f in found if not any(fnmatch.fnmatch(PurePosixPath(f).name, s) for s in SCAFFOLDING))
    if not kept:
        print(f"WARNING: no archive file matches {pattern}")
    return kept


def materialise(relpath: str, tracked: set[str]) -> Path:
    """On-disk path of an archive file (archive_file); tracked Phase 1.18B files come from git HEAD."""
    if not (relpath.startswith(P118B + "/") and relpath in tracked):
        return archive_file(relpath)
    cached = OUTPUTS_DIR / "_archive_cache" / "HEAD" / relpath
    if not cached.is_file():
        blob = subprocess.run(["git", "-C", str(ARCHIVE_ROOT), "show", f"HEAD:{relpath}"], capture_output=True, check=True)
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(blob.stdout)
    return cached


def plan(max_file_bytes: int) -> list[dict]:
    """One row per archive file: copied / referenced / missing, with its size and destination."""
    tracked = tracked_at_head()
    entries = [(dest, f"{base}/{n}") for dest, base, names in SHORTLIST for n in names.split()]
    entries += [(None, f"{base}/{n}") for base, names in REFERENCED for n in names.split()]
    rows: list[dict] = []
    for dest, pattern in entries:
        for src in expand(pattern, tracked):
            row = {"source": src, "destination": "", "bytes": None, "sha256_raw": "", "sha256_lf": "",
                   "status": "referenced", "_group": dest or "(referenced)"}
            try:
                row["_path"] = materialise(src, tracked)
            except FileNotFoundError:
                print(f"WARNING: missing in the archive working tree and at HEAD: {src}")
                rows.append({**row, "status": "missing"})
                continue
            row["bytes"] = row["_path"].stat().st_size
            if dest is not None and row["bytes"] > max_file_bytes:
                print(f"WARNING: {src} ({row['bytes'] / 1e6:.1f} MB) exceeds the per-file limit; referenced instead")
            elif dest is not None:  # keep the path below the archive experiment directory, never rename
                parts = PurePosixPath(src).parts
                row.update(destination=PurePosixPath(dest, *parts[2 if parts[0] == "outputs" else 1:]).as_posix(),
                           status="copied")
            rows.append(row)
    copied = [r for r in rows if r["status"] == "copied"]
    duplicates = {d for d in (r["destination"] for r in copied) if sum(r["destination"] == d for r in copied) > 1}
    if duplicates:
        raise SystemExit(f"destination collision: {sorted(duplicates)}")
    total = sum(r["bytes"] for r in copied)
    if total > TOTAL_CAP_BYTES:
        print(f"ABORT: {total / 1e6:.2f} MB exceeds the {TOTAL_CAP_BYTES / 1e6:.0f} MB cap; largest copied files:")
        for r in sorted(copied, key=lambda r: -r["bytes"])[:15]:
            print(f"  {r['bytes'] / 1e6:7.2f} MB  {r['source']}")
        raise SystemExit(2)
    return rows


def report(rows: list[dict]) -> None:
    copied = [r for r in rows if r["status"] == "copied"]
    for group in sorted({r["_group"] for r in copied}):
        members = [r for r in copied if r["_group"] == group]
        print(f"  {len(members):4d} files {sum(r['bytes'] for r in members) / 1e6:7.2f} MB  {group}")
    for status in ("copied", "referenced", "missing"):
        members = [r for r in rows if r["status"] == status]
        print(f"{status:>10}: {len(members)} files, {sum(r['bytes'] or 0 for r in members) / 1e6:.2f} MB")
    print("largest copied files:")
    for r in sorted(copied, key=lambda r: -r["bytes"])[:5]:
        print(f"  {r['bytes'] / 1e6:7.2f} MB  {r['source']}")
    for r in rows:
        if r["status"] == "missing":
            print(f"   missing: {r['source']}")


def clean_previous() -> None:
    manifest = RESULTS_DIR / "MANIFEST.csv"
    if manifest.is_file():
        old = pd.read_csv(manifest)
        for dest in old.loc[old["status"] == "copied", "destination"]:
            (RESULTS_DIR / dest).unlink(missing_ok=True)
    for folder in sorted((p for p in RESULTS_DIR.rglob("*") if p.is_dir()), reverse=True):
        if not any(folder.iterdir()):
            folder.rmdir()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print the plan and totals; write nothing")
    parser.add_argument("--clean", action="store_true", help="remove files copied by a previous run before recopying")
    parser.add_argument("--max-file-mb", type=float, default=8.0, help="per-file copy limit in MB (larger files are referenced)")
    args = parser.parse_args()
    rows = plan(int(args.max_file_mb * 1e6))
    report(rows)
    if args.dry_run:
        return
    if args.clean:
        clean_previous()
    for row in rows:
        if row["status"] == "missing":
            continue
        row["sha256_raw"] = sha256_file(row["_path"])
        row["sha256_lf"] = sha256_text_lf(row["_path"]) if row["_path"].suffix in TEXT_SUFFIXES else ""
        if row["status"] == "copied":
            target = RESULTS_DIR / row["destination"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(row["_path"], target)
    frame = pd.DataFrame([{k: r[k] for k in COLUMNS} for r in rows], columns=COLUMNS)
    frame["bytes"] = frame["bytes"].astype("Int64")
    write_csv(RESULTS_DIR / "MANIFEST.csv", frame)
    print(f"wrote {RESULTS_DIR / 'MANIFEST.csv'} ({len(frame)} rows)")


if __name__ == "__main__":
    main()
