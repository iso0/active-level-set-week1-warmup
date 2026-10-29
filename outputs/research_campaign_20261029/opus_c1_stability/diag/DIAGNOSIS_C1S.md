# C1 stability: DEV diagnosis of the BA regressions

**Status: DEV.** All data were already evaluated in C1C:
- STD repeats 203–282 (80 clusters, 400 learners; C1C exports `main_s1` / `main_s2`);
- RAND8 283–302 and LOCAL8 303–322 (C1C startup exports);
- an instrumented replay of 50 learners: all folds of repeats 203, 211, …, 275, chosen by ID, not by outcome.

Test labels, the corner (VX > 0.85 m/s and P > 330 W) and the hard group (short-Keyhole NEW + NEW conduction) are evaluator-side descriptors only. Oracle quantities are marked.

**Code:**
- `src/c1s_diag.py` (anatomy);
- `src/c1s_trace.py` (instrumented replay, bit-exact: max |Δp| = 0 against the recorded C1 at every budget, all 50 query paths reproduced);
- `src/c1s_dev.py` (decision-layer screen).

**Numbers:** `ANATOMY_SUMMARY.json`, `TRACE_SUMMARY.json`, `../dev/DEV_SCREEN.json`, and the CSV tables here.

## 1. What a regression is

In B24–B60 (C1 + margin, own path):
- 16.4 % of the steps b → b+1 lower BA. The mean drop is −0.0119, about one Keyhole test point (1 / (2 · 39) = 0.0128).
- 96 % of the regression steps contain at most 2 harmful decision flips.
- **A few boundary points cause the drops.** Flipping points sit on the boundary: median |p − 0.5| = 0.023 before and after the flip, and 75 % lie within 0.05.
- Per step there are 0.51 flips: 0.24 harmful and 0.27 helpful. The boundary random-walks with a slight positive drift.

## 2. Where, and which class

**Location** (flip shares against the share of pool runs):

| region | share of pool runs | share of flips | over-representation |
|---|---|---|---|
| fast-scan corner | 7.2 % | 41 % | × 5.7 |
| hard group | 4.1 % | 29 % | × 7 |

- Oscillating test points (≥ 3 flips in B24–B60): 2.8 per learner, 43 % of them in the corner.
- 50 % of the late margin queries fall in the corner.

**Class.** Keyhole points are 55 % of the harmful flips and 68 % of the BA lost through flips, because a Keyhole test point weighs 1/(2·39) and a conduction point 1/(2·69). Mostly Keyhole is lost.

**Locality** (relation to the query of that step):
- 55 % of the flipped points are among the nearest quarter of test points to the newly opened run; 25 % would be expected by chance.
- 80 % of the flips move towards the new run's label.

The regressions are a local reaction to each new label in a label-interleaved region. EA had already shown this region is not separated by the tested representations (claim C67; 87 % of the interleaved runs are in the corner).

## 3. Model internals (instrumented replay, 50 learners, 1,800 steps, 850 flips)

| component | share of flips (of harmful flips) | evidence |
|---|---|---|
| classifier refit with the new label and the new out-of-fold features | 62 % (61 %) | the flip disappears when the budget-b classifier is applied to the b + 1 depth predictions |
| depth change alone | 38 % | the flip remains with the old classifier |
| hyperparameter + response-standardisation re-estimation | 28 % (29 %) | the flip disappears when every GP keeps its budget-b hyperparameters and standardisation and is only conditioned on the new data |
| classifier configuration-weight switch | 12 % (13 %) | flip disappears with the budget-b weights |

**Notes.**
- **Standardisation is negligible:** per step, median |Δμ| = 0.004 and |Δσ/σ| = 1 %.
- **Hyperparameters:**
  - The full-fit hyperparameters drift smoothly: median per-step max |Δ log θ| = 0.12 (90 % quantile 0.57).
  - Steps with a harmful flip have larger moves than other steps: Δθ 0.31 vs 0.22; weight total variation 0.083 vs 0.060; median depth change at test points 0.019 vs 0.013.
- **The two MAP starts are not two modes.** The two starts of C1 reach the same optimum (|ΔJ| < 1, |Δθ| ≤ 0.05, identical predictions in every checked fit: 5 learners, budgets 8–60).
  - The winning start index changes in 48 % of steps only through numerical ties.
  - Averaging the two modes was therefore dropped: there is no mechanism behind it.
- Re-estimation flips are balanced: 50 % of them are harmful.

