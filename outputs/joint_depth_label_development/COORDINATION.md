# Coordination record — numerical work from 2026-10-16 (single coordinator: Claude)

This is the owner's instruction of 2026-10-16. Claude coordinates all new numerical work. All work on this machine stays within **4 compute threads in total**, BLAS/Torch sub-threads included. Astra opens no independent heavy queue. If a numerical pilot is assigned to Astra, she gets 1 thread and Claude at most 3. Unrelated workers count toward the total. Capacity is allocated once here, not by independent check-and-launch.

| Task | Owner | Threads | State (UTC) | Evidence |
|---|---|---|---|---|
| ASTRA_AL / BA_RISK | — | 0 | **STOPPED BY OWNER** 2026-10-16 21:01–21:03; no restart; P2 not completed (not a negative result) | `astra_al/cancellation/` |
| Physical monitor download (velocity, KE, laser power, max temperature; 136 NEW runs; pinned 2e1eec9c) | Claude | 1 (I/O) | done 21:18; 952/952 files verified | `physical/provenance/` |
| Pilot A: SURPRISE_DISCOVERY | Claude | 2 | done 21:25, evaluated 21:28 | `surprise_discovery/` |
| Pilot B: PHYSICAL_PILOT (physical outputs from x) | Claude | 1 | done 21:28 | `physical/` |
| Pilot C: TEMPORAL_VEL (temporal GP, velocity) | Claude | 1 | done 21:33 | `temporal_vel/` |
| PHYS_AUX, PHYS_AUX_REP (r5–8), E1_AUX (one correction) | Claude | ≤ 2 | done 21:36–21:44 | `phys_aux/`, `phys_aux_rep/`, `e1_aux/` |
| Astra package `astra_monitor_discovery_20261016` | Astra (design) | **0 granted** | received 21:24–21:39; snapshot copied verbatim 21:47 (13 files, SHA-256 identical) | `outputs/astra_monitor_discovery_20261016/` |
| Extra monitor download: NEW total energy and particle number; OLD monitor channels (owner approval 2026-10-17) | Claude | 1 (I/O) | done 23:18; 3639/3639 verified; 278 OLD paths missing remotely (56 runs) | `physical/provenance/download_manifest_physical2.csv` |
| Study 1 PHYS_AL: units, then ICM, then evaluation | Claude | 2 (+1 for ICM) | v1.1 extraction finished 23:26:16; units 23:26:59–23:45:29 (PIDs 12672 NEW, 3512 OLD; 380/380 ok); evaluated 23:48:18–23:49:35 | `phys_al/` |
| Study 2 PHYS_DISCOVERY: units, then evaluation | Claude | 1 | units NEW 23:27:00–23:28:45, OLD 23:28:45–23:30:46 (80/80 ok); evaluated 23:36–23:37 | `phys_discovery/` |
| Study 3 TEMPORAL_STRUCT | Claude | 2 | NEW 23:24:23–23:36:04 (PID 2752); OLD 23:31:04–23:40:16, in the slot Study 2 freed | `temporal_struct/` |
| Study 1 PHYS_AL ICM | Claude | 1 + 1 | OLD 23:37:48–23:46:54 (PID 16040, 420 fits); NEW 23:40:39–23:48:06 (PID 4348, 420 fits), in the slots the Study 3 runs freed | `phys_al/icm_predictions_*.json.gz` |
| Report, tables, figures | Claude | 1 | ≤ 00:45 on 2026-10-17; formatting and plots only | `STUDIES_REPORT_20261017.md`, `STUDIES_20261017_TABLES.md`, `studies_20261017_figures/` |

**State at 00:45 UTC on 2026-10-17:** no numerical process is running (0 python.exe). All three registered studies are complete and evaluated. Nothing is queued.

**Capacity check (23:42 UTC), with 4 leaf workers:**
- Measured CPU use over 10 s: 0.97, 0.97, 0.97 and 0.98 cores per worker.
- PID 4348 shows 4 OS threads, but its CPU use is one core, so the extra threads are idle (runtime or loader threads), not compute threads.
- One sub-second slip is logged as CAP-OBS in the ledger.

