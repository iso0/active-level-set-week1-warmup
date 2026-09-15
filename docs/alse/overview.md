# Overview

Thesis: "Sample-Efficient Active Level-Set Estimation, with an Application to Melt-Pool Regime Boundaries". Supervisor: Ioan.
This file is the entry point to the written record. It states the question, the final method, the evidence chain, the state of the project on 2026-09-03, and the framing decisions still open.
All archive paths are relative to the archive root (`../thesis_work_chatgpt`). Lean experiment names are those in `docs/architecture.md`. Every number was copied from the named artifact.

## 1. Research question and final method

1. Setting: SPH simulations of laser powder-bed fusion with four inputs, P [W], VX [m/s], LS [m, Gaussian spot radius], ST [K, substrate temperature], and one manual binary label, `has_keyhole`.
2. Question: which simulations should be labelled so that the keyhole/conduction boundary is learned with the fewest simulator calls?
3. Population: 405 simulations, 73 Keyhole, frozen in `data/population.csv` (byte-identical to archive `outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv`).
4. Surrogate: a 4D `GaussianProcessClassifier` with kernel `C(1,(1e-3,1e3)) * Matern(1,(1e-2,1e2), nu=1.5)`, zero optimizer restarts, fixed-kernel then `LogisticRegression(C=1.0)` fallback (`src/week7_phase6_real_data_boundary_active_level_set.py::fit_gpc`).
5. Acquisition: `binary_margin`, the training-pool candidate maximising `1 - 2|p - 0.5|`, ties to the lowest row index.
6. Start: 16-point seeded maximin design on the standardized training pool, features only, both classes required (`src/week8_5_frozen_sample_efficiency_confirmation.py::initial_design`).
7. Protocol: Week 8.5 frozen protocol v1.0.0, 20 repeats x 5 grouped folds = 100 runs, 30 random continuations per run, adaptive horizon 80 -> 120 -> 160 (`outputs/week8_5_frozen_confirmation/preregistered_protocol.json`).
8. Primary endpoint: Fold-B1-q20 accuracy AULC over budgets 16-80, that is accuracy on the ceil(0.2 x 81) = 17 test rows nearest the empirical boundary.
9. Headline: margin 0.813520 vs random 0.776220 (`outputs/week8_5_frozen_confirmation/repeat_level_metrics.csv`), delta +0.037300, two-sided 95% CI [0.030132, 0.044416], PASS (`decision_ledger.csv`, `bootstrap_or_hierarchical_ci.csv` in the same directory).
10. Exploratory frontier: the M3 surrogate (frozen physics logistic mean in h plus ARD Matern-3/2 residual GPC) reaches 0.8424908 on the same query paths (`outputs/week9_phase1_13_fixed_physics_ard_discrepancy/model_summary.csv`). No acquisition on top of M3 has beaten margin, including the committed Phase 1.18B result (section 2.9).

## 2. Evidence chain

Each phase lists the archive script, the decision taken, and the headline numbers with their source artifact. Lower is better for near-boundary error; higher is better for accuracy AULC.

### 2.1 Synthetic warm-up (Weeks 1-4)

| Phase | Archive script | Decision | Headline numbers | Artifact |
|---|---|---|---|---|
| Week 1-2, Branin (2D), GPR stand-in, five pool rules | `week2_acquisition_comparison.py` | randomized straddle best; random far behind | mean final error at n=50: randomized_straddle 0.0602, straddle 0.0620, smallest_abs_mu 0.0659, expected_feasibility 0.066350, random 0.1194 | `outputs/week2_acquisition_comparison/method_summary_table.csv` |
| Week 3, Ackley4 (4D), same rules | `week3_4d_named_benchmark_comparison.py` | straddle best in 4D; ranking not stable across functions | n=80: straddle 0.1684, randomized_straddle 0.1754, expected_feasibility 0.1898, smallest_abs_mu 0.2362, random 0.2827 | `outputs/week3_4d_named_benchmark_comparison/method_summary_table.csv` |
| Week 4 Exp 01-05, boundary metrics (q10/q20/q30) and GPR heuristics | `week4_01_boundary_metrics.py` .. `week4_05_*` | heuristics negative except lookahead on Branin; motivates a classifier surrogate | lookahead global error Branin 0.0559, Ackley 0.2290 | `outputs/week4_04_lookahead_boundary_uncertainty/{branin,ackley}/final_metrics_table.csv` |
| Week 4 Exp 06-09, fixed-kernel GPC, uncertainty-repulsion rule, Bernoulli SUR | `week4_06_gp_classifier_surrogate.py`, `week4_09_gpc_bernoulli_sur_validation.py` | no acquisition dominates across functions (claim C10) | q20 winners: Branin uncertainty_repulsion 0.2560, Hartmann4 SUR k25 0.3730, Ackley entropy 0.421167 (3 seeds) | `outputs/week4_09_gpc_bernoulli_sur_validation/combined/gpc_bernoulli_sur_validation_summary.csv` |

