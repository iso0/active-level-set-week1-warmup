# Protocol

Exact benchmark protocols, copied from the archive sources and artifacts. Paths are relative to `../thesis_work_chatgpt`. Lean code: `alse/protocol.py`, `alse/metrics.py`, `alse/stats.py`; experiments `frozen_protocol.py` (A), `real_benchmark.py` (B), `physics_surrogates.py` (C).

## A. Week 8.5 frozen protocol (confirmatory)

Source `src/week8_5_frozen_sample_efficiency_confirmation.py`. Declaration `outputs/week8_5_frozen_confirmation/preregistered_protocol.json`, id `week8_5_frozen_confirmation_protocol/v1.0.0`, sha256 of the canonical bytes `bb16865a06d8fbdeea00f8c41f0929bfb7fbaf2f7b3e4ebade9cb2ffc59b1c66` (`protocol_sha256.txt`; CRLF caveat in `docs/data.md` section 12). Other artifacts named below live in the same output directory.

Population
: `primary_common_population.csv`, 405 rows, 73 Keyhole, sha256 `c15658ca...`; `FEATURES = (P, VX, LS, ST)`; target `has_keyhole`; group `input_tuple_sha256`.

Splits (`build_splits`)
: repeats 1..20; `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed_u32(seed_key('outer_split', 'repeat', 'NN')))` on `has_keyhole`, grouped by `input_tuple_sha256`; 100 `SplitSpec(run_id='w85__rRR_fFF', repeat, fold, train_indices, test_indices)`, 324 train and 81 test rows each (`grouped_split_manifest.csv`).

Seeds (`seed_key`, `seed_u32`)
: `seed_key(*parts)` joins `'week8_5_frozen_confirmation|v1'` and the parts with `|`; `seed_u32(key) = int.from_bytes(sha256(key.encode('utf-8')).digest()[:8], 'little') % 2**32`. Key templates: `outer_split|repeat|NN`; `run|RUN|initial_design`; `run|RUN|arm|binary_margin|fit|budget|BBB`; `run|RUN|arm|binary_random|continuation|CC|order`; `run|RUN|arm|binary_random|continuation|CC|fit|budget|BBB`; `run|RUN|arm|binary_uncertainty_repulsion|h|0.15|fit|budget|BBB`; `hierarchical_bootstrap|draws|20000`. Forbidden legacy components: `6022026`, `primary_common`, `shared_pool_permutation`. 12 distinct fit keys collide after the uint32 reduction (`postrun_provenance_addendum.json`); random-order seeds are unique.

Initial design (`initial_design`)
: `StandardScaler` fitted on the training-pool features; `rng = default_rng(seed_u32(seed_key('run', run_id, 'initial_design')))`; first point `rng.integers(len(train))`; then greedy maximin: add the pool row whose distance to its nearest chosen row is largest, ties (`np.isclose`, rtol 1e-12, atol 1e-14) to the smallest population index; stop at 16 points; raise if both classes are not present (labels never steer the choice). Arm-blind; `initial_design_manifest.csv`.

Arms (`run_trajectory`)
: one query per budget step from the training pool minus queried rows. `binary_margin`: argmax of `u = 1 - 2|p - 0.5|`, ties to the lowest row index. `binary_random`: 30 continuations per run, each a predeclared permutation of train minus initial, seeded by `random_order_key`. `binary_uncertainty_repulsion`: `p6.choose_binary_candidate`, shortlist the top `max(25, ceil(0.10 n))` candidates by `u`, score `minmax(u) * (1 - exp(-d^2 / (2 * 0.15^2)))` with `d` the standardized distance to the nearest queried row, ties to the lowest row index. Fit seed per budget from the templates above.

Surrogate
: `week7_phase6::fit_gpc`: `GaussianProcessClassifier(ConstantKernel(1, (1e-3, 1e3)) * Matern(1, (1e-2, 1e2), nu=1.5), optimizer='fmin_l_bfgs_b', n_restarts_optimizer=0, max_iter_predict=100)`; fallback to a fixed-kernel GPC, then `LogisticRegression(C=1.0)`. Inputs standardized with the training-pool scaler.

Budgets and horizon (`declared_budgets`, `adaptive_run`)
: evaluate at 16..80 step 1, 82..120 step 2, 124..160 step 4. After H = 80 and H = 120, extend every arm uniformly if `rho_random(H) < 0.95`, stop at 160; `rho_random` = fraction of the 3000 Random continuations with an observed persistent 0.80 crossing. Observed 0.7337 / 0.798 / 0.831 at 80 / 120 / 160, final H = 160 (`adaptive_horizon_decision.json`). GPC fits = 100 x 32 x (H - 15) = 208 000 / 336 000 / 464 000; full run 9 336 s on 4 workers (`runtime_compute_report.json`). Not rerun in the lean project.

