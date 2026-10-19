# RC19B Keyhole — final paired adaptive comparison (fresh DEV repeats 11–18; frozen protocol PROTOCOL_RC19B.md)

**PRIMARY — ATSCF_MARGIN − E1CAL+straddle, LL_AULC (lower is better, margin 0.02): INCOMPLETE (1/8)** (mean Δ -0.0278 ± nan SE; good direction in 1/1 repeats)

## Pre-declared contrasts (verdict rule: mean beyond the margin AND ≥ 7 of 8 repeats in the same direction)

| role | contrast | metric | direction | margin | mean | se | min | max | repeats_good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| PRIMARY | ATSCF_MARGIN − E1CAL+straddle | LL_AULC | lower | 0.0200 | -0.0278 | – | -0.0278 | -0.0278 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − E1CAL+straddle | BA_AULC | higher | 0.0200 | -0.0001 | – | -0.0001 | -0.0001 | 0/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − E1CAL+straddle | LL_AULC | lower | 0.0200 | -0.0278 | – | -0.0278 | -0.0278 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − E1CAL+straddle | Brier_AULC | lower | 0.0050 | -0.0026 | – | -0.0026 | -0.0026 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − E1RAW+straddle | BA_AULC | higher | 0.0200 | -0.0025 | – | -0.0025 | -0.0025 | 0/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − E1RAW+straddle | LL_AULC | lower | 0.0200 | -0.0616 | – | -0.0616 | -0.0616 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − E1RAW+straddle | Brier_AULC | lower | 0.0050 | -0.0030 | – | -0.0030 | -0.0030 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − DEPTHCF_MARGIN | BA_AULC | higher | 0.0200 | 0.0099 | – | 0.0099 | 0.0099 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − DEPTHCF_MARGIN | LL_AULC | lower | 0.0200 | -0.0191 | – | -0.0191 | -0.0191 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − DEPTHCF_MARGIN | Brier_AULC | lower | 0.0050 | -0.0066 | – | -0.0066 | -0.0066 | 1/1 | INCOMPLETE (1/8) |
| secondary | DEPTHCF_MARGIN − E1CAL+straddle | BA_AULC | higher | 0.0200 | -0.0099 | – | -0.0099 | -0.0099 | 0/1 | INCOMPLETE (1/8) |
| secondary | DEPTHCF_MARGIN − E1CAL+straddle | LL_AULC | lower | 0.0200 | -0.0087 | – | -0.0087 | -0.0087 | 1/1 | INCOMPLETE (1/8) |
| secondary | DEPTHCF_MARGIN − E1CAL+straddle | Brier_AULC | lower | 0.0050 | 0.0040 | – | 0.0040 | 0.0040 | 0/1 | INCOMPLETE (1/8) |
| secondary | E1CAL+straddle − E1RAW+straddle | BA_AULC | higher | 0.0200 | -0.0024 | – | -0.0024 | -0.0024 | 0/1 | INCOMPLETE (1/8) |
| secondary | E1CAL+straddle − E1RAW+straddle | LL_AULC | lower | 0.0200 | -0.0338 | – | -0.0338 | -0.0338 | 1/1 | INCOMPLETE (1/8) |
| secondary | E1CAL+straddle − E1RAW+straddle | Brier_AULC | lower | 0.0050 | -0.0004 | – | -0.0004 | -0.0004 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − ATSAPPROX_MARGIN | BA_AULC | higher | 0.0200 | -0.0063 | – | -0.0063 | -0.0063 | 0/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − ATSAPPROX_MARGIN | LL_AULC | lower | 0.0200 | 0.0325 | – | 0.0325 | 0.0325 | 0/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − ATSAPPROX_MARGIN | Brier_AULC | lower | 0.0050 | 0.0074 | – | 0.0074 | 0.0074 | 0/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − G3_MARGIN | BA_AULC | higher | 0.0200 | 0.0144 | – | 0.0144 | 0.0144 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − G3_MARGIN | LL_AULC | lower | 0.0200 | -0.0913 | – | -0.0913 | -0.0913 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSCF_MARGIN − G3_MARGIN | Brier_AULC | lower | 0.0050 | -0.0255 | – | -0.0255 | -0.0255 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSAPPROX_MARGIN − E1RAW+straddle | BA_AULC | higher | 0.0200 | 0.0038 | – | 0.0038 | 0.0038 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSAPPROX_MARGIN − E1RAW+straddle | LL_AULC | lower | 0.0200 | -0.0941 | – | -0.0941 | -0.0941 | 1/1 | INCOMPLETE (1/8) |
| secondary | ATSAPPROX_MARGIN − E1RAW+straddle | Brier_AULC | lower | 0.0050 | -0.0104 | – | -0.0104 | -0.0104 | 1/1 | INCOMPLETE (1/8) |

