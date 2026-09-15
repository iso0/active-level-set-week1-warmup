# RESEARCH_DIAGNOSIS — what is actually blocking sample efficiency

Scope: independent reconstruction from the research branch `codex/week9-phase1-19b-prospective-robust-monotone-pool-lse` at commit `bf4782881bc27fe1ec5256dc3ba0516478a1ed13` (public GitHub repository `iso0/active-level-set-week1-warmup`) plus new computations on the frozen 405-case population. Every new number in this document was computed in this session from the committed population table, the committed 100 outer splits (20 repeats × 5 grouped folds), the committed Phase 1.14 M3-margin query paths, and the committed M3 implementation (`src/week9_phase1_11…`, `…1_13…`, `…1_14…`). Development data only; no new-pool label was read.

## 0. Reproduction gate

Before any new claim I re-ran one Phase 1.14 trajectory (`w85__r01_f01`) through the repository's own M3 + margin code path: the 80-query path matched the committed `m3_margin_paths.csv.gz` exactly (80/80) and the Fold-B1-q20 AULC 16–80 reproduced to 0.8920036764705884 (committed 0.89200368). The evaluation harness used below is therefore the repository's, not a re-implementation.

## 1. Reconstructed evidence chain (verified from committed artefacts)

| Claim in the brief | Committed artefact | Verified value | Status |
|---|---|---|---|
| A. Binary GPC margin beats matched Random, q20 AULC 16–80 | `outputs/week8_5_frozen_confirmation/final_results_narrative.md` | 0.8135 vs 0.7762, Δ=+0.0373, 95% [+0.0301, +0.0444], 20/20 repeats positive | VERIFIED |
| B. M3 beats H on the same A0 path | `week9_phase1_13…/FINAL_PHASE1_13_REPORT.md` | H 0.830813, M3 0.842491, Δ=+0.011677 [+0.007201, +0.016149]; early (16–40) +0.0044, late (41–80) +0.0161 | VERIFIED |
| C. M3-margin vs M3-on-A0 | `week9_phase1_14…/FINAL_PHASE1_14_REPORT.md` | +0.002132 [−0.001167, +0.005621]; early −0.0016 [−0.0075, +0.0041]; late +0.0045 [+0.0001, +0.0090]; B40 q20 KH-recall −0.0237 | VERIFIED |
| D/E. Residual redundant with margin | `week9_phase1_15a…` | correction magnitude vs margin ρ=−0.951; A0/A1 score ρ=+0.983 | VERIFIED |
| D/E. Repulsion, five scales | `week9_phase1_16…` | all five q20 intervals include zero; early ΔAULC +0.002…+0.006 (unresolved); q30 small positive | VERIFIED |
| D/E. Ranking distinctness audit | `week9_phase1_18a…` | straddle ρ=0.9991, EMI 0.9872, PA-TVR 0.9772 vs margin; SMOCU/SUR approximations distinct but invalid as implementations | VERIFIED |
| D/E. Exact-fixed finite-pool p(1−p) SUR | `week9_phase1_18b…` | −0.001379 [−0.003801, +0.000726]; physics-refit SUR −0.004453, path Jaccard 0.662 | VERIFIED |
| E. Monotone structure and its propagation | `week9_phase1_19a/b…` | 22,050 comparable pairs, 3 violations; hard propagation harmed BA-AULC (−0.0096 … −0.0132, all Holm p≈0) | VERIFIED |
| F. Stage-1 separability at B16 | `week9_phase1_19a…` + `…1_13/physics_mean_fit_diagnostics.csv.gz` | 55% exactly separable at B16; slope median 21.0 per revealed-sd of log h at B16, 6.5 at B24, 4.2 at B40, 3.9 at B80 | VERIFIED |
| F. M4 marginalised slope: no acquisition gain | not on any public branch | user-reported 0.8411 vs 0.8418 | NOT VERIFIABLE (treated as reported only, per user instruction) |
| G. DA-LSE / depth-latent | not on any public branch (Week 7 depth regressor is: q20 error 0.200 vs 0.176) | — | NOT VERIFIABLE beyond Week 7 |
| H. Saturation table | recomputed from `week9_phase1_18a…/candidate_scores_pre_reveal.csv.gz` | remaining band: 60.8/52.9/45.1/37.3/20.4/8.3 at B16/24/32/40/60/80 (band = [min KH h, max C h], 82 rows); candidates with 0.2<p<0.8: 25.9/22.4/19.1/16.5/1.3/0.1 | VERIFIED (band count 82 vs memo's 83: edge convention) |
| I. Full-label classifiers plateau ≈0.80–0.86 in the band; all 405 contexts unique | new computation, §3 | plateau 0.83–0.86 on q20; 405/405 unique (VX,LS,ST); 394/379/379 unique VX/LS/ST | VERIFIED |
| J. Configuration/TE does not explain band exceptions | new computation, §3 | adding one-hot configuration + TE to the full-label models changes q20 accuracy by −0.005…+0.006 | VERIFIED for the global covariate form; but see §4.4: all 3 KH of the 27-row alternative configuration are persistent exceptions |

Numbers in the brief that I could not trace to committed artefacts (M4, DA-LSE) are carried as user-reported and play no role in any decision below.

## 2. The central new measurement: the q20 endpoint has a hard, data-determined ceiling that M3 reaches by B60

For each of the 100 committed outer runs I trained on **all 324 training labels** and evaluated on the 81 held-out rows (`results/diag_ceiling_summary.csv`). This is the best any method can do with the labels available in the pool:

| Model (all 324 training labels) | q20 accuracy | q30 | full81 | q20 KH recall |
|---|---:|---:|---:|---:|
| M3 (repository implementation) | **0.8565** | 0.9012 | 0.9683 | 0.719 |
| GPC ARD Matérn-3/2, wide bounds, (log h, log VX, log LS, ST) | 0.8406 | 0.8852 | 0.9620 | 0.751 |
| free-exponent logistic (log P, log VX, log LS, ST) + cfg + TE | 0.8388 | 0.8796 | 0.9623 | 0.747 |
| H (log h logistic) | 0.8329 | 0.8756 | 0.9614 | 0.703 |
| free-exponent logistic | 0.8324 | 0.8760 | 0.9610 | 0.708 |
| Random forest (500) | 0.8282 | 0.8780 | 0.9623 | 0.717 |
| SVC-RBF / GBM / kNN5 / kNN1 | 0.810 / 0.809 / 0.777 / 0.718 | | | |
| Threshold-surface probit GP T with frozen hyperparameters (§MATHEMATICAL_DEVELOPMENT) | 0.859–0.862 (40 folds) | | 0.9685 | |
| Censored-depth level-set model using all 324 depths (D*=95–105 µm) | 0.853 (8 folds) | | 0.965–0.968 | |

The committed M3-margin learning curve reaches q20 = 0.846 at B40, 0.856 at B60 and 0.861 at B80 — i.e. **M3 with 80 margin-selected labels is already at its own 324-label ceiling** (0.8565); the margin-selected training set is marginally better than all 324 labels because far points do not perturb the Stage-1 logistic.

Mean gap between the M3-margin curve and the M3 ceiling: 0.0706 at B16, 0.0394 at B24, 0.0224 at B32, 0.0100 at B40, 0.0000 at B60, −0.0047 at B80. Averaged over windows: **0.0309 over B16–40, 0.0255 over B16–48, 0.0122 over B16–80, 0.0005 over B41–80.**

Consequences:

1. Any acquisition rule paired with M3 has at most ≈0.012 of AULC 16–80 to gain, and essentially nothing after B41. The primary endpoint used since Week 8.5 dilutes any early effect with 40 budgets of structurally zero headroom (the memo's inequality |ΔAULC| ≤ (B_s−16)/64·sup|ΔL| is now an equality with B_s≈50). The observed nulls of Phases 1.14, 1.16, 1.18B (|Δ| ≤ 0.0045) are consistent with this bound and do not require a defective acquisition to explain them.
2. The place where a label-free method can still act is B16–B40. There the gap to the 324-label classifier is 0.031. **Correction added after the oracle experiment (OLD_DATA_RND_REPORT §7): the 324-label ceiling is not an upper bound for selected training subsets — a test-label oracle reaches 0.93 by B24, i.e. +0.095 over margin at 16–40 — so the true bound on what a policy could gain early is at least three times larger than 0.031; the ceiling remains the correct reference for what full information gives on average, and for the late window, where every label-free policy converged to it.**
3. "Saturation" of model-uncertain candidates at B60 (1.3 candidates with 0.2<p<0.8 while ≈20 physical-band candidates remain) is not depletion of useful points: the model has converged to its ceiling, so the remaining band points carry no value under any smooth 4-input model.

## 3. Where the ceiling comes from: 13 persistent exception cases

Per point, across the 20 test folds each point occupies, the full-label M3 error rate (`results/diag_fulltrain_pointwise.csv`): 13 of 405 points are misclassified in ≥50% of full-label fits (10 of them in 100%). They occupy **14.1% of all q20 evaluation slots** and the mean full-label q20 error is 14.35%: the q20 ceiling is entirely these points. Composition:

| Group | Points | Evidence |
|---|---|---|
| Late-onset Keyhole (sequence Conduction → Keyhole; KH only late in the scan) at log h 20.36–20.76 | 6 of the 9 late-onset KH in the population (row idx 287, 299, 192, 384, 201, 199) | all 9 late-onset KH lie in the `old-data-local`/`old-data-remote-clean` partitions, none in `new-data`; immediate-onset KH (64) have full-label error 0.055, late-onset 0.667 |
| Transient Keyhole (4–19 KH frames, before T0) | 3 (idx 68, 108, 126) | median KH frames of persistent exceptions 25.5 vs 100 for correctly classified KH |
| Conduction with max depth at the empirical depth separator (105–112 µm) | 2 (idx 119, 157) | best single depth threshold separates labels at 99.75% (1 exception, depth 111.2 µm KH); these C cases sit exactly at it |
| Conduction at log h 20.84 inside a KH neighbourhood | 1 (idx 377; depth 75 µm) | — |
| Alternative simulation configuration (`XI=−0.0002, XF=0.0012, XL=0.0014, TE=0.00125`; 27 rows, ST=300 K, LS=45 µm) | all 3 KH of that configuration are among the exceptions (192, 199, 201) | a configuration covariate cannot learn 3 positives; hypothesis J is true globally but false for this subgroup |

Interpretation: the irreducible near-boundary error is a label-definition/provenance phenomenon (ever-observed KH with late or transient episodes; depth-marginal cases; a small alternative-configuration campaign), not an input-resolution limit in the usual sense. The Week 7 audit records that annotator identity for the old partitions is undocumented ("working-student subset not reliably identifiable"; label_1/label_2 disagreement flags exist). The supervisor's new labels are a single-annotator, single-campaign product; this matters for the predictions in `SATURATION_PREDICTIONS.md`.

## 4. Candidate bottleneck table

| Bottleneck | Verdict | Evidence |
|---|---|---|
| **Evaluation mismatch / endpoint dilution** (AULC 16–80 spends 62% of its weight where no headroom exists) | **SUPPORTED, rank 1** | §2: gap 0.0005 over B41–80 vs 0.0309 over B16–40; committed nulls all satisfy the resulting bound |
| **Input-space resolution ceiling** (in the form "labels of near-boundary cases are not predictable from (P,VX,LS,ST) by any smooth model") | **SUPPORTED, rank 2**, but with a specific mechanism: 13 exception cases, dominated by late/transient-onset KH in the old campaigns and depth-marginal C cases | §3; 8 model classes, ±cfg/TE, and a depth-augmented model all plateau at 0.83–0.86 |
| **Posterior overconfidence (early)** | **PARTIALLY SUPPORTED** | on the saved Phase 1.18A M3 states, among physical-band candidates with p≤0.1 or ≥0.9, the confidently wrong count is 6.8 (of 30.5 confident) at B16, 3.5/26.9 at B24, 0.5/14.6 at B40, 0.01/8.1 at B80; Stage-1 slope median 21 at B16 → 3.9 at B80. It is real at B16–24 and gone by B40; it cannot explain late nulls |
| **Wrong uncertainty object (p vs π)** | **NOT SUPPORTED as the missing reason under M3; SUPPORTED as a structural property of M3 that makes every "uncertainty-aware" M3 acquisition collapse to margin** | Spearman between p-margin and π-margin rankings on the same states: 0.816 (B16), 0.867 (B24), 0.979 (B32), 0.992 (B40), 0.98 (B60–80). Number of π-uncertain candidates (0.2<π<0.8): 9.0/7.9/5.3/2.6/0/0. See §5 for the mechanism |
| **Model bias of M3** | **NOT SUPPORTED at full information** (M3 is the best of nine model classes at its ceiling); **PARTIALLY SUPPORTED early** (B16 = H with a hard step; see OLD_DATA_RND_REPORT for the same-path early curves) | §2, §5 |
| **Pool support / depletion** | **PARTIALLY SUPPORTED** — true that useful candidates vanish, but because the model converges, not because band points run out (20 remain at B60) | §2, brief H |
| **Graph misspecification** (single crossing in log h) | **NOT SUPPORTED** | a graph-restricted threshold GP with frozen hyperparameters reaches the same ceiling as M3 (0.859–0.862 vs 0.8565) |
| **Missing/latent simulator variables; configuration/window** | **PARTIALLY SUPPORTED** — global covariates do nothing; the alternative configuration and late-onset episodes (window-length sensitive by definition of an "ever-KH" label) are where the exceptions live | §3 |
| **Finite-pool objective** | PARTIALLY SUPPORTED — the pool sum over unqueried candidates is a moving reference; under M3 it does not change the ranking materially (1.18B: revealed-set Jaccard P1/P0 0.964) | 1.18B |
| **Auxiliary-output information** | **NOT SUPPORTED for the ceiling** (all-depth censored model 0.853 vs M3 0.868 on the same 8 folds); early-budget value tested in OLD_DATA_RND_REPORT | §2 |
| **Context uniqueness (no exact power sweeps)** | VERIFIED as a fact (405 unique contexts), but not a bottleneck by itself: the GP over context pools neighbours; the graph model reaches the ceiling | §1 |

| **Training-set selection sensitivity of the endpoint** (found last, OLD_DATA_RND_REPORT §7) | **SUPPORTED, and larger than everything else** | a test-label greedy oracle reaches q20 0.93 by B24 (above the 324-label ceiling) and gains +0.095 AULC 16–40 over margin on the same runs; adding margin-selected labels afterwards *lowers* q20 to 0.875. The exceptions are locally clustered, so which labels are in the training set moves q20 by ±0.1; policy contrasts are ±0.005 |

Ranking of what blocks *measured* sample efficiency: (1) endpoint dilution over a zero-headroom window; (2) the exception ceiling; (3) early overconfidence of the near-unregularised physics slope; (4) the M3 latent-scale structure that neutralises every uncertainty-aware acquisition (next section). Items (1)–(2) are not fixable by acquisition; item (3)–(4) are fixable by the model, and only in B16–B40.

## 5. Why every M3-based acquisition reduced to margin (mechanism)

M3's latent is f = a + b·s(ℓ) + r(x) with b the near-unregularised logistic slope (median 21 at B16, 6.5 at B24, ≈4–5 from B32 on, per revealed-sd of log h; the revealed sd shrinks from 0.87 to 0.51 as margin concentrates queries, so in absolute log-h units the slope is ≈7–8 from B32) and r a residual with prior sd capped at 1 (the cap is hit in 58–86% of fits from B24). The Laplace latent variance of candidates is therefore nearly constant across candidates (median 0.73–0.87 from B24) and small relative to |m| (median |m| 8–54). Every acquisition of the form g(|m|, v) with v ≈ const is a monotone function of |m|, i.e. of margin: straddle 1.96σ−|m| (ρ=0.9991), EMI (0.9872), the residual correction (−0.951), local variance-reduction gates (0.977). The exact finite-pool p(1−p) SUR (1.18B) differs from margin only through cross-covariances, which under a capped residual with two length scales at their upper bound (l_P, l_LS, l_ST → 100 at B24–60; only l_VX ≈ 0.43–0.53 is informative) are a near-1-D function of VX; that SUR changed 3.6% of the revealed set and nothing in q20.

The boundary-location uncertainty implied by M3 is (residual sd)/(slope) ≈ 1/7.6 ≈ 0.13 log-h units at B32+ and ≈ 0.05/21 at B16, against an empirical contextual spread of the boundary of sd 0.17 log-h units (posterior mean of the threshold model fitted to all 405 labels) and a physical overlap band 0.89 wide. M3's residual is amplitude-starved and its uncertainty is not expressed in boundary units — it cannot tell an acquisition rule *where along the boundary* the location is unknown.

## 6. What is actually blocking sample efficiency (summary)

- The primary endpoint cannot register acquisition differences after ≈B50 because the model has reached the data ceiling; 16–80 AULC contrasts are diluted ≈2.5× relative to 16–40.
- The ceiling itself is set by 13 label-definition exception cases (3.2% of the population, 14% of q20 slots), concentrated in the old campaigns and the alternative configuration. No 4-input model and no auxiliary output moves it on the old pool.
- In the only window with headroom (B16–40, 0.031 full-information), M3 starts as a hard step in log h with a separable Stage-1 slope and no boundary-location uncertainty; every uncertainty-aware rule then reduces to margin.
- Two exact results (MATHEMATICAL_DEVELOPMENT §9) close the acquisition side: for a deterministic simulator, margin is exactly the information-optimal one-step rule (Prop. 1), and any coherent set-directed rule can beat it only through reference decisions the outcome would actually flip, each worth at most the query's own margin (Prop. 2). The exact Bayes-optimal transductive 0-1 rule, implemented with Owen's T, loses to margin by 0.03 on the endpoint because its expected flips lie where a 16–40-label posterior is not calibrated.
- What remains is model-side: the oracle shows the endpoint is dominated by which labels the training set contains and that queried exceptions poison neighbours under a smooth global-amplitude likelihood. The lever with real headroom is a likelihood that can discount locally conflicting labels, not a new acquisition. `OLD_DATA_RND_REPORT.md` reports the tests; `FINAL_DECISION.md` §I′ states the redirection.
