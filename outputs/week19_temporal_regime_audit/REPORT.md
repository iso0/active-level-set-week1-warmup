# Week 19 — temporal regime audit: Keyhole→Conduction transitions and the NEW depth/label mismatch

**Question (Ioan).** Which simulations contain both Keyhole and Conduction, especially Keyhole followed by only
Conduction, and which alternate between them? Can the monitor time series explain these transitions, and the loss
on October NEW of the OLD relationship between maximum depth and the label?

**Scope.** This is an investigation, not a requirement to make E1 win.

**Rules kept.**
- No model is trained. The only fits are E1's existing 1-D learned-threshold rule, applied to OLD values.
- No label, eligibility decision or historical output is changed.
- The 49 Bug-withheld NEW runs are not used: only their names were counted.
- C3 is not executed.
- q20 is reported only as historical.

**Evidence labels.**
- **OBS**: observation (frame labels and monitor rows as recorded).
- **HYP**: physical interpretation (a hypothesis; melt bounding boxes alone never establish cavity morphology or causation).
- **PRED**: existing Week 18 out-of-fold predictions.
- **POST-HOC**: any target or analysis motivated by the observed NEW labels.

Code: `src/week19_*.py`. Run: `python -m src.week19_temporal_audit all`. All paths below are relative to this directory unless stated.

## 0. Answer in brief

1. **Provenance holds.** 22 of 24 checks pass; the other 2 are information only (`tables/CHECKS.csv`).
   - `has_keyhole` = "any frame with `label_final == 'Keyhole'`" reproduces 405/405 OLD runs (73 positive) and 136/136 NEW runs (124 positive, 12 negative).
   - The Week 7 OLD sequence audit is reproduced row for row (K frames, K segments, K/(F+C+K), label-sequence SHA-256).
   - Every one of the 140,594 labelled frames maps to exactly one `iter.dat` row (OBS).
   - The folder `DT` equals the median frame interval (ratio 1.000 ± 0.003). It is not the solver step: `timestep × DT` overstates monitor time by the iterations per frame (median 410 OLD, 567 NEW). Every time below therefore comes from `iter.dat` → `time.dat`.

2. **Keyhole followed by only Conduction exists in both campaigns, in two distinct forms (OBS, `tables/K_then_C_subgroups.csv`).** It occurs in 26 OLD runs (all in OLD partition `new-data`, which is not the October campaign) and 23 NEW runs.
   - **Fast scans (VX ≥ 0.85 m/s; OLD 10, NEW 11).**
     - A short Keyhole run is the first active label after Forming Phase: median K/(F+C+K) 0.043 OLD, 0.066 NEW.
     - It ends at about 0.47 ms, and Conduction follows for the rest of the track (about 318 frames).
   - **Slow scans (VX < 0.4; OLD 7, NEW 12).**
     - Keyhole runs for a long time, near the ~300 µm depth cluster.
     - The switch to Conduction comes only 15–21 frames (about 0.35 ms) before the fixed 2.1 ms recording end, while the scan is still incomplete (every recording ends before 90 % of the derived exit).
   - The timing is almost identical in OLD and NEW.

3. **Other sequence patterns (OBS).**
   - **Alternation** (an observed Conduction frame between Keyhole frames): 13 OLD runs (all partition `new-data`) and 9 NEW runs. Switches are bracketed to one frame interval (median about 7 µs).
   - **"K ongoing at observation end"**: 43/73 OLD and 98/124 NEW positives. It is mostly right-censored:
     - 28/43 OLD and 65/98 NEW recordings end before 90 % of the derived exit;
     - 36/43 and 77/98 have no Scanning Stopped or Solidifying Stopped frame at all.
     - It is never called persistent Keyhole.
   - **NEW does not have more transient Keyhole.** Median K/(F+C+K) among positives is 0.84 NEW vs 0.72 OLD. Positives below 10 %: 10/124 NEW vs 12/73 OLD.