## AULC over B8–B60 (mean and SE over the 8 repeats)

| arm | BA_AULC_mean | BA_AULC_se | sens_AULC_mean | sens_AULC_se | spec_AULC_mean | spec_AULC_se | LL_AULC_mean | LL_AULC_se | Brier_AULC_mean | Brier_AULC_se | AUC_AULC_mean | AUC_AULC_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.9463 | – | 0.9323 | – | 0.9604 | – | 0.1387 | – | 0.0381 | – | 0.9867 | – |
| ATSCF_MARGIN | 0.9401 | – | 0.9233 | – | 0.9568 | – | 0.1712 | – | 0.0455 | – | 0.9807 | – |
| DEPTHCF_MARGIN | 0.9302 | – | 0.9087 | – | 0.9517 | – | 0.1903 | – | 0.0521 | – | 0.9787 | – |
| E1CAL+straddle | 0.9401 | – | 0.9353 | – | 0.9450 | – | 0.1990 | – | 0.0481 | – | 0.9781 | – |
| E1RAW+straddle | 0.9426 | – | 0.9490 | – | 0.9362 | – | 0.2328 | – | 0.0485 | – | 0.9827 | – |
| G3_MARGIN | 0.9257 | – | 0.9020 | – | 0.9493 | – | 0.2625 | – | 0.0711 | – | 0.9622 | – |

## BA ≥ 0.93: first qualifying budget and confirmation spend (b + 4 of the first confirmed pair; total revealed simulations, startup included)

| arm | confirmed | censored | first_mean | first_median | spend_mean | spend_median | spend_min | spend_max | spend_per_repeat |
|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 1/1 | 0 | 14.00 | 14.00 | 18.00 | 18.00 | 18 | 18 | 18 |
| ATSCF_MARGIN | 1/1 | 0 | 20.00 | 20.00 | 24.00 | 24.00 | 24 | 24 | 24 |
| DEPTHCF_MARGIN | 1/1 | 0 | 25.00 | 25.00 | 29.00 | 29.00 | 29 | 29 | 29 |
| E1CAL+straddle | 1/1 | 0 | 17.00 | 17.00 | 21.00 | 21.00 | 21 | 21 | 21 |
| E1RAW+straddle | 1/1 | 0 | 16.00 | 16.00 | 20.00 | 20.00 | 20 | 20 | 20 |
| G3_MARGIN | 1/1 | 0 | 25.00 | 25.00 | 29.00 | 29.00 | 29 | 29 | 29 |

Paired confirmation-spend differences (both confirmed; censoring counted separately):

