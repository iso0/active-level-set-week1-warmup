# RC21B confirmation stage (PHR_NRMAP) — final (fresh DEV repeats 35–42; frozen protocol PROTOCOL_RC21B.md)

**Q1 decision accuracy (co-primary) — NEW_MARGIN − H_MARGIN, BA-AULC over the small window (margin 0.02): NOT DIFFERENT (DEV)** (mean Δ +0.0030 ± 0.0034 SE; better in 6/8 repeats)

**Q2 paid simulations to a confirmed BA >= 0.93 (co-primary) — NEW_MARGIN − H_MARGIN: NO CLEAR DIFFERENCE (DEV)** (restricted mean difference -0.38 simulations; fewer/equal/more 4/1/3; censored 0/0)

**Answer to the main question (better decisions OR fewer paid simulations to the same BA target than the previous strongest model): NO (DEV).** Probability-only improvements (log loss / Brier) are reported below and are not decision superiority.

## Pre-declared contrasts

| role | contrast | metric | window | direction | margin | mean | se | min | max | repeats_good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 decision accuracy (co-primary) | NEW_MARGIN − H_MARGIN | BA | small | higher | 0.0200 | 0.0030 | 0.0034 | -0.0105 | 0.0157 | 6/8 | NOT DIFFERENT (DEV) |
| decision, NEW vs H | NEW_MARGIN − H_MARGIN | BA | all | higher | 0.0200 | 0.0012 | 0.0011 | -0.0033 | 0.0049 | 5/8 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | sensitivity | small | higher | 0.0200 | 0.0083 | 0.0059 | -0.0218 | 0.0284 | 6/8 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | specificity | small | higher | 0.0200 | -0.0023 | 0.0039 | -0.0262 | 0.0101 | 4/8 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | sensitivity | all | higher | 0.0200 | 0.0040 | 0.0021 | -0.0031 | 0.0149 | 5/8 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | specificity | all | higher | 0.0200 | -0.0017 | 0.0013 | -0.0057 | 0.0045 | 3/8 | NOT DIFFERENT (DEV) |
| probability, NEW vs H (key secondary) | NEW_MARGIN − H_MARGIN | log_loss | small | lower | 0.0100 | -0.0298 | 0.0048 | -0.0434 | -0.0116 | 8/8 | BETTER (DEV) |
| probability, NEW vs H | NEW_MARGIN − H_MARGIN | log_loss | all | lower | 0.0050 | -0.0123 | 0.0024 | -0.0215 | -0.0034 | 8/8 | BETTER (DEV) |
| probability, NEW vs H | NEW_MARGIN − H_MARGIN | brier | all | lower | 0.0050 | -0.0025 | 0.0007 | -0.0046 | 0.0002 | 6/8 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − ATSAPPROX_MARGIN | log_loss | small | lower | 0.0100 | -0.0239 | 0.0061 | -0.0384 | 0.0133 | 7/8 | BETTER (DEV) |
| control | NEW_MARGIN − ATSAPPROX_MARGIN | log_loss | all | lower | 0.0050 | -0.0138 | 0.0033 | -0.0242 | 0.0044 | 7/8 | BETTER (DEV) |
| control | NEW_MARGIN − ATSAPPROX_MARGIN | BA | small | higher | 0.0200 | 0.0071 | 0.0042 | -0.0116 | 0.0284 | 6/8 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − E1CAL+straddle | log_loss | all | lower | 0.0200 | -0.0644 | 0.0058 | -0.0975 | -0.0511 | 8/8 | BETTER (DEV) |
| control | NEW_MARGIN − E1RAW+straddle | BA | all | higher | 0.0200 | 0.0094 | 0.0015 | 0.0029 | 0.0162 | 8/8 | NOT DIFFERENT (DEV) |

