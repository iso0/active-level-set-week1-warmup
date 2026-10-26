# EA validation of C1 for the early-learning use: protocol

Registered 2026-10-26, about 16:05 UTC, before any fresh run. Frozen with `freeze/EA_VALIDATION_MANIFEST.json`.

## 0. Status and deviation (disclosed)

The registered DEV carry rule (`PROTOCOL_EA_CANDIDATES.md` §5) did NOT carry C1, because its late window is −0.0015 against A (`cand_dev/CAND_DEV.md`). That result stands. C1 is NOT proposed as a replacement thesis learner.

This validation is a recorded direction change made under the freedom clause.
- The owner's instruction asks for separate verdicts for early success, 0.93 savings and 0.95 reliability, and says a failure in one must not erase a measured gain in another.
- The carry rule's late condition joined these verdicts, so it did not follow that instruction.
- C1 is therefore tested once on fresh IDs, with the three verdicts below fixed now.
- No threshold is chosen from the fresh data, and no data is selected.

## 1. Systems

All systems use margin on their own probability.

| | system | role |
|---|---|---|
| C1 + margin (own path) | HA_TREND with MAP hyperparameters under the fixed weak prior; `src/ea_cand.py` SYSTEMS["C1"] | PRIMARY |
| A + margin (own path) | HA_LEAN, the thesis learner | reference |
| HA_LEAN selects / C1 predicts | same path as A | secondary |
| D: HA_LEAN selects / HA_TREND predicts | | secondary |
| E: HA_LEAN selects / evidence mixture predicts | | secondary |
| HA_LEAN on C1's path | | decomposition only |

Every system is compared against A + margin.

## 2. Fresh IDs

Inventory: STD repeats 1–162, K5 startups 1–40 and K4 startups 1–24 were used before (RC19–RC24, EL, EA).

| condition | IDs | learners |
|---|---|---|
| STD | repeats 163–202 × 5 folds | 200 learners in 40 clusters |
| K5 | startups 41–48 | 40 |
| K4 | startups 25–32 | 32 |

All are new splits or startups of the same 541 runs: DEV evidence, not external physical validation.

## 3. Runs

Job `ea-fwd` (`src/ea_fwd.py`), two units per task:
- **L unit:** A's own path; on it, at every budget 8..60, C1, D and E.
- **X unit:** C1's own path; on it, at every budget, A.

The startup is the common 8-point label-free maximin start (counted). Each cross prediction uses only the first b paid runs of its path.

**Checks:**
- p_L on the L path must equal A's own predictions exactly.
- Both paths must share the startup.

## 4. Verdicts

Three verdicts, each separate. The primary pair is C1 + margin against A + margin on STD: individual learners, 40 clusters, one-sided 95 % bounds over clusters.

**V-EARLY** (fixed small budget):

| condition on ΔBA-AULC B8–B24 | status |
|---|---|
| LCB > 0 | EARLY GAIN SHOWN |
| mean ≥ +0.003 | PRACTICAL |
| otherwise | NOT SHOWN |

**V-0.93** (stop at BA 0.93), on the restricted-mean saving RMS_A − RMS_X (horizon 60; neither a cost nor a bound):

| condition | status |
|---|---|
| LCB > 0 | SAVING SHOWN |
| mean ≥ 1.0 simulation | PRACTICAL |
| LCB > −1.0 | NOT WORSE |
| otherwise | NOT SHOWN |

Also reported: attainment counts, cumulative attainment at b = 16 / 24 / 40 / 60, the both-attained conditional difference, and the 0.90 figures.

**V-0.95** (reach and keep BA 0.95):
- RELIABLE if Δattainment(0.95) LCB ≥ −0.05 and Δkept(0.95) LCB ≥ −0.05; otherwise NOT RELIABLE.
- Also reported: the 0.95 restricted-mean saving with the V-0.93 statuses, and Δsustained(0.95), i.e. attained and BA ≥ 0.95 at every budget from the confirmation to 60.

**Late window** (reported with every verdict): ΔBA-AULC B28–B60 is LOSS SHOWN if its UCB < 0, otherwise NO LOSS SHOWN.

**Harm limits** (each flagged if exceeded):
- ΔLL B8–B60 ≤ +0.030;
- ΔBrier ≤ +0.010;
- mean CPU per decision step ≤ 3 × A's.

**Robustness** (reported, not in any verdict):
- a geometry warning if the per-region BA-AULC B8–B60 LCB is below −0.02 against A, in K5 or K4;
- the short-Keyhole / NEW-conduction hard group;
- the pooled values beside the individual ones.

**Use statement:** each verdict speaks only for its own use. There is no combined winner.

## 5. Expectations from DEV (written before the run)

C1 − A on DEV:

| early | 0.93 | 0.95 RMS | kept(0.95) | late |
|---|---|---|---|---|
| +0.0053 [+0.0041] | +1.64 [+0.80] | +0.68 [−0.58] | −0.055 [−0.095] | −0.0015 |

V-EARLY and V-0.93 are expected to be shown, V-0.95 to be NOT RELIABLE, and the late window to be LOSS SHOWN. These expectations do not change any rule.
