# PHYSICAL_PILOT (pilot B) — learning physical outputs from x = (P, VX, LS, ST)

**Status: REGISTERED BEFORE ANY SUMMARY WAS COMPUTED** (owner request of 2026-10-16: learn energy, temperature and flow outputs from the four inputs, judged by prediction error).
- **Code:** `src/jdl_physical_pilot.py`.
- **Manifest:** `PHYSICAL_MANIFEST.json`.
- **Data:** the pinned NEW monitors `ioandanielc/sph_v2 @ 2e1eec9c`, 952/952 files verified (`provenance/`).

## Starting point and the new question

- **Starting point.** Weeks 6/7 learned steady-state T0 summaries on the OLD-era data (`sph_v2 @ d69dac5b`, 165 runs) with a Matérn 3/2 + learned-nugget GP: KE R² 0.89 (relative RMSE 16.8%), depth 0.91, width 0.99.
- **New question.** On the October NEW population (136 runs, including the 23-run fast-scan corner), are **transient** physical summaries learnable from x? These are short spike size and duration of melt velocity and KE, and their timing relative to depth. Steady energy, temperature and laser-power levels are learned alongside them.
- **Why it matters.**
  - A learnable transient summary could become an auxiliary response that a selector learns from paid runs.
  - An unlearnable one cannot help at new runs, because there the monitors are not observed.

## Definitions (reused unchanged from `src/week19_series.py`)

- **Depth:** max(0, −z_min) on valid bounds rows. The sentinel 3.4e38 means no melt.
- **Active window:** valid rows with t ≤ `active_cutoff_ms`, which is min(recording end, 0.9 × derived domain exit); startup retained (Week 19 `depth_definitions.csv`).
- **T0:** the last 20% of the active window.
- **Hold rule:** dt_i = t_{i+1} − t_i.

## Channel meaning and units

| Channel | Unit | Meaning |
|---|---|---|
| `maximum-velocity_melt` | m/s | maximum melt-particle speed |
| `kinetic-energy_melt` | J, reported in nJ | aggregate kinetic energy of the melt-phase particles |
| `transferred-laser-power_melt` | W | laser power transferred to the melt |
| `maximum-temperature_melt` | K | maximum melt temperature |

Gas channels are not used. Argon output is never read as metal-vapour amount.

## Quality rules (no silent exclusion)

- **Row counts:** if a channel's row count differs from `time.dat`, the run's time-dependent summaries are UNAVAILABLE. This is recorded; nothing is truncated or repaired. The known case is the early-ended H-e7dbd8e5ce.
- **Non-finite values:** counted per run and channel, and excluded only from that channel's order statistics. This checks the earlier finding of 931 non-finite KE values.
- **Implausible velocities:** rows with velocity > 100 m/s are counted and excluded only from the velocity order statistics.

## Summaries (fixed before computation)

| Summary | Definition |
|---|---|
| S1 `ke_T0_med_nJ` | median melt KE over T0 (continuity with Week 7) |
| S2 `vmax_spike_logratio` | log(p99.9 / median) of maximum melt velocity, post-onset active window |
| S3 `vmax_spike_us` | time with velocity > 2 × its median (hold rule), µs |
| S4 `ke_spike_logratio` | log(p99.9 / median) of melt KE, post-onset active window |
| S5 `lag_ke_to_depth_us` | t(argmax depth) − t(argmax KE) inside the active window, µs |
| S6 `laser_T0_mean_W` | mean transferred laser power over T0 |
| S7 `tmax_T0_med_K` | median maximum melt temperature over T0 |

## Learnability (the endpoint: prediction error)

- **Setup:** out-of-fold predictions on the DEV repeat 3–4 folds. Training uses the fold pool, with all pool runs revealed; this is a diagnostic of what is learnable, not an acquisition.
- **Models:**
  - the training mean;
  - ridge on standardized log inputs (α = 1e-2);
  - GP Matérn 3/2 with ARD and a learned white nugget (the Week 7 protocol GP).
- **Metrics:** RMSE; R²_oof = 1 − SSE_model / SSE_mean; relative RMSE; GP 90% interval coverage; corner RMSE ratio GP / mean (evaluator-only corner).
- **Verdict per summary (fixed):** **LEARNABLE** if the mean R²_oof over repeats is ≥ 0.5, **WEAK** if 0.2–0.5, otherwise **NOT LEARNABLE**.
- **Separate diagnosis (evaluator side, never a learner input):**
  - the corner AUC of the **observed** summary for Keyhole. The earlier 23-run hint was 0.811 for the velocity peak/median, a research clue only;
  - the corner AUC of the **out-of-fold GP-predicted** summary, i.e. what an x-only learner could carry.
- **Cost:** GP fit time per fit and in total.

## Budget

- **Extraction:** 136 runs × 6 channels, about 0.5–1 s per run.
- **Learning:** 7 summaries × 10 folds × 3 models, with one GP fit each (≤ 2 s). The whole pilot takes minutes on one thread.
- **Next step (pilot C) only if useful:** if a summary is LEARNABLE and its predicted values carry corner information, a small temporal GP q(x,t) pilot follows on that channel.

## Limits

- This is DEV on inspected NEW runs; a new split is not new data.
- Revealing all pool runs in training is an upper bound on what a selector could learn; it is not an acquisition result.
