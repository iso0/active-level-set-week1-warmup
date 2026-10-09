# Week 19 — temporal regime audit

Ioan's question: which simulations contain Keyhole and Conduction, in particular Keyhole followed by only Conduction
and alternating regimes? Can the monitor time series explain these transitions, and the loss of OLD's
max-depth/label relationship on October NEW?

This is an investigation, not a method study. No model is trained, no label, eligibility decision or historical
output is changed, and C3 stays unused. Results: [REPORT.md](REPORT.md). Compact hand-off: [ASTRA_HANDOFF.md](ASTRA_HANDOFF.md).

## Reproduce

```bash
python -m src.week19_sources meta        # pinned tree metadata (sizes, Git blob / LFS ids) -> provenance/remote_metadata.csv.gz
python -m src.week19_sources download    # verify the cached bytes; download only the missing files at the pins
python -m src.week19_temporal_audit all  # labels -> series -> tables -> analysis -> ke -> figures -> checks -> manifest (~90 s)
python -m pytest src/tests/test_week19_sequences.py -q
```

The raw files live in the git-ignored cache `data/raw/sph_v2/<revision>/<path in repo>`:

- OLD files are at `b6dc254a…`, except 12 bounds files reused from the Week 7 audit pin `d69dac5b…`, which are byte-identical (verified).
- NEW files are at `2e1eec9c…`.

`_cache/` holds intermediate pickles. It is git-ignored and rebuilt by the `labels`, `series` and `tables` steps.

## Code

| Module | Role |
|---|---|
| `src/week19_sources.py` | Pins, eligible populations, pinned-tree metadata, verified reuse/download, `local_file()` |
| `src/week19_sequences.py` | Ledger loading (order preserved), `has_keyhole` re-derivation, sequence descriptors (no gap bridging) |
| `src/week19_series.py` | frames.csv → iter.dat → time.dat mapping; Week 7 windows; depth definitions A–D; frame-level depth |
| `src/week19_analysis.py` | Phase 2 comparisons, Phase 3 separability, the 12 NEW negatives, out-of-fold diagnostics |
| `src/week19_figures.py` | Figures |
| `src/week19_temporal_audit.py` | Driver, OLD reference-threshold recovery, reproduction checks, run manifest |
| `src/tests/test_week19_sequences.py` | Unit tests of the descriptors and the hold rule |

## Outputs

| Path | Content |
|---|---|
| `tables/CHECKS.csv` | 24 provenance and reproduction checks (22 PASS, 2 INFO, 0 FAIL) |
| `tables/temporal_registry.csv` | One row per eligible simulation (541): identity, inputs, evidence paths, QC, label counts, ratios, alternative labels, descriptors, timing, windows, depth definitions, flags |
| `tables/frame_level_map.csv.gz` | Every labelled frame (140,594): source labels, timestep, monitor row, monitor time, depth at that row, window flags |
| `tables/k_runs.csv`, `tables/regime_switches.csv` | Keyhole runs and Conduction/Keyhole switches, with times and brackets |
| `tables/descriptor_counts.csv`, `positive_K_fraction_summary.csv`, `alternative_label_class_changes.csv`, `switch_timing_summary.csv` | Phase 1–2 summaries |
| `tables/input_region_by_VX.csv`, `common_support_comparison.csv`, `fast_scan_common_support_cases.csv`, `K_then_C_subgroups.csv`, `K_then_C_cases.csv` | Input regions and like-for-like comparisons |
| `tables/representative_cases.csv`, `nearest_neighbours_new_negatives.csv`, `kinetic_energy_row_check.csv` | Representative IDs (deterministic rule) and matched cases |
| `tables/depth_definitions.csv`, `separability.csv`, `positives_below_uref_by_definition.csv` | Phase 3 |
| `tables/new_negatives_12_cases.csv`, `new_negatives_mechanism_summary.csv` | The 12 NEW negatives, one row each |
| `tables/oof_*.csv(.gz)` | Existing Week 18 DEV out-of-fold predictions and diagnostics (no retraining) |
| `figures/fig1`–`fig6` | Descriptors, K fractions, switch timing, depth definitions, the 12 negatives, representative cases |
| `provenance/` | Remote metadata, download manifests, label-membership audit, OLD threshold recovery, run log, `RUN_MANIFEST.json` (SHA-256 of every output) |

## Conventions

- **Keys.** Full simulation folder names are the keys. H suffixes are not unique; for example, `H-b302fc6cbd` names two different NEW runs.
- **Units.** LS is the spot radius (source: metres; tables: µm as `LS_um_radius`), depth is in µm, times are monitor times in ms.
- **Two different "G3" objects.** "G3" alone is the binary GP classifier. `G3_persistent_depth_um` (G3pd) is the Week 6/7 physical rolling-median statistic.
- **Evidence labels.** OBSERVATION, PHYSICAL INTERPRETATION (hypothesis), PREDICTIVE (existing predictions), POST-HOC (motivated by the NEW labels).
