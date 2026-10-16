# TEMPORAL_VEL (pilot C) — small temporal GP q(x, τ) on the maximum melt velocity channel

**Status: REGISTERED BEFORE ANY TEMPORAL_VEL OUTCOME** (owner request of 2026-10-16: a small temporal GP on one monitor channel if data quality and cost allow, judged by curve and peak error).
- **Code:** `src/jdl_temporal_vel.py`.
- **Manifest:** `TEMPORAL_VEL_MANIFEST.json`.

## Why this channel and this size

- **Why this channel:** pilot B found the velocity spike size the most learnable transient summary (out-of-fold R² 0.87), and informative in the corner. QC cleared it: 39 implausible rows in 9 runs, and no unequal row counts except the known early-ended run.
- **Scope:** the 40 long depth SVGP fits are **not** repeated. This is one exact GP per fold on a binned grid; the whole run takes minutes on one thread.

## Target

For each run, y(τ_k) is the log of the bin-median maximum melt velocity over K = 40 equal bins of normalized active-window time τ ∈ (0, 1].
- The bins use the Week 19 active window and post-onset valid rows only.
- Non-finite rows and rows above 100 m/s are excluded from the bin statistic only.
- Bin maxima are kept separately, to score peaks.
- A run without all 40 bins is UNAVAILABLE (recorded).

## Model

An exact 5-D Kronecker GP:
- **Covariance:** vec(Y) ~ N(μ, σ_f² K_x ⊗ K_τ + σ_n² I) on the complete training grid, i.e. runs × bins.
  - K_x: ARD Matérn 3/2 on the four standardized log inputs.
  - K_τ: Matérn 3/2 on τ.
- **Mean:** μ is the per-bin training mean, which is also the baseline.
- **Fitting:** ML-II by L-BFGS-B on the exact log marginal likelihood, computed via two eigendecompositions; 3 fixed restarts.
- **Validation:** NLML, mean and variance equal a brute-force full-covariance computation to 1e-8.

## Endpoints (fixed)

Out-of-fold on the DEV repeat 3–4 folds. Training uses the fold pool with all pool runs revealed; this is an upper bound, not acquisition.
- **Curve:** RMSE of log velocity, GP vs the mean curve; R²_curve = 1 − SSE_GP / SSE_mean; corner R²_curve (evaluator-only).
- **Peak:** |max_k ŷ − max_k y_max| in log units, and the peak-bin error in bins.
- **Uncertainty:** pointwise 90% coverage.
- **Cost:** fit seconds per fold, and in total.
- **Verdict:** **USEFUL** if the mean R²_curve is ≥ 0.3 **and** the GP beats the mean curve on peak error in both repeats; otherwise **NOT USEFUL**.

## Limits

- This is DEV on inspected NEW runs.
- The bin median smooths very short spikes, so peaks are scored against the bin maxima.
- A USEFUL verdict justifies only a later, separately registered, budgeted use as an auxiliary response. It is not a classification result.
