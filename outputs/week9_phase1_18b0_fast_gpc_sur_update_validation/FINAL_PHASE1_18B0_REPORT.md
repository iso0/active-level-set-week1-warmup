# Week 9 Phase 1.18B0 — FAST GPC-SUR update validation

## Decision

**FAST_SUR_REJECTED**; secondary model-refit result: **PHYSICS_REFIT_MATTERS**.

This phase used 25 predeclared frozen Phase 1.14 M3 snapshots, 307 pre-reveal candidates, both hypothetical labels and four update levels (2,456 candidate-label-level updates). No acquisition path was generated and no q20/B1/test outcome entered selection or scoring.

## Primary FAST versus exact-fixed gate

Median/q10 snapshot Spearman: 0.4813/-0.2106; top-1 agreement 44.0%; mean top-5 Jaccard 0.5238; median FAST-top rank under exact 2.0; sign-reversal fraction 28.7%; late-budget median Spearman 0.4749.

Spearman was undefined in 2/25 snapshots because one compared score vector was constant; these cases remain in top-k and sign diagnostics and were not imputed.

The median/q90 snapshot probability MAE was 1.062e-05/1.054e-04. Thus latent/predictive updates are numerically close, but SUR is a small difference of integrated uncertainties and its candidate ranking is not preserved. Small posterior error is not sufficient acquisition-score fidelity.

Hypothetical label 0/1 probability MAE: 2.047e-05/4.543e-05; the minority-class hypothetical update is less accurately approximated, but both absolute errors remain small.

## Refit decomposition

- Rank-one versus exact-fixed: median Spearman 0.4813, top-1 44.0%.
- Physics-refit versus exact-fixed: 0.2627, top-1 8.0%.
- Full-refit versus physics-refit: 0.9860, top-1 64.0%.

The h-only physics backbone refit materially changes the hypothetical ranking. Kernel reoptimization is much less disruptive under the predeclared rule. This supports treating fixed-model exact Laplace as the clean literature-aligned posterior-update comparator, while acknowledging that the normal empirical-Bayes pipeline itself changes after a label.

## Runtime

Mean seconds per hypothetical label: FAST 0.000132, exact-fixed 0.001636, physics-refit 0.005727, full-refit 0.066502. Naive 100-run B16→B80 all-candidate projections are approximately FAST 0.1, exact-fixed 1.6, physics-refit 5.6, full-refit 65.3 CPU-hours. These are linear extrapolations, not optimized-engine timings.

## Safe conclusion

FAST_RANK1 did not faithfully reproduce exact fixed-model GPC-SUR rankings and must not be used for a prospective trajectory. Exact-fixed SUR appears computationally far cheaper than full refitting, but its engineering feasibility and exact prospective protocol would require a separate predeclared decision; this phase does not test whether SUR beats Margin.
