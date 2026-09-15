# Week 9 Phase 2 final report — corrected transverse width

# Supervisor Phase 2 — one page

## Correction and question
The authoritative extractor verifies **ΔX = longitudinal length** and **ΔY = transverse width**. The original Phase 2 accidentally answered the ΔX question. This correction answers Ioan using **W(t)=Ymax−Ymin=ΔY**.

## Corrected data and physical width
350/405 traces are usable (70 Keyhole, 280 Conduction). Median transverse Wmax is 174.5 µm for Keyhole versus 174.8 µm for Conduction; WT0 is 158.7 versus 161.1 µm. This is a descriptive effect; standalone hard classification is reported separately.

## Temporal feature and derivative robustness
The strongest deterministic shape/robust-derivative feature is `robust_median_positive_dWdt_um_per_ms`: Conduction median 26.8, Keyhole median 19.5 µm/ms (Cliff's delta -0.266). Raw early-20% dW/dt medians (Conduction, Keyhole) are -205.4, -57.9 µm/ms; fixed robust medians are 382.6, 401.2. Early-20% derivative gate: **QUALIFIED**. No faster/slower physical claim is made unless direction survives denoising.

## Does true width add beyond h?
On q20, balanced accuracy is h-only 0.821, static width 0.510, width dynamics 0.505, and h+width 0.801. The h+width hard-decision contrasts are BA -0.020 [-0.029,-0.012] and Keyhole recall -0.063 [-0.078,-0.048]: **NOT SUPPORTED**.

Ranking/probability contrasts are ROC-AUC +0.002 [-0.007,+0.010], PR-AUC +0.020 [+0.011,+0.029], and Brier -0.001 [-0.004,+0.002] (negative Brier is better): **SUPPORTED**.

The fixed shape-only sensitivity preserves hard performance better: q20 BA contrast -0.001 [-0.009,+0.007], PR contrast +0.024 [+0.018,+0.031], Brier contrast -0.009 [-0.010,-0.008]. This diagnostic is not post-hoc tuning.

## Earliest prefix and onset
At τ=0.20, q20 BA changes +0.019 [+0.011,+0.025] and Keyhole recall +0.017 [+0.002,+0.029]; ROC/PR/Brier change +0.006/+0.019/-0.004. First-observed manual Keyhole timing exists for 70 traces. Robust peaks precede it in 100.0%, median descriptive lead 0.253 ms, but startup peaks are generic and no held-out warning rule exists. Verified pre-Keyhole warning: **NOT SUPPORTED**.

## What ΔX taught us
The archived longitudinal diagnostic had q20 width-dynamics BA 0.734 and h+ΔX BA 0.790; it described longitudinal growth, not transverse monitoring width.

## Canonical numbers
- Usable traces: 350/405; Keyhole: 70
- Wmax medians (Conduction, Keyhole): 174.829, 174.535 µm
- WT0 medians (Conduction, Keyhole): 161.118, 158.689 µm
- Best robust/shape temporal feature: robust_median_positive_dWdt_um_per_ms; Cliff's delta -0.2656
- q20 balanced accuracy (h, width dynamics, h+width): 0.8210, 0.5054, 0.8009
- q20 Keyhole recall (h, h+width): 0.7305, 0.6676
- q20 ROC/PR/Brier contrasts (h+width minus h): +0.0016, +0.0202, -0.0011
- τ=0.20 q20 BA/ROC/PR/Brier contrasts: +0.0185, +0.0058, +0.0186, -0.0043
- Final Phase 2 claim: INCREMENTAL / QUALIFIED SIGNAL; hard-decision NOT SUPPORTED; ranking/probability SUPPORTED


## Methods and claim discipline

The authoritative source and five pinned files verify ΔX=longitudinal length and ΔY=transverse width. All 100 frozen outer folds were intersected with the usable temporal subset. Primary temporal models use deterministic shape plus fixed robust-derivative features; raw finite differences are descriptive. Scalers and fixed logistic models are trained within each fold. B1/q20/q30 are evaluation-only. Repeat-block uncertainty resamples 20 repeats, keeping five folds together. The onset is the first observed valid manually labelled frame, not continuous physical onset.

## Direct scientific answers

1. The reported W(t) is transverse ΔY.
2. Static/profile effects are described by effect size, separately from classifier performance.
3. Derivative claims are governed by `derivative_robustness_gate.csv`.
4. Width-only dynamics and h+width are compared on hard and ranking/probability metrics separately.
5. Prefix models use no future samples.
6. No derivative peak is called a warning event.
7. The published ΔX result is retained only as a longitudinal diagnostic.
