# Week 6 Phase 4 results summary

## What Phase 4 closed

Phase 4 followed the chain **raw monitor files → verified physical meaning → simulation-level targets → compact exact-LOO modelling → focused input–output associations → beam-normalized penetration diagnostics**. It did not reopen the validated width, length, or penetration-depth model-selection work.

## Provenance and usable populations

- Branch: `codex/week6-phase4-new-outputs-feature-effects` at `b112f6b22898976f77410190614cb4fb218d38f9`.
- Dataset: `ioandanielc/sph_dataset` pinned at `0e859b748fdbc8454f66e58e101e333ac0479d42`; no revision lookup or update check.
- Phase 1 ledger SHA-256: `10DEF11AB64D62444AC14FED506266BEB748EEB5BF892ACDC12E7F0F6DDCF4FF`.
- Kinetic energy: 241/241 usable simulations.
- Total vertical height: 241/241 usable simulations.
- Persistent G3/R3 diagnostics: 240/241 available; sim_00101 has no Phase 3.5 adaptive interior.
- Descriptive associations: all 241 simulations; the depth controlled GP reuses the exact stable 230 population.

## Physical meaning and target definitions

`kinetic-energy_melt.dat` is interpreted as **instantaneous aggregate kinetic energy over the melt-phase particle subset**, stored in J and reported in nJ. The target windows are fully covered in all 241 simulations. Of the source files, 240 align over the full monitor and sim_00052 is pinned source-short but still covers both target windows. sim_00034 records 236 source NaNs; one T0-endpoint NaN is excluded, leaving 2,233 valid T0 rows. Valid values are non-negative, become active with melt, and are strongly non-monotone; therefore the monitor is not cumulative.

The exact solver reduction formula is not included locally. Ioan should confirm the particle-mass weighting before the phrase "total kinetic energy" is treated as solver-certified rather than the best-supported aggregate-monitor interpretation.

Total vertical height is `z_max - z_min`; penetration depth is `max(0, -z_min)`. The two are not interchangeable.

Both primary targets use the validated T0 median: the final 20% of melt-present observations before the laser reaches 90% of the positive-X domain. The only sensitivity target is the median over the Phase 3.5 adaptive active interior.

## Primary-versus-adaptive sensitivity

- T0 melt-pool kinetic energy: paired n=240, Spearman ρ=0.978, median absolute shift=0.2059 nJ, q95 shift=0.5859 nJ.
- T0 total vertical melt-pool height: paired n=240, Spearman ρ=0.952, median absolute shift=5.777 um, q95 shift=17.08 um.

## Compact model conclusions

- **T0 melt-pool kinetic energy**: point model `linear_ridge` (MAE 0.1154, RMSE 0.1875 nJ, R² 0.941); uncertainty model `matern32_learned_nugget` (95% coverage 0.971). Learned nugget useful: True. Competitive simple models: ["linear_ridge","polynomial_ridge_degree2"].
  The selected GP itself has MAE 0.08901 and RMSE 0.1739 nJ. Its paired improvement is statistically supported against the selected simple model, but the RMSE gain is smaller than the predeclared practical threshold 0.03164 nJ; parsimony therefore governs the point-model choice.
- **T0 total vertical melt-pool height**: point model `polynomial_ridge_degree2` (MAE 5.294, RMSE 8.523 um, R² 0.782); uncertainty model `matern32_learned_nugget` (95% coverage 0.963). Learned nugget useful: True. Competitive simple models: ["polynomial_ridge_degree2"].
  The selected GP itself has MAE 4.206 and RMSE 7.598 um. Its paired improvement is statistically supported against the selected simple model, but the RMSE gain is smaller than the predeclared practical threshold 1.012 um; parsimony therefore governs the point-model choice.

The learned WhiteKernel term is described as effective residual or unresolved model–data discrepancy. It is not identified as simulator noise.

## Focused physical associations

- Width–LS: raw Spearman ρ=0.469; conditional standardized Ridge β=0.373. The controlled curve is interpreted only over marked empirical support.
- Kinetic-energy–LS: raw Spearman ρ=0.223; conditional standardized Ridge β=0.017. Low/median/high-power controlled slices separate LS association from the power reference.
- Depth–P/VX: raw ρ(P)=0.789, ρ(VX)=-0.438; conditional β(P)=0.819, β(VX)=-0.500.
- Total-height–P/VX: raw ρ(P)=0.801, ρ(VX)=-0.310; conditional β(P)=0.793, β(VX)=-0.377.

ST is assessed across all four raw correlations and conditional coefficients; no mechanistic claim is made from a small or large association. P×VX and P×LS are the only interaction pairs analysed.

## Beam-normalized penetration

`T0_depth_over_LS` and `G3_over_LS` are dimensionless because depth and laser spot radius are both expressed in micrometres. `G3_over_LS` exactly equals persistent depth divided by LS; no redundant time-series pipeline was constructed.

Absolute depth asks how many micrometres the melt reaches below the surface. Depth/LS asks how large penetration is relative to beam radius. R0/R3 ask how deep-and-narrow the melt shape is. These denominators encode different physical comparisons.

**Mathematical-coupling warning:** LS is in the denominator of D/LS, so a negative LS–D/LS pattern can appear partly mechanically even when absolute depth changes little. Interpret LS primarily against absolute depth. G3/LS is retained only as a candidate for future independently label-rich analysis; high G3/LS does not establish Keyhole.

## Remaining limits

- The kinetic reduction formula still needs Ioan's solver-level confirmation.
- Controlled curves and surfaces are model-based associations at declared reference settings and are masked outside empirical support.
- R3 remains a provisional sustained deep-and-narrow descriptor, not final Keyhole ground truth.
- Active learning, a classifier, acquisition functions, and level-set estimation remain deferred.

## Validation

All 35/35 automated Phase 4 checks passed.