## AULC, B8–B24 (mean and SE over repeats)

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | q20_BA_mean | q20_BA_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.2152 | 0.0036 | 0.9211 | 0.0036 | 0.0594 | 0.0013 | 0.9757 | 0.0012 | 0.9037 | 0.0076 | 0.9386 | 0.0027 | 0.7206 | 0.0076 |
| E1CAL+straddle | 0.3181 | 0.0186 | 0.8898 | 0.0071 | 0.0812 | 0.0035 | 0.9516 | 0.0037 | 0.8697 | 0.0156 | 0.9098 | 0.0059 | 0.6944 | 0.0095 |
| E1RAW+straddle | 0.3780 | 0.0343 | 0.9097 | 0.0037 | 0.0759 | 0.0039 | 0.9660 | 0.0032 | 0.9329 | 0.0059 | 0.8866 | 0.0079 | 0.6966 | 0.0099 |
| H_MARGIN | 0.2211 | 0.0044 | 0.9253 | 0.0047 | 0.0602 | 0.0016 | 0.9758 | 0.0024 | 0.9087 | 0.0102 | 0.9419 | 0.0015 | 0.7394 | 0.0066 |
| NEW_MARGIN | 0.1912 | 0.0072 | 0.9283 | 0.0036 | 0.0537 | 0.0021 | 0.9775 | 0.0022 | 0.9170 | 0.0085 | 0.9396 | 0.0036 | 0.7391 | 0.0073 |

## AULC, B8–B60

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | q20_BA_mean | q20_BA_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.1597 | 0.0023 | 0.9419 | 0.0018 | 0.0432 | 0.0007 | 0.9839 | 0.0003 | 0.9309 | 0.0038 | 0.9529 | 0.0012 | 0.7653 | 0.0046 |
| E1CAL+straddle | 0.2103 | 0.0082 | 0.9267 | 0.0027 | 0.0544 | 0.0015 | 0.9731 | 0.0017 | 0.9135 | 0.0057 | 0.9400 | 0.0023 | 0.7465 | 0.0037 |
| E1RAW+straddle | 0.2427 | 0.0123 | 0.9369 | 0.0014 | 0.0526 | 0.0015 | 0.9801 | 0.0012 | 0.9485 | 0.0035 | 0.9254 | 0.0030 | 0.7504 | 0.0047 |
| H_MARGIN | 0.1582 | 0.0020 | 0.9452 | 0.0020 | 0.0429 | 0.0007 | 0.9858 | 0.0009 | 0.9358 | 0.0042 | 0.9546 | 0.0009 | 0.7776 | 0.0046 |
| NEW_MARGIN | 0.1459 | 0.0037 | 0.9463 | 0.0017 | 0.0404 | 0.0010 | 0.9863 | 0.0008 | 0.9398 | 0.0034 | 0.9529 | 0.0013 | 0.7770 | 0.0045 |

## Target attainment and confirmation spend (total paid simulations incl. the 8-point startup; confirmation = level at b and at b + 4; censored = not confirmed by B60). Held-out targets are offline benchmarks, not stopping rules.

| target | arm | confirmed | censored | first_mean | spend_mean | spend_median | spend_min | spend_max | spend_per_repeat |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.93 | ATSAPPROX_MARGIN | 8/8 | 0 | 13.62 | 21.12 | 20.50 | 15 | 27 | 19,19,22,15,19,26,22,27 |
| BA >= 0.93 | E1CAL+straddle | 8/8 | 0 | 20.75 | 25.38 | 25.00 | 14 | 35 | 26,14,34,25,21,23,25,35 |
| BA >= 0.93 | E1RAW+straddle | 8/8 | 0 | 19.25 | 24.25 | 23.00 | 21 | 30 | 26,23,27,22,21,23,22,30 |
| BA >= 0.93 | H_MARGIN | 8/8 | 0 | 11.75 | 16.75 | 16.00 | 14 | 23 | 14,14,16,15,16,23,20,16 |
| BA >= 0.93 | NEW_MARGIN | 8/8 | 0 | 12.00 | 16.38 | 17.00 | 12 | 20 | 18,12,20,14,18,19,14,16 |
| log_loss <= 0.2 | ATSAPPROX_MARGIN | 8/8 | 0 | 16.75 | 20.75 | 20.00 | 19 | 24 | 21,20,24,20,20,19,22,20 |
| log_loss <= 0.2 | E1CAL+straddle | 8/8 | 0 | 20.50 | 27.75 | 28.00 | 23 | 34 | 24,24,30,27,23,31,29,34 |
| log_loss <= 0.2 | E1RAW+straddle | 8/8 | 0 | 25.25 | 30.75 | 32.00 | 23 | 34 | 34,26,34,32,31,34,23,32 |
| log_loss <= 0.2 | H_MARGIN | 8/8 | 0 | 15.88 | 20.62 | 20.00 | 18 | 24 | 24,19,18,21,20,20,20,23 |
| log_loss <= 0.2 | NEW_MARGIN | 8/8 | 0 | 12.75 | 16.88 | 17.00 | 13 | 22 | 22,13,19,15,16,18,14,18 |

