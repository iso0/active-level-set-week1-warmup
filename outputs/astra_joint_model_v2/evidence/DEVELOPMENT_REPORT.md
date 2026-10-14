# Week 20 development report: active learning with the active-window target, and temporal-GP development

**Status.**
- Post-hoc DEV research: Track 1 uses repeats 1–4 and Track 2 uses repeats 1–2. This is not confirmation.
- C3 (repeats 17–20) stays reserved.
- No simulator job was run, and no label, eligibility decision or exclusion was changed. The 49 Bug-withheld NEW runs are not used.

**Branch and freezes.** The branch `week20-active-temporal-dev` starts from `7707d7f4`.
- Track 1 manifest and hypotheses: commit `acb14d4f`, pushed before any Track 1 fit.
- Track 2 manifest and hypotheses: commit `a17126cf`, pushed before any Track 2 fit.
- Track 2 post-start sensitivity T2-PS1: commit `05c4b0cf`, declared from training traces after 2 of 30 SVGP fits.
- Track 2 evaluation rules: commit `0274e5a1`, committed before any held-out prediction was scored.
- Every execution is listed in [ATTEMPT_LEDGER.md](ATTEMPT_LEDGER.md).
- **Run names:** H codes such as H-f4fc937e86 are shorthand only. The suffix is not unique: the 136 NEW runs carry 88 suffixes. [NAMED_RUNS.csv](NAMED_RUNS.csv) gives the full sim ID of every run named in this report.

**Evidence labels.**
- **PRED**: held-out predictions.
- **OBS**: table or ledger values.
- **POST-HOC**: an analysis added after results were seen; these are marked in file names.
- **HYP**: interpretation.

## Summary

**C3 confirmation, 2026-10-13: NOT CONFIRMED AT THE FROZEN BAR** (section *C3 confirmation* below).
- **Approval:** the owner approved; the freeze (`4164f67b`) came before any C3 computation, and all 180 C3 runs are reported.
- **Primary result:** on R3_NEW, ACTIVE − G3 BA-AULC is **+0.007 [−0.036, +0.053]**, against a frozen bar of +0.02 with interval > 0.
- **No loss elsewhere:** OLD +0.011 and POOLED +0.004, both above −0.01.
- **What replicates:** ACTIVE − WHOLE is +0.044 [+0.023, +0.067]. ACTIVE − G3 also holds on q20 (+0.069), AUC (+0.095) and Brier (−0.024), but these are not decisive.

**Update, 2026-10-13: Track 1 extension** (section *Track 1 extension* below).
- **New repeats:** the recommended next experiment ran on DEV repeats 5–8. ACTIVE − G3 on R3_NEW is **+0.056 [+0.009, +0.135]**; over all 8 DEV repeats it is **+0.056 [+0.015, +0.103]**.
- **Guard ablation:** the slope-sign guard does not explain the gain (WHOLE + guard − WHOLE = +0.002). The gain comes from the active-window target.
- **Decision:** the frozen decision rule returned **C3 PROTOCOL DRAFT**. The draft is written but not executed; its primary rule passes in about 60 % of DEV resamples.

**What improved (Week 20 round):**
1. **ACTIVE E1 + straddle on NEW (PRED).**

   | Measure | ACTIVE E1 | G3 | WHOLE E1 |
   |---|---:|---:|---:|
   | BA-AULC | 0.721 | 0.664 | 0.651 |
   | Brier | 0.067 | 0.093 | 0.119 |
   | AUC | 0.915 | 0.803 | 0.829 |

   - ACTIVE − G3 = +0.057 [−0.007, +0.115]; ACTIVE − WHOLE = +0.070 [+0.030, +0.110]; q20 ACTIVE − G3 = +0.096 [+0.053, +0.145].
   - On OLD and POOLED, ACTIVE matches WHOLE (difference ≤ 0.002), so switching the target has no measurable cost there.
2. **Why WHOLE E1 fails on NEW (OBS, with POST-HOC attribution).** It enters a reversed-slope threshold trap when the late negative (whole 312 µm) is its only paid negative.
   - In that state straddle keeps buying slow-scan positives until a second negative appears.
   - ACTIVE never enters the trap: its maximum learned threshold is 188.9 µm and it never has a reversed slope.
3. **Trajectories (PRED).** The separable input × time SVGP learns depth trajectories. Its RMSE is 0.386 → 0.267 → 0.215 (log1p) at B16 → B40 → B80, against 0.501 → 0.451 → 0.432 for the input-free mean trajectory.

**What did not improve:**
1. **Track 1 precision.** The primary NEW interval includes 0: repeat 2 is −0.032. NEW specificity stays ≤ 0.48 (AULC) in every arm.
2. **Maximum depth.** The scalar A GP predicts A about 10× better than either temporal model: median error 5.1 µm vs 65 µm (SVGP) at B40.
3. **Functional baseline.** It failed: paid runs whose recording ends early get ill-conditioned coefficients, and its RMSE grows with budget.
4. **Frozen SVGP.** It is under-converged (−23 % RMSE with 6000 iterations; post-start T2-PS1) and not stable in the number of inducing points.
5. **Matched pair and fast scans (OBS).** The matched pair has nearly identical observed depth trajectories (RMS 0.047 log1p), so no depth-based model separates its labels. In fast scans, even exactly observed depth features rank labels at only about 0.76 AUC.

**Candidate for the next experiment: ACTIVE E1 + straddle.**
- **Next step:** run the same frozen Track 1 protocol on the remaining DEV repeats 5–8 (DEV is 1–8; C1 and C2 are spent).
- **Added ablation:** WHOLE E1 with a slope-sign guard (no root accepted from a non-positive slope), declared before fitting. It separates the response-target effect from the threshold-rule effect.
- **C3:** freeze a C3 protocol (repeats 17–20, primary NEW BA-AULC ACTIVE − G3) only if NEW ACTIVE − G3 stays positive with a tighter interval.
- **Temporal models:** they are not ready to replace the scalar target. Their next development step is a converged SVGP and a functional model with a coefficient prior, compared on the same 30 checkpoints.

