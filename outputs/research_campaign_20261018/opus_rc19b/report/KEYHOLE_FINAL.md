# RC19B Keyhole — final paired adaptive comparison (fresh DEV repeats 11–18; frozen protocol PROTOCOL_RC19B.md)

**PRIMARY — ATSCF_MARGIN − E1CAL+straddle, LL_AULC (lower is better, margin 0.02): BETTER (DEV)** (mean Δ -0.0304 ± 0.0069 SE; good direction in 7/8 repeats)

## Pre-declared contrasts (verdict rule: mean beyond the margin AND ≥ 7 of 8 repeats in the same direction)

| role | contrast | metric | direction | margin | mean | se | min | max | repeats_good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| PRIMARY | ATSCF_MARGIN − E1CAL+straddle | LL_AULC | lower | 0.0200 | -0.0304 | 0.0069 | -0.0522 | 0.0134 | 7/8 | BETTER (DEV) |
| secondary | ATSCF_MARGIN − E1CAL+straddle | BA_AULC | higher | 0.0200 | 0.0067 | 0.0044 | -0.0129 | 0.0199 | 6/8 | NOT DIFFERENT (DEV) |
| secondary | ATSCF_MARGIN − E1CAL+straddle | LL_AULC | lower | 0.0200 | -0.0304 | 0.0069 | -0.0522 | 0.0134 | 7/8 | BETTER (DEV) |
| secondary | ATSCF_MARGIN − E1CAL+straddle | Brier_AULC | lower | 0.0050 | -0.0054 | 0.0025 | -0.0119 | 0.0085 | 6/8 | NOT DIFFERENT (DEV) |
| secondary | ATSCF_MARGIN − E1RAW+straddle | BA_AULC | higher | 0.0200 | -0.0007 | 0.0029 | -0.0145 | 0.0077 | 4/8 | NOT DIFFERENT (DEV) |
| secondary | ATSCF_MARGIN − E1RAW+straddle | LL_AULC | lower | 0.0200 | -0.0547 | 0.0095 | -0.1011 | -0.0242 | 8/8 | BETTER (DEV) |
| secondary | ATSCF_MARGIN − E1RAW+straddle | Brier_AULC | lower | 0.0050 | -0.0034 | 0.0022 | -0.0114 | 0.0067 | 6/8 | NOT DIFFERENT (DEV) |
| secondary | ATSCF_MARGIN − DEPTHCF_MARGIN | BA_AULC | higher | 0.0200 | 0.0060 | 0.0028 | -0.0087 | 0.0184 | 7/8 | NOT DIFFERENT (DEV) |
| secondary | ATSCF_MARGIN − DEPTHCF_MARGIN | LL_AULC | lower | 0.0200 | -0.0304 | 0.0070 | -0.0666 | 0.0049 | 7/8 | BETTER (DEV) |
| secondary | ATSCF_MARGIN − DEPTHCF_MARGIN | Brier_AULC | lower | 0.0050 | -0.0077 | 0.0021 | -0.0193 | 0.0024 | 7/8 | BETTER (DEV) |
| secondary | DEPTHCF_MARGIN − E1CAL+straddle | BA_AULC | higher | 0.0200 | 0.0007 | 0.0024 | -0.0093 | 0.0124 | 5/8 | NOT DIFFERENT (DEV) |
| secondary | DEPTHCF_MARGIN − E1CAL+straddle | LL_AULC | lower | 0.0200 | -0.0000 | 0.0039 | -0.0156 | 0.0143 | 4/8 | NOT DIFFERENT (DEV) |
| secondary | DEPTHCF_MARGIN − E1CAL+straddle | Brier_AULC | lower | 0.0050 | 0.0023 | 0.0017 | -0.0044 | 0.0079 | 3/8 | NOT DIFFERENT (DEV) |
| secondary | E1CAL+straddle − E1RAW+straddle | BA_AULC | higher | 0.0200 | -0.0074 | 0.0017 | -0.0163 | -0.0016 | 0/8 | NOT DIFFERENT (DEV) |
| secondary | E1CAL+straddle − E1RAW+straddle | LL_AULC | lower | 0.0200 | -0.0243 | 0.0065 | -0.0559 | -0.0043 | 8/8 | BETTER (DEV) |
| secondary | E1CAL+straddle − E1RAW+straddle | Brier_AULC | lower | 0.0050 | 0.0020 | 0.0007 | -0.0018 | 0.0049 | 1/8 | NOT DIFFERENT (DEV) |
| secondary | ATSCF_MARGIN − ATSAPPROX_MARGIN | BA_AULC | higher | 0.0200 | -0.0068 | 0.0024 | -0.0164 | 0.0005 | 1/8 | NOT DIFFERENT (DEV) |
| secondary | ATSCF_MARGIN − ATSAPPROX_MARGIN | LL_AULC | lower | 0.0200 | 0.0189 | 0.0059 | -0.0007 | 0.0531 | 1/8 | NOT DIFFERENT (DEV) |
| secondary | ATSCF_MARGIN − ATSAPPROX_MARGIN | Brier_AULC | lower | 0.0050 | 0.0053 | 0.0016 | 0.0003 | 0.0147 | 0/8 | WORSE (DEV) |
| secondary | ATSCF_MARGIN − G3_MARGIN | BA_AULC | higher | 0.0200 | 0.0123 | 0.0048 | -0.0095 | 0.0283 | 6/8 | NOT DIFFERENT (DEV) |
| secondary | ATSCF_MARGIN − G3_MARGIN | LL_AULC | lower | 0.0200 | -0.0882 | 0.0075 | -0.1240 | -0.0573 | 8/8 | BETTER (DEV) |
| secondary | ATSCF_MARGIN − G3_MARGIN | Brier_AULC | lower | 0.0050 | -0.0231 | 0.0026 | -0.0341 | -0.0124 | 8/8 | BETTER (DEV) |
| secondary | ATSAPPROX_MARGIN − E1RAW+straddle | BA_AULC | higher | 0.0200 | 0.0061 | 0.0021 | -0.0022 | 0.0175 | 7/8 | NOT DIFFERENT (DEV) |
| secondary | ATSAPPROX_MARGIN − E1RAW+straddle | LL_AULC | lower | 0.0200 | -0.0736 | 0.0061 | -0.1049 | -0.0519 | 8/8 | BETTER (DEV) |
| secondary | ATSAPPROX_MARGIN − E1RAW+straddle | Brier_AULC | lower | 0.0050 | -0.0087 | 0.0011 | -0.0133 | -0.0048 | 8/8 | BETTER (DEV) |

