# PROTOCOL IR: physical outputs, depth and the label

Registered 2026-10-31 around 16:30 UTC, before any number of parts A–G is computed.

Every rule below is fixed now. Changes after any result are recorded as amendments with their time and reason. Errata only: no earlier output is overwritten.

## 0. Disclosure: first look before registration (ledger row IR-PRE)

On 2026-10-31, before this protocol, Opus computed a one-off descriptive look for the owner. The scripts and their outputs are in `prelook/`, copied verbatim and not used by any later step:

- **Width extraction** by the unchanged Week 19 code. Its depth reproduces the pooled A to 6e-14 µm on 540 runs; one known bounds/time-mismatch run fails.
- **Spearman correlation with depth** (534 good records):

  | output | ρ |
  |---|---|
  | log h | 0.945 |
  | KE | 0.90 |
  | max temperature | 0.85 |
  | velocity spike ratio | 0.85 |
  | laser | 0.82 |
  | total energy | 0.80 |
  | particles | 0.80 |
  | spike time | 0.73 |
  | width | 0.50 |

- **Partial correlation after linear removal of the 4 log inputs:** ≤ 0.30, except total energy and particles at 0.53.
- **Label AUC alone:** depth 0.999, width 0.64.
- **10-fold CV logistic on true values** (n = 479):

  | features | log loss | BA |
  |---|---|---|
  | h + depth | 0.0665 | 0.975 |
  | h + depth + width | 0.0668 | 0.975 |
  | h + depth + 7 other outputs | 0.0704 | 0.964 |

**How this look shaped the design:**
- It made Opus add width and temperature next to KE as co-outputs, and add the ORACLE_CHAIN diagnostics.
- It sets no threshold.
- Parts A–F recompute everything with uncertainty, so those first-look numbers are superseded, not reused.

## 1. Questions

| id | question | Ioan's wording |
|---|---|---|
| Q1 | How strongly is each physical output tied to melt-pool depth? Does the tie survive once the inputs are known? Is it the same in conduction and Keyhole runs? | "relation between depth and kinetic energy"; "kinetic energy, temperature versus depth" |
| Q2 | How are melt-pool width and depth related? Is width, or the depth/width aspect ratio, informative about the regime? | "correlation between melt pool width and melt pool depth" |
| Q3 | Does exploiting these relations reduce the number of simulations needed for C1's early accuracy? | the chain inputs → hidden quantity → depth → label, in the thesis's terms |
| Q4 | Within one simulation, how are depth(t) and the other monitor signals (the DAT files) coupled in time? Does any signal move before depth at Keyhole onset? | "that connection with the DAT files" |

## 2. Data (part P1)

**D1 – geometry per run.** Computed by the unchanged `src.week19_series.process` on the verified raw copy. The bounds come from `position-bounds_melt.dat`; the active mask is Week 19's, and so are T0 and the first-active-frame time. Each value is "UNAVAILABLE" if the extraction fails; nothing is repaired.

| quantity | definition |
|---|---|
| W_A (µm) | maximum over active rows of the y-extent (full melt-pool width); same window and statistic as the pooled depth A = active-window maximum |
| W_T0 (µm) | median width over T0 rows |
| W_atA (µm) | width at the row of the maximum active depth |
| L_A (µm) | maximum active x-extent (length) |

- **Acceptance V1:** the recomputed A equals the pooled `A_um` with |Δ| ≤ 1e-9 µm for every run with finite A.

**D2 – active-window maxima of other channels** (descriptive extras, same window as A): KE_A, T_A and V_A (kinetic energy, maximum temperature, maximum velocity). The pooled T0 summaries remain the primary definitions; they are the audited `POOLED_MANIFEST` columns.

**D3 – time series** (part F):
- **Channels:** time, depth, width, length, KE, maximum temperature, maximum velocity, transferred laser power, total energy, particle number. These are the monitor files of the run.
- **Row alignment:** a channel is used only if it is row-aligned with `time.dat`. If it is not, it is UNAVAILABLE for that run: recorded, never truncated.
- **Window:** the active window.

**D4 – learner contract.**
- `src/ir_data.py` provides `paid_W(rev)`: log W_A for the PAID rows of a `src.rc19_pool.Reveal`, NaN elsewhere.
- KE and temperature come from `Reveal.paid_Y()` (`log_ke_T0_nJ`, `tmax_T0_K`).
- **Acceptance V2** (shadow test): permuting the width / KE / T values of all unpaid rows, test rows included, must leave every candidate's predictions identical (|Δ| = 0).

**Good records:** `short_record == False` and the needed values finite. Every sample size is reported.

