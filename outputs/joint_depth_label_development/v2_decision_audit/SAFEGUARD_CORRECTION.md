# Decision-audit safeguard correction (decision-audit-1.1, with addendum 1.1.1)

> **Addendum 1.1.1 (2026-10-14, 22:26 UTC).**
>
> **What happened in queue task T05 (22:20:46–22:20:50 UTC):**
> - The 1.1 `validate` ran in 3.6 s on one thread. It wrote `DECISION_AUDIT_VALIDATION.json` with status **PASS** and all 45 hard checks passing.
> - Those 45 checks are the 11 decision identities and references, including parity with Astra's frozen coefficients at m = 96 and m = 136, plus the 34 safeguard self-checks in section 4.
> - The valid synthetic case was accepted at 2^12 with a parity difference of 0.0.
> - The process then crashed with exit code 1 in its console echo: `json.dumps` was passed numpy bools, a line inherited from version 1.0.
> - The runner recorded T05 as `failed` and blocked T06–T08. Nothing was retried.
>
> **Correction 1.1.1:** the echo now casts the values to `bool`. No check, tolerance or output field changed.
> - Module SHA-256: `7af7a326…` → `e5e61a25cc4ac741d869ec1c68ff8f01f29cfc302d46cddefea8bc2b2842390f`.
> - The 1.1 validation file is kept as the record of that attempt. It no longer matches the module hash, so `manifest` refuses it, and T05 must be re-run on 1.1.1 before any freeze.
> - T05–T08 were not reset and the runner was not restarted. Re-running them is the owner's decision.

**Recorded:** 2026-10-14, 21:10 UTC (23:10 CEST), before the audit was validated, frozen or run.

**State when corrected:**
- `v2_decision_audit/` held only `intake/`. No `DECISION_AUDIT_VALIDATION.json`, manifest, cache record or result existed.
- No process had imported `src/jdl_v2_decision_audit.py`. The runner was waiting for capacity at T01, and T05–T08 were all `pending`.

This correction changes how checkpoints are accepted, which readouts they may enter and how the result is reported. It does not change the scientific design.

## 1. What was missing (verified in the code of commit `a0e3dd67`)

**A. Numerical-ladder failures would have been scored.**
- `run()` labelled a checkpoint `DECISION_NUMERICAL_STOP` when Astra's QMC ladder was not accepted.
- `evaluate()` then built every metric, contrast and decision-change row from all stored predictions, with no status filter. The summary only counted the stops.
- Consequence: a finite-batch decision that had not converged would have entered BA, sensitivity, specificity, the rule contrasts and the per-simulation changes.

**B. Probability parity was computed but never enforced.**
- `run()` recorded `max_abs_p_minus_stored_prediction` but compared it with no tolerance.
- `evaluate()` wrote `"probabilities_identical_across_cutoff_rules": True` as a literal.

**Related defects found in the same review:**
- Non-finite QMC coefficients would have been scored, because `A >= B` with NaN is a silent negative.
- A missing export, comparison record or simulation ID raised `SystemExit` or `KeyError` mid-run instead of being recorded.
- A `rho1_EP` checkpoint whose separate fit had failed would have been redirected to the mixture export, then crashed on the missing stored predictions.
- Cache records were not written atomically, although the queue's T07 completion check counts those files.

## 2. What changed

### Classification and order
Every checkpoint is classified before scoring, in this order: export validity → probability parity → QMC decisions → finiteness → ladder acceptance.

| Status | Meaning | Rules it may enter |
|---|---|---|
| `ok` | All checks pass | all four |
| `INVALID_EXPORT` | Failed or missing comparison fit; export missing from or differing with the frozen index; altered file; inconsistent sidecar; non-finite or misshaped arrays; weights not a probability vector; missing, duplicated or misaligned full simulation IDs | none |
| `PROBABILITY_PARITY_FAILURE` | Probability reconstructed from the export differs from the stored V2 prediction | none |
| `DECISION_NONFINITE` | Non-finite QMC coefficients, margins or ladder changes | `paid_fraction`, `cutoff_0.5` |
| `DECISION_NUMERICAL_STOP` | Ladder not accepted, or the QMC pass failed (e.g. a non-PSD covariance) | `paid_fraction`, `cutoff_0.5` |

### Tolerances (declared before any audit outcome)
- **Parity:** `P_PARITY_TOL = 1e-10`. The test is the maximum, over the test inputs, of |closed-form mixture probability from the export − stored V2 prediction|, and every value must be finite.
- **Weights:** `WEIGHT_SUM_TOL = 1e-9` (export consistency).

### Decisions and readouts
- **Attempted decisions are kept.** Every attempted decision is written to `decisions_all.csv.gz` with its checkpoint status and per-rule validity. Invalid decisions never enter a metric.
- **Readouts:** a pooled-per-repeat readout is `AVAILABLE` only if all five folds are valid for that rule and their test sets partition the NEW population exactly once. Otherwise it is `UNAVAILABLE`, its metrics are NaN, and no surviving-subset metric is reported.
- **Contrasts:** a `rule − cutoff_0.5` contrast needs both readouts in both repeats.

### Primary result and exit code
- **Primary:** `finite_batch` on all 20 `V2_EP_mixture` checkpoints (repeats 1–2 × folds 1–5 × B16/B40). It is `COMPLETE` only if all 20 are `ok`; otherwise it is `PRIMARY_UNAVAILABLE`.
- **When the primary is unavailable:**
  - `evaluate` still writes every output.
  - It writes `DECISION_AUDIT_UNAVAILABLE.json` instead of `DECISION_AUDIT_SUMMARY.json`, which is the queue's T08 completion marker, and exits with code 3.
  - The runner then records T08 as `failed` and does not commit it. T17 still runs and nothing is retried.
  - Unreadable records have the same effect.
