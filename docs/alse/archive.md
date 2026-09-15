# Archive map

The archive is the original ChatGPT/Codex repository that this lean tree replaces. It is read-only. This page says where it is, how each archived script and result maps into `alse/`, `experiments/` and `results/`, which artifacts exist nowhere else, how its recorded hashes were computed, why its scripts cannot run outside their original worktree, and what state Phase 1.18B is in. Sources: the inventory and critique of the archive (2026-09-03) and the archive itself; every path below was checked with `ls`.

## 1. Location and git linkage

| Fact | Value |
|---|---|
| Path | `C:/Users/ozgur/OneDrive/Masaüstü/thesis_works/thesis_work_chatgpt` (default of `alse.config.ARCHIVE_ROOT`, override with `ALSE_ARCHIVE`) |
| Contents | `src/` (55 modules + `__init__.py`, 89 603 lines), `outputs/` (55 directories), `docs/`, `reports/`, `notebooks/`, `scripts/`, `tests/`, `week3_4d_benchmark_search/`, `README.md`, `requirements.txt` |
| Git identity | A file copy of a git worktree. Its `.git` file points to `C:/Users/ozgur/Documents/thesis/.git/worktrees/thesis-week9-phase1-18b-prospective-global-gpc-sur-benchmark`; the registered worktree path is `C:/Users/ozgur/Documents/thesis-week9-phase1-18b-prospective-global-gpc-sur-benchmark`, branch `codex/week9-phase1-18b-prospective-global-gpc-sur-benchmark` |
| HEAD | The inventory was taken at `1e34b47` (Validate FAST GPC-SUR posterior updates, 2026-09-03 14:29 +0200). The original worktree then committed `2552078` (Add prospective global GPC-SUR benchmark, 2026-09-03 20:32 +0200, 56 files, 14 307 insertions). The gitdir is shared, so `git rev-parse HEAD` inside the copy now also prints `2552078` |
| `git status --short` in the copy | 52 lines: 49 ` D` (files that commit `2552078` added under `outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark/` and `notebooks/week_09/18_*.ipynb`, absent from the copy) and 3 ` M` (`analysis_specification.json`, `execution_report.json`, `src/week9_phase1_18b_prospective_global_gpc_sur_benchmark.py`). The src diff is 9 lines: the committed engine wraps `read_checkpoint` in `try/except` for interrupted checkpoints; the copy's version does not |
| `git worktree list` | 34 entries, one branch per phase (`codex/week6-*`, `codex/week7-phase*`, `codex/week8-*`, `codex/week9-phase1-*`). 30 are `prunable` (directory deleted). Present: `C:/Users/ozgur/Documents/thesis` (`main`, `6fd6be5`), `thesis-week4-chronology-restructure` (`2042f02`), `thesis-week5-first-conduction-gp` (`1751286`), `thesis-week9-phase1-18b-prospective-global-gpc-sur-benchmark` (`2552078`) |

Read-only rules. Nothing in this tree writes to the archive; tests reach it through the `archive_root` and `archive_src` fixtures in `conftest.py`. Inside the copy, run only `git status`, `git log`, `git show`, `git diff`. Do not run `checkout`, `commit`, `stash`, `reset` or `worktree prune` there: they act on the gitdir shared with the original worktree.

## 2. Archive to lean mapping

