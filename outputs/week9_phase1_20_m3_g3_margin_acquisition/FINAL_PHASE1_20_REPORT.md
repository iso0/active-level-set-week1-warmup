# Week 9 Phase 1.20 — M3 evaluator with sequential G3-margin acquisition

Decision: **G3_SELECTOR_SMALL_OR_UNRESOLVED**. This frozen offline finite-pool experiment does not support replacing M3-margin with G3-margin.

## Direct answers

1. **Is P2 different from A0?** Yes. The source audit verifies that Week 8.5 uses an isotropic Matérn-3/2 GPC, whereas Phase 1.12 G3 uses four ARD length scales. Exact fitting and prediction functions are imported, including bounds, fallbacks, preprocessing and seeds.
2. **Did query paths differ?** Against P1, mean prefix Jaccard is 0.520 at B40 and 0.620 at B80; 100% of B80 sequences differ. Active-only B40 Jaccard is 0.314. These describe path differences without establishing a causal mechanism. The first 16 points are identical in every run. P2 was generated live from revealed labels, not replayed from A0.
3. **Did P2 outperform P1?** M3 evaluated on P2 had lower mean early performance than M3 evaluated on P1: -0.002560 (95% repeat-block interval [-0.010570, +0.005446]); 9/20 repeat blocks positive. The interval includes zero, so the direction remains unresolved. The final recommendation also applies the frozen practical threshold.
4. **How large is the early difference?** -0.002560 normalized AULC, equivalent to -0.256 percentage points averaged over B16–B40.
5. **95% interval?** [-0.010570, +0.005446], percentile bootstrap of 20 paired repeat means, 10,000 draws.
6. **Positive repeats?** 9/20, retaining each repeat's five folds together.
7. **Full B16–B80 vs P1?** -0.007014 (95% repeat-block interval [-0.011681, -0.002494]); 7/20 repeat blocks positive.
8. **Versus P0?** Early: -0.005724 (95% repeat-block interval [-0.012324, +0.000581]); 7/20 repeat blocks positive. Full: -0.005839 (95% repeat-block interval [-0.010089, -0.001525]); 6/20 repeat blocks positive.
9. **Safest thesis interpretation?** With the same M3 evaluator and frozen splits, these results measure acquisition-path performance on the offline 405-simulation population. They establish no prospective simulator savings, external validity, causal mechanism or superiority of G3 as a predictive model.
10. **Replace the incumbent?** No. Retain M3-margin as the acquisition incumbent on this evidence.

## Design and evidence

P0 loads the exact Week 8.5 A0 trajectory. P1 loads the validated Phase 1.14 M3-margin trajectory. P2 fits the exact Phase 1.12 standalone G3 at each budget B16–B79 and selects the unqueried training-pool row minimizing |p_G3−0.5|, with smallest population row index resolving ties. The oracle reveals that label only after selection. M3 is refit on each prefix and evaluates the untouched 81-row test set at every integer budget B16–B80.

Population: 405 rows, 73 Keyhole, 332 Conduction. Inputs: P, VX, LS, ST (substrate temperature). has_keyhole means any observed frame has Keyhole behavior. All 100 stored grouped outer splits and initial designs are preserved; each run has 324 pool rows and 81 test rows. The historical loader deterministically reconstructs split objects, and every membership is checked against the persisted split manifest. No new split is selected.

The selector interface contains only training-pool features, training row IDs, revealed row IDs and labels, run ID and budget. Test features, test labels, hidden candidate labels and q20/q30 flags are absent. The q20/q30 subsets retain their frozen evaluation-only definitions. Candidate probability tables allow independent checking of all 6,400 choices.

**Endpoint distinction:** Earlier quoted values (H≈0.830813, G3≈0.826595, P0≈0.842491, P1≈0.844623) are accuracy AULCs. This phase's primary endpoint is balanced accuracy as requested. Both metrics are supplied at checkpoints; the historical accuracy values must not be compared numerically with the new balanced-accuracy endpoint.

Normalized trapezoidal AULC is the integral of balanced accuracy divided by 24 for B16–B40 or 64 for B16–B80. Higher is better. The only primary inference is P2−P1 on early q20. P2−P0 and q30/full-budget intervals are secondary descriptive robustness checks, with no new global multiple-testing family. Phase 1.14 has no sign-flip test; its bootstrap function and deterministic seed framework are reused exactly.

The pre-result practical threshold is 0.01 AULC. SUPPORTED requires a mean at least +0.01 and lower interval bound above zero. NOT_SUPPORTED requires a mean at most −0.01 and upper bound below zero. Remaining cases are SMALL_OR_UNRESOLVED. This threshold is an operational decision convention, not an established economic simulator-savings threshold.

## AULC estimates

| model   | subset   |   end_budget |   mean_AULC |   ci_lower |   ci_upper |
|:--------|:---------|-------------:|------------:|-----------:|-----------:|
| P0      | B1_q20   |           40 |    0.810516 |   0.802044 |   0.818795 |
| P0      | B1_q20   |           80 |    0.821939 |   0.814583 |   0.829293 |
| P0      | B1_q30   |           40 |    0.845702 |   0.839238 |   0.852251 |
| P0      | B1_q30   |           80 |    0.857231 |   0.852074 |   0.86235  |
| P1      | B1_q20   |           40 |    0.807353 |   0.800365 |   0.814203 |
| P1      | B1_q20   |           80 |    0.823115 |   0.815952 |   0.83028  |
| P1      | B1_q30   |           40 |    0.844933 |   0.84045  |   0.849247 |
| P1      | B1_q30   |           80 |    0.860067 |   0.855933 |   0.864091 |
| P2      | B1_q20   |           40 |    0.804793 |   0.794009 |   0.814363 |
| P2      | B1_q20   |           80 |    0.8161   |   0.809128 |   0.822971 |
| P2      | B1_q30   |           40 |    0.839602 |   0.830957 |   0.847349 |
| P2      | B1_q30   |           80 |    0.851259 |   0.846298 |   0.85638  |

