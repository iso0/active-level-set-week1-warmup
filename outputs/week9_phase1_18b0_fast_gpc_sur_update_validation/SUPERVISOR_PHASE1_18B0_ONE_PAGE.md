# Supervisor Phase 1.18B0 — one page

- 25 frozen snapshots, 307 candidates, 2,456 hypothetical-label/update-level calculations; no new path.
- FAST vs exact-fixed: median Spearman **0.481**, q10 **-0.211**, top-1 **44%**, top-5 Jaccard **0.524**; 2/25 correlations undefined for constant score vectors.
- Posterior probability MAE is tiny (median snapshot 1.06e-05), yet SUR rankings fail because the acquisition score is a small difference of global uncertainties.
- Hypothetical Keyhole updates have larger error than Conduction (4.54e-05 vs 2.05e-05).
- Physics-mean refitting matters strongly (median score Spearman 0.263); kernel reoptimization matters much less (0.986).
- **Decision: FAST_SUR_REJECTED / PHYSICS_REFIT_MATTERS.** Do not run FAST SUR prospectively. No SUR-vs-Margin performance claim was tested.