| Archive (`src/` unless stated) | `alse` module | Experiment | Results / status |
|---|---|---|---|
| `make_moons_sanity_check.py`, `outputs/make_moons/` | none | none | archive-only (dead) |
| `branin_week1.py` | `benchmarks.py` (branin, threshold, dataset, two-class design), `surrogates.py` (GPR stand-in) | `synthetic_gpr.py` | `outputs/branin_week1/summary.json` |
| `acquisition_rules.py` | `acquisition.py` (five GPR rules, RNG salts) | `synthetic_gpr.py` | none |
| `week2_acquisition_comparison.py` | `benchmarks.py` (`create_seed_design`, seed+100_000) | `synthetic_gpr.py` (S1) | `outputs/week2_acquisition_comparison/{method_summary_table.csv,summary.json}` |
| `week3_4d_benchmark_comparison.py` | `benchmarks.py` (`controlled_4d` definition only) | none | archive-only (superseded by Ackley) |
| `week3_4d_named_benchmark_comparison.py` | `benchmarks.py` (ackley4, seed+300_000) | `synthetic_gpr.py` (S2) | `outputs/week3_4d_named_benchmark_comparison/{method_summary_table.csv,tolerance_reach_table.csv}` |
| `week4_01_boundary_metrics.py` | `metrics.py` (q10/q20/q30 masks, `evaluate_budget`) | `synthetic_gpr.py` (S3) | `outputs/week4_01_boundary_metrics/combined/boundary_metric_summary.csv` |
| `week4_02`, `week4_03`, `week4_04` | `acquisition.py` (heuristic definitions) | S4 optional | `*/final_metrics_table.csv` only; rest archive-only |
| `week4_05_gated_geometric_boundary_contraction.py` | none | none | archive-only (its `final_metrics_table.csv` is the GPR reference read by 06/07/08) |
| `week4_06_gp_classifier_surrogate.py` | `surrogates.py` (fixed GPC), `acquisition.py` (classifier rules, shortlist-normalised repulsion) | `synthetic_gpc.py` (S5) | `outputs/week4_06_gp_classifier_surrogate/combined/` |
| `week4_07_optimized_gp_classifier_surrogate.py` | `surrogates.py` (optional variant kernels) | none | `combined/fixed_vs_optimized_classifier_comparison.csv`; rest archive-only |
| `week4_08_boundary_weighted_sur.py` | `benchmarks.py` (hartmann4, seed+700_000), `metrics.py` (GPC branch), `sur.py` | `synthetic_gpc.py` | GPR-side IVR/SUR archive-only |
| `week4_09_gpc_bernoulli_sur_validation.py` | `sur.py` (Bernoulli SUR), `acquisition.py` (pool-normalised repulsion) | `synthetic_gpc.py` (S6) | `outputs/week4_09_gpc_bernoulli_sur_validation/combined/` (claim C10) |
| `notebooks/week_05/01-05`, `outputs/week5_*` | none | none | archive-only (Week 5 has no src module) |
| `week6_phase1`, `phase2`, `phase2_5`, `phase3`, `phase3_5`, `phase4` | none (target constants documented in `docs/data.md`) | none | archive-only; decision CSV/MD files curated |
| `week7_sph_v2_common.py` | `data.py` (pins, ledgers, `parse_experiment_name`), `io.py` | none | none |
| `week7_phase1_sph_v2_dataset_shift_audit.py` | `data.py` (`experiment_registry`, `has_keyhole`) | none (D1 runs in the archive) | `outputs/week7_01_sph_v2_audit/{summary.json,experiment_registry.csv}` |
| `week7_phase2`, `week7_phase5_5` | none (frozen into `data/population.csv`) | none (D2) | `outputs/week7_02_*/summary.json`, `outputs/week7_05_5_*/population_readiness_by_partition.csv` |
| `week7_phase3`, `week7_phase4`, `week7_phase5` | none | none (D3) | archive-only; `depth_error_diagnosis_summary.csv`, `physical_proxy_candidate_scorecard.csv` curated |
| `week7_phase6_real_data_boundary_active_level_set.py` | `surrogates.py`, `acquisition.py`, `metrics.py`, `protocol.py` (Phase 6 splits, warm start), `data.py` (`input_tuple_hash`) | `real_benchmark.py` (R1) | `data/population.csv`; `outputs/week7_06_*/{phase6_final_decision.csv,active_learning_aulc_summary.csv,outer_split_manifest.csv}` |
| `week7_phase6_reporting.py`, `week7_phase7_reporting.py` | none | none | archive-only (figure suites) |
| `week7_phase7_final_boundary_hybrid_benchmark.py` | `acquisition.py` (hybrids), `metrics.py` (B1/B2/B3, `deterministic_order`), `stats.py` | `real_benchmark.py` (R2) | `outputs/week7_07_*/{phase7_final_decision.csv,phase7_preregistered_decision_rule.json,phase7_preregistered_decision_rule.sha256}` |
| `week8_final_sample_efficiency_thesis_consolidation.py` | none | none | `outputs/week8_02_thesis_consolidation/` curated with a stale-wording note (2.33x) |
| `week8_5_frozen_sample_efficiency_confirmation.py` | `protocol.py` (SplitSpec, maximin design, seed keys), `metrics.py` (`aulc`, `persistent_crossing`), `stats.py` (hierarchical bootstrap, decision ledger), `io.py` (`seed_u32`) | `frozen_protocol.py` (R3) | `outputs/week8_5_frozen_confirmation/{preregistered_protocol.json,decision_ledger.csv,bootstrap_or_hierarchical_ci.csv}`; tarballs stay in the archive |
| `week9_phase1_horizon_extension.py`, `week9_phase1_close_week8.py` | `metrics.py` (crossing evidence) | none (R4) | `outputs/week9_phase1_close_week8/{query_saving_claim_decision.json,crossing_by_horizon.csv}` |
| `week9_phase1_terminal_pca.py`, `week9_phase1_discriminative_update.py` | `physics.py` (`physical_scores`, optional) | none | archive-only |
| `week9_phase1_5_h_physics_confirmation.py` | `physics.py` (`h_coordinates`), `acquisition.py` (`choose_gpc_margin`) | `physics_surrogates.py` (P1, partly) | `outputs/week9_phase1_5_*/{active_AULC_contrasts.csv,empirical_exponent_summary.csv}` |
| `week9_phase1_7`, `phase1_8`, `phase1_9` | `physics.py` (`log_h`), `hybrid_gpc.py` (trend+residual kernel), `protocol.py` (A0 path loader), `stats.py` (repeat-block bootstrap) | `physics_surrogates.py` (P2-P4) | `primary_decision.json`, `primary_decomposition.csv`, `primary_AULC_summary.csv`; `tables/query_paths.csv.gz` (A0) read from the archive |
| `week9_phase1_10_*`, `week9_phase1_10_closure_diagnostics.py` | none | none | archive-only (needs network and pypdf) |
| `week9_phase1_11`, `phase1_12`, `phase1_13` | `physics.py` (`FixedMeanLaplaceGPC`, `fit_physics_mean`), `surrogates.py` (G0-G4), `hybrid_gpc.py` (M2W/M3) | `physics_surrogates.py` (P5) | `model_summary.csv`, `paired_contrasts.csv` per phase; `new_predictions.csv.gz` read from the archive |
| `week9_phase1_14_m3_margin_acquisition.py` | `acquisition.py` (`choose_m3_margin`), `protocol.py` (sequential runner, P1 path loader) | `physics_surrogates.py` (P6) | `paired_contrasts.csv`, `early_late_contrasts.csv`; `m3_margin_paths.csv.gz` read from the archive |
| `week9_phase1_15a`, `16`, `17a`, `18a`, `18b0` | `acquisition.py` (`choose_repulsion`), `sur.py` (Laplace-GPC utilities, exact update levels) | none | archive-only; decision JSON/CSV curated |
| `week9_phase1_18b_*.py`, `week9_phase1_18b_finalize.py` | `sur.py` (`hypothetical_update`, `score_candidates`) | none (section 8) | finished evidence only in commit `2552078` and the original worktree |
| `scripts/` (18 builders, 7 validators), `notebooks/`, `tests/` | none | none | archive-only; about five invariant checks re-expressed in `tests/` |
| `docs/thesis_progress_log.md`, `reports/01-05*.md` | none | none | sources for `docs/overview.md`, `docs/claims.md` |

