# Week 9 Phase 1.16 — M3 Margin + Repulsion Scale Audit

## Decision: REPULSION_MECHANISM_ONLY

## Frozen design and baseline

The exact Phase 1.14 M3-margin path is the c=0 baseline. Five geometry-relative scales (c=.25,.5,1,2,4) change only the acquisition score; M3, splits, initial designs, budgets, and evaluation definitions remain frozen. Inference uses 20 repeat blocks and 10,000 paired bootstrap draws.

## Primary q20 AULC scale response

| Arm | c | q20 AULC | Difference | 95% CI |
|---|---:|---:|---:|---:|
| M3_MARGIN | 0 | 0.844623 | +0.000000 | [+0.000000, +0.000000] |
| REP_C025 | 0.25 | 0.846144 | +0.001521 | [-0.000744, +0.003676] |
| REP_C050 | 0.5 | 0.846094 | +0.001471 | [-0.001255, +0.004049] |
| REP_C100 | 1 | 0.847169 | +0.002546 | [-0.000648, +0.005597] |
| REP_C200 | 2 | 0.846861 | +0.002238 | [-0.001673, +0.005786] |
| REP_C400 | 4 | 0.847321 | +0.002698 | [-0.000892, +0.005970] |

All five point estimates are positive, but every primary interval includes zero. The predeclared response therefore shows **no supported performance scale**. The best-looking numerical arm (REP_C400) is not promoted as a selected winner.

## Early/late and B40 Keyhole mechanism

| Arm | Early ΔAULC | Late ΔAULC | B40 q20 KH-recall Δ (95% CI) | B40 spread Δ |
|---|---:|---:|---:|---:|
| M3_MARGIN | +0.000000 | +0.000000 | 0 | +0.0000 |
| REP_C025 | +0.002218 | +0.001011 | -0.0179 [-0.0344, -0.0024] | -0.0425 |
| REP_C050 | +0.003395 | +0.000226 | -0.0162 [-0.0384, +0.0050] | +0.0151 |
| REP_C100 | +0.004890 | +0.001003 | -0.0138 [-0.0303, +0.0033] | +0.0721 |
| REP_C200 | +0.004975 | +0.000445 | -0.0111 [-0.0325, +0.0103] | +0.0981 |
| REP_C400 | +0.006103 | +0.000505 | -0.0032 [-0.0273, +0.0193] | +0.1011 |

Repulsion strengthens early q20 accuracy AULC at larger scales, but it does not repair the motivating B40 Keyhole-recall loss. c=.25 significantly worsens that recall; all other recall intervals include zero with negative point estimates. Geometry spreads for c≥.5, while c=.25 is too weak to prevent narrowing.

## Sample efficiency

| Arm | Reach rate at .84 | Median first hit | Mean paired budget difference | 95% CI |
|---|---:|---:|---:|---:|
| M3_MARGIN | 1.00 | 25.5 | +0.00 | [+0.00, +0.00] |
| REP_C025 | 1.00 | 27.0 | -1.25 | [-3.55, +0.70] |
| REP_C050 | 1.00 | 25.5 | -1.95 | [-5.00, +1.05] |
| REP_C100 | 1.00 | 26.0 | -1.05 | [-4.25, +1.80] |
| REP_C200 | 1.00 | 24.5 | -0.30 | [-4.25, +3.70] |
| REP_C400 | 1.00 | 24.0 | -1.80 | [-5.15, +1.30] |

All repeats reach .84, but no paired first-hit contrast excludes zero. There is no supported label-saving conclusion.

## q30 and full81 robustness

Every repulsion scale has a small supported positive q30 AULC difference (approximately +.0023 to +.0034). This is a useful robustness signal, but q30 is secondary and cannot overturn the unresolved primary q20 endpoint.

At B80, full81 accuracy and Keyhole-recall changes are negligible and unresolved; no meaningful global degradation is detected.

## Path and numerical behavior

At B40, mean Jaccard overlap falls from 0.786 (c=.25) to 0.657 (c=4). Repulsion genuinely changes geometry rather than merely reordering identical points. Active-query Keyhole fraction falls as repulsion strengthens, explaining why geometric diversity does not automatically recover Keyhole recall.

Optimizer convergence remains above 92.0%. Residual-SD upper-bound pressure remains high and is higher late for strong repulsion; numerical behavior is usable but not improved.

## Multiplicity

No overall q20 comparison survives Holm adjustment (smallest adjusted p=0.207).

## Safe interpretation

On the frozen 405-simulation benchmark, geometry-relative repulsion mitigates the spatial concentration of plain M3 margin for c≥.5, but this geometric correction does not produce a statistically resolved overall q20 AULC or first-hit advantage and does not recover B40 Keyhole recall. The broad positive q30 and early-q20 patterns are secondary qualified signals, not a robust acquisition gain.

## Claim boundary and next action

This replay does not establish universal superiority, an optimal scale, theoretical sample complexity, external transfer, or causal ARD importance.

Do not launch another broad repulsion search. Close repulsion as a performance-improvement direction; retain the geometry diagnostic as evidence that diversity alone is insufficient for the Keyhole-recall failure mode.