Evaluation flags (`b1_distance`, `boundary_flags`, `compute_metrics`)
: B1 distance over all 405 standardized rows (section D); test rows ordered by B1 with `p7.deterministic_order`; `B1_q20` = first `ceil(0.2 * 81) = 17` rows, `B1_q30` = first 25 rows. Metrics on flagged rows with `pred = p >= 0.5`: accuracy, recall, balanced_accuracy, FN, FP, TN, TP, row_count.

Endpoints (`aulc`, `persistent_crossing`, `build_run_metrics`)
: primary = Fold-B1-q20 accuracy AULC 16-80, `np.trapezoid(values, budgets) / 64` over the complete integer grid. Secondary: AULC 16-40, B1_q30 AULC 16-80, budget-40 and terminal metrics. Persistent crossing = first declared checkpoint at which it and the next two checkpoints are >= target (0.80 primary; 0.75 and 0.85 sensitivity), NaN if never (right-censored `H+`); restricted crossing = crossing if observed else H.

Inference (`hierarchical_bootstrap`)
: 20 000 draws; each draw resamples the 20 repeat ids with replacement, keeps all 5 folds, and resamples the 30 Random continuations with replacement inside each (repeat, fold). Estimands: `delta_AULC` (margin minus mean random), `delta_Q` (mean restricted random burden minus margin burden), `multiplier` (mean random burden / mean margin burden), `delta_repulsion_AULC16_80`, `delta_repulsion_AULC16_40`, `delta_repulsion_min`. One-sided 95% lower bound = 0.05 quantile; two-sided = 0.025 and 0.975 quantiles.

Decision rules (`decision_ledger`)
: performance PASS iff lower >= 0.020, QUALIFY iff point > 0, else FAIL. query_saving PASS iff rho >= 0.95 and lower >= 10, QUALIFY iff lower > 0, else FAIL. multiplier PASS iff rho >= 0.95 and lower >= 1.25, QUALIFY iff lower > 1, else FAIL. repulsion PASS iff lower of `delta_repulsion_min` >= 0.010, QUALIFY iff both point estimates > 0, else FAIL. Overall PASS iff the first three PASS, else NOT_CONFIRMED.

Outcome (`decision_ledger.csv`; two-sided intervals from `bootstrap_or_hierarchical_ci.csv`; horizon 160, rho 0.831):

| Claim | Point estimate | One-sided 95% lower | Two-sided 95% | Decision |
|---|---|---|---|---|
| primary_performance | +0.0372998 | 0.0312703 | [0.030132, 0.044416] | PASS |
| query_saving | 20.099 | 13.90995 | [12.485, 26.711] | QUALIFY |
| multiplier | 1.514436 | 1.329210 | [1.2928, 1.7605] | QUALIFY |
| repulsion_h_0.15 | +0.0018290 | -0.000625 | | QUALIFY |
| overall_primary_confirmation | | | | NOT_CONFIRMED |

Information flow: acquisition may use P, VX, LS, ST and labels revealed by its own queries; never test rows, hidden labels or B1/B2/B3 scores (`information_flow` in the protocol JSON).

## B. Phase 6/7 protocol (exploratory)

Source `src/week7_phase6_real_data_boundary_active_level_set.py` (Phase 6) and `src/week7_phase7_final_boundary_hybrid_benchmark.py` (Phase 7, a replay of the same runs). Artifacts under `outputs/week7_06_real_data_boundary_active_level_set/` and `outputs/week7_07_final_boundary_hybrid_benchmark/`. Cited by the Week 8 ledger C02/C03/C04.

Splits (`build_outer_splits`)
: `BASE_SEED = 6022026`; for repeat 0..3: `StratifiedGroupKFold(5, shuffle=True, random_state=stable_seed(6022026, population_name, repeat))` grouped by `input_tuple_sha256`; `run_id = '<population>__rNN_fNN'` (NN = repeat + 1; fold from 1); `run_seed = stable_seed(BASE_SEED, run_id)`; 20 runs, 324 / 81 (`outer_split_manifest.csv`). Populations: `primary_common` (405 rows) and the secondary G3-common population (404 rows).