## 3. Regenerable versus sole-copy evidence

| Artifact (archive path) | Size | Regenerable by | Keep policy |
|---|---|---|---|
| `outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark/checkpoints/` | copy: 150 files, 294 MB; original worktree: 200 files, 395 MB | `--run` (about 10 CPU-hours so far; last run 2840 s on 8 workers with 155 reused) | gitignored, sole copies; keep both, never delete |
| `outputs/week8_5_frozen_confirmation/week8_5_checkpoint_bundle.tar.gz` | 44 546 401 B, sha256 `1004fc29...` | Week 8.5 `run` (9336 s, 464 000 GPC fits) | keep (tracked); Week 9 A0 paths come from it |
| `outputs/week8_5_frozen_confirmation/week8_5_large_machine_readable_artifacts.tar.gz` | 25 907 280 B | `refresh-postrun` | keep (tracked) |
| `outputs/week9_phase1_close_week8/week9_phase1_h320_checkpoint_bundle.tar.gz` | 57 143 605 B | horizon extension (hours) | keep (tracked) |
| `outputs/week6_03_5_regime_target_design/regime_geometry_time_series.parquet/` (241 parts) | 901 MB | Week 6 Phase 3.5 from the sph_dataset raw cache, which is absent | only local frame-level geometry; leave in the archive, never copy |
| `outputs/week7_06_*/` caches (prediction history, checkpoints, figures) | about 170 MB | Phase 6 rerun, 922 s on 4 workers | regenerable |
| `outputs/week7_07_*/` caches | about 120 MB | Phase 7 rerun, 262 s | regenerable |
| Week 9 per-prediction dumps (1.11-1.18B0) | about 270 MB | per-phase `--run`, 4-15 min each | keep the three read by later phases: `week9_phase1_13/new_predictions.csv.gz`, `week9_phase1_14/m3_margin_paths.csv.gz`, `week9_phase1_18a/candidate_scores_pre_reveal.csv.gz` |
| Week 6 checkpoints and LOO predictions | about 75 MB | reruns needing the absent raw cache | leave in the archive |
| `notebooks/` (70 MB), `scripts/`, manifests, logs | - | builders and validators | scaffolding |

