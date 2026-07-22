# Week 5 — First-Conduction Gaussian Process Regression Log

This is a cumulative thesis decision record. Later Week 5 phases should preserve the provenance and decisions below and append or carefully extend the relevant results and next-decision sections.

## 1. Supervisor task and scientific objective

The Week 5 task is a real-data Gaussian Process regression warm-up using four process inputs to predict the first observed Conduction timestep. It establishes a reproducible simulation-level regression baseline before any active-learning or level-set-estimation work. This phase is not active learning and does not estimate a level set.

## 2. Data source and provenance

- Hugging Face repository: `ioandanielc/sph_dataset`
- CSV filename: `final-labels_all.csv`
- Pinned revision: `0e859b748fdbc8454f66e58e101e333ac0479d42`
- CSV SHA-256: `964a12d86435e9f0879e2e43384d997e1cc2faa7b9e4c3aeb49cf0e73e3fb154`
- Raw dimensions: 65,472 rows × 12 columns
- One simulation: one unique `name` group
- Total simulations: 241
- Usable first-observed Conduction targets: 238
- Excluded: 3 simulations because no Conduction frame is observed

## 3. Input and target definitions

```text
X = [P, VX, LS, ST]

y = minimum raw timestep for which label_final == "Conduction"
```

- `P` is laser power.
- `VX` is scan velocity.
- `LS` is laser spot radius.
- `ST` is substrate temperature.
- The target is a raw simulation timestep number and is not presented as physical time.
- Frame index is not used as the response.

## 4. Data-audit findings retained for the thesis

- `name` is the valid simulation grouping key; `hash` merges distinct simulations.
- 238 simulations reach Conduction; 91 form the strict-clean subset.
- 147 broad-dataset simulations contain Screenshot Bug before first observed Conduction.
- Three simulations do not reach Conduction.
- `bug_free` is inconsistent with the explicit Screenshot Bug labels.
- `label_1`, `label_2`, and `label_final` are identical in this CSV.
- Timestep schedules differ across simulations.
- Persistent onset was examined only as a diagnostic and differs from first observed onset in two simulations.
- Observational ambiguity intervals were measured but were not used as GP targets.

## 5. Final modelling decisions

- The literal first observed Conduction timestep is the target.
- Raw timestep is used without conversion to physical time.
- The clean dataset is analysed first.
- The broad dataset is analysed second.
- Screenshot Bug simulations remain in the broad dataset.
- In the broad dataset, the first actually observed Conduction timestep is treated as a point target.
- No interpolation or midpoint target is used.
- The three never-Conduction simulations are excluded.
- Persistent onset is not used as the primary target.
- The primary kernel set is isotropic RBF, ARD RBF, Matérn 3/2 and Matérn 5/2.
- Inputs are standardized inside each LOO fold.
- A fixed tiny jitter is used for numerical stability.
- No WhiteKernel is optimized in the primary comparison.
- Kernel performance is assessed with experiment-level LOO.
- Clean and broad aggregate metrics are ranked separately.
- An additional same-clean-points comparison is used to assess the effect of adding broad observations.

## 6. Why clean and broad are both analysed

The clean/no-Bug subset is an operational sensitivity analysis based only on the absence of Screenshot Bug labels, whereas the broad subset preserves substantially greater sample size and process-space coverage. Since filtering reduced the sample from 238 to 91 simulations and materially changed the target distribution, the no-Bug subset was not assumed to be a neutral random subsample or a confirmed higher-quality subset. The two datasets were therefore analysed separately. A paired comparison on the same no-Bug held-out simulations was additionally used to assess whether the broad training data improved or degraded predictions on that fixed evaluation subgroup.

## 7. Kernel rationale

