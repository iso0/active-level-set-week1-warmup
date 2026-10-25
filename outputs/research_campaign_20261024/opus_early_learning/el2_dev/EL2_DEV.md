# EL stage 2, DEV evaluation of mechanism E

Dated 2026-10-25. DEV evidence; it decides only whether E enters the confirmation.

- **Registration:** `PROTOCOL_EL2_MECHANISM.md`, pushed in dcdb8234 before this evaluation.
- **Code and output:** `src/el_mix.py`; job `el-mix-dev`, 544 units, 0 failed, 21:47–22:37 UTC, 3 single-thread workers.
- **Numbers and tables:** `EL2_DEV.json`, `*.csv`.
- **Checks:** p_L equals the recorded A and p_T the recorded D exactly at every compared budget (max |Δp| = 0.0).

**Systems.** All three share the same HA_LEAN-selected path:
- A: HA_LEAN predicts;
- D: HA_TREND predicts;
- E: the evidence-weighted mixture predicts.

## 1. STD, individual learners

64 repeat clusters (51–58 and 67–122), 320 learners.

| system | BA-AULC B8–B24 (pooled) | B8–B60 (pooled) | BA b8 / 12 / 16 / 24 / 40 / 60 | log loss | Brier | 0.93 attained / RMS / kept | 0.95 attained / RMS / kept | 0.95 maintenance |
|---|---|---|---|---|---|---|---|---|
| A | 0.9332 (0.9331) | 0.9471 (0.9470) | 0.897 / 0.929 / 0.938 / 0.946 / 0.954 / 0.957 | 0.1459 | 0.0402 | 315 / 17.78 / 295 | 268 / 29.11 / 213 | 0.768 |
| D | 0.9377 (0.9377) | 0.9474 (0.9473) | 0.913 / 0.937 / 0.941 / 0.945 / 0.952 / 0.956 | 0.1513 | 0.0409 | 318 / 17.00 / 288 | 261 / 29.45 / 204 | 0.741 |
| E | 0.9361 (0.9361) | 0.9478 (0.9476) | 0.905 / 0.935 / 0.940 / 0.946 / 0.954 / 0.957 | 0.1455 | 0.0399 | 318 / 17.09 / 293 | 271 / 28.54 / 214 | 0.749 |

Paired comparisons, one-sided 95 % bounds over 64 clusters:

| contrast | ΔBA-AULC B8–B24 | ΔBA-AULC B8–B60 | RMS saving 0.93 | RMS saving 0.95 | Δattain 0.95 | Δkept 0.95 | Δlog loss |
|---|---|---|---|---|---|---|---|
| D − A | +0.0045 [+0.0035, +0.0055], 52/64 | +0.0003 [−0.0001, +0.0008] | +0.78 [+0.11, +1.44] | −0.34 [−1.61, +0.93] | −0.022 [−0.053, +0.009] | −0.028 [−0.060, +0.003] | +0.0054 |
| E − A | +0.0029 [+0.0023, +0.0035], 54/64 | +0.0007 [+0.0005, +0.0009], 43/64 | +0.68 [+0.13, +1.24] | +0.57 [−0.43, +1.56] | +0.009 [−0.012, +0.031] | +0.003 [−0.014, +0.021] | −0.0004 [−0.0009, +0.0000] |
| E − D | −0.0016 [−0.0022, −0.0010] | +0.0003 [+0.0000, +0.0006] | −0.09 [−0.60, +0.41] | +0.91 [−0.03, +1.84] | | | −0.0058 |

**E − A by budget:**

| b | 8 | 12 | 16 | 24 | 40 | 60 |
|---|---|---|---|---|---|---|
| E − A | +0.008 | +0.006 | +0.002 | 0.000 | 0.000 | 0.000 |
| D − A | +0.016 | +0.007 | +0.003 | −0.001 | −0.002 | −0.001 |

E keeps about 60 % of D's early gain and loses nothing later.

**Weights.** The mean HA_TREND weight W_T is learned from the paid labels inside each learner:

| b | 8 | 12 | 16 | 24 | 32 | 40 | 60 |
|---|---|---|---|---|---|---|---|
| mean W_T | 0.52 | 0.53 | 0.54 | 0.51 | 0.45 | 0.38 | 0.30 |
| share of learners with W_T > 0.5 | 0.59 | 0.65 | 0.65 | 0.54 | 0.42 | 0.25 | 0.16 |

The evidence moves the weight from the trend emulator to the constant-mean one as depths accumulate, with no budget rule.

**CPU per step:**

| A | D | E |
|---|---|---|
| 0.143 s | 0.290 s | 0.290 s (2.0 × A) |

## 2. Robustness: reported, not in the rule

| per-region BA-AULC B8–B60 against A | k = 5 (32 startups) | k = 4 (16 startups) |
|---|---|---|
| D | −0.045 [LCB −0.054] | +0.032 [LCB +0.019] |
| E | −0.0075 [LCB −0.014] | +0.020 [LCB +0.014] |

- Pooled block BA-AULC B8–B60 against A: k = 5 E +0.006, D +0.011; k = 4 E +0.011, D +0.022.
- On the old five regions, kept(0.95) is A 32/128, D 8/128, E 27/128.

E is far less exposed than D to the extrapolation loss on the old regions, and keeps part of D's gain on the k = 4 partition.

## 3. Registered entry rule (DEV STD, point estimates)

| condition | value | holds? |
|---|---|---|
| early gain | +0.0029 | ✓ |
| RMS savings at 0.93 / 0.95 | +0.68 / +0.57 | both > 0 ✓ |
| attainment(0.95), E against A | 0.847 vs 0.838 | ✓ |
| kept(0.95), E against A | 0.669 vs 0.666 | ✓ |
| better than D at 0.95 | +0.57 vs −0.34 | ✓ |

→ **E enters the confirmation** on fresh IDs (`PROTOCOL_EL2_FINAL.md`).