## AULC over B8–B60 (mean and SE over the 8 repeats)

| arm | BA_AULC_mean | BA_AULC_se | sens_AULC_mean | sens_AULC_se | spec_AULC_mean | spec_AULC_se | LL_AULC_mean | LL_AULC_se | Brier_AULC_mean | Brier_AULC_se | AUC_AULC_mean | AUC_AULC_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.9434 | 0.0013 | 0.9351 | 0.0020 | 0.9517 | 0.0017 | 0.1569 | 0.0027 | 0.0422 | 0.0006 | 0.9864 | 0.0005 |
| ATSCF_MARGIN | 0.9366 | 0.0020 | 0.9239 | 0.0019 | 0.9493 | 0.0027 | 0.1758 | 0.0047 | 0.0476 | 0.0013 | 0.9801 | 0.0018 |
| DEPTHCF_MARGIN | 0.9306 | 0.0024 | 0.9164 | 0.0033 | 0.9448 | 0.0032 | 0.2061 | 0.0045 | 0.0552 | 0.0015 | 0.9780 | 0.0018 |
| E1CAL+straddle | 0.9299 | 0.0037 | 0.9185 | 0.0071 | 0.9413 | 0.0023 | 0.2062 | 0.0041 | 0.0530 | 0.0016 | 0.9745 | 0.0017 |
| E1RAW+straddle | 0.9373 | 0.0022 | 0.9466 | 0.0049 | 0.9280 | 0.0026 | 0.2305 | 0.0073 | 0.0510 | 0.0014 | 0.9811 | 0.0013 |
| G3_MARGIN | 0.9243 | 0.0043 | 0.9106 | 0.0076 | 0.9380 | 0.0042 | 0.2640 | 0.0059 | 0.0707 | 0.0021 | 0.9651 | 0.0026 |

## BA ≥ 0.93: first qualifying budget and confirmation spend (b + 4 of the first confirmed pair; total revealed simulations, startup included)

