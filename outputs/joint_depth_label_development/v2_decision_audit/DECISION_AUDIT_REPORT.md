# Cached-posterior decision audit (decision-audit-1.1.1): report

**Status.** A decision-only audit of the frozen V2 comparison. Data: NEW-136, DEV repeats 1–2, folds 1–5, B16/B40.
- **Zero fits.** No thesis model was refitted; the audit reads the exported posteriors of the stored V2 fits (V2_EP_mixture, its ρ = 1 EP component as rho1_EP, Binary_V2_EP).
- **Provenance:** an owner-authorized logged technical recovery of the failed queue task T05. Its sequence R04–R08 is in `../recovery/decision_audit_T05_T08/`.

| Step | What happened | Commit |
|---|---|---|
| Queue T05 (original attempt) | 1.1 wrote a PASS validation, then exited with code 1 in its console echo; T06–T08 blocked. The runner's records are unchanged; the 1.1 file is preserved | `034eae6b` |
| R05 | Validation retry with 1.1.1: exit 0, PASS, 45/45 hard checks, 9.9 s; validation SHA-256 `9505282d…`, module `e5e61a25…` | `97f1fde2` |
| R06 | Manifest frozen before any audit decision | `4107fa31` |
| R07 | 60 decision records in 325 s on one thread | — |
| R08 | Evaluation, exit 3 | `3e990a8d` |

**Not Astra's study.** This audit is not Astra's controlled acquisition study.
- Hers runs in her own pipeline on synthetic worlds and selects points sequentially.
- At 23:05 UTC it was in `CONTROLLED_RUN` with 109 of 420 planned fit requests done and no `CONTROLLED_RESULTS.json`. It is neither used nor duplicated here.

## 1. Outcome: **PRIMARY_UNAVAILABLE** (`DECISION_AUDIT_UNAVAILABLE.json`, exit code 3)

- **The frozen primary** is the finite-batch rule (A_m ≥ B_m, m = 136) on all 20 V2_EP_mixture checkpoints. It needs every checkpoint to pass Astra's frozen numerical acceptance:
  - Ladder 2^10 → 2^12 → 2^14 scrambled Sobol points.
  - Accept when the maximum signed-margin change is ≤ 0.015 and the π change is ≤ 0.003.
- **Only 11 of the 20 primary checkpoints were accepted.**
  - Primary stops (9): `NEW__r1_f1__B16__V2_EP_mixture`, `NEW__r1_f1__B40__V2_EP_mixture`, `NEW__r1_f2__B16__V2_EP_mixture`, `NEW__r1_f2__B40__V2_EP_mixture`, `NEW__r2_f1__B40__V2_EP_mixture`, `NEW__r2_f2__B40__V2_EP_mixture`, `NEW__r2_f3__B40__V2_EP_mixture`, `NEW__r2_f5__B16__V2_EP_mixture`, `NEW__r2_f5__B40__V2_EP_mixture`.
  - All 60 checkpoints: 39 `ok`, 21 `DECISION_NUMERICAL_STOP` (V2_EP_mixture 9, rho1_EP 11, Binary_V2_EP 1).
- **Why they stopped.**
  - Every stop failed the margin criterion at 2^14: maximum change 0.0151–0.0331. Their π changes were at most 6.6e-5.
  - The criterion takes the maximum over the reference pool and the test inputs. This matches Astra's frozen `balanced_method.decisions`.
  - **HYP:** posterior prevalences are high (E[π | D] 0.77–0.94). There the class-reversed coefficient (1 − η)/(1 − π) is heavy-tailed across posterior draws, and its QMC estimate did not settle to 0.015 within the ladder.
- **What did not fail.**
  - Probability parity held at every checkpoint: maximum |p_export − p_stored| = 2.2e-16 against a tolerance of 1e-10.
  - The three cutoff decisions recompute exactly from the single stored probability.
  - The test sets partition the cohort.
  - No checkpoint was dropped, no criterion was relaxed, and nothing was retried.
- **What 1.0 would have done.** These 21 unconverged finite-batch and posterior-mean-π decisions would have entered the metrics. Under 1.1.1 they are kept in `decisions_all.csv.gz` as failed output and scored nowhere.

## 2. Readouts (PRED; pooled per repeat, mean of repeats 1–2; UNAVAILABLE = some fold of some repeat not valid for that rule)

Sensitivity is the Keyhole recall and specificity the no-Keyhole recall. Each cell gives BA / q20 / sensitivity / specificity / short-K sensitivity.

