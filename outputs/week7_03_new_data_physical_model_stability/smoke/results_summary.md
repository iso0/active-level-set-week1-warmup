# Week 7 Phase 3 — new-data physical-response model stability

Mode: **SMOKE (non-scientific preflight)**

Immutable dataset: `ioandanielc/sph_v2@d69dac5bda8b622bc0de316b112815c6056c06ec`.
Repository starting point: `codex/week7-phase1-2-sph-v2-audit@f26f0671dd59938a8111883398fe38afedb6915d`.
The primary validation domain is `partition == new-data`; Week 6 and Week 7 populations were never pooled.

## Model-ready population

The audit retains all 165 new-data experiments. Eligibility was derived from corrected Phase 2 readiness fields: {"depth":164,"kinetic_energy":164,"total_height":164,"width":164}.
The monitor-incomplete experiment remains in `model_ready_population.csv` but is not fabricated into a regression row.

## Primary results

| Target | Raw RMSE winner | Protocol point model | MAE | Rel. MAE | RMSE | Rel. RMSE | R² | Protocol GP | Learned nugget useful? |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| T0 melt-pool width | Linear Ridge | Linear Ridge | 6.59177 um | 4.334% | 8.23571 um | 5.415% | 0.8666 | Matérn 3/2 + learned nugget | yes |
| T0 penetration depth | RBF, numerical jitter | Polynomial Ridge degree 2 | 41.404 um | 58.791% | 71.2737 um | 101.204% | 0.0595 | Matérn 3/2 + learned nugget | yes |
| T0 total vertical melt-pool height | Linear Ridge | Linear Ridge | 43.1356 um | 43.939% | 57.1072 um | 58.171% | 0.3410 | Matérn 3/2 + learned nugget | yes |
| T0 melt kinetic energy | Linear Ridge | Linear Ridge | 0.879762 nJ | 24.927% | 1.15091 nJ | 32.609% | 0.5857 | Matérn 3/2 + learned nugget | no |

Relative errors use `median(abs(y_observed))` as the denominator; each denominator is stored in `relative_error_table.csv`.
A shared learned nugget is interpreted only as improving predictive performance or calibration under the current regression model, not as proof of physical noise.

## Week 6 versus new-data stability

