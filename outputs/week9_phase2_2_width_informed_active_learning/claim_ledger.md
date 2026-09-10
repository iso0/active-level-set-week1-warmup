# Week 9 Phase 2.2 claim ledger

Primary question: **can the predictive width signal be turned into a legitimate sample-efficiency
improvement over M3 + M3-margin?**

Primary endpoint: q20 accuracy AULC B16–40, deployable predicted-width arm minus the incumbent.
Predeclared success: gain >= +0.010, paired 95% lower bound above zero, and Keyhole recall
not materially degraded.

The width feature throughout is `max_positive_delta_W`: the largest transverse-width increase between
one **consecutive resampled analysis point** and the next, on the pinned Phase 2 grid. These are not raw
solver timesteps.

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

## Status vocabulary
- **SUPPORTED** — the paired 95% repeat-block interval excludes zero in the favourable direction and,
  where a size bar applies, the effect clears it.
- **QUALIFIED** — directionally present but below the predeclared bar, or present on some endpoints only.
- **NOT SUPPORTED** — no detectable difference, or a difference in the unfavourable direction.
