# RC19 pooled from-scratch campaign (Opus) — status log

The live machine state is in `runner/HEARTBEAT.json` and `runner/STATUS.md`. Attempts are recorded in `outputs/joint_depth_label_development/ATTEMPT_LEDGER.md`, rows RC19-*.

**Budget:** the research-campaign-20261018 clock is unchanged; the deadline is 2026-10-20 08:41:20 UTC.

## Update 1 — 2026-10-19 13:40 UTC (about 19 h left)

**Resources:**
- Opus has 2 threads, used by the single queue `src/rc19_runner.ps1` (supervisor PID 17548, runner PID 19528, started 12:41 UTC).
- Astra has 2 threads; her deep-discovery campaign was running and untouched (her TEST 6,399 of 10,224 at 12:25 UTC).
- The RC18 runner was retired via its stop flag.

**Restart after a reboot:**

`powershell -NoProfile -ExecutionPolicy Bypass -File src\rc19_start_runner.ps1`

This is idempotent: finished units are skipped and a lock prevents a second runner.

**Done:**
1. **Pooled data layer:** 541 runs, checks, splits and a paid-only reveal interface. Shadow validation PASS for every learner family.
2. **Development** on pooled DEV repeats 1–2 (350 trajectories, 0 failures; results in the ledger row RC19-DEV):
   - regression: SHQ beats M0 by +0.026 R²-AULC; adaptive acquisition helps without an archive;
   - region: straddle +0.031 BA-AULC over maximin;
   - label: the physics classifier ties E1 + straddle on BA, with better log loss;
   - the NEW fast-scan corner fails for every arm.
3. **Freeze:** `PROTOCOL_RC19.md` plus the manifest, committed as 8f82e404 before any final unit.
4. **Addendum AX** (Astra's v2 selector on pooled data) registered (a93f4a61); hash-checked copy of her frozen files.

**Running:** the final programme on repeats 3–10, 920 units, label → region → regression → bounded temporal. Next comes the AX adapter acceptance, then the 32 AX trajectories.

**Next:** the report generated from the frozen units; the 3D pooled boundary view; the Turkish summary.

## Update 2 — 2026-10-19 15:12 UTC (about 17.5 h left)

**Final programme complete:** 920 of 920 units and AX 32 of 32, 0 failures. The runner (PID 17384) and supervisor (PID 17548) are IDLE; the runner stops by itself at the deadline. Astra's campaign was never touched: her TEST was at 6,813 of 10,224 at 13:55 UTC.

**Verdicts (DEV, 8 final repeats, margin 0.02, at least 7 of 8 in the same direction):**
- **A: BETTER.** SHQ vs M0 +0.035 R²-AULC (8 of 8). MOIVR adds +0.010.
- **B: BETTER.** Straddle vs maximin +0.027 BA-AULC (8 of 8). SHQ + straddle reaches BA 0.95 after 21–26 simulations.
- **C: NOT DIFFERENT.** The physics classifier vs E1 + straddle is +0.005 BA, but log loss is −0.086 (8 of 8). The NEW fast-scan corner is unresolved.
- **D:** no curve-model gain over the scalar GP.
- **AX:** Astra's local / surprise reaction −0.003 (0 of 8); her global SUR ≈ straddle (+0.006).

**Deliverables:**
- `FINAL_REPORT_RC19.md`, `report/RESULTS_TABLE.md`, `report/AX_RESULTS.md`;
- figures, predictions and paths;
- the 3D view (private claude.ai page);
- `MODEL_DEFINITIONS_RC19.md`, `QUEUE.md`.