4. **The 12 NEW negatives, individually (OBS; `tables/new_negatives_12_cases.csv`, `figures/fig5`).** 7 of the 12 reach the OLD reference threshold u_ref = 110.96 µm. Their accounts:
   - **H-f4fc937e86 — late-window maximum.** 312 µm, sustained after the derived exit, during frames labelled Scanning Stopped.
   - **H-e7dbd8e5ce — incomplete observation.** Bounds/time row mismatch, and only Initial Emptiness / Forming Phase labels.
   - **H-29cf03a279 — startup-related.** Its maximum lies inside the pipeline active interior but 25 frames before the first Conduction frame, i.e. during manual Forming Phase.
   - **Four fast-scan runs — unresolved.** Elevated depth (111.6–118.8 µm) 0–25 frames after the first Conduction frame:
     - persistent: H-b2eec677b1 (G3 persistent depth 111.9 µm, above u_ref);
     - transient: H-b302fc6cbd, H-2e066980ca, H-1d4ea0f649.
   - One positive lies below u_ref: H-349225d53c (88.8 µm). Its Keyhole frames all come after the 90 % cutoff, around and after the derived exit, at shallow monitored depth.

5. **Windows restore the ranking but not the OLD threshold level (OBS/POST-HOC, `tables/separability.csv`).**

   | NEW quantity | frozen whole-record max | A: active window | B: after first C/K frame (uses labels) |
   |---|---:|---:|---:|
   | AUC | 0.891 | 0.978 | 0.985 |
   | BA at the fixed OLD threshold | 0.704 | 0.769 | 0.814 |

   The descriptive NEW-only oracle thresholds are 148, 142 and 119 µm, against 111 µm on OLD. These are not held-out results.

6. **Like-for-like fast scans (OBS).**
   - The matched pair H-b302fc6cbd (negative) and H-b7e3ed2e12 (positive) has nearly identical inputs and depth traces (startup peak 115.6 vs 112.3 µm). The only difference is that 16 frames (about 76 µs) around the startup peak are labelled Keyhole in the positive and Conduction/Forming in the negative.
   - In the shared input region, frame spacing in spot-crossing units is the same in OLD and NEW (0.10–0.12). Frame sampling therefore does not explain the difference.
   - OLD has only 9 runs there (2 negatives), so a campaign effect cannot be separated from a region effect (consistent with erratum E18-3).

7. **E1 errors, from existing predictions only (PRED, `tables/oof_*`).** These are DEV repeats 1–8 at the final budget.
   - On R3_NEW, both models miss most negatives: specificity E1 0.385, G3 classifier 0.365.
   - E1's learned threshold rises to ≥ 200 µm (up to 309 µm) at some budget in 13 of the 32 folds whose paid pool contains H-f4fc937e86, and never otherwise.
   - In those folds E1 − G3 mean BA over budgets is −0.090. In the remaining folds it is +0.006 (R3_NEW overall −0.024).
   - POOLED is unaffected (learned threshold ≤ 118 µm).
   - This is an association in existing predictions, not a causal test.

8. **Verified pins and reference values.**
   - C3 (repeats 17–20) is unused: no cache file exists.
   - The historical DEV BA AULC reference values are reproduced: OLD 0.9443 / 0.9237 / 0.9299, POOLED 0.9474 / 0.9479 / 0.9499, NEW 0.6507 / 0.6713 / 0.6014 (E1 / G3 classifier / M3).

## 1. Provenance and reproduction (`tables/CHECKS.csv`, `provenance/`)

