# Architecture and porting contract

This document is the contract for porting the archived ChatGPT/Codex code
(`../thesis_work_chatgpt`, ~90k lines, 55 monolithic scripts) into the lean
`alse` package. Each module below lists its public API and the archive symbols
it is ported from (`file::symbol`, paths relative to the archive's `src/`).

## Layout

```
thesis/
  alse/
    config.py        paths (done)
    io.py            require, seeds (seed_key/seed_u32/stable_seed), json/csv/checkpoint io, hashing (done)
    benchmarks.py    synthetic oracles, thresholds, datasets, seed designs
    surrogates.py    GPR stand-in, fixed synthetic GPC, real-data GPR/GPC (Phase 6), GPC kernel family G0-G4
    physics.py       h coordinate, physics logistic mean, FixedMeanLaplaceGPC
    hybrid_gpc.py    M2W/M3 fixed-mean + residual GPC, trend+residual additive GPC (Phase 1.7/1.9)
    acquisition.py   GPR rules, Week-4 heuristics, classifier rules, continuous rules, hybrid rules, M3 margin, repulsion scale
    sur.py           Bernoulli SUR (synthetic), exact finite-pool GPC-SUR (Phase 1.18B), Laplace-GPC utilities (1.18A)
    metrics.py       boundary masks, B1/B2/B3, classification/regression metrics, AULC, persistent crossing
    protocol.py      Phase 6 splits/warm start; Week 8.5 frozen protocol (SplitSpec, build_splits, initial_design, seeds); path loaders; sequential runner
    data.py          dataset pins, population loading, input-tuple hash, ledger/registry download
    stats.py         hierarchical bootstrap, repeat-block bootstrap, run-level paired bootstrap, Holm
  experiments/       thin scripts (see docs/experiments.md)
  tests/             test_<module>.py + test_reproduction.py
```

## Porting rules (apply everywhere)

1. **Frozen behaviour is ported exactly.** Seed key strings and derivations,
   kernel definitions and bounds, optimizer settings, fallback chains,
   tie-break orders, normalisation conventions (shortlist vs pool), sample
   sizes, percentiles and seeds of thresholds. Mark each such function with a
   comment `# frozen: <archive file>::<symbol>` and cover it with a test that
   compares against the archive function (fixture `archive_src`) and/or a
   frozen artifact under `ARCHIVE_OUTPUTS` (`@pytest.mark.archive`).
2. **Drop scaffolding.** No git/branch/SHA assertions, no live Hugging Face
   revision checks, no output manifests, no source-file hashing, no notebook
   builders, no validators, no `historical_changes`, no absolute machine
   paths, no per-phase markdown/report writers, no figure suites.
3. **No import-time side effects.** Do not read outputs, set environment
   variables or mutate other modules' globals at import.
4. **Paths only via `alse.config`.** Archive artifacts via `ARCHIVE_OUTPUTS`.
5. **Names are semantic**, not chronological: `uncertainty_repulsion`, not
   `week6_classifier`. Where a legacy string is itself a seed component (RNG
   salts such as `'week2'`, `'week6_classifier'`, seed roots such as
   `'week8_5_frozen_confirmation|v1'`) keep the literal in a constants table
   with a comment saying it is a seed namespace.
6. **Size budget.** A module is at most ~600 lines (`hybrid_gpc.py`,
   `acquisition.py` at most ~800). Docstrings state the formula and origin in
   a few lines. Type hints on public functions.
7. **Tests** live in `tests/test_<module>.py`, pytest style, fast by default.
   Archive comparisons use the `archive_src` fixture (adds the archive root to
   `sys.path`, then `import src.<module>`); only import archive modules that
   are side-effect free at import: `acquisition_rules`, `branin_week1`,
   `week2_acquisition_comparison`, `week3_4d_named_benchmark_comparison`,
   `week4_01_boundary_metrics`, `week4_06_gp_classifier_surrogate`,
   `week4_08_boundary_weighted_sur`, `week4_09_gpc_bernoulli_sur_validation`,
   `week7_sph_v2_common`, `week7_phase6_real_data_boundary_active_level_set`,
   `week7_phase7_final_boundary_hybrid_benchmark`,
   `week8_5_frozen_sample_efficiency_confirmation`, and the Week 9
   `week9_phase1_*` modules. Never import `week6_phase2*`, `week6_phase4*`,
   `week7_phase3*`, `week7_phase4*`.
8. **Environment.** Python 3.14, numpy 2.5.1, scipy 1.18.0, scikit-learn
   1.9.0 (the versions that produced the frozen numbers). pandas is 3.0.5
   here but the archive ran 2.3.3: avoid pandas behaviour that changed in 3.0
   (string dtype, copy-on-write); prefer numpy arrays inside algorithms.

## Module contracts

### benchmarks.py
Ported from `branin_week1.py`, `week3_4d_named_benchmark_comparison.py`,
`week4_08_boundary_weighted_sur.py` (Hartmann4), `week2_acquisition_comparison.py::create_seed_design`,
`week3_4d_named_benchmark_comparison.py::create_seed_design`,
`week4_08_boundary_weighted_sur.py::create_hartmann_seed_design`, and the
archived `week3_4d_benchmark_comparison.py::controlled_4d_function` (definition only).

```python
def branin(X) -> np.ndarray; def ackley4(X) -> np.ndarray; def hartmann4(X) -> np.ndarray; def controlled_4d(X) -> np.ndarray
def scale_to_unit(X, lower, upper) -> np.ndarray; def unscale_from_unit(U, lower, upper) -> np.ndarray
@dataclass(frozen=True) class Benchmark: name, fn, lower, upper, threshold_percentile, threshold_sample_size, threshold_seed, pool_size, test_size, init_size, budget, seed_offset, rng_salt
BENCHMARKS: dict[str, Benchmark]   # 'branin' (S1 settings), 'ackley4' (S2), 'hartmann4' (Exp 08/09)
def compute_threshold(benchmark) -> float   # exact: branin 29.121261109594627; ackley4 10.3322025066197; hartmann4 -0.97797833 (verify digits in archive)
def labels_from_threshold(values, threshold) -> np.ndarray   # {-1,+1}
@dataclass class Dataset: pool, pool_scaled, pool_values, pool_labels, test, test_scaled, test_values, test_labels, threshold, seed
def make_dataset(benchmark, seed) -> Dataset   # exact reproduction of the archive's make_dataset per benchmark (pool then test from default_rng(seed))
def initial_design(benchmark, dataset, seed) -> np.ndarray   # exact: create_seed_design variants (rng seed+100_000 init 6 / seed+300_000 init 12 / seed+700_000 ...)
def random_two_class_initial_design(rng, labels, size) -> tuple[np.ndarray, int]   # branin_week1
def make_plot_grid(...)  # optional, small
```
Tests: thresholds exact to 1e-12 vs archive functions; `make_dataset`/`initial_design` arrays equal to the archive for seeds 0-1.

### surrogates.py
```python
# synthetic GPR stand-in — branin_week1::make_gp, fit_gp  (C(1,(0.1,10))*RBF(0.20,(0.08,1))+White(1e-4 fixed), alpha 1e-6, normalize_y False, 0 restarts, random_state=seed)
def make_gpr_standin(seed) -> GaussianProcessRegressor; def fit_gpr_standin(X, y, seed) -> GaussianProcessRegressor
# fixed synthetic GPC — week4_06::make_gp_classifier, fit_classifier, predict_p_plus  (C(1.0,fixed)*RBF(0.25,fixed), optimizer None, max_iter_predict 100); optional variant kernels from week4_07::make_base_kernel
def make_fixed_gpc(variant='fixed') -> GaussianProcessClassifier; def fit_fixed_gpc(X, y, variant='fixed'); def predict_p_plus(model, X) -> np.ndarray
# real-data (Phase 6) — week7_phase6::FitResult, make_signal_kernel, extract_kernel_diagnostics, fit_gpr, predict_gpr, fit_gpc, predict_gpc, continuous_probability, KERNEL_CONSTANT_BOUNDS (1e-3,1e3), KERNEL_LENGTH_BOUNDS (1e-2,1e2), GPR_ALPHA_PRIMARY 1e-8, GPR_ALPHA_RETRY 1e-6, ACTIVE_OPTIMIZER_RESTARTS 0. Keep the fallback chain (retry alpha; fixed kernel; LogisticRegression C=1.0) byte-identical, including the diagnostics fields callers read.
@dataclass class FitResult ...
def make_signal_kernel(kind='matern32'); def fit_gpr(x, y, seed, *, ...) -> FitResult; def predict_gpr(fit, x); def fit_gpc(x, y, seed, *, ...) -> FitResult; def predict_gpc(fit, x); def continuous_probability(mu, sigma, threshold)
# standalone GPC kernel family — week9_phase1_12::MODEL_SPECS, make_kernel, fit_gpc_model, predict_positive (G0 iso Matern32 == Phase 6 kernel, G1 iso RBF, G2 ARD RBF, G3 ARD Matern32, G4 iso Matern52; bounds (0.001,1000)/(0.01,100))
GPC_KERNELS: dict[str, ...]; def make_gpc_kernel(name); def fit_gpc_kernel(name, x, y, seed) -> FitResult
```
Tests: predictions equal (1e-12) to archive `p6.fit_gpc/predict_gpc` and `fit_gpr/predict_gpr` on a fixed 60-row subset of the population for seeds 0-1; `make_fixed_gpc` predictions equal to `week4_06` on a Branin dataset.

### physics.py
```python
def log_h(P, VX, LS) -> np.ndarray   # week9_phase1_7::log_h  (log(P/sqrt(VX*LS^3)), positivity check); LS = spot radius [m]; units W s^1/2 m^-2
def h_coordinates(frame) -> pd.DataFrame   # week9_phase1_5::h_coordinates (h_SI, log_h, h/(TI64_LIQUIDUS_K-ST)); TI64_LIQUIDUS_K = 1933.0
def physical_scores(frame) -> pd.DataFrame  # week9_phase1_discriminative_update::physical_scores (six fixed-form scores) — optional if small
@dataclass class PhysicsMeanFit; def fit_physics_mean(logh, labels, revealed) -> PhysicsMeanFit   # week9_phase1_11::fit_physics_mean (StandardScaler on log h, LogisticRegression C=1e6)
class FixedMeanLaplaceGPC   # week9_phase1_11::FixedMeanLaplaceGPC verbatim (Laplace with fixed prior mean; WB_COEFS/WB_LAMBDAS; EPS; diagnostics); plus LaplaceDiagnostics
```
Tests: `run_parity_gate` from `week9_phase1_11` re-expressed as a test (fixed-mean GPC with zero mean equals sklearn GPC probabilities); log_h equals archive on the population.

### hybrid_gpc.py
```python
# week9_phase1_13::residual_kernel(model, upper), HybridFit, fit_hybrid, components, fit_diagnostic, RESIDUAL_SD_BOUNDS (0.05,1.0), INITIAL_RESIDUAL_VARIANCE 0.09, PRIMARY_LENGTH_BOUNDS (0.01,100), BOUND_ATOL 5e-4  (M2W scalar length / M3 ARD ones(4))
def residual_kernel(model: str, upper: float = 100.0); def fit_hybrid(...) -> HybridFit; def components(...); def fit_diagnostic(...)
# week9_phase1_7::PhysicsRidgeResidualKernel, AdditiveFit, transform_additive_inputs, fit_additive, additive_components, matern32, PHYSICS_PRIOR_VARIANCE 25.0, MATERN_LENGTH_SCALE 1.5, RESIDUAL_SD_BOUNDS (0.05,1.0), LENGTH_SCALE_BOUNDS (0.25,4.0); week9_phase1_9::GenericTrendResidualKernel, fit_generic  → one TrendResidualKernel parametrised by the trend design matrix (1 column physics / 4 columns generic); week9_phase1_8::fit_additive_with_bound (different residual-SD cap) as a parameter
class TrendResidualKernel; def fit_additive(...) -> AdditiveFit; def additive_components(...)
```
Tests: M3 parity case from `week9_phase1_13` (`fixed_ard_parity_case` / `ard_parity_report.json`); `fit_additive` predictions equal to archive `p17.fit_additive` on a 60-row subset.

### acquisition.py
```python
# GPR pool rules — acquisition_rules.py (canonical): METHOD_ORDER, METHOD_DESCRIPTIONS, AcquisitionChoice, rng_for_method(seed, method, salt) [salts table: 'week2','week3_4d','week3_4d_ackley','week5','week6_classifier','week7','week7_1' — seed namespaces], smallest_abs_mu_scores, straddle_scores (1.96 sigma - |mu|), randomized_straddle_scores (sqrt(chi2_2) sigma - |mu|), expected_feasibility_scores (24-node Gauss-Hermite, eps 1.96 sigma, sigma floor 1e-12), choose_next_index
# Week-4 heuristics (definitions kept): week4_02::normalize_scores, choose_diversified_straddle (alpha 0.25); week4_03::choose_boundary_gated_diversified_straddle (gate 0.10, min 25, beta 0.50); week4_04::choose_lookahead_boundary_uncertainty_reduction (+ fit_fantasy_gp, boundary_uncertainty_values, shortlist 30). Drop week4_05 GBC and week4_08's re-implementation.
# classifier rules — week4_06::classifier_uncertainty_score (1-2|p-0.5|), binary_entropy, shortlist_by_uncertainty (0.10 / 25), nearest_labelled_distance, choose_classifier_candidate (margin, entropy, gated_diversity beta 0.50, uncertainty_repulsion bandwidth 0.15; SHORTLIST-normalised); week4_08/09::classifier_repulsion_scores (POOL-normalised variant used by the C10 numbers) — keep both as `uncertainty_repulsion_scores(..., normalise='shortlist'|'pool')`
# real-data rules — week7_phase6::choose_binary_candidate (canonical thesis rule: margin / uncertainty_repulsion with CLASSIFIER_GATE_FRACTION 0.10, CLASSIFIER_MIN_SHORTLIST_SIZE 25, CLASSIFIER_REPULSION_BANDWIDTH 0.15, standardized distance, minmax over shortlist, tie by lowest row index), choose_continuous_candidate (boundary_proximity, straddle STRADDLE_KAPPA 1.96 with online tau, randomized_straddle, expected_feasibility), normalize_scores, deterministic_argmax
# hybrids — week7_phase7::phase6_binary_priority, deterministic_percentile_rank, max_depth_straddle_scores, choose_hybrid_candidate (GATE_FRACTION 0.20; RANK weights 0.5/0.5)
# Week 9 — week9_phase1_5::choose_gpc_margin, choose_h_margin, choose_assisted_product; week9_phase1_14::choose_m3_margin (lexsort((idx, -u))[0]); week9_phase1_16::choose_repulsion (lambda_B = c * median d_min)
def argmax_position(scores) -> int      # returns position (week4_06/p6 deterministic_argmax)
def argmax_index(candidates, scores) -> int   # returns candidate value (week9_phase1_5 deterministic_argmax)
```
Tests: every rule equals the archive function on random inputs (indices exact, scores allclose 1e-12), including the shortlist/pool normalisation split and the online-tau straddle.

### sur.py
```python
# week4_09::choose_gpc_bernoulli_sur, reference_positions, bernoulli_uncertainty_from_p (C10 needs these); week4_08::posterior_covariance, gpr_p_plus (GPR-side IVR kept only if short)
# week9_phase1_18a::expected_logistic_curvature (24-node GH), logistic_gaussian_probability (Williams-Barber), posterior_covariance (from FixedMeanLaplaceGPC L_, W_sr_), emi_score
# week9_phase1_18b::hypothetical_update, score_candidates (exact-fixed and physics-refit finite-pool SUR; U = mean p(1-p) over unqueried pool; near-tie tol max(1e-14, 1e-6*scale); tie-break max score then smallest row index); week9_phase1_18b0::exact_update levels
```
Tests: equality with archive functions on small synthetic problems.

### metrics.py
```python
BOUNDARY_QUANTILES = (10, 20, 30); UNCERTAINTY_MULTIPLIER = 1.96
def boundary_masks(values, threshold) -> dict[int, np.ndarray]                        # week4_01
def evaluate_budget(..., surrogate='gpr'|'gpc') -> dict                              # week4_01 / week4_06 / week4_08 branches
def build_empirical_boundary_reference(population) -> ...                            # week7_phase6 (B1 = nearest opposite-label standardized distance; q10/20/30)
def boundary_metrics(population) -> pd.DataFrame                                     # week7_phase7::build_boundary_metrics (B1, B2 k=5, B3), class_distance_components, rank_fraction, robust_scaled
def deterministic_order(...)                                                         # week7_phase7::deterministic_order
def b1_distance(population) -> np.ndarray; def boundary_flags(spec, population, distances) -> dict[str, np.ndarray]   # week8_5 (B1_q20 = ceil(0.2*81)=17, B1_q30 = 25)
def subset_flags(...)                                                                # week9_phase1_7::subset_flags ({full81, B1_q30, B1_q20})
def classification_metrics(labels, probability, ...) -> dict; def regression_metrics(labels, predictions) -> dict   # week7_phase6
def compute_metrics(labels, probability, flag) -> dict                               # week8_5 (accuracy, recall, balanced_accuracy, FN/FP/TN/TP; p>=0.5)
def aulc(budgets, values, start=16, end=80) -> float                                  # week8_5::aulc (np.trapezoid over the complete integer grid / (end-start))
def persistent_crossing(budgets, values, target, consecutive=3) -> tuple[float, bool] # week8_5::persistent_crossing (NaN = right-censored)
AULC_REGIONS = {...}   # EARLY_B16_40/LATE_B41_80 (1.13/1.14) and EARLY 16-24 / MID 25-40 / LATE 41-80 / BROAD 16-40 (1.18B)
```
Tests: B1 distances and q20/q30 flags equal to archive `w85.b1_distance/boundary_flags` for all 100 SplitSpecs; `aulc` of the archived margin trajectories reproduces 0.8135202205882353 (tolerance 1e-9) from `ARCHIVE_OUTPUTS/week8_5_frozen_confirmation/repeat_level_metrics.csv` or `run_level_metrics.csv` (inspect which holds per-budget values; `checkpoint_metrics.csv` has them).

### protocol.py
```python
FEATURES = ("P", "VX", "LS", "ST")
# Phase 6/7 — week7_phase6::RunSpec, BASE_SEED 6022026, N_SPLITS 5, N_REPEATS 4, build_outer_splits (StratifiedGroupKFold(5, shuffle=True, random_state=stable_seed(BASE_SEED, population_name, repeat)) grouped by input_tuple_sha256; run_id '<pop>__rNN_fNN'), warm_start_indices (shared permutation stable_rng(BASE_SEED, run_id, 'shared_pool_permutation'); reveal >= 12 until both classes; cap), NOMINAL_WARM_START 12, MAX_WARM_START 80, FINAL_BUDGET 80, PRESENTATION_CHECKPOINTS
# Week 8.5 — week8_5::SplitSpec, SEED_ROOT 'week8_5_frozen_confirmation|v1', PROTOCOL_ID, ARMS, TARGETS, declared_budgets(horizon), build_splits(population, repeats=20, folds=5) (StratifiedGroupKFold, random_state=seed_u32(seed_key(ROOT,'outer_split','repeat',NN)); run_id 'w85__rRR_fFF'), initial_design(spec, population) (StandardScaler on training pool; first point uniform; greedy maximin to 16; ties -> smallest population index; both classes required), fit_seed_key, random_order_key, trajectory_identity
SEED_ROOTS = {...}   # every Week 9 SEED_ROOT literal (p17 'week9_phase1_7_physics_ridge_residual_gp|v1', p11, p13, p14, p16, p18a, p18b, ...) copied verbatim
# path loaders over archive artifacts: load_a0_paths() (week9_phase1_8 tables/query_paths.csv.gz → dict run_id -> list[int] of 80 indices), load_p1_paths() (week9_phase1_14 m3_margin_paths.csv.gz), load_frozen_specs() (rebuild the 100 SplitSpecs and verify against week8_5 grouped_split_manifest.csv)
def sequential_runner(spec, population, initial, budget, fit_fn, choose_fn, evaluate_fn, *, checkpoint=None) -> pd.DataFrame   # generic loop that replaces the six copies of run_one_spec/run_trajectory; must be able to reproduce week8_5::run_trajectory for binary_margin exactly (same fit seed keys per budget)
```
Tests (`@archive`): `build_outer_splits` == `ARCHIVE_OUTPUTS/week7_06_.../outer_split_manifest.csv`; `build_splits` == `week8_5_frozen_confirmation/grouped_split_manifest.csv` (or split_manifest.csv); `initial_design` == `initial_design_manifest.csv` for all 100 runs; `warm_start_indices` == `week7_06/active_initialization_audit.csv`.

### data.py
```python
SPH_DATASET_REPO = "ioandanielc/sph_dataset"; SPH_DATASET_REVISION = "0e859b748fdbc8454f66e58e101e333ac0479d42"
SPH_V2_REPO = "ioandanielc/sph_v2"; SPH_V2_REVISION_AUDIT = "d69dac5bda8b622bc0de316b112815c6056c06ec"; SPH_V2_REVISION = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
FEATURE_UNITS = {"P": "W", "VX": "m/s", "LS": "m", "ST": "K"}; PARTITIONS / LABEL_FILES; PHYSICAL_LABELS; TECHNICAL_LABELS
def load_population(path=POPULATION_CSV) -> pd.DataFrame   # asserts 405 rows / 73 has_keyhole / unique experiment_name; bool columns via strict_bool; keeps the frozen row order
def input_tuple_hash(frame) -> pd.Series                    # week7_phase6::input_tuple_hash (sha256 of '%.17g' P|VX|LS|ST)
def parse_experiment_name(name) -> dict; def decode_number(...)   # week7_sph_v2_common
def download_pinned_file(filename, revision=SPH_V2_REVISION, local_dir=DATA_DIR/'raw'/...) -> Path; def load_partition_labels(revision=...) -> pd.DataFrame   # week7_sph_v2_common (network)
def experiment_registry(labels) -> pd.DataFrame            # week7_phase1: per-experiment P/VX/LS/ST + has_keyhole = any(label_final=='Keyhole'), has_conduction, keyhole fraction, transient flag
# Target extraction (T0 window, max depth, G3/R3) is NOT ported: it lives in the archive (week7_phase2 + week6_phase1/phase3_5) and its output is frozen in data/population.csv. Document the rules in docs/data.md.
```
Tests: population checks; `input_tuple_hash` equals the stored `input_tuple_sha256` column for all rows; `parse_experiment_name` round-trips the stored P/VX/LS/ST for all rows.

### stats.py
```python
def hierarchical_bootstrap(run_metrics, draws=20000, seed_key=...) -> ...   # week8_5::hierarchical_bootstrap (resample 20 repeats, keep folds, resample 30 continuations), point_estimands, random_finite_fraction, aggregate_repeat_metrics
def repeat_block_bootstrap(values, key, root, draws=10000) -> (mean, lo, hi)  # week9_phase1_11/13::bootstrap_interval — seed_u32(seed_key(root, 'bootstrap', key)); roots from protocol.SEED_ROOTS
def bootstrap_repeat_ratio(...)                                            # week9_phase1_13
def paired_run_bootstrap(differences, resamples=5000, seed=...) -> ...      # week7_phase6::paired_comparisons core
def holm(pvalues) -> np.ndarray                                             # week9_phase1_16::holm_summary core
def decision_ledger(...)   # week8_5::decision_ledger rules (PASS iff lower >= 0.020; query_saving PASS iff rho >= 0.95 and lower >= 10; multiplier lower >= 1.25; repulsion lower(min) >= 0.010)
```
Tests: `repeat_block_bootstrap` reproduces an archived interval exactly (e.g. Phase 1.13 `paired_contrasts.csv` M3-H [+0.007201, +0.016149] from `model_summary`/repeat metrics with root `week9_phase1_13_...|v1`); `hierarchical_bootstrap` reproduces `week8_5_frozen_confirmation/bootstrap_or_hierarchical_ci.csv` performance interval [0.030132, 0.044416] from `run_level_metrics.csv` (tolerance 1e-9 if seeds are identical; otherwise document).

## Experiments (thin scripts; written after the library)
- `synthetic_gpr.py` — S1/S2/S3: Branin and Ackley4, five GPR rules, boundary metrics, `--benchmark --seeds --budget --smoke`.
- `synthetic_gpc.py` — S5/S6: fixed GPC rules (random, margin, entropy, uncertainty_repulsion shortlist/pool, Bernoulli SUR k15/k25) on Branin/Ackley4/Hartmann4.
- `real_benchmark.py` — R1/R2 core: Phase 6 protocol on `data/population.csv` (static folds; active arms binary_random/margin/uncertainty_repulsion and max_depth_straddle; optional hybrids), `--smoke`, `--workers`.
- `frozen_protocol.py` — R3: Week 8.5 protocol (prepare splits/designs, run arms with gzip checkpoints, finalize AULC/crossings/hierarchical bootstrap/decision ledger), `--smoke`, `--horizon`, `--workers`; full run documented as ~2.6 h and NOT required.
- `physics_surrogates.py` — P5/P6: replay M0 (Phase 6 GPC), H (h-only logistic), M2W and M3 on the frozen A0 path; M3-margin sequential run; `--limit-specs`.
- `curate_results.py` — copy the curated shortlist from the archive into `results/` with a size cap and a manifest.
- `summarize_results.py` — regenerate the headline tables from `results/`.

## Reproduction gates (tests/test_reproduction.py)
G0 margin q20 AULC 16-80 = 0.8135202205882353; Random 0.7762204350; M3 on A0 = 0.8424908088235293; P1 (M3-margin) = 0.844623161764706; Phase 7 decision 'BINARY ACQUISITION PRIMARY'; Branin S1 final mean errors 0.1194/0.0659/0.0620/0.0602/0.066350 (slow, opt-in).
