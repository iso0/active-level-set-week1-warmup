# ASTRA_AL — stopped by the owner (2026-10-16)

**Status: STOPPED BY OWNER (compute cost and priority). The study is INCOMPLETE.**

- The registered contrast **P2 (BA_RISK − V2_VARIANCE) was not completed.** It is not a negative result and must not be reported as one.
- P1 and S1 were already unavailable by protocol, because of two preserved ALIGNED_MARGIN decision stops (ledger AAL-INT).
- The frozen protocol, manifest, code and earlier numerical stops are unchanged. This record is separate from them.

## Decision and authority

The owner's instruction of 2026-10-16 says: stop the ongoing ASTRA_AL / BA_RISK computation, do not complete it, and do not wait for an hours-long risk step. It also forbids starting a new BA_RISK repeat or arm, and any extension of the numerical ladder.

## What was stopped (UTC)

| Time | Action | Evidence |
|---|---|---|
| 21:01:12 | `astra_al_risk` disabled in `pool/POOL_PLAN.json` (`enabled: false`, `max_workers: 0`) before any process was touched, so that no new BA_RISK launch could happen | `pool/pool_log.jsonl` event `OWNER_STOP_ASTRA_AL_RISK` |
| 21:01 | State snapshot of every unit, read only | `PRE_STOP_STATE.json` |
| 21:02:0x | Finalizer stopped: background task, then the verified inner bash PID 8632 (`jdl_astra_al_finalize.sh`) and its `sleep 300` PID 100 | process list: 0 finalizer processes left |
| 21:02:3x | BA_RISK workers terminated after command-line verification (`src.jdl_astra_al work --arms BA_RISK`). Each was an alias/real pair: 3108/23200 (`r4_f2`), 17196/15456 (`r4_f3`), 23608/7976 (`r4_f4`). No checkpoint was being written (`partial/tmp` empty) | 0 `jdl_astra_al` processes left |
| 21:02:49 | The pool runner (PID 21772) reaped the three workers (exit −1), released their stale locks and logged **POOL_END**. Every other study was already finished, so the runner exited by itself | `pool/pool_log.jsonl` |
| 21:03:02 | Post-stop snapshot is identical to the pre-stop snapshot (all checkpoints intact) | `POST_STOP_STATE.json` |
| 21:03:10 | Capacity check: 0 numeric processes on the machine, no runner or finalizer alive. Astra's pipeline is `COMPUTATION_FINISHED_REVIEW_REQUIRED` (wrapper not alive) | — |

No other process was touched. In particular, the unrelated PowerShell 12388 from 2026-10-14 was left alone.

## Last sound state of each trajectory

| Arm | Finished units | State at stop |
|---|---|---|
| ALIGNED_MARGIN | 10/10 | 8 `ok`; `r3_f4` DECISION_NUMERICAL_STOP at B20 and `r4_f3` at B24 (preserved; P1 and S1 unavailable) |
| V2_VARIANCE | 10/10 | all `ok` |
| BA_RISK | 6/10 (`r3_f1` to `r3_f5`, `r4_f1`; all `ok`, readouts to B24) | `r4_f2`: last sound budget B19, interrupted in step B20. `r4_f3`: B21, interrupted in B22. `r4_f4`: B16, interrupted in B17. `r4_f5`: never started. All partial checkpoints are kept in `_cache/astra_al/partial/`. |

## Numerics recorded (verified on disk at stop; `PRE_STOP_STATE.json`)

- **BA_RISK, finished units:** 48 selections, all accepted, **0 of 48 with a resolved ranking**; each was chosen by the frozen smallest-index rule among tolerance-tied candidates. Median selection time 9243 s (2.57 h).
- **BA_RISK, including partial units:** 59 selections, 0 resolved, median 9289 s. 33 of the 59 steps needed the (12,33) level.
- **V2_VARIANCE:** median selection time 20.5 s. **ALIGNED_MARGIN:** less than 1 ms.
- Caps were not reached: 230 of 270 fits and 690 of 900 component solves at the last interim evaluation.

## What may be reported

- Only the completed units, descriptively: `astra_al/results/` is the frozen evaluation of the 26 finished units, run 2026-10-16 19:50 UTC.
  - Repeat 3, descriptive: BA_RISK and V2_VARIANCE finite-batch BA-AULC are both 0.815, and short-K detection is 0 of 10 at B24 in both (ledger AAL-INT2).
- P2 is **not available: stopped by the owner**.
- ASTRA_AL had no G3/E1 comparison and no registered simulation-saving endpoint.

## Restart policy

No restart. The plan entry stays disabled. `src/jdl_astra_al_finalize.sh` must not be relaunched for this study.
