# TRAINED_AL protocol: a real-data DEV active-learning comparison with the trained joint model

**Status.** Frozen before any TRAINED_AL outcome; the manifest and source hashes are committed before the first trajectory.
- **Authorization:** the owner's execution request of 2026-10-15.
- **Nature:** EXPLORATORY development on previously inspected simulations, not confirmation.
- **Unchanged:** the Stage M and V2 screens stay failed, C3 stays spent and failed, and C4 is not run.
- **Code:** `src/jdl_trained_al.py` (trajectories) and `src/jdl_trained_al_eval.py` (endpoints, frozen with this file).

## 1. Design
- **Data:** NEW-136 (124 Keyhole / 12 no Keyhole; canonical labels unchanged), DEV repeats 3–4, folds 1–5.
- **Start:** the frozen feature-only B16 starts, `stage_a/stage_a_paths_NEW_r3_r4.csv` (maximin with task seed + [2]; hashes in the manifest), the same for every arm. Sequential queries run B17–B40.
- **Costs:** every arm pays for its 16 startup simulations and for every query. Paths diverge after the start.
- **Arms:**

  | Arm | Model and decision | Selector |
  |---|---|---|
  | G3_MARGIN (incumbent) | frozen Week 18 G3 GPC, per-step ML-II; p ≥ 0.5 | argmin \|p − 0.5\| |
  | ACTIVE_E1_STRADDLE | frozen Week 18 GPR on log A, per-step ML-II; its threshold rule | straddle |
  | JT_MARGIN | J_trained, p ≥ 0.5 | argmin \|p − 0.5\| (ties by simulation ID) |
  | JT_PV | the same J_trained and p ≥ 0.5 | paired probability-variance acquisition (see below) |

- **J_trained** is the joint depth–label GP of `src/jdl_model.py`.
  - Its response-prior amplitude and four ARD lengthscales are re-estimated by ML-II on the **currently paid** responses at every budget (`src/jdl_ex2.trained_config`, unchanged; noise 0.03).
  - The θ, δ and probit priors are those of Stage M.
  - The two J_trained arms share model and rule, so their contrast isolates query selection.
- **JT_PV selector:** the expected reduction of the integrated label-probability variance over the fold reference pool from observing the candidate's label and response (`JointDepthLabelGP.acquisition`).
  - Numerics follow Stage A's acceptance rule: Gauss–Hermite nodes 15/31/63, a gap > 2e + tail bound, and a fixed-ID tie rule.
  - An unresolved ranking is a recorded NUMERICAL STOP, never a margin fallback.
  - **Why this selector:** the corner errors persist because margin selection exploits the majority decision boundary. Variance reduction instead spends queries where the paired outputs most reduce label uncertainty over the reference pool.
- **Observation contract:**
  - The learner sees the four physical inputs of every candidate.
  - For paid simulations only, it also sees the canonical label and the available ACTIVE A. A missing A keeps its label and its cost.
  - Short-K membership, q20 membership, test outcomes, global counts and the VX = 0.85 cut never reach any learner or selector.

## 2. Endpoints

**Readouts and AULC.**
- Readouts are pooled per repeat and averaged over repeats 3–4; the decision is p ≥ 0.5 for every arm.
- **BA-AULC:** a trapezoid over every integer budget 16–40, divided by 24. Short-K-recall AULC and q20 AULC are defined the same way.
- **Checkpoints** (B16, B24, B32, B40): BA, sensitivity, specificity, unchanged q20, short-K recall (the existing 10 NEW short-K simulations, one event each per repeat), AUC, Brier, log loss, and TP/FN/TN/FP counts.

**Contrasts.**

| Name | Contrast | Role |
|---|---|---|
| C1 (primary) | JT_PV − G3_MARGIN, BA-AULC | candidate system vs incumbent |
| C2 | JT_PV − JT_MARGIN | query selection only |
| C3 | JT_MARGIN − G3_MARGIN | model, at the same selector type |
| S1–S3 | ACTIVE_E1 − G3; JT_PV − ACTIVE_E1; JT_MARGIN − ACTIVE_E1 | ACTIVE E1 reported alongside |

**Thresholds (stated before the run).**
- **Practical improvement:** a BA-AULC difference ≥ +0.04, which is about one more of the 12 negatives correctly rejected in every repeat across the curve.
- **Short-K retention guardrail (evaluation only, never a selector input):**
  - At B40, the arm's short-K detections summed over both repeats (20 events) must be at least G3's minus 2. That is at most two more missed short-K events than G3, i.e. 0.10 recall. The same count is reported at B24 and B32.
  - The short-K-recall AULC must be at least G3's minus 0.10.
- **Reading the result:**
  - A candidate "improves on G3 + margin" (a development signal) only if C1 ≥ +0.04 **and** retention is met.
  - A favourable point estimate whose bootstrap interval includes 0 is a development signal, not superiority. No non-inferiority claim is made.
  - A BA gain that comes with a short-K loss beyond the tolerance is a decision trade-off, not a solution.

## 3. Query efficiency (development criterion)

- **Target T, per repeat:** pooled BA ≥ 0.75, short-K recall ≥ 0.70 and q20 ≥ 0.70, sustained at two consecutive grid budgets of {16, 20, 24, 28, 32, 36, 40}.
- **Counting:** queries to attainment = that budget, startup included.
- **Censoring:** a run that never attains T is right-censored at its last available budget. This includes stopped trajectories and runs that meet T only at B40, which cannot be sustained.
- **Reporting:** attainment counts per arm (of 2 repeats), the budgets and the censored outcomes. Successful runs are never compared on their own.
- **Why this target:** on DEV 1–2 at fixed paths, no B40 method met all three conditions jointly (ACTIVE E1 0.730 / 0.60 / 0.75; J_trained at 0.5 0.707 / 0.60 / 0.717). The best DEV 5–8 fixed-path result is J_trained at 0.5, with 0.752 / 0.675 / 0.783. T sits just above the best joint fixed-path performance, so it is "useful" by the existing evidence. It was chosen before any new curve existed.
- **What it can and cannot show:** an AULC difference alone is not a query saving. If no arm attains T, that is the result.

## 4. Unavailable data, uncertainty, compute

**Unavailable readouts.**
- A fit failure or numerical stop ends the trajectory and is recorded.
- Readouts beyond the stop are UNAVAILABLE for that repeat and arm, so its AULC and any contrast using it are unavailable; for attainment it is censored.
- No surviving-subset value is reported, and no trajectory is extended, reseeded or replaced.

**Uncertainty.**
- Class-stratified simulation-cluster bootstrap (2000 draws, seed 20261013), with multiplicities shared by every arm, repeat and budget, for the AULC contrasts.
- It is conditional on the realised trajectories (acquisition randomness is not resampled), on two repeats only, and on previously inspected simulations. Intervals will be broad.

**Compute.**
- 40 trajectories, each with at most 25 fits.
- Workers: at most 3 of the 4 threads, allocated by the single coordinator `src/jdl_pool_runner.ps1` together with the Astra acquisition study. One BLAS thread per worker.
- Workers claim units by O_EXCL locks. J_trained trajectories write atomic per-budget state and resume bitwise identically; control trajectories are recomputed from B16 if interrupted.

**Reuse.** None. The Week 20 Track 1 G3 and E1 trajectories began from 8 maximin points plus queries, not from this B16 start, so they are not reused.

**Mechanism readouts (description).**
- AUC and Brier separate a gain in discrimination from a pure decision trade-off.
- The query composition (queried negatives; queries in the VX > 0.85 corner, evaluator-only) separates a change in query path from a change in the model.
