# Final red-team report

1. P1 overall q20 AULC effect: -0.001378676.
2. Paired CI excludes zero: False; interval [-0.003800551, +0.000726103].
3. Holm survives at 0.05: False.
4. EARLY/MID/LATE effects: +0.002169 / -0.003980 / -0.001033.
5. B40 q20 Keyhole recall P1−P0: -0.009060.
6. B40 active-query Keyhole fractions are disclosed in `b40_keyhole_diagnostics.csv`; they are retrospective.
7. B80 P1/P0 Jaccard: 0.9641; diversity alone is not called beneficial.
8. Mean P1−P0 global p(1-p) difference at common checkpoints: +4.802678e-04.
9. Whether global uncertainty translates to q20 is adjudicated only by the primary contrast above.
10. Mean near-tied fractions P1/P2: 0.006077/0.011135.
11. Tie break is deterministic smallest population-row index; no candidate was changed post hoc.
12. Threshold results are in `sample_efficiency_contrasts.csv`.
13. Label-saving decision: LABEL_SAVING_NOT_SUPPORTED.
14. Full-heldout B40/B80 values are in `fullheldout_diagnostics.csv`; catastrophic guardrail: False.
15. P2−P1 q20 effect: -0.003074, CI [-0.009072, +0.003056].
16. Physics-refit performance decision: PHYSICS_REFIT_SUR_CHANGES_PATH_ONLY.
17. P1/P2 score median Spearman -0.3079, top-1 0.0728, top-5 Jaccard 0.1039.
18. Median full-run seconds P1/P2: 216.86/469.06; cost is disclosed, not extrapolated.
19. Kernel/ARD numerical diagnostics are in `model_fit_diagnostics.csv.gz`; ARD is not interpreted causally.
20. Primary acquisition decision: GLOBAL_SUR_NO_GAIN.
21. Per the frozen stopping rule, acquisition development stops after this validated benchmark.
22. Narrow claim: see `claim_ledger.md`; no novelty, universal superiority, exact-paper equivalence, or unsupported label saving is claimed.

The audit also attacked future-label leakage, q20/q30/B1 leakage, off-by-one prefixes, candidate-pool drift, P0 reconstruction, hypothetical outcome weighting, P1 parameter drift, P2 kernel drift, FAST fallback, fold pseudo-replication, AULC orientation, and multiplicity. Retrospective B1/query-label diagnostics were computed only after paths were frozen.
