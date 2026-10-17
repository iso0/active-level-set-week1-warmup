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

**No duplicates:** the same fits are never run twice. Existing caches (TRAINED_AL, CORNER_LOCAL, pilot A references, Week 6/7/19 summaries) are reused and cited.
