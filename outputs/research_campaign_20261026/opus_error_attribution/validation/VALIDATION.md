# EA validation: C1 + margin against HA_LEAN + margin on fresh IDs

Dated 2026-10-26. DEV evidence: new splits and startups of the same 541-run pool.

**Registration and freeze:** `PROTOCOL_EA_VALIDATION.md` and `freeze/EA_VALIDATION_MANIFEST.json`, commit 04fc468a, before any fresh run. The manifest check passed at evaluation time.

**Run:** job `ea-fwd`, 544 units, 0 failed, 15:56–17:14 UTC.

**Check:** on HA_LEAN's path, the recomputed p_L equals A's own predictions exactly.

**Data:**
- STD repeats 163–202: 40 clusters, 200 learners;
- K5 startups 41–48;
- K4 startups 25–32.

**Systems:**
- C1 + margin selects on its own probability.
- A + margin = HA_LEAN, the thesis learner.
- On A's path: C1, D (HA_TREND) and E (evidence mixture).
- A on C1's path, for the decomposition only.

## 1. Registered verdicts (primary: C1 + margin against A + margin, STD individual learners)

| verdict | value | status |
|---|---|---|
| V-EARLY: ΔBA-AULC B8–B24 | +0.0056 [+0.0038, +0.0073], 33/40 | **EARLY GAIN SHOWN, PRACTICAL** (≥ +0.003) |
| V-0.93: restricted-mean saving | +0.61 [−0.29, +1.52] | NOT WORSE |
| V-0.95: reliability (Δattainment, Δkept) | +0.040 [−0.004], +0.020 [−0.031] | **RELIABLE** |
| 0.95 restricted-mean saving | +2.00 [+0.21, +3.80] | **SAVING SHOWN, PRACTICAL** (≥ 1 simulation) |
| late window ΔBA-AULC B28–B60 | −0.0005 [−0.0017, +0.0007] | NO LOSS SHOWN |
| harm: ΔLL / ΔBrier / CPU | +0.0013 / −0.0004 / 1.19× | within all limits |
| geometry: K5 per-region BA-AULC B8–B60 | −0.049 [LCB −0.072] | **WARNING** (K4 +0.043) |

## 2. Individual learners (pooled values within 0.001)

| system | BA-AULC B8–B24 | B8–B60 | BA b8 / 12 / 16 / 24 / 40 / 60 | log loss | Brier | CPU/step |
|---|---|---|---|---|---|---|
| A + margin | 0.9344 | 0.9477 | 0.901 / 0.929 / 0.939 / 0.946 / 0.954 / 0.958 | 0.1446 | 0.0400 | 0.149 s |
| **C1 + margin** | **0.9400** | **0.9493** | 0.921 / 0.939 / 0.943 / 0.948 / 0.953 / 0.957 | 0.1459 | 0.0397 | 0.177 s |
| HA_LEAN selects / C1 predicts | 0.9401 | 0.9493 | 0.921 / 0.936 / 0.941 / 0.947 / 0.955 / 0.957 | 0.1436 | 0.0392 | 0.324 s |
| D: HA_LEAN selects / HA_TREND predicts | 0.9387 | 0.9482 | 0.919 / 0.935 / 0.942 / 0.945 / 0.954 / 0.956 | 0.1508 | 0.0410 | 0.298 s |
| E: HA_LEAN selects / mixture predicts | 0.9370 | 0.9483 | 0.909 / 0.934 / 0.941 / 0.946 / 0.955 / 0.957 | 0.1443 | 0.0398 | 0.298 s |

## 3. Targets, 200 learners

- Spend is the confirmed b + 4, counting the 8 startup simulations.
- RMS is the restricted mean at horizon 60, with a non-attainer counted as 61. It is not a cost and not a bound.
- "Kept" means BA(60) ≥ τ. "Sustained" means BA ≥ τ at every budget after the confirmation.

| system | 0.90 attained / RMS / median | 0.93 attained / RMS / median / kept / sustained | 0.95 attained / RMS / median / kept / sustained |
|---|---|---|---|
| A + margin | 199 / 13.43 / 12 | 193 / 18.33 / 13 / 189 / 62 | 161 / 30.41 / 22.5 / 129 / 30 |
| **C1 + margin** | 200 / 12.66 / 12 | 194 / 17.72 / 13 / 181 / 75 | **169 / 28.40 / 21 / 133 / 41** |
| HA_LEAN selects / C1 predicts | 200 / 13.06 / 12 | 195 / 17.43 / 13 / 182 / 79 | 166 / 27.94 / 19 / 133 / 35 |
| D | 199 / 13.19 / 12 | 196 / 17.45 / 13 / 181 / 69 | 161 / 28.83 / 21 / 128 / 24 |
| E | 199 / 13.42 / 12 | 194 / 17.80 / 13 / 185 / 70 | 163 / 28.97 / 21.5 / 129 / 28 |

