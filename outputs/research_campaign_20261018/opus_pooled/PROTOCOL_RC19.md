# RC19 — pooled, from-scratch active learning on one 541-simulation pool (Opus; frozen before any final-repeat run)

**Status:** FROZEN by `final/RC19_FINAL_MANIFEST.json` (SHA-256 of the code, the data files and this protocol), committed before any final repeat runs.
- Final workers refuse to start if any frozen hash changed (`src/rc19_final.check`).
- The report generator `src/rc19_report.py` (which computes the primaries) is part of the freeze.

**Owner instruction:** 2026-10-19, "Unified-pool, from-scratch active learning".

**Budget:** the research-campaign-20261018 clock and deadline are unchanged (2026-10-20 08:41:20 UTC). Opus uses 2 threads; Astra keeps her 2.

**Evidence label: DEV.** All 541 simulations were inspected in earlier weeks.
- Pooled splits are new partitions of the same runs. Repeats and folds are correlated, not independent physical replications.
- C3's decision stands. C4, real-data Stage A, the simulator, paid cloud resources, main merges and outbound messages are not used.
- RC18's 21-query result is a conditional, archive-based transfer result and is **not** carried into this experiment.

## 1. Question

Our deployment starts without a labelled archive. We choose a simulation, pay for it, receive its result and update the learner.

**Main question:** how well does each method learn the following with a small TOTAL number of revealed simulations (startup included)?
- (A) the physical responses;
- (B) a physically defined region;
- (C) the Keyhole regime label.

The 405 + 136 records form ONE prospective pool. Batch identity selects no model, prior, threshold or acquisition; it is kept for provenance and for evaluator-only corner diagnostics.

## 2. Information contract

Implemented by `src/rc19_pool.Reveal` and validated before development: `data/PAID_ONLY_VALIDATION.json` PASS. Each arm was rerun with every never-paid outcome randomised and gave an identical path and identical predictions.

- **Before any query:** the inputs x = (P, VX, LS, ST) of all candidates are public. Outcomes and labels are hidden.
- **Startup:** the common feature-only startup is the first 8 points of the task's label-free maximin path. It is PAID and counted in every budget.
- **One query = one simulation.** It reveals the run's canonical label, active-window depth, physical summaries and its own record quality. Missing channels and truncated records keep their cost.
- **Updating:** after each query the learner refits on ALL revealed rows. This is ordinary sequential updating, as in G3/E1.
  - Inference shortcut: for model-independent designs (MAXIMIN, RANDOM), regression fits are made only at the recorded budgets. They cannot change the choice.
- **Never in a learner:**
  - free source outcomes, OLD emulators, full-data hyperparameters, global class counts, full-data label thresholds;
  - monitor-informed feature selection;
  - test labels or outputs, q20, short-Keyhole membership, region truth.
- **E1's one-class default** of log(111 µm) is a full-data constant and is never used. While one class has been revealed, every arm predicts the paid class rate and follows the label-free path. Every such query is counted.

## 3. Data, splits, evaluator-only fields

**Data:** `data/POOLED_MANIFEST.csv`, 541 rows; the 49 Bug-withheld NEW entries stay excluded. Checks are in `data/POOLED_CHECKS.json`:
- unique IDs; no duplicate or repeated conditions;
- the PHYS_AL and RC18-loader definitions agree;
- the batches are compatible where they overlap.
- **Notes:**
  - spike duration is zero-inflated;
  - maximum temperature shows a modest −32 K NEW-vs-OLD local offset, which is not blocking;
  - 56 OLD runs lack 6 channels; they stay candidates and keep their cost.

**Splits:** per repeat, a seeded random 5-fold partition (seed [1919, r]), not stratified by batch or label. Pool = 4 folds (432–433 candidates); test = 1 fold (108–109).
- Development: repeats 1–2 (seen; ledger RC19-DEV).
- **Final: repeats 3–10, 8 repeats × 5 folds**, never run before this freeze.
- Arms share the split, the startup and the seeds.

**Evaluator-only fields:**
- **q20:** the 20 % of each test fold closest to the pooled boundary (nearest opposite-class distance on the 541-run batch).
- **Pooled short-Keyhole:** has_keyhole = 1 and 0 < frac_K_FCK < 0.10 (22 runs). The NEW-only original set (10 runs) is a continuity column.
- **Batch-wise diagnostics:** in particular, conduction recall on NEW test runs, the fast-scan corner.