Raw data caches (`data/raw/huggingface/sph_dataset/`, `data/raw/sph_v2/<revision>/`, `.cache/external_masinelli/`) are absent from the archive. The only file list for a fresh download is `outputs/week7_02_sph_v2_target_extraction/monitor_source_plan.csv`.

Policy in this tree: `results/` holds curated evidence under a 50 MB cap; anything larger is listed by path and sha256 in `results/MANIFEST.csv` and stays in the archive. `data/population.csv` is the only dataset copied.

## 4. Hash conventions

This checkout has `core.autocrlf=true`. `.gitattributes` (53 lines) forces `text eol=lf` only for Phase 1.9 to 1.16 paths; nothing earlier and none of 1.17A, 1.18A, 1.18B0, 1.18B is covered. So most archived text files are CRLF on disk while git stores LF, and a recorded hash matches the file only under the convention it was computed with.

| Artifact | Recorded hash | Computed over | Raw sha256 of the file on disk |
|---|---|---|---|
| `outputs/week7_06_*/primary_common_population.csv` | `c15658ca...` | raw bytes of the CRLF file (406 CR) | `c15658ca...` (matches) |
| `outputs/week8_5_frozen_confirmation/preregistered_protocol.json` | `bb16865a...` (`protocol_sha256.txt`) | canonical JSON, `json.dumps(indent=2, sort_keys=True, ensure_ascii=False) + "\n"` (`week8_5...py::canonical_protocol_bytes`); identical to LF-normalised bytes | `f888d49b...` |
| `outputs/week7_07_*/phase7_preregistered_decision_rule.json` | `a3581cb6...` (`.sha256` file, `EXPECTED_PREREG_SHA256`) | LF-normalised bytes | `5ebfc959...` |
| `outputs/week6_01_*/week6_phase1_simulation_level_responses.csv` | `10DEF11A...` (uppercase, `phase3_runtime_provenance.json`) | LF-normalised bytes | `d0d38d6c...` |
| `source_hashes_json` in `outputs/week8_5_frozen_confirmation/run_manifest.json` (p6 source `23797dcb...`) | `23797dcb...` | raw bytes of the CRLF source file | `23797dcb...` (matches) |
| Tarballs (`1004fc29...`) | raw bytes | raw bytes | matches |

Rule: never "verify" an archive file by re-hashing it without naming the convention. Tests that pin a hash state raw, LF-normalised or canonical JSON.

## 5. Gates that stop archive scripts running outside their worktree

