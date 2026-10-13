# Stage A — acquisition value with the model held fixed: PROTOCOL DRAFT (prepared and validated, NOT executed)

## Status and gate
- **Stage M screen:** the frozen screen **failed** (`stage_m/STAGE_M_DECISION.json`). NEW B40 J − Binary_matched BA was +0.006, below the required +0.01.
- **Consequence:** under the rule written before Stage M, Stage A is **not recommended**, and this draft does not start it.
- **Runner:** `src/jdl_stage_a.py` is working and validated (`stage_a/stage_a_runner_validation.json`). Its `run` step refuses to execute without an owner decision and a committed `stage_a/STAGE_A_MANIFEST.json`.
- **What would justify Stage A:** for example, a revised model or decision rule that passes its own pre-registered screen (see `exploratory/EX1`). The draft below would then become the manifest after updating the candidate definition.

## Design (as prepared)

**Data and startup**
- **Data:** NEW, DEV repeats 3–4, five folds. These repeats were not used in Stage M (1–2) or EX1 (5–8).
  - Their feature-only maximin paths are already built and hashed (`stage_a/stage_a_paths_NEW_r3_r4.csv`); no label was revealed.
- **Startup:** the identical feature-only B16 prefix (maximin, task seed + [2]) for every arm, never extended.
  - A one-class prefix is valid for J. For the controls it means "fit contract not satisfied" (recorded, not repaired).

**Arms**

| Arm | Model | Query rule | Information received |
|---|---|---|---|
| **J_PV** | J, frozen Stage M priors, refit from the prior with every paid factor at every budget | expected reduction of the integrated posterior variance of Φ(h/τ), integrating the paired future (Z, Y) | paid Y and available A |
| **J_MARGIN** | the same J | argmin \|p − 0.5\| | paid Y and available A |
| G3_MARGIN (control) | frozen G3, paid-only ML-II | margin | paid Y |
| ACTIVE_E1_STRADDLE (control) | frozen E1, paid-only ML-II | straddle | paid Y and A |

- **Primary comparison:** J_PV vs J_MARGIN. The two arms share the model and the information, so their difference isolates query choice.

**Acquisition (J_PV)**
- Candidates: all unpaid training-pool simulations. Integration points: the fixed fold pool with uniform weights.
- Score: the response term plus the label term conditional on the response (Astra's closed form). The bivariate probit uses Genz BVNU.
- **Numerical ranking rule.**
  1. Score with 15 and 31 Gauss–Hermite nodes and set e = max |s31 − s15|. Accept the top candidate (by s31) if its gap exceeds 2e plus the omitted-tail bound.
  2. Otherwise compare 31 vs 63 nodes, rank by 63 and apply the same test.
  3. If still unresolved: if every relevant difference and gap is ≤ 1e-8, treat it as a numerical tie and break it by fixed simulation-ID order. Otherwise record a **numerical STOP** for that trajectory.
  - There is no fallback to margin, no reseeding and no lower-fidelity score.
  - Quadrature agreement does not validate the Laplace approximation (see `MECHANISM_REPORT.md` §7).

**Budget and endpoints**
- **Budget:** B16 → B40, one refit and one query per step.
- **Fit requests:** at most 10 task-folds × 2 J arms × 25 budgets = 500, plus up to 500 for the controls.
- **Primary endpoint:** the paired J_PV − J_MARGIN difference in BA-AULC over B16–B40 (trapezoid normalised by width, the Week 18 convention).
- **Reported alongside:** unchanged q20 accuracy AULC; B40 BA, log loss, Brier and specificity; unique-simulation short-K sensitivity; per-repeat values; and a simulation-cluster bootstrap conditional on the stored fits.
- **Logs:**
  - every candidate's score at every order, with the response and label components, the omitted-tail bound and the quadrature comparisons;
  - the gap and the tie or STOP decision;
  - the model state before each outcome is revealed (θ mean and SD, integrated variance, counts);
  - the first divergent query between J_PV and J_MARGIN, and the paid-set overlap at B40.
- **Claims allowed:** identical paths cannot show better query selection. No sample-saving claim follows from AULC alone; a separate pre-specified target and hitting-time design would be needed for that.

## Validation already run (synthetic task plus plumbing; `stage_a/stage_a_runner_validation.json`)
- **Runs:** both J arms run 5 steps; the control loops run from the same startup.
- **Information:** paired information is passed, and a missing response keeps its label and cost.
- **Leakage:** corrupting every unpaid and test outcome leaves the first selection and all scores identical.
- **Ties and logs:** the duplicate-candidate tie follows the fixed-ID rule, never margin. Score logs are complete.
- **Plumbing:** the NEW repeat 3–4 tasks and paths are built, with no label revealed.
