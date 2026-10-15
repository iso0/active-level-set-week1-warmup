# CORNER_LOCAL (Experiment C1) — local discrimination inside a learned scan-speed region

**Status: REGISTERED BEFORE ANY CORNER_LOCAL OUTCOME.** This is exploratory development on simulations that were inspected before. It is mechanism candidate 1 of at most 2 under the owner execution request of 2026-10-15. It is not confirmation. C4 is not authorized, C3 stays spent, and the failed Stage M and V2 screens stay failed.

- **Code:** `src/jdl_corner_local.py` (runner, validation) and `src/jdl_corner_local_eval.py` (evaluation, frozen with this protocol).
- **Manifest:** `CORNER_LOCAL_MANIFEST.json`. It is committed before the first unit, and workers refuse to start without it or after any frozen code changes.

## 1. Mechanism, benefit, failure, control

| | |
|---|---|
| **Observation** | On NEW, every model so far classifies everything outside the fast-scan corner correctly, except one early-ended run without A. Inside the corner (23 runs: 11 no-Keyhole, 12 Keyhole, 10 of them short-K) every model and rule has BA 0.45–0.60 (CLAIMS_MATRIX L1–L2). |
| **Mechanism (hypothesis)** | A stationary GP fitted by ML-II on all paid runs takes its length scales from the large, smooth all-Keyhole region. Inside the corner it then averages intermixed labels. If the corner labels carry structure at a shorter scale, a model can resolve it by doing two things: (i) learn the region from paid labels only, and (ii) fit a separate GP classifier, with its own ML-II hyperparameters, to the paid runs inside the region. |
| **Expected benefit** | Corner ranking above chance, so that short-K positives are detected while corner negatives are rejected. This targets short-K retention, which every BA gain so far has given up (Figure 2). |
| **Plausible failure** | There is no learnable structure at the available density (about 10–15 paid runs in the region). The local ML-II then picks long length scales and the model reproduces the stump leaf, which is an all-negative or all-positive corner. |
| **Decisive control** | **TREED_PERM**: the same model with the paid labels inside the region permuted. Class counts are kept, the seed is 7000 + 100 r + f + 101 b, and the paid sets are the same. Local discrimination exists only if TREED ranks the held-out corner runs better than TREED_PERM. |
| **Secondary controls** | **TREED_CONST**: the constant stump-leaf score inside the region, i.e. the split alone. **JT**: the global J_trained component alone. Both use the same paid sets. |
| **Prior tests (checked)** | Tested before: global GPs only (J, J_trained, V1/V2, ACTIVE E1, G3), the learned one-cut VX stump (V2 comparison: BA 0.851, short-K 0.10), and rule changes on unchanged posteriors (π̂, finite-batch). None fitted a separate model inside a learned region. The inspected Week 19 cut is a reference point, not a learner. Corner discrimination is listed as untested (U4). |

## 2. Predictor and arms

- **Global component:** J_trained, identical to TRAINED_AL (`jdl_ex2.trained_config` ML-II on the paid responses, plus `JointDepthLabelGP`). The validation checks it bitwise against the frozen TRAINED_AL B16 prediction.
- **Region:** `vx-stump-1.0` on standardized log VX of the paid runs. The region is the leaf whose class-weighted score is < 0.5, i.e. the learned no-Keyhole leaf. There is no region if the stump is constant or no leaf is below 0.5. The inspected 0.85 m/s cut is never read by the learner (validation: changing it changes nothing).
- **Local model inside the region:** sklearn `GaussianProcessClassifier`.
  - Kernel C · RBF with ARD over the 4 standardized log features. C ∈ [0.05, 20] (init 1), length scales ∈ [0.05, 20] (init 1).
  - L-BFGS-B without restarts, so it is deterministic.
  - It is fitted only if the paid runs inside the region contain both classes; otherwise the stump-leaf score is used.
  - **These bounds and inits are fixed here and never tuned.**
