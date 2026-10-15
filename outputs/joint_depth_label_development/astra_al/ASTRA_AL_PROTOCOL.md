# ASTRA_AL — real-data sequential acquisition with Astra's V2 policy (exploratory DEV)

**Status: REGISTERED BEFORE ANY ASTRA_AL OUTCOME.** This is exploratory development on simulations that were inspected before. It is not confirmation. C4 is not authorized. C3 stays spent, and its failed superiority result does not change. Historical failed screens (Stage M, V2) stay failed.

- **Authorization:** owner execution request of 2026-10-15, Experiment A. It runs Astra's previously unexecuted "bounded future DEV policy draft" (`outputs/astra_balanced_decision_acquisition/OPUS_DECISION_ACQUISITION_REQUEST.md`, §"Bounded future DEV policy draft").
- **Code:**
  - `src/jdl_astra_al.py` (runner and validation);
  - `src/jdl_astra_al_eval.py` (evaluation, frozen with this protocol);
  - Astra's byte-identical modules `balanced_method.py`, `joint_model_v2.py` and `v1_reference.py`, hash-checked against her MANIFEST at every import.
- **Manifest:** `ASTRA_AL_MANIFEST.json`, committed before the first unit. Workers refuse to start if the manifest is not committed or any frozen code hash differs.

## 1. Design

| Item | Frozen choice |
|---|---|
| Population | NEW-136 (all labelled NEW simulations), DEV repeats 3–4, folds 1–5 (10 task folds) |
| Start | The frozen feature-only B16 starts (`stage_a/stage_a_paths_NEW_r3_r4.csv`; sha256 as in the TRAINED_AL manifest). There is no startup extension and no one-class reseeding. Proper-prior one-class fits are allowed (`r3_f4` starts one-class). |
| Budgets | B16 → B24, i.e. eight sequential queries per trajectory |
| Model (all arms) | Astra's `JointModelV2`: the Stage M priors, ρ ∈ {0, 0.5, 1} with prior 1/3 each, and EP with whole-mixture Laplace fallback. Inputs are log-standardized on the fold pool. |
| Decision (all arms) | The finite-batch BA rule A_m ≥ B_m with m = 136. The reference is uniform over the fold pool. The A1 integration level is used: 2^10 → … → 2^16, accepted when the maximum signed-margin change is ≤ 0.015 and the π change is ≤ 0.003. The criterion is unchanged. |
| Arms (selectors) | **ALIGNED_MARGIN**: minimum \|A_m − B_m\|/(A_m + B_m). **V2_VARIANCE**: her integrated probability-variance lookahead. **BA_RISK**: her paired-output expected reduction of the optimized finite-batch BA loss. The arms share the same model, decision and paid outputs. |
| Response availability in the lookaheads | α = (paid responses + 1)/(paid simulations + 2) at each budget. This is a paid-evidence model, never the synthetic 0.75. |
| Seeds | Task seed s = 6000 + 100 r + f. Decisions use 91000 + s + 101 b. Risk uses 20000 + s + 101 b. These are her formulas. |
| B16 | Deterministic and identical for the three arms. It is executed in every unit, and executed fits are reported separately from the 270 logical requests. |

**Observation contract (learner side).**
- The learner sees:
  - the features P, VX, LS radius and ST, with the frozen transform;
  - the pool features, as the unlabelled reference;
  - the revealed canonical label Y and the available A (z = log(A/111)) of paid simulations only.
- The learner never sees:
  - unpaid or test labels, or unpaid or test monitor outputs;
  - short-K membership or q20 membership;
  - global class counts;
  - the inspected VX = 0.85 cutoff.
- A missing response keeps its label and its cost.

## 2. Numerics (registered before execution)

- **BA_RISK ladder:** (QMC bits, GH order) = (8, 9) → (10, 17) → (12, 33).
  - Accept a level when all four hold: max(order difference, 2 SE) ≤ 0.002; low-ESS outcome mass ≤ 0.002; current-risk tower discrepancy ≤ 0.002; normalization error ≤ 1e-8.
  - Ties within the error go to the smallest pool index.
  - **No precision extension** is registered. An unresolved ranking at (12, 33) is a NUMERICAL_STOP.
  - The m-parameterized copy of her `_candidate_table` equals hers bitwise at m = 96. This is a validation check.
- **V2_VARIANCE:** her GH ladder and acceptance, unchanged.
- **Numerical stops:** a decision or selector NUMERICAL_STOP ends the trajectory. Its data are preserved. No criterion is relaxed, and there is no fallback to another selector.
- **Caps (her draft):** 270 top-level requests and 900 component solves including fallback.
  - The solve cap is enforced before every fit: recorded solves plus 6 per active unit must be ≤ 900. Otherwise the fit is refused and the trajectory ends with CAP_STOP (preserved).
  - Component solves, fallbacks, score evaluations, ladder levels, near ties, timings and stops are recorded per step.
