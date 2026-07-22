# Week 5 GP Meeting Brief

## Task

Ioan requested a real-data Gaussian Process regression warm-up using laser power (P), scan velocity (VX), laser spot radius (LS) and substrate temperature (ST) to predict the first raw timestep at which Conduction is observed. The unit of analysis is one simulation, identified by name. The response is not converted to physical time. This work packages the regression baseline; it does not begin active learning or level-set estimation.

Active learning and level-set estimation were not started.

## What was done

- Audited the pinned Hugging Face CSV (65,472 rows, 241 simulations, SHA-256 964a12d86435e9f0879e2e43384d997e1cc2faa7b9e4c3aeb49cf0e73e3fb154).
- Defined 238 usable simulation-level targets and excluded three simulations with no observed Conduction.
- Compared the 91-simulation no-Screenshot-Bug subgroup with the inclusive 238-simulation broad dataset.
- Evaluated isotropic RBF, ARD RBF, Matérn 3/2 and Matérn 5/2 with experiment-level leave-one-out cross-validation and fold-local input scaling.
- Examined ARD lengthscales as descriptive, non-causal diagnostics.
- Tested Bug/Initial-Emptiness label sequences and their relationship with LS and the other inputs.
- Reviewed the largest 10 no-Bug and 20 broad Matérn 3/2 LOO errors without removing cases.
- Compared L-BFGS-B, SLSQP, Powell and a no-optimization baseline for Matérn 3/2; also performed a limited broad full-data Matérn 5/2 optimizer check.

## Main findings

Matérn 3/2 is the strongest point-prediction kernel on both datasets.

| Dataset | MAE | RMSE | R² | normalized RMSE | mean NLPD | 95% coverage |
|---|---:|---:|---:|---:|---:|---:|
| No-Bug, Matérn 3/2 | 1,735.8 | 2,537.0 | 0.9171 | 0.2863 | 9.8156 | 90.1% |
| Broad, Matérn 3/2 | 11,616.9 | 16,256.3 | 0.4060 | 0.7691 | 11.0404 | 92.9% |

Broad Matérn 5/2 is slightly better on probabilistic calibration (mean NLPD 11.0322 and coverage 93.7%) but slightly worse on point prediction (RMSE 16,402.7). The point-prediction recommendation therefore remains Matérn 3/2, with the calibration distinction reported explicitly.

Broad training worsened predictions on the same 91 no-Bug evaluation points for every kernel. For Matérn 3/2, no-Bug-only training gives RMSE 2,537.0 while broad training gives 17,398.5; broad training improves 10 points and worsens 81. This difference is not evidence that the broad labels are wrong.

The Bug sequence analysis finds:

- 150 of 241 simulations contain Screenshot Bug.
- 0/150 begins with Initial Emptiness in the stored CSV and 0/150 matches the literal Initial-Emptiness-then-Bug ordering.
- All 147 simulations with pre-Conduction Bug frames keep those frames inside the initial contiguous empty-like block.
- 99/150 have one initial Bug block; 51/150 have multiple separated blocks and Bug after a physical regime.

Bug-containing simulations have higher median LS (66.48 µm versus 59.86 µm), but P, VX, ST, initial empty-like duration and target distribution also differ. The Bug subgroup target median is 38,782 versus 13,933 raw timestep units. LS alone weakly predicts Bug occurrence (out-of-fold ROC AUC 0.5952); the four-input model is not better (0.5926). These are associations, not causal results.

The largest broad errors are not enriched for Bug labels: 55% of the top 20 are Bug-containing versus 61.8% overall. Fifteen of the 20 are in the earliest or latest target quartile, 15 fall outside the 95% interval, and their median LS is 75.77 µm versus 64.42 µm overall. Extreme target location and subgroup/design structure are more evident than a Bug-only explanation.

L-BFGS-B, SLSQP and Powell produce practically identical Matérn 3/2 LOO predictions. Clean RMSE differs by less than 0.0002 timestep units and broad RMSE by less than 0.001. Every optimized fit converges, with zero warnings, failures and parameter-bound hits. Powell is substantially slower; SLSQP is faster on the broad run but gives no meaningful predictive gain. The no-optimization baseline is worse, especially for broad uncertainty coverage (81.1%).

The broad full-data Matérn 5/2 check is also optimizer-stable: all three optimizers obtain signal scale 1.01², lengthscale 0.554 and log marginal likelihood about -283.7208.

## Ioan’s clarification and revised interpretation

Ioan clarified after the kernel experiment that the annotator may have labelled only the first empty image as Initial Emptiness and subsequent empty images as Screenshot Bug. Screenshot Bug therefore does not necessarily identify corrupted simulation data. He also suggested that empty images may have become more common after LS began to vary.

The literal stored-label ordering does not reproduce that recollection, but the 147/147 initial-block finding supports its broader repeated-empty-image interpretation. The no-Bug subset is therefore an operational subgroup, not a confirmed higher-quality subset. The clean/broad performance gap is consistent with subgroup or design heterogeneity, shifted input and target distributions, different empty-like durations, and missing batch/design variables.

## Final modelling recommendation

- Kernel: isotropic Matérn 3/2 for point prediction.
- Optimizer: retain sklearn's L-BFGS-B default.
- Data: keep the inclusive broad dataset as the primary data record under the fixed policy; use the 91 no-Bug simulations as a sensitivity subgroup.
- Reporting: state the broad Matérn 5/2 calibration advantage separately and do not imply that no-Bug means higher quality.

## Remaining caveats

- First observed Conduction is a raw simulation timestep, not exact physical transition time.
- Screenshot Bug semantics cannot be recovered conclusively from labels alone.
- The broad mapping is substantially harder and may omit batch/design factors.
- ARD lengthscales and logistic coefficients are descriptive, not causal.
- Gaussian predictive intervals are imperfect, especially for the largest broad errors.

## Suggested discussion point for the meeting

Can the original annotation convention, image sequence, or batch/design metadata be recovered well enough to test whether repeated empty frames or an unrecorded design change explains the broad subgroup heterogeneity? This should be resolved before deciding on a new scientific experiment.