Paired spend (restricted score: a censored trajectory is scored 64, a lower bound; observed differences use repeats where both confirmed):

| contrast | restricted_mean_difference(censored=64) | fewer/equal/more | both_confirmed | observed_mean_difference_both_confirmed | censored_first/second | per_repeat | verdict | target |
|---|---|---|---|---|---|---|---|---|
| NEW_MARGIN − H_MARGIN | -0.38 | 4/1/3 | 8 | -0.38 | 0/0 | 18/14;12/14;20/16;14/15;18/16;19/23;14/20;16/16 | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − ATSAPPROX_MARGIN | -4.75 | 8/0/0 | 8 | -4.75 | 0/0 | 18/19;12/19;20/22;14/15;18/19;19/26;14/22;16/27 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| H_MARGIN − ATSAPPROX_MARGIN | -4.38 | 7/1/0 | 8 | -4.38 | 0/0 | 14/19;14/19;16/22;15/15;16/19;23/26;20/22;16/27 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| NEW_MARGIN − E1RAW+straddle | -7.88 | 8/0/0 | 8 | -7.88 | 0/0 | 18/26;12/23;20/27;14/22;18/21;19/23;14/22;16/30 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| NEW_MARGIN − E1CAL+straddle | -9.00 | 8/0/0 | 8 | -9.00 | 0/0 | 18/26;12/14;20/34;14/25;18/21;19/23;14/25;16/35 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| NEW_MARGIN − H_MARGIN | -3.75 | 7/0/1 | 8 | -3.75 | 0/0 | 22/24;13/19;19/18;15/21;16/20;18/20;14/20;18/23 | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − ATSAPPROX_MARGIN | -3.88 | 7/0/1 | 8 | -3.88 | 0/0 | 22/21;13/20;19/24;15/20;16/20;18/19;14/22;18/20 | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |
| H_MARGIN − ATSAPPROX_MARGIN | -0.12 | 3/1/4 | 8 | -0.12 | 0/0 | 24/21;19/20;18/24;21/20;20/20;20/19;20/22;23/20 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − E1RAW+straddle | -13.88 | 8/0/0 | 8 | -13.88 | 0/0 | 22/34;13/26;19/34;15/32;16/31;18/34;14/23;18/32 | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − E1CAL+straddle | -10.88 | 8/0/0 | 8 | -10.88 | 0/0 | 22/24;13/24;19/30;15/27;16/23;18/31;14/29;18/34 | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |

## Matched budgets (mean over repeats): both recalls, q20 and the NEW-batch conduction recall (corner diagnostic)