Warm start (`warm_start_indices`)
: `permutation = pool[stable_rng(BASE_SEED, run_id, 'shared_pool_permutation').permutation(len(pool))]`; reveal in that order until at least `NOMINAL_WARM_START = 12` rows and both classes are seen; cap `min(MAX_WARM_START = 80, budget)`; raise otherwise. Observed 12 to 16 (`active_initialization_audit.csv`); common AULC start 16; `FINAL_BUDGET = 80`; one query per step; `PRESENTATION_CHECKPOINTS = (12, 15, 20, 25, 30, 40, 50, 60, 70, 80)`.

Methods (`PRIMARY_METHODS`, `SECONDARY_G3_METHODS`)
: `max_depth_random`, `max_depth_boundary_proximity`, `max_depth_straddle`, `max_depth_randomized_straddle`, `max_depth_expected_feasibility` on a Matern-3/2 GPR of `value__max_depth` (`fit_gpr`: `GPR_ALPHA_PRIMARY = 1e-8`, retry `GPR_ALPHA_RETRY = 1e-6`, y standardized on the queried set), with the online threshold tau chosen from the queried (depth, label) pairs only, direction higher depth = Keyhole (`choose_higher_threshold`; `STRADDLE_KAPPA = 1.96`). `binary_random`, `binary_margin`, `binary_uncertainty_repulsion` on the GPC of section A (`CLASSIFIER_GATE_FRACTION = 0.10`, `CLASSIFIER_MIN_SHORTLIST_SIZE = 25`, `CLASSIFIER_REPULSION_BANDWIDTH = 0.15`). Secondary: `g3_random`, `g3_straddle`, `max_depth_g3_common_random`, `max_depth_g3_common_straddle`, `binary_g3_common_random`, `binary_g3_common_margin`. Kernel bounds `KERNEL_CONSTANT_BOUNDS = (1e-3, 1e3)`, `KERNEL_LENGTH_BOUNDS = (1e-2, 1e2)`, `ACTIVE_OPTIMIZER_RESTARTS = 0`.

Metrics (`classification_metrics`, `summarize_active`)
: per budget on the 81 untouched test rows: balanced accuracy, sensitivity, specificity, global error, ROC AUC, average precision, Brier, and q10 / q20 / q30 error on the test-fold boundary subsets (`assign_test_boundary_subsets`: the 9 / 17 / 25 test rows nearest the boundary). AULC over 16-80 divided by 64 (`common_normalized_aulc__*`; lower error is better). Queries-to-tolerance for balanced accuracy >= 0.80 / 0.85 / 0.90 and q20, q30 error <= 0.30 / 0.25 / 0.20, no extrapolation.

Inference (`paired_comparisons`)
: `PAIRED_BOOTSTRAP_RESAMPLES = 5000` resamples of the 20 run-level differences; pairs `best_vs_best_descriptive`, `predeclared_straddle_vs_margin`, `predeclared_randomized_vs_repulsion`, and every active method against its shared random arm; descriptive only (`formal_hypothesis_test = False`).

Phase 6 decision (`build_final_decision`)
: CONTINUOUS MAX-DEPTH PRIMARY iff the best max-depth method beats the best binary method on q20 and q30 error AULC, its balanced-accuracy AULC is not worse by more than 0.02, both bootstrap upper bounds are below 0, the semantic audit passes (fewer than 50% of the flagged oracle errors are depth-ambiguity cases and fewer than 50% are near-recording-end cases), and the worst max-depth domain-transfer balanced accuracy is >= 0.60. BINARY PRIMARY iff binary is better on q20 and q30 with both lower bounds above 0, or the semantic audit fails. Otherwise HYBRID / NO CLEAR WINNER (observed; `phase6_final_decision.csv`).

Phase 7 (`choose_hybrid_candidate`, `evaluate_preregistered_decision`)
: the same 20 runs replayed from CSV. Methods M0 `shared_random_binary_head`, M1 `binary_uncertainty_repulsion`, M2 `max_depth_straddle`, M3 `hybrid_binary_gate20_max_depth_straddle` (top `ceil(0.20 n)` candidates by Phase 6 binary priority, then the max-depth straddle argmax; `GATE_FRACTION = 0.20`), M4 `hybrid_equal_rank_fusion` (argmax of `0.5 * rank_binary + 0.5 * rank_straddle`). Boundaries B1 / B2 / B3 (section D), quantiles 20 and 30; `stable_seed = p6.stable_seed('phase7', *parts)`; 5000-resample paired bootstrap. Preregistered rule `phase7_preregistered_decision_rule.json`, sha256 `a3581cb61c4b2f95aa71838fc9c199ca8f992fef7de67104970767db0af9643f`: a hybrid succeeds iff A (q20 error AULC below M1 under at least 2 of B1/B2/B3, with bootstrap upper bound < 0 under at least 2), B (q30 below M1 under at least 2), C (balanced-accuracy AULC >= M1 - 0.01), D (q20 below M0 under at least 2, with at least 1 upper bound < 0). Tree: HYBRID ACQUISITION PRIMARY, else MAX-DEPTH FORMULATION PRIMARY, else BINARY ACQUISITION PRIMARY, else NO ROBUST WINNER / METRIC-DEPENDENT. Observed: BINARY ACQUISITION PRIMARY (`phase7_final_decision.csv`).