Lean experiments: `synthetic_gpr.py` (Weeks 1-3 and Exp 01), `synthetic_gpc.py` (Exp 06 and 09).

### 2.2 Real-data regression warm-ups (Weeks 5-6, `ioandanielc/sph_dataset`, 241 simulations)

| Phase | Archive code | Decision | Headline numbers | Artifact |
|---|---|---|---|---|
| Week 5, first-Conduction timestep regression | `notebooks/week_05/01-05` (no src module) | Matern 3/2 default kernel; data provenance rules | clean 91 sims RMSE 2537.0, R2 0.9171; broad 238 sims RMSE 16256.3, R2 0.4060 | `outputs/week5_02_first_conduction_gp_kernel_comparison/{clean,broad}/*_kernel_metrics.csv` |
| Week 6, melt-pool response audit and depth model | `week6_phase1_melt_pool_data_audit.py` .. `week6_phase4_*` | T0 window rule; learned WhiteKernel nugget (method B); G3/R3 persistent-depth proxies defined | depth RMSE 2.728943 um, R2 0.968873 on 230 stable sims | `outputs/week6_02_5_depth_model_closure/depth_model_decision.md` |

These phases are protocol origins only. Their scientific conclusions were superseded by Week 7 on `sph_v2`. No lean experiment reproduces them; the target-extraction rules are documented in `docs/data.md`.

### 2.3 sph_v2 data and proxies (Week 7 Phases 1-5.5)

| Phase | Archive script | Decision | Headline numbers | Artifact |
|---|---|---|---|---|
| Ph1 audit and registry | `week7_phase1_sph_v2_dataset_shift_audit.py` | `has_keyhole` = any frame with `label_final == 'Keyhole'` | 407 experiments, 110 804 labelled frames, 73 Keyhole at pin d69dac5b | `outputs/week7_01_sph_v2_audit/summary.json` |
| Ph2 target extraction | `week7_phase2_sph_v2_physical_target_extraction.py` | T0, max depth, G3/R3 extracted; sentinel `s3.402823e+38` handled | 350/407 extracted, 57 monitor-incomplete | `outputs/week7_02_sph_v2_target_extraction/summary.json` |
| Ph3-4 regression on new data | `week7_phase3_*`, `week7_phase4_*` | depth error heavy-tailed and Keyhole-concentrated; pivot to the binary boundary problem | depth RMSE 21.8082 um (Matern 3/2 + nugget); Keyhole vs non-Keyhole RMSE 32.931 vs 9.788 um | `outputs/week7_03_new_data_physical_model_stability/stability_conclusion_table.csv`; `outputs/week7_04_new_data_feature_effects_depth_diagnostics/depth_error_diagnosis_summary.csv` |
| Ph5-5.5 proxies and population refresh | `week7_phase5_*`, `week7_phase5_5_*` | G3 separates new-data labels but transfers with caveat; max_depth is the robust scalar companion; population fixed at pin b6dc254a | G3 AUC 1.0000, LOO BA 1.0000; worst transfer BA G3 0.8125, max_depth 0.9444; 405/407 ready | `outputs/week7_05_keyhole_physical_proxy_analysis/physical_proxy_candidate_scorecard.csv`; `outputs/week7_05_5_g3_robustness_transfer_analysis/results_summary.md` |

