# Relation of this task (FR) to the published Thesis Research Hub

**Hub version read:** `main` 4fc9b5d50308f29013b7844ec39090b257aa713d. It is read only, through `git show origin/main:<path>` after a read-only fetch; main had not moved. No merge or edit of main was made.

## What was read

| file (Hub path) | used for |
|---|---|
| `docs/research/CLAIM_LEDGER.csv` | C1C-001 … C1C-004 (wording and status) |
| `research/astra/…` (the four earlier Astra campaigns) | not needed again; their central rows were completed in C1S (`../../opus_c1_stability/hub/ASTRA_CENTRAL_RECORD.md`) |

The Astra finite-pool assurance campaign of 2026-10-29 is **not** on the Hub (main 4fc9b5d predates it). Its record here is taken from Astra's delivered package; see `ASTRA_FINITE_POOL_ASSURANCE_RECORD.md`.

## Where FR attaches

**C1C-003** (Hub): "C1C preserves late performance within its registered margin and retains HA_LEAN as the safer reference for extrapolation or sustained-target use."
- FR asked whether a paid-only C1 / HA_LEAN trust rule could make C1 safe for that extrapolation use. On DEV: no. GATE − C1 on geometric blocks is +0.0045 [−0.0016]; K5 +0.022, K4 −0.013.
- FR adds a scope note to C1C-003, without changing it. On the same DEV block data:
  - HA_LEAN is safer on K5-type regions (+0.044);
  - it is worse on K4 (−0.034);
  - pooled over both designs no difference is shown (+0.005 [−0.008]).
  - "Safer for extrapolation" is therefore design-dependent.

**C1C-001 and C1C-004** are kept: C1 + margin is the in-pool recommendation, and all results are pool-only. The C1C frozen decision and code are unchanged.

**Distinct identifiers**
- "C1" here is the C1C learner: the HA_TREND depth GP with MAP under the fixed EA prior, plus margin.
- "GATE" and "AVG" are FR-only names.
- The earlier EL-2 evidence mixture is "E"; it was not rerun.

## Status of the branch

- Research branch `final-robustness-20261029`, starting at c8437907 (C1S results). Its ancestor 3caf7c4e is the science baseline.
- Pushed to GitHub, NOT merged into main.
- Any Hub update is a separate publication step for the owner.
