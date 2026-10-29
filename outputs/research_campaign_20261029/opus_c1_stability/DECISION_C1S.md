# C1S use decision

The decision follows the mapping that was registered before any fresh result (`PROTOCOL_C1S.md` §4; registration commit 9cad00ad, pushed). Its inputs:
- the verdicts on the primary set STD 323–362 (40 repeat clusters, 200 learners, own paths);
- the startup rule (RAND8 363–372, LOCAL8 373–382; descriptive, 10 clusters each).

Full tables: `evaluation/RESULTS_C1S.md`. Data: `evaluation/C1S_DECISION.json`. Diagnosis: `diag/DIAGNOSIS_C1S.md`.

## 1. Registered outcomes

Each row is AVG4 − C1 (both on C1's own path, so the opened runs are identical), 40 clusters, one-sided 95 % bounds.

| item | result | status |
|---|---|---|
| **STABILITY (primary)**: ΔS95, S95 = mean over b = 24..60 of max(0, 0.95 − BA(b)) | −0.000001 [−0.00010, +0.00010], 21/40 clusters positive; bootstrap 5 % / 95 %: −0.00009 / +0.00009 | **NOT_SHOWN** (DEV expectation −0.0001; practical threshold −0.0005) |
| EARLY: ΔBA-AULC B8–B24 | exactly 0 (max \|Δp\| over b ≤ 24 = 0) | EARLY_NONINFERIOR (identical by construction, checked) |
| FEWER SIMULATIONS: restricted-mean saving 0.90 / 0.93 / 0.95 | −0.01 [−0.02] / −0.17 [−0.33] / −0.64 [−1.06, −0.21] | NOT_WORSE / NOT_WORSE / **NOT_SHOWN** |
| SUSTAINMENT: Δsustained 0.93 / 0.95 (all learners) | +0.065 [+0.032] / +0.070 [+0.037]; at 0.95, 45/200 vs 31/200 | SUSTAIN_GAIN_SHOWN / SUSTAIN_GAIN_SHOWN |
| harm: Keyhole recall B24–B60 | +0.0001 [−0.0001] | met (limit −0.005) |
| harm: conduction recall B24–B60 | −0.0001 [−0.0003] | met (limit −0.005) |
| harm: late BA-AULC B24–B60 | −0.0000 [−0.0001] | met (limit −0.003) |
| harm: spend 0.90 / 0.93 / 0.95 | LCB −0.02 / −0.33 / **−1.06** | **0.95 not met** (limit −1.0) |
| harm: attainment(0.95) / kept(0.95) | +0.000 [−0.017] / −0.015 [−0.029] | met (limit −0.05) |
| startup rule | RAND8 ΔS95 +0.00003 (mean > 0); LOCAL8 −0.00002; harm limits fail in both (0.95 spend; in RAND8 also attainment and kept) | would restrict any recommendation to the standard maximin startup; moot here |

## 2. Decision (registered mapping applied)

1. Branch 1 (STABILITY + PRACTICAL and all harm limits met): not met. Stability is not shown.
2. Branch 2 (sustained(0.95) shown and all harm limits met): the sustainment gain is shown, but the 0.95 spend limit fails. Not met.
3. **Branch 3: KEEP_C1_UNCHANGED.** AVG4 is not adopted for any use, not even the hold-the-target use.

Consequences:
- **C1 + margin stays unchanged.** It remains the recommended in-pool learner for the early and stop-at-target uses. The C1C decision is closed and is not changed.
- **HA_LEAN + margin stays the frozen reference arm** and the extrapolation-safe choice.
- **This branch is complete.** No further seeds, variants or thresholds are run.

## 3. Mechanism (registered descriptive predictions, checked on fresh STD 323–362)

| prediction written before the run (from DEV) | fresh value | holds |
|---|---|---|
| ≥ 90 % of C1's regression steps contain ≤ 2 harmful flips | 96.8 % | yes |
| ≥ 30 % of C1's flips lie in the corner | 40.4 % | yes |
| harmful / helpful flips per step between 0.8 and 1.0 | 0.235 / 0.263 = 0.89 | yes |
| level part ≥ 70 % of C1's S95 | 0.00563 / 0.00698 = 81 % | yes |
| AVG4 roughly halves C1's flips per step | 0.256 vs 0.497 (0.52) | yes |

RAND8 and LOCAL8 agree on all five predictions (descriptive).

The diagnosis therefore replicates prospectively:
- **The regressions are balanced near-boundary flips.** Smoothing removes harmful and helpful flips alike, so the BA level does not move.
- **Most of the shortfall below 0.95 is a persistent level deficit of hard folds.** No decision-layer stabiliser can address it.

## 4. Caveats and descriptive results

These are reported beside the registered decision. They do not change it.

- **The sustainment gain is generic smoothing.**
  - EVERY4 ("update less often") gives the same gain: +0.075 [+0.039]; AVG4 − EVERY4 −0.005 [−0.033, +0.023].
  - AVG4 beats EVERY4 on S95 (−0.00026 [UCB −0.00011]) and on the 0.95 spend (+0.66 [+0.10]).
  - Neither improves on C1: EVERY4 − C1 ΔS95 +0.00026 [+0.00010], a shown loss.
- **Freezing at B24 loses.** FREEZE24 − C1: ΔS95 +0.0036 [+0.0024]; attainment(0.95) −0.195. Learning after b = 24 is real; the regressions are noise around a rising level.
- **AVG4's spend cost is a lag, not a loss of attainment.**
  - Attainment of 0.95 is equal: both 161, AVG4 only 2, C1 only 2, neither 35.
  - Among learners that attain under both, AVG4 confirms later: −0.55 [−0.91, −0.19] (conditional).
- **Kept(0.95) and above 0.95 at B60.** −0.015 [−0.029, −0.001] and −0.020 [−0.040, 0.000]. AVG4 smooths dips, but at B60 its average lags C1's latest probabilities.
- **Probability quality** (supplementary): log loss B24–B60 +0.0006 [+0.0004]; Brier +0.0001. Averaging blurs the probabilities slightly.
- **C1 − HA_LEAN on this third fresh set.** Descriptive; not a registered C1S decision; C1C stays closed.
  - Early: +0.0059 [+0.0041, +0.0077], 33/40 clusters positive. Replicated (EA +0.0056, C1C +0.0053).
  - 0.95 restricted-mean saving: +1.80 [+0.11]. Replicated (C1C +1.81).
  - Kept(0.95): −0.030 [−0.071]. **The C1C non-inferiority margin 0.05 is not met on this set** (C1C: +0.015 [−0.016]).
  - Sustained(0.95): −0.020 [−0.076, +0.036] (C1C −0.007). Lost after attainment: 29 vs 20 of 200.
  - Late B28–B60: −0.0013 [−0.0027, +0.0001], inside the 0.003 margin at the bound.
  - Hard group (evaluator-only): short-Keyhole NEW recall −0.033 [UCB −0.014], the same direction as EA (B60: 0.915 vs 0.955). NEW-conduction specificity is about 0.25 for both and remains unresolved.
- **Startup controls** have 10 clusters each and are descriptive. C1's early advantage over HA_LEAN holds there too: RAND8 +0.0086 [+0.0040]; LOCAL8 +0.0075 [+0.0024].

## 5. Claim boundaries

- **Pool-only.** Every ID is a new split or startup of the same 541 runs.
- **No novelty claimed.** Temporal smoothing of predictive probabilities is a known decision-layer device.
- **The supported contribution** is the measured mechanism of C1's late regressions, its prospective confirmation, and a registered negative test of the simplest stabiliser.