| arm | confirmed | censored | first_mean | first_median | spend_mean | spend_median | spend_min | spend_max | spend_per_repeat |
|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 8/8 | 0 | 11.50 | 10.00 | 18.00 | 18.00 | 13 | 24 | 15,20,24,22,13,14,19,17 |
| ATSCF_MARGIN | 8/8 | 0 | 14.25 | 15.00 | 20.38 | 20.00 | 15 | 27 | 15,21,22,19,19,21,19,27 |
| DEPTHCF_MARGIN | 8/8 | 0 | 19.12 | 18.50 | 25.50 | 26.00 | 16 | 35 | 27,23,35,16,25,24,27,27 |
| E1CAL+straddle | 8/8 | 0 | 20.25 | 19.00 | 25.25 | 23.00 | 19 | 39 | 19,26,39,19,33,19,27,20 |
| E1RAW+straddle | 8/8 | 0 | 18.50 | 17.50 | 24.50 | 21.50 | 19 | 39 | 20,26,39,19,23,20,29,20 |
| G3_MARGIN | 8/8 | 0 | 24.62 | 21.50 | 29.50 | 26.00 | 21 | 42 | 27,25,42,35,21,21,25,40 |

Paired confirmation-spend differences (both confirmed; censoring counted separately):

| contrast | both_confirmed | mean_difference | fewer/equal/more | only_first_censored | only_second_censored | both_censored | per_repeat_first/second |
|---|---|---|---|---|---|---|---|
| ATSCF_MARGIN − E1CAL+straddle | 8 | -4.88 | 5/1/2 | 0 | 0 | 0 | 15/19;21/26;22/39;19/19;19/33;21/19;19/27;27/20 |
| ATSCF_MARGIN − E1RAW+straddle | 8 | -4.12 | 5/1/2 | 0 | 0 | 0 | 15/20;21/26;22/39;19/19;19/23;21/20;19/29;27/20 |
| ATSCF_MARGIN − DEPTHCF_MARGIN | 8 | -5.12 | 6/1/1 | 0 | 0 | 0 | 15/27;21/23;22/35;19/16;19/25;21/24;19/27;27/27 |
| DEPTHCF_MARGIN − E1CAL+straddle | 8 | 0.25 | 4/1/3 | 0 | 0 | 0 | 27/19;23/26;35/39;16/19;25/33;24/19;27/27;27/20 |
| E1CAL+straddle − E1RAW+straddle | 8 | 0.75 | 3/4/1 | 0 | 0 | 0 | 19/20;26/26;39/39;19/19;33/23;19/20;27/29;20/20 |
| ATSCF_MARGIN − ATSAPPROX_MARGIN | 8 | 2.38 | 2/2/4 | 0 | 0 | 0 | 15/15;21/20;22/24;19/22;19/13;21/14;19/19;27/17 |
| ATSCF_MARGIN − G3_MARGIN | 8 | -9.12 | 7/1/0 | 0 | 0 | 0 | 15/27;21/25;22/42;19/35;19/21;21/21;19/25;27/40 |
| ATSAPPROX_MARGIN − E1RAW+straddle | 8 | -6.50 | 7/0/1 | 0 | 0 | 0 | 15/20;20/26;24/39;22/19;13/23;14/20;19/29;17/20 |

## Reliability with uncertainty

Calibration slope / intercept (logistic recalibration of y on logit p; 1 / 0 = calibrated), ECE and calibration-in-the-large: mean and SE over repeats; bins_mean_p_inside_Wilson95 = reliability bins (pooled over repeats and folds) whose mean prediction lies inside the Wilson 95 % interval of the observed frequency.