Lean: `alse.data` (pins, registry, population loading). Target extraction stays in the archive; its output is `data/population.csv`.

### 2.4 Exploratory benchmark (Week 7 Phases 6-7)

| Phase | Archive script | Decision | Headline numbers | Artifact |
|---|---|---|---|---|
| Ph6 central benchmark, 4 repeats x 5 grouped folds = 20 runs, warm start 12-16, budget 80 | `week7_phase6_real_data_boundary_active_level_set.py` | HYBRID / NO CLEAR WINNER | q20 error AULC binary_uncertainty_repulsion 0.1862 vs max_depth_straddle 0.2053 (difference CI [-0.0182, 0.0548]); BA AULC 0.9171 vs 0.9432; transfer floor 0.5159 (max_depth) vs 0.7457 (binary) | `outputs/week7_06_real_data_boundary_active_level_set/phase6_final_decision.csv`, `domain_transfer_model_summary.csv` |
| Ph7 preregistered hybrids, same 20 runs replayed | `week7_phase7_final_boundary_hybrid_benchmark.py` | BINARY ACQUISITION PRIMARY; both hybrid flags false | B1 q20 AULC binary 0.1862, max_depth 0.2053, gate20 0.1943, rank fusion 0.1872, random 0.2289 | `outputs/week7_07_final_boundary_hybrid_benchmark/phase7_final_decision.csv`, `phase7_method_scorecard.csv` |
| Week 8 offline consolidation | `week8_final_sample_efficiency_thesis_consolidation.py` | claim ledger C01-C13; STALE wording, see section 3.5 | B1-q20 accuracy AULC 0.8138 vs 0.7711; "budget 30 matched by Random at 70", 2.33x, 40 queries | `outputs/week8_02_thesis_consolidation/final_thesis_claim_ledger.csv`; `outputs/week8_01_final_sample_efficiency/random_equivalent_budget.csv` |

Lean: `real_benchmark.py`.

### 2.5 Frozen confirmation (Week 8.5)

Archive script `week8_5_frozen_sample_efficiency_confirmation.py`; lean `frozen_protocol.py`. All numbers from `outputs/week8_5_frozen_confirmation/decision_ledger.csv` and `bootstrap_or_hierarchical_ci.csv`; rho from `adaptive_horizon_decision.json`. Full run 9336 s (`runtime_compute_report.json`).

| Claim | Point estimate | One-sided 95% lower | Two-sided 95% CI | Rule | Decision |
|---|---|---|---|---|---|
| primary_performance (margin minus random, B1-q20 AULC 16-80) | +0.037300 | 0.031270 | [0.030132, 0.044416] | lower >= 0.020 | PASS |
| query_saving (queries to persistent 0.80 crossing) | 20.099 | 13.910 | [12.485, 26.711] | rho >= 0.95 and lower >= 10 | QUALIFY |
| multiplier | 1.5144x | 1.3292 | [1.2928, 1.7605] | rho >= 0.95 and lower >= 1.25 | QUALIFY |
| repulsion_h_0.15 (repulsion minus margin) | +0.001829 | -0.000625 (min over 16-80 and 16-40) | | lower >= 0.010 | QUALIFY |
| overall_primary_confirmation | | | | first three PASS | NOT_CONFIRMED |

The QUALIFY outcomes follow from rho_random = 0.7337 / 0.798 / 0.831 at horizons 80 / 120 / 160: too many random continuations never cross 0.80 within the horizon, so the saving is right-censored.

### 2.6 H=320 closure (Week 9 Phase 1)

Archive scripts `week9_phase1_horizon_extension.py`, `week9_phase1_close_week8.py`. Artifacts under `outputs/week9_phase1_close_week8/`.

| Quantity | Value | Artifact |
|---|---|---|
| persistent crossings at H=320 | margin 91/100, random 2727/3000 (267 guaranteed > 320, 6 indeterminate) | `crossing_by_horizon.csv`, `query_saving_claim_decision.json` |
| restricted mean query burden | margin 53.47 vs random 78.466, difference 24.996, ratio 1.467 | `final_q1_q9_answers.json` |
| descriptive two-sided CI of the difference | [10.317, 38.357] | `query_bootstrap_summary.json` |
| "at least X queries saved" | not identified, status NOT_SUPPORTED_MARGIN_TAIL_UNRESOLVED | `query_saving_claim_decision.json` |
| terminal B1-q20 accuracy gap at budget 40 / 80 / 160 / 320 | +0.0425 / +0.0371 / +0.0196 / +0.0006 | `terminal_accuracy_answers.csv` |

