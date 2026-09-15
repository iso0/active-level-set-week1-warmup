# Week 9 Phase 1.18A — Level-set acquisition compatibility audit

## Frozen design

All 100 published Phase 1.14 M3-margin paths were replayed at B16/24/32/40/60/80. This produced 600 posterior snapshots and 169,200 pre-reveal candidate occurrences. No point was selected, no label was newly revealed, and no trajectory was generated.

## Main ranking results

| Method vs Margin | median Spearman | q05 | top-1 | top-10 Jaccard | decision |
|---|---:|---:|---:|---:|---|
| Straddle | 0.9991 | 0.4710 | 0.663 | 0.844 | RANKING_DISTINCT_FROM_MARGIN |
| EMI | 0.9872 | 0.3614 | 0.660 | 0.748 | RANKING_DISTINCT_FROM_MARGIN |
| SMOCU approximation | -0.0884 | -0.9014 | 0.352 | 0.331 | RANKING_DISTINCT_FROM_MARGIN |
| SUR approximation | 0.6884 | -0.7707 | 0.285 | 0.437 | RANKING_DISTINCT_FROM_MARGIN |
| supplied PA-TVR | 0.9772 | 0.1473 | 0.222 | 0.484 | RANKING_DISTINCT_FROM_MARGIN |

Margin is not variance-blind: M3 probability integrates latent variance. Its limitation is that it does not separately optimize epistemic variance or expected domain-wide uncertainty reduction.

The full-pool approximations became exactly flat in a small number of snapshots, so Spearman was undefined there (Margin comparisons: SMOCU 4/600, SUR 4/600, EMI 22/600). These are reported as approximation degeneracies, not silently imputed. In the predeclared three-candidate exact-refit check, SMOCU's exact/approximate top IDs were 201/402, while SUR's were 201/201. Thus the approximate rankings are diagnostic evidence of distinctness, not a validated prospective implementation.

## PA-TVR falsification

The local Laplace variance-reduction factor is defensible with posterior-expected site curvature `W_C`. The proposed `S^-1/2 exp(-2mu^2/S)` factor was not derived from an ARD Matérn-3/2 tangent-hyperplane integral. It contains no cross-covariance to other locations and is therefore geometry-local, not global or non-myopic. L100→L1000 median ranking Spearman was 1.0000, top-1 agreement 0.963, and top-10 Jaccard 0.966. Decision: **PA_TVR_REJECTED**. It is not rescued by retrospective behavior.

## Runtime

Mean L100 snapshot M3 fit/local/global-approx scoring times were 0.112/0.005/0.100 s. A naive 100×64 prospective approximate-global replay is roughly 0.38 CPU-hours at observed cost, excluding orchestration. Exact candidate-by-candidate M3 refits would be far more expensive; this phase does not conflate the approximation with exact SMOCU/SUR.

## Retrospective diagnostic boundary

Truth/B1-like annotations were joined only after `candidate_scores_pre_reveal.csv.gz` was frozen and hashed. They describe which already-scored points rank highly; they are not acquisition performance, AULC, label saving, or a basis for method selection.

## Decision

PA-TVR is rejected. The single future candidate is **FAST_GPC_SUR**, because it directly targets random-set/level-set uncertainty and has verified GPC prior art, conditional on implementing and validating the literature-faithful classifier update before one prospective path. The current rank-one proxy is not that implementation. If the exactness gate fails, the recommendation becomes NONE. No novelty or sample-efficiency claim is made.
