# Data

Archive paths are relative to `../thesis_work_chatgpt`. Lean code: `alse/data.py`. The frozen dataset is `data/population.csv`. Target extraction is not ported; its rules are recorded in section 6.

## 1. Datasets and pinned revisions

| Dataset | Pin | Used by | Content |
|---|---|---|---|
| `ioandanielc/sph_dataset` (Hugging Face) | `0e859b748fdbc8454f66e58e101e333ac0479d42` | Weeks 5-6 | 241 folders `final_data_processed/sim_XXXXX/` (ids 1-242, id 136 missing) and `final-labels_all.csv` (`outputs/week6_01_melt_pool_data_audit/summary.json`) |
| `ioandanielc/sph_v2`, audit pin | `d69dac5bda8b622bc0de316b112815c6056c06ec` | Week 7 Phases 1-5 | 407 experiment folders, 3 partition ledgers; 350/407 targets extractable (`outputs/week7_02_sph_v2_target_extraction/summary.json`) |
| `ioandanielc/sph_v2`, final pin | `b6dc254a2b607a31cb9f97b40990339c3d5ca1e8` | Phase 5.5 onward, `data/population.csv` | audit pin plus 110 added files (`time.dat` and `kinetic-energy_melt.dat` for 55 old-data-local experiments), nothing modified or deleted (`outputs/week7_05_5_g3_robustness_transfer_analysis/hf_change_audit.json`) |

Archive constants: `src/week7_sph_v2_common.py::SPH_V2_REVISION` (audit), `WEEK6_REVISION`; `src/week7_phase6_real_data_boundary_active_level_set.py::EXPECTED_HF_REVISION` (final). Lean: `alse.data.SPH_DATASET_REVISION`, `SPH_V2_REVISION_AUDIT`, `SPH_V2_REVISION`.

## 2. Partition ledgers

Three CSV files at the repository root, one row per labelled frame, loaded by `week7_sph_v2_common::load_partition_labels` (lean `alse.data.load_partition_labels`).

| Partition | File | Experiments | Frames | Keyhole experiments |
|---|---|---|---|---|
| new-data | `labels_partition_1_new-data.csv` | 165 | 45 156 | 63 |
| old-data-local | `labels_partition_2_old-data-local.csv` | 179 | 49 304 | 8 |
| old-data-remote-clean | `labels_partition_3_old-data-remote-clean.csv` | 63 | 16 344 | 2 |
| total | | 407 | 110 804 | 73 |

Experiment and frame counts: `outputs/week7_01_sph_v2_audit/summary.json`. Keyhole per partition: `data/population.csv` grouped by `partition`.
Schema, asserted in exactly this order: `name, hash, P, VX, LS, ST, bug_free, correctly_finished, timestep, label_1, label_2, label_final`. Numbers in `P, VX, LS, ST` use `p` as the decimal point (`101p25` = 101.25; `week7_sph_v2_common::decode_number`). Each experiment appears in one partition only. The loader adds `partition_number, partition, partition_label_file, frame_row_in_partition` and `<feature>_numeric` columns.

## 3. Label semantics

- Only `label_final` is used. `label_1` and `label_2` disagree in 387/407 experiments (`anomaly_experiment_count` in `outputs/week7_01_sph_v2_audit/summary.json`); the disagreement is a review flag, never a label change.
- PHYSICAL labels: `Forming Phase`, `Conduction`, `Keyhole`. TECHNICAL labels: `Initial Emptiness`, `Scanning Stopped`, `Solidifying Stopped`, `Screenshot Bug`, `Unsure` (`week7_sph_v2_common::PHYSICAL_LABELS`, `TECHNICAL_LABELS`).
- Frames of one experiment are ordered by `(timestep, frame_row_in_partition)` (`week7_phase1_sph_v2_dataset_shift_audit::sequence_audit`).
- `has_keyhole` = any frame with `label_final == 'Keyhole'`; `has_conduction` likewise. The two are not exclusive: 73 Keyhole and 373 Conduction experiments, 6 700 Keyhole frames (`outputs/week7_01_sph_v2_audit/summary.json`).
- `keyhole_fraction_of_relevant_physical_frames` divides by the number of PHYSICAL-label frames.
- Transient: `keyhole_transient_by_sequence` = the last PHYSICAL frame is not Keyhole. Persistent: `keyhole_persistent_to_last_physical_frame`. Among the 73 Keyhole experiments: 30 transient, 43 persistent, 16 with more than one Keyhole segment (`outputs/week7_01_sph_v2_audit/experiment_label_sequences.csv`).
- Lean `alse.data.experiment_registry` reproduces `has_keyhole`, `has_conduction`, the fraction and the transient flag.

