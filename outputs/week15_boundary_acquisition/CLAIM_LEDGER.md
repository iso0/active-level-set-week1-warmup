# Week 15 claim ledger

Tags: THEOREM/EXACT · CONTROLLED SYNTHETIC (dev / frozen held-out) · HISTORICAL OLD · POST-HOC NEW · EXTERNAL · SPECULATIVE.

| # | Claim | Tag | Evidence |
|---|---|---|---|
| 1 | P(T_both > t) = [C(K,t) + C(N−K,t)]/C(N,t) for t ≥ 1 and E[T_both] = (N+1)/(K+1) + (N+1)/(N−K+1) − 1 for every adaptive rule under the exchangeable model; the Week 14 statement was wrong as written. | THEOREM/EXACT | THEORY_ERRATA E15-1; exact rational check N < 40; adaptive-rule simulation |
| 2 | Three smaller Week 14 theory errors corrected (front size 14.7 not 11; D4 tightness; O1a implied set). | THEOREM/EXACT | THEORY_ERRATA |
| 3 | Week 14's true-boundary headroom is mostly not label peeking: an expectation oracle (knows the truth, not the label realization) beats margin by 0.050/0.074/0.076 NSD AULC; peeking adds 0.003/0.000/0.028. | CONTROLLED SYNTHETIC (dev) | development/oracle_decomposition.csv |
| 4 | The headroom is large on held-out cells too (expectation oracle 0.602 vs margin 0.399; 0.40 vs 0.08). | CONTROLLED SYNTHETIC (held-out reference) | heldout/oracle_E_reference.csv |
| 5 | Edge-mismatch count = cut of the error set (B1); uniform-cloud surrogate estimates the nonlocal perimeter / boundary Dice deficit (B2). | THEOREM/EXACT + THEOREM | THEORY_WEEK15 |
| 6 | Unnormalized expected boundary mismatch prefers erasing an uncertain boundary (B3); this explains EBR's development collapse (0.267 vs 0.747). | THEOREM/EXACT + CONTROLLED SYNTHETIC | test_B3; development |
| 7 | Oracle headroom decomposes into peeking ≥ 0, truth knowledge ≥ 0 and a method gap (B4, one step). | THEOREM | THEORY_WEEK15 |
| 8 | No legal criterion tested (margin, BALD, VSUR, EBR-D) ranks candidates like the oracle (|ρ| ≤ 0.27). | CONTROLLED SYNTHETIC (dev) | oracle_alignment.csv |
| 9 | In a well-specified GP world the exact one-step Bayes look-ahead captures ≈ 24% of the oracle's per-step gain; margin's per-step gain is negative; EBR-D ≈ half of Bayes; over paths EBR-D/Bayes ≈ +0.01 NSD AULC and lower ASSD than margin. | CONTROLLED SYNTHETIC (dev) | bayes_frontier.csv, wellspec_*.csv |
| 10 | **EBR-D fails the frozen criteria** (better than margin in 7/16 held-out cells; mean −0.0095 NSD; catastrophic cells rough σ = 1 (−0.092) and Branin σ = 0 (−0.068)). Verdict NO NEW METHOD JUSTIFIED. | CONTROLLED SYNTHETIC (frozen held-out) | heldout/VERDICT.json |
| 11 | EBR-D acquires far fewer flipped labels than margin in noisy cells (e.g. 0.07 vs 0.37) without a corresponding NSD gain. | CONTROLLED SYNTHETIC (held-out) | cell_contrasts.csv |
| 12 | Boundary target beats volume target inside the same look-ahead (EBR-D − VSUR = +0.010 NSD on average), but both trail margin. | CONTROLLED SYNTHETIC (held-out) | VERDICT.json |
| 13 | Historical q20 accuracy agrees in sign with the true-boundary NSD contrast (EBR-D − margin) in only 62.5% of held-out cells (BA 75%). | CONTROLLED SYNTHETIC (held-out) | failure analysis |
| 14 | DC-BD reduces density sensitivity relative to the unweighted r-graph in every held-out smooth cell but fails the pre-registered comparisons with q20 accuracy (M-a) and in one cell M-b. | CONTROLLED SYNTHETIC (held-out) | METRIC_VERDICT.json |
| 15 | Real-data replays (see report §G) are descriptive only and cannot change the verdict. | HISTORICAL OLD / POST-HOC NEW / EXTERNAL | real_data/ |
| 16 | A calibration-gated hybrid (EBR-D only when the posterior is well specified) could be useful. | SPECULATIVE (not tested) | — |

## Claims that must not be made
- That EBR-D (or any Week 15 acquisition) is better than margin in general, or validated on NEW.
- That DC-BD is density-free or should replace q20.
- That the oracle headroom is attainable by non-cheating methods (only a small part is, in well-specified worlds).
