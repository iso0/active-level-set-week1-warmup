# RC22 part 1b — geometry-blocked evaluation (k-means k = 5 on public log inputs; each block withheld from fitting and querying)

## Pre-declared contrasts (fold-pooled curves, paired by repeat / seed)

| window | contrast | metric | direction | margin | mean | se | min | max | good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| small | REF|STD − H|STD | BA | higher | 0.0200 | 0.0100 | 0.0044 | -0.0025 | 0.0282 | 5/8 | NOT DIFFERENT (DEV) |
| all | REF|STD − H|STD | BA | higher | 0.0200 | 0.0043 | 0.0028 | -0.0128 | 0.0124 | 7/8 | NOT DIFFERENT (DEV) |
| small | REF|STD − H|STD | log_loss | lower | 0.0100 | -0.0278 | 0.0098 | -0.0563 | 0.0145 | 6/8 | NOT DIFFERENT (DEV) |
| all | REF|STD − H|STD | log_loss | lower | 0.0050 | -0.0009 | 0.0128 | -0.0528 | 0.0673 | 4/8 | NOT DIFFERENT (DEV) |
| small | REF|STD − E1RAW+straddle|STD | BA | higher | 0.0200 | 0.0330 | 0.0119 | -0.0274 | 0.0775 | 7/8 | BETTER (DEV) |
| all | REF|STD − E1RAW+straddle|STD | BA | higher | 0.0200 | 0.0117 | 0.0052 | -0.0085 | 0.0345 | 5/8 | NOT DIFFERENT (DEV) |
| small | REF|STD − E1RAW+straddle|STD | log_loss | lower | 0.0100 | -0.1552 | 0.0338 | -0.2789 | -0.0105 | 8/8 | BETTER (DEV) |
| all | REF|STD − E1RAW+straddle|STD | log_loss | lower | 0.0050 | -0.0624 | 0.0144 | -0.1232 | -0.0081 | 8/8 | BETTER (DEV) |
| small | REF|STD − E1CAL+straddle|STD | BA | higher | 0.0200 | 0.0605 | 0.0102 | 0.0291 | 0.1190 | 8/8 | BETTER (DEV) |
| all | REF|STD − E1CAL+straddle|STD | BA | higher | 0.0200 | 0.0203 | 0.0059 | -0.0073 | 0.0509 | 7/8 | BETTER (DEV) |
| small | REF|STD − E1CAL+straddle|STD | log_loss | lower | 0.0100 | -0.1327 | 0.0139 | -0.1914 | -0.0658 | 8/8 | BETTER (DEV) |
| all | REF|STD − E1CAL+straddle|STD | log_loss | lower | 0.0050 | -0.0556 | 0.0154 | -0.1069 | 0.0374 | 7/8 | BETTER (DEV) |

## AULC B8–B24

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | brier_mean | brier_se |
|---|---|---|---|---|---|---|---|---|---|---|
| E1CAL+straddle|STD | 0.8386 | 0.0084 | 0.3848 | 0.0106 | 0.8200 | 0.0259 | 0.8572 | 0.0143 | 0.1150 | 0.0039 |
| E1RAW+straddle|STD | 0.8661 | 0.0061 | 0.4072 | 0.0303 | 0.9112 | 0.0136 | 0.8210 | 0.0170 | 0.1053 | 0.0063 |
| H|STD | 0.8891 | 0.0104 | 0.2798 | 0.0107 | 0.8825 | 0.0207 | 0.8956 | 0.0085 | 0.0832 | 0.0044 |
| REF|STD | 0.8991 | 0.0098 | 0.2520 | 0.0128 | 0.9038 | 0.0180 | 0.8944 | 0.0088 | 0.0754 | 0.0047 |