## Track 1 — real active-learning benchmark (R3_NEW, R3_OLD, R1_POOLED; repeats 1–4 × 5 folds)

**Arms.** All arms are on identical tasks, splits and startup.

| Arm | Model and response | Acquisition |
|---|---|---|
| A | WHOLE E1: the historical Week 18 GPR on log whole-record max depth | straddle |
| B | ACTIVE E1: the same code on log A, the active-window max depth | straddle |
| C | G3: the historical binary GPC | margin |

**Procedure.**
- **Startup:** the Week 18 rule (8 maximin points, then continuation until both classes are revealed). It was identical for all 180 runs; the A-unavailable run was never in a startup set.
- **Refits:** after every paid query up to 80, as in the original methods.
- **Leakage guard:** the learner never receives an unpaid label or response.
- **Ledgers:** 14,400 rows, one per query.

**Fidelity (OBS).** Arms A and C reproduce the historical Week 18 DEV caches. Over 1,398 run-budget comparisons the maximum |Δp| is ≤ 6.2e-6, the cache rounding level (`track1/fidelity_vs_week18_caches.csv`). Their contrasts therefore equal the published DEV values exactly (T1-H0 supported).

### Results (PRED; pooled-per-repeat BA AULC on the Week 18 grid up to B80; repeat bootstrap 95 % interval, 4 repeats)

| Task | WHOLE E1 | ACTIVE E1 | G3 | ACTIVE − G3 | ACTIVE − WHOLE | WHOLE − G3 |
|---|---:|---:|---:|---|---|---|
| **R3_NEW (primary)** | 0.651 | **0.721** | 0.664 | **+0.057 [−0.007, +0.115]** | +0.070 [+0.030, +0.110] | −0.013 [−0.104, +0.037] |
| R3_OLD | 0.939 | 0.940 | 0.910 | +0.030 [+0.014, +0.052] | +0.001 [−0.004, +0.011] | +0.029 [+0.012, +0.052] |
| R1_POOLED | 0.945 | 0.947 | 0.943 | +0.005 [+0.002, +0.008] | +0.002 [−0.002, +0.006] | +0.003 [−0.000, +0.006] |

**Per repeat on NEW, ACTIVE − G3:** +0.062, −0.032, +0.067, +0.132. Repeat 2 is negative, so the primary interval includes 0.

**Secondary endpoints on NEW** (AULC; ACTIVE / G3 / WHOLE):

| Endpoint | ACTIVE | G3 | WHOLE | ACTIVE − G3 |
|---|---:|---:|---:|---|
| q20 | 0.768 | 0.672 | 0.662 | +0.096 [+0.053, +0.145] |
| Specificity (12 negatives) | 0.472 | 0.375 | 0.415 | |
| Sensitivity | 0.970 | 0.953 | 0.888 | |
| Short-K sensitivity (10 runs) | 0.731 | 0.578 | 0.628 | |
| Brier | 0.067 | 0.093 | 0.119 | |
| AUC | 0.915 | 0.803 | 0.829 | |

The full per-step curves are in `track1/curves_every_step.csv` and `track1/figures/track1_BA_curves.png`.

**Hypotheses.**
- **T1-H1 (primary, ACTIVE > G3 on NEW):** positive point estimate, but the interval includes 0, so not established at this precision.
- **T1-H2 (ACTIVE > WHOLE on NEW):** supported.
- **T1-H3 (OLD):**
  - WHOLE − G3 reproduces +0.029;
  - |ACTIVE − WHOLE| = 0.001 < 0.01, as predicted.
- **T1-H4 (POOLED):**
  - WHOLE − G3 reproduces +0.003;
  - ACTIVE − G3 (+0.005) ≥ WHOLE − G3, as predicted.

**Query savings (frozen Week 18 QTT definition, `track1/qtt.csv`).**
- **NEW, target G3's mean BA at B40 (0.698):** ACTIVE reaches it at the first grid point (16) in all 4 repeats. This is left-censored, so a saving cannot be quantified below 16. G3 reaches it in 3/4 repeats (16, 16, 56) and WHOLE in 2/4 (28, 56).
- **Post-hoc sustained-crossing check** (`track1/POSTHOC_qtt_sustained.csv`; the curve must stay above target until B80): ACTIVE sustains the B40 target in 2/4 repeats (from 24 and 28); G3 and WHOLE in 0/4.
- No saving is extrapolated beyond B80.

### Acquisition mechanism: the reversed-slope threshold trap (OBS from ledgers; POST-HOC attribution)

**WHOLE E1 on NEW.** The learned threshold reaches u ≥ 200 µm in **9 of 20 runs**. The historical caches, which saw only the grid budgets, showed 6. In all 9 runs the late negative H-f4fc937e86 had been paid before the first high-threshold step. This is temporal precedence (T1-H6 supported).

**The six long episodes** (`track1/POSTHOC_threshold_episodes.csv`) last 14–39 queries. *Erratum:* the commit message of `d50e43b9` says "7 runs"; the correct count is 6. The seventh run counted there has a positive-slope episode with three paid negatives.
- **Composition.** The late negative (whole 312.0 µm, the deepest value of any NEW run) is the *only* paid negative.
- **Threshold.** The logistic threshold fit then has a **negative slope (≈ −400)**: it separates "deeper = negative". The engine nevertheless uses its root, u ≈ 308 µm, as a "deeper = Keyhole" threshold.
- **Acquisition.** Straddle then queries runs predicted near 308 µm (median whole max of the chosen runs ≈ 302.7 µm). These are slow-scan positives, so no new negative is revealed during the episode.
- **End.** Each episode ends when a second negative is paid: five times H-e7dbd8e5ce (whole 145 µm) and once H-2e066980ca.

**Other episodes.** Two runs have one-step thresholds of 1e28–1e119 µm, from a near-zero negative slope. One run has a positive-slope episode at 220–232 µm, with three paid negatives.

