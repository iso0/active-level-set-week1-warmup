# Temporal repair report: do a longer NGD SVGP and a conditioned (PPCA) functional model fix the Week 20 temporal models?

**Status.** Development work on the Week 20 Track 2 checkpoints: NEW DEV repeats 1–2, ten folds, B16/B40/B80, 30 checkpoints. Not confirmation.
- **Freeze:** `temporal_repair/TEMPORAL_MANIFEST.json`, commit `29ca7364` (2026-10-13 14:00 UTC), written before any new temporal fit on study data.
- **Evaluation:** queue T15 (commit `da46dd70`) with the unchanged Week 20 Track 2 metric definitions.
- **Stopping-rule audit:** T16, commit `b3c1c6ac`; see `temporal_repair/TEMPORAL_STOPPING_AUDIT.md`.
- **Scheduling amendments (recorded before use):**
  - T-A2: checkpoint claims through lock files and a per-fit thread count.
  - T-A3: four one-thread workers after the Windows Update restart T-S4. The two fits killed by that restart were re-run in full; no partial result was used.
- **Evidence labels:** **PRED** = held-out predictions; **OBS** = logs and tables; **HYP** = interpretation.
- **What it measures:** curve accuracy is not canonical-label success.

## 1. What was run

- **Repair 1: NGD SVGP.**
  - Optimisers: natural-gradient descent (lr 0.1) on the variational distribution, plus Adam (lr 0.01) on the hyperparameters and inducing locations. Both learning rates are halved at 5,000 and 10,000 iterations.
  - Stopping rule: relative probe-ELBO change ≤ 5e-4 and probe-mean RMS change ≤ 5e-3 on 3 consecutive 250-iteration checks, within 1,000–20,000 iterations.
  - Fits: M = 400 inducing points on all 30 checkpoints; M = 800 on the ten B40 checkpoints.
- **Repair 2: PPCA functional model.** Rank-3 probabilistic PCA with missing data: EM with an exact per-run coefficient posterior, then one GP per coefficient, with that run's posterior variance as its noise.
- **Controls (unchanged):** training-mean trajectory; scalar A GP; frozen functional model (Week 20 ALS); frozen SVGP (2,000 Adam iterations); SVGP at 6,000 iterations (T2-PS1, five checkpoints).
- **Compute (OBS, `svgp_ngd_fits.jsonl`, `svgp_ngd_convergence.csv`):**
  - **All 40 SVGP fits stopped at the 20,000-iteration cap; none met the stopping rule.**
  - M400: 21 fits on 3 threads (median 35 min) and 9 on 1 thread (median 74 min).
  - M800: 10 fits on 1 thread (median 5.7 h, range 4.9–6.8 h).
  - Total fit time: 23.4 h for M400 and 60.2 h for M800.
  - PPCA: EM reached its 3,000-iteration cap at all 30 checkpoints.
- **Rows:** 270 trajectory rows and 260 like-for-like A rows per budget.

## 2. Frozen hypotheses and outcomes

| Hypothesis | Result (PRED; paired, 95 % interval) | Verdict |
|---|---|---|
| TR-H1: NGD SVGP M400 has lower mean trajectory RMSE than the frozen SVGP at every budget | B16 −0.200 [−0.225, −0.177]; B40 −0.109 [−0.126, −0.094]; B80 −0.089 [−0.100, −0.079] | **Supported** |
| TR-H2: lower median \|A error\| than the frozen SVGP at B40 and B80, but still above the scalar A GP | vs frozen: B40 −28.2 µm [−38.6, −16.9], B80 −14.8 µm [−26.2, −8.8]; vs scalar: B40 +31.2 [+26.6, +37.9], B80 +23.6 [+20.4, +26.8] | **Supported** |
| TR-H3: with equal effort, the M400 − M800 predictive-mean RMS difference at B40 is smaller than the frozen protocol's 0.167 at `ckpt_r1_f1_B40` | 0.198 at `ckpt_r1_f1_B40`; 0.027–0.198 over the ten B40 checkpoints (median 0.105) | **Falsified** at the named checkpoint |
| TR-H4: PPCA has max \|posterior-mean coefficient\| < 10 at every checkpoint, and lower mean RMSE than the frozen functional model at every budget | max 9.80 (frozen ALS up to 26,571); RMSE B16 −0.77 [−1.16, −0.44], B40 −3.57 [−5.51, −1.88], B80 −8.51 [−12.52, −5.56] | **Supported** |
| TR-H5: PPCA vs NGD SVGP (no direction committed) | PPCA − SVGP RMSE +0.50 / +0.59 / +0.69; A error +28.9 / +64.5 / +665 µm (B16/B40/B80) | NGD SVGP ranks above PPCA on both |
| TR-H6: neither repaired model reaches the scalar A GP's median \|A error\| at B40 or B80 | SVGP 36.3 / 27.5 µm vs scalar 5.1 / 3.9 µm (about 7×); PPCA 101 / 693 µm | **Supported** |
| TR-H7: calibration (no expectation; reported with widths) | §3 | Reported |