## 4. Experiment folders and `parameters.json`

Folder grammar (`week7_sph_v2_common::FOLDER_PATTERN`, lean `alse.data.FOLDER_PATTERN`):
`P-<P>_VX-<VX>_LS-<LS>_ST-<ST>_M-<material>_XI-<XI>_XF-<XF>_XL-<XL>_TE-<TE>_DT-<DT>_H-<hash>`, numbers with `p` decimals. Example, first row of `data/population.csv`: `P-102p928146519_VX-0p633805217924_LS-5p29394366699e-05_ST-318p223787128_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-7p61136145079e-06_H-6c9c68731f`. `parse_experiment_name` returns `P, VX, LS, ST, XI, XF, XL, TE, DT, material, folder_hash`.

Each folder holds `parameters.json`, `frames.csv` and `monitor/{position-bounds_melt,time,iter,kinetic-energy_melt}.dat` (`week7_phase1::REQUIRED_EXPERIMENT_FILES`). The registry reads the `parameters.json` keys `laser_power`, `scan_speed_x`, `laser_spot_size`, `substrate_temperature` (fields `.value`, `.unit`) and checks them against folder name and ledger with `atol=1e-14` (`week7_phase1::build_experiment_registry`; `outputs/week7_01_sph_v2_audit/experiment_registry.csv`). `XF` and `XL` from the folder name fix the domain end used by target extraction: `domain_max_x = min(XF, XL) + 12e-6` m, which is 0.001212 m for every row of `data/population.csv` (column `domain_max_x_m`).

## 5. Units

| Column | Unit | Note |
|---|---|---|
| `P` | W | laser power |
| `VX` | m/s | scan speed |
| `LS` | m | Gaussian spot RADIUS `r0`, not diameter: `week6_phase3_5_regime_target_design::load_metadata_map` asserts `laser_spot_size == experiment_details spot_radius`; `reports/02_data_unit_statistical_reproduction_audit.md` |
| `ST` | K | substrate temperature |
| `T0_*_um`, `max_*_um`, `G3_persistent_depth_um` | um | monitor bounds are in m, reported x 1e6 |
| `T0_kinetic_energy_nJ`, `max_kinetic_energy_nJ` | nJ | monitor in J, reported x 1e9 |
| `h` (Week 9) | W s^1/2 m^-2 | `h = P / sqrt(VX * LS^3)` with LS in m |

Caveat: Week 7 Phases 3-4 modelled `LS_um` (micrometres). The population and everything from Phase 6 on use `LS` in metres (copy of `LS_m`). Ranges in `data/population.csv`: P 52.54 to 449.76 W, VX 0.2010 to 0.9983 m/s, LS 40.03 to 89.70 um, ST 300.0 to 399.82 K.

## 6. Target extraction (archive only)

Implemented by `src/week7_phase2_sph_v2_physical_target_extraction.py::extract_one` (with `load_numeric`, `base_target_row`, `scalar_window_stats`, `locate_relative`, `extract_population`), using the Week 6 constants of `src/week6_phase1_melt_pool_data_audit.py` and the rolling helpers of `src/week6_phase3_5_regime_target_design.py`. Re-run at the final pin by `week7_phase5_5_g3_robustness_transfer_analysis::refresh_targets`.

Inputs
: four monitors per experiment: `position-bounds_melt.dat` (six columns `x_min,x_max,y_min,y_max,z_min,z_max` in m), `time.dat` (s), `iter.dat` (solver iteration), `kinetic-energy_melt.dat` (J). A missing or unparseable monitor is a failure. Row counts must agree; time and iteration must be strictly increasing.