The isotropic RBF kernel assumes a common smoothness scale across all standardized process variables. The ARD RBF kernel relaxes this assumption by learning a separate lengthscale for laser power, scan velocity, laser spot radius and substrate temperature. Matérn 3/2 and Matérn 5/2 kernels were included to test less restrictive smoothness assumptions than the infinitely differentiable RBF kernel. All kernels were evaluated under the same preprocessing, optimization and leave-one-out protocol. ARD lengthscales are descriptive model diagnostics, not causal importance scores.

## 8. Evaluation design

LOO uses nearly all available simulation-level observations for training in every fold and gives one held-out prediction for each of the 91 clean or 238 broad simulations. Scaling inside each fold prevents the held-out input from influencing preprocessing. MAE, median absolute error, RMSE, R² and normalized RMSE measure point prediction; NLPD, empirical 95% coverage and interval width assess probabilistic behavior. Clean and broad metrics are not directly interchangeable because the samples and target distributions differ. The same-clean-points comparison holds the 91 evaluation targets fixed while changing only whether the extra broad observations are available for training.

## 9. Results

### Clean kernel ranking

Primary RMSE order: Matérn 3/2 > ARD RBF — Automatic Relevance Determination RBF > Matérn 5/2 > Isotropic RBF.

| kernel_label | MAE | median_absolute_error | RMSE | R2 | normalized_RMSE | mean_negative_log_predictive_density | empirical_95_interval_coverage | mean_95_interval_width | total_runtime_seconds | optimization_warning_count |
|---|---|---|---|---|---|---|---|---|---|---|
| Matérn 3/2 | 1,735.8 | 1,092.1 | 2,537.0 | 0.9171 | 0.2863 | 9.8156 | 0.9011 | 13,861.9 | 3.8854 | 0 |
| ARD RBF — Automatic Relevance Determination RBF | 2,035.5 | 1,291.4 | 3,255.0 | 0.8636 | 0.3673 | 9.9604 | 0.8571 | 8,736.3 | 15.9956 | 49 |
| Matérn 5/2 | 2,545.3 | 1,538.1 | 3,724.6 | 0.8214 | 0.4203 | 10.1396 | 0.9011 | 18,027.2 | 4.4465 | 0 |
| Isotropic RBF | 4,402.2 | 3,100.9 | 6,141.7 | 0.5142 | 0.6931 | 10.8160 | 0.9121 | 24,118.1 | 5.7899 | 0 |

Best-by-metric findings:

- lowest MAE: **Matérn 3/2** (1735.8; timestep units).
- lowest median absolute error: **Matérn 3/2** (1092.1; timestep units).
- lowest RMSE: **Matérn 3/2** (2537; timestep units).
- highest R²: **Matérn 3/2** (0.91711).
- lowest normalized RMSE: **Matérn 3/2** (0.28631).
- lowest mean NLPD: **Matérn 3/2** (9.8156).
- coverage closest to 95%: **Isotropic RBF** (0.037912; absolute coverage error).
- narrowest mean 95% interval: **ARD RBF — Automatic Relevance Determination RBF** (8736.3; timestep units; narrowest is not automatically best).
- lowest total runtime: **Matérn 3/2** (3.8854; seconds).
- fewest recorded optimization warnings: **Isotropic RBF** (0; warnings).

### Broad kernel ranking

Primary RMSE order: Matérn 3/2 > Matérn 5/2 > Isotropic RBF > ARD RBF — Automatic Relevance Determination RBF.

| kernel_label | MAE | median_absolute_error | RMSE | R2 | normalized_RMSE | mean_negative_log_predictive_density | empirical_95_interval_coverage | mean_95_interval_width | total_runtime_seconds | optimization_warning_count |
|---|---|---|---|---|---|---|---|---|---|---|
| Matérn 3/2 | 11,616.9 | 7,414.2 | 16,256.3 | 0.4060 | 0.7691 | 11.0404 | 0.9286 | 58,070.3 | 55.0253 | 0 |
| Matérn 5/2 | 11,698.4 | 7,581.8 | 16,402.7 | 0.3952 | 0.7760 | 11.0322 | 0.9370 | 58,594.5 | 67.8181 | 0 |
| Isotropic RBF | 12,023.8 | 7,875.0 | 16,735.2 | 0.3705 | 0.7918 | 11.0402 | 0.9202 | 60,597.8 | 53.6230 | 0 |
| ARD RBF — Automatic Relevance Determination RBF | 12,982.0 | 8,231.9 | 18,597.1 | 0.2226 | 0.8799 | 11.3067 | 0.8908 | 58,098.2 | 289.5290 | 0 |