## C. Week 9 conventions on top of A

- Same 100 `SplitSpec`s, initial designs and B1 flags, imported from `w85`; population via `w85.load_population`.
- A0 path = the frozen `binary_margin` query sequence: `queried_indices[:80]` of `checkpoints/w85__rRR_fFF__binary_margin__c01.json` inside `outputs/week8_5_frozen_confirmation/week8_5_checkpoint_bundle.tar.gz`, tabulated in `outputs/week9_phase1_8_model_path_decomposition/tables/query_paths.csv.gz` (`week9_phase1_8::load_query_paths`; lean `alse.protocol.load_a0_paths`).
- P1 path = the M3-margin sequential path, `outputs/week9_phase1_14_m3_margin_acquisition/m3_margin_paths.csv.gz` (lean `load_p1_paths`).
- Replay: at each budget B in 16..80 fit on `path[:B]`, predict the 81 test rows, score the subsets `full81`, `B1_q30`, `B1_q20` (`week9_phase1_7::subset_flags`). Physics-mean fits are seeded by `p13.seed_u32('shared_physics', run_id, budget)`.
- AULC regions of the q20 accuracy curve: `EARLY_B16_40` = 16..40 and `LATE_B41_80` = 41..80 (Phases 1.13, 1.14); Phase 1.18B: `EARLY_B16_24`, `MID_B25_40`, `LATE_B41_80`, `BROAD_B16_40` (`week9_phase1_18b_finalize`).
- Repeat-block bootstrap (`bootstrap_interval`): the 20 repeat means resampled with replacement, `rng = default_rng(seed_u32('bootstrap', key))` under the module `SEED_ROOT` (section E), quantiles 0.025 and 0.975. `BOOTSTRAP_DRAWS`: 5000 (Phases 1.5, 1.7), 10 000 (1.8, 1.9, 1.11, 1.12, 1.13, 1.14, 1.15A, 1.16, 1.17A, 1.18A), 20 000 (1.18B). Phase 1.13 ratio intervals use `seed_u32('bootstrap-ratio', key)`.
- Holm: `week9_phase1_16::holm_summary` over the five repulsion scales against M3-margin (raw two-sided sign-test p); `week9_phase1_18b_finalize` over the family {P1-P0, P2-P0}.
- H = 320 continuation: budgets 164..320 step 4 (`week9_phase1_horizon_extension`), horizons (80, 120, 160, 200, 240, 280, 320), 20 000-draw hierarchical bootstrap seeded by `w85.seed_u32('week9_phase1|posthoc_h320|hierarchical_bootstrap|v1')` (`week9_phase1_close_week8`).

## D. Boundary definitions

Computed once on all 405 rows after `StandardScaler` on P, VX, LS, ST; evaluation-only, never visible to acquisition (`week7_phase7::build_boundary_metrics`, `week7_phase6::build_empirical_boundary_reference`, `week8_5::b1_distance`).

| Id | Definition | Near-boundary order |
|---|---|---|
| B1 | Euclidean distance to the nearest row with the opposite label | ascending |
| B2 | fraction of the k = 5 nearest neighbours (self excluded) with a different label; k = 10 secondary | descending |
| B3 | `d_opp / max(d_opp + d_same, 1e-15)`, `d_same` = nearest same-label distance | ascending |

Ties are broken by `experiment_name` (`deterministic_order = np.lexsort((names, values))`). Phase 6 `empirical_boundary_distance` equals B1. Global subsets on 405 rows: q10 / q20 / q30 = `ceil(q / 100 * 405)` = 41 / 81 / 122 rows. Test-fold subsets on 81 rows: 9 / 17 / 25. Week 8.5 and Week 9 use B1 only: `B1_q20` = 17 rows and `B1_q30` = 25 rows per fold.

## E. Seed derivation families and RNG salts

