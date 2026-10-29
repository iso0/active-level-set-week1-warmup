# Astra `astra_finite_pool_assurance_20261029`: short scoped record (SOURCE-TRANSFERRED)

**Status: SOURCE-TRANSFERRED.**
- Every statement below is condensed from Astra's own delivered files, read on 2026-10-29 (Opus, FR task).
- Opus did not recompute anything here and none of it is an Opus finding.
- No Astra file was copied into the repository and no Astra script was run or imported.
- Astra's live folder, environment, Git, scheduler and processes were not touched; its `work/` sibling was not opened.
- Astra's own state file says `CLOSED`, 2026-10-29T08:40:19Z, with no jobs.

## Sources read

Delivered package root: `C:\Users\ozgur\Documents\Codex\2026-10-10\files-pasted-by-the-user-you\outputs\astra_finite_pool_assurance_20261029\`

| file | SHA-256 |
|---|---|
| `FINAL_REPORT.md` | 8178f51b7ad895bb9986983c66af876a96973f3ddef0546de19a580c0f0ff1be |
| `OPUS_INTEGRATION_HANDOFF.md` | aa89f37eae4ee5b674e8dba567152d9dec35b70efe21af587cccce6583fca8c4 |
| `SONUC_TR.md` | fd8220f12dd4d26ff7cee1b3e8dea356c245ca1b82639e368a21d4c45fec9d21 |
| `RESULTS_INDEX.md` | 65e6cf8b41cda13cdf83905d6120e3762feceeb1d81e2fceef4b14a417e86760 |
| `CLOSURE_RECEIPT.json` | 31f18c423bbe9fdf9a26068a107e8792ddfae7e9b4468d63d9c4927d1c6aa7b9 |

`CAMPAIGN.json` gives the source commit 4fc9b5d50308f29013b7844ec39090b257aa713d, the baseline 3caf7c4e49499f30e6c9b642a226454068f08969 and the window 2026-10-29T00:10:49Z to 2026-10-31T00:10:49Z. The receipt reports 35 completed units, 0 failed, 0 deadline-censored, and that the campaign closed early.

## What it studied (scope)

**Question.** How well can a fixed C1 (and HA_LEAN) be *audited* with few extra labels? Finite-population sequential confidence bounds for BA and recalls are used: a hypergeometric supermartingale per stratum, with Bonferroni over at most 4 strata.

**Setting**
- **Models:** cached C1 and HA_LEAN predictions on EA DEV held-out folds, repeats 123/124 and folds 1/2, at training budgets 8, 12 and 24, on the cached HA_LEAN paths.
- **Panels:** 16 frozen panels, with 64 randomised audit repetitions per policy (random or active).
- **Independence:** these are overlapping fixtures of the same 541 pool, not independent worlds.
- **Not done:** no GP refit, no new physical outcome, no independent TEST, no model update.

**Not a learning-programme result.** It does not estimate a BA-AULC or acquisition gain.

## Findings and their status (Astra's wording, condensed)

**Original practical assurance gate: FAILED.**
- Measured at 32 extra labels (active policy) against its fixed gates:

  | quantity | active | gate |
  |---|---|---|
  | decisions resolved | 5.58 % | ≥ 50 % |
  | BA mean absolute error | 0.431 | ≤ 0.03 |
  | decision burden | 3.40 % lower | ≥ 20 % lower |

- References, completeness and the empirical validity screen passed.
- No truly-above-target cell was certified at 32 labels. Successful assurance was near-census, with about 80–95 extra labels to first resolution out of 108–109 targets.

**One post-hoc DEV repair of the point estimator only: passed its own frozen gate.**
- Repaired descriptive BA error at 32 labels: random 0.031, active 0.050.
- These repaired ratios are biased descriptive estimates, not certificates.
- No bound, query rule or gate was changed.

**A descriptive lead, not a result.** In a cached summary, the sign of a paired C1-versus-other difference was resolved at 32 labels in 72 % (active) against 17 % (random).
- The panels are dependent and this is exposed DEV.
- Astra proposes it only as a separately registered future study.

**Explicit limits**
- No automatic model update or stopping rule.
- No promise of cheap assurance: a rare-positive counterexample bounds the expected cost from below.
- Not a new estimator.
- Closest established tools: active testing, without-replacement confidence sequences, sequential stratified inference.

## Relation to the FR task

The two studies are independent:
- **Astra:** fixed-model audit. "How sure can we be about a given C1's BA?"
- **FR:** learning. "Can a paid-only trust rule between C1 and HA_LEAN reduce C1's loss on geometric blocks?"

FR uses none of Astra's code, labels or outputs, and Astra's result changes no FR rule. The active-testing line was not reopened, as instructed.