Decision: the AULC gain is early learning speed, not a terminal accuracy difference; no unconditional query-saving sentence is permitted.

### 2.7 Physics coordinate h and the M3 surrogate (Week 9 Phases 1.5-1.13)

All AULC values are B1-q20 accuracy AULC 16-80 on the frozen Week 8.5 splits. Phases 1.5 and 1.7 ran their own acquisition arms. Phase 1.8 separates model from path. Phases 1.9, 1.11, 1.12 and 1.13 replay every model on the frozen margin query path A0, so they compare models, not acquisitions.

| Phase | Archive script | Decision | Headline numbers | Artifact |
|---|---|---|---|---|
| 1.5 h coordinate, h = P / sqrt(VX * LS^3) [W s^1/2 m^-2] | `week9_phase1_5_h_physics_confirmation.py` | exponents recover theory; h-only model beats 4D GPC; h as acquisition on 4D GPC hurts | VX/P exponent -0.518 [-0.659, -0.381] vs theory -0.5; LS/P -1.444 [-1.995, -1.074] vs -1.5; h-model+h-query 0.831737 (+0.018217 [+0.011567, +0.024619]); h-query on 4D GPC -0.012693 | `outputs/week9_phase1_5_h_physics_confirmation/empirical_exponent_summary.csv`, `active_AULC_contrasts.csv` |
| 1.7 physics-ridge + Matern-3/2 residual GPC (M1), own margin path | `week9_phase1_7_physics_ridge_residual_gp.py` | PASS | 0.833539, +0.020018 [+0.014071, +0.026264], 19/20 repeats | `outputs/week9_phase1_7_physics_ridge_residual_gp/primary_decision.json` |
| 1.8 model x path decomposition | `week9_phase1_8_model_path_decomposition.py` | MODEL_DOMINANT | MODEL +0.021402 [+0.014550, +0.028858]; PATH -0.001383 [-0.005340, +0.002606]; M1 on A0 0.829972 | `outputs/week9_phase1_8_model_path_decomposition/primary_decomposition.csv`; `outputs/week9_phase1_11_fixed_mean_discrepancy_gp/model_summary.csv` |
| 1.9 generic log-linear trend control | `week9_phase1_9_physics_specificity_control.py` | PHYSICS_SPECIFIC_SUPPORTED | generic trend 0.812050; physics minus generic +0.017923 [+0.013442, +0.022725]; generic minus 4D -0.001471 | `outputs/week9_phase1_9_physics_specificity_control/primary_AULC_summary.csv` |
| 1.10 external Masinelli 2025 Ti64 | `week9_phase1_10_external_experimental_validation.py` | h discriminates but is not superior to a generic model (ledger claim E NOT SUPPORTED) | Ti64 H ROC-AUC 0.976471 vs G 0.992081; H minus G -0.015611 [-0.016686, -0.014536] | `outputs/week9_phase1_10_external_experimental_validation/ti64_model_summary.csv`, `ti64_paired_contrasts.csv`, `claim_ledger.md` |
| 1.11 fixed h-mean + isotropic residual (M2) | `week9_phase1_11_fixed_mean_discrepancy_gp.py` | FIXED_MEAN_SUPPORTED | M2 0.830230; h-only H 0.830813 | `outputs/week9_phase1_11_fixed_mean_discrepancy_gp/model_summary.csv` |
| 1.12 standalone GPC kernels G0-G4 | `week9_phase1_12_gpc_kernel_adequacy.py` | KERNEL_GAP_CLOSED | G3 ARD Matern-3/2 0.826595 | `outputs/week9_phase1_12_gpc_kernel_adequacy/model_summary.csv` |
| 1.13 M3 = frozen h logistic mean + ARD Matern-3/2 residual | `week9_phase1_13_fixed_physics_ard_discrepancy.py` | HYBRID_GAIN_SUPPORTED; M3 declared preferred simulator surrogate | M3 0.8424908 [0.838438, 0.846746]; M3-H +0.011677 [+0.007201, +0.016149]; M3-G0 +0.028971 [+0.021930, +0.035432] | `outputs/week9_phase1_13_fixed_physics_ard_discrepancy/model_summary.csv`, `paired_contrasts.csv` |

