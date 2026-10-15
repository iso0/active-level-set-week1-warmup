# STOP_RULE (Experiment C2) — a learner-side stopping rule for the J-family adaptive arms

**Status: REGISTERED BEFORE ANY STOP_RULE COMPUTATION.** This is exploratory development on simulations that were inspected before. It is mechanism candidate 2 of 2 under the owner execution request of 2026-10-15. It is not confirmation.

**This is a separate question.** It does not alter TRAINED_AL's query-efficiency endpoint. No arm attained that target (BA ≥ 0.75, short-K ≥ 0.70, q20 ≥ 0.70, sustained). That result stands, and it is not re-analysed here.

- **Code:** `src/jdl_stop_rule.py` (validation, run, frozen evaluation).
- **Manifest:** `STOP_RULE_MANIFEST.json`, committed before the run.

## 1. Mechanism, benefit, failure, control

| | |
|---|---|
| **Mechanism (hypothesis)** | Once the smooth region is resolved, margin-type acquisition spends most later queries inside the fast-scan corner. By B40, nearly every corner run of each training pool is paid: 139 of 240 post-start queries in each J-family arm, a median of 17 paid corner runs. Yet those labels did not transfer to held-out corner runs (CORNER_LOCAL L1 not supported). If so, the fold-pool predictions stop changing, and later queries buy no held-out performance. |
| **Expected benefit** | Fewer paid simulations per trajectory, with no material loss relative to continuing to B40. |
| **Plausible failure** | Corner predictions keep flipping as each new corner label arrives, so the rule never stops (censored at 40). Or the rule stops before the smooth region is resolved, causing a loss. |
| **Decisive control** | **FIXED_STOP**: every trajectory of the arm is stopped at one common budget, the rounded mean adaptive stop. The average cost is the same, with no adaptivity. If the adaptive rule is no better than FIXED_STOP, its value is only "fewer queries were enough", not the rule. |
| **Prior tests (checked)** | No stopping rule has been registered or run in this project. Week 19 and 20 "queries to target" used fixed grids. |

## 2. Rule (standard parameters, not tuned)

The rule is "stabilizing predictions" (Bloodgood & Vijay-Shanker, 2009).
- **Stop set:** the fold pool, features only, fixed across budgets.
- **Decisions:** at cutoff 0.5, from the arm's own predictor refitted on the stored paid prefix. The refits must reproduce the stored test predictions bitwise.
- **Agreement:** Cohen's κ between consecutive budgets, with κ = 1 for identical decision vectors.
- **Stop:** at the first b ∈ [20, 40] whose last three transitions have mean κ ≥ 0.99. Otherwise there is no stop: the cost is 40 and the trajectory is censored.
- **Arms:** the stored, completed paths; nothing is re-acquired.
  - JT_MARGIN (TRAINED_AL)
  - TREED_MARGIN (CORNER_LOCAL)
  - NEW DEV repeats 3–4, folds 1–5.
- **Observation contract:** unchanged — paid features, labels and A, plus pool features. The rule never reads a test or unpaid outcome; validation corrupts them and the rule's decisions stay identical.

## 3. Endpoints (prospective)

- **Per trajectory:** the stop budget; cost = stop budget, or 40 if censored. All queries are counted, the 16 start runs included.
- **Stopped system:** for each repeat, the pooled test predictions, with each fold at its own stop budget.
- **Non-inferiority against B40 (same arm, point estimates):** all three must hold. Paired bootstrap intervals are reported.
  - BA (mean over repeats) ≥ B40 − 0.02;
  - q20 ≥ B40 − 0.05;
  - short-K detections, summed over the two repeats (20 events), ≥ B40 − 2.
- **Verdict per arm:**
  - **"SAVING WITHOUT MATERIAL LOSS (DEV, relative to continuing to B40)"** iff the mean saving is ≥ 4 queries per trajectory and non-inferiority holds;
  - otherwise **"NO SAVING ESTABLISHED"**.
- **Always reported:**
  - the comparison with FIXED_STOP;
  - censored trajectories;
  - per-trajectory κ and the number of decision changes per budget.
- **What it does not show:** that the stopped system reaches a useful absolute performance level. The registered target was not reached by any arm. A saving relative to B40 is a statement about the acquisition schedule, not about usefulness.

## 4. Compute and limits

- **Compute:** 20 units, each about 25 refits of J_trained (TREED adds 3 small classifiers per refit). This is minutes on one thread, run through the pool runner.
- **Uncertainty:** the Stage M class-stratified simulation-cluster bootstrap, conditional on the stored paths and fits.
- **Inspection bias:** the flat late learning curves and the corner exhaustion were seen before this registration. The rule and its parameters are the standard published ones and are not tuned, but any favourable result is optimistic and needs data that has not been inspected.
