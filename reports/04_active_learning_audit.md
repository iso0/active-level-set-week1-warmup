# Phase 1.5 physics-informed active-learning audit

## Protocol and leakage status

The analysis imported the exact Week 8.5 split, initial-design, Fold-B1, AULC and persistent-crossing functions. The frozen baseline gate passed before new arms ran. All 100 outer runs were completed to H80; only the scientifically relevant `h_margin` arm was extended to H160. The 3000 saved Random continuations were reused.

The 19,200 H80 acquisition records state and the focused tests verify: candidates came only from the outer training pool; test rows, hidden unqueried labels and B1/B2/B3 were unavailable; no full-pool label threshold was fitted. Acquisition selectors accept only candidate indices and revealed-label model probabilities.

## Primary q20 AULC 16–80

| Model/policy | Mean AULC | Difference vs frozen 4D Margin | 95% repeat-block CI | Decision |
|---|---:|---:|---:|---|
| frozen 4D Margin | 0.81352 | — | — | reference |
| h query → h model | 0.83174 | +0.01822 | [+0.01157, +0.02462] | improves this 1D model-policy pair |
| h query → 4D GPC | 0.80083 | -0.01269 | [-0.02176, -0.00295] | worse 4D exploration |
| 5D GPC Margin | 0.81539 | +0.00187 | [-0.00322, +0.00659] | no resolved improvement |
| 4D×h uncertainty | 0.80547 | -0.00805 | [-0.01533, -0.00032] | worse than 4D Margin |

The key separation is therefore model versus acquisition policy. A strongly constrained 1D learner is sample-efficient on q20, but using its exact query sequence to train a 4D GPC loses 0.0127 AULC versus canonical 4D Margin. This is evidence that pure h querying under-explores residual 4D structure.

At budget 40, q20 accuracy was 0.8341 for the h model, 0.8047 for a 4D GPC on the same h-selected labels, and 0.8171 for frozen 4D Margin.

By H160, stable q20 ≥0.80 was observed in 86/100 h-model paths and 89/100 4D-GPC-on-h-query paths. Frozen 4D Margin reached it in 91/100 by H160. These censored rates do not support a universal “45 queries saved” headline.

## Verdict

- Physics-inspired `h` is useful as a low-dimensional **model prior**.
- Pure h acquisition does not improve learning of the full 4D boundary.
- Redundant 5D embedding is statistically unresolved versus 4D Margin and worsens static probability scores slightly.
- The untuned uncertainty product is inferior to canonical 4D Margin.
- No hidden-label Antigravity threshold was retained.