## 3. Part A: correlation structure (DESCRIPTIVE, evaluator view, all runs, true values)

**A1 – pairwise.**
- **Pairs:** Spearman ρ between log A and each of:
  - log W_A, log W_T0, log W_atA, log L_A;
  - log_ke_T0_nJ, tmax_T0_K, vmax_spike_logratio, vmax_spike_us, laser_T0_W, log_etot_T0_J, log_npart_T0;
  - log KE_A, T_A, log V_A, log h.
- The full matrix among all of these is reported as well.
- **Uncertainty:** 95 % percentile bootstrap, 2000 resamples, seed 31.
- **Subsets:**
  - all good records;
  - by class (conduction / Keyhole);
  - by batch (OLD / NEW; reported, never used in a learner);
  - the pooled boundary set: `boundary_flags` on all runs as one batch, top 20 %, evaluator only.

**A2 – beyond the inputs.** Three ways to remove what the inputs explain:
1. Rank-residual correlation after linear regression on log h.
2. The same on the 4 log inputs.
3. Correlation of out-of-fold GP residuals:
   - 10 folds, seed 31;
   - the C1-style GP for every output: h-trend with b = 3, Matérn 3/2 ARD, C1's MAP hyperprior, 2 starts, Q-rule noise;
   - fitted on 9 folds of all good runs, predicting the 10th.

   Its residual correlation matrix is the precondition for any multi-output transfer: shared variation that the inputs do not explain.

**A3 – width–depth physics.**
1. Theil–Sen slope of log A on log W_A, per class.
2. Aspect ratio A / W_A (and W_A / A) by class: median and IQR.
3. Zero-parameter literature criteria, "Keyhole if W/D ≤ c" for c ∈ {1.5, 2.0, 2.5}. Sources are fixed in part G. BA, sensitivity and specificity are reported against the label.
4. 10-fold CV threshold classifiers on log(D/W), log D and log W, each alone: BA and AUC.

**A4 – label information beyond depth (oracle, true values).**
- **CV design:** repeated stratified 10-fold CV, 20 repeats, seeds 0–19.
- **Model:** L2 logistic, C = 1, standardised on the training folds.
- **Feature sets:**
  - [h], [D], [h, D];
  - [h, D, X] and [h, X] and [X] for each X of A1;
  - [h, D, all T0 outputs] and [h, D, W_A, all T0 outputs].
- **Non-parametric check:** HistGradientBoosting (max_depth 3, 200 iterations, learning rate 0.05, no early stopping, random_state = repeat), comparing [h, D] with [h, D, X] for X ∈ {W_A, KE, T}.
- **Metrics:** log loss, BA (threshold 0.5) and AUC, on the common sample with every feature finite.
- **Contrasts:** paired differences against [h, D]; the mean over repeats with a 95 % t-interval over repeats.

**A5 – mediation.** CV log loss for five feature sets:
- the 4 log inputs;
- the 4 log inputs with quadratic and pairwise terms;
- [D];
- [inputs, D];
- [inputs, D, W_A].

The question: does depth carry the input → label information?

## 4. Part B: learnability at small budgets (DEV-DESCRIPTIVE)

**Learner-paths:** the recorded C1-selected paths, 272 in total. They are paid-id prefixes; no new query.

| set | source | learner-paths |
|---|---|---|
| STD 163–202 | EA `validation_std` | 200 |
| K5 41–48 | `validation_k5` | 40 |
| K4 25–32 | `validation_k4` | 32 |

**Budgets:** b ∈ {8, 12, 16, 20, 24, 32, 40, 60}.

**Outputs:**
- log A: C1's own depth model, R0 below;
- log W_A, log_ke_T0_nJ, tmax_T0_K, vmax_spike_logratio, laser_T0_W, log_etot_T0_J, log_npart_T0;
- each fitted by the C1-style GP on the paid finite values.

**Metrics on test rows** with finite truth and a complete record:
- standardised RMSE: RMSE divided by the pooled SD of that output over good records;
- R²_test = 1 − SSE / SST, around the test mean;
- 90 % interval coverage (latent + noise);
- depth RMSE on q20.

**Reported:**
- per budget, the median over learner-paths of the budget at which R²_test first reaches 0.8;
- the number of learner-paths that never reach it.

## 5. Part C: method screen. Do co-outputs improve depth at unopened inputs? (DEV)

**States:** the learner-paths and budgets of part B.

**Contingency:**
- If the timing smoke projects more than 8 worker-hours for part C, STD is reduced to 163–182 (100 learner-paths).
- This is decided from timing only, before any part C result.