| Arm, budget | finite_batch | posterior_mean_pi | paid_fraction (π̂) | cutoff_0.5 |
|---|---|---|---|---|
| V2_EP_mixture B40 | UNAVAILABLE (valid folds 3/5, 1/5) | UNAVAILABLE | 0.878 / 0.600 / 0.839 / 0.917 / 0.00 | 0.554 / 0.667 / 0.984 / 0.125 / 0.80 |
| V2_EP_mixture B16 | UNAVAILABLE (3/5, 4/5) | UNAVAILABLE | 0.792 / 0.567 / 0.710 / 0.875 / 0.15 | 0.600 / 0.717 / 0.992 / 0.208 / 1.00 |
| rho1_EP B40 | UNAVAILABLE (2/5, 2/5) | UNAVAILABLE | 0.880 / 0.600 / 0.843 / 0.917 / 0.00 | 0.554 / 0.667 / 0.984 / 0.125 / 0.80 |
| rho1_EP B16 | UNAVAILABLE (2/5, 3/5) | UNAVAILABLE | 0.806 / 0.567 / 0.738 / 0.875 / 0.15 | 0.579 / 0.700 / 0.992 / 0.167 / 1.00 |
| Binary_V2_EP B40 | UNAVAILABLE (5/5, 4/5) | UNAVAILABLE | 0.785 / 0.550 / 0.778 / 0.792 / 0.10 | 0.556 / 0.683 / 0.988 / 0.125 / 0.85 |
| Binary_V2_EP B16 | 0.630 / 0.533 / 0.677 / 0.583 / 0.45 | 0.587 / 0.517 / 0.673 / 0.500 / 0.40 | 0.634 / 0.533 / 0.560 / 0.708 / 0.45 | 0.594 / 0.683 / 0.980 / 0.208 / 1.00 |

- **Consistency check (OBS).** The cutoff_0.5 and paid_fraction readouts reproduce the V2 comparison's 0.5 and π̂ metrics exactly (for example V2 B40: 0.554 and 0.878). This confirms the export and parity path end to end.
- **Single-repeat values** of available checkpoints are in `metrics_per_repeat.csv`. They are not summaries of the experiment. For example, Binary_V2_EP B40 finite_batch is 0.754 in repeat 1, while repeat 2 is unavailable.
- **Available rule contrasts** (`rule_contrasts.csv`, cluster bootstrap):
  - V2 B40, paid_fraction − cutoff_0.5: BA +0.323 [0.230, 0.412]; sensitivity −0.145; specificity +0.792; short-K −0.80; q20 −0.067.
  - Binary V2 B16, finite_batch − cutoff_0.5: BA +0.036 [−0.069, +0.144]; sensitivity −0.302; specificity +0.375; short-K −0.55; q20 −0.150.

## 3. Interpretation (HYP)

1. **The audit's question stays open under the frozen numerics.** Whether Astra's finite-batch rule improves V2's BA on NEW cannot be answered: its QMC estimate did not meet the frozen acceptance at 9 of 20 primary checkpoints. That is the reported result, not a failure to be worked around.
2. **A decision-rule gain is not new discriminatory information.** Every readout uses the same posterior scores, so moving the threshold moves along one ROC curve.
   - The large π̂ − 0.5 gain (+0.32 BA) is again a corner-specificity trade: specificity +0.79 against short-K sensitivity −0.80.
   - None of this shows simulation savings. No acquisition was run.
3. **Where finite_batch is available** (Binary V2, B16), it sits between 0.5 and π̂: specificity up, sensitivity and short-K down, BA +0.036 with an interval including 0.

## 4. Not done (proposal only; owner decision)

- **What would make finite_batch available:** a prospectively registered numerical amendment, declared before any re-run, such as one more ladder level (2^16) or a margin criterion over the decision inputs only. It would be a new attempt with its own manifest and ledger row.
- **What stays unchanged:**
  - V2 screen: not passed.
  - C3: not confirmed.
- **Still not authorized:** C4 and real-data Stage A.

## Files
- `DECISION_AUDIT_MANIFEST.json`, `DECISION_AUDIT_VALIDATION.json` (R05), `DECISION_AUDIT_UNAVAILABLE.json`
- `metrics_per_repeat.csv`, `rule_contrasts.csv`
- `decision_changes_by_simulation.csv` (available contrasts only), `class_fractions_and_numerics.csv` (per-checkpoint status, ladder history, π, paid fraction, evaluator-only true fractions)
- `decisions_all.csv.gz` (every attempted decision, with validity)
- `SAFEGUARD_CORRECTION.md`