## AULC B8–B60

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | brier_mean | brier_se |
|---|---|---|---|---|---|---|---|---|---|---|
| E1CAL+straddle|STD | 0.8929 | 0.0035 | 0.2940 | 0.0060 | 0.9011 | 0.0094 | 0.8846 | 0.0060 | 0.0850 | 0.0021 |
| E1RAW+straddle|STD | 0.9014 | 0.0025 | 0.3008 | 0.0108 | 0.9510 | 0.0047 | 0.8518 | 0.0069 | 0.0805 | 0.0024 |
| H|STD | 0.9089 | 0.0026 | 0.2392 | 0.0053 | 0.9365 | 0.0085 | 0.8813 | 0.0049 | 0.0721 | 0.0013 |
| REF|STD | 0.9131 | 0.0043 | 0.2384 | 0.0147 | 0.9428 | 0.0066 | 0.8835 | 0.0070 | 0.0698 | 0.0038 |

## Target attainment of the fold-pooled curves

| target | arm | confirmed | spend_mean | spend_max |
|---|---|---|---|---|
| BA >= 0.93 | E1CAL+straddle|STD | 5/8 | 42.20 | 58.00 |
| BA >= 0.93 | E1RAW+straddle|STD | 1/8 | 37.00 | 37.00 |
| BA >= 0.93 | H|STD | 6/8 | 47.00 | 60.00 |
| BA >= 0.93 | REF|STD | 6/8 | 27.17 | 49.00 |
| BA >= 0.95 | E1CAL+straddle|STD | 0/8 | – | – |
| BA >= 0.95 | E1RAW+straddle|STD | 0/8 | – | – |
| BA >= 0.95 | H|STD | 0/8 | – | – |
| BA >= 0.95 | REF|STD | 0/8 | – | – |
| log_loss <= 0.2 | E1CAL+straddle|STD | 2/8 | 34.50 | 36.00 |
| log_loss <= 0.2 | E1RAW+straddle|STD | 1/8 | 36.00 | 36.00 |
| log_loss <= 0.2 | H|STD | 7/8 | 45.71 | 60.00 |
| log_loss <= 0.2 | REF|STD | 7/8 | 29.29 | 59.00 |

| contrast | target | restricted_mean_difference(censored=64) | fewer/equal/more | censored_a/b | per_unit | verdict |
|---|---|---|---|---|---|---|
| REF|STD − H|STD | BA >= 0.93 | -14.88 | 4/0/4 | 2/2 | –/60;49/34;33/59;29/–;18/–;19/16;15/56;–/57 | NO CLEAR DIFFERENCE (DEV) |
| REF|STD − H|STD | BA >= 0.95 | 0.00 | 0/8/0 | 8/8 | –/–;–/–;–/–;–/–;–/–;–/–;–/–;–/– | NO CLEAR DIFFERENCE (DEV) |
| REF|STD − H|STD | log_loss <= 0.2 | -14.38 | 4/1/3 | 1/1 | 59/52;21/22;–/59;23/23;13/–;19/60;14/53;56/51 | NO CLEAR DIFFERENCE (DEV) |
| REF|STD − E1RAW+straddle|STD | BA >= 0.93 | -24.25 | 6/2/0 | 2/7 | –/–;49/–;33/37;29/–;18/–;19/–;15/–;–/– | FEWER SIMULATIONS (DEV) |
| REF|STD − E1RAW+straddle|STD | BA >= 0.95 | 0.00 | 0/8/0 | 8/8 | –/–;–/–;–/–;–/–;–/–;–/–;–/–;–/– | NO CLEAR DIFFERENCE (DEV) |
| REF|STD − E1RAW+straddle|STD | log_loss <= 0.2 | -26.88 | 7/0/1 | 1/7 | 59/–;21/–;–/36;23/–;13/–;19/–;14/–;56/– | FEWER SIMULATIONS (DEV) |
| REF|STD − E1CAL+straddle|STD | BA >= 0.93 | -14.00 | 5/1/2 | 2/3 | –/58;49/–;33/27;29/40;18/55;19/–;15/31;–/– | NO CLEAR DIFFERENCE (DEV) |
| REF|STD − E1CAL+straddle|STD | BA >= 0.95 | 0.00 | 0/8/0 | 8/8 | –/–;–/–;–/–;–/–;–/–;–/–;–/–;–/– | NO CLEAR DIFFERENCE (DEV) |
| REF|STD − E1CAL+straddle|STD | log_loss <= 0.2 | -23.00 | 6/0/2 | 1/6 | 59/36;21/–;–/33;23/–;13/–;19/–;14/–;56/– | FEWER SIMULATIONS (DEV) |