| arm | budget | BA | sensitivity | specificity | log_loss | brier | AUC | q20_BA | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 8 | 0.855 | 0.819 | 0.891 | 0.335 | 0.101 | 0.942 | 0.654 | 0.458 |
| ATSAPPROX_MARGIN | 12 | 0.915 | 0.888 | 0.942 | 0.225 | 0.061 | 0.977 | 0.709 | 0.292 |
| ATSAPPROX_MARGIN | 16 | 0.930 | 0.921 | 0.939 | 0.202 | 0.055 | 0.980 | 0.735 | 0.333 |
| ATSAPPROX_MARGIN | 20 | 0.938 | 0.924 | 0.951 | 0.180 | 0.048 | 0.984 | 0.734 | 0.260 |
| ATSAPPROX_MARGIN | 24 | 0.946 | 0.937 | 0.955 | 0.166 | 0.044 | 0.985 | 0.763 | 0.240 |
| ATSAPPROX_MARGIN | 32 | 0.952 | 0.944 | 0.960 | 0.138 | 0.036 | 0.988 | 0.787 | 0.281 |
| ATSAPPROX_MARGIN | 40 | 0.951 | 0.940 | 0.962 | 0.131 | 0.035 | 0.988 | 0.783 | 0.365 |
| ATSAPPROX_MARGIN | 60 | 0.957 | 0.953 | 0.962 | 0.117 | 0.031 | 0.990 | 0.806 | 0.333 |
| E1CAL+straddle | 8 | 0.789 | 0.775 | 0.803 | 0.515 | 0.140 | 0.879 | 0.624 | 0.406 |
| E1CAL+straddle | 12 | 0.860 | 0.815 | 0.904 | 0.378 | 0.096 | 0.945 | 0.667 | 0.448 |
| E1CAL+straddle | 16 | 0.910 | 0.900 | 0.920 | 0.301 | 0.072 | 0.961 | 0.708 | 0.365 |
| E1CAL+straddle | 20 | 0.921 | 0.913 | 0.928 | 0.231 | 0.060 | 0.972 | 0.719 | 0.406 |
| E1CAL+straddle | 24 | 0.919 | 0.888 | 0.949 | 0.223 | 0.059 | 0.974 | 0.743 | 0.510 |
| E1CAL+straddle | 32 | 0.941 | 0.927 | 0.955 | 0.171 | 0.043 | 0.980 | 0.762 | 0.490 |
| E1CAL+straddle | 40 | 0.946 | 0.937 | 0.954 | 0.155 | 0.041 | 0.985 | 0.770 | 0.438 |
| E1CAL+straddle | 60 | 0.950 | 0.943 | 0.957 | 0.146 | 0.038 | 0.986 | 0.783 | 0.438 |
| E1RAW+straddle | 8 | 0.849 | 0.888 | 0.810 | 0.598 | 0.125 | 0.930 | 0.646 | 0.292 |
| E1RAW+straddle | 12 | 0.894 | 0.920 | 0.868 | 0.441 | 0.087 | 0.957 | 0.669 | 0.344 |
| E1RAW+straddle | 16 | 0.915 | 0.941 | 0.890 | 0.350 | 0.070 | 0.970 | 0.695 | 0.229 |
| E1RAW+straddle | 20 | 0.927 | 0.947 | 0.908 | 0.299 | 0.061 | 0.975 | 0.716 | 0.260 |
| E1RAW+straddle | 24 | 0.938 | 0.953 | 0.923 | 0.238 | 0.051 | 0.981 | 0.749 | 0.292 |
| E1RAW+straddle | 32 | 0.950 | 0.956 | 0.943 | 0.191 | 0.043 | 0.985 | 0.774 | 0.375 |
| E1RAW+straddle | 40 | 0.949 | 0.953 | 0.946 | 0.172 | 0.041 | 0.987 | 0.778 | 0.396 |
| E1RAW+straddle | 60 | 0.952 | 0.953 | 0.950 | 0.162 | 0.038 | 0.989 | 0.778 | 0.396 |
| H_MARGIN | 8 | 0.845 | 0.805 | 0.884 | 0.382 | 0.115 | 0.910 | 0.675 | 0.260 |
| H_MARGIN | 12 | 0.922 | 0.906 | 0.938 | 0.245 | 0.066 | 0.977 | 0.735 | 0.135 |
| H_MARGIN | 16 | 0.929 | 0.909 | 0.948 | 0.201 | 0.054 | 0.983 | 0.740 | 0.219 |
| H_MARGIN | 20 | 0.945 | 0.935 | 0.956 | 0.176 | 0.046 | 0.987 | 0.770 | 0.260 |
| H_MARGIN | 24 | 0.947 | 0.934 | 0.959 | 0.164 | 0.043 | 0.987 | 0.770 | 0.219 |
| H_MARGIN | 32 | 0.953 | 0.947 | 0.960 | 0.135 | 0.036 | 0.990 | 0.796 | 0.281 |
| H_MARGIN | 40 | 0.958 | 0.952 | 0.963 | 0.127 | 0.034 | 0.991 | 0.804 | 0.302 |
| H_MARGIN | 60 | 0.956 | 0.952 | 0.961 | 0.116 | 0.032 | 0.991 | 0.801 | 0.333 |
| NEW_MARGIN | 8 | 0.862 | 0.848 | 0.875 | 0.332 | 0.101 | 0.929 | 0.690 | 0.250 |
| NEW_MARGIN | 12 | 0.929 | 0.924 | 0.934 | 0.204 | 0.057 | 0.976 | 0.742 | 0.188 |
| NEW_MARGIN | 16 | 0.935 | 0.921 | 0.949 | 0.176 | 0.049 | 0.982 | 0.737 | 0.240 |
| NEW_MARGIN | 20 | 0.940 | 0.929 | 0.952 | 0.160 | 0.044 | 0.985 | 0.749 | 0.292 |
| NEW_MARGIN | 24 | 0.945 | 0.936 | 0.953 | 0.150 | 0.041 | 0.987 | 0.771 | 0.260 |
| NEW_MARGIN | 32 | 0.951 | 0.945 | 0.956 | 0.136 | 0.037 | 0.989 | 0.783 | 0.292 |
| NEW_MARGIN | 40 | 0.957 | 0.957 | 0.958 | 0.123 | 0.034 | 0.991 | 0.800 | 0.281 |
| NEW_MARGIN | 60 | 0.957 | 0.951 | 0.964 | 0.110 | 0.031 | 0.992 | 0.806 | 0.354 |

