# Week 18 data audit (Phase 1)

Sources: `outputs/week12_startup_and_transfer_development/audit/{old405_inputs_labels,new136}.csv`,
`outputs/week7_06_real_data_boundary_active_level_set/primary_common_population.csv` (OLD continuous targets),
`docs/alse/data.md`, `outputs/week11_bug_audit/`, `outputs/week11_new_data_arrival_audit/`. Code:
`src/week18_data_audit.py`. All real-data statements are POST-HOC (NEW) / HISTORICAL (OLD), descriptive.

## 1. Simulator settings and label definition
- Same material (Ti64) everywhere. Label `has_keyhole` = any frame manually labelled Keyhole (frame-level
  labels aggregated per run).
- **OLD-405 is not homogeneous.** 364 runs: TE = 0.0021 s, domain XI 0.0002 / XF 0.0014 / XL 0.0012 ("standard",
  identical to all 136 NEW runs). 14 runs: TE = 0.00125 s, standard domain (0 Keyhole). 27 runs: TE = 0.00125 s,
  domain XI −0.0002 / XF 0.0012 / XL 0.0014 (3 Keyhole). These 41 runs sit at low power (median P 100–157 W).
- **Time-step rule differs:** DT·VX/LS ≈ 0.075 (1–99%: 0.042–0.119) in OLD vs 0.108 (0.097–0.120) in NEW.
- OLD-405 combines three acquisition partitions: "new-data" 164 runs (63 Keyhole, median P 266 W),
  old-data-local 178 (8, P 151 W), old-data-remote-clean 63 (2, P 162 W); prevalence differences follow input coverage.
- Ranges: OLD P 53–450 W, VX 0.20–1.00 m/s, LS 40–90 µm, ST 300–400 K; NEW P 350–450 W, VX 0.21–0.99, LS 40–50 µm,
  ST 302–500 K. 72/136 NEW runs lie inside the OLD bounding box; 40 OLD runs (38 Keyhole) inside the NEW box.

## 2. Is the label a threshold of a continuous output? (OLD; continuous targets exist for all 405 OLD runs)
| Output | AUC for has_keyhole | best single-threshold BA |
|---|---:|---:|
| max depth (µm) | **1.0000** | **0.9985** (≈ 111 µm) |
| persistent depth (G3_persistent_depth_um) | 0.9941 | 0.9795 |
| persistent depth/width ratio | 0.9945 | 0.9764 |
| T0 depth | 0.9730 | 0.9092 |
| widths | 0.55–0.67 | 0.60–0.66 |
Every Keyhole run has max depth ≥ 111.2 µm and every non-Keyhole run ≤ 111.6 µm, in every partition and settings
group. **The binary label is, to within one run, the level set {max depth ≥ ≈ 111 µm}.** Max depth is bimodal
(median 63 µm, 90th percentile 274 µm; only 2.7% of runs within ±10% of 111 µm): the regime change is a jump,
but conduction-side depth carries distance-to-transition information.
Week 7 Phase 6 already compared a max-depth GPR level-set formulation with binary GPC on OLD: BA AULC 0.943 vs
0.917 (+0.026, paired interval [+0.011, +0.043]); q20 error 0.205 vs 0.186 (interval crosses 0); verdict "HYBRID /
NO CLEAR WINNER", partly because of an inter-partition transfer floor. **NEW has no continuous targets in the
repository**: the sealed NEW file contains labels only; the NEW monitors exist in the Hugging Face dataset
`ioandanielc/sph_v2` (download requires the owner's permission — open decision D1).

## 3. OLD/NEW compatibility
- Overlap: an OLD-trained G3 agrees with 94.4% of the 72 NEW labels inside the OLD box (KH-majority baseline
  88.9%; non-KH recall 4/8) and 92.2% outside (baseline 93.8%; 1/4).
- **"Level shift" is a region effect.** Physics-only logistic thresholds in log h: OLD 20.69 (standard runs
  20.70); NEW 20.82; **NEW inside the OLD box 20.94 vs OLD inside the NEW box 20.91**; NEW outside 20.41. Where
  the campaigns overlap they agree; the log-h threshold changes across the input space. Week 17's "physics level
  moved between campaigns" (20.69 → 20.82) compares different regions.
- **No campaign effect under a flexible model.** Pooled GPC evidence: G3 −69.922; + NEW random intercept −69.921
  (offset variance 0.06 vs latent amplitude 96); + NEW-specific residual surface −69.495.
- Pooled 5-fold CV (4 repeats, stratified by campaign × class): OLD BA ≈ 0.93–0.95 for every pooled variant;
  NEW predictions are dominated by fold-partition noise (per-repeat paired differences up to ±0.19 BA; 12 rare
  cases); a NEW random intercept changes nothing; OLD-only training ranks NEW at least as well as pooled training
  (AUC +0.04 on standard runs).
- **Decision:** POOLED = OLD ∪ NEW (541 runs, 33.6% Keyhole) is a legitimate primary real benchmark; POOLED_STD
  (500 runs, the 41 non-standard OLD runs removed) is a sensitivity analysis.

## 4. Withheld Bug simulations
49 of the 185 NEW runs contain "Screenshot Bug" frames starting 57–99% into the run (median 82%); eligibility was
never resolved (`outputs/week11_bug_audit/bug_audit_summary.json`: usability UNRESOLVED). They remain excluded
from every benchmark and test.

## Amendment 2026-10-05 (after Astra Round 3; original text above kept)
§3's "level shift is a region effect" is overstated — see ERRATA E18-3: 1-D log-h threshold shift NEW − OLD
+0.17 [0.03, 0.29] overall, +0.01 [−0.14, 0.28] in the overlap (2 + 8 non-Keyhole runs). Campaign shift and region
effect are not distinguishable with these data; the pooled 4-D GPC needs no campaign offset.