Best-by-metric findings:

- lowest MAE: **Matérn 3/2** (11617; timestep units).
- lowest median absolute error: **Matérn 3/2** (7414.2; timestep units).
- lowest RMSE: **Matérn 3/2** (16256; timestep units).
- highest R²: **Matérn 3/2** (0.40598).
- lowest normalized RMSE: **Matérn 3/2** (0.76911).
- lowest mean NLPD: **Matérn 5/2** (11.032).
- coverage closest to 95%: **Matérn 5/2** (0.013025; absolute coverage error).
- narrowest mean 95% interval: **Matérn 3/2** (58070; timestep units; narrowest is not automatically best).
- lowest total runtime: **Isotropic RBF** (53.623; seconds).
- fewest recorded optimization warnings: **Isotropic RBF** (0; warnings).

### Same-clean-points result

| kernel_label | clean_trained_MAE | clean_trained_RMSE | broad_trained_MAE | broad_trained_RMSE | clean_points_improved_by_broad_training | clean_points_worsened_by_broad_training | median_paired_improvement_clean_minus_broad |
|---|---|---|---|---|---|---|---|
| Isotropic RBF | 4,402.2 | 6,141.7 | 12,850.8 | 16,433.6 | 13 | 78 | -7,422.7 |
| ARD RBF — Automatic Relevance Determination RBF | 2,035.5 | 3,255.0 | 13,454.0 | 18,429.4 | 17 | 74 | -8,506.7 |
| Matérn 3/2 | 1,735.8 | 2,537.0 | 13,303.7 | 17,398.5 | 10 | 81 | -9,689.6 |
| Matérn 5/2 | 2,545.3 | 3,724.6 | 13,077.2 | 17,095.0 | 12 | 79 | -8,775.0 |

- **Isotropic RBF:** clean-trained MAE/RMSE 4402.2/6141.7; broad-trained 12850.8/16433.6; improved/worsened/tied points 13/78/0; median paired improvement -7422.7.
- **ARD RBF — Automatic Relevance Determination RBF:** clean-trained MAE/RMSE 2035.5/3255.0; broad-trained 13454.0/18429.4; improved/worsened/tied points 17/74/0; median paired improvement -8506.7.
- **Matérn 3/2:** clean-trained MAE/RMSE 1735.8/2537.0; broad-trained 13303.7/17398.5; improved/worsened/tied points 10/81/0; median paired improvement -9689.6.
- **Matérn 5/2:** clean-trained MAE/RMSE 2545.3/3724.6; broad-trained 13077.2/17095.0; improved/worsened/tied points 12/79/0; median paired improvement -8775.0.

### ARD lengthscale patterns

| dataset | input | standardized_space_lengthscale | full_fit_anisotropy_ratio_max_over_min |
|---|---|---|---|
| clean | P | 0.7642 | 376.4951 |
| clean | VX | 0.2656 | 376.4951 |
| clean | LS | 100.0000 | 376.4951 |
| clean | ST | 1.7332 | 376.4951 |
| broad | P | 0.9449 | 5.9849 |
| broad | VX | 0.4045 | 5.9849 |
| broad | LS | 0.8201 | 5.9849 |
| broad | ST | 0.1579 | 5.9849 |

- **Clean:** shortest lengthscale VX=0.266; longest LS=100; max/min ratio 376.50.
- **Broad:** shortest lengthscale ST=0.158; longest P=0.945; max/min ratio 5.98.

