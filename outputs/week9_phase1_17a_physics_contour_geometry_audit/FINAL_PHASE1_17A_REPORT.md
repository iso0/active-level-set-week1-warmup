# Week 9 Phase 1.17A — Physics-Contour Geometry Audit

## Decision: MIXED_GEOMETRIC_MECHANISM

No new active-learning path or acquisition was run. The 38,400 published Phase 1.16 active selections were decomposed in each outer run's exact standardized Euclidean coordinates.

## Scale response

| c | mean r_N | mean r_T | mean r_ST | total distance | B1 distance | q20 fraction | KH fraction |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.1843 | 0.5681 | 0.2476 | 0.7685 | 0.8225 | 0.6877 | 0.4205 |
| 0.25 | 0.1817 | 0.5687 | 0.2496 | 0.8012 | 0.8336 | 0.6745 | 0.4138 |
| 0.5 | 0.1880 | 0.5550 | 0.2570 | 0.8504 | 0.8531 | 0.6509 | 0.4027 |
| 1 | 0.2012 | 0.5431 | 0.2557 | 0.8841 | 0.8712 | 0.6297 | 0.3994 |
| 2 | 0.2032 | 0.5440 | 0.2528 | 0.8960 | 0.8768 | 0.6236 | 0.3975 |
| 4 | 0.2035 | 0.5445 | 0.2520 | 0.8983 | 0.8781 | 0.6219 | 0.3972 |

## Extra-distance mechanism

From c=0 to c=4, mean distance changes by +0.1299 (repeat-block 95% CI [+0.1245, +0.1350]). Of the positive increase in mean squared component energy, normal contributes 30.1%, P/VX/LS physical tangent 42.9%, and ST 26.9%. Absolute tangent energy is the largest contributor, but its share falls by -0.0236; normal share rises by +0.0192, while the ST-share change +0.0044 is unresolved.

## Budget dependence

EARLY: c=4 raises ST share from 0.250 to 0.282 while tangent share falls. MID (B25–40): normal share rises 0.159→0.173, tangent share is nearly unchanged (0.598→0.594), and ST share falls 0.243→0.233. LATE: normal share rises 0.190→0.216 and tangent share falls 0.561→0.531. The mechanism is therefore budget-dependent and is not strongest in one component around B25–40.

## Retrospective boundary and class associations

At c=4, retrospective B1 distance changes +0.0557, q20 concentration -0.0658, and active-query Keyhole fraction -0.0233 relative to margin. q20-like minus non-q20 queries at c=4 have Δr_N=-0.0078, Δr_T=+0.0762, and Δr_ST=-0.0684: q20-like queries are more tangent and less ST, not more normal. Keyhole minus Conduction queries at c=4 have Δr_N=+0.0402, Δr_T=-0.0083, and Δr_ST=-0.0319.
For c=4, repeat-aggregated Spearman associations with retrospective B1 distance are normal -0.000 [-0.017, +0.016], tangent -0.151 [-0.172, -0.132], and ST +0.145 [+0.118, +0.172]. Greater B1 distance is associated with more ST share and less tangent share; it is not associated with greater normal share at c=4. These are retrospective associations, not acquisition inputs or causal effects.

## Numerical integrity

Zero-distance events: 0. Maximum orthogonality error 9.992e-16; maximum reconstruction error 2.355e-16; maximum energy error 2.276e-15; maximum fraction-sum error 8.882e-16. Exact Phase 1.16 selected-distance recovery maximum difference: 4.441e-16.

## Safe interpretation

The extra squared-distance energy is mixed: tangent 42.9%, normal 30.1%, and ST 26.9%. Neither normal escape nor ST-nullspace escape alone explains the Phase 1.16 result. The decomposition describes local physics-contour geometry only; it does not identify the true M3 boundary normal or a causal physical direction.

## Next step

Do not run Phase 1.17B now. A tangent-only PCTR rule would remove the normal component but would not resolve the ST association, and most extra energy is already tangent plus ST. The audit therefore does not isolate a clear harmful mechanism that PCTR specifically addresses.