Sentinel
: `+-3.402823e+38` means "no melt" (`SOLVER_NO_MELT_SENTINEL_VALUE`). The single malformed field `s3.402823e+38` (experiment `...H-1553ff852f`; `outputs/week7_02_sph_v2_target_extraction/summary.json`) is read as that sentinel by `load_numeric`; no other repair. A bounds row is valid iff all six values are finite, `|v| < 1e30` (`SENTINEL_THRESHOLD`) and `max >= min` on every axis.

Geometry per row
: `width = y_max - y_min`; `length = x_max - x_min` (diagnostic only); `depth = max(0, -z_min)`; `total_height = z_max - z_min`.

Active region
: `laser_exit_time = domain_max_x / VX`; `active_cutoff = min(t_end, 0.90 * laser_exit_time)` (`ACTIVE_DOMAIN_FRACTION = 0.90`); active rows = valid rows with `t <= active_cutoff`; failure if there are none.

T0 window
: valid rows with `t` in the last 20% of `[first_valid_time, active_cutoff]` (`LATE_WINDOW_FRACTION = 0.20`); if fewer than 50 rows, the last 50 active rows (`MIN_LATE_ROWS = 50`, flag `T0_fallback_last_rows_used`). The kinetic monitor must cover the window with at least one finite non-negative value.

T0 targets
: `T0_<response>` = median over the window, plus mean, variance, std, cv, relative trend and count (`week6_phase1::_window_cv_trend`). Responses: width, length, depth, total_height (um) and kinetic_energy (nJ).

Max targets
: `max_<response>` = maximum over all valid rows, with row index, iteration, time and location `before / inside / after` T0 (`locate_relative`). `value__max_depth` in the population is `max_depth_um`. Over the 350 rows at the audit pin the maximum depth lies before / inside / after T0 in 246 / 68 / 36 cases (`outputs/week7_02_sph_v2_target_extraction/summary.json`).

G3 and R3
: laser position `x = VX * t`; adaptive interior `[onset_x + 50e-6, min(last_valid_x, domain_max_x) - 50e-6]` (`STARTUP_MARGIN_M`, `END_MARGIN_M`). `G3_persistent_depth_um` = maximum of the 50-um trailing rolling median of depth over that interior (`rolling_distance_stat`, `PRIMARY_PERSISTENCE_WINDOW_UM = 50`). `R3_persistent_depth_width_ratio` = the same statistic of `depth / width` with a 12-um width guard (`safe_ratio`, `PRIMARY_WIDTH_GUARD_M = 3 * 4e-6`). No interior gives NaN: one experiment, `...H-bf889bf790` (`outputs/week7_05_5_g3_robustness_transfer_analysis/current_revision_simulation_level_targets.csv`).

Flags, never exclusions
: `flag_primary_window_unstable_week6_rule` (T0 cv > 0.10 for width or length, > 0.15 for depth); `recording_ends_before_90pct_domain` (141 rows); `flag_depth_bounding_box_ambiguity_candidate` (`max_depth - G3 > 20 um` and `max_depth / G3 > 1.25`; 8 rows); `active_region_too_short` (fewer than 50 active rows). Counts: `outputs/week7_02_sph_v2_target_extraction/summary.json`.

Label timing
: ledger timesteps are matched exactly to `iter.dat` to count Keyhole frames before / inside / after T0. 22 of the 70 Keyhole-positive rows have no Keyhole frame inside T0 (same summary); this is why `max_depth`, not `T0_depth`, is the physical companion of `has_keyhole`.

## 7. Population construction (405 rows, 73 Keyhole)

