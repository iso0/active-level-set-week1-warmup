# Week 6 Phase 4 decision log

## Scope and supervisor requests

- Phase 4 was needed to close Ioan's kinetic-energy, total-height, focused feature-relationship, and beam-normalization requests.
- Normalized first-Conduction is explicitly excluded because Burak removed it from this phase.
- Dataset-update checking is excluded because Burak already confirmed no new upload; only missing files from the exact pinned revision were materialized.
- Width and depth targets and selected uncertainty models are reused; their model-selection pipelines were not rerun.
- Length is not a Phase 4 focus because Ioan's remaining questions concern width, penetration, energy, height, and beam normalization.

## New target meaning

- Kinetic monitor: `kinetic-energy_melt.dat` at `final_data_processed/sim_XXXXX/monitor/kinetic-energy_melt.dat`.
- Best-supported semantics: instantaneous aggregate kinetic energy over the melt-phase particle subset, in J (reported as nJ).
- Coverage caveat: sim_00052 is source-short but fully covers T0/adaptive windows; sim_00034 has 236 recorded NaNs, with one T0-endpoint NaN excluded and 2,233 valid T0 rows retained.
- Residual semantic caveat: The local repository does not include the solver reduction formula; Ioan should confirm the exact particle-mass weighting. File naming, SI-unit metadata, aggregate-monitor documentation, row alignment, and strongly non-monotone time behaviour support the stated interpretation.
- The T0 median is appropriate because the audited monitor is instantaneous and non-cumulative.
- Total height is z_max−z_min and includes both above- and below-surface extent; it is not penetration depth.
- T0 is used for direct comparability with validated geometry targets. The adaptive interior is the single limited sensitivity factor.
- Adaptive sensitivity does not overturn T0 as the controlled, cross-response primary target: kinetic ρ=0.978 with median shift 0.206 nJ; height ρ=0.952 with median shift 5.777 µm. The height tail is substantial (q95 17.079 µm), so temporal-definition sensitivity remains a limitation rather than evidence to replace T0.

## Compact modelling

- The compact comparison is sufficient because only two new responses need model selection; repeating the entire Phase 3 matrix would expand scope without answering a new robustness question.
- A simple point model is retained when the GP RMSE gain is below max(1% of target range, 2% of target IQR), even if the paired confidence interval excludes zero; this separates statistical detectability from practical relevance.
- kinetic_energy: selected kernel-family GP `matern32_learned_nugget`; selected point model `linear_ridge`; selected uncertainty model `matern32_learned_nugget`.
- kinetic_energy: learned nugget remains useful = True; simple models competitive = ["linear_ridge","polynomial_ridge_degree2"].
- total_height: selected kernel-family GP `matern32_learned_nugget`; selected point model `polynomial_ridge_degree2`; selected uncertainty model `matern32_learned_nugget`.
- total_height: learned nugget remains useful = True; simple models competitive = ["polynomial_ridge_degree2"].
- A learned nugget is effective unresolved model–data discrepancy, not a claim of simulator noise.

## Physical associations

- Width–LS, kinetic-energy–LS, depth–P/VX, total-height–P/VX, and ST associations are reported using raw Spearman, conditional standardized Ridge, and support-masked controlled GP views.
- Width–LS is positive (raw ρ=0.469; conditional β=0.373); the supported median-reference GP curve rises across LS.
- Kinetic-energy–LS is weak after adjustment (raw ρ=0.223; β=0.017); P dominates (β=0.973), so aggregate energy does not support a general larger-LS/lower-energy conclusion.
- Depth is positively associated with P (β=0.819) and negatively with VX (β=-0.500); total height shows the same directions (β(P)=0.793, β(VX)=-0.377).
- ST conditional coefficients are small: width 0.026, depth -0.049, kinetic energy -0.021, and total height -0.050.
- Only P×VX and P×LS interactions are examined; this is the physically motivated limit requested for Phase 4.
- Language is associative because the simulation design and fitted response surfaces do not by themselves identify causal effects.

## Normalized penetration

- D/LS is useful as beam-scale normalization, while D/width describes shape slenderness.
- LS-versus-D/LS requires caution because LS is mathematically coupled through the denominator.
- G3/LS is retained for future independently label-rich analysis; R3 and G3/LS are descriptive candidates, not Keyhole truth.

## Deferred work

- Ioan should confirm the exact aggregate kinetic-energy reduction formula and particle-mass weighting.
- Onset versus sustained Keyhole remains unresolved.
- Active learning, final classification, acquisition design, and level-set estimation remain deferred until explicit review and authorization.