| contrast | both_confirmed | mean_difference | fewer/equal/more | only_first_censored | only_second_censored | both_censored | per_repeat_first/second |
|---|---|---|---|---|---|---|---|
| ATSCF_MARGIN − E1CAL+straddle | 1 | 3.00 | 0/0/1 | 0 | 0 | 0 | 24/21 |
| ATSCF_MARGIN − E1RAW+straddle | 1 | 4.00 | 0/0/1 | 0 | 0 | 0 | 24/20 |
| ATSCF_MARGIN − DEPTHCF_MARGIN | 1 | -5.00 | 1/0/0 | 0 | 0 | 0 | 24/29 |
| DEPTHCF_MARGIN − E1CAL+straddle | 1 | 8.00 | 0/0/1 | 0 | 0 | 0 | 29/21 |
| E1CAL+straddle − E1RAW+straddle | 1 | 1.00 | 0/0/1 | 0 | 0 | 0 | 21/20 |
| ATSCF_MARGIN − ATSAPPROX_MARGIN | 1 | 6.00 | 0/0/1 | 0 | 0 | 0 | 24/18 |
| ATSCF_MARGIN − G3_MARGIN | 1 | -5.00 | 1/0/0 | 0 | 0 | 0 | 24/29 |
| ATSAPPROX_MARGIN − E1RAW+straddle | 1 | -2.00 | 1/0/0 | 0 | 0 | 0 | 18/20 |

## Reliability with uncertainty

Calibration slope / intercept (logistic recalibration of y on logit p; 1 / 0 = calibrated), ECE and calibration-in-the-large: mean and SE over repeats; bins_mean_p_inside_Wilson95 = reliability bins (pooled over repeats and folds) whose mean prediction lies inside the Wilson 95 % interval of the observed frequency.

| arm | budget | cal_slope | cal_slope_se | cal_intercept | cal_intercept_se | ECE | ECE_se | cal_in_large | cal_in_large_se | bins | bins_mean_p_inside_Wilson95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | 1.619 | – | 0.190 | – | 0.049 | – | -0.002 | – | 10 | 7 |
| ATSAPPROX_MARGIN | 24 | 1.490 | – | -0.125 | – | 0.038 | – | 0.013 | – | 10 | 9 |
| ATSAPPROX_MARGIN | 40 | 1.315 | – | -0.090 | – | 0.023 | – | 0.007 | – | 10 | 9 |
| ATSAPPROX_MARGIN | 60 | 1.194 | – | -0.150 | – | 0.029 | – | 0.008 | – | 10 | 10 |
| ATSCF_MARGIN | 16 | 1.543 | – | 0.252 | – | 0.056 | – | -0.002 | – | 10 | 9 |
| ATSCF_MARGIN | 24 | 1.632 | – | -0.180 | – | 0.059 | – | 0.024 | – | 10 | 8 |
| ATSCF_MARGIN | 40 | 1.590 | – | -0.096 | – | 0.055 | – | 0.017 | – | 10 | 8 |
| ATSCF_MARGIN | 60 | 1.245 | – | -0.122 | – | 0.025 | – | 0.009 | – | 10 | 9 |
| DEPTHCF_MARGIN | 16 | 2.488 | – | 0.237 | – | 0.113 | – | 0.008 | – | 10 | 4 |
| DEPTHCF_MARGIN | 24 | 1.897 | – | 0.010 | – | 0.079 | – | 0.020 | – | 10 | 6 |
| DEPTHCF_MARGIN | 40 | 1.510 | – | -0.173 | – | 0.040 | – | 0.018 | – | 10 | 9 |
| DEPTHCF_MARGIN | 60 | 1.364 | – | -0.090 | – | 0.028 | – | 0.011 | – | 10 | 10 |
| E1CAL+straddle | 16 | 0.758 | – | -0.480 | – | 0.036 | – | 0.031 | – | 10 | 9 |
| E1CAL+straddle | 24 | 0.949 | – | -0.530 | – | 0.036 | – | 0.030 | – | 10 | 9 |
| E1CAL+straddle | 40 | 0.854 | – | -0.488 | – | 0.020 | – | 0.018 | – | 10 | 9 |
| E1CAL+straddle | 60 | 1.349 | – | -0.542 | – | 0.029 | – | 0.022 | – | 10 | 8 |
| E1RAW+straddle | 16 | 0.459 | – | -0.909 | – | 0.048 | – | 0.037 | – | 10 | 6 |
| E1RAW+straddle | 24 | 0.505 | – | -1.006 | – | 0.047 | – | 0.041 | – | 10 | 7 |
| E1RAW+straddle | 40 | 0.486 | – | -0.678 | – | 0.036 | – | 0.021 | – | 10 | 7 |
| E1RAW+straddle | 60 | 0.704 | – | -0.850 | – | 0.033 | – | 0.022 | – | 10 | 9 |
| G3_MARGIN | 16 | 2.334 | – | -0.320 | – | 0.185 | – | 0.076 | – | 10 | 5 |
| G3_MARGIN | 24 | 2.324 | – | 0.059 | – | 0.148 | – | 0.060 | – | 10 | 5 |
| G3_MARGIN | 40 | 1.706 | – | -0.569 | – | 0.073 | – | 0.048 | – | 10 | 5 |
| G3_MARGIN | 60 | 1.650 | – | -0.250 | – | 0.057 | – | 0.029 | – | 10 | 8 |