## 4. Workstreams, arms and pre-declared primaries

Every comparison is paired by repeat; test predictions of a repeat are pooled over its 5 folds.

**Verdict rule (all primaries):**
- **BETTER (DEV)** iff the mean paired Δ ≥ the practical margin and Δ > 0 in ≥ 7 of the 8 repeats.
- **WORSE (DEV)** iff the mean Δ ≤ −margin and Δ < 0 in ≥ 7 repeats.
- Otherwise **NOT DIFFERENT (DEV)**.
- The margin is 0.02 for every workstream (R²-AULC or BA-AULC).

### A. Physical outputs (job `final-reg`, horizon B80, recorded every 4 queries)

**Models:**
- **M0:** per-output GP, Matérn-3/2 ARD on standardised log inputs, constant mean, ML-II.
- **M0Q:** M0 + paid-record quality. A paid run whose record ended before 0.95 × its own planned end gets noise × 10⁴; its cost and evaluation remain.
- **SHQ:** ARD lengthscales shared by the 8 outputs of the paid runs + Q.
- The candidate SHQH (log h coordinate as a 5th input) was dropped in development: R²-AULC −0.005 vs SHQ.

**Designs:** MAXIMIN for SHQ, M0 and M0Q; seeded RANDOM and MOIVR for SHQ and M0Q. MOIVR's target set is the 8 primary outputs.

**Primary outputs (one set for the pooled benchmark):** log A, log KE T0, spike log-ratio, spike duration, laser T0, temperature T0, log total energy T0 and log particle number T0.

**Absolute levels** (held-out R²; 0.9 × the development full-pool attainable R², rounded down to 0.05, never from final outcomes):

| Output | Level |
|---|---|
| log A, log KE, laser, temperature | 0.85 |
| spike log-ratio, log total energy, log particle number | 0.80 |
| spike duration | 0.60 |

For reference, the development full-pool held-out R² ranges from 0.988 (laser) down to 0.703 (spike duration).

**PRIMARY A:** SHQ vs M0 under the identical MAXIMIN design. Endpoint: R²-AULC over B8–B80, the mean over recorded budgets and the 8 outputs. Development, repeats 1–2: +0.034 / +0.018.

**Secondary (exploratory, all repeats shown):**
- quality M0Q − M0 and sharing SHQ − M0Q;
- acquisition MOIVR − MAXIMIN and RANDOM − MAXIMIN given SHQ and given M0Q;
- SHQ − M0Q under MOIVR;
- accuracy, cov90 and NLPD at B16 / B40 / B80;
- per-output and joint endpoints with censoring;
- batch diagnostics.

### B. Velocity-spike region {spike log-ratio ≥ log 2} (job `final-region`, horizon B60, every budget recorded)

The threshold keeps its RC18 physical meaning (99.9th-percentile melt velocity at least twice its median) and is not tuned.

**Arms:** SHQ and M0, each with STRADDLE (1.96 σ − |μ − τ|), MAXIMIN, RANDOM and TRUVAR (`rc18_gp.truvar_lse`).
- TRUVAR settings are fixed: β = 1.96, η = 0, latent-variance reduction over the still-unclassified set, and a fallback to straddle when that set is empty.
- This implementation does not settle the published TruVaR family.

**PRIMARY B:** STRADDLE vs MAXIMIN under SHQ, BA-AULC over B8–B60. Development: +0.031 / +0.030.

**Secondary:**
- SHQ − M0 under STRADDLE and under MAXIMIN;
- TRUVAR − STRADDLE; RANDOM − MAXIMIN;
- both recalls at B16 / B24 / B40 / B60;
- queries to BA ≥ 0.95 (absolute; confirmed at b and b + 4), with censoring;
- collection (band share of the post-startup paid runs) vs learning.

### C. Keyhole label (job `final-label`, horizon B60)

**Arms (equal start and total budget):**
- **G3_MARGIN:** Week 18 G3, a direct GP classifier on x.
- **E1_STRADDLE and E1_MAXIMIN:** Week 18 E1, a depth GP with a depth-to-label threshold from the currently revealed pairs only.
- **PHYSCF_ATS_MARGIN:** the from-scratch physical-output classifier.
  - An SHQ response model for log A, maximum temperature T0 and spike log-ratio is fitted on the paid runs.
  - g is an L2-logistic model (C = 1) trained on the paid runs' LEAVE-ONE-OUT predicted outputs (cross-fitted).
  - It is deployed on the predictive means at new x, so training and deployment see the same kind of input.
