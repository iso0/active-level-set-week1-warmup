# Execution queue: joint-depth-label-dev

**Status of this file:** the persistent record of what runs, what waits and what is only proposed. Live per-task status is in `QUEUE_STATE.json` and the event log is `queue_log.jsonl` (both written by the runner). Recorded 2026-10-14, 19:15 local time (CEST).

## A. Running jobs, left untouched

| Job | Owner | State at 19:00 | Remaining | Handling |
|---|---|---|---|---|
| Temporal SVGP workers P1–P4: four 1-thread processes, PIDs 10216 / 22648 / 20544 / 11824, schedule T-A3 | Opus, temporal repair | 27 of 40 fits done (21 M400, 6 M800). The four second-round M800 fits (`ckpt_r2_f2..f5_B40`) are running. | 4 M800 fits (about 6.8 h each at 1 thread), then 9 M400 fits | No stop, pause, restart or change of source, branch, configuration or lock. |
| Astra's decision-acquisition pipeline: wrapper `pwsh` PID 19116, worker PIDs 23120 / 14640 | Astra | Waiting for a host slot since 15:49 (`REFERENCE_CHECKS_OR_HOST_QUEUE`); 8 CPU-s used, no reference group, fit or result | Its own reference gate, then its controlled study | Read-only. Counted as holding one slot whenever it is active. Its files are never written. |

## B. Opus's authorized queue: runner tasks (`QUEUE.json`)

Every task uses one BLAS thread and carries `--threads 1` on its command line. Component allowances are those of the cited manifests.