**Step-level algorithmic attribution (POST-HOC).** We recomputed the same threshold rule on the same paid pairs, replacing only the late negative's value with its A value (110.755 µm). In all 11 episodes this gives u = 80–189 µm, below 200. This establishes the threshold-rule effect at the episode start only; it is not a re-run of the active-learning path.

**ACTIVE E1.** It never reaches 200 µm on NEW (maximum 188.9 µm; T1-H5 supported) and never has a reversed slope. Across all tasks, WHOLE E1 has 175 reversed-slope steps, all on NEW.

**Other diagnostics.**
- Learned-threshold trajectories: `track1/figures/track1_NEW_threshold_trajectories.png`.
- Reversed-slope steps of WHOLE E1 on NEW: 175.
- Roots outside the paid range: 72 steps (WHOLE) vs 10 (ACTIVE).
- G3: Laplace fixed-point violations 0; L-BFGS non-success messages 76 of 4,367 fits.
- E1: no L-BFGS warnings.

**Paths.**
- The arms diverge after the startup: Jaccard overlap of the B80 paid sets 0.66–0.76 on NEW (`track1/path_overlap.csv`).
- Negatives make up 11–12 % of the paid runs in all arms.
- ACTIVE pays the A-unavailable run in 13/20 NEW runs (queries 37–80). Its query is counted and its label kept, but it gives no response pair.

**Limitations.**
- There are four repeats only, so the repeat bootstrap is coarse.
- A was chosen after the Week 19 audit had seen all NEW labels, so these are optimistic DEV numbers.
- NEW specificity stays low for every arm (≤ 0.48 AULC).
- The reversed-slope trap is a property of the historical threshold rule. A slope-sign guard was not tested: it would be a new candidate, not a repair.

## Track 2 — temporal-GP development (NEW; repeats 1–2 × 5 folds; B16 / B40 / B80)

**Setting.**
- **Training data:** at each of the 30 checkpoints (2 repeats × 5 folds × 3 budgets), the paid runs of the Week 19 shared, label-blind paid paths. Only paid runs are used.
- **Held-out runs:** every run of the fold's held-out set, scored on complete runs. Each held-out set has 26–28 runs with a trajectory.
- **Missing trajectory:** the run H-e7dbd8e5ce has no trajectory (bounds/time mismatch), so it can be neither trained on nor scored.
- **Labels:** canonical labels are never used for training. They enter only the descriptive label-information table.

**Representation (OBS, label-free; `track2/trajectory_inventory.csv`, `compression_error_all_runs.csv`).**
- **Response and time:** y = log(1 + depth µm) on the native time axis, with s = t / derived exit (the active-window convention).
- **Windows:** the planned horizon s_plan = min(TE, 0.9·exit) / exit comes from the scheduled settings. The observed window s_obs is where the recording actually ends.
  - Five runs with a trajectory stop recording before the planned horizon. A sixth truncated run, H-e7dbd8e5ce, has no trajectory.
  - These windows are never stretched or tail-filled. Planned-horizon and observed-window quantities are reported separately.
