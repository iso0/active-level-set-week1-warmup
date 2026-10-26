# EA stage 2: DEV evaluation of the candidate

Dated 2026-10-26. DEV evidence.

**Registration:** `PROTOCOL_EA_CANDIDATES.md` (0020b07e), before this evaluation.

**Job:** `ea-cand-dev`, 272 units, 0 failed, 15:00–15:50 UTC.

**Data:**
- the recorded HA_LEAN paths of STD repeats 123–162 (40 clusters, 200 learners; disjoint from the diagnosis repeats);
- K5 startups 33–40 and K4 startups 17–24.

All systems predict on the same paths and the same paid data.

**Checks:** with the prior off and one start, the candidate code reproduces the recorded HA_TREND (D) and HA_LEAN (A) bit-exactly.

## STD, individual learners (pooled within 0.001)

| system | BA-AULC B8–B24 | B8–B60 | late B28–B60 | log loss | Brier | 0.93 attained / RMS | 0.95 attained / RMS / kept / sustained | CPU/step |
|---|---|---|---|---|---|---|---|---|
| A HA_LEAN | 0.9343 | 0.9482 | 0.9554 | 0.1436 | 0.0397 | 190 / 19.12 | 159 / 30.04 / 139 / 31 | 0.14 s |
| D HA_TREND | 0.9386 | 0.9482 | 0.9532 | 0.1497 | 0.0407 | 195 / 17.09 | 157 / 29.35 / 131 / 23 | 0.28 s |
| E evidence mixture | 0.9371 | 0.9487 | 0.9547 | 0.1435 | 0.0394 | 192 / 18.03 | 160 / 29.59 / 129 / 25 | 0.28 s |
| **C1** HA_TREND + MAP under a weak prior | **0.9396** | **0.9490** | 0.9539 | **0.1429** | **0.0390** | 194 / 17.49 | 156 / 29.35 / 128 / 29 | 0.17 s |
| C1a constant-mean + the same prior | 0.8961 | 0.9363 | 0.9559 | 0.1629 | 0.0467 | 194 / 19.61 | 161 / 30.38 / 130 / 41 | 0.16 s |
| C1b HA_TREND, 2 starts, no prior | 0.9385 | 0.9481 | 0.9531 | 0.1500 | 0.0408 | 194 / 17.51 | 159 / 29.23 / 132 / 25 | 0.27 s |

"Sustained" means attained, and BA ≥ τ at every budget from the confirmation to 60.

## Paired contrasts

Cluster means over 40 repeats, with one-sided 95 % bounds.

| X − ref | early | late | RMS saving 0.93 | RMS saving 0.95 | Δkept 0.95 | Δsustained 0.95 | Δlog loss |
|---|---|---|---|---|---|---|---|
| C1 − A | +0.0053 [+0.0041, +0.0066], 37/40 | −0.0015 [−0.0022, −0.0008] | +1.64 [+0.80, +2.47] | +0.68 [−0.58, +1.95] | −0.055 [−0.095, −0.015] | −0.010 [−0.055, +0.035] | −0.0007 |
| C1 − D | +0.0010 [+0.0004, +0.0017] | +0.0007 [+0.0002] | −0.40 | −0.01 | −0.015 | +0.030 | −0.0068, 39/40 lower |
| C1 − E | +0.0025 [+0.0017] | −0.0009 | +0.54 | +0.24 | −0.005 | +0.020 | −0.0006 |
| C1 − C1b (prior, at equal starts) | +0.0012 [+0.0005] | +0.0008 [+0.0002] | +0.02 | −0.13 | −0.020 | +0.020 | −0.0070 |
| D − A | +0.0043 | −0.0022 | +2.04 | +0.69 | −0.040 | −0.040 | +0.0061 |
| E − A | +0.0028 | −0.0006 | +1.09 | +0.45 | −0.050 | −0.030 | −0.0001 |

**C1 − A by budget:**

| b | 8 | 12 | 16 | 24 | 40 | 60 |
|---|---|---|---|---|---|---|
| C1 − A | +0.022 | +0.006 | +0.003 | +0.001 | −0.001 | −0.002 |
| D − A | +0.015 | +0.005 | +0.002 | 0.000 | −0.002 | −0.002 |

**Blocks** (per region, against A):

| | k = 5 | k = 4 |
|---|---|---|
| C1 | −0.043 (warning level, as D −0.039) | +0.036 |
| E | −0.006 | |

## Registered carry rule (§5)

| condition | C1 | C1a |
|---|---|---|
| early against A, LCB > 0 | ✓ | ✗ (−0.038) |
| early against D | ✓ (≥ −0.001) | ✗ |
| late against A ≥ 0 | **✗ (−0.0015)** | |

C1 also beats C1b (+0.0012), so the prior, not the extra start, carries its gain.

**Result: NOT CARRIED.** Under the registered rule, no new thesis learner goes to the forward validation. This result stands.

## Reading (DEV)

**What C1 fixes:**
- It is the best measured early-learning system: early +0.0053 against A, +0.0010 against D, +0.0025 against E.
- It removes the trend model's probability-quality penalty: log loss equals A's, while D pays +0.006.
- It is cheap: 1.2 × A's CPU, because one model is fitted. D and E each need two.

**What C1 does not fix:**
- The late window (−0.0015 against A).
- Keeping BA 0.95 at B60 (−0.055). On the stricter "sustained" measure, C1 is close to A (−0.010) and better than D (+0.030).

**Interpretation, a hypothesis:**
- The D2T oracle's late advantage needs hyperparameters that are representative of the whole pool. A generic weak prior does not supply them.
- ML-II / MAP fitted on margin-selected paid runs, which concentrate near the boundary and in the corner, reflects that region's local roughness.

## Recorded direction change (registered before any fresh run)

Separate from the carry rule, see `PROTOCOL_EA_VALIDATION.md`.
- The owner's instruction asks for separate verdicts for early success, 0.93 savings and 0.95 reliability, so that a failure in one does not erase a measured gain in another.
- The carry rule's late-window condition was my own stricter addition and does not follow that instruction.
- **Deviation:** C1 is tested once on fresh IDs, with three separate pre-registered verdicts, for the narrower use-case claim (early learning / BA 0.93).
- It is NOT a replacement thesis learner. The late and 0.95 verdicts are expected to fail and are reported either way.
