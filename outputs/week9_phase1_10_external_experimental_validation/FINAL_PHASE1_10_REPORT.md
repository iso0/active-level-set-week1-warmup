# Week 9 Phase 1.10 — independent experimental validation

## Question and scope

This small predeclared experiment asks whether the SPH-derived process direction remains useful for Conduction-versus-Keyhole discrimination in the independent Masinelli et al. experimental LPBF process map. The external target is transition-inclusive predominant post-mortem metallographic regime, not the thesis any-valid-frame simulator label; this is **independent but non-identical experimental validation**.

Only pre-process `P`, `VX`, and derived `h` were used. Optical signals, active learning, B1/q20/q30, material normalization, and alloy pooling were excluded.

## Source and population gate

The pinned public workbooks at GitHub commit `50ccb1bab03c626cb9f83d9c4f44182f58dda439` reproduced the forensic audit exactly. Ti64 has 60 bundles, 38 exact `(P,VX)` conditions, 26 Conduction and 34 transition-inclusive Keyhole labels. 316L has 60/38/37/23. Ti64 contains two binary-discordant repeated conditions; 316L contains none. Raw third-party data were not committed.

The paper reports a 50 µm `1/e²` spot **diameter**, so thesis `LS=r0=25e-6 m`. The computed coordinate is dimensional:

`h = P / sqrt(VX * LS^3)` with `P` in W and `VX` in m/s.

Because `LS` is constant, this study tests only the fixed `P*VX^(-1/2)` direction. It cannot validate the `LS^(-3/2)` exponent or a universal threshold.

## Frozen grouped OOF protocol

Each alloy was evaluated separately with 20 deterministic repeats × 5 `StratifiedGroupKFold` folds. The exact `(P,VX)` condition is the group, so no replicate crosses a fold. Each repeat pools all five held-out folds into one complete 60-bundle OOF vector before computing metrics. Every held-out fold contains both classes.

- H: training-standardized `log(h)`; L2 logistic regression, `C=1`, intercept.
- G: training-standardized `[log(P), log(VX)]`; the identical L2 logistic implementation.
- GPC (secondary): training-standardized `[log(P), log(VX)]`; `ConstantKernel × Matérn-3/2`, one optimizer start, no test-driven tuning.

Intervals bootstrap the 20 paired repeat blocks with 10,000 draws. They quantify sensitivity to the frozen grouped-CV partitions; they are not intervals from 20 independent experimental datasets.

## Ti64 primary result

- H: ROC-AUC 0.9765; PR-AUC 0.9842; balanced accuracy 0.9226; Keyhole recall 0.9029; Brier 0.0741.
- G: ROC-AUC 0.9921; PR-AUC 0.9937; balanced accuracy 0.9503; Keyhole recall 0.9294; Brier 0.0640.
- GPC: ROC-AUC 0.9896; PR-AUC 0.9918; balanced accuracy 0.9343; Keyhole recall 0.9206; Brier 0.0612.
- Primary H−G ROC-AUC: -0.015611, 95% split-bootstrap CI [-0.016686, -0.014536].

The predeclared verdict is **GENERIC_DIRECTION_SUPERIOR**. The fixed direction is nevertheless strongly discriminative in absolute terms (H ROC-AUC 0.9765); the more flexible two-slope logistic extracts a small but repeat-stable additional ranking signal.

## Condition-level robustness

After excluding the two discordant Ti64 conditions, the 36-condition sensitivity gives H ROC-AUC 0.9958, G 0.9970, H−G -0.001250 [-0.002656, +0.000156]. Strict-majority sensitivity excludes the same tied conditions and is identical by construction. Thus the bundle-level generic advantage is materially reduced and statistically unresolved once unavoidable label-discordant repeats are removed.

## 316L secondary result

- H: ROC-AUC 0.9912; PR-AUC 0.9866; balanced accuracy 0.9071; Keyhole recall 0.8413; Brier 0.0519.
- G: ROC-AUC 0.9959; PR-AUC 0.9941; balanced accuracy 0.9258; Keyhole recall 0.8543; Brier 0.0518.
- Primary-style H−G ROC-AUC contrast (secondary material): -0.004700 [-0.007756, -0.001467].

This is qualitatively consistent evidence that the fixed direction organizes the 316L map, but it is not cross-material transfer because coefficients were fitted and evaluated within 316L.

## Decision and safe claim

**Safe thesis claim:** “The fixed `P*VX^(-1/2)` physics-aligned direction provides substantial Conduction–Keyhole discrimination in an independent, non-identical Ti-6Al-4V experimental process map. A generic two-slope log-linear model performs modestly better in the primary bundle-level grouped OOF analysis, while their difference becomes unresolved after excluding two label-discordant repeated conditions.”

The result does not experimentally prove SPH physics, validate the spot-size exponent, establish a universal boundary, or demonstrate external active-learning benefit.

## Main limitation and next step

There are only 38 unique conditions per alloy, the Ti64 map has two conditions with conflicting bundle labels, and the external predominant metallographic target differs from the thesis any-frame label. The repeated-CV intervals therefore describe partition sensitivity, not population-level experimental replication uncertainty.

A finite-pool experimental AL replay is technically feasible, but it is **not the next confirmatory step for physics-direction superiority**: H is strong yet G is better in the primary bundle-level analysis. Any later replay should be explicitly exploratory and compare physics and generic policies fairly.