Reliability-diagram bins: report/keyhole_final_reliability_bins.csv.

## Hard fast-scan corner (NEW-batch conduction test runs; evaluator-only diagnostic): conduction recall and error COUNTS summed over repeats

| arm | budget | spec_NEW_mean | spec_NEW_min | spec_NEW_max | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | 0.250 | 0.250 | 0.250 | 9 | 12 |
| ATSAPPROX_MARGIN | 24 | 0.333 | 0.333 | 0.333 | 8 | 12 |
| ATSAPPROX_MARGIN | 40 | 0.333 | 0.333 | 0.333 | 8 | 12 |
| ATSAPPROX_MARGIN | 60 | 0.417 | 0.417 | 0.417 | 7 | 12 |
| ATSCF_MARGIN | 16 | 0.333 | 0.333 | 0.333 | 8 | 12 |
| ATSCF_MARGIN | 24 | 0.500 | 0.500 | 0.500 | 6 | 12 |
| ATSCF_MARGIN | 40 | 0.417 | 0.417 | 0.417 | 7 | 12 |
| ATSCF_MARGIN | 60 | 0.417 | 0.417 | 0.417 | 7 | 12 |
| DEPTHCF_MARGIN | 16 | 0.583 | 0.583 | 0.583 | 5 | 12 |
| DEPTHCF_MARGIN | 24 | 0.500 | 0.500 | 0.500 | 6 | 12 |
| DEPTHCF_MARGIN | 40 | 0.417 | 0.417 | 0.417 | 7 | 12 |
| DEPTHCF_MARGIN | 60 | 0.500 | 0.500 | 0.500 | 6 | 12 |
| E1CAL+straddle | 16 | 0.250 | 0.250 | 0.250 | 9 | 12 |
| E1CAL+straddle | 24 | 0.333 | 0.333 | 0.333 | 8 | 12 |
| E1CAL+straddle | 40 | 0.500 | 0.500 | 0.500 | 6 | 12 |
| E1CAL+straddle | 60 | 0.417 | 0.417 | 0.417 | 7 | 12 |
| E1RAW+straddle | 16 | 0.250 | 0.250 | 0.250 | 9 | 12 |
| E1RAW+straddle | 24 | 0.250 | 0.250 | 0.250 | 9 | 12 |
| E1RAW+straddle | 40 | 0.417 | 0.417 | 0.417 | 7 | 12 |
| E1RAW+straddle | 60 | 0.417 | 0.417 | 0.417 | 7 | 12 |
| G3_MARGIN | 16 | 0.167 | 0.167 | 0.167 | 10 | 12 |
| G3_MARGIN | 24 | 0.667 | 0.667 | 0.667 | 4 | 12 |
| G3_MARGIN | 40 | 0.333 | 0.333 | 0.333 | 8 | 12 |
| G3_MARGIN | 60 | 0.500 | 0.500 | 0.500 | 6 | 12 |