## Individual learners (one fold / block each): confirmed own BA ≥ 0.93 by B60 (undefined when the learner's test set has one class)

| arm | learners | defined | attained | spend_mean_attainers | spend_median_attainers |
|---|---|---|---|---|---|
| E1CAL+straddle|STD | 40 | 32 | 8 | 17.62 | 16.50 |
| E1RAW+straddle|STD | 40 | 32 | 8 | 18.88 | 15.50 |
| H|STD | 40 | 32 | 8 | 16.62 | 14.50 |
| REF|STD | 40 | 32 | 7 | 20.71 | 14.00 |

## Matched budgets (fold-pooled, mean over repeats)

| arm | budget | BA | sensitivity | specificity | log_loss | spec_NEW | q20_BA |
|---|---|---|---|---|---|---|---|
| E1CAL+straddle|STD | 8 | 0.675 | 0.553 | 0.797 | 0.590 | 0.552 | 0.597 |
| E1CAL+straddle|STD | 12 | 0.804 | 0.746 | 0.862 | 0.440 | 0.500 | 0.644 |
| E1CAL+straddle|STD | 16 | 0.891 | 0.898 | 0.883 | 0.332 | 0.469 | 0.700 |
| E1CAL+straddle|STD | 24 | 0.899 | 0.891 | 0.907 | 0.272 | 0.510 | 0.728 |
| E1CAL+straddle|STD | 40 | 0.908 | 0.930 | 0.886 | 0.254 | 0.427 | 0.762 |
| E1CAL+straddle|STD | 60 | 0.926 | 0.932 | 0.919 | 0.250 | 0.490 | 0.755 |
| E1RAW+straddle|STD | 8 | 0.798 | 0.809 | 0.787 | 0.680 | 0.260 | 0.646 |
| E1RAW+straddle|STD | 12 | 0.855 | 0.900 | 0.811 | 0.459 | 0.406 | 0.658 |
| E1RAW+straddle|STD | 16 | 0.885 | 0.954 | 0.816 | 0.328 | 0.281 | 0.735 |
| E1RAW+straddle|STD | 24 | 0.903 | 0.954 | 0.852 | 0.288 | 0.302 | 0.753 |
| E1RAW+straddle|STD | 40 | 0.917 | 0.969 | 0.865 | 0.254 | 0.312 | 0.789 |
| E1RAW+straddle|STD | 60 | 0.921 | 0.967 | 0.875 | 0.231 | 0.333 | 0.781 |
| H|STD | 8 | 0.733 | 0.581 | 0.886 | 0.513 | 0.510 | 0.639 |
| H|STD | 12 | 0.887 | 0.872 | 0.902 | 0.292 | 0.146 | 0.752 |
| H|STD | 16 | 0.913 | 0.929 | 0.898 | 0.238 | 0.156 | 0.772 |
| H|STD | 24 | 0.919 | 0.950 | 0.887 | 0.224 | 0.104 | 0.787 |
| H|STD | 40 | 0.912 | 0.957 | 0.867 | 0.238 | 0.115 | 0.799 |
| H|STD | 60 | 0.933 | 0.974 | 0.892 | 0.173 | 0.167 | 0.800 |
| REF|STD | 8 | 0.799 | 0.718 | 0.880 | 0.392 | 0.260 | 0.690 |
| REF|STD | 12 | 0.863 | 0.850 | 0.876 | 0.282 | 0.229 | 0.724 |
| REF|STD | 16 | 0.923 | 0.935 | 0.911 | 0.215 | 0.198 | 0.777 |
| REF|STD | 24 | 0.915 | 0.957 | 0.873 | 0.242 | 0.052 | 0.781 |
| REF|STD | 40 | 0.915 | 0.960 | 0.871 | 0.242 | 0.083 | 0.796 |
| REF|STD | 60 | 0.938 | 0.968 | 0.908 | 0.168 | 0.146 | 0.798 |