| Kind | Where (constant, `src/` file) |
|---|---|
| Branch / commit asserts | `EXPECTED_BRANCH` in `week6_phase2_5`, `week6_phase3`, `week6_phase3_5`, `week6_phase4`, `week8_final`; `STARTING_HEAD`/`EXPECTED_HEAD b112f6b2` in `week6_phase3`, `week6_phase3_5`, `week6_phase4`; `STARTING_HEAD f26f0671` (`week7_phase3`); `PHASE3_PARENT_SHA 1118d30f` (`week7_phase4`); `PHASE4_COMMIT_SHA 5b700401` (`week7_phase5`); `PHASE5_COMMIT_SHA 3367f4c9` (`week7_phase5_5`); `EXPECTED_PHASE55_PARENT 6cc2ea15` (`week7_phase6`); `EXPECTED_PHASE6_COMMIT 5734de6f` (`week7_phase7`); `EXPECTED_PARENT 167aad94` (`week8_final`, `scripts/validate_week8.py`); `STARTING_SHA`/`START_SHA` in every `week9_phase1_*` module (`bdb6eb36`, `b36a815e`, `2f750c8c`, `f74c6252`, `8d99c197`, `45e2677b`, `e33cca4f`, `5a21e5dc`, `16145398`, `fbe76352`, `1e34b475`); `FROZEN_COMMIT 6487722f` (`horizon_extension`) |
| Live remote checks | `git ls-remote --heads origin` and `EXPECTED_HF_REVISION b6dc254a` against Hugging Face in `week7_phase6` |
| Byte-hash manifests | `EXPECTED_CORE_ARTIFACT_HASHES`/`CORE_HASHES` over Week 6 sources, notebooks and outputs (`week6_phase3`, `week6_phase3_5 --validate-only`); `source_hashes_json` stamped by `week8_5`; `FROZEN_ARCHIVE_SHA256 1004fc29...` (`horizon_extension`); `run_manifest.json` per Week 9 phase; `week9_phase1_18b_finalize.py::validate` greps the engine source for literal strings such as `reference = np.delete(candidates, j)` |
| Absolute paths | `ORIGINAL_WORKTREE = C:\Users\ozgur\Documents\thesis` (`week6_phase1`, `phase2`, `phase3`, `phase3_5`, `phase4`, `week7_phase5_5`); `WEEK6_RAW_ROOT` under `C:/Users/ozgur/Documents/thesis-week6-melt-pool-audit/` (`week7_sph_v2_common`); interpreter paths in section 6 |
| git as a runtime dependency | `subprocess` in 46 places; every Week 9 `historical_changes()` and 11 test files shell out to `git`, so a copy without the parent `.git` fails before any science runs |

Consequence: "runnable" in section 7 means runnable in the original worktree. This tree imports archive modules only for parity tests and only those that are side-effect free at import (`docs/architecture.md`, porting rule 7).

## 6. Environment behind the frozen numbers

| Item | Recorded value and source |
|---|---|
| Interpreter | Python 3.14.4 (MSC v.1944, AMD64), Windows 11 (`outputs/week6_03_model_target_robustness/phase3_runtime_provenance.json`) |
| Libraries | numpy 2.5.1, pandas 2.3.3, scipy 1.18.0, scikit-learn 1.9.0, matplotlib 3.11.1 (same file; sklearn 1.9.0 also in `outputs/week9_phase1_10_closure_diagnostics/regularization_sensitivity.csv`, R3 row) |
| `requirements.txt` | lower bounds only (`numpy>=2.3`, `scipy>=1.17`, `scikit-learn>=1.7`, `pandas>=2.3,<3`); not listed: `pytest` (21 test files), `pypdf` (`week9_phase1_10`), `joblib` (imported by 11 src modules; arrives with scikit-learn), a Jupyter kernelspec named `thesis` |
| Interpreter paths in code | `.\.venv\Scripts\python.exe` (`README.md` L19, `week6_phase2_5` L8-12); `C:\Users\ozgur\Documents\thesis-week6-melt-pool-audit\.venv\Scripts\python.exe` (provenance JSON); `C:\Users\ozgur\anaconda3\envs\thesis\python.exe -m pytest` (`scripts/build_week9_phase1_5_artifacts.py` L267, `build_week9_phase1_7_artifacts.py` L255); `ROOT.parent/thesis-week5-first-conduction-gp/.venv/Scripts/python.exe` and two sibling venvs (`week9_phase1_10` L895-897); kernel `thesis` (`week9_phase1_18b_finalize.py` L424-426, `18b0` L319) versus `python3` elsewhere |
| This machine now | Python 3.14.4 at `C:\Users\ozgur\AppData\Local\Python\pythoncore-3.14-64\python.exe`; numpy 2.5.1, pandas 3.0.5, scipy 1.18.0, scikit-learn 1.9.0, pytest 8.4.2, joblib 1.5.3, pypdf 6.16.2; `jupyter` not on the shell PATH |