| arm | budget | cal_slope | cal_slope_se | cal_intercept | cal_intercept_se | ECE | ECE_se | cal_in_large | cal_in_large_se | bins | bins_mean_p_inside_Wilson95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | 1.631 | 0.055 | -0.331 | 0.153 | 0.062 | 0.005 | 0.030 | 0.007 | 10 | 5 |
| ATSAPPROX_MARGIN | 24 | 1.490 | 0.056 | -0.343 | 0.093 | 0.048 | 0.003 | 0.025 | 0.005 | 10 | 6 |
| ATSAPPROX_MARGIN | 40 | 1.272 | 0.053 | -0.227 | 0.031 | 0.032 | 0.003 | 0.015 | 0.001 | 10 | 7 |
| ATSAPPROX_MARGIN | 60 | 1.095 | 0.053 | -0.190 | 0.036 | 0.023 | 0.001 | 0.009 | 0.002 | 10 | 8 |
| ATSCF_MARGIN | 16 | 1.671 | 0.106 | -0.143 | 0.088 | 0.079 | 0.003 | 0.027 | 0.006 | 10 | 3 |
| ATSCF_MARGIN | 24 | 1.554 | 0.062 | -0.161 | 0.080 | 0.053 | 0.005 | 0.021 | 0.005 | 10 | 5 |
| ATSCF_MARGIN | 40 | 1.339 | 0.111 | -0.117 | 0.059 | 0.036 | 0.005 | 0.012 | 0.002 | 10 | 6 |
| ATSCF_MARGIN | 60 | 1.158 | 0.052 | -0.163 | 0.048 | 0.024 | 0.003 | 0.010 | 0.002 | 10 | 7 |
| DEPTHCF_MARGIN | 16 | 2.403 | 0.185 | 0.096 | 0.171 | 0.117 | 0.007 | 0.030 | 0.008 | 10 | 2 |
| DEPTHCF_MARGIN | 24 | 2.081 | 0.077 | -0.142 | 0.086 | 0.089 | 0.005 | 0.035 | 0.003 | 10 | 3 |
| DEPTHCF_MARGIN | 40 | 1.573 | 0.076 | -0.303 | 0.052 | 0.054 | 0.003 | 0.031 | 0.003 | 10 | 4 |
| DEPTHCF_MARGIN | 60 | 1.338 | 0.069 | -0.123 | 0.059 | 0.035 | 0.003 | 0.014 | 0.002 | 10 | 5 |
| E1CAL+straddle | 16 | 0.816 | 0.081 | -0.565 | 0.175 | 0.070 | 0.007 | 0.032 | 0.010 | 10 | 3 |
| E1CAL+straddle | 24 | 1.047 | 0.113 | -0.234 | 0.071 | 0.048 | 0.010 | 0.014 | 0.004 | 10 | 3 |
| E1CAL+straddle | 40 | 1.225 | 0.113 | -0.171 | 0.108 | 0.037 | 0.006 | 0.009 | 0.004 | 10 | 7 |
| E1CAL+straddle | 60 | 1.225 | 0.056 | -0.214 | 0.052 | 0.033 | 0.004 | 0.012 | 0.002 | 10 | 6 |
| E1RAW+straddle | 16 | 0.472 | 0.039 | -0.897 | 0.209 | 0.062 | 0.007 | 0.040 | 0.010 | 10 | 3 |
| E1RAW+straddle | 24 | 0.551 | 0.038 | -0.745 | 0.099 | 0.043 | 0.003 | 0.029 | 0.006 | 10 | 3 |
| E1RAW+straddle | 40 | 0.575 | 0.022 | -0.533 | 0.047 | 0.031 | 0.002 | 0.016 | 0.001 | 10 | 6 |
| E1RAW+straddle | 60 | 0.571 | 0.018 | -0.499 | 0.048 | 0.028 | 0.002 | 0.011 | 0.002 | 10 | 6 |
| G3_MARGIN | 16 | 2.158 | 0.134 | -0.588 | 0.086 | 0.158 | 0.010 | 0.086 | 0.004 | 10 | 2 |
| G3_MARGIN | 24 | 2.270 | 0.059 | -0.576 | 0.070 | 0.148 | 0.007 | 0.075 | 0.004 | 10 | 1 |
| G3_MARGIN | 40 | 1.875 | 0.086 | -0.536 | 0.069 | 0.106 | 0.006 | 0.057 | 0.003 | 10 | 3 |
| G3_MARGIN | 60 | 1.564 | 0.042 | -0.317 | 0.027 | 0.058 | 0.003 | 0.030 | 0.002 | 10 | 6 |

Reliability-diagram bins: report/keyhole_final_reliability_bins.csv.

## Hard fast-scan corner (NEW-batch conduction test runs; evaluator-only diagnostic): conduction recall and error COUNTS summed over repeats