Lean: `physics_surrogates.py` (replay of M0, H, M2W, M3 on A0; M3-margin sequential run).

### 2.8 Acquisition search on M3 (Week 9 Phases 1.14-1.18B0)

| Phase | Archive script | Decision | Headline numbers | Artifact |
|---|---|---|---|---|
| 1.14 M3-margin sequential (P1) vs M3 on A0 (P0) | `week9_phase1_14_m3_margin_acquisition.py` | LATE_ACQUISITION_GAIN_ONLY | P1 0.844623 vs P0 0.8424908; +0.002132 [-0.001167, +0.005621], 12/20; late 41-80 +0.004510 [+0.000120, +0.009020]; early 16-40 -0.001556 | `outputs/week9_phase1_14_m3_margin_acquisition/paired_contrasts.csv`, `early_late_contrasts.csv`, `run_manifest.json` |
| 1.15A correction-magnitude signal | `week9_phase1_15a_physics_residual_signal_audit.py` | redundant with margin | Spearman(abs correction, M3 margin) = -0.9506 | `outputs/week9_phase1_15a_physics_residual_signal_audit/correction_signal_summary.csv` |
| 1.16 repulsion scale sweep c in {0.25..4} on M3 | `week9_phase1_16_m3_repulsion_scale_audit.py` | null | best Holm-adjusted p 0.207 (c=4), no rejection | `outputs/week9_phase1_16_m3_repulsion_scale_audit/multiplicity_summary.csv` |
| 1.17A contour geometry | `week9_phase1_17a_physics_contour_geometry_audit.py` | MIXED_GEOMETRIC_MECHANISM | | `outputs/week9_phase1_17a_physics_contour_geometry_audit/mechanism_decision.json` |
| 1.18A level-set acquisition compatibility | `week9_phase1_18a_level_set_acquisition_compatibility_audit.py` | PA_TVR_REJECTED; SUR and SMOCU classed REQUIRES_APPROXIMATION; recommendation FAST_GPC_SUR pending validation | | `outputs/week9_phase1_18a_level_set_acquisition_compatibility_audit/method_decisions.csv`, `pa_tvr_decision.json` |
| 1.18B0 fast rank-one SUR vs exact | `week9_phase1_18b0_fast_gpc_sur_update_validation.py` | FAST_SUR_REJECTED | median Spearman 0.481 (gate 0.95); top-1 agreement 0.44 | `outputs/week9_phase1_18b0_fast_gpc_sur_update_validation/primary_decision.json` |

### 2.9 Phase 1.18B, prospective exact GPC-SUR

Archive scripts `week9_phase1_18b_prospective_global_gpc_sur_benchmark.py` (engine) and `week9_phase1_18b_finalize.py` (analysis). Arms P1_EXACT_FIXED_SUR and P2_PHYSICS_REFIT_SUR (exact finite-pool GPC-SUR, U = mean p(1-p) over the unqueried pool) against P0 = M3-margin with gate 0.844623161764706 (`outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark/baseline_gate.json`, `analysis_specification.json`).

The archive working tree holds no result for this phase, but the archive's git HEAD does. See section 3.3 for the discrepancy. Numbers below are from the committed files at archive commit `2552078` (2026-09-03 20:32, "Add prospective global GPC-SUR benchmark"), readable with `git show 2552078:<path>`; they are absent as files in the working tree.