**Reference R0:** C1's depth model, i.e. `src.ea_cand.depth_fit_cand` with SYSTEMS["C1"] (h-trend, MAP, 2 starts), on the paid prefix. It gives the latent mean and variance of log A at the test rows.

**Candidates (6, carried at most 1).** Each is given for a co-output q ∈ {W: log W_A, KE: log_ke_T0_nJ, T: tmax_T0_K}.

*LMC_q:* a bivariate GP of (log A, q), a linear model of coregionalisation with two latent processes.
- **Covariance:**

  K = Σ_{r=1,2} a_r a_rᵀ ⊗ k_r(x, x′) + blockdiag(9 z_h z_hᵀ, 9 z_h z_hᵀ) + diag(σ²_output · w)

  - k_r is a unit-variance Matérn 3/2 ARD kernel with lengthscales ℓ_r.
  - Each output carries its own h-trend, with coefficient ~ N(0, 3²) integrated.
- **Outputs:** standardised on the paid good records.
- **Priors:**
  - log ℓ_rk ~ N(0, 1);
  - a_ij ~ N(0, 1);
  - log σ²_i ~ N(log 0.01, 1.5²).
- **Fit:** MAP by L-BFGS-B from 2 fixed starts:
  1. ℓ = 1, a = [[0.9, 0.3], [0.3, 0.9]], σ² = 0.1;
  2. ℓ₁ = e^{−0.5}, ℓ₂ = e^{0.5}, a = [[0.7, 0.5], [0.5, 0.7]], σ² = 0.01.
  The lowest objective is kept.
- **Missing values:** a missing q entry is dropped (heterotopic data).
- **Q rule:** short records get noise × 1e4 on both outputs.

