# Week 9 Phase 1.11 — Fixed Physics Mean + GP Discrepancy

## Result
Decision: **FIXED_MEAN_SUPPORTED**.

M2 q20 AULC was 0.830230, versus M0 0.813520, M1 0.829972, and MH 0.830813.
Matched M2−M0: +0.016710 [+0.010239, +0.022992] (18/20 positive repeat blocks).
Matched M2−M1: +0.000257 [-0.001438, +0.002284].
Matched M2−MH: -0.000584 [-0.002440, +0.001443].

## Low-data B16
q20 accuracy M0/MH/M1/M2: 0.7318 / 0.7865 / 0.7847 / 0.7865.
q20 Keyhole recall M0/MH/M1/M2: 0.4975 / 0.7194 / 0.7221 / 0.7194.
Relative to M0, M2 increased B16 q20 Keyhole recall by +0.2219 [+0.1790, +0.2653] and reduced mean false negatives by 1.48. M2 and MH had identical B16 hard decisions.

## Residual stability
Residual-SD lower/upper/any bound rates were M1 0.359/0.151/0.510, versus M2 0.278/0.003/0.281.
Matched any-bound change M2−M1: -0.229 [-0.263, -0.192].
Fallback rates M1/M2: 0.0000/0.0000; M2 optimizer non-convergence rate: 0.0577.

## Scientific answers
1. M2 retained the low-data advantage over M0, chiefly through Keyhole recovery at B16.
2. The discrepancy GP did not show resolved q20 AULC benefit beyond MH on the same labels.
3. M2 and M1 were predictively indistinguishable under the repeat-block interval.
4. Freezing the mean materially reduced residual-SD bound hitting, especially upper-bound hits.
5. There were no fit fallbacks, but 5.77% of M2 optimizations ended without a convergence-success flag.
6. The evidence therefore supports M2 as a cleaner two-stage physics-informed architecture when a discrepancy term is desired; MH remains simpler and equally predictive here.

## Safe interpretation
The training-fitted h latent mean was frozen before the 4D GP discrepancy fit. This preserves the low-data physics benefit while reducing residual-SD boundary pathology relative to M1. It removes direct re-optimization of the physics coefficient, but does not make the residual orthogonal to h and does not solve identifiability. All comparisons use the same frozen A0 path, so no acquisition claim is made.
