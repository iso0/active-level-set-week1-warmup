# Final red-team report

1. Margin is not variance-blind; it lacks a separate epistemic/global-reduction objective.
2. Straddle/EMI collapse is adjudicated over all 600 snapshots, not one run: RANKING_DISTINCT_FROM_MARGIN / RANKING_DISTINCT_FROM_MARGIN.
3. SMOCU ranking status: RANKING_DISTINCT_FROM_MARGIN; implementation is explicitly approximate.
4. SUR ranking status: RANKING_DISTINCT_FROM_MARGIN; implementation is explicitly approximate.
5. The local `v^2W/(1+vW)` update is valid as a same-location Laplace approximation.
6. `W_C` is the most coherent pre-observation Laplace curvature; `W_A` is not a Hessian.
7. The exponential PA gate is not justified for ARD Matérn-3/2.
8. PA-TVR is not demonstrated tangent-aware.
9. PA-TVR is not global/non-myopic.
10. It resembles tMSE/gSUR with an unsupported physics-scaled gate.
11. It directly inherits bound-hitting ARD lengths.
12. L100→L1000: median Spearman 1.0000, top-10 Jaccard 0.966.
13. It is cheaper than principled global methods because it omits their global posterior consequence.
14. Distinct ranking alone is not scientific justification.
15. Broad GPC-SUR and physics-informed GPC novelty are already occupied.
16. No defensible PA-TVR novelty statement remains after the geometry failure.
17. Exactly one future experiment is conditionally justified only after faithful-update validation.
18. Candidate: FAST_GPC_SUR because it directly targets level-set/random-set uncertainty; otherwise NONE.