## Decision on Astra's package (21:47 UTC)

**No reservation is granted now, and it was not run.** Reasons:
1. **Not frozen.** `FROZEN_MANIFEST.json` is absent, yet her runner requires it and her handoff takes the code digest from it.
2. **Workspace rule.** Her runner writes into her own workspace, which this project never modifies.
3. **Overlap and authority.** The owner's instruction says her proposals need not be adopted. Its question — surprise → bounded local reaction while global exploration is kept — overlaps with the completed SURPRISE_DISCOVERY pilot.
   - **Her distinct additions:** null and bad-monitor worlds, a same-schedule ablation (the discriminating test for a global-coverage confound), and a 4-query bounded episode.
   - **Option for the owner:** a 1-thread reservation (≤ 1200 s, 650 solves) once she supplies `FROZEN_MANIFEST.json`. It would run on a copy, never in her workspace.

## Her two remarks, checked

1. **Temporal work gating.** In practice the temporal pilot was **not** gated on the short-K classification. As the owner's first instruction asked, its channel was chosen from the cheap scalar pilot. Her point that temporal modelling is independent of scalar wins is accepted for future protocols.
2. **QC of the early-ended run.** The structural point is valid: the extractor marks a run with unequal row counts UNAVAILABLE before counting non-finite values, so `QC_SUMMARY.json` has no counts for that run. Raw reconciliation (21:46 UTC; ledger QC-REC):
   - H-e7dbd8e5ce has **0** non-finite KE (115,600 KE and time rows).
   - **All 931** previously reported non-finite KE values are in **H-ce04be44b1** (24,323 rows), as pilot B reported.
   - Her attribution of the 931 values to the early-ended run is therefore not supported by the raw files.
   - Pilot B's frozen outputs are unchanged.
   - **Erratum, 2026-10-18 (ledger QC-REC-ERRATUM).** The "0 non-finite KE, 115,600 rows" check above was made on the wrong run. `P-376p072436697…_H-e7dbd8e5ce` shares the H code. The early-ended run `P-423p267621988…_H-e7dbd8e5ce` has row-mismatched channels: time 40,803, bounds 40,805, KE 40,807, temperature 40,804 rows. It has 0 non-finite values. Astra's structural point was right: row mismatch and non-finite counts are two distinct findings. The 931 values still belong to H-ce04be44b1.

**No duplicates:** the same fits are never run twice. Existing caches (TRAINED_AL, CORNER_LOCAL, pilot A references, Week 6/7/19 summaries) are reused and cited.

---

## Research campaign 20261018 (owner decision of 2026-10-18; 48 hours from T0)

**Single coordination record.** From now on, the single machine-readable record is `pool/POOL_PLAN.json`, in the block `coordination` and the list `external_reservations`. Both Opus and Astra read it, and Astra's runner reads it directly. This file is its human-readable log.

**Update protocol** (`src/rc18_coord.py`):
1. Take the exclusive lock `pool/COORDINATION.lock`.
2. Read the record and change only your own share.
3. Write a temporary file and `os.replace` it.
4. Delete the lock.

**Budget:**
- T0 = **2026-10-18 08:41:20 UTC**; deadline = **2026-10-20 08:41:20 UTC** (48 h).
- This is one total budget: errors and restarts do not reset it, and no new fit starts after the deadline.

**Host and capacity:** `Burak`, 8 logical CPUs / 4 physical cores, 31.8 GB RAM. Capacity is **4 numerical threads in total**.
- At 08:45 UTC there were no unrelated numerical workers (0 python/julia/Rscript).
- Background load was about 1 logical CPU, from interactive apps only (Claude, ChatGPT/Codex UI, Task Manager).