| Quantity | Value | Artifact (at commit 2552078) |
|---|---|---|
| q20 AULC P0 / P1 / P2 | 0.844623 / 0.843244 / 0.840170 | `outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark/model_aulc_summary.csv` |
| P1 minus P0 | -0.001379 [-0.003801, +0.000726], 9/20 positive | `q20_primary_contrasts.csv` |
| P2 minus P0 | -0.004453 [-0.010703, +0.001627], 8/20 positive | `q20_primary_contrasts.csv` |
| Holm-adjusted p (P1-P0, P2-P0) | 1.0, 1.0 | `multiplicity_adjustment.csv` |
| decisions | GLOBAL_SUR_NO_GAIN; PHYSICS_REFIT_SUR_CHANGES_PATH_ONLY; LABEL_SAVING_NOT_SUPPORTED | `primary_decision.json`, `physics_refit_decision.json`, `sample_efficiency_decision.json` |
| run | 200 jobs, 155 reused, 8 workers, 2840 s, complete | `execution_report.json` |

The committed supervisor page states that this result "closes the planned Week 9 acquisition search" (`SUPERVISOR_PHASE1_18B_ONE_PAGE.md` at commit 2552078). No lean experiment is planned for 1.18B; `alse.sur` keeps the exact finite-pool update.

## 3. State of the thesis on 2026-09-03

### 3.1 Confirmed (frozen, preregistered, citable as primary)

- Binary GPC with `binary_margin` beats random on near-boundary accuracy AULC: +0.037300 [0.030132, 0.044416], PASS (`outputs/week8_5_frozen_confirmation/decision_ledger.csv`).
- Query saving and multiplier are QUALIFY, not PASS; overall confirmation NOT_CONFIRMED (same file).
- An "at least X queries saved" sentence is not identified even at H=320 (`outputs/week9_phase1_close_week8/query_saving_claim_decision.json`).
- The Phase 7 preregistered rule chose BINARY ACQUISITION PRIMARY over both hybrids (`outputs/week7_07_final_boundary_hybrid_benchmark/phase7_final_decision.csv`).

### 3.2 Exploratory (repeat-block bootstraps on frozen paths; no preregistration beyond each phase's own ledger)

- Phase 6/7 benchmark numbers (20 runs, warm start 12-16), including the Max-Depth GPR comparator.
- The h coordinate, M1, M2, G3, M3 model chain (Phases 1.5-1.13); 1.9 and 1.11-1.13 are A0 replays.
- Every acquisition result on M3 (Phases 1.14-1.18B); none beats margin at the 16-80 endpoint.
- Phase 1.10 external validation, a qualified negative that no ledger cites.

### 3.3 Unfinished or inconsistent

Phase 1.18B exists in two states inside the same archive.

| | Archive working tree (the snapshot the lean project reads) | Archive git HEAD `2552078` (branch `codex/week9-phase1-18b-prospective-global-gpc-sur-benchmark`, also on `origin`) |
|---|---|---|
| Checkpoints | 77/100 P1 and 73/100 P2 (`checkpoints/P1_EXACT_FIXED_SUR/`, `checkpoints/P2_PHYSICS_REFIT_SUR/`, 294 MB, gitignored); median `run_seconds` 201 s (P1) and 460 s (P2), so about 4.7 CPU-hours were outstanding | run completed with 155 checkpoints reused (`execution_report.json`) |
| `execution_report.json` | 2-job smoke record, `complete: false` | `complete: true`, 200 jobs, 8 workers, 2840 s |
| Finalize outputs | none; `week9_phase1_18b_finalize.py` was never run here | 49 committed files (reports, `q20_primary_contrasts.csv`, figures); decision GLOBAL_SUR_NO_GAIN |
| Engine source | 6-line older variant (no try/except around interrupted checkpoints) | committed version; `.gitignore` identical in both |

`git status` in the archive lists the 49 committed result files as deleted and 3 as modified, because the working-tree snapshot predates the commit. The critique of the inventory (`map/CRITIQUE.md`) recorded HEAD as `1e34b47` on 2026-09-03; the branch advanced at 20:32 the same day. Action needed: restore the committed 1.18B outputs into the archive working tree (`git checkout -- outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark` or a copy from the parent repository at `C:/Users/ozgur/Documents/thesis`) before `curate_results.py` runs, or cite them by commit as this file does. Until then the lean tree treats 1.18B as committed-but-unmaterialised, and the later committed result wins over the "in progress" description.

### 3.4 Two coexisting protocols

