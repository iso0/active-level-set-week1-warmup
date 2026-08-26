# Week 8.5 frozen sample-efficiency confirmation: evidence map

Scope: one authoritative audit of the already-frozen Week 6/7/8 artifacts; no experiment, split, model, acquisition, label, or target reconstruction.

## Provenance and frozen population

- Audit checkout: branch `codex/week8-5-frozen-sample-efficiency-confirmation`, `HEAD=401b51c3da96897995d2156cde92604231ba9b4a` (Week 8 final consolidation commit).
- Frozen Week 8 source parent / Phase 7 ancestor: `167aad945b20822de712e891e901bd3ec6d5ffc6`; Phase 6 commit `5734de6f533e1de1e15a07de24e7d4e6e53bb6fa`; Phase 6 parent `6cc2ea150b9deb6ec9dd529d94ac55cc86556cfb`; sph_v2 revision `b6dc254a2b607a31cb9f97b40990339c3d5ca1e8`.
- Population code: `src/week7_phase6_real_data_boundary_active_level_set.py:321-406`, `load_population_tables()`. It reads Phase 5.5 `current_revision_simulation_level_targets.parquet` plus `physical_proxy_population_reference.csv`, constructs `primary_ready`, and fail-closes at 405 rows, 73 `has_keyhole=True`, 332 false. Features are `(P,VX,LS,ST)`; `ST` is substrate temperature. Authoritative CSV: `outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv` (SHA-256 `c15658cac87a8616a1984185ec1afc8126a1db811f0d5819e62cfb621a7486c7`).
- Manual `has_keyhole` remains ground truth; maximum depth is `max(0,-z_min)` side information, not a replacement label. Week 8 source doc explicitly performs no new run/fit/search/split/label construction (`src/week8_final_sample_efficiency_thesis_consolidation.py:1-17`).

## Outer repeats, grouped splits, and seeds

- Frozen constants and seed generator: `src/week7_phase6_real_data_boundary_active_level_set.py:96-112,212-218` (`BASE_SEED=6022026`, `N_SPLITS=5`, `N_REPEATS=4`, nominal warm start 12, final budget 80; SHA-256-derived `stable_seed`).
- Split function: `build_outer_splits()` at `src/week7_phase6_real_data_boundary_active_level_set.py:512-568`. It uses `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=stable_seed(BASE_SEED,"primary_common",repeat))`; groups are exact `input_tuple_sha256` values, and train/test group overlap is explicitly rejected. Primary run IDs are `primary_common__r01..r04_f01..f05`; each is 324 training-pool / 81 untouched-test rows.
- Exact split random states (repeat loop index 0..3): **272181870, 4075310866, 826906454, 2248840826**. Run seed rule is `stable_seed(BASE_SEED, run_id)` (all 20 run IDs are retained in `outer_split_manifest.csv` and the reuse audit; no alternate seed set is introduced).
- Authoritative split manifest: `outputs/week7_06_real_data_boundary_active_level_set/outer_split_manifest.csv` (SHA-256 `637badaee28d3cd4ebe13851b686ec9266327cad25d1e76460d5e75ce47af73d`). Phase 7/Week 8 reuse audit: `outputs/week7_07_final_boundary_hybrid_benchmark/phase6_run_reuse_audit.csv` (SHA-256 `c89b0f9f2516050c692e094c66c13dc9b9b25e663ebea62b782ea6c6f517705b`), 20/20 PASS for split and warm hashes.

## Warm start and matched-run feasibility