| arm | budget | spec_NEW_mean | spec_NEW_min | spec_NEW_max | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | 0.198 | 0.000 | 0.500 | 77 | 96 |
| ATSAPPROX_MARGIN | 24 | 0.312 | 0.083 | 0.500 | 66 | 96 |
| ATSAPPROX_MARGIN | 40 | 0.292 | 0.167 | 0.333 | 68 | 96 |
| ATSAPPROX_MARGIN | 60 | 0.333 | 0.333 | 0.333 | 64 | 96 |
| ATSCF_MARGIN | 16 | 0.167 | 0.000 | 0.333 | 80 | 96 |
| ATSCF_MARGIN | 24 | 0.219 | 0.083 | 0.583 | 75 | 96 |
| ATSCF_MARGIN | 40 | 0.344 | 0.167 | 0.417 | 63 | 96 |
| ATSCF_MARGIN | 60 | 0.354 | 0.250 | 0.500 | 62 | 96 |
| DEPTHCF_MARGIN | 16 | 0.531 | 0.333 | 1.000 | 45 | 96 |
| DEPTHCF_MARGIN | 24 | 0.542 | 0.417 | 0.750 | 44 | 96 |
| DEPTHCF_MARGIN | 40 | 0.427 | 0.333 | 0.583 | 55 | 96 |
| DEPTHCF_MARGIN | 60 | 0.490 | 0.417 | 0.583 | 49 | 96 |
| E1CAL+straddle | 16 | 0.479 | 0.333 | 0.667 | 50 | 96 |
| E1CAL+straddle | 24 | 0.552 | 0.333 | 0.833 | 43 | 96 |
| E1CAL+straddle | 40 | 0.479 | 0.333 | 0.750 | 50 | 96 |
| E1CAL+straddle | 60 | 0.417 | 0.333 | 0.500 | 56 | 96 |
| E1RAW+straddle | 16 | 0.385 | 0.250 | 0.500 | 59 | 96 |
| E1RAW+straddle | 24 | 0.427 | 0.250 | 0.667 | 55 | 96 |
| E1RAW+straddle | 40 | 0.354 | 0.250 | 0.417 | 62 | 96 |
| E1RAW+straddle | 60 | 0.396 | 0.333 | 0.500 | 58 | 96 |
| G3_MARGIN | 16 | 0.135 | 0.000 | 0.333 | 83 | 96 |
| G3_MARGIN | 24 | 0.219 | 0.083 | 0.417 | 75 | 96 |
| G3_MARGIN | 40 | 0.281 | 0.250 | 0.417 | 69 | 96 |
| G3_MARGIN | 60 | 0.396 | 0.333 | 0.500 | 58 | 96 |

## Secondary: q20 boundary BA and short-K capture

| arm | budget | q20_BA | shortK_pooled_captured | shortK_pooled_total | shortK_NEW_captured | shortK_NEW_total |
|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | 0.74 | 17.00 | 22.00 | 8.25 | 10.00 |
| ATSAPPROX_MARGIN | 24 | 0.76 | 16.88 | 22.00 | 8.12 | 10.00 |
| ATSAPPROX_MARGIN | 40 | 0.78 | 17.50 | 22.00 | 8.75 | 10.00 |
| ATSAPPROX_MARGIN | 60 | 0.78 | 16.62 | 22.00 | 8.00 | 10.00 |
| ATSCF_MARGIN | 16 | 0.70 | 16.12 | 22.00 | 7.75 | 10.00 |
| ATSCF_MARGIN | 24 | 0.76 | 18.00 | 22.00 | 8.38 | 10.00 |
| ATSCF_MARGIN | 40 | 0.77 | 16.62 | 22.00 | 8.00 | 10.00 |
| ATSCF_MARGIN | 60 | 0.78 | 17.50 | 22.00 | 8.50 | 10.00 |
| DEPTHCF_MARGIN | 16 | 0.69 | 10.88 | 22.00 | 4.88 | 10.00 |
| DEPTHCF_MARGIN | 24 | 0.73 | 12.38 | 22.00 | 5.38 | 10.00 |
| DEPTHCF_MARGIN | 40 | 0.75 | 15.25 | 22.00 | 7.12 | 10.00 |
| DEPTHCF_MARGIN | 60 | 0.77 | 14.62 | 22.00 | 7.12 | 10.00 |
| E1CAL+straddle | 16 | 0.71 | 13.00 | 22.00 | 5.62 | 10.00 |
| E1CAL+straddle | 24 | 0.74 | 14.00 | 22.00 | 5.62 | 10.00 |
| E1CAL+straddle | 40 | 0.76 | 14.75 | 22.00 | 6.62 | 10.00 |
| E1CAL+straddle | 60 | 0.77 | 15.12 | 22.00 | 7.12 | 10.00 |
| E1RAW+straddle | 16 | 0.71 | 15.88 | 22.00 | 7.00 | 10.00 |
| E1RAW+straddle | 24 | 0.75 | 17.38 | 22.00 | 7.62 | 10.00 |
| E1RAW+straddle | 40 | 0.76 | 17.25 | 22.00 | 8.25 | 10.00 |
| E1RAW+straddle | 60 | 0.78 | 17.25 | 22.00 | 8.25 | 10.00 |
| G3_MARGIN | 16 | 0.69 | 16.00 | 22.00 | 8.00 | 10.00 |
| G3_MARGIN | 24 | 0.72 | 15.62 | 22.00 | 7.75 | 10.00 |
| G3_MARGIN | 40 | 0.75 | 16.25 | 22.00 | 7.75 | 10.00 |
| G3_MARGIN | 60 | 0.78 | 15.88 | 22.00 | 7.25 | 10.00 |