| Item | Verified value |
|---|---|
| Repository | `iso0/active-level-set-week1-warmup`. Local `main` = `origin/main` = `40580a6d` at start; work on branch `week19-temporal-audit`. No AGENTS.md exists; `.codex/` is untracked Codex tooling and is untouched. |
| OLD population | `outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv` (= `data/alse/population.csv`), sha256 `c15658ca…`; 405 runs, 73 positive; partitions new-data 164 (63), old-data-local 178 (8), old-data-remote-clean 63 (2) |
| OLD pin | `ioandanielc/sph_v2@b6dc254a2b607a31cb9f97b40990339c3d5ca1e8`. The 3 ledgers (407 experiments, 110,804 frames) are identical at `d69dac5b` and `2e1eec9c`. The 2 non-eligible OLD experiments are the documented `H-4ecd858c02` and `H-f4a4199ba7`. |
| NEW pin | `@2e1eec9c98fd57609d2815f174586336ab59da07`. `labels_new_data_4_prep.csv` is 12,397,054 B with SHA-256 `b45518a5…` (it is LFS: the tree OID is the pointer). 185 names = 136 eligible + 49 non-eligible; the 49 equal the Week 11 `bug_affected` set (`outputs/week11_bug_audit/simulation_bug_status.csv`). |
| Raw bytes | 2,168 files verified by size plus Git blob SHA-1 or LFS SHA-256 against the pinned trees:<ul><li>NEW: 272 downloaded, 273 reused (Week 18 cache);</li><li>OLD: 1,611 downloaded, 12 bounds files reused from the audit pin (byte-identical);</li><li>kinetic energy only for 20 focused cases.</li></ul>Manifests: `provenance/download_manifest*.csv`. |
| frames.csv | Rows, timesteps (order) and labels agree with the ledgers for 541/541 runs; `frame_idx` is contiguous |
| Timing | 0 unmatched or duplicate timesteps; `iter.dat`/`time.dat` rows equal and strictly increasing for all 541 runs. Frame interval median 7.46 µs OLD and 10.30 µs NEW (medians of per-run medians). |
| Reproduction | Whole-record maximum depth reproduces the frozen OLD (population) and NEW (`week18…/phase1/new_depth.csv`) values to 6e-14 µm. G3 persistent depth (404 OLD) and T0 depth (405) reproduce Week 7 to 6e-14 µm. Derived exit and 90 % cutoff reproduce to 1e-13 ms. |
| October audit spot checks | **H-f4fc937e86:**<ul><li>max 311.99990 µm at 2.042652 ms, after the derived exit at 1.270891 ms;</li><li>active-window max 110.75500 µm; G3 persistent depth 93.83694 µm;</li><li>≥ 300 µm in 18,065 rows, 3 episodes, longest 0.316815 ms.</li></ul>**H-29cf03a279:** max 131.19130 µm at 0.4303165 ms, inside the active window and adaptive interior; G3 persistent depth 119.66220 µm.<br>**H-e7dbd8e5ce:** max 144.97870 µm; 40,805 bounds vs 40,803 time rows; 33 IE + 17 F, no C/K. |
| OLD reference threshold | E1's learned-threshold rule (`src/week18_engine.py::DepthGPR.fit`) applied to all 405 OLD runs, which are not separable (min positive 111.198, max negative 111.584 µm):<ul><li>1-D logistic regression on log depth gives **u_ref = 110.964 µm**;</li><li>OLD BA at u_ref is 0.9985, equal to the best single-threshold BA.</li></ul>Engine default 111.0 and Week 18 count rule 111.2 are recorded (`provenance/old_reference_threshold.json`). The threshold is never tuned on NEW. |
| C3 | 0 cache files for repeats 17–20 anywhere under `outputs/week18_independent_research/` (verified, not executed) |
| DEV reference values | `outputs/week18_independent_research/phase3/depth3/aulc_real.csv`, mean over repeats 1–8, reproduced to 4 dp (§0, item 8) |

A compatibility note. Week 6's `rolling_distance_stat` assigns into `Series.to_numpy()`, which is read-only under
pandas 3 (copy-on-write). `src/week19_series.py::rolling_distance_median` reuses its indexer and constants and only
copies the array. Equivalence is established by C12 (the Week 7 G3 persistent depth is reproduced on all OLD runs).

## 2. Phase 1 — frame and time audit

**Definitions.**
- Frames are ordered by (timestep, source row), as in Week 7.
- A *K run* is a maximal block of consecutive Keyhole frames. Any other label ends it, including technical labels and Forming Phase. Runs are never joined across a gap.
- *K blocks* are K runs not separated by an observed Conduction frame. *Alternation* means two or more blocks.
- The *final active regime* is the label of the last C or K frame.
- Ratios:
  - K/(F+C+K), Week 7's fraction;
  - Ioan's K/(K+C), undefined (not 0) when K+C = 0. That happens for the two forming-only runs, one OLD and one NEW.
- Switches are bracketed between the two observed frames.
- Time-weighted fractions use frame-centred (midpoint) intervals over frames with mapped times. The denominator is the time covered by F+C+K frames (`FCK_time_covered_ms`). They agree with the frame fractions to ≤ 0.004 at the median.

**Counts (eligible runs only; `tables/temporal_registry.csv`).**