pandas caveat: the archive ran pandas 2.3.3, this tree runs 3.0.5. Archive modules imported through `archive_src` therefore execute under a pandas they never saw. Keep algorithms on numpy arrays, avoid behaviour that changed in 3.0 (default string dtype, copy-on-write), and treat a parity failure that involves DataFrame indexing as a pandas suspect before a science suspect.

## 7. Commands for the archived experiments

All commands run from the archive root as `python -m src.<module>`; `--smoke`/`--quick` exist where shown. Wall times are the values recorded in the archive outputs; "not recorded" means no artifact states one.

| ID | Command | Workers | Wall time | Network | Needs checkpoints or prior outputs |
|---|---|---|---|---|---|
| S1 | `week2_acquisition_comparison` (no args) | 1 | not recorded (minutes) | no | none |
| S2 | `week3_4d_named_benchmark_comparison` (no args) | 1 | not recorded (minutes) | no | none |
| S3 | `week4_01_boundary_metrics` (no args) | 1 | not recorded | no | none |
| S4 | `week4_04_lookahead_boundary_uncertainty` (no args) | 1 | not recorded (expensive) | no | none |
| S5 | `week4_06_gp_classifier_surrogate [--quick] [--skip-smoke]` | 1 | not recorded | no | `outputs/week4_05_*/*/final_metrics_table.csv` as GPR reference |
| S6 | `week4_08_boundary_weighted_sur --full` then `week4_09_gpc_bernoulli_sur_validation --full --benchmarks branin hartmann4 [ackley] [--max-seeds N] [--shortlist-sizes 15 25]` | 1 | 1735 s + 1721 s | no | 09 imports 08 |
| D1 | `week7_phase1_sph_v2_dataset_shift_audit [--smoke] [--refresh-tree] --workers 6` | 6 | 765 s | HF `d69dac5b` | none |
| D2 | `week7_phase2_sph_v2_physical_target_extraction [--smoke] --workers 6`, then `week7_phase5_5_g3_robustness_transfer_analysis [--smoke]` | 6 | 157 s (Phase 2) | HF, both pins | Phase 1 outputs, `monitor_source_plan.csv`; Phase 5.5 also reads the absent Week 6 cache and `ORIGINAL_WORKTREE` |
| D3 | `week7_phase5_keyhole_physical_proxy_analysis [--smoke]` | 1 | not recorded | no | Phase 2 and Phase 4 outputs |
| R1 | `week7_phase6_real_data_boundary_active_level_set {prepare,smoke,full} --workers 4 [--force]` | 4 | 922 s (active 796 s) | HF ledgers, `ls-remote origin`, HF revision check | `primary_common_population.csv`, `outer_split_manifest.csv` |
| R2 | `week7_phase7_final_boundary_hybrid_benchmark [--smoke] [--prepare-only] --workers 4 [--force] [--force-reproduction]` | 4 | 262 s | git gates only | Phase 6 CSVs (`active_query_history.csv`) |
| R3 | `week8_5_frozen_sample_efficiency_confirmation {prepare,smoke,run,finalize,refresh-postrun,all} --workers 4 [--max-wall-hours 6] [--horizon 80/120/160]` | 4 | 9336 s (2.6 h); do not rerun | no | `refresh-postrun` needs the checkpoints inside the 44.5 MB bundle |
| R4 | `week9_phase1_horizon_extension {preflight,extract,validate,run,status,refresh} --workers 4 [--limit-jobs N]`; `week9_phase1_close_week8 {analyze,figures,package,reports} [--bootstrap-draws N]` | 4 | hours (extension); analysis minutes | no | Week 8.5 bundle (sha `1004fc29...`), H=320 bundle |
| P1 | `week9_phase1_5_h_physics_confirmation {audit,static,active,aggregate,figures} [--horizon 80] [--workers 1] [--arms ...]` | 1 (default) | active arms hours, not recorded | no | `split_manifest.csv`; arm checkpoints in `active_checkpoints_H160.tar.gz` |
| P2 | `week9_phase1_7_physics_ridge_residual_gp {baseline-gate,static,active,aggregate,figures} [--workers 1]` | 1 (default) | not recorded | no | checkpoints gitignored and absent |
| P3 | `week9_phase1_8_model_path_decomposition {audit,cross,y00-checkpoints,sensitivity,aggregate,figures,reports,notebook,red-team,...} --workers 4 [--limit-specs N]` | 4 | not recorded | no | A0 paths from the Week 8.5 bundle |
| P4 | `week9_phase1_9_physics_specificity_control {gate,smoke,active,static,aggregate,figures,reports,notebook,red-team,validate,...} --workers 4` | 4 | not recorded | no | Phase 1.7/1.8 tables |
| P5 | `week9_phase1_11_fixed_mean_discrepancy_gp --parity --run --finalize --workers 4`; `week9_phase1_12_gpc_kernel_adequacy --run [--g0-checkpoints] ...`; `week9_phase1_13_fixed_physics_ard_discrepancy --parity --run --sensitivity --finalize --publish --workers 4 [--limit-specs N]` | 4 | 262 / 543 / 570 s | no | `--run` recomputes (checkpoints absent); `--publish` works offline from tracked tables |
| P6 | `week9_phase1_14_m3_margin_acquisition --preflight --run --sensitivity --finalize --workers 4 [--limit-specs N]` | 4 | 214 s | no | Phase 1.13 tables |
| P7 | `week9_phase1_18b_prospective_global_gpc_sur_benchmark --preflight --run --workers 6 [--limit-specs N] [--arms P1_EXACT_FIXED_SUR P2_PHYSICS_REFIT_SUR]`; then `week9_phase1_18b_finalize --finalize` | 6 default (8 used) | 2840 s with 155/200 reused; per run P1 median 217 s, P2 469 s | no | checkpoints; finalize needs `week9_phase1_18a/candidate_scores_pre_reveal.csv.gz` and kernel `thesis` |