## Secondary: q20 boundary BA and short-K capture

| arm | budget | q20_BA | shortK_pooled_captured | shortK_pooled_total | shortK_NEW_captured | shortK_NEW_total |
|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | 0.78 | 19.00 | 22.00 | 9.00 | 10.00 |
| ATSAPPROX_MARGIN | 24 | 0.83 | 20.00 | 22.00 | 10.00 | 10.00 |
| ATSAPPROX_MARGIN | 40 | 0.81 | 16.00 | 22.00 | 8.00 | 10.00 |
| ATSAPPROX_MARGIN | 60 | 0.83 | 18.00 | 22.00 | 9.00 | 10.00 |
| ATSCF_MARGIN | 16 | 0.67 | 9.00 | 22.00 | 3.00 | 10.00 |
| ATSCF_MARGIN | 24 | 0.75 | 11.00 | 22.00 | 5.00 | 10.00 |
| ATSCF_MARGIN | 40 | 0.82 | 20.00 | 22.00 | 10.00 | 10.00 |
| ATSCF_MARGIN | 60 | 0.83 | 19.00 | 22.00 | 10.00 | 10.00 |
| DEPTHCF_MARGIN | 16 | 0.72 | 11.00 | 22.00 | 4.00 | 10.00 |
| DEPTHCF_MARGIN | 24 | 0.73 | 11.00 | 22.00 | 4.00 | 10.00 |
| DEPTHCF_MARGIN | 40 | 0.79 | 15.00 | 22.00 | 7.00 | 10.00 |
| DEPTHCF_MARGIN | 60 | 0.82 | 17.00 | 22.00 | 8.00 | 10.00 |
| E1CAL+straddle | 16 | 0.70 | 14.00 | 22.00 | 7.00 | 10.00 |
| E1CAL+straddle | 24 | 0.78 | 18.00 | 22.00 | 9.00 | 10.00 |
| E1CAL+straddle | 40 | 0.75 | 16.00 | 22.00 | 7.00 | 10.00 |
| E1CAL+straddle | 60 | 0.80 | 18.00 | 22.00 | 8.00 | 10.00 |
| E1RAW+straddle | 16 | 0.73 | 18.00 | 22.00 | 9.00 | 10.00 |
| E1RAW+straddle | 24 | 0.75 | 20.00 | 22.00 | 9.00 | 10.00 |
| E1RAW+straddle | 40 | 0.76 | 18.00 | 22.00 | 8.00 | 10.00 |
| E1RAW+straddle | 60 | 0.78 | 18.00 | 22.00 | 8.00 | 10.00 |
| G3_MARGIN | 16 | 0.75 | 18.00 | 22.00 | 9.00 | 10.00 |
| G3_MARGIN | 24 | 0.76 | 12.00 | 22.00 | 5.00 | 10.00 |
| G3_MARGIN | 40 | 0.77 | 18.00 | 22.00 | 9.00 | 10.00 |
| G3_MARGIN | 60 | 0.80 | 16.00 | 22.00 | 7.00 | 10.00 |