*CHAIN_q* (Ioan's chain):
- **Depth model:** a GP with basis H = [z_h, s(q̂)]; both coefficients ~ N(0, 3²) are integrated. The residual is Matérn 3/2 ARD, with C1's MAP prior and starts.
- **q̂** is the C1-style GP for q:
  - at the paid rows: honest K = 10 out-of-fold predictions; fold of the j-th paid run = j mod K;
  - at the test rows: the full-fit prediction.
- **s(·)** standardises with the paid out-of-fold mean and SD.

**Controls and diagnostics (never carried):**

| name | definition | purpose |
|---|---|---|
| SUM2 | depth-only GP with K = Σ_r a_r² k_r + 9 z_h z_hᵀ + noise (LMC priors and starts restricted to depth) | separates a richer depth kernel from transfer |
| ICM_W | LMC_W with ℓ₁ = ℓ₂ tied | theory check: noise-free isotopic data cancel inter-task transfer |
| ORACLE_CHAIN_q | CHAIN_q with the TRUE q at paid and test rows (evaluator only) | the value of knowing q everywhere |

**Metrics per state** (test rows of the learner-path):

| id | metric |
|---|---|
| M1 | proxy BA: the BA of g*(z_h, â) ≥ 0.5 against the labels (definition of g* below) |
| M2 | RMSE of log A on good test rows, and on the q20 test rows |
| M3 | NLPD on good test rows (latent + noise variance) |

g* is an L2 logistic (C = 1) on standardised [log h, log A]. It is fitted once on all good records with true values, is evaluator-only, and is frozen and recorded before the screen (acceptance V6).

**Aggregation:**
- Window mean per learner-path, then mean per cluster (STD repeat, or block-startup cluster).
- One-sided 95 % t-bounds across clusters.
- Proxy BA needs both classes on the test rows; other learner-paths are counted, not used.

**Carry rule** (candidate − R0; all four must hold):

| rule | condition |
|---|---|
| S1 | STD proxy-BA, early budgets {8, 12, 16, 20, 24}: mean ≥ +0.005 and LCB > 0 |
| S2 | STD q20 log-depth RMSE, early: relative change ≤ −3 % and UCB < 0 |
| S3 | STD proxy-BA, late budgets {32, 40, 60}: LCB ≥ −0.003 |
| S4 | geometric (K5 + K4 clusters) proxy-BA, all budgets: LCB ≥ −0.005 |

- **Choice:** among the passing candidates, the largest S1 mean is carried. Ties go to the simpler candidate: CHAIN before LMC, then W before KE before T.
- **No candidate passes:** parts D and E are not run, and the method answer is "NOT SHOWN on DEV".

## 6. Part D: downstream DEV test (only if a candidate is carried)

**Pipeline:** C1's pipeline with R0 replaced by the carried candidate:
- both in the honest K = 10 out-of-fold paid features and in the full fit;
- for CHAIN, nested: q̂ for each depth fold's training set is recomputed with its own inner K = 10 cross-fit, so no run's own outcomes enter its own feature;
- classifier `src.rc22_common.phr_family` on [z_h, â], one-class rule and threshold unchanged.

**Grid:** the part C learner-paths, at budgets 8–24 every 1 and 28–60 every 4.

**Reference:** the recorded C1_own probabilities.
- A reproduction check runs at b ∈ {12, 40} on 10 units: max |Δp| ≤ 1e-6, acceptance V5.

**DEV rule** (candidate − C1; all four must hold):

| rule | condition |
|---|---|
| D1 | STD BA-AULC on the evaluated budgets 8–24: mean ≥ +0.004 and LCB > 0 |
| D2 | STD BA-AULC 28–60: LCB ≥ −0.003 |
| D3 | geometric BA-AULC on all evaluated budgets: LCB ≥ −0.005 |
| D4 | STD log loss on budgets 8–24: UCB ≤ +0.005 |

## 7. Part E: fresh test (only if D passes)

- A freeze commit is made, then `PROTOCOL_IR_FRESH.md` is registered before any fresh result.
- **Fresh IDs** (unused): STD 383–422, K5 49–56, K4 33–40.
- **Runs:** own-path C1 + margin and candidate + margin, up to B60.
- **Timing:** no part E start after 2026-11-02T00:00Z.

## 8. Part F: within-run time coupling (DESCRIPTIVE)

**Data:** all runs with the needed aligned channels (D3), on the active window.

| step | what is computed |
|---|---|
| F1 | within-run Spearman ρ between depth(t) and each of W, L, KE, T, V, laser, E_tot and N_part (t) over active valid rows; distribution by class |
| F2 | lead–lag on the post-onset active window (first C/K frame to cutoff), resampled to a uniform 1 µs grid (linear): τ* = argmax over τ ∈ [−100, 100] µs of corr(depth(t), s(t − τ)), for z-scored levels and for 20 µs-smoothed first differences; τ* > 0 means s leads depth; median τ*, share τ* > 0 and peak correlation, by class |
| F3 | Keyhole onset: every Keyhole run aligned at the time of its first K frame; event-triggered mean of z-scored signals over [−100, +100] µs, with 95 % bootstrap bands over runs |
| F4 | early-window information (exploratory): the median of each signal over the first 25 % of the active window, against the final A (Spearman) and the label (AUC) |

## 9. Part G: literature check

1. Melt-pool geometry criteria for Keyhole vs conduction (W/D thresholds) and normalised enthalpy.
2. Multi-output GP transfer theory: cancellation of inter-task transfer under isotopic, noise-free data, and autokrigeability.
3. Auxiliary-output and multi-task learning for AM process maps.

Each source is cited exactly. A claim is labelled LITERATURE and never changes a rule above.

## 10. Acceptance tests (code, before any part B–D result)

| id | test |
|---|---|
| V1 | width extraction reproduces A |
| V2 | paid-only shadow test |
| V3 | LMC: analytic vs numeric gradient (relative error ≤ 1e-5). Reduction: a = diag with one latent off, and identical kernels → equals the single-output GP (≤ 1e-8). Synthetic noise-free isotopic ICM: depth prediction equals the single-output one (≤ 1e-6) |
| V4 | CHAIN: a zero s(q̂) column gives exactly R0 (≤ 1e-10); a run's own q and depth never change its own out-of-fold q̂ |
| V5 | R0 inside C1's pipeline reproduces the recorded C1_own probabilities (≤ 1e-6) |
| V6 | g* is frozen; its coefficients and its BA on true depths are recorded |

## 11. Resources and stops

- **Workers:** at most 3 single-thread workers.
- **Window:** 2026-10-31T16:09:01Z to 2026-11-02T16:09:01Z.
- **Part C** must finish by 2026-11-01T18:00Z; otherwise it continues only on the reduced STD set.
- **Part E** does not start after 2026-11-02T00:00Z.
- **Failures:** a failed unit is recorded and never silently dropped. If more than 2 % of the units of a part fail, that part is reported INCOMPLETE.

## 12. Evidence labels and the one final verdict

**Labels:**
- DESCRIPTIVE: parts A and F; evaluator view, true values;
- DEV: parts B–D;
- FRESH: part E;
- LITERATURE: part G.

**The report ends with exactly one of:**

| verdict | condition |
|---|---|
| **V-A ANSWERED, NO GAIN** | the relations are measured; using the other outputs does not reduce simulations (C or D fails) |
| **V-B GAIN ON DEV ONLY** | D passes; E fails or is not run |
| **V-C GAIN CONFIRMED** | E passes |
| **V-D INCOMPLETE** | a required part could not finish within the window |