| | OLD (405) | NEW (136) |
|---|---:|---:|
| labelled frames | 110,357 | 30,237 |
| IE / F / C / K | 12,642 / 16,922 / 51,831 / 6,700 | 4,723 / 3,557 / 4,462 / 13,584 |
| SS / SoS / Screenshot Bug / Unsure | 16,432 / 5,055 / 773 / 2 | 2,702 / 1,209 / 0 / 0 |
| conduction only | 331 | 11 |
| K then C, no later K | 18 | 25 |
| alternating, terminal C | 12 | 1 |
| C then K, K at end | 9 | 2 |
| alternating, K at end | 1 | 8 |
| Keyhole only (no C frame) | 33 | 88 |
| forming only (no C/K) | 1 (`H-bf889bf790`, non-standard settings) | 1 (`H-e7dbd8e5ce`) |
| K followed only by C (subset) | 26 | 23 |
| K runs / runs touching the last frame | 124 / 36 | 145 / 77 |
| K→C switches (runs) / C→K switches (runs) | 77 (31) / 56 (22) | 43 (34) / 20 (11) |

**Where things occur in OLD.** All OLD transient or alternating cases lie in partition `new-data`. The 8 old-data-local positives all end in Keyhole (`C_then_K`).

**Anomaly flags** (kept, not excluded):
- Forming Phase after the first active frame: 12 OLD, 4 NEW;
- Initial Emptiness after physical onset: 8 OLD;
- maximum depth in the last bounds row: 3 OLD, 2 NEW;
- recording ends before 90 % of the derived exit: 167 OLD, 79 NEW. With the fixed TE = 2.1 ms this happens for VX below about 0.64 m/s.

**Alternative labels (new columns only; `tables/alternative_label_class_changes.csv`).** Only positives can change, from 1 to 0.

| Rule | OLD | NEW |
|---|---:|---:|
| K/(F+C+K) ≥ 5 % | 8 | 4 |
| K/(F+C+K) ≥ 10 % | 12 | 10 |
| K/(K+C) ≥ 5 % (1 undefined each) | 6 | 4 |
| K/(K+C) ≥ 10 % (1 undefined each) | 11 | 8 |

The changed runs are mostly fast-scan short-initial-K positives: all 10 in NEW, and 8 of 12 in OLD for K/(F+C+K) ≥ 10 %. The canonical `has_keyhole` is unchanged.

**Timing caveats.**
- Labels are frame-sampled. A transition is known only to lie between two frames: usually adjacent, median about 7 µs apart, at most 0.165 ms when Forming Phase frames intervene.
- "Last frame K" is reported as `last_frame_is_K` (36 OLD, 77 NEW). It is distinct from "K ongoing at observation end".

## 3. Phase 2 — transitions and input regions

- **Switch timing (simulation level; `tables/switch_timing_summary.csv`, `figures/fig3`).**
  - The first K→C switch of each run falls in the established active window for 30/31 OLD and 34/34 NEW runs.
  - It occurs at a median 0.38 (OLD) and 0.37 (NEW) of the derived exit time.
  - Late switches (after the 90 % cutoff) are 16/133 OLD and 10/63 NEW of all switches.
- **Two forms of K followed by only Conduction (`tables/K_then_C_subgroups.csv`, `K_then_C_cases.csv`).** These are described in §0, item 2. Medians:

  | | fast OLD | fast NEW | slow OLD | slow NEW |
  |---|---:|---:|---:|---:|
  | n | 10 | 11 | 7 | 12 |
  | K/(F+C+K) | 0.043 | 0.066 | 0.333 | 0.521 |
  | first K (ms) | 0.40 | 0.41 | 1.16 | 1.05 |
  | last K→C switch (ms) | 0.47 | 0.48 | 1.72 | 1.77 |
  | frames after the last K | 318 | 318 | 21 | 16 |
  | max depth (µm) | 129 | 119 | 288 | 304 |

- **Input concentration (`tables/input_region_by_VX.csv`).**
  - NEW covers P 350–450 W and LS 40–50 µm only.
  - Its negatives are 11/12 at VX ≥ 0.85 (the twelfth is the forming-only H-e7dbd8e5ce at 0.33).
  - In the bin VX ≥ 0.9, NEW holds 10 negatives and 10 positives.
  - In OLD the same bin holds 52 conduction-only runs and 8 positives, spread over P 73–449 W and LS 40–89 µm.
