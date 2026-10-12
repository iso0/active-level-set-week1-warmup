# Track 2 hypotheses and evaluation criteria (frozen before any Track 2 fit)

*Written 2026-10-12T20:17:41+00:00; methods in `manifest_track2.json`.*

**Status.** Post-hoc DEV development; not confirmatory. Numerical expectations are given only where measured evidence supports them.

## Hypotheses

- **T2-H1_inputs_help.** At every budget (B16/B40/B80) both temporal models (rank-3 functional and separable SVGP) have lower simulation-weighted trajectory RMSE (log1p depth, observed bins) than the input-free training-mean trajectory. Basis: depth trajectories depend strongly on scan speed (slow scans near 300 um, fast scans near 110 um). Falsified if either model is not lower at any budget.
- **T2-H2_learning.** Trajectory RMSE of both temporal models decreases from B16 to B80 (mean over the ten folds). Falsified otherwise.
- **T2-H3_max_depth.** For the maximum depth A of held-out runs (like-for-like runs, observed window = planned horizon), the scalar A GP has a lower median absolute error (um) than both temporal models at B40 and at B80. Basis: the scalar model targets A directly, while bin means lose 0.004-0.02 log1p units at the native peak (measured compression gap). Falsified if a temporal model is lower at B40 or B80.
- **T2-H4_short_events.** The temporal models' underestimation of A (relative to the native maximum) is larger for runs whose near-peak episode (depth >= 95 % of A) is shorter than one bin width than for longer episodes. Basis: bin means smooth sub-bin peaks by construction.
- **T2-H5_calibration.** No numerical expectation. 50 % and 90 % pointwise predictive intervals are evaluated on observed bins, together with interval coverage for A.
- **T2-H6_model_ranking.** No directional expectation between the functional baseline and the separable SVGP.
- **T2-H7_matched_pair_fast_scans.** No assumption either way. Evaluated: (a) whether the observed trajectories of the matched pair (H-b302fc6cbd vs H-b7e3ed2e12) differ beyond each model's predictive uncertainty; (b) whether the models' predictions for the two runs differ; (c) descriptively, whether trajectory features (predicted A, predicted time above u_ref) rank held-out labels within fast scans (VX > 0.85; exploratory). Trajectory accuracy and canonical-label information are reported separately; no classifier is built.
- **T2-H8_truncated.** For the six runs whose recording ends before the planned horizon, planned-horizon predicted maxima and observed-window maxima are reported separately as different estimands. No expectation.

## Evaluation

- simulation-weighted trajectory RMSE (observed bins) and median;
- 50 %/90 % pointwise interval coverage and width (latent + noise variance);
- A error (um, log1p) vs native maximum and vs bin-mean maximum; 90 % interval coverage of A;
- argmax timing error (us) and time-above-u_ref error (us) on the observed window;
- short-event analysis: near-peak (>= 95 % of A) episode shorter than one bin;
- runtime, peak memory, SVGP ELBO trace, SVGP vs exact on a controlled example, M=400 vs M=800 at one checkpoint;
- representative best / median / worst held-out runs and the named runs (matched pair, late negative);
- planned-horizon vs observed-window quantities reported separately for the six truncated runs.
