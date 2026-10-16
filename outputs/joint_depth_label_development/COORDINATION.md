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
