# What did we actually ask?

Phase 2.1R showed that `max_positive_delta_W` helps a model **rank** Keyhole risk. It is the largest
transverse-width increase between one **consecutive resampled analysis point** and the next — not a raw
solver timestep. Phase 2.1R-E showed that number is available within the opening ~5% of the trace. Neither says width helps **active learning**, and
there is a trap in assuming it does.

**The trap.** At budget B only the B already-queried simulations legitimately have an observed width.
An unqueried candidate does not. Scoring candidates with their true width would be reading the answer
sheet. So this phase keeps three information regimes strictly apart:

* **Regime A — deployable.** Fit a width predictor on the queried points only,
  `[P, VX, LS, ST] → hat ΔW`, and score candidates with the *predicted* width.
  Concretely: at budget 16 we know the label and observed width of 16 simulations, learn width from the
  four process inputs on those 16, and for an unqueried candidate predict — say 28 µm — and let the
  width-informed M3 use 28. Only once we actually query it does the real value replace the 28.
* **Regime C — oracle.** Every candidate's true width is visible. Deliberately leaky, reported only as
  an upper bound and labelled **ORACLE WIDTH — NOT DEPLOYABLE**.
* **Regime B — early-prefix side information.** Opening-5% width bought at an explicit cost, never free.

Everything else is the frozen thesis protocol: 405 simulations, the 100 frozen outer splits, the frozen
16-point initial designs, the budget-by-budget trajectory 16 → 80, the q20/q30 boundary masks, and M3
(physics logistic mean on `log h`, frozen, plus an ARD Matérn-3/2 discrepancy GP). The incumbent is
**M3 + M3 probability margin**.

## The incumbent is re-derived, not quoted

The A0 arm here reproduces the published Phase 1.14 M3-margin q20 accuracy AULC B16–40 of
**0.8260417** — measured here as
**0.8260417** (difference
0.00e+00, PASS). That is what licenses reading every width
arm on the same scale.

## Per-budget q20 accuracy

| budget | A0  M3-margin (incumbent) | A1  predicted-width margin (deployable) | A4  ORACLE width margin (not deployable) |
|---|---|---|---|
| B16 | 0.7859 | 0.7876 | 0.7871 |
| B24 | 0.8171 | 0.8235 | 0.8206 |
| B32 | 0.8341 | 0.8276 | 0.8371 |
| B40 | 0.8465 | 0.8482 | 0.8488 |
| B60 | 0.8565 | 0.8641 | 0.8671 |
| B80 | 0.8612 | 0.8676 | 0.8712 |

## The primary endpoint: q20 accuracy AULC B16–40

| contrast | difference [95% CI] | interval excludes zero |
|---|---|---|
| A1_predicted_width_margin − A0_m3_margin | -0.0015 [-0.0054, +0.0025] | no |
| A4_oracle_width_margin − A0_m3_margin | +0.0026 [-0.0012, +0.0067] | no |
| A1_model_on_A0_path − A0_m3_margin | +0.0010 [-0.0011, +0.0032] | no |
| A4_model_on_A0_path − A0_m3_margin | +0.0029 [+0.0006, +0.0052] | yes |
| A0_model_on_A1_path − A0_m3_margin | -0.0019 [-0.0049, +0.0014] | no |

**Deployable gain: -0.0015
[-0.0054, +0.0025].**
The predeclared success bar was +0.010 with a lower bound above zero.

Across the other metrics, on the same primary endpoint:

| metric | A1 − A0 [95% CI] |
|---|---|
| accuracy | -0.0015 [-0.0054, +0.0025] |
| balanced accuracy | -0.0015 [-0.0053, +0.0025] |
| keyhole recall | -0.0021 [-0.0108, +0.0072] |
| roc auc | +0.0011 [-0.0013, +0.0033] |
| pr auc | +0.0013 [-0.0019, +0.0048] |
| brier score | +0.0008 [-0.0013, +0.0037] |
| conduction recall | -0.0009 [-0.0068, +0.0046] |

## Oracle headroom: how much was there to win at all?

* incumbent A0: **0.8260**
* deployable A1: **0.8245**
* ORACLE A4 (NOT DEPLOYABLE): **0.8287**

Oracle headroom `A4 − A0` = **+0.0026
[-0.0012, +0.0067]**.
Recovered fraction of that headroom by the deployable method:
**-57%**.

## Model value versus acquisition value

| arm | regime | model value (fixed path) | path value (implied) | total (own path) |
|---|---|---|---|---|
| A1_predicted_width_margin | deployable (Regime A) | +0.0010 | -0.0025 | -0.0015 |
| A4_oracle_width_margin | ORACLE WIDTH - NOT DEPLOYABLE | +0.0029 | -0.0003 | +0.0026 |

A better model is not a better acquisition rule. The model column holds the query path fixed at the
incumbent's; the path column is what is left over.

## Can width be predicted at all from the process inputs?