### Uncertainty calibration

- Clean, ARD RBF — Automatic Relevance Determination RBF: coverage 85.7%, mean width 8736.3.
- Clean, Isotropic RBF: coverage 91.2%, mean width 24118.1.
- Clean, Matérn 3/2: coverage 90.1%, mean width 13861.9.
- Clean, Matérn 5/2: coverage 90.1%, mean width 18027.2.
- Broad, ARD RBF — Automatic Relevance Determination RBF: coverage 89.1%, mean width 58098.2.
- Broad, Isotropic RBF: coverage 92.0%, mean width 60597.8.
- Broad, Matérn 3/2: coverage 92.9%, mean width 58070.3.
- Broad, Matérn 5/2: coverage 93.7%, mean width 58594.5.

### Optimization warnings and runtime

- Recorded optimization warnings across LOO and full fits: 50.
- Optimization/fit failures: 0.
- Summed LOO fold runtime: 496.1 seconds.
- Full-data fit runtime: 1.9 seconds.
- All four kernels used `fmin_l_bfgs_b`, `n_restarts_optimizer=1`, `alpha=1e-06`, `normalize_y=True`, and the same seed.

## 10. Interpretation and thesis relevance

- Kernel-ranking stability: The RMSE winner is shared, but the remaining kernel ordering changes. RMSE-rank correlation is 0.400.
- ARD contribution: ARD RBF changes RMSE relative to isotropic RBF by +47.00% on clean data and -11.13% on broad data (positive means ARD reduces RMSE).
- Additional broad observations: Broad training reduces RMSE on the same 91 clean points for 0 of 4 kernels.
- Uncertainty intervals: empirical coverage and mean widths are listed above; coverage nearer 95% is better calibrated under the provisional Gaussian assumptions, but width must be considered at the same time.
- Later surrogate modelling: the separate clean/broad winners and paired result provide an evidence-based shortlist for the next methodological decision.
- What this does not prove: physical transition-time correctness, causal input importance, the physical meaning of Screenshot Bug labels, or active-learning performance.

## 11. Limitations

- First observed Conduction may not equal an exact physical transition time.
- Raw timestep is not converted to physical time.
- Broad targets may be preceded by frames labelled Screenshot Bug; subsequent supervisor context indicates that some such labels may represent repeated Initial Emptiness images rather than corrupted simulation data.
- Simulator data are deterministic, but extracted labels can introduce effective target ambiguity.
- ARD lengthscales are not causal feature importance.
- The data design is not assumed to be a perfect uniform random sample.
- This is GP regression, not active level-set estimation.
- `alpha=1e-06` is numerical jitter and not a fitted observation-noise model.

## 12. Next decision

The requested Week 5 diagnostic and optimizer work is complete. Retain Matérn 3/2 with L-BFGS-B as the default regression baseline, keep the broad inclusion policy fixed, and use the no-Bug analysis as a subgroup sensitivity check. The next scientific decision should be discussed with Ioan before any new experiment: determine whether batch/design variables or a more explicit representation of the initial empty-like duration can be obtained and evaluated. Active learning and level-set estimation remain not started.

## Supervisor clarification on Screenshot Bug and Initial Emptiness

**Recorded 2026-07-22, after the Phase 2 kernel comparison.**

The supervisor noted that the student may have labelled only the first empty image as Initial Emptiness and subsequent empty images as Screenshot Bug. Screenshot Bug therefore does not necessarily identify a corrupted simulation. He also suggested that empty images may have become more common after laser spot radius began to vary.

The term “clean subset” is retained as an operational experiment label and refers only to simulations without any Screenshot Bug label. It must not be interpreted as a confirmed higher-quality subset.

