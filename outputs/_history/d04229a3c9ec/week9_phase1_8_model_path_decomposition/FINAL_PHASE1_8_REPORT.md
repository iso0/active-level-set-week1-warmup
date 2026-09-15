# Week 9 Phase 1.8 — Final report

## Question and frozen 2 × 2 design

This study separates the prediction-model contribution from the contribution of the query path induced by the physics-informed model/policy. No new acquisition trajectory was generated. `Y00` and `Y11` are reused published results; only `Y10` and `Y01` are full new fixed-path replays.

| | A0: frozen 4D path | A1: frozen physics path |
|---|---:|---:|
| M0: canonical 4D GPC | Y00 0.813520221 | Y01 0.807187500 |
| M1: physics ridge + residual GP | Y10 0.829972426 | Y11 0.833538603 |

All values are Fold-B1-q20 accuracy AULC 16–80.

## Primary decomposition

- Total `Y11-Y00`: +0.020018382, 95% repeat-block CI [+0.014204963,+0.026351333].
- Symmetric MODEL contribution: +0.021401654, CI [+0.014549632,+0.028858169].
- Symmetric PATH contribution: -0.001383272, CI [-0.005340246,+0.002605756].
- Interaction: +0.009898897, CI [+0.000813074,+0.019224035].
- MODEL-PATH: +0.022784926, CI [+0.013244485,+0.032978171].

Decision: **MODEL_DOMINANT** under the predeclared CI rule.

The physics model on the original 4D path has `ME_A0=+0.016452206` [+0.010859375,+0.022090993]. The physics-induced path under the ordinary 4D model has `PE_M0=-0.006332721` [-0.014048828,+0.001438764]. This is a query-path contribution induced by the physics-informed model/policy, not acquisition-function superiority.

## Budget-16 low-data diagnostic

Both paths are identical through the shared initial 16 simulations, so every effect below is purely prediction-model structure:

- full81: accuracy +0.013333 [+0.005802,+0.020991]; balanced_accuracy +0.062926 [+0.048502,+0.078024]; keyhole_recall +0.140286 [+0.114762,+0.167239]
- B1_q30: accuracy +0.042400 [+0.022400,+0.063200]; balanced_accuracy +0.091210 [+0.068205,+0.116119]; keyhole_recall +0.227283 [+0.187634,+0.269094]
- B1_q20: accuracy +0.052941 [+0.028235,+0.078824]; balanced_accuracy +0.084467 [+0.058419,+0.110582]; keyhole_recall +0.224611 [+0.181880,+0.267620]

The same-model numerical gates pass exactly: `Y00(16)=Y01(16)` and `Y10(16)=Y11(16)` for the stored evaluation metrics.

## Fixed-path residual-bound sensitivity

Residual-SD upper bounds 0.5, 1.0 and 2.0 were evaluated only on the already observed A0 and A1 paths at budgets 16, 40 and 80. No path was regenerated and no setting was selected. The maximum A1 q20-accuracy spread across bounds at a checkpoint is 0.010000; verdict: **checkpoint-level advantage locally stable in direction, with small variation**. This is a three-checkpoint diagnostic, not a sensitivity AULC or a new model-selection result. Detailed bound-hit rates, realized residual RMS, fitted SD and length scale are in `regularization_sensitivity.csv`.

## Safe conclusion

On this frozen 405-simulation benchmark, the Phase 1.7 improvement decomposes into a prediction-model contribution and a query-path contribution induced by the physics-informed model/policy. The predeclared dominance decision is **MODEL_DOMINANT**. This is not evidence of universal physical validity, acquisition-function superiority, or prospective experimental performance.

## Main limitation

This is a retrospective fixed-path decomposition on one simulator/material dataset. The paths are themselves posterior-dependent, and the additive physics trend and 4D residual are not fully identifiable because `h` is derived from `P,VX,LS`. The residual bound diagnostic is local robustness analysis, not tuning.
