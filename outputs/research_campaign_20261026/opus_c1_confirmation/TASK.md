# C1 confirmation (C1C): task record

**Owner instruction:** 2026-10-26, pasted Turkish (summary below). The original wording governs.
**Task start:** 2026-10-26T18:05:16Z, the first state check. One 48-hour window, ending 2026-10-28T18:05:16Z; quota waits, restarts and session changes never reset it.
**Start state:**
- HEAD = origin/joint-depth-label-dev = 21a1c045d5fb0fb811fac85dbea186259235b38d, no later commits, no tracked changes.
- EA campaign CLOSED (17:17:19Z).
- Astra campaign `astra_joint_local_20261026` ACTIVE with 3 workers (read-only check of `astra_state.json`).

## Goal

Validate **C1 + margin** as one fixed recipe, show its reliability, and give a clear use decision. Report separately:
- the early-learning gain;
- the query saving to BA 0.95;
- robustness.

## Instruction summary

1. **Fix C1 exactly as in EA** (`src/ea_cand.py` SYSTEMS["C1"]): model, physics trend, prior centres and SDs, optimiser starts, honest cross-fit, classifier and threshold, margin and the one-class rule.
   - Verify reproduction on earlier cases.
   - No unjustified refactor or new variant.
   - Freeze code, recipe, IDs, metrics and decision rules by commit + push BEFORE any new result.
2. **Main validation:** 80 fresh STD repeats 203–282 (400 learners), uncertainty over repeat clusters.
   - Arms: C1 + own margin path vs HA_LEAN + own margin path; the strong early control (HA_LEAN selects / HA_TREND predicts); C1 on HA_LEAN's path.
   - Shared startup, test set and budget.
   - One registered evaluation: no peeking, stopping or resizing.
   - Two pre-defined 40-repeat subgroups are shown; the verdict is on all 80.
   - Old results stay side by side, never pooled selectively.
3. **Separate verdicts** with the EA definitions; ambiguities resolved before results.
   - Covered: early; 0.90 / 0.93 efficiency; 0.95 efficiency; attainment and sustainment; probability quality and CPU.
   - Individual learners primary, pooled beside.
   - Full metric list: §3 of the protocol.
4. **Startup robustness:** random-8 and clustered-8 label-free startups, ≥ 20 fresh repeats each, IDs separate.
   - One-class starts are kept, and the cost of finding the second class is counted.
   - Results are reported separately, not averaged with the standard startup.
5. **Prior sensitivity (control only):** SDs × 0.5 and × 2, centres unchanged, on the reviewed DEV paths.
   - Never promoted to the candidate.
   - Full-pool diagnostics were seen when the prior was chosen; this design effect is disclosed.
6. **Information rules:**
   - one 541-run pool, no OLD/NEW changes, no free archive;
   - every opened simulation counts (startup included), and a run's channels are opened once;
   - no oracle, full-pool hyperparameters, test labels or hard-group membership in any deployable arm;
   - labels, exclusions and hard-group definitions unchanged;
   - no physical simulator, paid API / cloud or protected C4 evaluation;
   - if 0.95 does not replicate: no further seeds or variants.
7. **Decision document:**
   - where C1 + margin is recommended;
   - replication of the early gain and of the 0.95 saving;
   - startup and prior effects;
   - when HA_LEAN is safer;
   - pool-only claims;
   - a short external-validation plan for Ioan, built from the existing physical-data proposal (no simulations, no messages);
   - known MAP / GP parts are not presented as an original method.
8. **Astra, resources, continuity:**
   - Astra's live folder, Git, environment, processes, automations and share are never touched.
   - Writes in `thesis_shared_runtime/campaign_20261026` are limited to `opus_state.json` (new campaign id) and own lock and temp files; the EA closure records are not changed.
   - ≤ 3 single-thread numerical workers (Astra 3, system 2), memory guard.
   - Chat-independent, checkpointed and retry-safe runner; persistent TASK / STATE / NEXT_ACTION; no continuous LLM polling.
9. **Delivery:**
   - one-page Turkish result; the fixed model's equation and algorithm;
   - tables for the main, startup and prior parts, plus per-target tables;
   - old vs new side by side;
   - predictions, paid IDs and a cost breakdown;
   - independent recomputation and a freeze check;
   - the use decision and the external-validation plan;
   - records updated without deleting failures;
   - commit and push by explicit paths, then a local = remote SHA check.

Campaign id: `opus_c1_confirmation_20261026`. Folder: `outputs/research_campaign_20261026/opus_c1_confirmation/`.
