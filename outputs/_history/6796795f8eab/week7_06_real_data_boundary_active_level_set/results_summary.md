# Week 7 Phase 6 — Real-data boundary and active level-set results

This report uses Ioan's manual experiment-level Keyhole label as the reference. Maximum depth is an unchanged physical response, not a replacement label, and its learned threshold is not a universal physical constant.

1. **Primary population:** 405 simulations.
2. **Class composition:** 73 Keyhole and 332 non-Keyhole.
3. **Semantic consistency:** broadly yes for an experiment-level ‘Keyhole at least once’ reference: 60/73 positives place max depth inside a saved-Keyhole episode span, but this is an interval proxy rather than an exact morphology join.
4. **Timing/artifact caution:** only 4/405 maxima coincide with a saved labelled frame; 12 positives peak after their last saved Keyhole frame and one between spans. The deterministic raw review found 0/16 isolated-spike candidates, so no dominant obvious spike mechanism was found, but sparse timing alignment remains important.
5. **Max-depth predictability:** held-out Matérn-3/2 GPR RMSE = 21.691 µm and R² = 0.921.
6. **Binary predictability:** held-out Matérn-3/2 GPC balanced accuracy = 0.919, with q20/q30 errors 0.176/0.126.
7. **Static global comparison:** mixed. Max-Depth has higher balanced accuracy and sensitivity (0.949/0.952 versus 0.919/0.855), while Binary has lower global error (0.040 versus 0.053).
8. **Static q20:** Binary is better: error 0.176 versus Max-Depth 0.200.
9. **Static q30:** Binary is also better: error 0.126 versus Max-Depth 0.152.
10. **Transient Keyhole:** Max-Depth is more sensitive (0.973 versus 0.916), but its persistent-case sensitivity is also higher (0.947 versus 0.840); the advantage is not transient-specific.
11. **Online threshold stability:** reasonably stable within runs but not universal. Final max_depth_straddle thresholds have mean 110.043 µm, standard deviation 1.878 µm, and range 108.141–113.740 µm.
12. **Queries before threshold stability:** median 20.5 queries under the declared ‘all later values within max(2 µm, 5%) of final tau’ rule.
13. **Best Max-Depth acquisition:** max_depth_straddle.
14. **Best Binary acquisition:** binary_uncertainty_repulsion.
15. **Max-Depth versus random:** yes on q20 AULC; active-minus-random = -0.032, descriptive 95% interval [-0.063, -0.003].
16. **Binary versus random:** yes on q20 AULC; active-minus-random = -0.043, descriptive 95% interval [-0.071, -0.014].
17. **q20 AULC:** Binary is lower in the mean (0.186 versus Max-Depth 0.205), but the Max-minus-Binary paired interval [-0.018, 0.055] crosses zero.
18. **q30 AULC:** Binary is lower in the mean (0.133 versus Max-Depth 0.151), but the paired interval [-0.008, 0.044] crosses zero.
19. **Balanced-accuracy AULC:** Max-Depth is higher (0.943 versus Binary 0.917); the Max-minus-Binary interval [0.011, 0.043] stays positive.
20. **Queries to useful performance:** target-dependent. For BA ≥ 0.90, Max-Depth reaches in median 14.0 queries in 20/20 runs versus Binary 16.0 in 19/20; for q20 error ≤ 0.20, Max-Depth reaches 15/20 and Binary 18/20.
21. **Stability across matched runs:** the q20/q30 cross-formulation intervals cross zero, whereas balanced-accuracy AULC consistently favours Max-Depth. Both selected active methods improve over their shared random baselines. Intervals remain descriptive because repeated-CV runs reuse simulations.
22. **Domain shift:** this weakens a Max-Depth-only conclusion. The all-route BA floors are Binary 0.746 and Max-Depth 0.516; all-old→new is 0.538 versus 0.904, while new→all-old reverses direction (0.926 versus 0.746). All transfer routes are secondary stress tests.
23. **G3 after Max-Depth:** it adds no robust primary advantage on the matched 404 rows: q20 AULC is G3 straddle 0.254, common Max-Depth straddle 0.233, and Binary margin 0.179. G3 remains secondary.
24. **Boundary disagreement:** yes, in specific supported descriptive slices; disagreement spans 4.9%–7.1% of supported grid cells. These full-data slices are not held-out physical truth.
25. **Final formulation decision:** **HYBRID / NO CLEAR WINNER** — The q20/q30 hierarchy, paired descriptive uncertainty, balanced-accuracy support, or semantic/domain evidence does not jointly justify a single formulation.

## Hard stop

Phase 6 is intentionally uncommitted and unpushed. No labels were changed, no target was redefined, and no Phase 7 work was started.