This clarification changes the interpretation, not the target or inclusion rule. The broad dataset continues to include Screenshot Bug simulations, and the response remains the first raw timestep at which Conduction is actually observed. No interpolation, ambiguity midpoint, persistent-onset replacement, or physical-time conversion is introduced. The three never-Conduction simulations remain excluded. The earlier observational ambiguity intervals remain conservative CSV-label diagnostics; they do not prove that every Bug-associated target is physically interval-censored.

## 13. Label-sequence and laser-radius diagnostics

### Sequence evidence

- 150 of 241 simulations contain at least one Screenshot Bug frame.
- None of those 150 simulations begins with an Initial Emptiness label, and none matches the strict stored-label sequence “Initial Emptiness followed immediately by one or more Screenshot Bug frames”.
- All 147 simulations with a pre-Conduction Screenshot Bug have those pre-Conduction Bug frames inside the initial contiguous empty-like block, where empty-like is a diagnostic union of Initial Emptiness and Screenshot Bug.
- 99 of 150 Bug-containing simulations have one initial Bug block only; 51 have multiple separated Bug blocks.
- 51 of 150 contain Bug frames outside the initial empty-like block and after a physical regime has already appeared.

The literal stored-label ordering does not reproduce the supervisor's recollection. However, the 147/147 initial-block result strongly supports the broader possibility that pre-Conduction Screenshot Bug labels can describe repeated empty images. The labels alone cannot establish the underlying physical meaning, so the recollection is neither treated as confirmed nor rejected.

### Input and target differences

Bug-containing simulations have a higher median laser spot radius than no-Bug simulations (66.48 µm versus 59.86 µm), but LS is not the only difference. Mean P is 165.21 versus 146.59, mean VX is 0.6335 versus 0.5900, and mean ST is 352.04 versus 342.62. The first-observed-Conduction target distribution differs much more strongly: the Bug subgroup median is 38,782 raw timestep units versus 13,933 in the no-Bug subgroup.

Across all 241 simulations, LS has a positive descriptive association with initial empty-like raw-timestep width (Spearman ρ=0.2840) and, among the 238 observed-Conduction simulations, with first observed Conduction timestep (ρ=0.3189). Its association with Screenshot Bug frame count is weak (ρ=0.0887). VX and ST also relate to sequence behavior: VX has ρ=-0.7296 with initial empty-like width and ρ=-0.5129 with the target, while ST has ρ=0.3468 with initial empty-like width. These are observational associations, not causal effects.

The LS-only logistic diagnostic gives out-of-fold ROC AUC 0.5952 with standardized coefficient +0.4030. The four-input model gives AUC 0.5926 with standardized coefficients P +0.2562, VX +0.1618, LS +0.3012 and ST +0.1839. Adding P, VX and ST changes AUC by -0.0026 relative to LS alone. The weak discrimination does not support treating LS as a sufficient explanation of Bug occurrence.

### Revised clean-versus-broad interpretation

The Phase 2 same-clean-points result remains numerically unchanged: broad training worsened predictions on the 91 no-Bug evaluation points for all four kernels. For Matérn 3/2, broad training improved 10 points and worsened 81, with RMSE 17,398.5 versus 2,537.0 for no-Bug-only training. This is not evidence that broad labels are invalid. It is consistent with subgroup/design heterogeneity, different process-space and LS distributions, a strongly shifted target distribution, different initial empty-like duration, and batch or design variables absent from P, VX, LS and ST.

### Largest Matérn 3/2 LOO errors

For the ten largest no-Bug errors, eight targets lie in the earliest or latest target quartile, four points lie on a process-space boundary proxy, one is in a sparse-region proxy, and three fall outside the nominal 95% interval. Their median LS (59.58 µm) and median five-nearest-neighbour distance (0.971) are close to the full no-Bug values (59.86 µm and 0.966).

