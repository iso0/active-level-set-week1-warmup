# FR DEV result: the paid-only trust gate GATE does not capture the geometric gain area. The task closes

**Status: DEV.** The data are recorded EA paths of the same 541-run pool, read as a model effect at identical paid data. No new simulation was opened.
- **Rule:** `../PROTOCOL_FR_DEV.md`, registered in c4edc59a before any DEV gate result.
- **Numbers:** `DEV_GATE.json` (rule and contrasts), `DEV_TABLES.json` (strong alternative and targets), `dev_gates.csv.gz` (every gate refit).
- **Independent recomputation:** `../exports/EXPORTS_ACCEPTANCE.json` (PASS, max |Δ| = 4e-17).

## 1. Registered DEV rule

Contrasts are GATE − C1; clusters as in the protocol.

| rule | value | needed | result |
|---|---|---|---|
| C-GEO: geometric per-region BA-AULC B8–B60 (32 startup clusters) | **+0.0045 [−0.0016, +0.0106]**, 18/32 positive | mean ≥ +0.010 and LCB > 0 | **FAIL** |
| C-EARLY: STD BA-AULC B8–B24 (20 clusters) | +0.0002 [−0.0003, +0.0006] | LCB ≥ −0.003 | pass |
| C-LATE: STD BA-AULC B25–B60 | +0.0009 [+0.0005, +0.0013] | LCB ≥ −0.003 | pass |

**Decision (registered):** CLOSE: the paid-only gate does not capture the gain area.
- No fresh test is run.
- The fresh IDs stay unused: STD 383+, K5 49+, K4 33+.
- No new candidate, variant or size change follows.

## 2. Where GATE stands: identical paid data, BA-AULC B8–B60