- **Common support (`tables/common_support_comparison.csv`, `fast_scan_common_support_cases.csv`).** The box is P 350.0–449.8 W, VX 0.209–0.986 m/s, LS 40.0–49.9 µm, ST 301.6–399.8 K.
  - NEW: 72 runs (64 positive); OLD: 40 runs (38 positive).
  - Fast scans inside the box:
    - NEW 13: 8 negatives, with active-window max 79–119 µm; 5 positives (all K→C), 112–148 µm, first K run 15–28 frames.
    - OLD 9: 2 negatives (99 and 112 µm; the 111.6 µm OLD negative H-1ef68d8f61 peaks 22 frames before its first Conduction frame); 7 positives, 116–157 µm.
  - Frame spacing × VX/LS is 0.10–0.12 in both campaigns there.
- **Representative cases (deterministic rule; `tables/representative_cases.csv`, `figures/fig6`).** The rule picks the run closest to its group median. The table also holds the verified matched pair. H suffixes are shown for brevity; several are shared by other runs (for example `H-c87ffcf9e3` by 10), so the full names are in the table.
  - K then C: OLD `H-1d842653b1`, NEW `H-b924a3dcb1`.
  - Alternating: OLD `H-eac21b41c2`, NEW `H-6ca7f366ce`.
  - K at end: OLD `H-c87ffcf9e3` (VX 0.315), NEW `H-349225d53c`.
  - Conduction only: OLD `H-c5f6eebf67`.
  - Matched pair: NEW `…H-b302fc6cbd` (negative, VX 0.960) and NEW `…H-b7e3ed2e12` (positive, VX 0.953). This pair is verified by full name. H-b302fc6cbd also names a different NEW positive (VX 0.502).
  - Kinetic energy (melt subset, J → nJ) is shown for these cases only. It is not absorbed laser energy, and its row counts equal time rows for all 20 downloaded cases (`tables/kinetic_energy_row_check.csv`).
- **Frame-level depth versus label (OBS; `tables/frame_level_map.csv.gz`).** This uses depth at the exact monitor row of each labelled frame. Frames are not independent, so only simulation-level conclusions are drawn.
  - K-frame vs C-frame AUC: 0.993 OLD, 0.978 NEW.
  - Simulations with a Conduction frame at or above u_ref: 26/371 OLD vs 26/47 NEW.
  - In 4 NEW negatives, C-labelled frames reach u_ref: H-b2eec677b1 4.8 %, H-2e066980ca 2.1 %, H-1d4ea0f649 1.6 %, H-b302fc6cbd 0.6 % of their C frames.

## 4. Phase 3 — depth definitions (no model training)

| Definition | Window (derived unless noted) | Uses manual labels | Coverage |
|---|---|---|---|
| frozen | whole-record maximum of valid bounds rows (E1 target, unchanged) | no | 541/541 |
| A | valid rows with t ≤ min(recording end, 0.90 × derived exit); startup retained | no | 540 (H-e7dbd8e5ce: bounds/time mismatch) |
| B | A after the first Conduction/Keyhole frame | **yes** (POST-HOC, exploratory) | 539 (no C/K frame in the two forming-only runs) |
| C: G3 persistent depth | max of the 50 µm trailing rolling median of depth in the adaptive interior | no | 537 |
| C: T0 depth | median over the final 20 % of the active window | no | 540 |
| D | time with depth ≥ u_ref, in four windows (whole, A, B, interior). Hold rule: each valid row holds its value until the next row; invalid rows count nowhere. | B window: yes | 539–540 |

Units are µm for depth and ms for time. Failure reasons are in the `failure` and `record_flags` columns of `tables/depth_definitions.csv`.

**Separability** (`tables/separability.csv`; full population, unchanged eligibility):