| budget | width observations | RMSE | MAE | R² | Spearman |
|---|---|---|---|---|---|
| B16 | 14.2 | 7.87 µm | 5.95 µm | +0.071 | +0.317 |
| B24 | 21.3 | 7.72 µm | 5.80 µm | +0.092 | +0.362 |
| B32 | 28.5 | 7.50 µm | 5.71 µm | +0.137 | +0.376 |
| B40 | 35.5 | 7.34 µm | 5.60 µm | +0.153 | +0.384 |
| B60 | 54.8 | 6.74 µm | 5.17 µm | +0.277 | +0.453 |
| B80 | 73.5 | 6.55 µm | 4.98 µm | +0.336 | +0.534 |

Evaluated on training-pool points the predictor has **not** seen, at every budget.

## Why A2 (uncertainty-aware width) and A3 (early-prefix side information) were not run

Both were predeclared, and both are settled by the oracle bound rather than skipped for convenience.

**A3 — early-prefix side information (Regime B).** Phase 2.1R-E established that at the 5% prefix the
feature already equals its full-trace value for 95.4% of simulations. So the information A3 could buy is,
to within that 95.4%, the *same* information the oracle arm is handed for free. The oracle arm is the
best case for that information — it pays nothing for it and gets it for every candidate — and it returns
+0.0026 [-0.0012,
+0.0067] on the primary endpoint, an interval containing zero. A3 would
buy a near-copy of that information at a strictly positive cost in labelled simulations, so under every
cost ratio in [0.05, 0.1, 0.2, 0.5, 1.0] it is dominated by an arm that already fails. Running it could only
produce a worse number with a longer runtime.

**A2 — marginalising over width uncertainty.** A2 exists to recover signal lost by plugging in the
*mean* predicted width instead of integrating over its predictive distribution. That can only ever
recover ground between the deployable arm and the oracle arm, because integrating over a distribution
whose truth is known collapses to the oracle. With the oracle headroom itself indistinguishable from
zero, there is no gap for A2 to close.

This is the kill criterion working as intended: the oracle bound was built precisely so that a negative
result here stops the direction instead of motivating more variants.

## Claim ledger

| claim | status | guardrail |
|---|---|---|
| PRIMARY — deployable predicted-width M3-margin beats the incumbent on q20 accuracy AULC B16–40 by at least +0.010 | NOT SUPPORTED | -0.0015 [-0.0054, +0.0025]; predeclared success needs both >= +0.010 and a lower bound above zero |
| ORACLE WIDTH — NOT DEPLOYABLE — even perfectly known width improves the incumbent's q20 AULC B16–40 meaningfully | NOT SUPPORTED | +0.0026 [-0.0012, +0.0067]; this is the ceiling on any width-informed acquisition, not an achievable result |
| The width-informed model is better than the incumbent when the query path is held fixed (model value) | NOT SUPPORTED | A1 model on the incumbent path: +0.0010 [-0.0011, ...]; a model gain is not an acquisition gain |
| Width information changes which simulations get queried | SUPPORTED | 100% of runs diverge from the incumbent path; mean Jaccard overlap at B40 = 0.829 |
| The changed query path is what produces any gain (acquisition value) | NOT SUPPORTED | implied path value = total − model = -0.0025 on q20 accuracy AULC B16–40 |
| Width can be predicted well enough from [P, VX, LS, ST] at low budget to preserve the useful signal | NOT SUPPORTED | at B16 the queried-only predictor reaches R² = 0.071 (RMSE 7.87 µm) on still-unqueried points; by B80 R² = 0.336 |
| Any apparent gain required exposing true width for unqueried candidates | NOT SUPPORTED | the deployable arm never reads an unqueried candidate's true width; the oracle arm that does is labelled and reported separately |
| This phase re-derives the incumbent rather than reusing published numbers | SUPPORTED | phase114_reproduction_gate.csv: the A0 arm reproduces the published Phase 1.14 M3-margin q20 accuracy AULC B16–40 |
| Early-prefix width side information (Regime B) could rescue the direction | NOT SUPPORTED | not run, and dominated by construction: at the 5% prefix the feature equals its full-trace value for 95.4% of simulations (Phase 2.1R-E), so Regime B buys a near-copy of the oracle's information at a positive cost while the oracle itself shows no meaningful headroom |
| Marginalising over width-prediction uncertainty (A2) could rescue the direction | NOT SUPPORTED | not run: A2 can only recover ground between the deployable arm and the oracle arm, and that gap is indistinguishable from zero |
| Results transfer to the 55 simulations with no usable width trace | NOT SUPPORTED | those points always carry a predicted width; missingness is structured (5.5% Keyhole versus 20%), so all results are conditional on it |
| This is confirmatory evidence for the thesis' external protocol | NOT SUPPORTED | OLD-405 development evidence only; the frozen external-confirmation protocol is untouched |

## Verdict

**KILLED**

## What this is not

OLD-405 development evidence only. No change to the frozen external-confirmation protocol, no
monitoring claim, and nothing here transfers to the 55 simulations whose width trace is unusable —
those always carry a predicted value, and their missingness is structured (5.5% Keyhole against 20%).