- **Decision:** cutoff 0.5.
- **TREED_MARGIN (adaptive):**
  - NEW DEV repeats 3–4, folds 1–5, starting from the frozen feature-only B16 starts (the TRAINED_AL paths), B16–B40.
  - Selection is argmin |p_TREED − 0.5| over the unpaid pool, ties by simulation ID (as `SA.select_margin`).
  - TREED_PERM, TREED_CONST and JT are computed at every budget on TREED_MARGIN's own paid sets. Their cost and their paths are identical.
- **FIXED:** TREED, TREED_PERM, TREED_CONST and JT on the fixed Week 19 feature-only paths (DEV repeats 1–2, B16 and B40). These are the paths of the V2 comparison and Figure 2.
- **Observation contract:** unchanged from TRAINED_AL — paid features, labels and A only.
  - The learner never sees unpaid or test outcomes, short-K or q20 membership, global class counts, or a fixed VX cut.
  - The evaluator-only corner (VX > 0.85 m/s) is used only to describe results.

## 3. Endpoints (prospective; `src/jdl_corner_local_eval.py`)

- **L1 (primary, local discrimination):**
  - Measure: the pooled corner AUC at B40 on TREED_MARGIN's paid sets, TREED − TREED_PERM, mean of repeats 3–4.
  - **SUPPORTED** iff the 95% interval is above 0; otherwise **NOT SUPPORTED**.
  - Reported beside it: per repeat; B24 and B32; the same on the fixed paths; TREED − TREED_CONST; TREED − JT.
- **L2 (system):**
  - Measure: TREED_MARGIN − JT_MARGIN (TRAINED_AL, same frozen starts), BA-AULC over B16–B40.
  - **Practically better** iff all of the following hold: the difference is ≥ +0.04 (TRAINED_AL's threshold); the interval is above 0; both repeats are positive; short-K at B40 is at most 2 missed events (of 20) worse than JT_MARGIN.
  - A BA gain that fails only the short-K condition is a **trade-off**. Anything else is **no practical difference established**.
  - Against G3 and ACTIVE E1, only repeat 4 exists, so that comparison is descriptive. The repeat-3 controls are unavailable by the TRAINED_AL protocol.
- **L3 (path held fixed):** TREED − JT on the same paid sets, i.e. the predictor effect without a path difference.
- **Query efficiency:**
  - The TRAINED_AL target: BA ≥ 0.75, short-K ≥ 0.70 and q20 ≥ 0.70, sustained over two consecutive grid points of 16..40 (step 4).
  - It is right-censored at B40. All queries are counted, including the start.
  - A saving is reported only if TREED_MARGIN attains the target in both repeats, and then as a lower bound against censored comparators.
- **Always reported:** BA, both class recalls, q20, short-K recall, AUC, Brier, log loss, corner confusion counts, the region diagnostics (cut, leaf, paid runs in the region, local kernel), and where the queries went (evaluator-only).
- **Incomplete units** are UNAVAILABLE, never a surviving subset.
- **Uncertainty:** the Stage M class-stratified simulation-cluster bootstrap (2000 draws, seed 20261013), conditional on paths and fits. There are 23 corner runs per repeat, so corner intervals will be wide.

## 4. Compute

There are 11 units: 10 adaptive trajectories and 1 fixed-path unit. The cost is about 270 J_trained fits plus 3 small local classifiers per fit, roughly minutes on one thread. The coordinated pool runner (`pool/POOL_PLAN.json`) runs one worker, inside the shared four-thread limit. Each budget is checkpointed atomically, and resume is bitwise identical (validated).

## 5. What a result can and cannot mean

- **L1 SUPPORTED** would show that held-out corner labels are partly predictable from the four inputs, which is local discrimination. That would be DEV evidence on inspected runs. It is not a confirmation, and not a statement about the labels' physical meaning.
- **L1 NOT SUPPORTED** would mean this local model at this density finds nothing beyond chance. It would **not** show that no model can distinguish the recorded labels. Similar depth trajectories are not such proof either.
- Because the corner, its size and the failure of global models were all found by inspecting these simulations, any favourable number is optimistic and needs data that has not been inspected.