- **Compression:** native series have up to 115,600 rows per run. They are reduced to bin means on a uniform s-grid.
  - The training-only rule picks the smallest K in {90, 180, 360, 720} whose median training compression RMSE is ≤ 0.04. It chose K = 360 (bin width 0.0025 s units, 3–14 µs depending on the run's exit time; median 6.4 µs) at all 30 checkpoints.
  - At K = 360, over all 135 runs, the compression RMSE has median 0.037 and maximum 0.30 (log1p units).
  - The peak lost to bin averaging has median 0.004 log1p (about 0.4 % of A) and maximum 0.28.
  - Each training run's exact native maximum is added as one extra training point at its native time.

**Models.**

| Model | Description | Inference |
|---|---|---|
| Training-mean trajectory | input-free baseline: the per-bin mean (and variance) of the paid training trajectories | — |
| Scalar A GP (reference) | the Week 19 ACTIVE E1 GP on log A (engine code); 30 refits equal the pilot's saved predictions | exact (sklearn) |
| Rank-3 functional | training mean + 3 basis functions from alternating least squares with missing entries; each coefficient gets its own GP over the 4 log inputs (Matérn-3/2 ARD + white noise) | exact (sklearn) |
| Separable input × time GP | k = σ² · Matérn-3/2 ARD(4 log inputs) × Matérn-3/2(s); M = 400 learned inducing points; Adam, 2000 iterations, minibatch 1024, float64 | sparse variational (GPyTorch) |

- **Posterior trajectories:** the functional and SVGP summaries of the maximum, its timing and the time above u_ref come from 2000 posterior latent trajectories per held-out run, never from the maximum of the posterior mean.
- **Why not exact Kronecker.** The training design is a staircase: each run has its own observed window, plus one off-grid maximum point. The Kronecker identity holds only on a complete grid. It was checked there (`svgp_validation.json`): posterior mean vs dense GP 6e-14, log marginal likelihood 2e-13.
- **SVGP validation on a controlled example.** With the inducing points equal to all 375 training inputs, the SVGP matches the exact GP to 2.2e-5 in mean and 3.5e-5 in variance (ELBO − LML = −0.93). With 60 learned inducing points the mean error is 0.42, so the inducing-point count matters.

**Fit diagnostics (OBS).**
- **Functional ALS:** stopped at its 500-iteration cap at 22 of 30 checkpoints, before reaching the 1e-10 relative tolerance; the residual variance was 0.005–0.011.
- **Coefficient-GP bounds:** sklearn reported a hyperparameter at a bound at 29 of 30 checkpoints (noise level 26, a length scale 27).
- **SVGP:** per-fit training-loss traces and hyperparameters are in `svgp_fits.jsonl`.

**Order of execution.**
1. All 128 temporal/functional fits finished before any held-out prediction was scored: 30 frozen SVGP fits, then the frozen M = 800 check, then the 5 declared post-start fits.
2. The decision rules (`track2/EVALUATION_RULES_T2.md`, commit `0274e5a1`) were committed while the SVGP fits were still running.

**Evaluation bug (fixed before reporting).** The first evaluation run looked up named runs by their H suffix. That suffix is not unique: the 136 NEW runs carry only 88 distinct suffixes, and H-b302fc6cbd is shared by G5 and a slow-scan positive.
- The named-run table now uses full sim IDs, and `NAMED_RUNS.csv` lists every run named in this report.
- Every frozen-evaluation table was byte-identical before and after the fix.
- The H codes used in this report and in earlier weeks are shorthand only; `NAMED_RUNS.csv` gives the exact run for each.

### Results (PRED; 270 held-out rows per budget = 135 runs × 2 repeats; like-for-like A rows: 130 runs × 2 = 260)

**Hypotheses** (rules fixed before scoring; `track2/hypothesis_verdicts_T2.csv`):

| Hypothesis | Verdict | Why |
|---|---|---|
| T2-H1 inputs help | **FALSIFIED** | The SVGP is lower than the training mean at every budget, but the functional baseline is higher at every budget. |
| T2-H2 learning | **FALSIFIED** | The SVGP decreases monotonically (fold means 0.386 → 0.267 → 0.215); the functional baseline increases (1.47 → 4.33 → 9.41). |
| T2-H3 scalar best for A | **SUPPORTED** | The scalar A GP has the lowest median A error at B40 and B80 (and at B16). |
| T2-H4 short events | **INCONCLUSIVE** | No like-for-like run has a near-peak episode (≥ 95 % of A) shorter than one bin (3–14 µs), so it cannot be tested. The three runs that do are truncated runs, whose maximum falls where the recording stops. |
| T2-H5 – H8 | descriptive | Reported below. |
| T2-PS1 (post-start) | **FALSIFIED** | 6000 instead of 2000 iterations lowers the SVGP trajectory RMSE by **23.0 %** (0.257 → 0.198; all five checkpoints improve). The frozen SVGP is therefore optimization-limited. |

**Trajectory accuracy** (log1p depth, observed bins; `summary_trajectory.csv`). Mean per-run RMSE, median in parentheses:

| Model | B16 | B40 | B80 | 50 % coverage (B16 / 40 / 80) | 90 % coverage | 90 % width |
|---|---|---|---|---|---|---|
| Training-mean trajectory | 0.501 (0.500) | 0.451 (0.461) | 0.432 (0.416) | 0.39 / 0.40 / 0.43 | 0.94 / 0.97 / 0.96 | 1.38 / 1.34 / 1.31 |
| Rank-3 functional | 1.454 (0.282) | 4.326 (0.316) | 9.335 (1.371) | 0.76 / 0.87 / 0.91 | 0.91 / 0.96 / 0.96 | 4.4 / 32 / 76 |
| **Separable SVGP** | **0.386** (0.351) | **0.267** (0.225) | **0.215** (0.188) | 0.77 / 0.80 / 0.82 | 0.99 / 0.99 / 0.99 | 2.29 / 1.64 / 1.28 |

- **Paired SVGP − training mean** (95 % cluster bootstrap over simulations): −0.115 [−0.142, −0.087], −0.184 [−0.208, −0.158], −0.217 [−0.244, −0.189] at B16 / B40 / B80.
- **Paired functional − training mean:** +0.95 [+0.54, +1.42], +3.87 [+2.02, +6.14], +8.90 [+5.76, +13.32].
- **SVGP calibration.** The SVGP intervals are conservative: 90 % intervals cover 99 % of bins, and 50 % intervals cover 77–82 %.

**Maximum depth A** (like-for-like runs; `summary_max_timing_exceedance.csv`):

| Model | median \|A error\| µm (B16 / 40 / 80) | median signed error µm | A 90 % coverage | Brier of P(max > u_ref) vs the event A > u_ref |
|---|---|---|---|---|
| **Scalar A GP** | **8.2 / 5.1 / 3.9** | −0.8 / −0.2 / −0.6 | 0.82 / 0.87 / 0.87 | 0.045 / 0.022 / 0.025 |
| Separable SVGP | 104.7 / 64.6 / 42.3 | +98.4 / +48.6 / +27.3 | 0.92 / 0.95 / 0.96 | 0.032 / 0.041 / 0.039 |
| Rank-3 functional | 206 / 387 / 4.1e9 | +184 / +387 / +4.1e9 | 0.74 / 0.72 / 0.80 | 0.063 / 0.042 / 0.070 |

- **Paired scalar − SVGP** (median \|error\|): −96 [−125, −81], −59 [−72, −47], −38 [−50, −31] µm.
- **Interval caveat.** The temporal-model A intervals are latent-trajectory intervals and exclude residual noise; the scalar interval includes noise.
- **Where the SVGP's A bias comes from (POST-HOC, `POSTHOC_svgp_A_estimator_diagnostic.csv`).**
  - The frozen estimator, the median of the maxima of posterior trajectories, is biased upward.
  - The maximum of the SVGP posterior *mean* is nearly unbiased (signed −0.2 / −1.2 / −1.8 µm), but still has a median error of 86 / 39 / 30 µm.
  - So the bias comes from posterior spread entering the sample maxima. Even the mean trajectory misses A by about 8× the scalar error at B80.

**Timing and exceedance** (SVGP; functional in parentheses; like-for-like runs):
- **Argmax timing error:** median 253 / 188 / 178 µs (functional 119 / 182 / 213 µs). The argmax is ill-conditioned on the near-flat keyhole plateau, so this is a weak timing metric.
- **Time above u_ref:** error median 212 / 66 / 42 µs (functional 301 / 292 / 453 µs). The median observed time above u_ref is 1,242 µs, so at B80 the SVGP error is about 3 % of the observed time.

**Truncated runs (T2-H8).** These are the five truncated runs that have a trajectory; H-e7dbd8e5ce has none.
- **Estimands differ:** the observed A of these runs is an observed-window maximum. Planned-horizon and observed-window predictions are different estimands.
- **SVGP medians over the six checkpoints:**

  | Run | planned-horizon maximum (µm) | observed-window maximum (µm) | observed A (µm) |
  |---|---:|---:|---:|
  | H-374c2f82c8 | 288 | 116 | 238 |
  | H-3fdf3f0635 | 370 | 187 | 252 |
  | H-6dae2a1270 | 543 | 200 | 298 |
  | H-ce04be44b1 | 139 | 124 | 87 |
  | H-2d632333b4 | 483 | 467 | 303 |

  - The large gaps between planned-horizon and observed-window values show how much depth history these recordings miss.
  - For three runs (H-374c2f82c8, H-3fdf3f0635, H-6dae2a1270) the observed-window prediction is far below the observed A: the SVGP underestimates the early rise.
- **Scalar A GP:** it predicts about 300 µm for the slow-scan truncated runs. This is the full-window value of similar runs; it cannot know that the record ends early.
- **Recording-end artefact (POST-HOC):** two of these runs, H-ce04be44b1 and H-374c2f82c8, end with invalid-bounds rows that the frozen rule sets to depth 0 (5 and 1 bins).
  - These bins dominate the worst SVGP error (H-ce04be44b1, RMSE 0.99).
  - Excluding them lowers the SVGP mean RMSE by 0.007 at each budget; no verdict changes.

**Matched pair and fast scans (T2-H7)** (`matched_pair_trajectories.csv`, `named_runs_predictions.csv`, `information_preserved_descriptive.csv`):
- **(a) OBS: the observed depth trajectories of G5 (recorded negative, A 115.6 µm) and G4 (recorded positive, A 112.3 µm) are nearly identical.**
  - Their RMS difference is 0.047 log1p (about 5 % in depth) over all 360 bins.
  - The SVGP's predictive spread for the difference is 0.45–0.76, 10–16 times larger; for the functional model it is 1.9–66.
  - A depth-trajectory model, even a perfect one, has no depth signal here that separates the two labels. Whatever distinguishes them is not in the monitored depth history at this resolution.
- **(b) PRED: the models' predicted difference between the two runs is larger than the true difference.** It is 0.08–0.38 for the SVGP, which is model noise, not signal.
  - In repeat 2 both runs are held out in the same checkpoint, so only their inputs differ. Even then the SVGP's predicted difference is 0.08–0.36.
  - At B40, repeat 1 (figure), its G4 prediction sinks to about 3.5–4.0 log1p after s ≈ 0.35, while both observed trajectories stay near 4.3.
- **(c) Label information, descriptive AUC on like-for-like rows (no classifier).**

  | Feature | All runs | Fast scans (VX > 0.85; 22 runs: 12 positive, 10 negative; exploratory) |
  |---|---|---|
  | Observed A | 0.976 | 0.758 |
  | Observed time above u_ref | 0.975 | 0.754 |
  | Scalar GP, predicted A (B16 / 40 / 80) | 0.969 / 0.969 / 0.965 | 0.69 / 0.69 / 0.65 |
  | SVGP, predicted A | 0.937 / 0.946 / 0.958 | 0.75 / 0.53 / 0.59 |
  | SVGP, predicted time above u_ref | 0.968 / 0.954 / 0.957 | 0.73 / 0.55 / 0.57 |

  - The canonical label agrees with the event "A > u_ref" in 95.4 % of runs, but in only 72.7 % of fast scans.
  - In fast scans, even the exactly observed depth features rank labels at only about 0.76. The predicted features vary between 0.53 and 0.75 across budgets, from just 22 runs.
  - Trajectory accuracy and label information are therefore different questions. The SVGP's better trajectories do not give it better label information than the scalar A GP.

**Information preserved by the representation (OBS, label-free; `information_preserved_representation.csv`).**
- The bin-mean compression at K = 360 keeps the trajectories to a median RMSE of 0.037 log1p (90th percentile 0.058).
- It loses a median 0.004 log1p at the peak (90th percentile 0.007), and the exact native maximum is kept as an extra training point.
- What the representation discards is sub-bin variation, below 3–14 µs depending on the run. Among the 130 like-for-like runs, the median near-peak episode lasts 269 µs and none is shorter than one bin.

**Runtime, memory and approximation fidelity** (`resources_and_runtime.csv`, `svgp_inducing_fidelity.csv`):

| Model | Fits | Median time per fit | Total | Peak memory |
|---|---:|---:|---:|---:|
| Scalar A GP | 30 | 0.06 s | 1.6 s | — |
| Rank-3 functional (3 coefficient GPs per checkpoint) | 90 | 1.3 s per checkpoint | 40 s | — |
| Separable SVGP, frozen (M = 400, 2000 iterations) | 30 | 166 s | 82.5 min | 0.60 GiB |
| SVGP, M = 800 (frozen check) | 1 | 505 s | 8.4 min | 0.52 GiB |
| SVGP, 6000 iterations (T2-PS1) | 5 | 384 s | 32 min | 0.44 GiB |

- **The frozen SVGP is not converged.** Its training loss was still falling at iteration 2000: the median change over the last block was −0.033.
  - With 6000 iterations the learned noise falls from a median of 0.012 to 0.004, and the held-out RMSE drops by 23 %.
  - In the same comparison (POST-HOC, `POSTHOC_svgp_it6000_A_error.csv`), the median A error drops from 60 to 45 µm. The scalar GP's error is 5.0 µm on the same rows.
  - The A 90 % coverage collapses from 0.96 to 0.49, so the longer-trained SVGP is overconfident about the maximum.
- **The inducing-point approximation is not stable at the frozen budget.** At `ckpt_r1_f1_B40`, M = 800 changes the predictive mean by 0.167 RMS and the predicted A by a median of 31 µm.
  - Its held-out RMSE is worse (0.309 vs 0.247), probably because 800 inducing points are even less converged after 2000 iterations.
  - The controlled example shows that the variational machinery itself is exact when M = N. The instability therefore comes from the optimization budget.

**Why the functional baseline failed (POST-HOC diagnosis; `POSTHOC_functional_failure.csv`, `POSTHOC_wellposed_checkpoints_comparison.csv`).** The diagnosis recomputes the frozen deterministic ALS basis; no coefficient GP is refitted.
- **Mechanism.** Paid runs whose recording ends early (s_obs = 0.20–0.35) see only the first 80–140 bins. On those bins the three basis functions are nearly collinear: the smallest singular value is down to 1e-4.
  - With the frozen ridge of 1e-6, these runs get coefficients up to 26,571, compared with a median of about 7.
  - The coefficient GPs are trained on these values. Their predictions for held-out runs then explode, reaching 1e47 µm for A.
  - At 21 of the 30 checkpoints at least one paid run has \|coefficient\| > 100, and the functional mean RMSE there is 7.1.
  - The failure grows with budget, consistent with more early-ending runs being paid: 0–4 such runs at B16, 2–6 at B40 and 6–11 at B80.
- **The other 9 checkpoints.** These are well-posed by a training-side criterion: no paid run has \|coefficient\| > 100. There the functional model is the most accurate trajectory model.
  - Mean RMSE: 0.256 for the functional model, 0.343 for the SVGP and 0.479 for the training mean. The functional model is lower than the SVGP at 8 of the 9 checkpoints.
  - Its A error is still 52 µm, against 5.1 µm for the scalar GP.
  - This is a post-hoc, selected comparison. It shows a fixable design flaw: a coefficient prior or regularization for partially observed runs. It is not evidence that the functional model is better.

**Representative predictions.**
- `track2/figures/track2_representative_B40_r1.png` shows the best, median and worst held-out SVGP runs at B40 (repeat 1), followed by G5, G4 and the late negative, with functional and SVGP 90 % bands, the scalar A prediction, u_ref and the planned horizon.
- `track2/figures/track2_errors_by_budget.png` shows the errors by budget on a log scale.

### Track 2 interpretation (HYP)

- **What the SVGP can and cannot do.** The input × time GP learns depth trajectories: it is clearly better than an input-free trajectory and improves with budget. But it is optimization-limited at the frozen budget, sensitive to the inducing-point count, and conservative pointwise.
- **The maximum depth.** A, the quantity behind the label rule, is predicted about 10× worse by both temporal models than by the scalar A GP. The trajectory models would not improve the classifier as replacements for the scalar target.
- **The matched pair.** Its depth trajectories are nearly identical, so neither model can separate its opposite labels through depth, and the observed trajectories cannot either.
- **Fast scans.** Within fast scans, exactly observed depth features reach only about 0.76 AUC.
- **What a temporal model could add.** It could contribute timing, exceedance and planned-versus-observed-window information that the scalar target cannot express. To be useful it first needs converged training (or natural-gradient updates), and the functional route needs a coefficient prior.

**Limitations.**
- There are only two repeats and the same 30 checkpoints, from the Week 19 shared paths. The paid paths are not adaptive to the temporal models.
- The fast-scan subset has only 22 runs.
- All post-hoc analyses are labelled and are not used for verdicts.

## Track 1 extension (2026-10-13) — DEV repeats 5–8 and a slope-sign guard

**Design.**
- **Freeze:** commit `c96eaefb`, pushed before any extension fit (`track1_ext/manifest_track1_ext.json`, `HYPOTHESES_TRACK1_EXT.md`).
- **Protocol:** the frozen Track 1 runner and protocol, unchanged (code hashes checked), on the remaining DEV repeats 5–8. DEV is 1–8; C1 and C2 were spent in Week 18.
- **Added ablation arm D: WHOLE E1 + guard.** It is arm A, except when the paid pairs are not separable and the logistic slope is ≤ 0. In that case the reversed root is not used, and u falls back to 111 µm, the engine's own single-class default.
  - Arm D ran on all 20 R3_NEW runs.
  - Its conditional runs on OLD and POOLED were not needed: arm A had no non-positive-slope step there.
- **Execution:** 200 runs, 14,568 scalar fits, 5.4 min with 4 workers × 1 thread, all `ok`.

**Results (PRED; BA-AULC up to B80; repeat bootstrap; `track1_ext/contrasts_r5_8.csv`, `contrasts_r1_8.csv`):**

| R3_NEW | Repeats 5–8 | Repeats 1–8 (8 repeats) |
|---|---|---|
| **ACTIVE − G3 (primary)** | **+0.056 [+0.009, +0.135]** | **+0.056 [+0.015, +0.103]** |
| ACTIVE − WHOLE | +0.084 [+0.054, +0.126] | +0.077 [+0.050, +0.106] |
| WHOLE + guard − WHOLE | +0.002 [−0.031, +0.039] | — |
| ACTIVE − (WHOLE + guard) | +0.082 [+0.074, +0.091] | — |
| WHOLE − G3 | −0.028 [−0.120, +0.085] | −0.021 [−0.080, +0.039] |

- **Mean BA-AULC on R3_NEW, repeats 5–8:** ACTIVE 0.734, G3 0.678, WHOLE + guard 0.652, WHOLE 0.650.
- **Per-repeat ACTIVE − G3 over repeats 1–8:** +0.062, −0.032, +0.067, +0.132, +0.004, +0.029, +0.176, +0.013. Seven of eight are positive.
- **Secondary endpoints on NEW, repeats 5–8** (ACTIVE / G3 / WHOLE + guard / WHOLE):

  | Endpoint | ACTIVE | G3 | WHOLE + guard | WHOLE |
  |---|---:|---:|---:|---:|
  | q20 | 0.799 | 0.706 | 0.740 | 0.693 |
  | Specificity | 0.494 | 0.404 | 0.327 | 0.440 |
  | Sensitivity | 0.974 | 0.953 | 0.977 | 0.860 |
  | Short-K sensitivity | 0.780 | 0.614 | 0.796 | 0.652 |
  | Brier | 0.064 | 0.085 | 0.068 | 0.137 |
  | AUC | 0.911 | 0.834 | 0.853 | 0.836 |

  - ACTIVE − G3: q20 +0.093 [+0.033, +0.179], AUC +0.077 [+0.023, +0.113], Brier −0.021 [−0.030, −0.012].
- **R3_OLD, repeats 5–8:** ACTIVE − G3 = +0.015 [+0.011, +0.020] and ACTIVE − WHOLE = −0.006 [−0.013, +0.001].
- **R1_POOLED, repeats 5–8:** ACTIVE − G3 = +0.006 [−0.000, +0.014].
- **QTT** (frozen definition, target = G3's mean BA at B40 over repeats 5–8, 0.687): ACTIVE reaches it in 4/4 repeats (16, 16, 20, 16); G3, WHOLE and WHOLE + guard each in 3/4.

**Hypotheses** (`track1_ext/hypothesis_verdicts.csv`):

| Hypothesis | Verdict | Note |
|---|---|---|
| X-H0 fidelity to the Week 18 caches | **FALSIFIED** (one run) | See the diagnosis below. |
| X-H1 primary: ACTIVE − G3 > 0 | **SUPPORTED** | +0.056; the interval excludes 0 on these four new repeats. |
| X-H2 ACTIVE − WHOLE > 0 | **SUPPORTED** | +0.084 |
| X-H3a guard identity | **SUPPORTED** | In the 11 runs without a non-positive slope, arm D equals arm A exactly. |
| X-H3b guard effect > 0 | **SUPPORTED by the letter, negligible** | +0.002 [−0.031, +0.039] |
| X-H4 OLD and POOLED | **SUPPORTED** | — |
| X-H5 threshold mechanism | **SUPPORTED** | ACTIVE's maximum u is 189.2 µm; all 10 WHOLE runs with u ≥ 200 µm had paid the late negative first. |

- **Fidelity diagnosis (OBS; `track1_ext/DIAG_g3_R1_POOLED_r8f1_divergence.*`).**
  - Arm A matches the caches everywhere: maximum |Δp| 5e-6.
  - Arm C matches in 59 of 60 runs. The exception is G3 on R1_POOLED repeat 8 fold 1, which differs from budget 24 onwards (maximum |Δp| 0.39).
  - The historical engine loop (`src.week18_engine.run`) reproduces the cache exactly with 4 BLAS threads. With 1 thread it follows the extension's path exactly, diverging at query 23.
  - The cause is therefore floating-point threading in one G3 run, not a code difference. The frozen result is kept.
  - The effect on the POOLED WHOLE − G3 mean is 0.0005. The diagnostic cost 146 G3 fits.

**Mechanism: what the guard shows (OBS from ledgers).**
- **The trap starts at startup.** In 9 of the 20 NEW runs, the startup set's only negative is the late negative (whole 312 µm).
  - The unguarded WHOLE then has a reversed slope (≈ −350) from the very first fit at B8, and stays at u ≈ 308 µm for 2–73 steps.
- **The guard removes the trap.** It sets u = 111 µm for 1–5 steps, until straddle pays a second negative; ordinary positive-slope learning then resumes. Sensitivity rises from 0.860 to 0.977 and Brier falls from 0.137 to 0.068.
- **Specificity falls, so BA does not change.** It drops from 0.440 to 0.327 because the whole-record maximum separates NEW labels poorly once a sensible threshold is used.
- **Conclusion (HYP, supported by X-H3c: +0.082 [+0.074, +0.091]):** ACTIVE's advantage over WHOLE on NEW comes from the response target, the active-window maximum. It does not come from avoiding the reversed-slope root.

**Decision (frozen rule, `track1_ext/decision.json`): C3 PROTOCOL DRAFT, not executed.**
- **The draft:** `c3_draft/C3_PROTOCOL_DRAFT.md`.
- **Primary rule:** R3_NEW ACTIVE − G3 ≥ +0.02 with interval > 0, plus no loss below −0.01 on OLD or POOLED.
- **Chance of passing:** resampling four of the eight DEV repeats gives about **60 %** for the primary rule. The bar alone is met in 87 % of draws, but the interval excludes 0 in only 62 %.
- **Optimism:** DEV numbers are optimistic, because A was defined after the NEW labels had been seen.
- **Ownership:** C3 is untouched. Spending it is the owner's decision.

## C3 confirmation (2026-10-13) — ACTIVE E1 + straddle vs G3 + margin

**Freeze and execution.**
- **Approval:** the owner approved the C3 draft in chat ("C3 taslağını onaylıyorum, dondur ve çalıştır").
- **Freeze:** `c3/FREEZE_C3.md` (commit `4164f67b`). It was committed and pushed before any C3 task object was built. The decision rule, candidate, reference and predictions are unchanged from the draft.
- **Data:** block C3 (repeats 17–20, 5 folds, three tasks), used once through the frozen Track 1 runner at 4 workers × 1 BLAS thread.
- **Execution:** 180 runs, 13,128 scalar fits, 5.2 min, all `ok`. Nothing was rerun.
- **Startup checks** (`c3/c3_tasks_and_startup.csv`): no single-class start, and the A-unavailable run is in no startup set.

**Locked decision (PRED; `c3/decision_c3.json`): NOT CONFIRMED AT THE FROZEN BAR.**

| Rule | Result | Passed? |
|---|---|---|
| Q3a: R3_NEW BA-AULC ACTIVE − G3 ≥ +0.02 with interval > 0 | **+0.007 [−0.036, +0.053]** | no |
| Q3b: R3_OLD ACTIVE − G3 ≥ −0.01 | +0.011 [−0.007, +0.031] | yes |
| Q3b: R1_POOLED ACTIVE − G3 ≥ −0.01 | +0.004 [−0.002, +0.008] | yes |

- **Per-repeat R3_NEW ACTIVE − G3:** −0.055, −0.008, +0.073, +0.018.
- **Mean BA-AULC on R3_NEW:** ACTIVE 0.695, G3 0.688, WHOLE 0.651.
  - G3 was strong in repeat 17 (0.780) and weak in repeat 19 (0.576).
  - ACTIVE ranged from 0.649 to 0.725.
- **Against the prediction:** DEV predicted the primary rule would pass with probability about 0.60. It did not pass. The C3 estimate (+0.007) is 1.4 standard errors of a four-repeat mean below the DEV mean (+0.056, SD 0.069). That is consistent with sampling variability and with the expected optimism of DEV, since A was defined after the NEW labels had been seen.

**Reported, not decisive (PRED; `c3/contrasts.csv`)** — R3_NEW, ACTIVE − G3:

| Endpoint | Difference [95 % interval] |
|---|---|
| q20 | **+0.069 [+0.033, +0.115]** |
| AUC | **+0.095 [+0.035, +0.156]** |
| Brier | **−0.024 [−0.031, −0.016]** |
| Sensitivity | +0.033 [+0.023, +0.042] |
| Short-K sensitivity | +0.279 [+0.208, +0.391] |
| Specificity | −0.018 [−0.096, +0.061] |

- **Reading:** ACTIVE ranks and calibrates NEW runs better than G3, and finds far more short-K positives. Its balanced accuracy at p = 0.5 does not differ, because it does not gain specificity.
- **ACTIVE − WHOLE on R3_NEW:** **+0.044 [+0.023, +0.067]**. The target ablation replicates.
- **WHOLE − G3:** −0.037 [−0.090, +0.017].
- **QTT** (target = G3's mean BA at B40 over C3, 0.688): ACTIVE reaches it at the first grid point in 4/4 repeats; G3 and WHOLE in 3/4.
- **Mechanism (OBS):**
  - WHOLE reaches u ≥ 200 µm in 10 of 20 NEW runs; in every one the late negative had been paid first. In 4 of them it is the only paid negative, and WHOLE has 201 reversed-slope steps in all.
  - ACTIVE's maximum u is 199.1 µm, with no reversed slope.
- **POST-HOC observation:** ACTIVE's NEW BA falls slightly with budget (0.722 at B16, 0.705 at B40, 0.695 at B80). G3's is 0.678, 0.688 and 0.670.

**Interpretation (HYP).**
- **What is not confirmed:** the DEV advantage of ACTIVE E1 + straddle over G3 + margin in NEW balanced accuracy.
- **What replicates:** two DEV findings hold on C3.
  - The active-window target beats the whole-record target, and the reversed-slope trap explains part of WHOLE's failure.
  - ACTIVE has better ranking, calibration and short-K detection than G3.
- **Remaining limitation:** ACTIVE's specificity on NEW, which stays below 0.5. The binary label of fast scans is not captured by a single depth threshold.
- **Status of C3:** it is now spent. Any further candidate needs a new data source or a new confirmation design.

## Delivery for Ioan

G5 = H-b302fc6cbd, frame 81, was added in front, side and top views (`ioan_addendum/`).
- **Provenance:** fetched at the pinned NEW revision and verified by LFS SHA-256. All three images are usable after a visual check (usability only).
- **Why frame 81:** it is the last frame before G5's depth maximum (−4.84 µs). The already-linked frame 82 lies +0.18 µs after the maximum, past a sharp drop in monitored depth (114.3 → 89.1 µm).
- **Contents:** a side-by-side sheet of frames 81 and 82 at the same scale. Labels and depths are in a separate `KEY_ADDENDUM.md`.
- **Week 19 gallery:** only a pointer section was appended to `GALLERY.md` and `KEY.md`; the earlier content is byte-identical (tested).

## Execution, resources and deviations

- **Scalar learner fits:** 13,101 in Track 1 plus 30 Track 2 refits of the scalar reference, giving 13,131 of the 15,000 cap.
- **Temporal/functional fits:** 128 of the 160 cap: 90 functional coefficient GPs, 2 validation fits, 30 frozen SVGP fits, 1 frozen check with M = 800 and 5 post-start fits.
- **CPU and memory:**
  - Fitting and evaluation jobs ran one at a time with at most 4 threads (Track 1: 4 workers × 1 thread; SVGP: 4 torch threads).
  - Only short single-thread checks ran beside the SVGP job.
  - Peak memory per process was 0.6 GiB.
- **Wall time:** about 3.0 h of the 8 h limit (19:45 to 22:41 UTC). No run was restarted or discarded.
- **Deviations, all recorded in the ledger:**
  - **Post-hoc analyses** are marked `POSTHOC_`.
    - Track 1: episodes, sustained QTT and the threshold-rule recomputation.
    - Track 2: functional-failure diagnosis, the well-posed-checkpoint comparison, the SVGP A-estimator diagnostic, A error at 6000 iterations and the terminal-invalid-rows sensitivity.
  - **T2-PS1 (post-start).** Declared from training traces only, before any held-out evaluation. **Falsified:** −23.0 %.
  - **Evaluation rules.** Written after fitting had started but before any scoring (`0274e5a1`).
  - **Evaluation bug.** The named-run lookup used non-unique H suffixes; it was fixed and the evaluation re-run, with the frozen tables byte-identical.
  - **Commit message error.** The `d50e43b9` message says 7 trap runs; the correct count is 6.
  - **Correction to the frozen T2-H8 wording.** It speaks of "six truncated runs". One of the six, H-e7dbd8e5ce, has no trajectory, so five are reported.
- **Continuation round (2026-10-13, Track 1 extension; counted separately with the same caps):**
  - 14,714 scalar fits of 15,000, including the 146 diagnostic G3 fits; no temporal fits.
  - About 25 min; at most 4 threads.
  - Cumulative across both rounds: 27,845 scalar fits and 128 temporal/functional fits.
  - C3 untouched.
- **New environment:** a git-ignored `.venv` with torch 2.13.0+cpu and gpytorch 1.15.1 was created for the sparse variational GP.