- **When only a secondary readout is unavailable:** the summary is written with `PRIMARY_COMPLETE_SECONDARY_UNAVAILABLE` and the affected readouts are labelled.

### Summary flags, records and gates
- **Derived summary flags:**
  - `probability_parity_pass_all_checkpoints`;
  - `cutoff_decisions_recomputed_from_p`, which recomputes the three cutoff decisions from the single stored probability column;
  - `probabilities_identical_across_cutoff_rules`, which combines the two above.
- **Ambiguity:** flags of accepted decisions are counted separately from numerical failure.
- **Records:** written to `_cache/decision_audit/_partial/` and moved into place atomically.
- **Gates:**
  - `run` refuses a manifest that does not declare `decision-audit-1.1` and the 1e-10 tolerance.
  - `manifest` refuses a validation file produced by another module version or hash.

### Unchanged
- Model and exports.
- Decision equations: `batch_coefficients`, `decision_pass`, `decisions`.
- m = 136, τ = 0.15.
- Ladder 2^10 → 2^12 → 2^14 and its 0.015 / 0.003 acceptance.
- QMC seeds, rules, metric definitions, labels, bootstrap and success criteria.
- C3 stays failed. C4 and real-data Stage A are not touched.

## 3. Hashes (SHA-256)

| File | Before | After |
|---|---|---|
| `src/jdl_v2_decision_audit.py` | `4199768ba7aefc680ddccf2ed33262a655be772acf2e4faff05732b42e26b806` (commit `a0e3dd67`) | `7af7a326c44f37d3baa8845976d942e82e41da5990cb790845f7f600dd3c7f7a` |
| `src/tests/test_jdl_v2_decision_audit.py` | (new) | `be9096a102951d89a672340aab60730738b75966e32fc0dad8aec000402deb6f` |
| `src/jdl_run_tests.py` (new file added to `FILES`) | `f80960d89ace4fdd6b8ad20ea4a02e2e5a642abedc2e26acfa796f21ecbe5ed8` | `f747e255b8061743c4dec720d919005fa02782b00ce5a82f83b17aeaf953a31a` |

No frozen hash is invalidated: the module was never in a manifest. The audit manifest (T06) will freeze the new hash. It also requires the T05 validation to have been produced by this exact file.

## 4. Tests

**Not yet run.** The host is at capacity: four one-thread SVGP workers plus Astra's reserved slot make five slots against a limit of four. Only `py_compile` and a static undefined-name check have been run; nothing has been executed numerically. The tests run through the existing queue when capacity allows.

**T05 gate (`validate`, must PASS before the T06 freeze and the T07 run):** `safeguard_selftest()` runs on a synthetic two-component export. A self-test error is recorded and fails the gate. It contains 34 hard checks:
- **Valid case:** accepted, and identical to the 1.0 computation in decisions, A, B, π and ambiguity count.
- **Forced numerical failures:**
  - forced ladder failure: `DECISION_NUMERICAL_STOP`, only the QMC rules excluded, attempted decisions kept;
  - indefinite covariance with unchanged diagonal: `DECISION_NUMERICAL_STOP` via `FloatingPointError`;
  - forced NaN coefficient: `DECISION_NONFINITE`.
- **Parity:** a 1e-8 mismatch fails, half the tolerance is accepted, a NaN stored prediction fails.
- **Invalid exports (seven variants):** NaN h mean, weights summing to 0.9, misaligned inputs, duplicated test ID, stored IDs differ, sidecar fold differs, loader reason.
- **Export files (eight checks):** valid export, exact ρ = 1 reuse, failed fit, missing record, not in the frozen index, frozen-hash mismatch, missing file, altered bytes.
- **Availability (six checks):** all `ok` gives `COMPLETE`; one primary stop gives `PRIMARY_UNAVAILABLE` (with the readouts affected exactly); a secondary failure keeps the primary; a missing or duplicated primary record and an incomplete test partition give `PRIMARY_UNAVAILABLE`.
- **Queue marker:** the marker is absent when the primary is unavailable and present when it is complete, and the queue's T08 marker is `DECISION_AUDIT_SUMMARY.json`.

**T17 (`src/jdl_run_tests.py` → `src/tests/test_jdl_v2_decision_audit.py`):**
- `test_valid_checkpoint_is_accepted_and_unchanged`
- `test_forced_ladder_failure_is_excluded_from_the_qmc_rules`
- `test_non_psd_covariance_is_a_numerical_stop`
- `test_nonfinite_coefficients_are_flagged`
- `test_probability_parity_is_enforced_at_1e_10` (four cases)
- `test_invalid_exports_enter_no_rule` (seven cases)
- `test_export_files_are_verified_against_the_frozen_index`
- `test_one_failed_primary_checkpoint_makes_the_primary_unavailable`
- `test_missing_invalid_or_unpartitioned_primary_is_unavailable` (five cases)
- `test_duplicate_record_is_never_scored`
- `test_secondary_failure_keeps_a_complete_primary`
- `test_incomplete_audit_never_writes_the_queue_completion_marker`
- `test_validation_gate_contains_the_safeguard_selftest`
- `test_written_audit_outputs_respect_availability`, which checks the real outputs once they exist.
