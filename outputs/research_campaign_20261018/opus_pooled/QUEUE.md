# RC19 persistent execution queue (Opus)

| Item | Where / what |
|---|---|
| Queue engine | `src/rc19_runner.ps1`, with supervisor `src/rc19_supervisor.ps1`; single instance through `runner/runner.lock` |
| Plan (jobs, priorities, dependencies `after`, worker caps) | `runner/PLAN.json`, re-read every 30 s |
| Live progress / heartbeat | `runner/HEARTBEAT.json` (every cycle), `runner/STATUS.md` (every 5 min) |
| Events | `runner/runner_log.jsonl` (worker start/end/failure, stale locks); supervisor events in `runner/supervisor_log.jsonl` |
| Resource ownership | Opus share = 2 threads in `outputs/joint_depth_label_development/pool/POOL_PLAN.json`. Each launch is checked and recorded inside the coordination lock. Astra's 2 threads are never used; her processes are recognised by codex ancestry, her listed PIDs, or her workspace path in the command line. |
| Protocol / hashes | development: `PROTOCOL_RC19.md` §8 and ledger RC19-DEV; final: `final/RC19_FINAL_MANIFEST.json` (freeze commit 8f82e404), checked by every final worker before it claims a unit; addendum AX: `PROTOCOL_RC19_ADDENDUM_AX.md` (commit a93f4a61) plus `astra_copy/COPY_MANIFEST.json` and `astra_copy/ADAPTER_ACCEPTANCE.json` (PASS) |
| Checkpoints | one file per finished unit: `<stage>/<job>/units/<unit>.json.gz` (atomic write). Failures: `<stage>/<job>/failed/<unit>.json`, never retried automatically. Claims: `<stage>/<job>/locks/<unit>.lock` (PID inside; released when the PID is dead). |
| Deadline | from the coordination record, 2026-10-20 08:41:20 UTC. No unit is claimed after it; unfinished work stays checkpointed and is reported as such. |

## Jobs

| Job | Units | Dependency | Command |
|---|---|---|---|
| dev_label / dev_label2 / dev_region / dev_reg / dev_full / dev_temporal | 100 / 20 / 120 / 80 / 20 / 10 | — | `python -m src.rc19_jobs work <job> --threads 1` |
| final_label | 280 | freeze manifest | `python -m src.rc19_jobs work final-label --threads 1` |
| final_region | 320 | freeze manifest | `python -m src.rc19_jobs work final-region --threads 1` |
| final_reg | 280 | freeze manifest | `python -m src.rc19_jobs work final-reg --threads 1` |
| final_temporal | 40 | freeze manifest | `python -m src.rc19_jobs work final-temporal --threads 1` |
| addendum_ax | 32 | AX acceptance PASS + freeze manifest | `python -m src.rc19_astra work --threads 1` |

## Exact launch / resume

Detached, idempotent: finished units are skipped and a second runner exits at once.

`powershell -NoProfile -ExecutionPolicy Bypass -File src\rc19_start_runner.ps1`

The supervisor restarts a crashed runner at most 6 times in 6 h. A reboot or log-off stops it; run the line above again.

## Continuation verified

- The RC18 runner was retired through its plan flag (exit 0, supervisor end at 12:40:39 UTC).
- The RC19 runner started at 12:41:43 UTC.
- Final tally: 17 worker processes started and 15 logged exit 0. The other 2 were the region workers orphaned by the deliberate runner kill (RC19-RESTART-TEST, 13:52 UTC); they finished all their units unreaped. No worker failed.
- Every final unit is complete: 920 of 920, plus AX 32 of 32.
- The runner (PID 17384 after the restart) is IDLE and stops by itself at the deadline.
- Unit-level resume works: workers skip units that are done or failed, and different workers on one job never duplicate a unit (O_EXCL claims).
