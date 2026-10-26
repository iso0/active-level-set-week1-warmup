# EA stage 1, amendment 2: one headroom diagnostic before any candidate

Dated 2026-10-26, about 14:55 UTC. Registered after the amendment-1 results and before this diagnostic is computed.

## Amendment-1 results

STD repeats 83–122, 200 learners, BA-AULC against R0_L (HA_LEAN):

| diagnostic | early B8–B24 | late B28–B60 | other |
|---|---|---|---|
| D2 hyperparameter oracle | +0.0053 [+0.0040] | +0.0021 | +0.0013 against R0_T early |
| D3 linear-in-z_h emulator | +0.0047 | −0.0097 | |
| D4 corner-capped margin, against the recorded margin path | +0.0021 [+0.0013] | | restricted-mean saving 0.93 +0.61 [+0.04], 0.95 +0.51 [−0.33]; kept(0.95) −0.040 |

Margin pays 24.8 corner runs of 60.

## Reading

- The early emulator loss is mostly an information limit of the b paid depths. Ideal hyperparameters recover only +0.005 of the +0.040 gap to the true-depth oracle; unlimited data recovers +0.022.
- The selector's corner spending has small value loss: +0.002 early BA, about +0.6 simulations at 0.93, nothing at 0.95.

## D2T: trend + ideal hyperparameters (evaluator-only)

The HA_TREND depth GP with its hyperparameters FIXED at the full-pool ML-II values of the same trend model, conditioned on the b paid depths, under HA_LEAN stacking. It gives the combined headroom of "physics trend + perfect small-n hyperparameter inference".

**Decision rule (fixed now):**

| D2T − R0_T, early BA-AULC | conclusion |
|---|---|
| < +0.002 | No emulator-inference candidate is justified. The development stage reports that the deployable slack is about +0.005 early, and that the remaining gap needs information not available in the paid depths. |
| ≥ +0.002 | One candidate that approximates D2T's mechanism with paid data only (e.g. integration over the trend GP's hyperparameters under a fixed weakly informative prior) may be registered, with its mechanism controls. |