**C1 + margin against A + margin, by target:**

| target | both | C1 only | A only | neither | conditional both-attained saving | cumulative attainment C1 / A at b = 16, 24, 40, 60 |
|---|---|---|---|---|---|---|
| 0.95 | 153 | 16 | 8 | 23 | +1.29 simulations | 0.42 / 0.38, 0.565 / 0.53, 0.755 / 0.725, 0.845 / 0.805 |
| 0.93 | 192 | 2 | 1 | 5 | | 0.725 / 0.715, 0.84 / 0.835, 0.95 / 0.935, 0.97 / 0.965 |
| 0.90 | | | | | | at b = 16: 0.965 / 0.92 |

The test-based target time is an evaluation of learning speed, not an online stopping rule.

## 4. Decomposition and the other systems (cluster means, one-sided 95 % bounds)

| contrast | early | late | RMS 0.93 | RMS 0.95 | Δsustained 0.95 | ΔLL |
|---|---|---|---|---|---|---|
| model on C1's path: C1 − (HA_LEAN on C1's path) | +0.0098 [+0.0073], 40/40 | 0.0000 | +0.63 [+0.11] | +1.61 [+0.50] | +0.075 [+0.034] | −0.0064 |
| path for HA_LEAN: (HA_LEAN on C1's path) − A | −0.0043 [−0.0074] | −0.0005 | −0.01 | +0.40 | −0.020 | +0.0077 |
| path for C1: C1 + margin − (HA_LEAN selects / C1 predicts) | −0.0002 | 0.0000 | −0.29 | −0.47 | +0.030 | +0.0024 |
| C1 + margin − D | +0.0013 [−0.0006] | +0.0009 | −0.27 | +0.42 | +0.085 [+0.024] | −0.0048 |
| C1 + margin − E | +0.0029 [+0.0013] | 0.0000 | +0.09 | +0.56 | +0.065 [+0.015] | +0.0016 |
| D − A | +0.0043 | **−0.0014 [−0.0021]** (loss shown) | +0.89 [+0.09] | +1.58 [+0.48] | −0.030 | +0.0061 |
| E − A | +0.0026 | −0.0005 [−0.0009] (loss shown) | +0.53 | +1.44 [+0.58] | −0.010 | −0.0003 |

**Reading:**
- C1's gain is a **model** effect. On the same paid data its predictions beat HA_LEAN's at every early budget (40/40).
- Its own margin path is about as good as HA_LEAN's path for C1, and worse for HA_LEAN's predictor.

## 5. Robustness (reported, not in the verdicts)

**Blocks:**

| | per-region BA-AULC B8–B60, C1 + margin | A | pooled, C1 | pooled, A |
|---|---|---|---|---|
| K5 | 0.681 | 0.730 | 0.939 | 0.924 |
| K4 | 0.704 | 0.661 | 0.943 | 0.917 |

On the old five regions, the trend models (C1, D) keep the per-region extrapolation weakness. E does not: −0.006.

**Short-Keyhole hard group** at B60:

| | C1 | A |
|---|---|---|
| hard-group BA | 0.609 | 0.622 |
| NEW-conduction specificity | 0.30 | 0.29 |
| short-Keyhole recall | 0.915 | 0.955 |

The hard group is not resolved by any system.

## 6. Stability across repeat sets (disclosed)

The same candidate on the DEV set (repeats 123–162, on HA_LEAN's path):

| | DEV set | this test |
|---|---|---|
| early | +0.0053 | +0.0056 |
| 0.93 | +1.64 | +0.91 (on A's path) |
| 0.95 RMS | +0.68 | +2.47 (on A's path) |
| Δkept(0.95) | **−0.055** [−0.095] | +0.020 |

- **The early gain is stable** across the two sets.
- **The 0.95 keeping result changed sign** between the sets. Comparable swings occurred for D in the EL study: 0.95 RMS −1.11 vs +0.69.
- So the registered 0.95 verdict holds for this test, but it is a single-test result. A larger pre-registered replication is needed before a general 0.95 claim.
