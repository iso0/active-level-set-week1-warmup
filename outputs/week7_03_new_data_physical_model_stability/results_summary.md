# Week 7 Phase 3 — new-data physical-response model stability

Mode: **FULL**

Immutable dataset: `ioandanielc/sph_v2@d69dac5bda8b622bc0de316b112815c6056c06ec`.
Repository starting point: `codex/week7-phase1-2-sph-v2-audit@f26f0671dd59938a8111883398fe38afedb6915d`.
The primary validation domain is `partition == new-data`; Week 6 and Week 7 populations were never pooled.

## Model-ready population

The audit retains all 165 new-data experiments. Eligibility was derived from corrected Phase 2 readiness fields: {"depth":164,"kinetic_energy":164,"total_height":164,"width":164}.
The monitor-incomplete experiment remains in `model_ready_population.csv` but is not fabricated into a regression row.

## Primary results

| Target | Raw RMSE winner | Protocol point model | MAE | Rel. MAE | RMSE | Rel. RMSE | R² | Protocol GP | Learned nugget useful? |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| T0 melt-pool width | Matérn 3/2 + learned nugget | Polynomial Ridge degree 2 | 3.24067 um | 1.945% | 4.29955 um | 2.580% | 0.9861 | Matérn 3/2 + learned nugget | yes |
| T0 penetration depth | Matérn 5/2, numerical jitter | Matérn 3/2 + learned nugget | 11.9375 um | 15.972% | 21.8082 um | 29.178% | 0.9103 | Matérn 3/2 + learned nugget | no |
| T0 total vertical melt-pool height | Matérn 3/2, numerical jitter | Matérn 3/2 + learned nugget | 12.6091 um | 12.530% | 22.4006 um | 22.261% | 0.9002 | Matérn 3/2 + learned nugget | no |
| T0 melt kinetic energy | Matérn 3/2 + learned nugget | Matérn 3/2 + learned nugget | 0.302242 nJ | 9.022% | 0.563873 nJ | 16.832% | 0.8900 | Matérn 3/2 + learned nugget | yes |

Relative errors use `median(abs(y_observed))` as the denominator; each denominator is stored in `relative_error_table.csv`.
A shared learned nugget is interpreted only as improving predictive performance or calibration under the current regression model, not as proof of physical noise.

## Week 6 versus new-data stability

