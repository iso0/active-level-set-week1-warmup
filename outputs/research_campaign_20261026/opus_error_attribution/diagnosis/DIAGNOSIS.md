# EA stage 1: where the current system's error comes from

Dated 2026-10-26. DEV evidence on one 541-run pool.

**Design and records:**
- Registered design: `PROTOCOL_EA_HYPOTHESES.md` (d4dc329d), amendments 1 (fb7e361f) and 2 (613c9c7b), each before its own computation.
- Numbers: `DIAGNOSIS.json`, `AMENDMENT1_DIAGNOSTICS.json`, `AMENDMENT2_D2T.json`, `DEPTH_STRUCTURE_DESIGN_DIAGNOSTIC.json`; tables in `*.csv(.gz)`.
- Oracle rungs are **evaluator-only diagnostics**: not methods, no query saving, no universal ceiling.

**Data:** the recorded HA_LEAN margin paths of STD repeats 83–122 (200 learners, 40 clusters), K5 startups 25–32, K4 startups 9–16.

**Budgets:**
- early = 8..24, every budget;
- late = 28..60, every 4.

**Common test rows:** every test run with a recorded depth (one pool run has none).

**Checks:**
- R0_L = recorded A and R0_T = recorded D, bit-exact in every unit.
- The generic cross-fit path reproduces HA_LEAN and HA_TREND bit-exactly.

## 1. The rung ladder (STD, individual learners; pooled values within 0.001)

| rung | what changes | early BA-AULC | late | BA at b = 8 / 12 / 16 / 24 / 40 / 60 |
|---|---|---|---|---|
| R0_L | current HA_LEAN | 0.9342 | 0.9554 | 0.897 / 0.933 / 0.938 / 0.947 / 0.955 / 0.958 |
| R0_T | HA_TREND | 0.9382 | 0.9537 | 0.912 / 0.938 / 0.941 / 0.946 / 0.953 / 0.957 |
| R1a_L | trained on in-sample emulator means | 0.9257 | 0.9533 | |
| R1b_L | trained on the measured paid depths | 0.9251 | 0.9535 | |
| R2_L | ORACLE: R0_L classifier, true test depth | 0.9475 | 0.9742 | |
| R2_T | ORACLE: R0_T classifier, true test depth | 0.9552 | 0.9725 | |
| R3u | ORACLE: unlimited-data emulator both sides | 0.9563 | 0.9612 | 0.942 / 0.955 / 0.958 / 0.961 / 0.962 / 0.961 |
| R3 | ORACLE: true depth both sides | 0.9741 | 0.9823 | 0.957 / 0.972 / 0.976 / 0.980 / 0.982 / 0.983 |
| R4 | ORACLE: R3 + three log-input directions ⟂ h | 0.9679 | 0.9807 | |
| R5 | ORACLE: R3 + flexible residual over (h, a) | 0.9739 | 0.9819 | |
| R6 / R6u | ORACLE: large n (≈433 pool runs), true / unlimited-emulator depth | 0.9815 / 0.9608 | | |

**Paired steps** (cluster means over 40 repeats; one-sided 95 % bounds; all 40/40 unless stated):

| step | early | late |
|---|---|---|
| test-time depth: R2_L − R0_L | +0.0133 [+0.0114] | +0.0188 |
| training feature given true test depth: R3 − R2_L | +0.0267 [+0.0243] | +0.0081 |
| attainable from inputs (unlimited data): R3u − R0_L | +0.0221 [+0.0204] | +0.0058 |
| not attainable from inputs with this emulator family: R3 − R3u | +0.0179 | +0.0211 |
| representation, + transverse inputs: R4 − R3 | −0.0063 | −0.0016 |
| flexible family over (h, a): R5 − R3 | −0.0003 | −0.0004 |
| deployable training on measured paid depths: R1b_L − R0_L | −0.0091 | −0.0018 |

**Error types, early:** missed Keyhole is the larger share (R0_L recall 0.922 vs conduction recall 0.946). With the true depth (R3) both reach 0.974.

## 2. Answers to the registered hypotheses

| | hypothesis | verdict | evidence |
|---|---|---|---|
| H-A | depth emulator | **SUPPORTED as the dominant stage** | see the two windows below |
| H-B | classifier with known depth | **REJECTED** in this family | R5 ≈ R3; R3 at b = 8 is 0.957 and at b = 12 is 0.972, so labels are not the limit once depth is known; R6 ≈ R3 at late budgets |
| H-C | compression of 4 inputs into (h, a) | **REJECTED** | R4 < R3 at both windows |
| H-D | combination / label–time window | a small residual part | see below |

