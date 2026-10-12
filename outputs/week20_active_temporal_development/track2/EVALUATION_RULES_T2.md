# Track 2 evaluation rules (POST-START, written before any held-out evaluation)

*Written 2026-10-12, while the 30 frozen SVGP fits were running (5 of 30 done). At this point no held-out prediction of any Track 2 model had been scored or viewed.*

**Why this file exists.**
- `HYPOTHESES_TRACK2.md` was frozen before any fit, but some hypotheses need an exact decision rule: which rows, which average, which comparison.
- This file fixes those rules before scoring. It does not change any hypothesis, method, seed or fit.
- Metrics added here, beyond the frozen evaluation list, are marked **ADDED**.

## Scored rows and bins

- **Rows:** one row per held-out run with a trajectory, per checkpoint (2 repeats × 5 folds × 3 budgets). The run `H-e7dbd8e5ce` has no trajectory (bounds/time mismatch) and cannot be scored.
- **Trajectory metrics:** every observed bin of the held-out run.
  - Checked label-free before scoring: none of the 233,910 observed held-out bins lies outside the bins covered by that checkpoint's paid training trajectories, so every model is scored on the same bins.
- **Like-for-like rows** (maximum depth A, timing, exceedance): runs whose recording reaches the planned horizon. The six truncated runs are reported only under T2-H8.
- **A** is the canonical active-window maximum `A_um`. It equals the native trajectory maximum to 1.7e-13 µm.
- **Temporal-model A** is the median, over 2000 posterior latent trajectories, of the maximum over the planned horizon. Its 90 % interval is the 5–95 % range of those maxima.
  - These are latent-trajectory intervals: residual noise is excluded, as fixed in the frozen scripts.
  - The scalar A GP interval includes noise (latent + noise variance of log A).
  - The two A intervals are therefore different estimands, and coverage is compared with that caveat.

## Decision rules

| Hypothesis | Rule | Verdict |
|---|---|---|
| T2-H1 inputs help | For each budget (16, 40, 80) and each temporal model (functional, SVGP): the mean per-run trajectory RMSE over all scored rows is lower than that of the training-mean trajectory on the same rows. | SUPPORTED only if all 6 comparisons hold; otherwise FALSIFIED. |
| T2-H2 learning | For each temporal model: the mean over the ten (repeat, fold) checkpoints of the per-checkpoint mean RMSE is lower at B80 than at B16. Strict monotonicity (B16 > B40 > B80) is reported in addition. | SUPPORTED only if B80 < B16 for both models. |
| T2-H3 max depth | Like-for-like rows at B40 and at B80: the median absolute A error (µm) of the scalar A GP is lower than that of the functional model and lower than that of the SVGP. | SUPPORTED only if all 4 comparisons hold. FALSIFIED if any temporal model is lower or equal. |
| T2-H4 short events | For each temporal model, pooled over budgets and repeats (like-for-like rows): the median signed log1p A error (prediction − A) of short-event rows is lower than that of the other rows. A short-event row is one whose near-peak episode (≥ 95 % of A) is shorter than one bin. Per-budget values are reported in addition. | SUPPORTED only if this holds for both models. INCONCLUSIVE if fewer than 5 distinct short-event runs exist. |
| T2-H5 calibration | 50 % and 90 % pointwise coverage and width; A 90 % coverage. | Descriptive; no verdict. |
| T2-H6 ranking | Functional vs SVGP on trajectory RMSE and A error, per budget. | Descriptive; no verdict. |
| T2-H7 matched pair, fast scans | (a) The observed RMS difference between the G5 (`H-b302fc6cbd`) and G4 (`H-b7e3ed2e12`) bin-mean trajectories on their common bins, divided by the RMS of √(sd_G5² + sd_G4²). This is the spread of the difference of two independent predictive draws. A ratio above 2 is read as "differs beyond predictive uncertainty". (b) The RMS difference between the two predicted mean trajectories. (c) AUCs of the predicted features against canonical labels, overall and for VX > 0.85 (exploratory). | Descriptive; no classifier and no verdict. |
| T2-H8 truncated | Planned-horizon predicted maximum, observed-window predicted maximum and the observed A, side by side. | Descriptive. |
| T2-PS1 (post-start) | The mean per-run trajectory RMSE over the held-out rows of `ckpt_r1_f{1..5}_B40`, 6000 vs 2000 iterations, on the same scored bins. | SUPPORTED if the relative change is below 10 % in absolute value. |

## ADDED metrics (descriptive; no verdict)

- **Exceedance probability of the maximum.** P(max over planned horizon > u_ref) from the posterior trajectories. For the scalar GP it is Φ((μ − log u_ref) / √(latent + noise)).
  - It is scored against the trajectory event A > u_ref with the Brier score (trajectory accuracy).
  - It is scored separately, by AUC, against the canonical label (label information).
  - It is not a keyhole probability.
- **Paired differences with intervals.** For T2-H1 and T2-H3: the paired difference (model − reference) with a 95 % cluster bootstrap over simulations (2000 draws, seed 0).
  - Each simulation appears once per repeat, so the two repeats of a run are resampled together.
  - The interval is reported only; it does not change the verdict.
- **Named runs.** Per-run predictions for G5, G4 and the late negative `H-f4fc937e86`.
- **Information preserved by the representation.** Compression RMSE and loss at the native peak at K = 360, from `compression_error_all_runs.csv`; label-free.