| | Phase 6/7 (exploratory) | Week 8.5 (confirmatory) |
|---|---|---|
| Archive script | `week7_phase6_real_data_boundary_active_level_set.py`, `week7_phase7_*` | `week8_5_frozen_sample_efficiency_confirmation.py` |
| Runs | 4 repeats x 5 grouped folds = 20 | 20 repeats x 5 grouped folds = 100 |
| Initial design | shared permutation, reveal >= 12 until both classes (observed 12-16, `active_initialization_audit.csv`) | 16-point seeded maximin, both classes required |
| Random baseline | one binary_random arm | 30 predeclared continuations per run |
| Primary metric | q20 error AULC 16-80 (lower better) | B1-q20 accuracy AULC 16-80 (higher better) |
| Inference | 5000-resample paired bootstrap, descriptive (`active_paired_bootstrap_intervals.csv`) | 20 000-draw hierarchical bootstrap, preregistered rules |
| Cited by | Week 8 ledger C02/C03/C04 | every Week 9 phase |

The thesis must present Phase 6/7 as exploratory and Week 8.5 as confirmatory. Both initial-design rules and both repulsion normalisations (shortlist in `week7_phase6`, pool in `week4_08/09`) survive in `alse` because stored trajectories depend on them.

### 3.5 Two headline-wording conflicts

| Topic | Week 8 consolidation (`outputs/week8_02_thesis_consolidation/final_thesis_claim_ledger.csv`) | Later frozen result | Rule |
|---|---|---|---|
| Primary acquisition | C02: binary uncertainty-repulsion primary | Week 8.5: binary_margin primary; repulsion minus margin +0.001829, one-sided lower -0.000625, QUALIFY | Margin is the confirmatory method; repulsion is the Phase 6/7 exploratory champion with the ablation caveat |
| Sample-efficiency headline | C01 / H04: budget 30 matched by Random at 70, 2.33x, 40 queries saved | Week 8.5: 20.099 queries [12.485, 26.711], 1.5144x, both QUALIFY; H=320: saving not identified | Quote the Week 8.5 ledger; treat H=320 as the diagnostic that forbids an unconditional saving sentence |

The Week 8 package was never regenerated after Week 8.5. Where the two disagree, the later frozen result wins and the conflict is stated in the text.

## 4. Open framing decisions

These come from the archive inventory, section 9 items 8-14. The student must decide each one before `docs/claims.md` is final.

1. Which headline is cited: Week 8 (2.33x), Week 8.5 (1.51x QUALIFY) or Week 9 H=320 (no identified saving). This file adopts Week 8.5 with the H=320 caveat.
2. Whether M3 (Phase 1.13, 0.8425) is the thesis surrogate or the thesis stops at the frozen 4D GPC (0.8135). Phase 1.7 must be framed as a model gain (Phase 1.8 MODEL_DOMINANT), not an acquisition gain. M3 lengthscales are standardized-space geometry, not physics: the residual-SD bound and the ARD upper bound are hit in a large share of fits (`model_fit_summary.csv` at commit 2552078: upper-bound fraction 0.79, residual-SD bound fraction 0.79 for P0).
3. How the two protocols (3.4) are presented, and which initial-design and repulsion-normalisation rule is called "the method".
4. Whether the Max-Depth GPR comparator (Week 8 C03/C07) stays in the story after Week 8.5 dropped it. If yes, `choose_continuous_candidate` and the online-threshold machinery must be kept in full.
5. Which Week 1-4 numbers appear directly. Only Exp 09 is cited by a ledger (C10); Ackley ran with 3 seeds there.
6. Scope of the Week 5 and Week 6 chapters: full chapters with tables, or a protocol-origin appendix. No ledger cites a Week 6 number.
7. Keep or drop: Phase 1.10 external validation, the secondary G3-common benchmark (404 rows), and the Week 6 Phase 3.5 label-circularity finding as a stated limitation.

Related documents: `docs/architecture.md` (porting contract), `docs/experiments.md` (experiment index), `docs/claims.md` (permitted and forbidden claims), `docs/protocol.md`, `docs/data.md`, `docs/decisions.md`, `docs/archive.md`.
