# External validation of C1 + margin: a short plan for Ioan

**Status: plan only.** No simulation has been started and no message has been sent. This plan reviews and extends the existing RC24 proposal (`outputs/research_campaign_20261021/opus_rc24/PHYSICAL_DATA_PROPOSAL.md`, blocks R1–R3). It reuses the repository's label-blind intake and sealed-oracle gate (`docs/external_validation/NEW_DATA_ARRIVAL_RUNBOOK.md`).

## 1. What the pool shows, and what it cannot

In the 541-run pool, on 80 fresh repeats, C1 + margin compared with the current reference HA_LEAN + margin:
- learns earlier: BA-AULC B8–B24 +0.0053; BA at 8 runs 0.918 vs 0.899;
- reaches BA 0.93 / 0.95 with about 1 / 2 fewer simulations;
- loses nothing late, within 0.003 BA.

These findings also hold for random and clustered startups and for half or double the prior width.

All of these are re-splits of the pool on which the method was developed. Three questions need new runs:

| | question | why the pool cannot answer it |
|---|---|---|
| Q1 | Does the early gain hold on runs that played no part in any design choice? | Every pool split reuses the same 541 runs. |
| Q2 | Is C1 safe outside the sampled input region? | Geometric blocks of the pool showed a per-region warning for C1 (−0.049 BA-AULC); no external region exists in the pool. |
| Q3 | Is the fast-scan corner label deterministic? | If the label there flips between solver seeds, BA 0.95 near the corner is a ceiling question, not a learner question. |

## 2. Runs requested

Same solver and version as the NEW batch; record length TE = 2.1 ms.

| block | design | runs | answers |
|---|---|---|---|
| **V1** new pool | label-free maximin Latin hypercube over the pooled ranges P 52–450 W, VX 0.20–1.0 m/s, LS 40–90 µm, ST 300–500 K; same size as the NEW batch | 136 | Q1 |
| **R3** external anchor (RC24) | 4 × 4 grid in (P, VX) at an LS 10 % outside the pooled range; ST at the median | 16 | Q2 |
| **R1** replicates (RC24) | 8 existing corner runs × 3 solver seeds | 24 | Q3 |
| R2 forming-phase probe (RC24, optional) | 6 corner inputs × 2 laser ramp-up settings | 12 | mechanism only |

Total: 176 runs, or 188 with R2. If the budget is tight, V1 + R3 (152 runs) answers the two learner questions.

## 3. When the models are frozen

Everything below is committed before any run is requested:
- **Learners.** C1 + margin and HA_LEAN + margin exactly as frozen in commit 63e9ae1d. Only their usual paid-only fitting is applied to new data: no retuning, no new variant.
- **Design points.** The V1 / R3 input lists, generated label-free from a fixed seed, with their SHA-256 hashes.
- **R3 predictions.** Full-pool-trained probabilities of C1, HA_LEAN, HA_TREND and the h-only model at the 16 R3 inputs, written and committed before the runs.
- **Analysis addendum.** It fixes the arms, folds and re-splits, endpoints and the decision rules of §5, and its hash is recorded.

## 4. How the new results are opened

The repository runbook is followed:
1. The delivery is quarantined as a label-free manifest plus a sealed label oracle.
2. Label-blind intake, and a check that the batch is new.
3. Owner decisions on folds and re-splits, made without labels.
4. Freeze commit.
5. The oracle is opened only through the locked `execute` command, which verifies the freeze commit.

The analysis runs once. There is no re-seeding, no extension and no replacement after labels are seen. A missing or ineligible batch means "validation not run", not "method failed".

## 5. Which comparison tests which claim

| claim | comparison | decision rule (fixed in advance) |
|---|---|---|
| early gain (Q1) | V1: C1 + margin vs HA_LEAN + margin, both learning on the new pool from the same 8-point label-free startup; 5 folds × 20 re-splits; ΔBA-AULC B8–B24 | **confirmed** if the mean is > 0 and the 95 % repeat-block interval is above 0 |
| no late harm (Q1) | V1: ΔBA-AULC B28–B60 | non-inferior if the interval is above −0.01 |
| fewer simulations to 0.93 / 0.95 | V1: restricted-mean saving | **descriptive only**: with about 27 test runs per fold, BA is too coarse for a 0.95 decision |
| extrapolation safety (Q2) | R3: frozen full-pool C1 vs HA_LEAN on the 16 out-of-range runs | harm flag if C1 misclassifies at least 3 more of the 16 than HA_LEAN; exact binomial intervals |
| corner determinism (Q3) | R1: label flip rate between solver seeds, per input | flip rate ≥ 0.2 means the corner is aleatoric, and the 0.95 target near it is capped by the data |

**Limits.**
- Re-splitting one batch measures split noise, not batch-to-batch variation, so a V1 confirmation means "on this batch".
- V1 is mainly a check against gross failure. It is not known in advance whether an effect of the pool size (+0.005 BA-AULC) is detectable on a single 136-run batch, so a non-confirmation would be inconclusive, not a refutation. The pool replication remains the effect-size estimate.
