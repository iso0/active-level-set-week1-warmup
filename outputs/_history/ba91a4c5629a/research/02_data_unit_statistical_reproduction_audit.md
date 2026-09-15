# Phase 1.5 data, units and statistical reproduction audit

## Canonical identity and units

- Population: 405 unique simulations; 73 manual experiment-level Keyhole and 332 Conduction.
- Inputs: `P` in W, `VX` in m/s, `LS` in m, `ST` in K.
- Ranges: P 52.545–449.762 W; VX 0.2010–0.9983 m/s; LS 40.029–89.704 µm; ST 300.0–399.818 K.
- `ST` is substrate temperature.
- Authoritative code trace: `week6_phase3_5_regime_target_design.load_metadata_map` reads `details["lasers"]["single_gaussian_laser"]["physics"]["shape"]["spot_radius"]` and asserts equality to `parameters["laser_spot_size"]`. Therefore `LS` is the Gaussian spot radius `r0`, not diameter.
- Canonical population SHA-256: `c15658cac87a8616a1984185ec1afc8126a1db811f0d5819e62cfb621a7486c7`.

## Frozen protocol reproduction

The logical canonical JSON hash is `bb16865a06d8fbdeea00f8c41f0929bfb7fbaf2f7b3e4ebade9cb2ffc59b1c66`. Windows CRLF checkout bytes differ from the recorded raw byte hash, so Phase 1.5 verifies the parsed canonical JSON bytes and never rewrites the historical file.

All exact invariants passed:

- 20 repeat blocks × 5 grouped folds = 100 outer runs;
- 324 training/query-pool rows and 81 untouched test rows per run;
- exact saved 16-row initial design in every run;
- Fold-B1-q20 = 17 and q30 = 25 held-out rows;
- physical-input groups are train/test disjoint;
- B1 is evaluation-only.

The saved Week 8.5 AULC means were reproduced without rerunning the 3000 Random paths:

| Quantity | Value |
|---|---:|
| 4D Margin mean q20 AULC 16–80 | 0.8135202 |
| matched Random mean q20 AULC 16–80 | 0.7762204 |
| reproduced difference | 0.0372998 |
| recorded grouped-bootstrap mean difference | 0.0373096 |
| absolute discrepancy | 0.00000981 |

Baseline reproduction status: **PASS**.

## Static statistical results

Every model used the same exact frozen folds. Metrics were pooled over the five held-out folds within each repeat, and paired uncertainty resampled the 20 repeat blocks rather than treating 100 folds as independent datasets.

- Empirical exponent ratios: VX/P `-0.518` (95% bootstrap `[-0.659,-0.381]`) and LS/P `-1.444` (`[-1.995,-1.074]`). Both theory values `-0.5` and `-1.5` lie inside the intervals: **consistent**, not independently discovered.
- `log(h)` logistic full-fold ROC-AUC `0.98970`, PR-AUC `0.95005`, balanced accuracy `0.92220`.
- Canonical 4D GPC full-fold ROC-AUC `0.99259`, PR-AUC `0.96829`, balanced accuracy `0.92509`.
- On q20, `log(h)` Keyhole recall `0.70955` versus 4D GPC `0.73233`; paired difference `-0.02278`, 95% interval `[-0.04376,-0.00162]`.
- The 5D redundant GPC did not improve probability quality: versus 4D, full ROC-AUC difference `-0.000417` and Brier deterioration `+0.000584`; q20 ROC-AUC difference `-0.002535`.
- The fixed `h/(1933 K-ST)` sensitivity uses Gan et al. (2021) Supplementary Table 3 and was worse than bare `h`. Exact differences are regenerated in the static tables. This does not prove temperature is physically irrelevant; it says the chosen partial normalization adds no predictive value in this narrow ST domain.

## OOF screening audit

The 405 unique-row probabilities are averages of 20 predictions, each made while that row was held out. With fixed zones `p<0.05`, `0.05<=p<=0.95`, `p>0.95`:

| Zone | n | Keyhole | Conduction | Relevant predictive value |
|---|---:|---:|---:|---:|
| low | 295 | 1 | 294 | NPV 0.99661 |
| ambiguous | 62 | 26 | 36 | — |
| high | 48 | 46 | 2 | PPV 0.95833 |

This is a retrospective simulator-domain screening rule, not a manufacturing safety rule. Ten equal-width-bin OOF ECE is `0.01866`, MCE `0.35895`, and Brier `0.02943`. The small ECE and large MCE are compatible: ECE downweights sparse bins, while MCE is controlled by a worst bin containing only three rows.

Artifacts: `data_and_protocol_audit.json`, `split_integrity.csv`, `baseline_reproduction_gate.json`, `empirical_exponent_summary.csv`, `static_model_summary.csv`, `static_paired_contrasts.csv`, `screening_zone_summary.csv`, and `calibration_summary.json`.