Export acceptance: {"cells": 1696, "cells_table": 1696, "BA": 0.0, "log_loss": 0.0, "sensitivity": 0.0, "specificity": 0.0, "brier": 0.0, "PASS": true}

## Blocks: geometry and extrapolation (public inputs; labels evaluator-side)

| block+1 | n | keyhole | P_median_W | VX_median | LS_median_um | ST_median | frac_outside_pool_box | median_dist_to_pool | median_nn_within_pool |
|---|---|---|---|---|---|---|---|---|---|
| 1.000 | 149.000 | 1.000 | 202.895 | 0.736 | 74.929 | 349.795 | 0.000 | 0.854 | 0.341 |
| 2.000 | 88.000 | 84.000 | 389.553 | 0.467 | 44.653 | 426.831 | 0.727 | 1.157 | 0.353 |
| 3.000 | 91.000 | 0.000 | 131.050 | 0.779 | 52.960 | 329.383 | 0.055 | 0.818 | 0.342 |
| 4.000 | 118.000 | 101.000 | 377.704 | 0.544 | 44.138 | 342.152 | 0.000 | 0.899 | 0.370 |
| 5.000 | 95.000 | 11.000 | 167.780 | 0.306 | 65.042 | 354.238 | 0.042 | 0.990 | 0.334 |

## Per block (individual learners, mean over 8 seeds; BA undefined when the block has one class)