- `warm_start_indices()` at `src/week7_phase6_real_data_boundary_active_level_set.py:1427-1441` creates one deterministic permutation per `(BASE_SEED, run_id, "shared_pool_permutation")`, takes at least 12 rows, and stops only after both revealed manual classes occur. It does not use hidden labels to skip candidates. This is an initial queried design, not model-parameter warm-start; `fit_gpc()` refits at each budget.
- Reused effective warm starts are 19 runs at 12 and 1 run at 16; Week 8 deliberately compares the common integer grid 16–80 (`src/week8_final_sample_efficiency_thesis_consolidation.py:78-79,477-560`). The one 16-row run is therefore fully represented; the 12-row runs are evaluated from the common budget 16 onward.
- `phase6_run_reuse_audit.csv` records generated-vs-saved warm equality, warm hash equality, split hash equality, same population row order, and PASS status for all 20 runs. This establishes matched split/warm feasibility. Phase 7 baseline reconciliation is independently 80/80 PASS (`outputs/week7_07_final_boundary_hybrid_benchmark/validation_results.csv`, V14).

## Binary GPC and acquisition implementations

- Method inventory: `src/week7_phase6_real_data_boundary_active_level_set.py:133-167` includes `binary_random`, `binary_margin`, and `binary_uncertainty_repulsion` in the frozen primary method set.
- Binary model: `fit_gpc()` at `src/week7_phase6_real_data_boundary_active_level_set.py:791-870` uses `GaussianProcessClassifier` with the frozen Matern-3/2 signal kernel, zero optimizer restarts, `random_state=seed`, and fixed-kernel/logistic numerical fallbacks; `predict_gpc()` is at `:874-875`. Active fit seeds are `stable_seed(spec.run_seed, method, budget)` (`:1603`).
- `choose_binary_candidate()` at `src/week7_phase6_real_data_boundary_active_level_set.py:954-1003`: `binary_margin` selects deterministic maximum uncertainty `1-2|p-0.5|`; `binary_uncertainty_repulsion` selects from the top uncertainty shortlist (10% of pool, minimum 25), multiplying normalized uncertainty by distance repulsion with bandwidth 0.15. `binary_random` is not a score rule: `run_active_arm()` uses the predetermined permutation branch at `:1731-1738` and records `shared_predetermined_random_pool_order`.
- Phase 7 method mapping: `src/week7_phase7_final_boundary_hybrid_benchmark.py:89-112` maps `shared_random_binary_head -> binary_random`, `binary_uncertainty_repulsion -> binary_uncertainty_repulsion`, and `max_depth_straddle -> max_depth_straddle`. `run_method_arm()` at `:1033-1070,1282-1296` loads and replays saved Phase 6 trajectories for mapped methods; it does not redraw Random trajectories. Thus Week 8 `M_RANDOM=shared_random_binary_head` (`src/week8_final_sample_efficiency_thesis_consolidation.py:61-63`) is the authoritative saved random trajectory, while `M_BINARY=binary_uncertainty_repulsion` is the saved champion trajectory.

## Fold-level B1 q20/q30 and AULC

- Boundary definitions are evaluation-only. Phase 7 `build_boundary_metrics()` (`src/week7_phase7_final_boundary_hybrid_benchmark.py:472-565`) computes B1 nearest opposite-manual-label distance, B2 local disagreement, and B3 relative class-distance ratio; all definitions record `enters_acquisition=False`. `test_boundary_flags()` at `:665-686` ranks each untouched test fold independently and creates B1/B2/B3 q10/q20/q30 flags. For every 81-row primary test fold, B1-q20 has `ceil(.20*81)=17` rows and B1-q30 has `ceil(.30*81)=25` rows.
- Exact fold/budget/method values: `outputs/week8_01_final_sample_efficiency/boundary_accuracy_run_level.csv` (20 run IDs × repeats/folds × Binary/Random/Max-Depth × budget × B1/B2/B3 × q20/q30). Week 8 reconstruction is `compute_learning_curves()` at `src/week8_final_sample_efficiency_thesis_consolidation.py:477-560`; accuracy is exactly `1-error` and no test row enters acquisition.
- AULC is frozen in Phase 7 `summarize_learning()` at `src/week7_phase7_final_boundary_hybrid_benchmark.py:1727-1770`: trapezoid integration on every integer budget 16–80 divided by 64. Per-run source: `outputs/week7_07_final_boundary_hybrid_benchmark/phase7_aulc_summary.csv` (SHA-256 `e6edce57afb3546191a8e81d51191c3cf85142b8c0c45833e4caa3ee6f362021`). Week 8 aggregation is `normalized_aulc()` / `compute_real_scorecard()` at `src/week8_final_sample_efficiency_thesis_consolidation.py:1092-1217`.