| Week 6 conclusion | New-data evidence | Status | Evidence |
|---|---|---|---|
| GP outperforms Linear Ridge in out-of-sample error | Matérn 3/2 + learned nugget RMSE=3.5047 versus Linear Ridge RMSE=10.8163; paired MAE/RMSE robust advantage=True. | **REPRODUCED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| GP outperforms degree-2 Polynomial Ridge in raw error | Matérn 3/2 + learned nugget RMSE=3.5047 versus Polynomial Ridge degree 2 RMSE=4.29955; paired MAE/RMSE robust advantage=True. | **REPRODUCED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| A shared learned nugget is useful for predictive performance or calibration under the GP model | useful=True; point advantage=False; calibration advantage=0.03659; NLPD advantage=0.03166. | **REPRODUCED** | `noise_treatment_comparison.csv; model_selection_decisions.csv` |
| Week 6 protocol selected Matérn 3/2 + learned nugget | New-data empirical learned-kernel winner=Matérn 3/2 + learned nugget; protocol selection=Matérn 3/2 + learned nugget. | **REPRODUCED** | `kernel_comparison.csv; paired_model_comparisons.csv` |
| GP outperforms Linear Ridge in out-of-sample error | Matérn 3/2 + learned nugget RMSE=21.8082 versus Linear Ridge RMSE=43.2581; paired MAE/RMSE robust advantage=True. | **REPRODUCED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| GP outperforms degree-2 Polynomial Ridge in raw error | Matérn 3/2 + learned nugget RMSE=21.8082 versus Polynomial Ridge degree 2 RMSE=33.6038; paired MAE/RMSE robust advantage=True. | **REPRODUCED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| A shared learned nugget is useful for predictive performance or calibration under the GP model | useful=False; point advantage=False; calibration advantage=0.006098; NLPD advantage=-0.02599. | **REVERSED** | `noise_treatment_comparison.csv; model_selection_decisions.csv` |
| Week 6 protocol selected Matérn 3/2 + learned nugget | New-data empirical learned-kernel winner=Matérn 3/2 + learned nugget; protocol selection=Matérn 3/2 + learned nugget. | **REPRODUCED** | `kernel_comparison.csv; paired_model_comparisons.csv` |
| GP outperforms Linear Ridge in out-of-sample error | Matérn 3/2 + learned nugget RMSE=22.4006 versus Linear Ridge RMSE=44.5167; paired MAE/RMSE robust advantage=True. | **REPRODUCED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| GP outperforms degree-2 Polynomial Ridge in raw error | Matérn 3/2 + learned nugget RMSE=22.4006 versus Polynomial Ridge degree 2 RMSE=34.2421; paired MAE/RMSE robust advantage=True. | **REPRODUCED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| A shared learned nugget is useful for predictive performance or calibration under the GP model | useful=False; point advantage=False; calibration advantage=0; NLPD advantage=-0.01604. | **REVERSED** | `noise_treatment_comparison.csv; model_selection_decisions.csv` |
| Week 6 protocol selected Matérn 3/2 + learned nugget | New-data empirical learned-kernel winner=Matérn 5/2 + learned nugget; protocol selection=Matérn 3/2 + learned nugget. | **REPRODUCED** | `kernel_comparison.csv; paired_model_comparisons.csv` |
| GP outperforms Linear Ridge in out-of-sample error | Matérn 3/2 + learned nugget RMSE=0.563873 versus Linear Ridge RMSE=0.730832; paired MAE/RMSE robust advantage=True. | **REPRODUCED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| GP outperforms degree-2 Polynomial Ridge in raw error | Matérn 3/2 + learned nugget RMSE=0.563873 versus Polynomial Ridge degree 2 RMSE=0.678717; paired MAE/RMSE robust advantage=True. | **REPRODUCED** | `fold_level_predictions.csv; paired_model_comparisons.csv` |
| A shared learned nugget is useful for predictive performance or calibration under the GP model | useful=True; point advantage=False; calibration advantage=0.01829; NLPD advantage=0.1259. | **REPRODUCED** | `noise_treatment_comparison.csv; model_selection_decisions.csv` |
| Week 6 protocol selected Matérn 3/2 + learned nugget | New-data empirical learned-kernel winner=Matérn 3/2 + learned nugget; protocol selection=Matérn 3/2 + learned nugget. | **REPRODUCED** | `kernel_comparison.csv; paired_model_comparisons.csv` |
| Width is relatively simple and degree-2 Polynomial Ridge is competitive with GP | polynomial_ridge_competitive=True; protocol point model=polynomial_ridge_degree2. | **REPRODUCED** | `model_selection_decisions.csv; model_metric_table.csv` |
| Depth benefits materially from GP flexibility | simple_models_competitive=[]; protocol point model=matern32_learned_nugget. | **REPRODUCED** | `model_selection_decisions.csv; paired_model_comparisons.csv` |
| Polynomial Ridge is the parsimonious total-height point model; Matérn 3/2 plus nugget supplies uncertainty | new point=matern32_learned_nugget; new GP=matern32_learned_nugget; relative RMSE=22.261%. | **WEAKENED** | `week6_vs_new_data_comparison.csv` |
| Linear Ridge is the parsimonious kinetic-energy point model; GP uncertainty remains useful | new point=matern32_learned_nugget; relative MAE=9.022%; relative RMSE=16.832%; R2=0.8900. | **WEAKENED** | `week6_vs_new_data_comparison.csv` |
| Model difficulty should be compared using relative error and ranking, not absolute error alone | depth: higher relative out-of-sample error in the new sampled domain; kinetic_energy: higher relative out-of-sample error in the new sampled domain; total_height: higher relative out-of-sample error in the new sampled domain; width: lower relative out-of-sample error in the new sampled domain | **UNRESOLVED** | `week6_vs_new_data_comparison.csv` |
| The Week 6 candidate/evaluation pipeline and all target-specific final model choices transfer unchanged | The fold-local LOO comparison pipeline remains adequate without new kernels or a larger search, but total-height and kinetic-energy point choices changed and the learned-nugget conclusion reversed for depth and total height. | **WEAKENED** | `model_selection_decisions.csv; week6_vs_new_data_comparison.csv; noise_treatment_comparison.csv` |

Differences in absolute MAE/RMSE are not interpreted alone because the sampled design and target scales shifted. The historical table emphasizes relative errors, rankings, nugget behavior and calibration.

## Pipeline decision

The **comparison/evaluation pipeline is adequate without adding kernels or expanding the search**, but the Week 6 target-specific final choices should **not** be frozen unchanged. Width retains the parsimonious polynomial point model; depth retains a GP family but no longer supports a shared nugget as the preferred uncertainty treatment; total height and kinetic energy now require GP point models under the preserved selection protocol; and total height also no longer supports the shared nugget.

## Validation and scope

Validation status counts: `{"PASS":24}`.
No label was modified, no eligible row was silently removed, and the maximum-kinetic-energy anomaly was not promoted to a Phase 3 target.

**HARD STOP:** no classifier, feature-effect/causal analysis, target redesign, active learning, level-set estimation or later Week 7 phase was run.