## Hard fast-scan corner (NEW-batch conduction runs predicted Keyhole, summed over repeats) and calibration

| arm | budget | cal_slope | ECE | corner_errors | corner_n |
|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 24 | 1.461 | 0.049 | 73 | 96 |
| ATSAPPROX_MARGIN | 40 | 1.260 | 0.031 | 61 | 96 |
| ATSAPPROX_MARGIN | 60 | 1.169 | 0.022 | 64 | 96 |
| E1CAL+straddle | 24 | 1.127 | 0.063 | 47 | 96 |
| E1CAL+straddle | 40 | 1.093 | 0.037 | 54 | 96 |
| E1CAL+straddle | 60 | 1.173 | 0.034 | 54 | 96 |
| E1RAW+straddle | 24 | 0.529 | 0.045 | 68 | 96 |
| E1RAW+straddle | 40 | 0.562 | 0.033 | 58 | 96 |
| E1RAW+straddle | 60 | 0.556 | 0.031 | 58 | 96 |
| H_MARGIN | 24 | 1.710 | 0.055 | 75 | 96 |
| H_MARGIN | 40 | 1.433 | 0.034 | 67 | 96 |
| H_MARGIN | 60 | 1.194 | 0.022 | 64 | 96 |
| NEW_MARGIN | 24 | 1.335 | 0.038 | 71 | 96 |
| NEW_MARGIN | 40 | 1.303 | 0.026 | 69 | 96 |
| NEW_MARGIN | 60 | 1.171 | 0.021 | 62 | 96 |

## Short-Keyhole capture (diagnostic)

| arm | budget | shortK_captured | shortK_total |
|---|---|---|---|
| ATSAPPROX_MARGIN | 24 | 146 | 176 |
| ATSAPPROX_MARGIN | 60 | 146 | 176 |
| E1CAL+straddle | 24 | 109 | 176 |
| E1CAL+straddle | 60 | 127 | 176 |
| E1RAW+straddle | 24 | 144 | 176 |
| E1RAW+straddle | 60 | 138 | 176 |
| H_MARGIN | 24 | 140 | 176 |
| H_MARGIN | 60 | 148 | 176 |
| NEW_MARGIN | 24 | 140 | 176 |
| NEW_MARGIN | 60 | 143 | 176 |

## Compute: decision CPU (seconds, single thread) separately from the paid-simulation count

