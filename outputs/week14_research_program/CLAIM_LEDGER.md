# Week 14 claim ledger

Tags: **THEOREM/EXACT**, **CONTROLLED SYNTHETIC** (development or frozen held-out, stated),
**HISTORICAL OLD**, **POST-HOC NEW**, **EXTERNAL/PUBLIC** (Masinelli et al. 2025), **SPECULATIVE**.
"Known" marks results that restate prior work.

## Discovery (cold start)

| # | Claim | Tag | Evidence |
|---|---|---|---|
| D-1 | Under an exchangeable rare-set prior no query rule (adaptive or not) beats or loses to random sampling in discovery law. | THEOREM/EXACT | THEORY D1; test_D1 |
| D-2 | A label-blind design certifies discovery of every rare region with pure radius > r iff its fill distance ≤ r; minimax cost lies in [(N(2r)+1)/2, N(r)]. | THEOREM/EXACT | THEORY D2; test_D2 |
| D-3 | Under monotone labels the Pareto fronts contain both classes; minimax cost Θ(|Min|+|Max|), polylog in n for product designs. | THEOREM/EXACT (fact elementary) | THEORY D3; test_D3 |
| D-4 | Interleaving J orders costs at most a factor J relative to the best. | THEOREM/EXACT (known construction) | THEORY D5; test_D5 |
| D-5 | On a held-out monotone family the order certificate costs 2.0 queries at d = 2, 4, 6 while maximin costs 4.0–6.3 and random 13–17. | CONTROLLED SYNTHETIC (frozen held-out) | C1, P1–P2 |
| D-6 | Farthest-first can be worse than random for discovery (rare islands in the density bulk). | CONTROLLED SYNTHETIC (development + held-out) | C5; C1 P4 (two-islands, d = 4: 17.9 vs 14.8) |
| D-7 | On OLD-405 pools the order certificate and the log-h score both discover both classes in 2 queries (max 2). | HISTORICAL OLD | real_discovery.csv |
| D-8 | On Masinelli Ti64/316L with 1–3 minority bundles, the front order needs 2.0–2.5 queries on average (max 8) versus 8.4–16.4 for random and up to 35 for maximin. | EXTERNAL/PUBLIC | real_discovery.csv, R2 |
| D-9 | On NEW-136 the order certificate fails (max 21; 9/100 pools > 16) because the labels violate the order; the log-h score extremes need ≤ 7 and the three-way hedge ≤ 14 queries in all 100 pools, so either would have avoided the Week 11 single-class B16 STOP. | POST-HOC NEW | real_discovery.csv; R1 failed as pre-registered for FRONT |

## Physics in the model

| # | Claim | Tag | Evidence |
|---|---|---|---|
| P-1 | Signed dominance is exactly the order shared by all positive-exponent scaling laws. | THEOREM/EXACT (elementary) | THEORY O1 |
| P-2 | Encoding physics as a fixed mean (M3) or as the only predictor (H) is best in-domain and incurs large losses under shift (worst M3 − G3 = −0.19 BA, H − G3 = −0.26 on held-out synthetic cells). | CONTROLLED SYNTHETIC (frozen held-out) | C2, P6 |
| P-3 | The same pattern holds on real data: M3 − G3 = −0.121 (OLD→NEW) and −0.098 (NEW-only); M3 ≈ G3 in-domain on OLD (+0.002). | HISTORICAL OLD + POST-HOC NEW | real_models.csv |
| P-4 | Dominance-closure override (G3C) improves BA by +0.010 to +0.028 and NSD by +0.03 to +0.08 in shifted cells where the order is valid or locally violated (curvedMono, hartmannDev); it does not help in-domain. | CONTROLLED SYNTHETIC (frozen held-out) | C2, P5c |
| P-5 | G3C can hurt when an omitted coordinate modulates the rare boundary (twoRegimeST: BA −0.016 n.s., NSD −0.075 significant). Pre-registered P5a/P5b failed. | CONTROLLED SYNTHETIC (frozen held-out) | C2 |
| P-6 | Risk asymmetry: the worst G3C − G3 cell over all held-out synthetic and real settings is −0.023 BA, versus −0.19 to −0.26 for physics-as-level / physics-only. | CONTROLLED SYNTHETIC + real | fig3 |
| P-7 | On real data G3C helps within-material on Masinelli (+0.016/+0.020 BA at n = 10, zero closure errors), is neutral for OLD→NEW and Ti64↔316L, +0.006 on OLD in-domain, and hurts on NEW-only (−0.023; 11% of implied labels wrong). | EXTERNAL + HISTORICAL OLD + POST-HOC NEW | real_models.csv, anomaly_sensitivity.csv |
| P-8 | 64 of the 75 order violations on NEW-136 come from one non-Keyhole case at P 423 W, VX 0.332 m/s, LS 42 µm, ST 473 K; it is a candidate for a data-quality audit (not relabelled, not removed). | POST-HOC NEW | fig6 |
| P-9 | A strict monotone GP prior (probit virtual derivatives, small scale) lowers BA in imbalanced saturated regimes because it imposes a minimum slope. | CONTROLLED SYNTHETIC (development) | DEVELOPMENT_DESIGN, C10 |
| P-10 | Gating closure by the source-label violation rate would avoid the NEW harm. | SPECULATIVE (not tested prospectively) | — |