AULC over B8–B60 (every budget) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.9463 | 0.9463 | 0.9463 | 0.1387 | 0.1387 | 0.1387 | 0.0381 | 0.0381 | 0.0381 | 0.9867 | 0.9867 | 0.9867 |
| ATSCF_MARGIN | 0.9401 | 0.9401 | 0.9401 | 0.1712 | 0.1712 | 0.1712 | 0.0455 | 0.0455 | 0.0455 | 0.9807 | 0.9807 | 0.9807 |
| DEPTHCF_MARGIN | 0.9302 | 0.9302 | 0.9302 | 0.1903 | 0.1903 | 0.1903 | 0.0521 | 0.0521 | 0.0521 | 0.9787 | 0.9787 | 0.9787 |
| E1CAL+straddle | 0.9401 | 0.9401 | 0.9401 | 0.1990 | 0.1990 | 0.1990 | 0.0481 | 0.0481 | 0.0481 | 0.9781 | 0.9781 | 0.9781 |
| E1RAW+straddle | 0.9426 | 0.9426 | 0.9426 | 0.2328 | 0.2328 | 0.2328 | 0.0485 | 0.0485 | 0.0485 | 0.9827 | 0.9827 | 0.9827 |
| G3_MARGIN | 0.9257 | 0.9257 | 0.9257 | 0.2625 | 0.2625 | 0.2625 | 0.0711 | 0.0711 | 0.0711 | 0.9622 | 0.9622 | 0.9622 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF_MARGIN − E1CAL+straddle | BA_AULC | -0.0001 | – | -0.0001 | -0.0001 | 0/1 |
| ATSCF_MARGIN − E1CAL+straddle | LL_AULC | -0.0278 | – | -0.0278 | -0.0278 | 1/1 |
| ATSCF_MARGIN − E1CAL+straddle | Brier_AULC | -0.0026 | – | -0.0026 | -0.0026 | 1/1 |
| ATSCF_MARGIN − E1RAW+straddle | BA_AULC | -0.0025 | – | -0.0025 | -0.0025 | 0/1 |
| ATSCF_MARGIN − E1RAW+straddle | LL_AULC | -0.0616 | – | -0.0616 | -0.0616 | 1/1 |
| ATSCF_MARGIN − E1RAW+straddle | Brier_AULC | -0.0030 | – | -0.0030 | -0.0030 | 1/1 |
| ATSCF_MARGIN − DEPTHCF_MARGIN | BA_AULC | 0.0099 | – | 0.0099 | 0.0099 | 1/1 |
| ATSCF_MARGIN − DEPTHCF_MARGIN | LL_AULC | -0.0191 | – | -0.0191 | -0.0191 | 1/1 |
| ATSCF_MARGIN − DEPTHCF_MARGIN | Brier_AULC | -0.0066 | – | -0.0066 | -0.0066 | 1/1 |
| DEPTHCF_MARGIN − E1CAL+straddle | BA_AULC | -0.0099 | – | -0.0099 | -0.0099 | 0/1 |
| DEPTHCF_MARGIN − E1CAL+straddle | LL_AULC | -0.0087 | – | -0.0087 | -0.0087 | 1/1 |
| DEPTHCF_MARGIN − E1CAL+straddle | Brier_AULC | 0.0040 | – | 0.0040 | 0.0040 | 0/1 |
| E1CAL+straddle − E1RAW+straddle | BA_AULC | -0.0024 | – | -0.0024 | -0.0024 | 0/1 |
| E1CAL+straddle − E1RAW+straddle | LL_AULC | -0.0338 | – | -0.0338 | -0.0338 | 1/1 |
| E1CAL+straddle − E1RAW+straddle | Brier_AULC | -0.0004 | – | -0.0004 | -0.0004 | 1/1 |
| ATSCF_MARGIN − ATSAPPROX_MARGIN | BA_AULC | -0.0063 | – | -0.0063 | -0.0063 | 0/1 |
| ATSCF_MARGIN − ATSAPPROX_MARGIN | LL_AULC | 0.0325 | – | 0.0325 | 0.0325 | 0/1 |
| ATSCF_MARGIN − ATSAPPROX_MARGIN | Brier_AULC | 0.0074 | – | 0.0074 | 0.0074 | 0/1 |
| ATSCF_MARGIN − G3_MARGIN | BA_AULC | 0.0144 | – | 0.0144 | 0.0144 | 1/1 |
| ATSCF_MARGIN − G3_MARGIN | LL_AULC | -0.0913 | – | -0.0913 | -0.0913 | 1/1 |
| ATSCF_MARGIN − G3_MARGIN | Brier_AULC | -0.0255 | – | -0.0255 | -0.0255 | 1/1 |
| ATSAPPROX_MARGIN − E1RAW+straddle | BA_AULC | 0.0038 | – | 0.0038 | 0.0038 | 1/1 |
| ATSAPPROX_MARGIN − E1RAW+straddle | LL_AULC | -0.0941 | – | -0.0941 | -0.0941 | 1/1 |
| ATSAPPROX_MARGIN − E1RAW+straddle | Brier_AULC | -0.0104 | – | -0.0104 | -0.0104 | 1/1 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX_MARGIN | 1/1 | 14.00 | 18.00 | 18 |
| ATSCF_MARGIN | 1/1 | 20.00 | 24.00 | 24 |
| DEPTHCF_MARGIN | 1/1 | 25.00 | 29.00 | 29 |
| E1CAL+straddle | 1/1 | 17.00 | 21.00 | 21 |
| E1RAW+straddle | 1/1 | 16.00 | 20.00 | 20 |
| G3_MARGIN | 1/1 | 25.00 | 29.00 | 29 |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | 0.940 | 0.929 | 0.951 | 0.987 | 0.044 | 0.162 | 0.781 | 19.000 | 0.250 |
| ATSAPPROX_MARGIN | 24 | 0.957 | 0.949 | 0.965 | 0.991 | 0.036 | 0.135 | 0.827 | 20.000 | 0.333 |
| ATSAPPROX_MARGIN | 40 | 0.958 | 0.944 | 0.971 | 0.993 | 0.029 | 0.106 | 0.809 | 16.000 | 0.333 |
| ATSAPPROX_MARGIN | 60 | 0.963 | 0.954 | 0.971 | 0.994 | 0.027 | 0.100 | 0.827 | 18.000 | 0.417 |
| ATSCF_MARGIN | 16 | 0.911 | 0.863 | 0.959 | 0.975 | 0.058 | 0.209 | 0.665 | 9.000 | 0.333 |
| ATSCF_MARGIN | 24 | 0.934 | 0.904 | 0.965 | 0.985 | 0.045 | 0.172 | 0.746 | 11.000 | 0.500 |
| ATSCF_MARGIN | 40 | 0.962 | 0.959 | 0.965 | 0.988 | 0.035 | 0.141 | 0.817 | 20.000 | 0.417 |
| ATSCF_MARGIN | 60 | 0.964 | 0.959 | 0.968 | 0.990 | 0.031 | 0.121 | 0.827 | 19.000 | 0.417 |
| DEPTHCF_MARGIN | 16 | 0.922 | 0.888 | 0.956 | 0.981 | 0.066 | 0.251 | 0.719 | 11.000 | 0.583 |
| DEPTHCF_MARGIN | 24 | 0.930 | 0.904 | 0.956 | 0.983 | 0.051 | 0.194 | 0.728 | 11.000 | 0.500 |
| DEPTHCF_MARGIN | 40 | 0.948 | 0.934 | 0.962 | 0.989 | 0.038 | 0.141 | 0.791 | 15.000 | 0.417 |
| DEPTHCF_MARGIN | 60 | 0.960 | 0.949 | 0.971 | 0.991 | 0.031 | 0.117 | 0.818 | 17.000 | 0.500 |
| E1CAL+straddle | 16 | 0.925 | 0.919 | 0.930 | 0.967 | 0.056 | 0.264 | 0.699 | 14.000 | 0.250 |
| E1CAL+straddle | 24 | 0.941 | 0.934 | 0.948 | 0.974 | 0.047 | 0.203 | 0.781 | 18.000 | 0.333 |
| E1CAL+straddle | 40 | 0.948 | 0.949 | 0.948 | 0.987 | 0.042 | 0.150 | 0.753 | 16.000 | 0.500 |
| E1CAL+straddle | 60 | 0.960 | 0.964 | 0.956 | 0.991 | 0.032 | 0.125 | 0.799 | 18.000 | 0.417 |
| E1RAW+straddle | 16 | 0.935 | 0.949 | 0.922 | 0.979 | 0.055 | 0.265 | 0.725 | 18.000 | 0.250 |
| E1RAW+straddle | 24 | 0.940 | 0.959 | 0.922 | 0.980 | 0.051 | 0.246 | 0.752 | 20.000 | 0.250 |
| E1RAW+straddle | 40 | 0.951 | 0.959 | 0.942 | 0.988 | 0.043 | 0.185 | 0.762 | 18.000 | 0.417 |
| E1RAW+straddle | 60 | 0.958 | 0.964 | 0.951 | 0.992 | 0.032 | 0.127 | 0.780 | 18.000 | 0.417 |
| G3_MARGIN | 16 | 0.922 | 0.888 | 0.956 | 0.940 | 0.096 | 0.354 | 0.746 | 18.000 | 0.167 |
| G3_MARGIN | 24 | 0.889 | 0.807 | 0.971 | 0.954 | 0.089 | 0.325 | 0.757 | 12.000 | 0.667 |
| G3_MARGIN | 40 | 0.946 | 0.939 | 0.953 | 0.984 | 0.047 | 0.182 | 0.772 | 18.000 | 0.333 |
| G3_MARGIN | 60 | 0.955 | 0.939 | 0.971 | 0.992 | 0.036 | 0.147 | 0.800 | 16.000 | 0.500 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | -0.002 | 1.619 | 0.049 | 9 | 12 |
| ATSAPPROX_MARGIN | 24 | 0.013 | 1.490 | 0.038 | 8 | 12 |
| ATSAPPROX_MARGIN | 40 | 0.007 | 1.315 | 0.023 | 8 | 12 |
| ATSAPPROX_MARGIN | 60 | 0.008 | 1.194 | 0.029 | 7 | 12 |
| ATSCF_MARGIN | 16 | -0.002 | 1.543 | 0.056 | 8 | 12 |
| ATSCF_MARGIN | 24 | 0.024 | 1.632 | 0.059 | 6 | 12 |
| ATSCF_MARGIN | 40 | 0.017 | 1.590 | 0.055 | 7 | 12 |
| ATSCF_MARGIN | 60 | 0.009 | 1.245 | 0.025 | 7 | 12 |
| DEPTHCF_MARGIN | 16 | 0.008 | 2.488 | 0.113 | 5 | 12 |
| DEPTHCF_MARGIN | 24 | 0.020 | 1.897 | 0.079 | 6 | 12 |
| DEPTHCF_MARGIN | 40 | 0.018 | 1.510 | 0.040 | 7 | 12 |
| DEPTHCF_MARGIN | 60 | 0.011 | 1.364 | 0.028 | 6 | 12 |
| E1CAL+straddle | 16 | 0.031 | 0.758 | 0.036 | 9 | 12 |
| E1CAL+straddle | 24 | 0.030 | 0.949 | 0.036 | 8 | 12 |
| E1CAL+straddle | 40 | 0.018 | 0.854 | 0.020 | 6 | 12 |
| E1CAL+straddle | 60 | 0.022 | 1.349 | 0.029 | 7 | 12 |
| E1RAW+straddle | 16 | 0.037 | 0.459 | 0.048 | 9 | 12 |
| E1RAW+straddle | 24 | 0.041 | 0.505 | 0.047 | 9 | 12 |
| E1RAW+straddle | 40 | 0.021 | 0.486 | 0.036 | 7 | 12 |
| E1RAW+straddle | 60 | 0.022 | 0.704 | 0.033 | 7 | 12 |
| G3_MARGIN | 16 | 0.076 | 2.334 | 0.185 | 10 | 12 |
| G3_MARGIN | 24 | 0.060 | 2.324 | 0.148 | 4 | 12 |
| G3_MARGIN | 40 | 0.048 | 1.706 | 0.073 | 8 | 12 |
| G3_MARGIN | 60 | 0.029 | 1.650 | 0.057 | 6 | 12 |