## Information-flow constraints

- Query rows declare known inputs `P,VX,LS,ST`, reveal outcomes only after query, and set boundary-score, hidden-label, and hidden-response pre-selection flags false (`src/week7_phase7_final_boundary_hybrid_benchmark.py:948-992`; active arm logic `:1113-1247`).
- Candidate arrays are restricted to the outer training pool; untouched test rows are rejected; hidden pool labels/responses and evaluation B1/B2/B3 scores are never used by acquisition. Phase 7 validation V10, V15, V19–V21 and Week 8 validation P1V07, P1V11, P1V24 are PASS. Hybrid depth is queried-only auxiliary acquisition information; Hybrid primary predictions remain Binary GPC.
- Week 8 is strictly retrospective/offline: `outputs/week8_01_final_sample_efficiency/phase8_01_preflight.json` says `new_simulator_runs=false`, `new_splits=false`, `new_acquisition=false`, `new_model=false`, `offline_retrospective_benchmark=true`, `prospective_new_simulator_validation=false` (SHA-256 `2583ca03812ed4c5b7745c003bc3e51dbe01be46cc679c6892a544d411834d78`).

## Week 8 headlines (machine-readable authority)

`outputs/week8_01_final_sample_efficiency/headline_results.csv` (SHA-256 `bbf7455ffa7b7d576545b022954f5df7c339851f5df583683c22d83f2554f977`) and `headline_results.md` provide the claim ledger. Key values:

- At budget 40: Binary B1-q20 **81.2%** vs Random **76.8%** (+4.4 pp); B1-q30 **86.2%** vs **83.2%** (+3.0 pp).
- B1-q20 accuracy ≥80%: Binary **18/20**, median first crossing **16** queries; Random **14/20**, median **30** among successful runs.
- Binary B1-q20 mean: **79.7% at budget 30**, first matched by the observed Random mean near **70** queries: ~40 saved calls, **2.33×** equivalent. At budget 40, Random does not match by 80: strict **>40** saved and **>2.00×** lower-query-equivalent only.
- B1-q20 AULC: Binary **0.8138**, Random **0.7711**; B2/B3 q20 error-AULC reductions are **0.0549/0.0492**. At budget 30, mean Keyhole discovery is Binary **12.20** vs Random **5.45** (secondary diagnostic only).
- At budget 40, **48.2%** of pooled B1-q20 saved predictions have GPC confidence ≥80%; **93.3%** of that subset is correct. This is model confidence, not physical-boundary certainty.
- Final scorecard authority: `outputs/week8_02_thesis_consolidation/final_real_data_scorecard.csv` (SHA-256 `7915bd86a7fb488488295cdac14ddc3b469ae4ebcd6711f09d5118f110a6145f`).

## Caveats and runtime pointers

- The 20 runs are 4 repeated 5-fold partitions of the same 405 saved simulations, not 20 independent physical campaigns. B1/B2/B3 are sampled empirical boundary-like subsets; q20/q30 accuracy is not continuous physical-boundary certainty. Associations are not causal. Unsuccessful target crossings are censored at 80; Random-equivalent budgets use observed piecewise-linear interpolation only, never extrapolation (`src/week8_final_sample_efficiency_thesis_consolidation.py:638-718,832-904`).
- Runtime/dependency pointer: `outputs/week8_01_final_sample_efficiency/runtime_summary.json` records the established executable `C:\Users\ozgur\Documents\thesis-week5-first-conduction-gp\.venv\Scripts\python.exe`, saved-artifacts-only execution, 24/24 executed code cells, 0 stored errors, 28/28 requirements and 34/34 validation; Phase 7 runtime used the same scientific stack (NumPy, pandas, SciPy, scikit-learn, joblib, huggingface_hub) and 4 workers.