- **On "converged" (TR-H1, TR-H2):** the hypotheses call the repaired SVGP "converged". It was trained to the 20,000-iteration cap without meeting its rule. The comparisons are of fits at the cap.
- **On "equal effort" (TR-H3):** this meant equal iteration count. M800, which has more parameters, is less optimised at the same cap. At five of the ten B40 checkpoints its trajectory RMSE is clearly worse than M400's (0.27–0.36 against 0.15–0.23).

## 3. Results (PRED; `summary_trajectory.csv`, `summary_A_timing_exceedance.csv`)

### Trajectory (observed bins, log1p-depth units; mean over runs)

| Model | RMSE B16 / B40 / B80 | Median RMSE B40 | 50 % coverage B40 | 90 % coverage B40 | 90 % width B40 |
|---|---|---|---|---|---|
| svgp_ngd_M400 | 0.186 / 0.158 / 0.126 | 0.121 | 0.68 | 0.89 | 0.47 |
| svgp_ngd_M800 (B40 only) | — / 0.185 / — | 0.125 | 0.70 | 0.90 | 0.56 |
| frozen svgp (2,000 it) | 0.386 / 0.267 / 0.215 | 0.225 | 0.80 | 0.99 | 1.64 |
| svgp_it6000 (5 checkpoints) | — / 0.198 / — | 0.170 | 0.55 | 0.89 | 0.62 |
| functional_ppca | 0.686 / 0.752 / 0.821 | 0.243 | 0.78 | 0.93 | 6.77 |
| frozen functional | 1.454 / 4.326 / 9.335 | 0.316 | 0.87 | 0.96 | 32.2 |
| training-mean trajectory | 0.501 / 0.451 / 0.432 | 0.461 | 0.40 | 0.97 | 1.34 |

- **NGD SVGP vs the training mean:** M400 beats it by −0.32 / −0.29 / −0.31 RMSE.
- **PPCA's mean is dragged up by a few runs.** Its mean RMSE is worse than the training mean (+0.19 / +0.30 / +0.39), but its median RMSE is better (0.24–0.28 against 0.42–0.50).

### A, timing and exceedance (like-for-like runs; medians)

| Model | \|A error\| µm B16 / B40 / B80 | A inside its 90 % interval B16 / B40 / B80 | argmax-time error µs B40 | time-above-u_ref error µs B40 | Brier P(max > u_ref) B40 |
|---|---|---|---|---|---|
| scalar A GP | 8.2 / 5.1 / 3.9 | 0.82 / 0.87 / 0.87 | — | — | — |
| svgp_ngd_M400 | 48.1 / 36.3 / 27.5 | 0.60 / 0.37 / 0.25 | 80.0 | 19.8 | 0.064 |
| svgp_ngd_M800 | — / 41.2 / — | — / 0.53 / — | 90.6 | 19.1 | 0.042 |
| frozen svgp | 104.7 / 64.6 / 42.3 | 0.92 / 0.95 / 0.96 | 187.8 | 65.7 | 0.041 |
| functional_ppca | 77.0 / 100.9 / 692.6 | 0.67 / 0.59 / 0.44 | 163.9 | 223.4 | 0.034 |
| frozen functional | 205.6 / 386.6 / 4.1e9 (exploded) | 0.74 / 0.72 / 0.80 | 181.9 | 292.1 | 0.042 |