| Definition | OLD AUC | OLD BA at u_ref | NEW AUC | NEW BA at u_ref (FP / FN) | NEW at OLD rule threshold | NEW oracle (same population, descriptive) |
|---|---:|---:|---:|---:|---:|---:|
| frozen | 0.99996 | 0.9985 | 0.891 | 0.704 (7 / 1) | 0.704 | 0.914 at 147.8 µm |
| A | 0.99996 | 0.9985 | 0.978 | 0.769 (5 / 1) | 0.723 | 0.960 at 142.2 µm |
| B (labels) | 1.0000 | 1.0000 | 0.985 | 0.814 (4 / 1) | 0.769 | 0.984 at 119.2 µm |
| G3 persistent depth | 0.994 | 0.938 | 0.966 | 0.880 (2 / 7) | 0.802 | 0.955 at 133.0 µm |
| T0 depth | 0.973 | 0.781 | 0.963 | 0.907 (0 / 23) | 0.898 | 0.940 at 90.7 µm |
| D, fraction above u_ref (active window) | 0.99996 | — | 0.978 | — | 0.765 | 0.968 |

- "OLD rule threshold" applies E1's learned-threshold rule to OLD values of that definition only: 110.5 (A), 104.8 (B), 101.0 (G3 persistent depth), 86.5 (T0). For D it is OLD's best single threshold.
- Excluding incomplete records (bounds/time mismatch, unmappable timing, no C/K label) changes little: NEW frozen AUC 0.889.
- Additionally excluding the 246 recordings that end before 90 % of the derived exit leaves 57 NEW runs, for which the frozen AUC is 0.843. The early-ending recordings are the slow scans and hold most positives.

**The 12 NEW negatives** (`tables/new_negatives_12_cases.csv`). Each row lists ID, inputs, labels, timing, all definitions and a mechanism category relative to u_ref.

| H | VX | max (µm) | where | A | B | G3 persistent depth | category |
|---|---:|---:|---|---:|---:|---:|---|
| f4fc937e86 | 0.954 | 312.0 | after derived exit; Scanning Stopped frames; ≥ 300 µm for 18,065 rows | 110.8 | 110.8 | 93.8 | late-window maximum |
| e7dbd8e5ce | 0.332 | 145.0 | last bounds row; rows 40,805 vs 40,803; IE/F labels only | — | — | — | incomplete observation (not established Conduction) |
| 29cf03a279 | 0.912 | 131.2 | active interior, 25 frames before the first C frame | 131.2 | 90.3 | 119.7 (event also before the first C frame) | startup-related; also above u_ref in G3 persistent depth |
| b2eec677b1 | 0.970 | 118.8 | active, 2 frames after the first C frame | 118.8 | 118.8 | 111.9 | **unresolved**: persistent elevation after the first C frame |
| b302fc6cbd | 0.960 | 115.6 | active, at the first C frame | 115.6 | 115.6 | 99.0 | **unresolved**: transient |
| 2e066980ca | 0.899 | 115.1 | active, 20 frames after the first C frame | 115.1 | 115.1 | 107.0 | **unresolved**: transient |
| 1d4ea0f649 | 0.904 | 111.6 | active, 25 frames after the first C frame | 111.6 | 111.6 | 107.2 | **unresolved**: transient |
| be08daa72c | 0.919 | 107.3 | 2 frames before the first C frame | 107.3 | 87.2 | 95.3 | below u_ref |
| 210d3fce7d | 0.978 | 98.7 | 2 frames before the first C frame | 98.7 | 86.7 | 86.4 | below u_ref |
| 3172b413b1 | 0.980 | 90.8 | 8 frames before the first C frame | 90.8 | 82.7 | 86.4 | below u_ref |
| 6f28bdc6c9 | 0.961 | 88.5 | after derived exit | 79.4 | 79.4 | 78.9 | below u_ref |
| ce04be44b1 | 0.965 | 87.3 | recording ends at 0.44 ms (35 % of exit); 14 C frames | 87.3 | 87.3 | 74.7 | below u_ref; short recording |

All 12 are `technical_usability_status = KEEP` with `bug_free = correctly_finished = 1`. Those fields do not establish complete observation.

**Accounting** (relative to u_ref; `tables/new_negatives_mechanism_summary.csv`):
- 7 disagreements:
  - 1 late-window maximum;
  - 1 incomplete observation;
  - 1 startup-related (manual forming window);
  - 4 unresolved elevated depth after the first Conduction frame (1 persistent, 3 transient).
- 5 agree.