## 8. Phase 1.18B: state and what to do

Two copies of this phase exist and they differ.

| | Archive copy (OneDrive) | Original worktree (`C:/Users/ozgur/Documents/thesis-week9-phase1-18b-...`) |
|---|---|---|
| Checkpoints | 77 P1 + 73 P2 (150/200), 294 MB | 100 + 100, 395 MB |
| `execution_report.json` | 2-job smoke: `complete: false`, 196 s, 2 workers | `complete: true`, jobs 200, reused 155, workers 8, 2840 s |
| Finalize outputs | absent | present and committed in `2552078`: `primary_decision.json` = `GLOBAL_SUR_NO_GAIN` (`catastrophic_fullheldout_degradation: false`); `model_aulc_summary.csv` P0 0.8446231617647058, P1 0.8432444852941178, P2 0.8401700367647059 |
| Engine source | older, without the `try/except` on interrupted checkpoints | committed version; working tree clean |

So the run was finished and finalised in the original worktree on 2026-09-03; the "finish or archive" decision is closed there. What is still open is that the archive copy, which `alse.config` points at, holds a pre-finalize snapshot of this one directory.

Recommended steps:

1. Back up the original repository `C:/Users/ozgur/Documents/thesis` (push or copy); commit `2552078` and the 395 MB of gitignored checkpoints are the only complete record of Phase 1.18B.
2. Sync the archive copy once by plain file copy of `outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark/` (and `src/week9_phase1_18b_prospective_global_gpc_sur_benchmark.py`) from the original worktree, then treat it as read-only again. Record the sync in `docs/decisions.md`. Do not use `git checkout` inside the copy (section 1).
3. Curate `primary_decision.json`, `model_aulc_summary.csv`, `q20_primary_contrasts.csv` and `multiplicity_adjustment.csv` into `results/` after the sync; `docs/claims.md` should then cite 1.18B as a closed negative (no acquisition on M3 beats margin).

If a rerun from the copy is ever attempted anyway: `--run --workers 6` resumes from existing checkpoints (23 P1 + 27 P2 remain, about 4.7 CPU-hours), then `week9_phase1_18b_finalize --finalize`. Pitfalls: `baseline_gate.json` records `start_sha 1e34b475...` while the shared HEAD is now `2552078`, so the engine's git gate is untested in the copy; the finalize notebook step executes under a Jupyter kernelspec named `thesis` (`week9_phase1_18b_finalize.py` L424-426), which the other phases do not use and which is not installed for the interpreter listed in section 6; `validate()` greps the engine source for literal strings, so the engine must not be reformatted.
