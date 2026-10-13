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
| T2-S | 2026-10-12 | Track 2 fits: scalar refits (30; equal to the pilot to 7e-15), functional baseline (30 checkpoints × 3 coefficient GPs = 90), SVGP validation on the controlled example (2 fits) | 30 | 92 | `track2/scalar_reference_fits.csv`, `track2/functional_fits.csv`, `track2/svgp_validation.json` | Cumulative scalar fits: 13,131. |
| PS | 2026-10-12 | POST-START declaration `track2/POSTSTART_DECLARATION.md`: T2-PS1, 6000-iteration SVGP at the five repeat-1 B40 checkpoints, 5 fits | 0 | 0 | — | Based on training-loss traces of 2 finished fits only; no held-out result seen. |
| ER | 2026-10-12 | POST-START evaluation rules `track2/EVALUATION_RULES_T2.md` and the evaluation script `src/week20_track2_eval.py`, committed while the SVGP fits ran (5 of 30 done) | 0 | 0 | — | Fixes the decision rule for each frozen hypothesis and adds descriptive metrics marked ADDED. Before writing it, one label-free check: 0 of 233,910 observed held-out bins lie outside training support. No held-out prediction scored or viewed. |
| T2-V | 2026-10-12 | `.venv/Scripts/python.exe -m src.week20_track2_svgp fit`: the 30 frozen separable-SVGP fits (2000 iterations, M = 400), one process with 4 torch threads, run alone; exit 0, no failure, no restart | 0 | 30 | `track2/svgp_fits.jsonl`, `_cache/track2/predictions/svgp_*.npz`, `provenance/svgp_fit_stdout.log` | 82.5 min in total (median 166 s per fit, max 208 s); peak memory 0.6 GiB. Training-loss change over the last block: median −0.033 (range −0.044 to −0.015), still falling. Cumulative temporal/functional fits: 122. |
| T2-F | 2026-10-12 | `.venv/Scripts/python.exe -m src.week20_track2_svgp fidelity`: the frozen M = 800 inducing-point check at `ckpt_r1_f1_B40`, 2000 iterations, run alone | 0 | 1 | `_cache/track2/predictions/svgp_M800_ckpt_r1_f1_B40.npz`, `provenance/svgp_fidelity_stdout.log` | 505 s; peak 0.52 GiB; exit 0. Cumulative temporal/functional fits: 123. |
| T2-P | 2026-10-12 | `.venv/Scripts/python.exe -m src.week20_track2_svgp_poststart`: POST-START T2-PS1, the same SVGP with 6000 iterations at `ckpt_r1_f{1..5}_B40`, run alone, as declared in `05c4b0cf` | 0 | 5 | `_cache/track2/predictions/svgp_it6000_*.npz`, `provenance/svgp_poststart_stdout.log` | 32 min (median 384 s per fit); peak 0.44 GiB; exit 0. Cumulative temporal/functional fits: **128 of 160**. |
| EV1 | 2026-10-12 | `python -m src.week20_track2_eval`: first evaluation of all Track 2 predictions, after all 128 fits had finished | 0 | 0 | `track2/evaluation_per_run.csv.gz`, summary tables, verdicts, figures, `provenance/track2_eval_stdout.log` | 14 s. **Bug found:** the named-run table and figure looked runs up by H suffix, which is not unique (NEW: 136 runs, 88 suffixes; H-b302fc6cbd is shared by G5 and a slow-scan positive). The matched-pair analysis already used full sim IDs. |
| EV2 | 2026-10-12 | Evaluation re-run after the fix (named runs by full sim ID), with `NAMED_RUNS.csv` and the POST-HOC diagnostics added | 0 | 0 | as EV1 + `NAMED_RUNS.csv`, `track2/POSTHOC_*.csv` | Versus EV1, 20 of the 22 output files are byte-identical. `named_runs_predictions.csv` changed; `evaluation_per_run.csv.gz` changed only in its gzip timestamp (every table derived from it is byte-identical); the figure picks happened to be right in EV1. The POST-HOC functional-failure diagnosis recomputes the frozen deterministic ALS basis for the 30 checkpoints, plus 3 ad-hoc recomputations before this run. These are diagnostic recomputations of an intermediate quantity of the frozen fits, with no coefficient-GP fit, and are not counted as new fits. |
| EV3–4 | 2026-10-12 | Evaluation re-runs for presentation and POST-HOC tables: log-scale and clipped figure axes; terminal-invalid-rows sensitivity; well-posed-checkpoint comparison; gzip with a fixed timestamp | 0 | 0 | `track2/figures/*.png`, `track2/POSTHOC_*.csv`, `provenance/track2_eval_run{2,3,4}_stdout.log` | Every frozen-evaluation table is byte-identical to EV1. |

**Totals at the end of this round:**
- **Scalar learner fits:** 13,131 of 15,000.
- **Temporal/functional fits:** 128 of 160. These are 90 functional coefficient GPs, 2 validation fits, 30 frozen SVGP fits, 1 fit with M = 800 and 5 post-start fits.
- **CPU and memory:** the fitting and evaluation jobs ran one at a time with at most 4 threads (Track 1: 4 workers × 1 thread; SVGP: 4 torch threads). A few short single-thread checks (file reads and the label-free support check) ran beside the SVGP job. Peak memory per process was 0.6 GiB.
- **Wall time:** the request arrived at 19:45 UTC; the last evaluation ended at 22:41 UTC, about 3.0 h of the 8 h limit.
- **Restarts and discarded runs:** none.

## Continuation round (2026-10-13): Track 1 extension on DEV repeats 5–8

**Request.** "gerekli adımlara devam et" ("continue with the necessary steps"). This round runs the next experiment recommended in DEVELOPMENT_REPORT.md.

**Caps (assumed):**
- The Week 20 limits apply afresh to this round: ≤ 15,000 scalar learner fits, ≤ 4 threads, ≤ 8 GiB, ≤ 8 h.
- The round is counted separately from the Week 20 round, and cumulative totals are reported.
- C3 stays unused.

| # | UTC | What ran | Scalar fits | Temporal fits | Outputs | Notes |
|---|---|---|---:|---:|---|---|
| X-M | 2026-10-13 | `python -m src.week20_track1_ext manifest`, run twice: the second run adds the analysis-module hash. No fit. | 0 | 0 | `track1_ext/manifest_track1_ext.json`, `track1_ext/HYPOTHESES_TRACK1_EXT.md`, `track1_ext/startup_checks.csv` | The historical WHOLE/G3 expectations come from the Week 18 caches, which are already-known results. The startup checks use paid labels only, through the protocol's own startup. Committed and pushed before any extension fit. |