**H-A, early window.** The true depth closes +0.040 BA. With b paid depths that information is not available:
- ideal hyperparameters recover only +0.005 (D2 hyperparameter oracle: flat GP +0.0053 [+0.0040]);
- the physics trend recovers +0.004 (R0_T);
- the linear-in-h emulator recovers +0.005 (D3);
- trend and ideal hyperparameters together recover +0.007 (D2T: +0.0071 against R0_L, +0.0031 [+0.0022] against R0_T);
- unlimited data would recover +0.022 (R3u).

So the early loss is mostly an **information limit**: one depth per simulation, and the depth at unqueried inputs is uncertain whatever the structure. A smaller part is an **estimation problem of the trend GP's hyperparameters**.

**H-A, late window.** The current system (0.955) is close to the input-only ceiling of this emulator family (R3u 0.961, R6u 0.961). The remaining gap to R3 (+0.021) is not attainable from the four inputs with this family even with all other runs.

**H-D residual.**
- The errors that no rung fixes come mainly from a small set of runs.
- Only 15 pool runs have an opposite-label nearest neighbour in (z_h, true a) that is closer than their nearest same-label neighbour. 87 % of them are in the fast-scan corner, 40 % are short-Keyhole, none is an early-ending record.
- 13 of these 15 cause 76 % of the late errors that even the true depth does not fix.
- This is not read as unlearnable, random or label error. The tested representations simply do not separate them.

## 3. The two mechanisms behind the measured slack

**(a) The trend GP's ML-II hyperparameters fail at small and medium n** (20 learners, full paid fit):

| b | 8 | 12 | 16 | 24 | 40 |
|---|---|---|---|---|---|
| share of fits with any hyperparameter at a bound | 1.00 | 1.00 | 0.95 | 0.75 | 0.45 |
| share with noise variance collapsed to the lower bound 1e-6 | 0.80 | 0.65 | 0.50 | 0.35 | 0.20 |

- Lengthscales often run to the upper bound; mean log ℓ_P is 3.4 at b = 8 against 0.07 at full pool.
- Multi-start optimisation changes the optimum in 20–50 % of fits, but the ML-II optimum itself overfits: it interpolates the paid depths.
- With the full-pool hyperparameters the trend model is better at EVERY budget, b = 24: 0.9515 vs 0.9459, b = 40: 0.9576 vs 0.9528. HA_TREND's known late loss is therefore an estimation artefact, not a property of the physics trend.

**(b) The selector.**
- Margin pays on average 24.8 of 60 runs in the 7 % fast-scan corner.
- Capping the corner at its proportional share of 4 runs (an evaluator-defined region, diagnostic only) gains:
  - +0.0021 [+0.0013] early BA;
  - +0.61 [+0.04] simulations to 0.93;
  - nothing reliable at 0.95 (kept −0.040).
- The selector is not the main bottleneck; its measured slack is small.

## 4. Controls

**Geometric blocks.** Individual = per region; BA is dominated by minorities of 1–17 runs.

| per-region BA-AULC | R0_L | R3 |
|---|---|---|
| k = 5, early / late | 0.68 / 0.76 | 0.87 / 0.89 |
| k = 4, early / late | 0.63 / 0.67 | 0.86 / 0.88 |

The emulator's extrapolation into an unseen region is the main loss there, too. Unlike in STD, training on the measured paid depths (R1b) helps in blocks: +0.10 early on k = 5.

**Hard group (RC24 definition).**

| | NEW conduction predicted Keyhole, early / late | short-Keyhole recall |
|---|---|---|
| R0_L | 83 % / 77 % | |
| R3 (true depth) | 62 % / 61 % | high under every rung (0.83–0.94) |

The false-Keyhole problem of the hard group is not solved by the true depth either.

## 5. Design decision

The registered rule (amendment 2) is met: D2T − R0_T early is +0.0031, at least +0.002.

The development target is the **small-n hyperparameter inference of the trend depth GP**:
- It is the only measured, deployable-in-principle slack that improves both windows: D2T is +0.007 early and +0.002 late against A, with no late loss.
- The rest of the early gap is an information limit. The late gap needs information outside the inputs.
- The selector stays margin: D4's slack is small and comes from an evaluator-defined region.

The candidate is registered in `PROTOCOL_EA_CANDIDATES.md` before it is evaluated.
