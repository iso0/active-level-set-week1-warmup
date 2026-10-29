# FR task: one simple C1 / HA_LEAN trust combination (final research task)

Owner request of 2026-10-29. Opus started at **2026-10-29T13:31:37Z**. The hard limit is **6 h: 2026-10-29T19:31:37Z**. Quota waits, session changes and restarts do not reset it.

**Question.** "İki modelin ölçülmüş tamamlayıcılığını, yalnız açılmış simülasyonlardan öğrenilen sade bir güven kuralıyla kullanabilir miyiz?"
- C1 + margin is strong early.
- HA_LEAN + margin is better on some hard runs and some geometric blocks.
- A combination only helps where the two models disagree. It must be learned from paid runs and public inputs only.

## Fixed setting

| item | value |
|---|---|
| main method | C1 + margin (HA_TREND + MAP, `src/ea_cand.py` SYSTEMS["C1"]); code and earlier results frozen |
| reference | HA_LEAN + margin |
| baselines | science C1/C1C 3caf7c4e; start of this branch c8437907 (C1S closed) |
| data | the one 541-run pool; no OLD/NEW routing; no free archive; every opened run counts, the startup included |
| unchanged | labels, exclusions, decision threshold 0.5, error weights |
| not used | unopened physical outputs; hard-group or short-Keyhole membership, campaign id or test labels inside a learner; simulator, paid service, cloud, C4 |
| compute | at most 3 heavy single-thread workers (BLAS/OpenMP = 1); Astra's 3 slots and the system's 2 are not used |
| coordination | only `thesis_shared_runtime\campaign_20261029\opus_state.json` (Astra's file is read only) |
| outputs | `outputs/research_campaign_20261029/opus_final_robustness/` |
| branch | `final-robustness-20261029`; push to GitHub; no main merge, no force push |

## Not repeated (already tested)

- Residual GP on raw inputs (RC21/RC21B).
- A global C1 / HA_TREND mixture or the EL-2 evidence mixture (E: global Laplace-evidence weights between two ML-II emulators).
- AVG4 or hysteresis (C1S).
- BA_RISK, JEER, coverage rules.

## Order of work

1. Gain-area diagnosis on DEV records at identical paid prefixes. The rule to go on is written down before any number is computed (`GAIN_AREA_PROTOCOL.md`). If the gate fails, the task closes.
2. One candidate at most, with a fixed-weight control, developed on DEV paths: model effect first, then the candidate's own margin path.
3. Freeze (commit before any fresh result). Fresh IDs come from an inventory. Then the fresh test, evaluation, independent recomputation, reports and records.