- **Inducing sensitivity** (`inducing_sensitivity.csv`): the median \|A difference\| between M400 and M800 predictions at B40 is 4.7–41.6 µm across the ten checkpoints.
- **Conditioning** (`functional_ppca_conditioning.csv`): the largest posterior coefficient SD is at most 0.67.

## 4. Stopping rule (`temporal_repair/TEMPORAL_STOPPING_AUDIT.md`)

- **The rule cannot be met.** Check-to-check changes stay at the optimiser's noise level, about 5e-3 relative ELBO and 1.6e-2 RMS in standardized mean units, so no check of any fit met the mean criterion. The rule sits below the noise floor (claims F5).
- **Two definitional issues, neither changing any decision:**
  - The probe ELBO up-weights the KL term by up to n/m = 2.87.
  - The 5e-3 mean tolerance is applied in standardized units. That equals 0.010 in log1p units, about twice as loose as documented.
- **Reproducibility caveat.** Each fit's variational initialisation noise comes from the unseeded process-global torch RNG, so a re-run with another worker order could differ slightly.

## 5. Interpretation (HYP)

1. **The optimisation was the main SVGP defect.** Training the same SVGP for longer with NGD:
   - halves its trajectory error at B16 and cuts it by about 40 % at B40/B80;
   - lowers its A error from 65 to 36 µm at B40;
   - improves timing and time-above-reference errors: the argmax-time error falls by a factor of 1.8–2.3 and the time-above-reference error by 2.5–7.6 (B80–B16).
2. **It is still not an A model.** Its median A error stays about 7× the scalar A GP's.
   - Its A 90 % intervals now under-cover badly (0.25–0.60 against nominal 0.90), and its P(max > u_ref) Brier is worse than the frozen SVGP's at B40/B80: the model became sharper but overconfident about the maximum.
   - Pointwise trajectory coverage, by contrast, is near nominal at 90 %.
   - For the A endpoint, the scalar A GP remains the model to use.
3. **More inducing points do not help at a fixed iteration budget.** M800 is no closer to M400 than the frozen pair was at the named checkpoint, and is often worse.
4. **PPCA fixes conditioning, not accuracy.** It removes the exploding coefficients and is far better than the frozen functional model. But its mean trajectory error is worse than the training-mean curve because of a few failing runs, and its A error explodes at B80. It is not usable for A or for exceedance.
5. **What this does and does not support.**
   - It supports trajectory and timing description with the NGD SVGP.
   - It supports no claim about canonical labels, simulation savings or confirmation.
   - Week 20 C3 stays failed.

## 6. Limitations

- **No fit met its stopping rule.** Every comparison is at the iteration cap.
- **Thread counts differ** across the M400 fits (3 or 1), so wall times are not comparable.
- **Bitwise reproducibility** depends on worker history (§4).
- **Development data:** these are inspected repeats, and the bootstrap is conditional on the checkpoints. The 6,000-iteration control covers only five checkpoints.

## 7. Files

`temporal_repair/`:
- `TEMPORAL_MANIFEST.json`
- `summary_trajectory.csv`, `summary_A_timing_exceedance.csv`, `paired_differences.csv`
- `inducing_sensitivity.csv`, `svgp_ngd_convergence.csv`, `functional_ppca_conditioning.csv`
- `evaluation_per_run.csv.gz`
- `svgp_ngd_fits.jsonl`, `functional_ppca_fits.jsonl`
- `stopping_audit_summary.json`, `stopping_audit_per_fit.csv`, `TEMPORAL_STOPPING_AUDIT.md`
- `checkpoint_mechanism/`

Scheduling and interruption records: ledger rows T-S1 to T-S4, T-A2 to T-A4.
