# C1 stability (C1S): task record

**Owner instruction:** 2026-10-29, pasted Turkish, invoked with `/graphify`. The original wording governs.

**Task start:** 2026-10-29T00:10:41Z, the first state check. One 48-hour window, ending 2026-10-31T00:10:41Z; quota waits, restarts and session changes never reset it.

**Start state**

| item | state |
|---|---|
| repository | iso0/active-level-set-week1-warmup |
| worktree | `C:\Users\ozgur\Documents\thesis\.claude\worktrees\joint-depth-label-dev` |
| HEAD | 3caf7c4e (= origin/joint-depth-label-dev, the C1/C1C baseline) |
| origin/main | 4fc9b5d (Research Hub); `src/` identical (0 files differ; merge-base = 3caf7c4e) |
| research branch | `c1-stability-20261029`, created at 3caf7c4e. No reset; 49 untracked experiment records kept. |
| processes | no Python process running at the start; Astra's codex host present, no Astra worker |
| shared folder | `thesis_shared_runtime\campaign_20261029` did not exist yet |

## Goal

Keep C1's early success, find the cause of the regressions during learning, and implement one justified improvement.
- This is a research task: no thesis writing, no archiving or consolidation project, no new physical data.
- **Primary metric:** BA-AULC B8–B24; B8–B60 is also reported.
- **Reported beside it:**
  - both recalls; FN / FP counts;
  - attainment, confirmation, keeping at B60, sustaining;
  - simulation and CPU cost.
- **Supplementary, never used to change the winner:** F2, precision, log loss, Brier.
- **Fixed references:** C1 + margin is the main method and stays unchanged. HA_LEAN + margin is the historical reference. C1C is closed and is not reopened.

## Instruction summary

1. **Versions and workspace.** Verify the versions and the workspace. Work on the research branch. Push results; no merge to main.
2. **Graphify.**
   - Use only the explicit pinned graph: two narrow queries, verified against the source.
   - Write a usage note and a C1 code map (both in `graphify/`).
   - Never use the old default graph. Change no global setting. Never use the snapshot as an experiment workspace.
   - Use the Hub reading layer for navigation only; go to the real reports. Keep historical M3/G3, the old corner-local C1 and the C1C model apart.
3. **Scientific targets and fixed references:** listed under Goal.
4. **Diagnose first** (DEV, from existing EA/C1C predictions, paths and records).
   - Questions:
     - do a few boundary points cause the drops?
     - which class is lost?
     - how do depth, GP hyperparameters, target standardisation and classifier weights change?
     - what is the model-update effect, and what is the path effect?
   - Controls on identical paid data; a few recomputed cases, with the selection rationale recorded.
   - Oracle stopping or version picking is diagnosis only.
   - All learners are kept.
5. **Develop and test.**
   - At most 2 justified candidates, at most 1 carried forward.
   - A simple mechanism control: freeze at a fixed budget, or update less often.
   - No repeat of the EL mixture, BA_RISK, JEER or coverage rules.
   - Freeze code, protocol, sample size, primary comparison and rules by commit before the fresh test.
   - Fresh test on ≥ 40 unused same-pool repeats × 5 folds, fixed size, no C4 / protected gates. Controls: C1 + margin, HA_LEAN + margin, the simple control.
   - Pre-register:
     - the early-loss margin (do not relax C1C's 0.003);
     - one primary stability metric with a practical threshold (suggested: mean shortfall of BA below 0.95 over B24–B60);
     - harm limits for both classes and for spend;
     - a limited random / clustered startup control.
   - Report 0.90 / 0.93 / 0.95 endpoints separately. "Stability", "early BA" and "fewer simulations" are separate decisions.
6. **Data and resources.**
   - One 541-run pool; every opened run counts; no hard-group or unopened information reaches a learner.
   - Astra: never touched or waited for.
   - Coordination: `thesis_shared_runtime\campaign_20261029` (own `opus_state.json`, locks, delivery area only).
   - ≤ 3 single-thread workers; one 48 h window; detached, checkpointed runner; no continuous LLM polling; early close.
7. **Delivery.**
   - Plain Turkish report: mechanism, change, early / stability / both classes / spend, the C1 decision.
   - Predictions, decisions, query IDs, cost, failures, independent recomputation.
   - Records updated.
   - Relation to the Research Hub recorded with source paths; missing central Astra records completed from the published read-only reports, transferred findings kept separate.
   - The list of changed Python files with a small local map.
   - Commit by explicit paths, push to the research branch, local = remote SHA.

**Campaign id:** `opus_c1_stability_20261029`. **Folder:** `outputs/research_campaign_20261029/opus_c1_stability/`.

**Graphify:**
- [graphify/GRAPHIFY_USAGE.md](graphify/GRAPHIFY_USAGE.md)
- [graphify/C1_CODE_MAP.md](graphify/C1_CODE_MAP.md)

## Outcome (2026-10-29T02:13:11Z, closed early)

- **Decision:** KEEP_C1_UNCHANGED (registered mapping, branch 3). C1 + margin is unchanged; the one carried candidate AVG4 is adopted for no use.
- **Mechanism:** balanced near-boundary flips; all 5 registered predictions hold on fresh data. About 81 % of the late shortfall below 0.95 is a level deficit.
- **Fresh test:** AVG4 - C1 dS95 -0.000001 [-0.00010, +0.00010] (NOT_SHOWN); early identical; sustained(0.95) +0.070 [+0.037]; 0.95 spend -0.64 [-1.06] fails the -1.0 harm limit.
- **Reports:** [FINAL_REPORT_C1S.md](FINAL_REPORT_C1S.md) (Turkish), [DECISION_C1S.md](DECISION_C1S.md), [evaluation/RESULTS_C1S.md](evaluation/RESULTS_C1S.md), [COST_BREAKDOWN.json](COST_BREAKDOWN.json).
