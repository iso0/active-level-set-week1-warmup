# Final red-team report

1. **Multiple configurations?** Yes; exact counts are recorded without fuzzy grouping.
2. **Window bias?** Plausible for 167 rows; causal mislabelling is not identifiable.
3. **Models survive main-only?** Predictive strength survives, but ranking is metric-dependent: M3 leads ROC-AUC/Brier and G3 leads balanced accuracy/Keyhole recall. No architecture was tuned.
4. **Depth floor?** A label-free terminal pile supports censoring; its threshold is empirical, not a universal geometry constant.
5. **Stage-1 separation?** Exact threshold checks, not coefficient size alone, establish it. Probability claims use held-out metrics.
6. **Residual/ARD relations?** Associations only; no causal wording.
7. **Pair accounting?** Directed and unique-unordered counts are separate; every violation is listed.
8. **Configuration explanation of violations?** No: all 3 persist in the main configuration.
9. **Hard propagation?** Oracle retrospective only and produces wrong implications; no label-saving claim.
10. **Letham equivalence?** Rejected: Phase 1.18B did not test GlobalSUR, and logistic M3 cannot use the probit closed form directly.
11. **Leakage/new paths?** Published Phase 1.14 prefixes only; fits use revealed labels, held-out labels only score probabilities.
12. **Storage/history?** No earlier artifact is copied; historical paths and parent SHA are referenced.

No issue found justifies relabelling, rewriting a frozen phase, or claiming a new active-learning result.