AULC over B8–B60 (every budget) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.9434 | 0.9361 | 0.9485 | 0.1569 | 0.1453 | 0.1672 | 0.0422 | 0.0394 | 0.0450 | 0.9864 | 0.9836 | 0.9880 |
| ATSCF_MARGIN | 0.9366 | 0.9270 | 0.9447 | 0.1758 | 0.1618 | 0.2013 | 0.0476 | 0.0439 | 0.0550 | 0.9801 | 0.9696 | 0.9860 |
| DEPTHCF_MARGIN | 0.9306 | 0.9157 | 0.9361 | 0.2061 | 0.1955 | 0.2331 | 0.0552 | 0.0518 | 0.0646 | 0.9780 | 0.9685 | 0.9836 |
| E1CAL+straddle | 0.9299 | 0.9147 | 0.9410 | 0.2062 | 0.1879 | 0.2204 | 0.0530 | 0.0465 | 0.0596 | 0.9745 | 0.9666 | 0.9794 |
| E1RAW+straddle | 0.9373 | 0.9264 | 0.9433 | 0.2305 | 0.2085 | 0.2669 | 0.0510 | 0.0465 | 0.0560 | 0.9811 | 0.9746 | 0.9856 |
| G3_MARGIN | 0.9243 | 0.9059 | 0.9368 | 0.2640 | 0.2419 | 0.2908 | 0.0707 | 0.0625 | 0.0796 | 0.9651 | 0.9542 | 0.9741 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF_MARGIN − E1CAL+straddle | BA_AULC | 0.0067 | 0.0044 | -0.0129 | 0.0199 | 6/8 |
| ATSCF_MARGIN − E1CAL+straddle | LL_AULC | -0.0304 | 0.0069 | -0.0522 | 0.0134 | 7/8 |
| ATSCF_MARGIN − E1CAL+straddle | Brier_AULC | -0.0054 | 0.0025 | -0.0119 | 0.0085 | 6/8 |
| ATSCF_MARGIN − E1RAW+straddle | BA_AULC | -0.0007 | 0.0029 | -0.0145 | 0.0077 | 4/8 |
| ATSCF_MARGIN − E1RAW+straddle | LL_AULC | -0.0547 | 0.0095 | -0.1011 | -0.0242 | 8/8 |
| ATSCF_MARGIN − E1RAW+straddle | Brier_AULC | -0.0034 | 0.0022 | -0.0114 | 0.0067 | 6/8 |
| ATSCF_MARGIN − DEPTHCF_MARGIN | BA_AULC | 0.0060 | 0.0028 | -0.0087 | 0.0184 | 7/8 |
| ATSCF_MARGIN − DEPTHCF_MARGIN | LL_AULC | -0.0304 | 0.0070 | -0.0666 | 0.0049 | 7/8 |
| ATSCF_MARGIN − DEPTHCF_MARGIN | Brier_AULC | -0.0077 | 0.0021 | -0.0193 | 0.0024 | 7/8 |
| DEPTHCF_MARGIN − E1CAL+straddle | BA_AULC | 0.0007 | 0.0024 | -0.0093 | 0.0124 | 5/8 |
| DEPTHCF_MARGIN − E1CAL+straddle | LL_AULC | -0.0000 | 0.0039 | -0.0156 | 0.0143 | 4/8 |
| DEPTHCF_MARGIN − E1CAL+straddle | Brier_AULC | 0.0023 | 0.0017 | -0.0044 | 0.0079 | 3/8 |
| E1CAL+straddle − E1RAW+straddle | BA_AULC | -0.0074 | 0.0017 | -0.0163 | -0.0016 | 0/8 |
| E1CAL+straddle − E1RAW+straddle | LL_AULC | -0.0243 | 0.0065 | -0.0559 | -0.0043 | 8/8 |
| E1CAL+straddle − E1RAW+straddle | Brier_AULC | 0.0020 | 0.0007 | -0.0018 | 0.0049 | 1/8 |
| ATSCF_MARGIN − ATSAPPROX_MARGIN | BA_AULC | -0.0068 | 0.0024 | -0.0164 | 0.0005 | 1/8 |
| ATSCF_MARGIN − ATSAPPROX_MARGIN | LL_AULC | 0.0189 | 0.0059 | -0.0007 | 0.0531 | 1/8 |
| ATSCF_MARGIN − ATSAPPROX_MARGIN | Brier_AULC | 0.0053 | 0.0016 | 0.0003 | 0.0147 | 0/8 |
| ATSCF_MARGIN − G3_MARGIN | BA_AULC | 0.0123 | 0.0048 | -0.0095 | 0.0283 | 6/8 |
| ATSCF_MARGIN − G3_MARGIN | LL_AULC | -0.0882 | 0.0075 | -0.1240 | -0.0573 | 8/8 |
| ATSCF_MARGIN − G3_MARGIN | Brier_AULC | -0.0231 | 0.0026 | -0.0341 | -0.0124 | 8/8 |
| ATSAPPROX_MARGIN − E1RAW+straddle | BA_AULC | 0.0061 | 0.0021 | -0.0022 | 0.0175 | 7/8 |
| ATSAPPROX_MARGIN − E1RAW+straddle | LL_AULC | -0.0736 | 0.0061 | -0.1049 | -0.0519 | 8/8 |
| ATSAPPROX_MARGIN − E1RAW+straddle | Brier_AULC | -0.0087 | 0.0011 | -0.0133 | -0.0048 | 8/8 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX_MARGIN | 8/8 | 11.50 | 18.00 | 15,20,24,22,13,14,19,17 |
| ATSCF_MARGIN | 8/8 | 14.25 | 20.38 | 15,21,22,19,19,21,19,27 |
| DEPTHCF_MARGIN | 8/8 | 19.12 | 25.50 | 27,23,35,16,25,24,27,27 |
| E1CAL+straddle | 8/8 | 20.25 | 25.25 | 19,26,39,19,33,19,27,20 |
| E1RAW+straddle | 8/8 | 18.50 | 24.50 | 20,26,39,19,23,20,29,20 |
| G3_MARGIN | 8/8 | 24.62 | 29.50 | 27,25,42,35,21,21,25,40 |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | 0.936 | 0.930 | 0.943 | 0.983 | 0.051 | 0.191 | 0.736 | 17.000 | 0.198 |
| ATSAPPROX_MARGIN | 24 | 0.944 | 0.938 | 0.951 | 0.988 | 0.042 | 0.158 | 0.763 | 16.875 | 0.312 |
| ATSAPPROX_MARGIN | 40 | 0.950 | 0.944 | 0.957 | 0.989 | 0.036 | 0.134 | 0.780 | 17.500 | 0.292 |
| ATSAPPROX_MARGIN | 60 | 0.951 | 0.942 | 0.960 | 0.990 | 0.034 | 0.123 | 0.779 | 16.625 | 0.333 |
| ATSCF_MARGIN | 16 | 0.914 | 0.892 | 0.937 | 0.965 | 0.067 | 0.244 | 0.705 | 16.125 | 0.167 |
| ATSCF_MARGIN | 24 | 0.944 | 0.934 | 0.955 | 0.986 | 0.043 | 0.166 | 0.761 | 18.000 | 0.219 |
| ATSCF_MARGIN | 40 | 0.948 | 0.937 | 0.959 | 0.987 | 0.038 | 0.140 | 0.774 | 16.625 | 0.344 |
| ATSCF_MARGIN | 60 | 0.952 | 0.944 | 0.960 | 0.989 | 0.035 | 0.129 | 0.780 | 17.500 | 0.354 |
| DEPTHCF_MARGIN | 16 | 0.908 | 0.871 | 0.945 | 0.975 | 0.072 | 0.269 | 0.686 | 10.875 | 0.531 |
| DEPTHCF_MARGIN | 24 | 0.931 | 0.911 | 0.950 | 0.982 | 0.055 | 0.212 | 0.733 | 12.375 | 0.542 |
| DEPTHCF_MARGIN | 40 | 0.942 | 0.934 | 0.951 | 0.985 | 0.042 | 0.164 | 0.751 | 15.250 | 0.427 |
| DEPTHCF_MARGIN | 60 | 0.946 | 0.928 | 0.965 | 0.986 | 0.037 | 0.143 | 0.771 | 14.625 | 0.490 |
| E1CAL+straddle | 16 | 0.902 | 0.882 | 0.922 | 0.964 | 0.073 | 0.282 | 0.706 | 13.000 | 0.479 |
| E1CAL+straddle | 24 | 0.932 | 0.916 | 0.949 | 0.975 | 0.055 | 0.216 | 0.745 | 14.000 | 0.552 |
| E1CAL+straddle | 40 | 0.943 | 0.930 | 0.956 | 0.985 | 0.042 | 0.154 | 0.761 | 14.750 | 0.479 |
| E1CAL+straddle | 60 | 0.947 | 0.937 | 0.957 | 0.988 | 0.036 | 0.137 | 0.769 | 15.125 | 0.417 |
| E1RAW+straddle | 16 | 0.914 | 0.926 | 0.901 | 0.967 | 0.071 | 0.346 | 0.709 | 15.875 | 0.385 |
| E1RAW+straddle | 24 | 0.938 | 0.949 | 0.928 | 0.981 | 0.052 | 0.229 | 0.750 | 17.375 | 0.427 |
| E1RAW+straddle | 40 | 0.949 | 0.952 | 0.945 | 0.989 | 0.040 | 0.160 | 0.763 | 17.250 | 0.354 |
| E1RAW+straddle | 60 | 0.952 | 0.951 | 0.954 | 0.990 | 0.036 | 0.154 | 0.781 | 17.250 | 0.396 |
| G3_MARGIN | 16 | 0.890 | 0.860 | 0.919 | 0.932 | 0.109 | 0.381 | 0.693 | 16.000 | 0.135 |
| G3_MARGIN | 24 | 0.926 | 0.913 | 0.939 | 0.969 | 0.080 | 0.301 | 0.719 | 15.625 | 0.219 |
| G3_MARGIN | 40 | 0.940 | 0.931 | 0.948 | 0.978 | 0.059 | 0.232 | 0.755 | 16.250 | 0.281 |
| G3_MARGIN | 60 | 0.952 | 0.938 | 0.965 | 0.988 | 0.039 | 0.157 | 0.785 | 15.875 | 0.396 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 16 | 0.030 | 1.631 | 0.062 | 77 | 96 |
| ATSAPPROX_MARGIN | 24 | 0.025 | 1.490 | 0.048 | 66 | 96 |
| ATSAPPROX_MARGIN | 40 | 0.015 | 1.272 | 0.032 | 68 | 96 |
| ATSAPPROX_MARGIN | 60 | 0.009 | 1.095 | 0.023 | 64 | 96 |
| ATSCF_MARGIN | 16 | 0.027 | 1.671 | 0.079 | 80 | 96 |
| ATSCF_MARGIN | 24 | 0.021 | 1.554 | 0.053 | 75 | 96 |
| ATSCF_MARGIN | 40 | 0.012 | 1.339 | 0.036 | 63 | 96 |
| ATSCF_MARGIN | 60 | 0.010 | 1.158 | 0.024 | 62 | 96 |
| DEPTHCF_MARGIN | 16 | 0.030 | 2.403 | 0.117 | 45 | 96 |
| DEPTHCF_MARGIN | 24 | 0.035 | 2.081 | 0.089 | 44 | 96 |
| DEPTHCF_MARGIN | 40 | 0.031 | 1.573 | 0.054 | 55 | 96 |
| DEPTHCF_MARGIN | 60 | 0.014 | 1.338 | 0.035 | 49 | 96 |
| E1CAL+straddle | 16 | 0.032 | 0.816 | 0.070 | 50 | 96 |
| E1CAL+straddle | 24 | 0.014 | 1.047 | 0.048 | 43 | 96 |
| E1CAL+straddle | 40 | 0.009 | 1.225 | 0.037 | 50 | 96 |
| E1CAL+straddle | 60 | 0.012 | 1.225 | 0.033 | 56 | 96 |
| E1RAW+straddle | 16 | 0.040 | 0.472 | 0.062 | 59 | 96 |
| E1RAW+straddle | 24 | 0.029 | 0.551 | 0.043 | 55 | 96 |
| E1RAW+straddle | 40 | 0.016 | 0.575 | 0.031 | 62 | 96 |
| E1RAW+straddle | 60 | 0.011 | 0.571 | 0.028 | 58 | 96 |
| G3_MARGIN | 16 | 0.086 | 2.158 | 0.158 | 83 | 96 |
| G3_MARGIN | 24 | 0.075 | 2.270 | 0.148 | 75 | 96 |
| G3_MARGIN | 40 | 0.057 | 1.875 | 0.106 | 69 | 96 |
| G3_MARGIN | 60 | 0.030 | 1.564 | 0.058 | 58 | 96 |