| arm | block+1 | budget | n1 | n0 | sensitivity | specificity | BA | log_loss |
|---|---|---|---|---|---|---|---|---|
| E1CAL+straddle|STD | 1 | 16 | 1.000 | 148.000 | 1.000 | 0.968 | 0.984 | 0.236 |
| E1CAL+straddle|STD | 1 | 24 | 1.000 | 148.000 | 1.000 | 0.971 | 0.986 | 0.150 |
| E1CAL+straddle|STD | 1 | 40 | 1.000 | 148.000 | 1.000 | 0.973 | 0.986 | 0.192 |
| E1CAL+straddle|STD | 1 | 60 | 1.000 | 148.000 | 1.000 | 0.974 | 0.987 | 0.218 |
| E1CAL+straddle|STD | 2 | 16 | 84.000 | 4.000 | 0.884 | 0.594 | 0.739 | 0.350 |
| E1CAL+straddle|STD | 2 | 24 | 84.000 | 4.000 | 0.921 | 0.688 | 0.804 | 0.306 |
| E1CAL+straddle|STD | 2 | 40 | 84.000 | 4.000 | 0.887 | 0.531 | 0.709 | 0.273 |
| E1CAL+straddle|STD | 2 | 60 | 84.000 | 4.000 | 0.969 | 0.312 | 0.641 | 0.168 |
| E1CAL+straddle|STD | 3 | 16 | 0.000 | 91.000 | – | 0.966 | – | 0.208 |
| E1CAL+straddle|STD | 3 | 24 | 0.000 | 91.000 | – | 1.000 | – | 0.125 |
| E1CAL+straddle|STD | 3 | 40 | 0.000 | 91.000 | – | 1.000 | – | 0.077 |
| E1CAL+straddle|STD | 3 | 60 | 0.000 | 91.000 | – | 1.000 | – | 0.136 |
| E1CAL+straddle|STD | 4 | 16 | 101.000 | 17.000 | 0.921 | 0.507 | 0.714 | 0.345 |
| E1CAL+straddle|STD | 4 | 24 | 101.000 | 17.000 | 0.882 | 0.529 | 0.706 | 0.336 |
| E1CAL+straddle|STD | 4 | 40 | 101.000 | 17.000 | 0.975 | 0.529 | 0.752 | 0.234 |
| E1CAL+straddle|STD | 4 | 60 | 101.000 | 17.000 | 0.923 | 0.706 | 0.815 | 0.240 |
| E1CAL+straddle|STD | 5 | 16 | 11.000 | 84.000 | 0.795 | 0.732 | 0.764 | 0.568 |
| E1CAL+straddle|STD | 5 | 24 | 11.000 | 84.000 | 0.727 | 0.780 | 0.754 | 0.495 |
| E1CAL+straddle|STD | 5 | 40 | 11.000 | 84.000 | 0.830 | 0.698 | 0.764 | 0.526 |
| E1CAL+straddle|STD | 5 | 60 | 11.000 | 84.000 | 0.727 | 0.807 | 0.767 | 0.499 |
| E1RAW+straddle|STD | 1 | 16 | 1.000 | 148.000 | 1.000 | 0.902 | 0.951 | 0.229 |
| E1RAW+straddle|STD | 1 | 24 | 1.000 | 148.000 | 1.000 | 0.949 | 0.975 | 0.135 |
| E1RAW+straddle|STD | 1 | 40 | 1.000 | 148.000 | 1.000 | 0.964 | 0.982 | 0.116 |
| E1RAW+straddle|STD | 1 | 60 | 1.000 | 148.000 | 1.000 | 0.954 | 0.977 | 0.158 |
| E1RAW+straddle|STD | 2 | 16 | 84.000 | 4.000 | 0.918 | 0.469 | 0.693 | 0.338 |
| E1RAW+straddle|STD | 2 | 24 | 84.000 | 4.000 | 0.935 | 0.562 | 0.749 | 0.325 |
| E1RAW+straddle|STD | 2 | 40 | 84.000 | 4.000 | 0.954 | 0.375 | 0.664 | 0.245 |
| E1RAW+straddle|STD | 2 | 60 | 84.000 | 4.000 | 0.973 | 0.312 | 0.643 | 0.169 |
| E1RAW+straddle|STD | 3 | 16 | 0.000 | 91.000 | – | 0.951 | – | 0.133 |
| E1RAW+straddle|STD | 3 | 24 | 0.000 | 91.000 | – | 0.999 | – | 0.033 |
| E1RAW+straddle|STD | 3 | 40 | 0.000 | 91.000 | – | 1.000 | – | 0.029 |
| E1RAW+straddle|STD | 3 | 60 | 0.000 | 91.000 | – | 1.000 | – | 0.037 |
| E1RAW+straddle|STD | 4 | 16 | 101.000 | 17.000 | 0.984 | 0.279 | 0.632 | 0.319 |
| E1RAW+straddle|STD | 4 | 24 | 101.000 | 17.000 | 0.970 | 0.368 | 0.669 | 0.317 |
| E1RAW+straddle|STD | 4 | 40 | 101.000 | 17.000 | 0.986 | 0.441 | 0.714 | 0.280 |
| E1RAW+straddle|STD | 4 | 60 | 101.000 | 17.000 | 0.974 | 0.537 | 0.755 | 0.231 |
| E1RAW+straddle|STD | 5 | 16 | 11.000 | 84.000 | 0.955 | 0.644 | 0.799 | 0.674 |
| E1RAW+straddle|STD | 5 | 24 | 11.000 | 84.000 | 0.955 | 0.634 | 0.794 | 0.703 |
| E1RAW+straddle|STD | 5 | 40 | 11.000 | 84.000 | 0.920 | 0.655 | 0.788 | 0.663 |
| E1RAW+straddle|STD | 5 | 60 | 11.000 | 84.000 | 0.852 | 0.696 | 0.774 | 0.589 |
| H|STD | 1 | 16 | 1.000 | 148.000 | 0.375 | 0.998 | 0.687 | 0.073 |
| H|STD | 1 | 24 | 1.000 | 148.000 | 0.750 | 0.998 | 0.874 | 0.055 |
| H|STD | 1 | 40 | 1.000 | 148.000 | 0.875 | 0.995 | 0.935 | 0.046 |
| H|STD | 1 | 60 | 1.000 | 148.000 | 1.000 | 0.992 | 0.996 | 0.034 |
| H|STD | 2 | 16 | 84.000 | 4.000 | 0.949 | 0.281 | 0.615 | 0.275 |
| H|STD | 2 | 24 | 84.000 | 4.000 | 0.957 | 0.312 | 0.635 | 0.214 |
| H|STD | 2 | 40 | 84.000 | 4.000 | 0.975 | 0.312 | 0.644 | 0.180 |
| H|STD | 2 | 60 | 84.000 | 4.000 | 0.975 | 0.250 | 0.612 | 0.170 |
| H|STD | 3 | 16 | 0.000 | 91.000 | – | 0.997 | – | 0.137 |
| H|STD | 3 | 24 | 0.000 | 91.000 | – | 1.000 | – | 0.101 |
| H|STD | 3 | 40 | 0.000 | 91.000 | – | 1.000 | – | 0.036 |
| H|STD | 3 | 60 | 0.000 | 91.000 | – | 1.000 | – | 0.024 |
| H|STD | 4 | 16 | 101.000 | 17.000 | 0.932 | 0.360 | 0.646 | 0.334 |
| H|STD | 4 | 24 | 101.000 | 17.000 | 0.953 | 0.316 | 0.635 | 0.308 |
| H|STD | 4 | 40 | 101.000 | 17.000 | 0.943 | 0.346 | 0.644 | 0.325 |
| H|STD | 4 | 60 | 101.000 | 17.000 | 0.981 | 0.456 | 0.719 | 0.210 |
| H|STD | 5 | 16 | 11.000 | 84.000 | 0.795 | 0.750 | 0.773 | 0.440 |
| H|STD | 5 | 24 | 11.000 | 84.000 | 0.886 | 0.713 | 0.800 | 0.512 |
| H|STD | 5 | 40 | 11.000 | 84.000 | 0.966 | 0.631 | 0.798 | 0.675 |
| H|STD | 5 | 60 | 11.000 | 84.000 | 0.898 | 0.717 | 0.807 | 0.494 |
| REF|STD | 1 | 16 | 1.000 | 148.000 | 0.625 | 0.988 | 0.807 | 0.076 |
| REF|STD | 1 | 24 | 1.000 | 148.000 | 0.250 | 0.997 | 0.624 | 0.040 |
| REF|STD | 1 | 40 | 1.000 | 148.000 | 0.125 | 0.998 | 0.562 | 0.032 |
| REF|STD | 1 | 60 | 1.000 | 148.000 | 0.375 | 0.997 | 0.686 | 0.028 |
| REF|STD | 2 | 16 | 84.000 | 4.000 | 0.940 | 0.281 | 0.611 | 0.235 |
| REF|STD | 2 | 24 | 84.000 | 4.000 | 0.963 | 0.156 | 0.560 | 0.194 |
| REF|STD | 2 | 40 | 84.000 | 4.000 | 0.982 | 0.219 | 0.600 | 0.173 |
| REF|STD | 2 | 60 | 84.000 | 4.000 | 0.984 | 0.281 | 0.632 | 0.173 |
| REF|STD | 3 | 16 | 0.000 | 91.000 | – | 1.000 | – | 0.080 |
| REF|STD | 3 | 24 | 0.000 | 91.000 | – | 1.000 | – | 0.032 |
| REF|STD | 3 | 40 | 0.000 | 91.000 | – | 1.000 | – | 0.025 |
| REF|STD | 3 | 60 | 0.000 | 91.000 | – | 1.000 | – | 0.013 |
| REF|STD | 4 | 16 | 101.000 | 17.000 | 0.947 | 0.390 | 0.668 | 0.349 |
| REF|STD | 4 | 24 | 101.000 | 17.000 | 0.968 | 0.228 | 0.598 | 0.370 |
| REF|STD | 4 | 40 | 101.000 | 17.000 | 0.947 | 0.360 | 0.654 | 0.355 |
| REF|STD | 4 | 60 | 101.000 | 17.000 | 0.981 | 0.426 | 0.704 | 0.260 |
| REF|STD | 5 | 16 | 11.000 | 84.000 | 0.818 | 0.815 | 0.817 | 0.377 |
| REF|STD | 5 | 24 | 11.000 | 84.000 | 0.875 | 0.682 | 0.778 | 0.644 |
| REF|STD | 5 | 40 | 11.000 | 84.000 | 0.989 | 0.640 | 0.814 | 0.702 |
| REF|STD | 5 | 60 | 11.000 | 84.000 | 0.773 | 0.780 | 0.776 | 0.420 |

