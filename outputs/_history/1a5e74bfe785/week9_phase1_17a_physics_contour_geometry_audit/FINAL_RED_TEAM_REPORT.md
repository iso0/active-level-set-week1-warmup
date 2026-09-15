# Final red-team report

- Exact published Phase 1.16 paths are read; no selection or model fitting occurs.
- Nearest neighbors use the original standardized Euclidean metric, not the proposed tangent metric.
- Local standardized gradient uses the chain-rule scale factors and has exactly zero ST component.
- Geometry is written and hashed before truth/B1/q20/q30 are joined.
- Orthogonality, vector reconstruction, energy identity, and fraction sum are tested row-wise.
- Candidate rows are descriptive; inference aggregates the five folds inside 20 repeat blocks.

## Adversarial mechanism answers

1. **Normal escape?** Partial contribution (30.1% of positive extra energy), but not a dominant explanation; c=4 normal/B1 association is unresolved.
2. **ST-nullspace escape?** Partial contribution (26.9%), and ST share is positively associated with B1 distance, but it is not dominant and its c=4 overall share increase is unresolved.
3. **Genuine P/VX/LS tangent spread?** Largest absolute contribution (42.9%), but tangent share decreases rather than increases.
4. **Budget-dependent?** Yes: early ST increase, mid mixed pattern, late normal-share increase.
5. **Strongest around B25–40?** Total distance and B1 displacement rise there, but no single component dominates that region.
6. **Greater B1 distance?** Most consistently higher ST share and lower tangent share; not higher normal share at c=4.
7. **Lower q20 concentration?** q20-like queries are more tangent and less ST; under c=4 they are not enriched in normal share.
8. **Lower active-query Keyhole fraction?** Keyhole selections have more normal and less ST than Conduction; under c=4 their tangent difference is near zero.
9. **Would PCTR remove a harmful mechanism?** It removes normal motion only; the audit does not establish that normal motion drives the harmful B1/q20 shift.
10. **Is Euclidean repulsion already mostly tangent?** In absolute extra energy, tangent is the largest single component, but the overall mechanism remains mixed.
11. **Is ST responsible?** Association is present, especially with B1 distance, but causality is not established and the MID ST share falls.
12. **Run Phase 1.17B?** No. A clear PCTR-specific harmful mechanism was not isolated.

- Increased ST share is not interpreted as causal irrelevance.
- Physics-contour normal is not called the true GP boundary normal.
- Component/B1 and component/Keyhole relationships are retrospective associations.