| Task | Depends on / gate | Protocol and code | Allowance | Approx. computation |
|---|---|---|---|---|
| T01 V2 validation | – ; gate `status = PASS` | `src/jdl_v2_validation.py` (tolerances in-file) | ≈ 110 component solves + 16 chains (part of the 300) | 3–6 min |
| T02 V2 freeze | T01 passed | `src/jdl_v2_comparison.py manifest` → committed `V2_MANIFEST.json` | 0 | seconds |
| T03 V2 run | T02 | nine arms, 180 top-level requests, exports (`src/jdl_v2_export.py`) | ≤ 300 attempts incl. validation and fallback | 2–5 min |
| T04 V2 evaluate | T03 | `src/jdl_v2_evaluate.py` (frozen definitions) | 0 | 1 min |
| T05 decision-rule validation | – ; gate `status = PASS` | `src/jdl_v2_decision_audit.py validate` (m = 2/4/96/136 identities; parity with Astra's coefficients; Gaussian fixture) | 0 fits | 1 min |
| T06 decision-audit freeze | T04, T05; gates T01 and T05 | `DECISION_AUDIT_MANIFEST.json` (m = 136, fixed fold reference, four rules) | 0 | seconds |
| T07 decision-audit run | T06 | decision-only readouts on the exported posteriors | **0 fits** | 1–3 min |
| T08 decision-audit evaluate | T07 | metrics, rule contrasts, per-simulation changes | 0 | 1 min |
| T09 EX metrics addendum | – | `src/jdl_ex_metrics_addendum.py` (stored predictions only) | 0 fits | 1 min |
| T10 POST-HOC descriptive re-run | – | `src/jdl_ex_descriptive.py` (adds corner BA and AUC files) | 0 fits | seconds |
| T11 checkpoint-mechanism validation | – | `src/jdl_svgp_resumable.py validate` (torch venv; synthetic data) | 3 short synthetic trainings | 1–3 min |
| T12 EX3 freeze | T01 passed | `src/jdl_ex3.py manifest` → committed `EX3_MANIFEST.json` | 0 | seconds |
| T13 EX3 run | T12 | NEW DEV 5–8, B16/B40 | ≤ 200 component solves | 1–3 min |
| T14 EX3 evaluate | T13 | – | 0 | 1 min |
| T15 temporal evaluation | waits for all 30 M400 + 10 M800 fits and no SVGP worker alive | `src/jdl_temporal_eval.py evaluate` (frozen in `29ca7364`) | 0 fits | 5–15 min |
| T16 stopping-audit numbers | same wait | `src/jdl_temporal_stopping_audit.py` | 0 | seconds |
| T17 tests | after the above (runs even if some are blocked) | `src/jdl_run_tests.py` | 0 | 1–2 min |
| T18 notebook | after T15 | `src/jdl_notebook.py` | 0 | 1 min |

- **Ordering:** the runner takes the first ready task in this order, so the V2 chain runs first, then the decision audit, then the no-fit analyses, then EX3, then the temporal tasks once their fits exist.
- **Failed gates:**
  - If T01 fails, T02–T04, T06–T08 and T12–T14 are blocked and recorded; T05 and T09–T11 and T15–T18 still run.
  - If T05 fails, only T06–T08 are blocked.
  - Nothing is retried automatically.
- **Decision-audit safeguards (decision-audit-1.1, recorded 2026-10-14 21:10 UTC, before T05–T08 ran):** see `v2_decision_audit/SAFEGUARD_CORRECTION.md`.
  - T05 now also runs 34 safeguard self-checks, and its gate needs all of them to pass.
  - T07 writes one record per checkpoint with an acceptance status (P_PARITY_TOL = 1e-10).
  - If the primary finite-batch audit is incomplete, T08 writes `DECISION_AUDIT_UNAVAILABLE.json` instead of its completion marker and exits with code 3. The runner then records T08 as `failed`, does not commit it, and still runs T17.
  - `QUEUE.json` is unchanged.
- **Commits:** after each successful task its outputs, together with this queue directory, are committed by path and pushed. Git failures are logged, not fatal.

## C. Continuation mechanism (what actually advances the queue)

- **Runner:** `src/jdl_queue_runner.ps1`, one PowerShell process. It holds a single-instance handle on `queue/runner.lock`.
  - **No double claims:** it counts every leaf numerical process (1 slot with `--threads 1`, otherwise 4), excluding Astra's process tree, plus one reserved slot for Astra's pipeline while that pipeline is active. A job starts only if the total stays ≤ 4 at two checks 60 s apart.
  - **Who gets which slot:** the first slot freed by the temporal workers is left to Astra, which is already waiting for it; Opus's runner uses the next one. Because both runners use compatible counts, at most four numerical threads run at any time.
- **Resume after any interruption** (reboot, session end):

  ```
  powershell -NoProfile -ExecutionPolicy Bypass -File src\jdl_queue_runner.ps1
  ```

  - Completed tasks are recognised from their outputs and never rerun.
  - An interrupted V2 or EX3 run refuses to continue until its pending marker has been audited.
- **Limitations:**
  - The runner computes and commits, but the narrative reports (`V2_MODEL_REPORT.md`, `EX_METRICS_ADDENDUM.md`, the decision-audit report, `TEMPORAL_REPAIR_REPORT.md`, the claims matrix) need an Opus agent turn after the computations.
  - A reboot also stops the temporal workers; restarting them is a separate, explicit recovery step.

## C2. Logged technical recovery of T05–T08 (owner authorization of 2026-10-14)

- **What happened:**
  - Queue T05 wrote a PASS validation (45/45) and then exited with code 1 at its console echo.
  - The runner recorded T05 as `failed` and T06–T08 as `blocked`.
  - These records stay unchanged in `QUEUE_STATE.json` and `queue_log.jsonl`.
- **Recovery sequence:** `src/jdl_recovery_decision_audit.ps1` is a one-shot sequence, not a second runner. It has its own lock, state and log in `recovery/decision_audit_T05_T08/`.

  | Step | Action |
  |---|---|
  | R04 | Preserve the 1.1 PASS file |
  | R05 | Validation retry with decision-audit-1.1.1 |
  | R06 | Freeze and commit the manifest |
  | R07 | Decision-only run (zero fits) |
  | R08 | Evaluate (exit 3 = PRIMARY_UNAVAILABLE, recorded) |

- **Coordination with the live runner:**
  - **Capacity:** both use the same rule, so the combined total stays at four threads or fewer.
  - **No duplicate work:** the live runner never reruns T05–T08, because they are `failed` or `blocked` in its state.
  - **No shared outputs:** the recovery writes only `v2_decision_audit/`, `_cache/decision_audit/` and its own records. T15–T18 write elsewhere.
  - **Tests:** T17 only reads the audit outputs once the summary file exists.

## D. Outside the authorized scope (proposals or drafts only)

- **Real-data Stage A** (`STAGE_A_PROTOCOL_DRAFT.md`): not authorized.
- **C4 stability check** (`C4_STABILITY_DRAFT.md`): not authorized.
- **Astra's bounded DEV 3–4 acquisition policy draft** (three selectors, B16–B24, ≤ 270 top-level and 900 component solves): explicitly "do not execute now".
- **Any savings endpoint, new simulations, morphology/annotation review, relabelling, q30 or a main-branch merge:** not authorized.