| condition | C1 | HA_LEAN (A) | GATE | AVG (w = 0.5) | D_on_A (A's path only) |
|---|---|---|---|---|---|
| STD (20 repeats, both paths) | 0.9491 | 0.9474 | **0.9498** | 0.9494 | 0.9482 |
| K5 (16 startups, per region) | 0.6768 | 0.7204 | 0.6985 | 0.7104 | 0.6838 |
| K4 (16 startups, per region) | 0.6882 | 0.6546 | 0.6755 | 0.6746 | 0.6830 |
| geometric (K5 + K4) | 0.6825 | 0.6875 | 0.6870 | 0.6925 | 0.6834 |

**K5 and K4 separately (GATE − C1):**
- K5: +0.0217 [+0.0172, +0.0263], 16/16. GATE recovers half of A's +0.044 advantage.
- K4: −0.0127 [−0.0174, −0.0080], 2/16. **A loss on K4 is shown.**

**The control (GATE − AVG):**

| window | GATE − AVG |
|---|---|
| geometric | −0.0055 [−0.0086, −0.0023], worse than the fixed average |
| STD early | +0.0013 [+0.0005, +0.0020], better, only because w = 1 below b = 16 |
| STD late | −0.0000 |

**AVG − C1:**
- geometric +0.0100 [+0.0017, +0.0182];
- STD early **−0.0011** [−0.0020, −0.0002];
- K4 −0.0137.

The local rule is not better than a fixed half-half weight on the blocks. A fixed weight is the EL-type answer and was not a candidate here.

## 3. Mechanism: why a paid-only gate cannot see the K5 problem

| quantity (4,704 refits; none hit the data-insufficient rule) | STD | K5 | K4 |
|---|---|---|---|
| nested spatial out-of-fold log loss, C1 − A, on the paid runs | −0.069 | −0.073 | −0.052 |
| mean MAP intercept a / slope c | 0.39 / 0.18 | 0.46 / 0.22 | 0.34 / 0.13 |
| mean w at the test runs, B25–B60 | 0.61 | 0.66 | 0.60 |

**What the paid runs show**
- On the paid runs, C1 predicts held-out spatial groups better than HA_LEAN in every design.
- The fitted slope c is positive, so the gate trusts C1 more the farther a point is from the data.
- It therefore gives C1 slightly more weight on the K5 test regions (0.66) than on STD (0.61).

**Why this does not carry over to the blocks**
- In the block design the test region is withheld from fitting **and** from querying. A learner never sees it.
- Inside and between the four paid regions, C1's physics trend extrapolates well.
- Across the boundary of some K5 regions it does not. In K4 it does.
- The information that would tell a learner "use HA_LEAN here" lies only in runs it may not open.
- The gate's weight ends up near a fixed 0.6 / 0.4 mixture for b ≥ 16 in all designs. That mixture helps on K5 and hurts on K4.

This matches EA's diagnosis: the bottleneck is the depth at unqueried inputs.

**Contrast with the label-informed diagnostic META** (`../gain/GAIN_AREA.json`): +0.021 geometric (K5 +0.049, K4 −0.007).
- META fits other learners' test labels from the same 541 runs, which overlap any fresh test runs.
- So it can never become a method.
- The part of the oracle room that is predictable at all is predictable only with labels the learner does not have.

## 4. Other quantities (DEV, reported only)

**STD learners (GATE − C1, B8–B60)**

| quantity | value |
|---|---|
| log loss | −0.0011 [−0.0015, −0.0006] |
| Keyhole recall | +0.0014 [+0.0007] |
| conduction recall | −0.0000 |
| hard group: short-Keyhole NEW recall | 0.906 → 0.925 |
| hard group: NEW conduction specificity | 0.211 → 0.206 |

The hard-group change runs in the same direction as HA_LEAN: Keyhole up, conduction down. It is a trade-off, not a solution, and it was not tested on fresh data.

**Geometric:**
- log loss **+0.0149** (worse);
- conduction recall −0.0063 [−0.0087, −0.0038].

**Targets on the recorded paths** (STD, 200 learner-paths). This is a model effect on fixed paths, not an end-to-end cost. Spend counts the 8 startup simulations and the b + 4 confirmation.

| system | 0.90 attained / spend / kept / sustained | 0.93 attained / spend / kept / sustained | 0.95 attained / spend (median) / kept / lost / sustained |
|---|---|---|---|
| C1 | 200 / 12.88 / 198 / 150 | 195 / 15.92 / 182 / 75 | 171 / 21.78 (17) / 134 / 37 / 35 |
| GATE | 200 / 12.85 / 198 / 146 | 195 / 16.10 / 186 / 83 | 172 / 21.93 (18) / 138 / 34 / 33 |
| A | 199 / 13.10 / 199 / 118 | 195 / 16.33 / 188 / 49 | 169 / 23.95 (21) / 136 / 33 / 31 |
| AVG | 200 / 12.87 / 198 / 143 | 195 / 15.72 / 186 / 72 | 170 / 21.78 (17) / 138 / 32 / 29 |
| D_on_A (100 A-path learner-paths) | 99 / 12.97 / 99 / 72 | 99 / 16.26 / 90 / 32 | 84 / 21.87 (19) / 66 / 18 / 12 |

**GATE − C1:**
- restricted-mean saving 0.90 +0.04 [−0.05], 0.93 −0.17 [−0.51], 0.95 +0.07 [−1.01];
- Δkept(0.95) +0.020 [−0.010];
- Δattained(0.95) +0.005 [−0.027].

**Strong alternative D_on_A** (HA_TREND on A's path, A-path learner-paths, against C1 on the same path):
- STD early −0.0007 [−0.0015, +0.0000];
- geometric B8–B60 +0.0013 [−0.0017, +0.0043];
- K5 +0.0045, K4 −0.0020.

## 5. Checks

| check | result |
|---|---|
| reduction w ≡ 1 | identical to C1 + margin (path and every probability, max |Δp| = 0) |
| reduction w ≡ 0 | identical to HA_LEAN + margin |
| shadow test | flipping the labels and permuting the outputs of every never-opened run left the path, the probabilities and the gate parameters identical (`SMOKE.json`) |
| exports | `../exports/dev`: C1, A, GATE and D_on_A at every budget, plus the recorded paid ids |
| independent recomputation | C-GEO, C-EARLY, C-LATE, AVG − C1 and the gain-area G1, from the export files with own code: PASS |