| arm | trajectories | cpu_s_mean | cpu_s_total | decision_cpu_s_per_step | paid_simulations_per_trajectory |
|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 40 | 3.74 | 149.69 | – | 60.00 |
| E1S | 40 | 27.18 | 1087.39 | – | 60.00 |
| H_MARGIN | 40 | 46.27 | 1851.00 | 0.87 | 60.00 |
| NEW_MARGIN | 40 | 46.56 | 1862.55 | 0.88 | 60.00 |

## Matched-path by-products on the physical arms' own paths (every budget; exploratory)

| arm | log_loss B8–B24 | BA B8–B24 | sensitivity B8–B24 | specificity B8–B24 | log_loss B8–B60 | BA B8–B60 | sensitivity B8–B60 | specificity B8–B60 |
|---|---|---|---|---|---|---|---|---|
| PHR@H_MARGIN | 0.2486 | 0.9276 | 0.9114 | 0.9439 | 0.1781 | 0.9459 | 0.9362 | 0.9555 |
| PHR@NEW_MARGIN | 0.2458 | 0.9275 | 0.9140 | 0.9410 | 0.1775 | 0.9454 | 0.9375 | 0.9534 |
| PHR_FX@H_MARGIN | 0.2700 | 0.9254 | 0.9090 | 0.9418 | 0.1881 | 0.9452 | 0.9359 | 0.9545 |
| PHR_FX@NEW_MARGIN | 0.2730 | 0.9217 | 0.9074 | 0.9361 | 0.1906 | 0.9441 | 0.9371 | 0.9511 |
| PHR_FXMAP@H_MARGIN | 0.2211 | 0.9254 | 0.9090 | 0.9418 | 0.1582 | 0.9452 | 0.9359 | 0.9545 |
| PHR_FXMAP@NEW_MARGIN | 0.2257 | 0.9217 | 0.9074 | 0.9361 | 0.1603 | 0.9441 | 0.9371 | 0.9511 |
| PHR_NR@H_MARGIN | 0.2413 | 0.9289 | 0.9147 | 0.9430 | 0.1743 | 0.9467 | 0.9381 | 0.9553 |
| PHR_NR@NEW_MARGIN | 0.2385 | 0.9289 | 0.9175 | 0.9403 | 0.1731 | 0.9465 | 0.9399 | 0.9531 |
| PHR_NRMAP@H_MARGIN | 0.1921 | 0.9282 | 0.9136 | 0.9428 | 0.1475 | 0.9465 | 0.9377 | 0.9552 |
| PHR_NRMAP@NEW_MARGIN | 0.1912 | 0.9283 | 0.9170 | 0.9396 | 0.1459 | 0.9463 | 0.9398 | 0.9529 |
| SHQ_ATS_H@H_MARGIN | 0.2211 | 0.9253 | 0.9087 | 0.9419 | 0.1582 | 0.9452 | 0.9358 | 0.9546 |
| SHQ_ATS_H@NEW_MARGIN | 0.2256 | 0.9217 | 0.9072 | 0.9362 | 0.1602 | 0.9441 | 0.9370 | 0.9512 |
| SHQ_ATS_X@H_MARGIN | 0.2318 | 0.9121 | 0.8854 | 0.9388 | 0.1686 | 0.9371 | 0.9210 | 0.9533 |
| SHQ_ATS_X@NEW_MARGIN | 0.2427 | 0.9067 | 0.8829 | 0.9305 | 0.1719 | 0.9359 | 0.9226 | 0.9491 |

Decomposition (paired by repeat): 'model on P's queries' = same paid prefixes, different classifier; 'path' = same classifier, different query paths.

