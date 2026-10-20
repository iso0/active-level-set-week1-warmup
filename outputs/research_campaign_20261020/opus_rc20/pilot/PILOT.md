# RC20 pilot — remedy selection (pre-registered rule, PROTOCOL_RC20_STAGE1.md section 5) and timing

**Rule outcome: NONE.** Δ(FD) = +0.0100 (better in 19/80 unit-budgets), Δ(MAP) = +0.0021 (better in 60/80).

Mean per-unit test log loss by budget (pilot units; DEV):

| budget | SHQ_ATS | SHQ_ATS_FD | SHQM_ATS | SHQ_A | M0Q_A | SHQ_ATS_H | SHQT_ATS |
|---|---|---|---|---|---|---|---|
| 8.0000 | 0.5852 | 0.5440 | 2.5403 | 0.5542 | 0.4897 | 0.4712 | 0.3011 |
| 12.0000 | 0.2738 | 0.2914 | 0.3050 | 0.3463 | 0.3468 | 0.2311 | 0.2508 |
| 16.0000 | 0.2177 | 0.2323 | 0.2126 | 0.2730 | 0.2832 | 0.1906 | 0.2291 |
| 20.0000 | 0.1804 | 0.1850 | 0.1673 | 0.2321 | 0.2586 | 0.1657 | 0.2112 |
| 24.0000 | 0.1583 | 0.1615 | 0.1536 | 0.1982 | 0.2072 | 0.1485 | 0.1802 |
| 40.0000 | 0.1362 | 0.1378 | 0.1339 | 0.1558 | 0.1577 | 0.1284 | 0.1590 |
| 60.0000 | 0.1233 | 0.1234 | 0.1210 | 0.1316 | 0.1309 | 0.1174 | 0.1311 |

Mechanism diagnostics (means over pilot units): RMS differences of the training features, in units of the feature SD; honest = out-of-fold (refitted hyperparameters), approx = RC19 closed-form LOO of the full fit, in-sample = the full fit at the paid runs; classifier coefficient norms; spread of the fold models' log lengthscales and their mean absolute deviation from the full fit:

| budget | rms_oof_vs_approx_A | rms_oof_vs_approx_T | rms_oof_vs_approx_S | rms_oof_vs_insample_A | rms_oof_vs_insample_T | rms_oof_vs_insample_S | rms_approx_vs_insample_A | rms_approx_vs_insample_T | rms_approx_vs_insample_S | coef_norm_honest | coef_norm_approx | fold_logell_sd | fold_logell_absdev_from_full |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8.000 | 1.133 | 1.872 | 1.440 | 1.541 | 2.321 | 1.953 | 0.707 | 0.997 | 0.812 | 1.079 | 1.181 | 1.213 | 1.049 |
| 12.000 | 0.542 | 0.707 | 0.591 | 0.903 | 1.011 | 0.949 | 0.579 | 0.537 | 0.528 | 1.181 | 1.335 | 0.550 | 0.384 |
| 16.000 | 0.416 | 0.467 | 0.397 | 0.756 | 0.754 | 0.688 | 0.504 | 0.446 | 0.426 | 1.337 | 1.436 | 0.470 | 0.326 |
| 20.000 | 0.267 | 0.266 | 0.264 | 0.677 | 0.615 | 0.593 | 0.550 | 0.483 | 0.432 | 1.444 | 1.543 | 0.251 | 0.185 |
| 24.000 | 0.222 | 0.194 | 0.228 | 0.652 | 0.530 | 0.531 | 0.549 | 0.442 | 0.414 | 1.516 | 1.618 | 0.217 | 0.158 |
| 40.000 | 0.219 | 0.183 | 0.189 | 0.575 | 0.474 | 0.442 | 0.495 | 0.405 | 0.353 | 1.704 | 1.725 | 0.240 | 0.184 |
| 60.000 | 0.215 | 0.162 | 0.160 | 0.573 | 0.430 | 0.374 | 0.498 | 0.380 | 0.305 | 1.694 | 1.806 | 0.238 | 0.187 |

Seconds per budget (all constructions incl. both remedy candidates and diagnostics):

| budget | mean | max |
|---|---|---|
| 8.00 | 1.63 | 2.97 |
| 12.00 | 2.01 | 3.31 |
| 16.00 | 1.97 | 3.54 |
| 20.00 | 1.89 | 2.66 |
| 24.00 | 1.96 | 2.29 |
| 40.00 | 2.33 | 2.90 |
| 60.00 | 2.78 | 3.44 |

