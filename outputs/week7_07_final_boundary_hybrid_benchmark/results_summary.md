# Week 7 Phase 7 — Final boundary-metric robustness and Hybrid acquisition benchmark

Manual experiment-level `has_keyhole` remains the regime ground truth. Maximum depth is physical side information from the same queried simulation; for Hybrid methods it affects acquisition only, while the primary prediction remains Binary GPC.

1. **Phase 6 publication:** yes. The exact commit is `5734de6f533e1de1e15a07de24e7d4e6e53bb6fa`; local, upstream, and remote were equal before Phase 7 began.
2. **Exact run reuse:** yes. All 20 Phase 6 primary outer runs, test folds, candidate pools, deterministic permutations, warm starts, and budget accounting were hash-verified.
3. **Boundary-region agreement:** B1/B2/B3 off-diagonal rank correlations span 0.3625–0.7135; q20 Jaccard spans 0.5140–0.6200. They overlap but are not interchangeable.
4. **Binary Phase 6 boundary advantage:** yes under all three definitions when compared with Max-Depth on mean q20 AULC.
5. **Hybrid Gate on B1 q20:** Gate 0.1943 versus Binary 0.1862.
6. **Hybrid Gate on B2 q20:** Gate 0.2110 versus Binary 0.1924.
7. **Hybrid Gate on B3 q20:** Gate 0.1959 versus Binary 0.1774.
8. **Hybrid Rank Fusion:** B1/B2/B3 q20 means are 0.1872, 0.1961, and 0.1835, compared with Binary 0.1862, 0.1924, and 0.1774.
9. **Preregistered robust-improvement rule:** hybrid_binary_gate20_max_depth_straddle: FAIL; hybrid_equal_rank_fusion: FAIL.
10. **q30 consistency:** rankings are B1: binary_uncertainty_repulsion (0.1332) < hybrid_equal_rank_fusion (0.1340) < hybrid_binary_gate20_max_depth_straddle (0.1438) < max_depth_straddle (0.1506) < shared_random_binary_head (0.1687); B2: binary_uncertainty_repulsion (0.1324) < hybrid_equal_rank_fusion (0.1351) < max_depth_straddle (0.1411) < hybrid_binary_gate20_max_depth_straddle (0.1454) < shared_random_binary_head (0.1692); B3: binary_uncertainty_repulsion (0.1340) < hybrid_equal_rank_fusion (0.1362) < hybrid_binary_gate20_max_depth_straddle (0.1461) < max_depth_straddle (0.1640) < shared_random_binary_head (0.1751).
11. **Balanced-accuracy cost:** ranking is max_depth_straddle (0.9432) > binary_uncertainty_repulsion (0.9171) > hybrid_equal_rank_fusion (0.9076) > hybrid_binary_gate20_max_depth_straddle (0.8983) > shared_random_binary_head (0.8735); material degradation is defined as more than 0.01 below Binary.
12. **Early Keyhole discovery:** at budget 30, Gate found a mean 8.50 positives versus Binary 12.20 under identical simulator-query budgets.
13. **Transient Keyhole:** final mean sensitivity is Gate 0.8898 versus Binary 0.9165; this is descriptive and uses the unchanged subgroup definition.
14. **Partition specificity:** new, old-local, and old-remote results are saved separately; old-remote remains highly uncertain because its positive count is tiny.
15. **Query-trajectory difference:** Gate/Binary mean Jaccard at budget 80 is 0.6317; median first divergence occurs at query 13.0.
16. **Did Max-Depth alter queries?** yes whenever a Hybrid selection differs from the exact Binary champion candidate; the run-level fractions are saved in `phase7_failure_diagnostics.csv`.
17. **q20/BA Pareto movement:** Gate is on the frontier for 0/3 definitions and Rank Fusion for 0/3; see the unweighted Pareto artifact.
18. **q30/BA Pareto movement:** reported separately for every B1/B2/B3 definition; no arbitrary weighted score was introduced.
19. **Computational overhead:** mean run time is Binary 6.31 s, Gate 9.06 s, Fusion 8.99 s, and Max-Depth 5.07 s.
20. **Simulator-cost interpretation:** Hybrid computation is more expensive, but every method still receives exactly the same number of simulator queries. Simulator and computational efficiency are not conflated.
21. **Maximum depth if Hybrid loses:** it remains a strongly predictable physical response and the Phase 6 continuous comparator; losing as auxiliary acquisition information would not erase that physical value.
22. **Boundary definition for the thesis:** emphasize B1 for direct continuity with Phase 6, and present B2/B3 as preregistered robustness diagnostics rather than replacing B1 with a post-hoc consensus.
23. **Robustness diagnostics:** B2, B3, consensus q20/q30, robust-scaling sensitivity, partition summaries, and supported surfaces remain diagnostic; B1/B2/B3 q20/q30 drive the preregistered decision.
24. **Final recommended real-data active strategy:** **BINARY ACQUISITION PRIMARY** — Neither Hybrid met the robust rule and Binary remained no worse on the preregistered boundary hierarchy under at least two definitions.
25. **Scientific lesson:** richer continuous physical information can change where a binary active learner queries, but it counts as a thesis-level boundary improvement only if the benefit survives multiple model-independent boundary definitions without a material global-performance cost.

## Complete rankings

- q20, lower is better: B1: binary_uncertainty_repulsion (0.1862) < hybrid_equal_rank_fusion (0.1872) < hybrid_binary_gate20_max_depth_straddle (0.1943) < max_depth_straddle (0.2053) < shared_random_binary_head (0.2289); B2: binary_uncertainty_repulsion (0.1924) < hybrid_equal_rank_fusion (0.1961) < max_depth_straddle (0.2018) < hybrid_binary_gate20_max_depth_straddle (0.2110) < shared_random_binary_head (0.2472); B3: binary_uncertainty_repulsion (0.1774) < hybrid_equal_rank_fusion (0.1835) < hybrid_binary_gate20_max_depth_straddle (0.1959) < max_depth_straddle (0.2219) < shared_random_binary_head (0.2266)
- q30, lower is better: B1: binary_uncertainty_repulsion (0.1332) < hybrid_equal_rank_fusion (0.1340) < hybrid_binary_gate20_max_depth_straddle (0.1438) < max_depth_straddle (0.1506) < shared_random_binary_head (0.1687); B2: binary_uncertainty_repulsion (0.1324) < hybrid_equal_rank_fusion (0.1351) < max_depth_straddle (0.1411) < hybrid_binary_gate20_max_depth_straddle (0.1454) < shared_random_binary_head (0.1692); B3: binary_uncertainty_repulsion (0.1340) < hybrid_equal_rank_fusion (0.1362) < hybrid_binary_gate20_max_depth_straddle (0.1461) < max_depth_straddle (0.1640) < shared_random_binary_head (0.1751)
- balanced-accuracy AULC, higher is better: max_depth_straddle (0.9432) > binary_uncertainty_repulsion (0.9171) > hybrid_equal_rank_fusion (0.9076) > hybrid_binary_gate20_max_depth_straddle (0.8983) > shared_random_binary_head (0.8735)

## Hard stop

No manual label, physical target, kernel, gate fraction, rank weight, or preregistered decision condition was changed after results. Phase 7 remains uncommitted and unpushed pending review; no Phase 8 was started.