1. Registry of 407 experiments from folder names, `parameters.json` and ledgers (section 4).
2. Labels per experiment (section 3).
3. Targets at the audit pin: 350/407 successes, 57 failures, all from missing monitors (new-data 164/165, old-data-local 123/179, old-data-remote-clean 63/63; `outputs/week7_02_sph_v2_target_extraction/summary.json`).
4. Refresh at the final pin (`week7_phase5_5::refresh_targets`): 55 old-data-local experiments re-extracted from the restored monitors, 352 rows reused after a git diff proved their inputs unchanged (`phase55_refresh_action` in `current_revision_simulation_level_targets.csv`). Ready counts: new-data 164/165, old-data-local 178/179, old-data-remote-clean 63/63, total 405/407 (`outputs/week7_05_5_g3_robustness_transfer_analysis/population_readiness_by_partition.csv`).
5. Selection (`week7_phase6::load_population_tables`; lean `alse.data.load_population` only checks the result): `primary_ready = valid_manual_label & valid_features & physical_target_extraction_success & geometry_target_ready & max_depth notna` gives the primary common population, 405 rows; `primary_ready & G3 notna` gives the secondary G3 population, 404 rows. Assertions: 407 / 405 / 404 rows, 73 Keyhole, no `source_label_modified`, no `simulation_silently_removed`.
6. The two excluded experiments, both `has_keyhole = False` (`current_revision_simulation_level_targets.csv`): new-data `...H-4ecd858c02` (missing `kinetic-energy_melt.dat` and `position-bounds_melt.dat`) and old-data-local `...H-f4a4199ba7` (missing `kinetic-energy_melt.dat` and `time.dat`).
7. Grouping key `input_tuple_sha256` = sha256 of the ASCII string of `'%.17g'`-formatted P, VX, LS, ST joined by `|` (`week7_phase6::input_tuple_hash`; lean `alse.data.input_tuple_hash`). Every group has size 1 in the 405 (`input_group_size`).

By partition: new-data 164 rows (63 Keyhole), old-data-local 178 (8), old-data-remote-clean 63 (2) (`data/population.csv`).

## 8. The frozen file `data/population.csv`

Byte-identical copy of `outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv`: 405 data rows, 1 097 989 bytes, CRLF line endings, sha256 of the raw bytes `c15658cac87a8616a1984185ec1afc8126a1db811f0d5819e62cfb621a7486c7` (the value stamped in `source_hashes_json` of `outputs/week8_5_frozen_confirmation/decision_ledger.csv`). After CRLF to LF normalisation the sha256 is `d31391e256c7b07f0ee4544baf65a6aeb80df21c7cba2cbf8cd2a2b24524ccbe` (section 12). Row order is frozen: split manifests index rows by position.

Columns that matter (of about 200):

| Column | Meaning |
|---|---|
| `experiment_name` | folder name, unique |
| `partition` | one of the three ledgers |
| `P`, `VX`, `LS`, `ST` | features in W, m/s, m, K (copies of `P_W`, `VX_m_per_s`, `LS_m`, `ST_K`) |
| `has_keyhole` | target, bool, 73 True |
| `input_tuple_sha256` | grouping key for `StratifiedGroupKFold` |
| `value__max_depth` | `max_depth_um`, response of the Max-Depth GPR arms (Phase 6/7) |
| `value__G3` | `G3_persistent_depth_um`, one NaN |
| `has_conduction`, `keyhole_transient_by_sequence`, `keyhole_persistent_to_last_physical_frame`, `keyhole_persistence_group` | label-sequence descriptors from Phase 1 |
| `primary_ready`, `secondary_g3_ready`, `primary_exclusion_reasons` | selection flags; `primary_ready` is True in every row |

Lean loader `alse.data.load_population` asserts 405 rows, 73 `has_keyhole`, unique names, and parses booleans strictly.

## 9. Re-downloading the raw data

