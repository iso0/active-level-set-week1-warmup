# Week 9 Phase 1.5 — final static-model and calibration audit

## Scope and protocol

This report describes the analysis that was actually executed. It is not a prospective design memo. Every result uses the exact frozen Week 8.5 population and outer splits: 405 simulations, 20 repeat blocks × 5 folds, 324 training/query-pool rows and 81 untouched test rows per fold. `has_keyhole` is the manual target; `ST` is substrate temperature; `LS` is the Gaussian laser spot radius stored in metres. Fold-B1-q20/q30 contain 17/25 test rows and are evaluation-only.

All scalers and models were fitted on the 324 training rows. Paired intervals resample the 20 repeat blocks while retaining all five folds. They quantify stability across the frozen split design, not transfer to new materials or physical experiments.

## Executed model set

| ID | Representation and estimator | Role |
|---|---|---|
| `log_h_logistic` | `log(P / sqrt(VX*LS^3))`, train-only scaling, logistic regression | Primary one-dimensional physics score |
| `log_h_st_logistic` | `log(h/(1933 K - ST))`, train-only scaling, logistic regression | Partial liquidus-temperature sensitivity; not a full dimensionless Keyhole number |
| `logistic_M1` | Standardized P, VX, LS, ST main effects | Transparent 4D comparator |
| `logistic_M3` | M1 plus the declared interaction | Parsimonious interaction comparator |
| `gpc_1d_h` | `log(h)` with the canonical GPC | Nonlinear 1D sensitivity |
| `gpc_4d` | P, VX, LS, ST with the canonical GPC | Canonical nonlinear baseline |
| `gpc_5d_h_augmented` | P, VX, LS, ST, `log(h)` with the canonical GPC | Redundant-coordinate representation sensitivity |
| declared scalar scores | train-only scalar logistic calibration | Small, fixed physics-score benchmark |

The GPC uses `ConstantKernel × Matern(nu=1.5)` with the repository's fixed bounds and zero optimizer restarts. `log(h)` is deterministic in P, VX and LS, so the 5D model contains no new information; any change is a representation effect.

## Static discrimination and boundary performance

The principal 20-repeat means are:

| Model | Full ROC-AUC | Full PR-AUC | Full balanced accuracy | q20 ROC-AUC | q20 Keyhole recall |
|---|---:|---:|---:|---:|---:|
| `log_h_logistic` | 0.989697 | 0.950055 | 0.922196 | 0.903899 | 0.709549 |
| `gpc_4d` | 0.992587 | 0.968286 | 0.925087 | 0.919710 | 0.732327 |
| `gpc_5d_h_augmented` | 0.992171 | 0.966363 | 0.927299 | 0.917175 | 0.740425 |
| `logistic_M3` | 0.993411 | 0.970959 | 0.934073 | 0.925785 | 0.765200 |

The one-dimensional h model is a strong global discriminator, but it is not equivalent to the full 4D boundary model. On q20, its Keyhole-recall difference versus GPC-4D is -0.022777 with a repeat-block 95% interval [-0.043764, -0.001615]. Full-fold ROC-AUC and PR-AUC are also lower. This is evidence that residual multivariate structure matters near the empirical boundary.

Adding deterministic `log(h)` to the 4D GPC did not improve it: the full-fold ROC-AUC difference was -0.000417 and the q20 ROC-AUC difference was -0.002535. The temperature sensitivity `log(h/(1933-ST))` also did not help: full balanced-accuracy difference versus `log(h)` was -0.004870, interval [-0.006774, -0.003082], and Brier score was worse by +0.000773, interval [+0.000736, +0.000812]. This only tests a partial temperature correction over the observed 300–400 K range.

Detailed repeat metrics and paired contrasts are saved in `static_repeat_metrics.csv`, `static_model_summary.csv`, and `static_paired_contrasts.csv`.

## Empirical exponent recovery

The executed exponent model used unstandardized `log(P)`, `log(VX)`, and `log(LS)` predictors. It did not include ST. The recovered ratios were:

| Ratio | Estimate | Stratified row-bootstrap 95% interval | Theory |
|---|---:|---:|---:|
| VX exponent / P exponent | -0.517798 | [-0.659198, -0.381127] | -0.5 |
| LS exponent / P exponent | -1.444157 | [-1.994969, -1.074209] | -1.5 |

The intervals come from 1,000 deterministic stratified row-bootstrap draws on the fixed 405-row simulator population. The 100 training-fold estimates are separately saved for split-stability inspection. Both theoretical values lie inside their intervals, so the safe conclusion is “consistent with the proposed coordinate,” not discovery, proof, or physical validation.

## OOF screening and calibration

For each simulation, the 20 held-out `log_h_logistic` probabilities were averaged to form a 405-row repeated-OOF ensemble. Fixed retrospective zones gave:

| Zone | Count | Keyhole | Conduction | Screening diagnostic |
|---|---:|---:|---:|---|
| p < 0.05 | 295 | 1 | 294 | NPV 0.99661 |
| 0.05 ≤ p ≤ 0.95 | 62 | 26 | 36 | ambiguous |
| p > 0.95 | 48 | 46 | 2 | PPV 0.95833 |

This is a retrospective simulator-domain screening rule, not an industrial safety rule or a prospectively calibrated deployment threshold.

Using 10 fixed equal-width probability bins, the same unique-row OOF ensemble had ECE 0.018662, MCE 0.358952, and Brier score 0.029425. The largest calibration gap came from a bin containing only three rows; therefore a small ECE and large MCE are not contradictory. Counts and gaps for every non-empty bin are preserved in `calibration_summary.json`.

## Residual-case analysis

`residual_case_analysis.csv` compares each row's mean OOF probabilities and ensemble decisions for the h-logistic and 4D GPC models, together with P, VX, LS, ST, label, `log(h)`, and q20/q30 membership frequencies. The delivered residual flags are ensemble-level diagnostics. They do not estimate per-repeat error-rate contrasts and must not be described as stable causal subgroups. The residual map supports only the limited conclusion that pure h compression misses some boundary-relevant 4D structure.

## GPC optimization diagnostics

All static GPC fits completed without logistic fallback. Kernel-bound hits occurred in 0/100 1D fits, 38/100 4D fits, and 1/100 5D fits. Protocol-matched discrimination comparisons remain usable, but probability/calibration interpretation for the GPCs is qualified by this optimizer-bound behavior. Exact fold-level diagnostics are in `gpc_kernel_bound_diagnostics.csv`.

## Audit decision

**PASS with explicit qualifications.** The frozen protocol was respected and the implemented outputs support the main static conclusions: h is a compact, physics-consistent score with strong discrimination; it loses measurable information near the boundary; the redundant 5D embedding does not improve the 4D GPC; and the partial ST correction is not beneficial here. The evidence is retrospective, single-material, simulator-domain evidence and does not establish causality, transfer, or a deployment guarantee.

The following ideas were not part of the delivered analysis and remain future-work options only: a full material-property Keyhole number, delta-method exponent intervals, per-repeat screening-zone stability tables, per-repeat residual error-rate contrasts, and an additive physics-ridge-plus-residual GP.