| Share | Threads | Status | Granted (UTC) | Valid until (UTC) | Rule |
|---|---|---|---|---|---|
| Opus | 2 | active | 2026-10-18 08:46:11 | 2026-10-20 08:41:20 | runner `src/rc18_runner.ps1`, at most 2 leaf processes × 1 BLAS thread; Astra's frozen pilot (1 thread) is drawn from this share |
| Astra | 2 | **reserved** | 2026-10-18 08:46:11 | 2026-10-20 08:41:20 | created before any heavy Opus computation; Opus never uses it without Astra's completion/release record; Astra lists her live jobs in the record |

**Not reopened:** ASTRA_AL / BA_RISK (cancelled by the owner on 2026-10-16) and the 2026-10-15 pool runner (ended with POOL_END).

**Live jobs:** their PIDs, commands and start times are kept in `pool/POOL_PLAN.json` (the `shares[].jobs` and `external_reservations` fields) and in the runner heartbeat `outputs/research_campaign_20261018/opus/runner/HEARTBEAT.json`.

**Opus runner jobs, RC18.** From `runner/runner_log.jsonl`. Each job ran 1 worker with 1 BLAS thread, every exit code was 0, and no unit failed.

| Job | Worker PID | Start → end (UTC, 2026-10-18) | Units |
|---|---|---|---|
| selftest / selftest_crash | 19164 / 23564, 11268 | 08:56:04 → 08:56:34 | self-test only (crash path intended) |
| data_extract | 25244 | 09:13:40 → 09:21:14 | 541 |
| dev_reg / dev_moivr / dev_region | 5952 / 7176 / 11168 | 09:29:17 → 10:19:44 | 60 / 50 / 240 |
| final_reg_new_maximin | 25932 | 10:36:20 → 10:53:04 | 100 |
| final_reg_old_maximin | 12252 | 10:41:53 → 10:51:02 | 40 |
| final_region | 3244 | 10:51:03 → 11:26:33 | 480 |
| transfer_design (A2) | 11144 | 10:59:39 → 11:03:42 | 60 |
| final_label | 25776 | 11:04:43 → 11:07:15 | 100 |
| physlabel (A3) | 16284 | 11:08:16 → 11:13:21 | 40 |
| final_reg_designs | 9352 | 11:15:53 → 11:46:48 | 160 |
| d2_features | 26748 | 11:28:04 → 12:08:04 | 80 |
| d2_curves | 13640 | 11:46:48 → 12:25:47 | 80 |
| robust_r34 (A1) | 17772 | 12:08:04 → 12:18:12 | 70 |
| physgpc (A4) | 17892 | 13:33:47 → 13:39:51 | 40 |

**State at 14:05 UTC:**
- The runner (PID 29180) and supervisor (PID 7136) are alive and IDLE, with no queued work.
- Opus holds 0 slots in the record. Astra's 2-thread share is untouched, and she has registered no jobs.
- Restart: `powershell -NoProfile -ExecutionPolicy Bypass -File src\rc18_start_runner.ps1`.

### RC19 pooled from-scratch queue (owner instruction 2026-10-19)

The budget is unchanged: the same campaign clock and the same deadline, 2026-10-20 08:41:20 UTC.

**Single Opus queue:** `src/rc19_runner.ps1`, with plan `outputs/research_campaign_20261018/opus_pooled/runner/PLAN.json`.
- Started detached at about 12:41 UTC through `src/rc19_start_runner.ps1`. Supervisor PID 17548; the runner PID is in `opus_pooled/runner/HEARTBEAT.json`.
- The RC18 runner was idle and has been retired with `stop_runner` (exit 0 at 12:40:39 UTC).

**Capacity:** Opus 2 threads, Astra 2 threads reserved and untouched, total 4.
- At 12:25 UTC Astra had 2 live single-thread workers (`run_unit.py --threads 1`). They are not listed in her share's `jobs`, and they do not descend from codex.exe.
- The RC19 runner therefore counts any process whose command line contains her workspace path (`\Codex\` or `astra_`) against her share, never against Opus.

**Launch rule:** a worker starts only after the runner takes the coordination lock and re-checks that
- Opus used + 1 ≤ min(2, runner_slots), and
- Astra used + Opus used + 1 ≤ 4.

The Opus job list in the record is written in the same lock.