| decomposition | contrast | window | metric | mean | se | repeats_good |
|---|---|---|---|---|---|---|
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | BA | 0.0066 | 0.0021 | 7/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | log_loss | -0.0344 | 0.0043 | 8/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | sensitivity | 0.0097 | 0.0032 | 7/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | specificity | 0.0034 | 0.0018 | 6/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | BA | 0.0022 | 0.0008 | 7/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | log_loss | -0.0143 | 0.0015 | 8/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | sensitivity | 0.0027 | 0.0016 | 7/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NRMAP@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | specificity | 0.0017 | 0.0006 | 6/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | BA | 0.0029 | 0.0014 | 6/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | -0.0290 | 0.0033 | 8/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | 0.0049 | 0.0022 | 6/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | 0.0009 | 0.0013 | 5/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | BA | 0.0013 | 0.0006 | 6/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | -0.0107 | 0.0016 | 8/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | 0.0019 | 0.0013 | 6/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NRMAP@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | 0.0007 | 0.0003 | 7/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | BA | -0.0036 | 0.0041 | 3/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | 0.0045 | 0.0056 | 3/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | -0.0014 | 0.0073 | 4/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | -0.0057 | 0.0039 | 3/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | BA | -0.0011 | 0.0011 | 2/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | 0.0020 | 0.0019 | 3/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | 0.0013 | 0.0027 | 3/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | -0.0034 | 0.0013 | 2/8 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | small | BA | 0.0001 | 0.0036 | 3/8 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | small | log_loss | -0.0009 | 0.0056 | 4/8 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | small | sensitivity | 0.0034 | 0.0070 | 5/8 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | small | specificity | -0.0032 | 0.0037 | 4/8 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | all | BA | -0.0001 | 0.0012 | 4/8 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | all | log_loss | -0.0016 | 0.0027 | 4/8 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | all | sensitivity | 0.0021 | 0.0027 | 5/8 |
| path: NEW model on NEW's vs H's queries | PHR_NRMAP@NEW_MARGIN − PHR_NRMAP@H_MARGIN | all | specificity | -0.0024 | 0.0013 | 3/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | BA | -0.0150 | 0.0030 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | log_loss | 0.0171 | 0.0030 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | sensitivity | -0.0244 | 0.0054 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | specificity | -0.0057 | 0.0016 | 1/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | BA | -0.0082 | 0.0015 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | log_loss | 0.0116 | 0.0010 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | sensitivity | -0.0145 | 0.0029 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | specificity | -0.0020 | 0.0008 | 1/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | BA | -0.0132 | 0.0022 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | 0.0107 | 0.0033 | 1/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | -0.0233 | 0.0041 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | -0.0031 | 0.0018 | 2/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | BA | -0.0080 | 0.0011 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | 0.0104 | 0.0012 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | -0.0148 | 0.0023 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | -0.0012 | 0.0011 | 2/8 |

## PHR posterior diagnostics along the physical arms' paths (means)

| arm | budget | post_residual | post_mean_tau_F | post_mean_tau_h | post_mean_sigma_r | post_mean_ell_given_res | n_configs |
|---|---|---|---|---|---|---|---|
| H_MARGIN | 8 | 0.493 | 1.867 | 2.581 | 0.567 | 1.125 | 112.000 |
| H_MARGIN | 12 | 0.488 | 1.644 | 2.743 | 0.558 | 1.128 | 112.000 |
| H_MARGIN | 16 | 0.492 | 1.462 | 2.764 | 0.565 | 1.125 | 112.000 |
| H_MARGIN | 24 | 0.503 | 1.337 | 2.722 | 0.585 | 1.113 | 112.000 |
| H_MARGIN | 40 | 0.454 | 1.324 | 2.468 | 0.478 | 1.103 | 112.000 |
| H_MARGIN | 60 | 0.327 | 1.453 | 2.022 | 0.269 | 1.157 | 112.000 |
| NEW_MARGIN | 8 | 0.493 | 1.867 | 2.581 | 0.567 | 1.125 | 112.000 |
| NEW_MARGIN | 12 | 0.483 | 1.623 | 2.760 | 0.547 | 1.128 | 112.000 |
| NEW_MARGIN | 16 | 0.483 | 1.419 | 2.836 | 0.546 | 1.126 | 112.000 |
| NEW_MARGIN | 24 | 0.479 | 1.326 | 2.712 | 0.537 | 1.123 | 112.000 |
| NEW_MARGIN | 40 | 0.461 | 1.249 | 2.475 | 0.500 | 1.105 | 112.000 |
| NEW_MARGIN | 60 | 0.331 | 1.449 | 2.126 | 0.276 | 1.152 | 112.000 |