For the twenty largest broad errors, 15 targets lie in the earliest or latest quartile, 15 fall outside the nominal 95% interval, four meet the sparse-region proxy and none meets the process-boundary proxy. Their Bug rate is 55%, below the full broad rate of 61.8%, so the largest errors are not enriched for Bug labels. Their median LS is higher (75.77 µm versus 64.42 µm) and their median five-nearest-neighbour distance is modestly higher (0.801 versus 0.760). Late/edge targets and subgroup structure are more evident than a single Bug-only or sparsity-only explanation. No cases were removed.

## 14. Matérn 3/2 optimizer-family comparison

All optimizer comparisons used the Phase 2 Matérn 3/2 specification, fold-local scaling, normalize_y=True, alpha=1e-6, no WhiteKernel, identical bounds, two common deterministic starts for L-BFGS-B/SLSQP/Powell, and experiment-level LOO.

### Clean/no-Bug data

L-BFGS-B, SLSQP and Powell are numerically equivalent for held-out prediction: RMSE is respectively 2,537.006918, 2,537.006767 and 2,537.006734; MAE is 1,735.765231, 1,735.765095 and 1,735.765126. Each gives 90.11% empirical 95% coverage, and every one of the 91 fits converges without warnings, failures or parameter-bound hits. No optimization increases RMSE to 2,770.378128 but widens intervals enough to give 94.51% coverage; its lower NLPD must therefore not be read as better point prediction. Summed fold runtimes in the final run were approximately 3.4 s (L-BFGS-B), 4.2 s (SLSQP), 18.9 s (Powell), and 0.2 s (no optimization).

### Broad data

The three optimized methods are again practically identical: L-BFGS-B/SLSQP/Powell RMSE is 16,256.261409/16,256.260691/16,256.261361, with MAE 11,616.870211/11,616.868777/11,616.870204 and 92.86% coverage. All 238 fits for each optimizer converge with zero warnings, failures and parameter-bound hits. No optimization has RMSE 16,871.408714 and only 81.09% coverage. SLSQP is faster on this run than L-BFGS-B, while Powell is much slower; the held-out differences remain scientifically negligible.

The maximum absolute prediction difference versus L-BFGS-B is 0.0052 timestep units on clean data for SLSQP/Powell and 0.0580 for SLSQP on broad data, against targets measured in thousands of timestep units. Full-data optimized Matérn 3/2 kernels are the same to displayed precision across all three optimizers: “0.88**2 × Matern(length_scale=1.16, nu=1.5)” on clean data and “1.01**2 × Matern(length_scale=0.623, nu=1.5)” on broad data. No optimizer resolves the broad-data prediction gap.

The limited broad full-data Matérn 5/2 check is likewise stable: all three optimizers obtain “1.01**2 × Matern(length_scale=0.554, nu=2.5)” with log marginal likelihood about -283.7208 and no failure. This does not overturn the LOO point-prediction preference for Matérn 3/2.

## 15. Final Week 5 recommendation and limitations

- **Recommended kernel:** isotropic Matérn 3/2, because it has the best MAE, median absolute error, RMSE, R² and normalized RMSE on both Phase 2 datasets.
- **Recommended optimizer:** L-BFGS-B, because SLSQP and Powell do not materially improve held-out prediction; L-BFGS-B is stable, already supported by sklearn, and avoids extra custom-optimizer complexity.
- **Dataset interpretation:** retain the broad dataset as the inclusive primary record under the fixed data policy, and report the no-Bug subset as an operational subgroup sensitivity analysis. Do not describe it as verified cleaner data.
- **Uncertainty caveat:** broad Matérn 5/2 retains slightly better Phase 2 NLPD and 95% coverage than Matérn 3/2, so probabilistic calibration should be stated separately from the point-prediction recommendation.
- **Scientific limit:** the response is an observed raw timestep, not an exact physical transition time. Missing batch/design variables, the label convention and deterministic-simulator extraction ambiguity remain plausible explanations for heterogeneity.

Week 5 ends here. No active learning, level-set estimation, GP classification, ARD Matérn expansion or additional optimizer family was started.