- **Ablations:**
  - PHYSCF_A_MARGIN: depth only;
  - PHYSMC_ATS_MARGIN: g trained on measured outputs, deployed by averaging over 200 draws from the response predictive distribution;
  - PHYSCF_ATS_MAXIMIN: acquisition control.
- **Development-only candidates not carried forward:** PHYSCF_ALL / PHYSMC_ALL, every paid output with L2. They gave the same BA, and no NEW-corner gain (NEW conduction recall 0.27–0.31).

**PRIMARY C:** PHYSCF_ATS_MARGIN vs E1_STRADDLE, BA-AULC over B8–B60. Development: +0.004 / −0.004.

**Key secondary (the same rule, reported next to the primary):** mean log loss over B8–B60. Development: 0.139 / 0.169 vs 0.233 / 0.227.

**Other secondary:**
- G3 contrasts;
- both recalls, AUC, Brier, q20 BA, short-Keyhole captured/total (pooled and NEW-only);
- NEW-batch conduction recall (the fast-scan corner; development 0.29–0.54 for every arm);
- queries to BA ≥ 0.93 (absolute; confirmed at b and b + 4), with censoring;
- fit failures and fallbacks.

### D. Time structure (job `final-temporal`; bounded, exploratory)

**Endpoint:** early-horizon peak amplitude, 0–0.25 ms after the run's own onset, of KE (log) and of maximum temperature. Predicted at B16 and B40 of the paid MAXIMIN path by three predictors:
- the direct scalar GP (M0Q on the per-run feature);
- curve models fitted on the paid runs' native 5-µs early curves: KRONn, PHASE, PHASE_PCA (RC18 `curve_models`, unchanged);
- the x-independent mean paid curve.

The test run's own curve never enters a prediction.

**Rule:** a curve model beats the scalar GP iff its error ≤ 0.95 × the scalar error AND ≤ 0.95 × the mean-curve error in ≥ 7 of 8 repeats. This is not a full-trajectory result.

## 5. Endpoint rules

- **First qualifying budget:** the first recorded b at the absolute level.
- **Confirmed budget:** at the level at b and at b + 4, spending up to b + 4. The last pair of the horizon is tested.
- **Not reached:** censored at the horizon, with completion rates. No code (44 / 64) is treated as an observed budget, and no saving is computed when an endpoint was not observed.
- Average per-output savings are never multiplied by the number of outputs.
- The joint campaign endpoint requires all 8 outputs at their levels at the same budget.
- Held-out R² is offline; no automatic stopping claim is made.

## 6. Costs

- **Simulation cost:** total revealed queries per trajectory, startup included. One query reveals all outputs and is counted once.
- **Modelling CPU:** recorded per unit, separately.

## 7. Execution and failures

- **Queue:** `src/rc19_runner.ps1`, a single queue with a detached supervisor. Capacity: Opus ≤ 2, Astra's 2 respected, total ≤ 4.
- **Unit protocol:** O_EXCL claims, atomic checkpoints, failures recorded and never retried, no claim after the deadline.
- **Failure handling:** a failed unit is reported and missing from its arm. A primary with missing units is reported as INCOMPLETE, never imputed.

## 8. Disclosures (development results seen before this freeze; ledger RC19-DEV)

- **Regression, R²-AULC B8–B80, mean of 8 outputs:**

  | Arm | R²-AULC |
  |---|---|
  | M0 MAXIMIN | 0.819 |
  | M0Q MAXIMIN | 0.822 |
  | SHQ MAXIMIN | 0.845 |
  | SHQH MAXIMIN | 0.840 |
  | M0Q MOIVR | 0.848 |
  | SHQ MOIVR | 0.861 |
  | M0Q RANDOM | 0.830 |
  | SHQ RANDOM | 0.857 |

- **Region, BA-AULC:** SHQ STRADDLE 0.949, SHQ TRUVAR 0.945, SHQ MAXIMIN 0.918, M0 STRADDLE 0.934, M0 MAXIMIN 0.907.
- **Label, BA-AULC:** E1_STRADDLE 0.944, PHYSCF_ATS 0.944, G3 0.918. All arms have NEW conduction recall ≤ 0.54.
- **Choices informed by these numbers:** the margins, the horizons, the arm list and the decision to drop SHQH / ALL.
- **Levels:** set from the offline full-pool references (development repeats only).
