# Week 9 Phase 1.13 — Fixed Physics Mean + ARD GP Discrepancy

## Decision: HYBRID_GAIN_SUPPORTED

## Same-path q20 result
AULC H/G0/G3/M2/M3: 0.830813 / 0.813520 / 0.826595 / 0.830230 / 0.842491.
Primary M3-H: +0.011677 [+0.007201, +0.016149] (18/20 positive repeats).
M3-M2: +0.012261 [+0.007638, +0.016705].
Mechanistic M3-M2W: +0.012261 [+0.007624, +0.016609].
M3-G3: +0.015896 [+0.008051, +0.024219].

## Early versus late
Early B16-40 M3-H +0.004436 [+0.001324, +0.007917]; M3-G3 +0.048640 [+0.040319, +0.056741].
Late B41-80 M3-H +0.016094 [+0.009660, +0.022300]; M3-G3 -0.004457 [-0.014744, +0.006418].

## Checkpoints
B16 q20 accuracy H/G3/M2/M3: 0.7865/0.7235/0.7865/0.7859; KH recall: 0.7194/0.5251/0.7194/0.7221.
B40 q20 accuracy H/G3/M2/M3: 0.8359/0.8253/0.8347/0.8494; KH recall: 0.7457/0.7473/0.7469/0.7724.
B80 q20 accuracy H/G3/M2/M3: 0.8341/0.8571/0.8347/0.8576; KH recall: 0.7118/0.7644/0.7262/0.7327.

## Residual role
At B16/B40/B80, q20 decisions changed relative to the frozen physics mean in 1.1%/4.2%/5.5%. Residual posterior-mean SD was 0.069/0.328/0.507.
Among changed q20 decisions, the beneficial shares were 47.4%/66.2%/71.3%; harmful shares were 52.6%/33.8%/28.7%.
No orthogonality or identified physical decomposition is claimed.

## Bounds and sensitivity
M3 residual-SD upper-bound hit rate over B16-80 was 47.9% (any amplitude bound: 55.3%); this is a material regularization limitation.
M3 L100 any-upper-length-bound rates at B16/B40/B80: 25.0%/83.0%/66.0%.
Changing the length upper bound 100 to 1000 produced maximum checkpoint full81 probability MAE 0.0009 and maximum absolute q20 accuracy change 0.0006.
Predictions are locally stable to L1000, but fitted ARD geometry is bound-sensitive. ARD lengthscales are standardized-space geometry diagnostics, not physical importance or exponents.

## q30 robustness
M3-H +0.012250 [+0.009153, +0.015391]; M3-M2W +0.012122 [+0.008900, +0.015303]; M3-G3 +0.014172 [+0.007641, +0.021385].

## Scientific conclusion
Preferred simulator surrogate: **YES**. Future M3-margin acquisition experiment justified: **YES**.
All evidence is model-only on one frozen simulator benchmark and one A0 path. Acquisition, external transfer, causal importance, orthogonality, and universal physics are not tested.