**Positives** (`tables/positives_below_uref_by_definition.csv`):
- Under the frozen, A and B definitions, only H-349225d53c is below u_ref:
  - its 117 K frames span 1.229–1.805 ms, after the 90 % cutoff (1.112 ms) and across the derived exit (1.235 ms);
  - the monitored depth at those frames has median 23 µm and maximum 88 µm.
- Under G3 persistent depth, 9 OLD and 7 NEW positives fall below u_ref: the fast-scan short-K positives and three non-standard OLD runs `…H-fb250c7cf9`.

## 5. Relation to E1 errors (PRED, existing out-of-fold predictions only)

**Data.** Week 18 DEV, repeats 1–8 × 5 folds.
- E1 = `GPR_depth|mlii|straddle` (full depth; `phase3/depth3/cache_real`); reference = G3 classifier + margin (`phase2/cache_real`).
- Each DEV run is predicted once per repeat (C20).
- Final budget: B80 for R3_NEW, B120 for R3_OLD and R1_POOLED.
- BA is pooled over all OOF predictions, threshold p ≥ 0.5.
- Bins use K/(F+C+K); the K/(K+C) bins are in the same file. The short-K bins contain only positives, so no two-class BA is computed inside them.

| Task / arm | BA | specificity, negatives (sims) | sensitivity (0, .05) | sensitivity [.05, .10) | sensitivity [.10, 1] |
|---|---:|---:|---:|---:|---:|
| R3_NEW E1 | 0.668 | 0.385 (12) | 0.719 (4) | 0.708 (6) | 0.970 (114) |
| R3_NEW G3 | 0.661 | 0.365 (12) | 0.750 (4) | 0.542 (6) | 0.987 (114) |
| R3_OLD E1 | 0.955 | 0.973 (332) | 0.828 (8) | 0.906 (4) | 0.955 (61) |
| R3_OLD G3 | 0.935 | 0.988 (332) | 0.781 (8) | 0.625 (4) | 0.912 (61) |
| R1_POOLED E1 | 0.949 | 0.951 (344) | 0.771 (12) | 0.763 (10) | 0.971 (175) |
| R1_POOLED G3 | 0.958 | 0.969 (344) | 0.781 (12) | 0.813 (10) | 0.966 (175) |

Denominators and IDs: `tables/oof_diagnostics_by_K_fraction.csv`. Per-run error rates: `tables/oof_per_simulation_final_budget.csv`.

**Learned threshold (`tables/oof_E1_threshold_pull_by_fold.csv`).** The cached `u` shows the threshold E1 actually used at each budget.
- On R3_NEW it reaches ≥ 200 µm (up to 309.3 µm) only when H-f4fc937e86 is in the paid pool: 13/32 such folds, 76 budget steps; 0/8 folds with it in the test set.
- Mean BA over budgets, E1 − G3:

  | R3_NEW folds | E1 − G3 |
  |---|---:|
  | threshold pulled (12 with defined BA) | −0.090 |
  | not pulled (18) | −0.017 |
  | H-f4fc937e86 in test (8) | +0.058 |
  | all except the pulled folds | +0.006 |
  | overall (38 with both classes in test) | −0.024 |

- On R1_POOLED the learned threshold stays at 110–118 µm and E1 − G3 is −0.0005.

**Reading.**
- This is a strong association between one record's late-window maximum and E1's NEW deficit.
- The set of pulled folds depends on E1's own queries. No intervention (for example, E1 with target A) was run, and none is allowed in this audit.
- Most of the elevated fast-scan negatives (§4) are misclassified by both models, so they are not specific to E1. H-29cf03a279, H-b2eec677b1, H-2e066980ca and H-1d4ea0f649 have R3_NEW error rates of 0.75–1.0 for both E1 and G3; H-b302fc6cbd has 0.25 (E1) and 0.625 (G3).

## 6. Hypotheses (HYP; none established by bounding boxes)

1. **Startup transient.** In fast scans, a startup depth peak of 110–150 µm at the end of Forming Phase is sometimes annotated as a short Keyhole and sometimes as Forming/Conduction. The monitored peak depths overlap for 110–120 µm. Whether a vapour depression formed cannot be read from melt bounds; it needs the frame images (front/side/top PNG paths in `frames.csv`) and Ioan's labelling criterion.
2. **End-of-track events, in opposite directions.**
   - H-f4fc937e86: a post-exit, Scanning-Stopped deep excursion with no Keyhole label.
   - H-349225d53c: post-cutoff Keyhole labels at shallow monitored depth.
   - Both lie outside the pipeline active window. The bounding-box length jumps to about 1.4 mm after the exit in several NEW runs (`figures/fig6`), so melt-flagged particles away from the pool may enter the bounds. To be checked with images.
