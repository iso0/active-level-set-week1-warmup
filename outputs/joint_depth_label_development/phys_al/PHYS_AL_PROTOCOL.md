# PHYS_AL (Study 1) — active learning of physical outputs from x = (P, VX, LS, ST)

**Status: REGISTERED BEFORE ANY PHYS_AL OUTCOME.** Owner approval of 2026-10-17 ("hepsine onay veriyorum"). Ioan, 2026-10-15: "try to fit other quantities … energy or temperature". The OLD and NEW populations are reported separately and never pooled. All of this is DEV work on simulations that were inspected before.
- **Code:** `src/jdl_phys_al.py`.
- **Manifest:** `PHYS_AL_MANIFEST.json`.
- **Data:** pinned monitors from `ioandanielc/sph_v2` (NEW `2e1eec9c`; OLD `b6dc254a` with verified reuse of the `d69dac5b` cache), SHA-checked (`physical/provenance/`).

## Questions

1. How many paid simulations does each acquisition need to learn a physical output to a fixed accuracy? This is judged at the same budget, with every query counted.
2. One simulation reveals all of its monitors. Does a single shared acquisition for all outputs (MO_MAXVAR) lose accuracy compared with target-specific acquisition?
3. Does a joint multi-output GP (ICM) learn faster than independent GPs on the same paid sets?

## Targets (fixed)

**Primary:**
- log A: the active-window maximum depth, i.e. E1's response.
- log KE_T0.
- The velocity spike log-ratio and the velocity spike duration.
- The transferred laser power over T0.
- The maximum melt temperature over T0.

**Secondary (new channels):**
- log mean total melt energy over T0.
- log median melt particle number over T0 (a melt-pool size proxy).

**Definitions and data handling:**
- Pilot B's frozen definitions are reused: the Week 19 active window, T0 and the hold rule. OLD values come from the same `summarize` function.
- A target value that is unavailable for a paid run is skipped for that target and logged, never imputed. The run still counts as paid.

## Design

- **Splits:** DEV repeats 3–4, folds 1–5.
  - NEW: the TRAINED_AL tasks.
  - OLD: the Stage M task builder, with feature-only maximin paths from `SMM.make_paths`, which is label-free.
- **Start and budget:** the first 8 points of the frozen feature-only maximin path; budgets B8–B60.
- **Model (every arm):** GP Matérn 3/2 with ARD and a white nugget, on fold-standardized log inputs; `normalize_y`; ML-II without restarts.
- **Arms:**
  - **RANDOM:** seeded; the path is target-independent and every target is predicted on it.
  - **MAXIMIN:** frozen path continuation; also target-independent.
  - **MAXVAR:** argmax of the predictive sd, per target.
  - **IVR:** argmax of the integrated variance reduction over the fold pool (closed form, validated against brute force), per target.
  - **MO_MAXVAR:** argmax of Σ_t var_t / var(paid y_t) over the primary targets, with every target predicted.
- **ICM (secondary):**
  - **Model:** B ⊗ K_x plus per-output noise, computed exactly by whitened Kronecker algebra (validated against brute force), with B = wwᵀ + diag(κ).
  - **Comparison:** against independent GPs on the identical RANDOM, MAXIMIN and MO_MAXVAR paths at budgets 8..60, step 4.
  - **Expectation:** because every simulation reveals every output (isotopic data), ICM gains are expected to be small. That expectation is stated in advance.

## Endpoints (fixed before any run)

- **Accuracy curve:** R²(b) = 1 − SSE_b / SSE_ref on the pooled test predictions of each repeat, where SSE_ref uses deviations from the population mean (an evaluator-side normalization only).
- **Area under the curve:** R²-AULC over B8–B60.
- **Attainable accuracy:** R²_full = pooled out-of-fold R² with the whole fold pool paid. A target is LEARNABLE if R²_full ≥ 0.5. The target level is 0.9 × R²_full.
- **Budget-to-target:** the first grid budget where R² ≥ level both there and at the next grid point, right-censored at 64.
- **FEWER SIMULATIONS (DEV):** the arm reaches the level in both repeats, and at least 4 queries earlier than both RANDOM and MAXIMIN in both repeats. Censored references count as 64.
- **SAME-BUDGET GAIN (DEV):** the R²-AULC minus the better of RANDOM and MAXIMIN is ≥ +0.02 on the mean, and positive in both repeats.
- **Otherwise:** no claim.
- **Also reported:** R² at B8/16/24/40/60, ICM vs independent RMSE, and compute time.

## Budget and compute

- **Volume per population:** 20 units for RANDOM/MAXIMIN, 10 for MO_MAXVAR, and 160 for MAXVAR/IVR across 8 targets. That is about 2–12 s per unit, measured in validation.
- **ICM:** about 400 fits.
- **Limits:** a per-unit time limit of 1800 s; at most 3 workers with one BLAS thread each, inside the 4-thread total.

## Limits

- This is DEV work, and a new split is not new data.
- R²_full uses all pool runs, so it is an upper-bound reference, not an acquisition result.
- Pool exhaustion: 60 of about 108 NEW pool runs (or about 324 OLD) are paid by B60. Differences are expected mainly early in the curve.
