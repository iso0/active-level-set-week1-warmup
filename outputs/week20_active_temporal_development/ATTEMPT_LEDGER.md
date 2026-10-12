# Week 20 attempt ledger (post-hoc DEV research)

Every execution that fits a model, computes acquisition paths or evaluates results is listed. Runs whose outputs were thrown away are listed too.

**Fit accounting:**
- **Caps:** 15,000 scalar learner fits; 160 temporal or functional fits; ≤ 4 CPU threads; ≤ 8 GiB; ≤ 8 h in total.
- **Scope:** C3 (repeats 17–20) is reserved and unused. No simulator job, no label change, no exclusion change.

| # | UTC | What ran | Scalar fits | Temporal/functional fits | Outputs | Notes |
|---|---|---|---:|---:|---|---|
| M1 | 2026-10-12 | `python -m src.week20_track1_al manifest`: builds the 60 task-folds and checks responses and labels against the Week 19 inputs; no fit | 0 | 0 | `track1/manifest_track1.json`, `track1/HYPOTHESES_TRACK1.md` | Committed and pushed before any Track 1 fit. |
| T1-0 | 2026-10-12 | Track 1 runner on R3_NEW repeat 1 fold 1, all three arms, to time the runs and check fidelity. Kept as part of the frozen run (cached). | 219 | 0 | `_cache/track1` | Fidelity: max \|Δp\| vs Week 18 caches 5e-6. |
| T1-1 | 2026-10-12 | `python -m src.week20_track1_al run 4`: the remaining 177 runs, 4 workers × 1 thread, 6.4 min, worker peak 0.24 GiB, all `ok` | 12,882 | 0 | `_cache/track1`, `provenance/track1_run_log.jsonl` | Cumulative scalar fits: 13,101. The log field `started_utc` records the time the log was written (end of run). |
| T1-A | 2026-10-12 | `python -m src.week20_track1_analysis`: curves, AULC, contrasts, QTT and fidelity; no learner fit. | 0 | 0 | `track1/*.csv`, `track1/figures/` | Post-hoc additions, marked POSTHOC in file names: episode table; sustained-crossing QTT; 11 one-dimensional threshold-rule recomputations with the late negative's value set to its A. These are not learner fits. |
| T2-D | 2026-10-12 | `python -m src.week20_track2_data extract` and `python -m src.week20_track2_models prep`: native NEW trajectories (135; native maximum = A to 1.7e-13 µm), compression errors, the training-only resolution rule (K = 360 at all 30 checkpoints) and checkpoint files | 0 | 0 | `track2/trajectory_inventory.csv`, `track2/compression_error_all_runs.csv`, `track2/checkpoints.csv` | No model fitted. |
| M2 | 2026-10-12 | `python -m src.week20_track2_models manifest`: Track 2 methods, hypotheses T2-H1..H8 and fit accounting | 0 | 0 | `track2/manifest_track2.json`, `track2/HYPOTHESES_TRACK2.md` | Committed and pushed before any Track 2 fit. Environment: `.venv` (git-ignored) with torch 2.13.0+cpu and gpytorch 1.15.1, built on the system site packages; numpy inside it is 2.4.6, so sklearn models run with the system Python. |
| T2-S | 2026-10-12 | Track 2 fits in progress: scalar refits (30; equal to the pilot to 7e-15), functional baseline (30 checkpoints × 3 coefficient GPs = 90), SVGP validation (2 fits), separable SVGP (30, running) | 30 | 92 (+30 running) | `track2/scalar_reference_fits.csv`, `track2/functional_fits.csv`, `track2/svgp_validation.json`, `track2/svgp_fits.jsonl` | Cumulative scalar fits: 13,131. |
| PS | 2026-10-12 | POST-START declaration `track2/POSTSTART_DECLARATION.md`: T2-PS1, 6000-iteration SVGP at the five repeat-1 B40 checkpoints, 5 fits | 0 | 0 | — | Based on training-loss traces of 2 finished fits only; no held-out result seen. |