## 4. Model effect against path effect (flips per step, B24–B60)

| system | flips / step | harmful | helpful | regression share | S95 mean |
|---|---|---|---|---|---|
| C1 + margin, own path | 0.514 | 0.244 | 0.270 | 0.164 | 0.00638 |
| C1 on HA_LEAN's path | 0.540 | 0.255 | 0.285 | 0.169 | 0.00674 |
| HA_LEAN + margin, own path | 0.493 | 0.231 | 0.262 | 0.155 | 0.00665 |
| HA_LEAN on C1's path | 0.571 | 0.269 | 0.303 | 0.172 | 0.00688 |
| HA_TREND (ML-II) on HA_LEAN's path | 0.658 | 0.313 | 0.345 | 0.184 | – |

- **Model effect on identical paid data:** C1 is about 10 % more reactive than HA_LEAN. The MAP correction already cut HA_TREND's churn by 18 %.
- **Path effect:** C1's own path is slightly calmer for C1 (−5 %) and harder for HA_LEAN (+16 %).

## 5. What the proposed stability metric measures

S95 = mean over b = 24..60 of max(0, 0.95 − BA(b)); C1 DEV mean 0.00638.

| part of S95 | value | share |
|---|---|---|
| persistent level, max(0, 0.95 − mean BA B24–B60) | 0.00523 | 82 % |
| fluctuation (Jensen gap) | 0.00115 | 18 % |

- 90 % of S95 comes from the 41 % of learners whose late mean BA is below 0.95.
- **The persistent level matches EA:**
  - late BA is near the input-only ceiling (0.961);
  - 13 interleaved runs cause 76 % of the late errors that even the true depth does not fix.
- **ORACLE:** keeping the best version so far would give S95 = 0.0011. This needs test labels, and the best-so-far value is inflated by lucky upward flips. It is not a deployable rule.

## 6. Decision-layer screen (DEV, path-identical to C1, so equal spend in simulations)

Each variant uses C1's own probabilities. Early budgets (b ≤ 24) are unchanged. STD, 80 clusters; contrasts are variant − C1.

| variant | ΔS95 | Δsustained 0.95 | 0.95 restricted-mean saving | Δattain 0.95 | late BA B24–B60 |
|---|---|---|---|---|---|
| AVG4: mean p of the last 4 budgets (b ≥ 25) | −0.0001 [UCB −0.0000] | +0.058 [+0.037] | −0.52 [LCB −0.91] | −0.018 | +0.0001 |
| HYST05: decision kept while \|p − 0.5\| < 0.05 | −0.0002 [UCB −0.0001] | +0.087 [+0.062] | −0.78 [LCB −1.27] | −0.035 | +0.0001 |
| EVERY4 (control: update every 4 budgets) | +0.0001 | +0.083 | −1.45 | −0.040 | −0.0004 |
| FREEZE24 (control: freeze at B24) | +0.0028 | +0.070 | −4.03 | −0.195 | −0.0050 |

**Sensitivity only.** AVG2 and AVG8, and HYST02 and HYST10, behave the same way. RAND8 and LOCAL8 show no S95 gain for any variant.

**Reading.** Decision-layer stabilisers can only redistribute balanced flips in time:
- they buy sustainment at the price of later attainment;
- they leave the shortfall practically unchanged (−1 % to −3 % of S95).

The freezing controls show the extreme of the same trade.

## 7. Diagnosis summary

**Mechanism.**
- C1's late BA regressions are single near-boundary test points, mostly Keyhole, in the label-interleaved fast-scan corner and the hard group.
- They are flipped locally by each new margin label in that region; half of the margin queries go there late.
  - About 62 % of these flips come through the classifier refit.
  - About 28 % come through the smooth drift of the MAP hyperparameters.
- They are balanced (harmful ≈ helpful) and explain only about 18 % of the late shortfall below 0.95.
- The remaining 82 % is a persistent level deficit of hard test folds. Its deployable slack lies outside decision smoothing; EA located it in information, not in the selector.

**Where the slack is not.**
- No separate hyperparameter mode: the two starts coincide.
- No standardisation effect.
- No multi-start fix to make.

**How it differs from earlier failures.**
- BA_RISK, JEER, coverage and the EL mixture changed acquisition or prediction to gain BA.
- Here the mechanism is a balanced boundary random walk. The only lever on the regressions themselves is the decision dynamics; the level is untouched by any of them.
