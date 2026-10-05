# Week 18+ research log (resume point for "continue")

Start: 2026-10-05, main = `bbb79eaf` (Week 17). Deadline context: thesis due 15 Dec; research until ~mid-Nov.

## Status board
| Phase | State | Pointer |
|---|---|---|
| 0 Re-ground / red-team | in progress | RED_TEAM.md, this log |
| 1 Data foundation | in progress | DATA_AUDIT.md |
| 2 Benchmark redesign | not started | BENCHMARK_SPEC.md |
| 3 Research loop | not started | ATTEMPT_LEDGER.md |
| 4 Theory | not started | THEORY_WEEK18.md |
| 5 Confirmation | 0 rounds used | FREEZE_ROUND_k.md |

## Open decisions for the owner
- D1. NEW continuous targets (depth/width) need the NEW monitors from Hugging Face `ioandanielc/sph_v2`
  (download = permission required). Not downloaded. OLD continuous targets are in the repository.

## Log
- 2026-10-05 Phase 0: sim_id fields parsed. OLD-405 mixes simulator settings: 41 runs TE = 0.00125 s
  (vs 0.0021), 27 runs with a different domain (XI −0.0002 / XF 0.0012 / XL 0.0014); time-step rule
  DT·VX/LS ≈ 0.075 (0.04–0.12) in OLD vs 0.108 (0.097–0.120) in NEW. OLD-405 = three partitions
  (new-data 164 rows / 63 KH; old-data-local 178 / 8; old-data-remote-clean 63 / 2). NEW homogeneous.
  Labels: has_keyhole = any frame labelled Keyhole (frame-level labels), so run length can matter.
  49 Bug simulations: Screenshot-Bug frames late in the run, eligibility UNRESOLVED → stay out.
- 2026-10-05 Phase 1: has_keyhole = 1[max depth ≥ ≈111 µm] on OLD (AUC 1.000); NEW has no continuous
  targets in the repo (D1). Compatibility: labels agree in the overlap; log-h "level shift" is a region effect
  (thresholds 20.91 OLD-in-NEW-box vs 20.94 NEW-in-OLD-box); no campaign offset under a flexible GPC (+0.001
  nats). POOLED (541) adopted as primary real benchmark, POOLED_STD (500) as sensitivity. DATA_AUDIT.md.
- 2026-10-05 Open item (a) resolved (`phase0/new_hyper_seed_factorial*`): margin BA AULC ≈ 0.66 under fixed
  OLD hypers and per-step ML-II and both seed schemes; random gains +0.023–0.026 from ML-II; random − margin
  −0.022/−0.003 (fixed; W15/W17 seeds) vs +0.002/+0.020 (ML-II). The NEW exception = ML-II × random-design
  interaction + seed noise; margin is not hyperparameter-limited.
- 2026-10-05 Items (b)–(d) recorded in ERRATA.md / RED_TEAM.md.
- 2026-10-05 Phase 2: BENCHMARK_SPEC.md locked (tasks R1/R1_STD/R2/R2rev/R3_NEW/R3_OLD, S1 twins, S2 stress;
  blocks DEV 1–8, C1 9–12, C2 13–16, C3 17–20; metrics incl. queries-to-target). Twin truths fitted to the 541
  pooled labels (agreement 0.946–1.000; T_NW/T_QL nearly erase NEW's rare pocket). Baseline reproduction on DEV
  launched (`src/week18_baselines.py`, caches `phase2/cache_*`).