| Week 6 conclusion | New-data evidence | Status | Evidence |
|---|---|---|---|
| GP outperforms Linear Ridge in out-of-sample error | Matérn 3/2 + learned nugget RMSE=17.6082 versus Linear Ridge RMSE=8.23571; paired MAE/RMSE robust advantage=False. | **UNRESOLVED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| GP outperforms degree-2 Polynomial Ridge in raw error | Matérn 3/2 + learned nugget RMSE=17.6082 versus Polynomial Ridge degree 2 RMSE=22.0871; paired MAE/RMSE robust advantage=True. | **REPRODUCED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| A shared learned nugget is useful for predictive performance or calibration under the GP model | useful=True; point advantage=False; calibration advantage=0; NLPD advantage=8.391e-06. | **REPRODUCED** | `noise_treatment_comparison.csv; model_selection_decisions.csv` |
| Week 6 protocol selected Matérn 3/2 + learned nugget | New-data empirical learned-kernel winner=Matérn 5/2 + learned nugget; protocol selection=Matérn 3/2 + learned nugget. | **REPRODUCED** | `kernel_comparison.csv; paired_model_comparisons.csv` |
| GP outperforms Linear Ridge in out-of-sample error | Matérn 3/2 + learned nugget RMSE=59.0598 versus Linear Ridge RMSE=65.8786; paired MAE/RMSE robust advantage=True. | **REPRODUCED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| GP outperforms degree-2 Polynomial Ridge in raw error | Matérn 3/2 + learned nugget RMSE=59.0598 versus Polynomial Ridge degree 2 RMSE=71.2737; paired MAE/RMSE robust advantage=False. | **WEAKENED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| A shared learned nugget is useful for predictive performance or calibration under the GP model | useful=True; point advantage=False; calibration advantage=0; NLPD advantage=1.551e-05. | **REPRODUCED** | `noise_treatment_comparison.csv; model_selection_decisions.csv` |
| Week 6 protocol selected Matérn 3/2 + learned nugget | New-data empirical learned-kernel winner=RBF + learned nugget; protocol selection=Matérn 3/2 + learned nugget. | **REPRODUCED** | `kernel_comparison.csv; paired_model_comparisons.csv` |
| GP outperforms Linear Ridge in out-of-sample error | Matérn 3/2 + learned nugget RMSE=59.254 versus Linear Ridge RMSE=57.1072; paired MAE/RMSE robust advantage=False. | **UNRESOLVED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| GP outperforms degree-2 Polynomial Ridge in raw error | Matérn 3/2 + learned nugget RMSE=59.254 versus Polynomial Ridge degree 2 RMSE=59.7881; paired MAE/RMSE robust advantage=False. | **WEAKENED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| A shared learned nugget is useful for predictive performance or calibration under the GP model | useful=True; point advantage=False; calibration advantage=0; NLPD advantage=8.482e-06. | **REPRODUCED** | `noise_treatment_comparison.csv; model_selection_decisions.csv` |
| Week 6 protocol selected Matérn 3/2 + learned nugget | New-data empirical learned-kernel winner=Matérn 5/2 + learned nugget; protocol selection=Matérn 3/2 + learned nugget. | **REPRODUCED** | `kernel_comparison.csv; paired_model_comparisons.csv` |
| GP outperforms Linear Ridge in out-of-sample error | Matérn 3/2 + learned nugget RMSE=1.29175 versus Linear Ridge RMSE=1.15091; paired MAE/RMSE robust advantage=False. | **UNRESOLVED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| GP outperforms degree-2 Polynomial Ridge in raw error | Matérn 3/2 + learned nugget RMSE=1.29175 versus Polynomial Ridge degree 2 RMSE=2.0266; paired MAE/RMSE robust advantage=False. | **WEAKENED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| A shared learned nugget is useful for predictive performance or calibration under the GP model | useful=False; point advantage=False; calibration advantage=0; NLPD advantage=-0.01977. | **REVERSED** | `noise_treatment_comparison.csv; model_selection_decisions.csv` |
| Week 6 protocol selected Matérn 3/2 + learned nugget | New-data empirical learned-kernel winner=Matérn 3/2 + learned nugget; protocol selection=Matérn 3/2 + learned nugget. | **REPRODUCED** | `kernel_comparison.csv; paired_model_comparisons.csv` |
| Width is relatively simple and degree-2 Polynomial Ridge is competitive with GP | polynomial_ridge_competitive=False; protocol point model=linear_ridge. | **REVERSED** | `model_selection_decisions.csv; model_metric_table.csv` |
| Depth benefits materially from GP flexibility | simple_models_competitive=["polynomial_ridge_degree2"]; protocol point model=polynomial_ridge_degree2. | **REVERSED** | `model_selection_decisions.csv; paired_model_comparisons.csv` |
| Polynomial Ridge is the parsimonious total-height point model; Matérn 3/2 plus nugget supplies uncertainty | new point=linear_ridge; new GP=matern32_learned_nugget; relative RMSE=58.171%. | **WEAKENED** | `week6_vs_new_data_comparison.csv` |
| Linear Ridge is the parsimonious kinetic-energy point model; GP uncertainty remains useful | new point=linear_ridge; relative MAE=24.927%; relative RMSE=32.609%; R2=0.5857. | **REPRODUCED** | `week6_vs_new_data_comparison.csv` |
| Model difficulty should be compared using relative error and ranking, not absolute error alone | depth: higher relative out-of-sample error in the new sampled domain; kinetic_energy: higher relative out-of-sample error in the new sampled domain; total_height: higher relative out-of-sample error in the new sampled domain; width: higher relative out-of-sample error in the new sampled domain | **UNRESOLVED** | `week6_vs_new_data_comparison.csv` |

Differences in absolute MAE/RMSE are not interpreted alone because the sampled design and target scales shifted. The historical table emphasizes relative errors, rankings, nugget behavior and calibration.

## Validation and scope

Validation status counts: `{"FAIL":3,"PASS":19,"WARNING":2}`.
No label was modified, no eligible row was silently removed, and the maximum-kinetic-energy anomaly was not promoted to a Phase 3 target.

**HARD STOP:** no classifier, feature-effect/causal analysis, target redesign, active learning, level-set estimation or later Week 7 phase was run.