## Paired contrasts

| contrast   | subset   |   end_budget |   mean_difference |    ci_lower |     ci_upper |   positive_repeat_blocks |   zero_repeat_blocks |   bootstrap_draws |       seed | inference_role        |
|:-----------|:---------|-------------:|------------------:|------------:|-------------:|-------------------------:|---------------------:|------------------:|-----------:|:----------------------|
| P2-P1      | B1_q20   |           40 |       -0.00256001 | -0.01057    |  0.00544599  |                        9 |                    0 |             10000 | 2286804453 | primary               |
| P2-P0      | B1_q20   |           40 |       -0.00572358 | -0.0123242  |  0.000581398 |                        7 |                    0 |             10000 | 2599148892 | secondary descriptive |
| P2-P1      | B1_q20   |           80 |       -0.00701444 | -0.0116813  | -0.00249444  |                        7 |                    0 |             10000 | 1320338375 | secondary descriptive |
| P2-P0      | B1_q20   |           80 |       -0.0058391  | -0.0100888  | -0.00152502  |                        6 |                    0 |             10000 | 3326407179 | secondary descriptive |
| P2-P1      | B1_q30   |           40 |       -0.00533126 | -0.0118331  |  0.0012504   |                        6 |                    0 |             10000 | 3560789404 | secondary descriptive |
| P2-P0      | B1_q30   |           40 |       -0.00610044 | -0.0112648  | -0.000960766 |                        6 |                    0 |             10000 | 2090614420 | secondary descriptive |
| P2-P1      | B1_q30   |           80 |       -0.00880755 | -0.012533   | -0.00518352  |                        3 |                    0 |             10000 | 1409692847 | secondary descriptive |
| P2-P0      | B1_q30   |           80 |       -0.00597225 | -0.00937568 | -0.00269561  |                        4 |                    0 |             10000 | 2701655718 | secondary descriptive |

## Path mechanisms

| contrast   |   budget |   prefix_jaccard |   active_only_jaccard |   different_sequence |
|:-----------|---------:|-----------------:|----------------------:|---------------------:|
| P2-P0      |       24 |         0.559858 |             0.0863916 |                    1 |
| P2-P0      |       40 |         0.536657 |             0.334399  |                    1 |
| P2-P0      |       80 |         0.71375  |             0.656981  |                    1 |
| P2-P1      |       24 |         0.550224 |             0.0714432 |                    1 |
| P2-P1      |       40 |         0.520285 |             0.314178  |                    1 |
| P2-P1      |       80 |         0.620217 |             0.548892  |                    1 |

Jaccard is intersection size divided by union size. Prefix overlap includes the shared initialization; active-only overlap excludes it. Revealed Keyhole counts/fractions and selector margins are in their companion tables. Margins diagnose each selector only: G3 and M3 probabilities must not be assumed equally calibrated. Phase 1.14 contains no equivalent standardized coverage diagnostic, so no new spatial mechanism study is added.

Revealed class composition (counts are means over runs):

| model   |   budget |   keyhole_count |   keyhole_fraction |
|:--------|---------:|----------------:|-------------------:|
| P0      |       16 |            5.17 |           0.323125 |
| P0      |       24 |            9.44 |           0.393333 |
| P0      |       40 |           17.37 |           0.43425  |
| P0      |       80 |           29.06 |           0.36325  |
| P1      |       16 |            5.17 |           0.323125 |
| P1      |       24 |            9    |           0.375    |
| P1      |       40 |           16.43 |           0.41075  |
| P1      |       80 |           32.08 |           0.401    |
| P2      |       16 |            5.17 |           0.323125 |
| P2      |       24 |            8.74 |           0.364167 |
| P2      |       40 |           15.89 |           0.39725  |
| P2      |       80 |           27.76 |           0.347    |

Exact-fit diagnostics (all warnings and per-fit details remain in the compressed table):

| model   |   fit_count |   fallback_count |   optimizer_converged_fraction |   optimized_primary_fraction |   any_length_bound_fraction |
|:--------|------------:|-----------------:|-------------------------------:|-----------------------------:|----------------------------:|
| G3      |        6400 |                0 |                     nan        |                            1 |                    0.851719 |
| M3      |        6500 |                0 |                       0.919231 |                          nan |                    0.645231 |

M3 reports optimizer convergence for 91.923% of fits (525 of 6,500 fits are not declared converged). G3 and M3 used no fallbacks. These numerical diagnostics are retained as a limitation of the unchanged historical fitting procedure; passing parity gates does not mean every optimizer declared convergence. No alternate solver was substituted after inspecting results.

## Validation and reproducibility

The baseline gates reproduce stored G3 B16 test probabilities and M3 B24 test probabilities and next query. Final validation checks all B16 evaluator predictions across 100 runs, exact A0 parity with the original Week 8.5 checkpoint archive, stored split membership, P1 path identity, uniqueness, training-only eligibility, all candidate argmins, frozen subset flags and complete metrics. Old P0/P1 metrics are independently reconstructed from stored predictions and compared to Phase 1.14.

`input_provenance.json` pins input hashes and runtime versions. `fit_diagnostics.csv.gz` retains exact G3 fallbacks/warnings and M3 optimization diagnostics. The study does not replace or repair historical model implementations. Per-budget atomic checkpoints resume interrupted outer runs; sequential budgets within a run are never parallelized.

Figures: `figures/01_q20_learning_curve.png`, `02_early_q20_zoom.png`, `03_early_P2_minus_P1.png`, `04_early_P2_minus_P0.png`.