3. **A ~300 µm depth ceiling.** The tight cluster of positive maxima at 301–305 µm (both campaigns) suggests a geometric limit, such as the substrate or domain depth. It is not verified here: the domain z-extent is not in the folder parameters read so far.
4. **Campaign versus region.** OLD's perfect max-depth separation may partly reflect sparse OLD sampling of the fast, high-power, small-spot region (9 runs). The data cannot distinguish a campaign effect from a region effect.

## 7. Limitations

- Frame sampling bounds every transition time; episode durations are first-to-last labelled frame, with no extrapolation.
- Monitor rows are not independent experiments. All counts are per simulation.
- B and the post-forming window D depend on manual labels and are POST-HOC. Any target chosen from these results (A, B, a VX-dependent threshold) would be post-hoc with respect to the NEW labels.
- NEW negatives are 12 runs; percentages are fragile.
- G3 persistent depth and T0 for NEW are new computations with the Week 7 definitions. They were not previously in the repository.
- Kinetic energy was downloaded for 20 focused cases only.
- The OOF analysis uses DEV predictions at existing budgets. "Mean BA over budgets" in the fold-level analysis is a simple average, not the trapezoid AULC.

## 8. Next decisions (for the owner; nothing here is frozen)

1. **Ask Ioan, with the frame images** of the 12 negatives, the matched pair and H-349225d53c:
   - how are the startup peak frames and the Scanning-Stopped frames judged;
   - should end-of-track frames count toward `has_keyhole`?
2. **If a depth target change is wanted** (for example, A instead of the whole-record maximum, which removes the 312 µm late event and the threshold pull):
   - develop it on DEV only;
   - pre-register it;
   - spend C3 once.
   - Its motivation is POST-HOC.
3. **Keep the NEW claims scoped.** Report NEW as "label not a whole-record depth threshold; partly explained by windows; 4/12 fast-scan negatives unresolved".
4. **Optionally verify the domain depth** (parameters.json z-extent) to test hypothesis 3. This needs no labels.

## 9. Corrections to earlier wording (historical files unchanged)

- **H-f4fc937e86.** Week 18 `DATA_AUDIT.md` (amendment 2) calls its maximum "an end-of-domain spike (312 µm at 97 % of the run)". It is a sustained post-exit elevation: ≥ 300 µm in 18,065 rows over three episodes, the longest 0.317 ms, during Scanning Stopped frames.
- **OLD AUC.** "OLD AUC 1.000" is 0.99996 unrounded. One OLD negative (H-1ef68d8f61, 111.58 µm) exceeds the minimum positive (111.20 µm), and its maximum occurs 22 frames before its first Conduction frame.
- **H-29cf03a279.** The October audit's "maximum inside the active interior" is correct for the pipeline windows. The maximum also precedes the first Conduction frame, i.e. it falls in the manually labelled Forming Phase.

## 10. Evidence paths

| Topic | Path (in this directory unless stated) |
|---|---|
| Registry and frames | `tables/temporal_registry.csv`, `tables/frame_level_map.csv.gz` |
| Runs and switches | `tables/k_runs.csv`, `tables/regime_switches.csv` |
| Phase 2 | `tables/descriptor_counts.csv`, `tables/K_then_C_subgroups.csv`, `tables/common_support_comparison.csv`, `tables/fast_scan_common_support_cases.csv` |
| Phase 3 | `tables/depth_definitions.csv`, `tables/separability.csv`, `tables/new_negatives_12_cases.csv` |
| Predictions | `tables/oof_*` |
| Checks and provenance | `tables/CHECKS.csv`, `provenance/*` |
| Figures | `figures/fig1_descriptors_by_group.png` … `fig6_representative_cases.png` |
| Raw files | `data/raw/sph_v2/<revision>/<simulation>/…` (repository root, git-ignored), listed in `provenance/download_manifest.csv` |