## Evaluation

| # | Claim | Tag | Evidence |
|---|---|---|---|
| E-1 | Every linear confusion metric orders two non-dominating predictors by a single precision threshold; accuracy vs BA reverse exactly on ρ ∈ (π, ½). | THEOREM/EXACT (known: ROC iso-performance) | THEORY E1 |
| E-2 | Cut-edge recall on r-graphs converges to a density-weighted soft boundary recall with tolerance ≈ edge length. | THEOREM (consistency) / heuristic (small-r expansion) | THEORY E2 |
| E-3 | Every finite-pool boundary metric tested (q20 accuracy, BA, BER, BEF1, kNN/Gabriel/r-graph) reverses the ranking of two equal-geometry predictors when the evaluation density moves. | CONTROLLED SYNTHETIC (development + held-out) | C3, fig4 |
| E-4 | Length-weighted Gabriel cut-edge recall reduces that density sensitivity in every held-out cell (2.5–3.3× in 3-D, 1.3× in 6-D) but does not uniformly improve rank agreement with ASSD (P7b failed in 3/12 cells). | CONTROLLED SYNTHETIC (frozen held-out) | C3 |
| E-5 | q20 accuracy and BER are blind to spurious regions away from the boundary; BEF1 is not. | CONTROLLED SYNTHETIC | C2 (counterexamples) |
| E-6 | OLD and NEW boundary scores are not comparable as boundary quality because their evaluation densities differ. | SPECULATIVE application of E-3 to real data | — |

## Acquisition headroom

| # | Claim | Tag | Evidence |
|---|---|---|---|
| H-1 | The full-pool model is not an acquisition ceiling (a finite-metric oracle exceeds it by 0.03–0.09 BA). | CONTROLLED SYNTHETIC (descriptive) | Study 4, C7 |
| H-2 | That oracle does not improve the true boundary (NSD below margin), whereas a true-objective oracle beats margin by +0.05 to +0.10 NSD: acquisition headroom on the estimand exists but is not identifiable from finite-pool metrics. | CONTROLLED SYNTHETIC (descriptive) | Study 4b, C8, fig5 |
| H-3 | The true-objective oracle avoids boundary-localized label noise (flipped acquired labels ≤ 2% vs 8–17% for margin). | CONTROLLED SYNTHETIC (descriptive); mechanism known | Study 4c |
| H-4 | BALD does not realize this headroom (worse than margin in the NEW-like cell). | CONTROLLED SYNTHETIC (development) | Study 5 |
| H-5 | Replace-one sensitivity bounds on acquisition gaps are vacuous for these GPCs. | CONTROLLED SYNTHETIC | Study 4 |
| H-6 | Week 13's "0.014 window" on OLD is a model-specific reference gap, not a ceiling. | HISTORICAL OLD + H-1 | — |

## Claims that must NOT be made

- That any Week 14 method is validated on NEW-136 (all NEW results are post-hoc).
- That closure override (G3C) is a generally safe improvement (it failed on NEW-only and on twoRegimeST).
- That the length-weighted metric solves density dependence or should replace q20.
- That acquisition "does not matter": headroom on the true boundary exists in the synthetic study.
- That the NEW anomaly is a mislabel (only that it is the dominant order violation and merits an audit).
- That the discovery theorems are deep or entirely new (see LITERATURE_NOVELTY_AUDIT.md).