- **Validation:** `ASTRA_AL_VALIDATION.json` must PASS before the freeze. It covers:
  - her independent reference checks, read only;
  - frozen-source identity;
  - the m-identities and the parity with her m = 96/136 code;
  - bitwise equality of the risk table;
  - outcome normalization at m = 136;
  - the risk selector and the A1 decision at m = 136;
  - the joint-covariance identity;
  - invariance of the first selections (margin, variance) and of the risk scores when every hidden label and depth is corrupted;
  - CAP_STOP before a refused fit;
  - ten task folds on the frozen paths.

## 3. Endpoints (prospective)

- **Primary contrasts:**
  - P1 = BA_RISK − ALIGNED_MARGIN;
  - P2 = BA_RISK − V2_VARIANCE.
  - Both use the pooled-per-repeat finite-batch BA-AULC over B16–B24 (trapezoid / 8), averaged over repeats 3–4. Per-repeat values are always reported.
- **Secondary:**
  - S1 = V2_VARIANCE − ALIGNED_MARGIN;
  - the 0.5-cutoff BA of the mixture probability on the same posterior;
  - AUC-AULC;
  - checkpoints at B16, B20 and B24;
  - terminal (B24) BA, both class recalls, q20 (unchanged incumbent definition), short-K recall, and the AUC, Brier score and log loss of the mixture probability;
  - per-simulation decisions;
  - how often the finite-batch decision differs from the 0.5 cutoff.
- **Short-K guardrail (evaluation only, never a selector input):** at B24, short-K detections are summed over both repeats (20 events). A contrast whose arm misses more than 2 events beyond its comparator fails the guardrail.
- **Practical adoption rule (fixed before the run, as her draft requires; not borrowed from the synthetic study):** "practically better" requires all of the following. A BA gain that fails only the guardrail is a **trade-off**. Anything else is **no practical difference established**.
  1. The mean BA-AULC contrast is ≥ 0.02.
  2. Its 95% bootstrap interval excludes 0.
  3. Both repeats have the same sign.
  4. The guardrail holds.
- **Incomplete trajectories:**
  - A readout at budget b exists for a repeat only if all five trajectories of that arm reached b with a numerically accepted test decision. Otherwise it is UNAVAILABLE.
  - An AULC needs every budget.
  - There is no carry-forward and no surviving-subset estimate.
  - Units still running are reported as running, never as results.
- **Uncertainty:**
  - The Stage M class-stratified simulation-cluster bootstrap (2000 draws, seed 20261013) is used, with identical multiplicities across arms, budgets and repeats.
  - It is conditional on the realized trajectories and fits, two repeats, and previously inspected simulations.
  - With ten short-K simulations per repeat, intervals will be broad. No adoption decision is made from a favourable point estimate.
- **No savings endpoint** is registered (her draft). Different paths or a higher AULC do not measure saved simulations.

## 4. Compute plan and capacity

- The coordinated pool runner `src/jdl_pool_runner.ps1` allocates the combined four-thread limit (Astra's work included) from `pool/POOL_PLAN.json`.
  - One BLAS thread per worker.
  - Units are claimed with O_EXCL locks in `_cache/astra_al/locks/<arm>/`.
  - There is a per-budget atomic checkpoint (temp file + `os.replace`), and resume is deterministic.
  - Each worker exits after one unit (`--max-units 1`), so capacity is re-allocated at every unit boundary.
- **Cheap arms** (ALIGNED_MARGIN, V2_VARIANCE) run first, with up to 2 workers. The validation measured about 13 s and 27 s for one step.
- **BA_RISK:**
  - The predeclared first unit `NEW__r3_f1__BA_RISK` runs alone until its first acquisition step (B16 → B17) is recorded. Its measured per-step time is written to the pool log with a projected completion time.
  - After that, BA_RISK receives up to 2 concurrent workers while any other registered study has claimable units, and up to 3 otherwise. The lookahead never starves the other registered comparisons.
- Unfinished units are reported as unfinished. Interim reports carry the unit counts.

## 5. Interpretation limits

- This is a DEV comparison of three selectors under one model and decision. It is not a demonstration of saved simulations, not a confirmation, and not evidence about other populations.
- A decision-rule gain is not new discriminatory information.
- If BA_RISK mainly buys specificity by rejecting transient positives (a short-K loss), the loss target is insufficient for the scientific goal (her discriminating interpretation).
- Because the simulations and their labels were inspected before, every number here is development evidence.