- Mechanism: `hf_hub_download(repo_id="ioandanielc/sph_v2", repo_type="dataset", revision=<pin>, filename=<path in repo>, local_dir=<root>)` (`week7_sph_v2_common::download_pinned_file`; lean `alse.data.download_pinned_file`). No token handling is recorded anywhere.
- Local layout: `data/raw/sph_v2/<revision>/<path in repo>` (archive `RAW_ROOT`; lean `data/raw/` is gitignored).
- File manifest: `outputs/week7_02_sph_v2_target_extraction/monitor_source_plan.csv`, 1 628 rows = 407 experiments x 4 monitors; column `sph_v2_relative_path` is `<folder>/monitor/<file>`; `remote_exists` is False for the 114 files missing at the audit pin; `source_mode` records the origin of each file (854 `week6_cache_verified_against_sph_v2_git_blob`, 660 `pinned_sph_v2_download`, 114 `missing_in_pinned_sph_v2`). The three ledgers (section 2) and the 407 `parameters.json` files complete a rebuild.
- Expected outcome at the final pin: 407 rows, 405 successes, the two failures of section 7, 73 Keyhole. No end-to-end run from a fresh download has been performed; the archive population reused verified Week 6 cache bytes for 854 files.
- Processing time reference: Phase 1 765 s, Phase 2 157 s, downloads excluded (`runtime_seconds` in `outputs/week7_01_sph_v2_audit/summary.json` and `outputs/week7_02_sph_v2_target_extraction/summary.json`).

## 10. Weeks 5-6 dataset (`sph_dataset`)

- `final-labels_all.csv` at the pin above: 65 472 rows x 12 columns (same schema as section 2), 17 421 654 bytes, sha256 `964a12d86435e9f0879e2e43384d997e1cc2faa7b9e4c3aeb49cf0e73e3fb154`, 241 simulations, downloaded by `notebooks/week_05/01_first_conduction_data_audit.ipynb` (`outputs/week5_01_first_conduction_data_audit/data_audit_summary.json`).
- Per simulation folder `final_data_processed/sim_XXXXX/`: `experiment_details.json`, `metadata.json`, `labeling_provenance.json`, `monitor/*.dat`; 241 folders, all monitor-complete (`outputs/week6_01_melt_pool_data_audit/summary.json`).
- Week 6 ledger: `outputs/week6_01_melt_pool_data_audit/week6_phase1_simulation_level_responses.csv`, 241 x 199.
- All 241 simulations reappear in `sph_v2` (`exact_week6_match_count`); the 186 with complete monitors at the audit pin reproduce their Week 6 T0 targets with 0 material changes (`outputs/week7_02_sph_v2_target_extraction/summary.json`, `exact_old_new_target_comparison_summary.csv`).
- No lean code reads this dataset; the raw cache is absent on this machine.

## 11. External sources (Phase 1.10 only)

From `outputs/week9_phase1_10_external_experimental_validation/source_manifest.json`: GitHub `GiulioMa/LPBF-SmartAM-Optical-Data` at commit `50ccb1bab03c626cb9f83d9c4f44182f58dda439`, files `Microscopy_1.xlsx` (10 610 B, sha256 `885ee692...`) and `experiment_parameters_ref.xlsx` (15 178 B, sha256 `4043e796...`); paper Masinelli et al. 2025, Additive Manufacturing 101, 104677, DOI `10.1016/j.addma.2025.104677` (PDF 3 630 055 B, sha256 `37c7e2d6...`); Zenodo record 13380755 (raw data not used). The paper defines the spot as a 50 um diameter at 1/e^2. Cache `.cache/external_masinelli/` is gitignored and absent.

## 12. Hash conventions (CRITIQUE c-M1, c-M2)

| Artifact | Recorded sha256 | Bytes hashed | On-disk sha256 (CRLF checkout) |
|---|---|---|---|
| `primary_common_population.csv` = `data/population.csv` | `c15658ca...` | raw bytes, CRLF | same |
| `outputs/week8_5_frozen_confirmation/preregistered_protocol.json` | `bb16865a...` | canonical JSON, `json.dumps(indent=2, sort_keys=True) + "\n"`, LF (`week8_5::canonical_protocol_bytes`) | `f888d49b...` |
| `outputs/week7_07_final_boundary_hybrid_benchmark/phase7_preregistered_decision_rule.json` | `a3581cb6...` | LF bytes | `5ebfc959...` |
| `outputs/week6_01_melt_pool_data_audit/week6_phase1_simulation_level_responses.csv` | `10def11a...` | LF bytes | `d0d38d6c...` |

The archive checkout has CRLF on every text file not covered by `.gitattributes`, which pins `eol=lf` only from Phase 1.9 on. Check a hash against the convention in this table, never against the other one.