`seed_key` / `seed_u32`
: key = ROOT and parts joined by `|`; `int.from_bytes(sha256(key.encode('utf-8')).digest()[:8], 'little') % 2**32`. `week8_5` builds the key with `seed_key`; every Week 9 module defines `seed_u32(*parts)` that prepends its own ROOT. Lean `alse.io.seed_key`, `seed_u32`, `alse.protocol.SEED_ROOTS`.

`stable_seed` / `stable_rng`
: `int.from_bytes(sha256(':'.join(parts))[:8], 'little') % 2**32`; `week7_phase6::stable_seed`; `week7_phase7::stable_seed = p6.stable_seed('phase7', *parts)`; identical bodies in `week4_07::stable_seed` and `week4_08::stable_seed`. Lean `alse.io.stable_seed`.

`deterministic_seed`
: `int.from_bytes(sha256('|'.join((BASE, *parts)))[:4], 'big')`, a module-local BASE: `week6_phase2` 6202, `week6_phase3` 6303, `week6_phase4` 6404, `week7_phase4` 7404, `week7_phase5` 7505, `week7_phase3` (regression and proxy bootstraps; not ported).

Frozen `SEED_ROOT` literals (`grep SEED_ROOT src/`), each `<module>|v1` unless stated:

- `week8_5_frozen_sample_efficiency_confirmation`: `week8_5_frozen_confirmation|v1`
- `week9_phase1_5_h_physics_confirmation|v1`, `week9_phase1_7_physics_ridge_residual_gp|v1`, `week9_phase1_8_model_path_decomposition|v1`, `week9_phase1_9_physics_specificity_control|v1`
- `week9_phase1_11_fixed_mean_discrepancy_gp|v1`, `week9_phase1_12_gpc_kernel_adequacy|v1`, `week9_phase1_13_fixed_physics_ard_discrepancy|v1`, `week9_phase1_14_m3_margin_acquisition|v1`
- `week9_phase1_15a_physics_residual_signal_audit|v1`, `week9_phase1_16_m3_repulsion_scale_audit|v1`, `week9_phase1_17a_physics_contour_geometry_audit|v1`
- `week9_phase1_18a_level_set_acquisition_compatibility_audit`: `week9_phase1_18a|frozen-prefix|v1`
- `week9_phase1_18b0_fast_gpc_sur_update_validation`: `week9_phase1_18b0|validation-gate|v1`
- `week9_phase1_18b_prospective_global_gpc_sur_benchmark|v1`
- `week9_phase1_horizon_extension` and `week9_phase1_close_week8` reuse `w85.seed_u32` with Week 8.5 keys, plus the H = 320 bootstrap key of section C.

RNG salts of the synthetic experiments. Every salt seeds `np.random.default_rng(int.from_bytes(sha256(text)[:8], 'little') % 2**32)`; `stable_seed(...)` produces the same text with `:` joins.

| Salt | Key text | Module |
|---|---|---|
| `week2` | `f"{seed}:{method}:week2"` | `acquisition_rules::rng_for_method` (Branin, S1; the original five rules on Branin everywhere) |
| `week3_4d` | `f"{seed}:{method}:week3_4d"` | `week3_4d_benchmark_comparison::rng_for_week3_method` (superseded custom 4D function) |
| `week3_4d_ackley` | `f"{seed}:{method}:week3_4d_ackley"` | `week3_4d_named_benchmark_comparison::rng_for_week3_named_method` (Ackley4, S2; the original five rules on Ackley everywhere) |
| `week5` | `f"{seed}:{benchmark}:{method}:week5"` | `week4_02..05::rng_for_experiment_method`, new heuristics only; original rules route to the `week2` or `week3_4d_ackley` RNG |
| `week6_classifier` | `f"{seed}:{benchmark}:{method}:week6_classifier"` | `week4_06::rng_for_experiment_method` (fixed-kernel GPC rules, S5) |
| `week6_1_classifier` | `stable_seed(seed, benchmark, method, 'week6_1_classifier')` | `week4_07::rng_for_method` (optimised-kernel diagnostic) |
| `week7` | `stable_seed(seed, benchmark, method, 'week7')` | `week4_08::rng_for_method`, non-original methods (Hartmann4, IVR, SUR) |
| `week7_1` | `stable_seed(seed, benchmark, method, 'week7_1')` | `week4_09::stable_rng` (GPC Bernoulli SUR validation, S6, claim C10) |

Renaming any salt or root changes every stored trajectory and interval; keep the literals in `alse` constant tables and mark them as seed namespaces.
