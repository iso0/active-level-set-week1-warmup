# RC21 sequential stage — final (fresh DEV repeats 27–34; frozen protocol PROTOCOL_RC21_FINAL.md)

**Q1 decision accuracy (co-primary) — NEW_MARGIN − H_MARGIN, BA-AULC over the small window (margin 0.02): NOT DIFFERENT (DEV)** (mean Δ +0.0022 ± 0.0039 SE; better in 5/8 repeats)

**Q2 paid simulations to a confirmed BA >= 0.93 (co-primary) — NEW_MARGIN − H_MARGIN: NO CLEAR DIFFERENCE (DEV)** (restricted mean difference -1.75 simulations; fewer/equal/more 4/1/3; censored 0/0)

**Answer to the main question (better decisions OR fewer paid simulations to the same BA target than the previous strongest model): NO (DEV).** Probability-only improvements (log loss / Brier) are reported below and are not decision superiority.

## Pre-declared contrasts

| role | contrast | metric | window | direction | margin | mean | se | min | max | repeats_good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 decision accuracy (co-primary) | NEW_MARGIN − H_MARGIN | BA | small | higher | 0.0200 | 0.0022 | 0.0039 | -0.0173 | 0.0164 | 5/8 | NOT DIFFERENT (DEV) |
| decision, NEW vs H | NEW_MARGIN − H_MARGIN | BA | all | higher | 0.0200 | 0.0021 | 0.0011 | -0.0021 | 0.0068 | 6/8 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | sensitivity | small | higher | 0.0200 | 0.0093 | 0.0073 | -0.0251 | 0.0358 | 6/8 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | specificity | small | higher | 0.0200 | -0.0049 | 0.0051 | -0.0287 | 0.0077 | 4/8 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | sensitivity | all | higher | 0.0200 | 0.0048 | 0.0019 | -0.0052 | 0.0123 | 7/8 | NOT DIFFERENT (DEV) |
| decision, NEW vs H (descriptive) | NEW_MARGIN − H_MARGIN | specificity | all | higher | 0.0200 | -0.0006 | 0.0020 | -0.0077 | 0.0086 | 5/8 | NOT DIFFERENT (DEV) |
| probability, NEW vs H | NEW_MARGIN − H_MARGIN | log_loss | small | lower | 0.0100 | 0.0203 | 0.0080 | -0.0122 | 0.0539 | 1/8 | WORSE (DEV) |
| probability, NEW vs H | NEW_MARGIN − H_MARGIN | log_loss | all | lower | 0.0050 | 0.0108 | 0.0039 | -0.0051 | 0.0275 | 2/8 | NOT DIFFERENT (DEV) |
| probability, NEW vs H | NEW_MARGIN − H_MARGIN | brier | all | lower | 0.0050 | 0.0009 | 0.0010 | -0.0040 | 0.0051 | 3/8 | NOT DIFFERENT (DEV) |
| generic inputs on own queries, X vs H | X_MARGIN − H_MARGIN | BA | small | higher | 0.0200 | -0.0067 | 0.0035 | -0.0209 | 0.0071 | 2/8 | NOT DIFFERENT (DEV) |
| generic inputs on own queries, X vs H | X_MARGIN − H_MARGIN | BA | all | higher | 0.0200 | -0.0033 | 0.0008 | -0.0066 | 0.0002 | 1/8 | NOT DIFFERENT (DEV) |
| generic inputs on own queries, X vs H | X_MARGIN − H_MARGIN | log_loss | small | lower | 0.0100 | -0.0027 | 0.0056 | -0.0267 | 0.0224 | 4/8 | NOT DIFFERENT (DEV) |
| generic inputs on own queries, X vs H | X_MARGIN − H_MARGIN | log_loss | all | lower | 0.0050 | -0.0016 | 0.0037 | -0.0244 | 0.0071 | 2/8 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − ATSAPPROX_MARGIN | log_loss | small | lower | 0.0100 | 0.0295 | 0.0056 | 0.0089 | 0.0581 | 0/8 | WORSE (DEV) |
| control | NEW_MARGIN − ATSAPPROX_MARGIN | BA | small | higher | 0.0200 | 0.0043 | 0.0033 | -0.0136 | 0.0194 | 6/8 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − E1CAL+straddle | log_loss | all | lower | 0.0200 | -0.0294 | 0.0052 | -0.0464 | -0.0049 | 8/8 | BETTER (DEV) |
| control | NEW_MARGIN − E1RAW+straddle | BA | all | higher | 0.0200 | 0.0058 | 0.0020 | -0.0033 | 0.0138 | 7/8 | NOT DIFFERENT (DEV) |
| control | NEW_MARGIN − G3_MARGIN | log_loss | all | lower | 0.0200 | -0.0991 | 0.0055 | -0.1254 | -0.0742 | 8/8 | BETTER (DEV) |

## AULC, B8–B24 (mean and SE over repeats)

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | q20_BA_mean | q20_BA_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.2038 | 0.0045 | 0.9254 | 0.0033 | 0.0550 | 0.0015 | 0.9795 | 0.0014 | 0.9026 | 0.0073 | 0.9481 | 0.0039 | 0.7376 | 0.0046 |
| E1CAL+straddle | 0.3057 | 0.0143 | 0.9009 | 0.0066 | 0.0772 | 0.0038 | 0.9557 | 0.0039 | 0.8909 | 0.0157 | 0.9108 | 0.0058 | 0.6908 | 0.0111 |
| E1RAW+straddle | 0.3688 | 0.0251 | 0.9130 | 0.0049 | 0.0741 | 0.0046 | 0.9662 | 0.0030 | 0.9325 | 0.0087 | 0.8936 | 0.0098 | 0.6920 | 0.0091 |
| G3_MARGIN | 0.3796 | 0.0077 | 0.8883 | 0.0046 | 0.1085 | 0.0029 | 0.9257 | 0.0053 | 0.8529 | 0.0095 | 0.9238 | 0.0032 | 0.7034 | 0.0092 |
| H_MARGIN | 0.2130 | 0.0075 | 0.9274 | 0.0027 | 0.0580 | 0.0022 | 0.9789 | 0.0017 | 0.9105 | 0.0065 | 0.9444 | 0.0032 | 0.7296 | 0.0074 |
| NEW_MARGIN | 0.2333 | 0.0086 | 0.9296 | 0.0036 | 0.0608 | 0.0027 | 0.9784 | 0.0019 | 0.9198 | 0.0071 | 0.9395 | 0.0039 | 0.7333 | 0.0063 |
| X_MARGIN | 0.2103 | 0.0041 | 0.9208 | 0.0044 | 0.0586 | 0.0014 | 0.9743 | 0.0018 | 0.9006 | 0.0111 | 0.9409 | 0.0030 | 0.7214 | 0.0048 |

## AULC, B8–B60

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | q20_BA_mean | q20_BA_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.1575 | 0.0020 | 0.9414 | 0.0016 | 0.0425 | 0.0007 | 0.9857 | 0.0005 | 0.9289 | 0.0027 | 0.9540 | 0.0019 | 0.7621 | 0.0052 |
| E1CAL+straddle | 0.2018 | 0.0067 | 0.9314 | 0.0032 | 0.0516 | 0.0019 | 0.9753 | 0.0018 | 0.9199 | 0.0072 | 0.9428 | 0.0019 | 0.7502 | 0.0091 |
| E1RAW+straddle | 0.2324 | 0.0096 | 0.9384 | 0.0026 | 0.0505 | 0.0020 | 0.9804 | 0.0013 | 0.9455 | 0.0043 | 0.9312 | 0.0036 | 0.7498 | 0.0083 |
| G3_MARGIN | 0.2715 | 0.0034 | 0.9226 | 0.0025 | 0.0726 | 0.0012 | 0.9611 | 0.0020 | 0.9010 | 0.0063 | 0.9442 | 0.0019 | 0.7341 | 0.0084 |
| H_MARGIN | 0.1616 | 0.0041 | 0.9420 | 0.0017 | 0.0441 | 0.0012 | 0.9855 | 0.0006 | 0.9333 | 0.0033 | 0.9508 | 0.0021 | 0.7560 | 0.0054 |
| NEW_MARGIN | 0.1724 | 0.0057 | 0.9442 | 0.0019 | 0.0450 | 0.0015 | 0.9858 | 0.0008 | 0.9381 | 0.0039 | 0.9502 | 0.0019 | 0.7614 | 0.0068 |
| X_MARGIN | 0.1600 | 0.0026 | 0.9387 | 0.0018 | 0.0441 | 0.0008 | 0.9835 | 0.0006 | 0.9272 | 0.0050 | 0.9502 | 0.0021 | 0.7543 | 0.0057 |

## Target attainment and confirmation spend (total paid simulations incl. the 8-point startup; confirmation = level at b and at b + 4; censored = not confirmed by B60). Held-out targets are offline benchmarks, not stopping rules.

| target | arm | confirmed | censored | first_mean | spend_mean | spend_median | spend_min | spend_max | spend_per_repeat |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.93 | ATSAPPROX_MARGIN | 8/8 | 0 | 11.75 | 18.62 | 18.00 | 12 | 27 | 27,25,18,18,15,14,20,12 |
| BA >= 0.93 | E1CAL+straddle | 8/8 | 0 | 19.00 | 25.25 | 24.00 | 15 | 35 | 29,35,34,27,20,21,21,15 |
| BA >= 0.93 | E1RAW+straddle | 8/8 | 0 | 19.25 | 23.62 | 23.50 | 20 | 28 | 26,28,27,26,20,21,21,20 |
| BA >= 0.93 | G3_MARGIN | 8/8 | 0 | 26.75 | 32.00 | 29.50 | 21 | 57 | 25,57,34,21,30,29,35,25 |
| BA >= 0.93 | H_MARGIN | 8/8 | 0 | 10.50 | 18.12 | 15.50 | 13 | 33 | 14,23,33,17,15,14,16,13 |
| BA >= 0.93 | NEW_MARGIN | 8/8 | 0 | 11.38 | 16.38 | 17.50 | 13 | 19 | 17,19,19,13,13,18,19,13 |
| BA >= 0.93 | X_MARGIN | 8/8 | 0 | 14.00 | 20.12 | 18.00 | 12 | 30 | 30,20,18,29,16,18,18,12 |
| log_loss <= 0.2 | ATSAPPROX_MARGIN | 8/8 | 0 | 14.62 | 19.00 | 19.00 | 16 | 23 | 23,19,19,17,17,22,19,16 |
| log_loss <= 0.2 | E1CAL+straddle | 8/8 | 0 | 21.25 | 27.25 | 25.50 | 24 | 35 | 35,25,27,31,24,26,25,25 |
| log_loss <= 0.2 | E1RAW+straddle | 8/8 | 0 | 26.25 | 31.38 | 29.00 | 24 | 40 | 26,40,39,39,25,24,28,30 |
| log_loss <= 0.2 | G3_MARGIN | 8/8 | 0 | 41.00 | 48.25 | 47.50 | 39 | 56 | 39,56,45,51,45,44,50,56 |
| log_loss <= 0.2 | H_MARGIN | 8/8 | 0 | 14.00 | 19.75 | 20.50 | 14 | 23 | 22,18,23,22,20,14,18,21 |
| log_loss <= 0.2 | NEW_MARGIN | 8/8 | 0 | 19.00 | 23.00 | 21.50 | 19 | 30 | 26,30,27,22,19,20,21,19 |
| log_loss <= 0.2 | X_MARGIN | 8/8 | 0 | 14.62 | 18.62 | 18.00 | 16 | 21 | 18,17,18,21,18,16,20,21 |

Paired spend (restricted score: a censored trajectory is scored 64, a lower bound; observed differences use repeats where both confirmed):

| contrast | restricted_mean_difference(censored=64) | fewer/equal/more | both_confirmed | observed_mean_difference_both_confirmed | censored_first/second | per_repeat | verdict | target |
|---|---|---|---|---|---|---|---|---|
| NEW_MARGIN − H_MARGIN | -1.75 | 4/1/3 | 8 | -1.75 | 0/0 | 17/14;19/23;19/33;13/17;13/15;18/14;19/16;13/13 | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| X_MARGIN − H_MARGIN | 2.00 | 3/0/5 | 8 | 2.00 | 0/0 | 30/14;20/23;18/33;29/17;16/15;18/14;18/16;12/13 | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − X_MARGIN | -3.75 | 4/1/3 | 8 | -3.75 | 0/0 | 17/30;19/20;19/18;13/29;13/16;18/18;19/18;13/12 | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − ATSAPPROX_MARGIN | -2.25 | 5/0/3 | 8 | -2.25 | 0/0 | 17/27;19/25;19/18;13/18;13/15;18/14;19/20;13/12 | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| NEW_MARGIN − E1RAW+straddle | -7.25 | 8/0/0 | 8 | -7.25 | 0/0 | 17/26;19/28;19/27;13/26;13/20;18/21;19/21;13/20 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| NEW_MARGIN − E1CAL+straddle | -8.88 | 8/0/0 | 8 | -8.88 | 0/0 | 17/29;19/35;19/34;13/27;13/20;18/21;19/21;13/15 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| NEW_MARGIN − G3_MARGIN | -15.62 | 8/0/0 | 8 | -15.62 | 0/0 | 17/25;19/57;19/34;13/21;13/30;18/29;19/35;13/25 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| NEW_MARGIN − H_MARGIN | 3.25 | 2/1/5 | 8 | 3.25 | 0/0 | 26/22;30/18;27/23;22/22;19/20;20/14;21/18;19/21 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| X_MARGIN − H_MARGIN | -1.12 | 5/1/2 | 8 | -1.12 | 0/0 | 18/22;17/18;18/23;21/22;18/20;16/14;20/18;21/21 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − X_MARGIN | 4.38 | 1/0/7 | 8 | 4.38 | 0/0 | 26/18;30/17;27/18;22/21;19/18;20/16;21/20;19/21 | MORE SIMULATIONS (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − ATSAPPROX_MARGIN | 4.00 | 1/0/7 | 8 | 4.00 | 0/0 | 26/23;30/19;27/19;22/17;19/17;20/22;21/19;19/16 | MORE SIMULATIONS (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − E1RAW+straddle | -8.38 | 7/1/0 | 8 | -8.38 | 0/0 | 26/26;30/40;27/39;22/39;19/25;20/24;21/28;19/30 | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − E1CAL+straddle | -4.25 | 6/1/1 | 8 | -4.25 | 0/0 | 26/35;30/25;27/27;22/31;19/24;20/26;21/25;19/25 | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |
| NEW_MARGIN − G3_MARGIN | -25.25 | 8/0/0 | 8 | -25.25 | 0/0 | 26/39;30/56;27/45;22/51;19/45;20/44;21/50;19/56 | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |

## Matched budgets (mean over repeats): both recalls, q20 and the NEW-batch conduction recall (corner diagnostic)

| arm | budget | BA | sensitivity | specificity | log_loss | brier | AUC | q20_BA | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 8 | 0.876 | 0.834 | 0.919 | 0.302 | 0.087 | 0.959 | 0.683 | 0.448 |
| ATSAPPROX_MARGIN | 12 | 0.920 | 0.895 | 0.945 | 0.220 | 0.059 | 0.980 | 0.714 | 0.312 |
| ATSAPPROX_MARGIN | 16 | 0.935 | 0.914 | 0.956 | 0.187 | 0.049 | 0.982 | 0.742 | 0.229 |
| ATSAPPROX_MARGIN | 20 | 0.937 | 0.921 | 0.954 | 0.175 | 0.046 | 0.985 | 0.752 | 0.219 |
| ATSAPPROX_MARGIN | 24 | 0.943 | 0.931 | 0.954 | 0.159 | 0.042 | 0.987 | 0.761 | 0.250 |
| ATSAPPROX_MARGIN | 32 | 0.946 | 0.934 | 0.959 | 0.146 | 0.039 | 0.988 | 0.776 | 0.333 |
| ATSAPPROX_MARGIN | 40 | 0.947 | 0.938 | 0.956 | 0.138 | 0.037 | 0.988 | 0.764 | 0.260 |
| ATSAPPROX_MARGIN | 60 | 0.953 | 0.947 | 0.959 | 0.121 | 0.033 | 0.990 | 0.788 | 0.333 |
| E1CAL+straddle | 8 | 0.838 | 0.830 | 0.847 | 0.459 | 0.116 | 0.916 | 0.665 | 0.292 |
| E1CAL+straddle | 12 | 0.901 | 0.907 | 0.895 | 0.343 | 0.088 | 0.951 | 0.661 | 0.281 |
| E1CAL+straddle | 16 | 0.912 | 0.897 | 0.927 | 0.273 | 0.068 | 0.966 | 0.700 | 0.406 |
| E1CAL+straddle | 20 | 0.920 | 0.904 | 0.936 | 0.233 | 0.061 | 0.971 | 0.722 | 0.490 |
| E1CAL+straddle | 24 | 0.930 | 0.911 | 0.949 | 0.198 | 0.052 | 0.976 | 0.745 | 0.510 |
| E1CAL+straddle | 32 | 0.940 | 0.926 | 0.953 | 0.174 | 0.044 | 0.980 | 0.759 | 0.479 |
| E1CAL+straddle | 40 | 0.947 | 0.937 | 0.957 | 0.151 | 0.039 | 0.985 | 0.782 | 0.427 |
| E1CAL+straddle | 60 | 0.949 | 0.938 | 0.959 | 0.136 | 0.036 | 0.988 | 0.782 | 0.438 |
| E1RAW+straddle | 8 | 0.886 | 0.923 | 0.850 | 0.513 | 0.099 | 0.953 | 0.686 | 0.240 |
| E1RAW+straddle | 12 | 0.903 | 0.935 | 0.871 | 0.443 | 0.087 | 0.961 | 0.655 | 0.188 |
| E1RAW+straddle | 16 | 0.917 | 0.927 | 0.907 | 0.317 | 0.067 | 0.970 | 0.705 | 0.333 |
| E1RAW+straddle | 20 | 0.928 | 0.940 | 0.916 | 0.279 | 0.061 | 0.975 | 0.719 | 0.406 |
| E1RAW+straddle | 24 | 0.937 | 0.943 | 0.931 | 0.221 | 0.051 | 0.980 | 0.728 | 0.333 |
| E1RAW+straddle | 32 | 0.946 | 0.950 | 0.943 | 0.188 | 0.044 | 0.984 | 0.764 | 0.417 |
| E1RAW+straddle | 40 | 0.950 | 0.953 | 0.947 | 0.166 | 0.040 | 0.987 | 0.772 | 0.365 |
| E1RAW+straddle | 60 | 0.954 | 0.952 | 0.955 | 0.153 | 0.036 | 0.989 | 0.788 | 0.385 |
| G3_MARGIN | 8 | 0.831 | 0.800 | 0.863 | 0.436 | 0.134 | 0.899 | 0.671 | 0.156 |
| G3_MARGIN | 12 | 0.857 | 0.814 | 0.900 | 0.426 | 0.127 | 0.896 | 0.691 | 0.260 |
| G3_MARGIN | 16 | 0.904 | 0.867 | 0.942 | 0.370 | 0.103 | 0.927 | 0.708 | 0.208 |
| G3_MARGIN | 20 | 0.910 | 0.894 | 0.926 | 0.351 | 0.098 | 0.950 | 0.722 | 0.167 |
| G3_MARGIN | 24 | 0.917 | 0.890 | 0.944 | 0.320 | 0.086 | 0.955 | 0.728 | 0.260 |
| G3_MARGIN | 32 | 0.928 | 0.909 | 0.947 | 0.247 | 0.064 | 0.974 | 0.729 | 0.323 |
| G3_MARGIN | 40 | 0.942 | 0.931 | 0.952 | 0.212 | 0.053 | 0.980 | 0.741 | 0.292 |
| G3_MARGIN | 60 | 0.948 | 0.935 | 0.961 | 0.176 | 0.044 | 0.984 | 0.768 | 0.344 |
| H_MARGIN | 8 | 0.870 | 0.828 | 0.911 | 0.340 | 0.101 | 0.939 | 0.694 | 0.240 |
| H_MARGIN | 12 | 0.929 | 0.912 | 0.947 | 0.237 | 0.063 | 0.980 | 0.731 | 0.167 |
| H_MARGIN | 16 | 0.924 | 0.901 | 0.947 | 0.208 | 0.056 | 0.981 | 0.724 | 0.104 |
| H_MARGIN | 20 | 0.940 | 0.932 | 0.949 | 0.172 | 0.046 | 0.986 | 0.743 | 0.146 |
| H_MARGIN | 24 | 0.937 | 0.926 | 0.947 | 0.173 | 0.047 | 0.985 | 0.728 | 0.198 |
| H_MARGIN | 32 | 0.950 | 0.946 | 0.954 | 0.145 | 0.039 | 0.989 | 0.771 | 0.188 |
| H_MARGIN | 40 | 0.948 | 0.944 | 0.952 | 0.140 | 0.038 | 0.989 | 0.764 | 0.177 |
| H_MARGIN | 60 | 0.953 | 0.947 | 0.958 | 0.121 | 0.034 | 0.990 | 0.782 | 0.271 |
| NEW_MARGIN | 8 | 0.908 | 0.892 | 0.923 | 0.342 | 0.095 | 0.963 | 0.726 | 0.198 |
| NEW_MARGIN | 12 | 0.926 | 0.921 | 0.932 | 0.263 | 0.068 | 0.979 | 0.714 | 0.042 |
| NEW_MARGIN | 16 | 0.941 | 0.938 | 0.944 | 0.216 | 0.055 | 0.982 | 0.738 | 0.094 |
| NEW_MARGIN | 20 | 0.941 | 0.935 | 0.948 | 0.191 | 0.048 | 0.984 | 0.747 | 0.135 |
| NEW_MARGIN | 24 | 0.942 | 0.931 | 0.952 | 0.177 | 0.045 | 0.985 | 0.743 | 0.156 |
| NEW_MARGIN | 32 | 0.948 | 0.943 | 0.953 | 0.156 | 0.040 | 0.988 | 0.761 | 0.156 |
| NEW_MARGIN | 40 | 0.952 | 0.947 | 0.956 | 0.142 | 0.037 | 0.990 | 0.776 | 0.198 |
| NEW_MARGIN | 60 | 0.953 | 0.947 | 0.960 | 0.123 | 0.034 | 0.991 | 0.787 | 0.312 |
| X_MARGIN | 8 | 0.856 | 0.797 | 0.915 | 0.337 | 0.101 | 0.931 | 0.693 | 0.312 |
| X_MARGIN | 12 | 0.913 | 0.889 | 0.937 | 0.232 | 0.065 | 0.972 | 0.724 | 0.208 |
| X_MARGIN | 16 | 0.928 | 0.914 | 0.943 | 0.200 | 0.054 | 0.979 | 0.714 | 0.135 |
| X_MARGIN | 20 | 0.935 | 0.924 | 0.945 | 0.177 | 0.048 | 0.982 | 0.728 | 0.104 |
| X_MARGIN | 24 | 0.939 | 0.929 | 0.948 | 0.162 | 0.044 | 0.984 | 0.738 | 0.135 |
| X_MARGIN | 32 | 0.944 | 0.936 | 0.952 | 0.144 | 0.039 | 0.987 | 0.755 | 0.177 |
| X_MARGIN | 40 | 0.947 | 0.942 | 0.953 | 0.137 | 0.037 | 0.988 | 0.765 | 0.177 |
| X_MARGIN | 60 | 0.949 | 0.940 | 0.958 | 0.123 | 0.035 | 0.989 | 0.779 | 0.271 |

## Hard fast-scan corner (NEW-batch conduction runs predicted Keyhole, summed over repeats) and calibration

| arm | budget | cal_slope | ECE | corner_errors | corner_n |
|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 24 | 1.546 | 0.049 | 72 | 96 |
| ATSAPPROX_MARGIN | 40 | 1.321 | 0.033 | 71 | 96 |
| ATSAPPROX_MARGIN | 60 | 1.133 | 0.023 | 64 | 96 |
| E1CAL+straddle | 24 | 0.982 | 0.038 | 47 | 96 |
| E1CAL+straddle | 40 | 1.194 | 0.030 | 55 | 96 |
| E1CAL+straddle | 60 | 1.335 | 0.037 | 54 | 96 |
| E1RAW+straddle | 24 | 0.563 | 0.039 | 64 | 96 |
| E1RAW+straddle | 40 | 0.578 | 0.031 | 61 | 96 |
| E1RAW+straddle | 60 | 0.590 | 0.027 | 59 | 96 |
| G3_MARGIN | 24 | 2.165 | 0.153 | 71 | 96 |
| G3_MARGIN | 40 | 1.753 | 0.092 | 68 | 96 |
| G3_MARGIN | 60 | 1.532 | 0.066 | 63 | 96 |
| H_MARGIN | 24 | 1.579 | 0.051 | 77 | 96 |
| H_MARGIN | 40 | 1.385 | 0.035 | 79 | 96 |
| H_MARGIN | 60 | 1.166 | 0.023 | 70 | 96 |
| NEW_MARGIN | 24 | 1.643 | 0.060 | 81 | 96 |
| NEW_MARGIN | 40 | 1.510 | 0.044 | 77 | 96 |
| NEW_MARGIN | 60 | 1.362 | 0.031 | 66 | 96 |
| X_MARGIN | 24 | 1.227 | 0.040 | 83 | 96 |
| X_MARGIN | 40 | 1.196 | 0.028 | 79 | 96 |
| X_MARGIN | 60 | 0.977 | 0.016 | 70 | 96 |

## Short-Keyhole capture (diagnostic)

| arm | budget | shortK_captured | shortK_total |
|---|---|---|---|
| ATSAPPROX_MARGIN | 24 | 132 | 176 |
| ATSAPPROX_MARGIN | 60 | 139 | 176 |
| E1CAL+straddle | 24 | 116 | 176 |
| E1CAL+straddle | 60 | 126 | 176 |
| E1RAW+straddle | 24 | 131 | 176 |
| E1RAW+straddle | 60 | 142 | 176 |
| G3_MARGIN | 24 | 119 | 176 |
| G3_MARGIN | 60 | 125 | 176 |
| H_MARGIN | 24 | 135 | 176 |
| H_MARGIN | 60 | 141 | 176 |
| NEW_MARGIN | 24 | 136 | 176 |
| NEW_MARGIN | 60 | 135 | 176 |
| X_MARGIN | 24 | 130 | 176 |
| X_MARGIN | 60 | 133 | 176 |

## Compute: decision CPU (seconds, single thread) separately from the paid-simulation count

| arm | trajectories | cpu_s_mean | cpu_s_total | decision_cpu_s_per_step | paid_simulations_per_trajectory |
|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 40 | 3.64 | 145.41 | – | 60.00 |
| E1S | 40 | 27.10 | 1084.14 | – | 60.00 |
| G3_MARGIN | 40 | 8.49 | 339.58 | – | 60.00 |
| H_MARGIN | 40 | 46.48 | 1859.14 | 0.88 | 60.00 |
| NEW_MARGIN | 40 | 47.48 | 1899.34 | 0.90 | 60.00 |
| X_MARGIN | 40 | 46.12 | 1844.95 | 0.87 | 60.00 |

## Matched-path by-products on the physical arms' own paths (every budget; exploratory)

| arm | log_loss B8–B24 | BA B8–B24 | sensitivity B8–B24 | specificity B8–B24 | log_loss B8–B60 | BA B8–B60 | sensitivity B8–B60 | specificity B8–B60 |
|---|---|---|---|---|---|---|---|---|
| PHR@H_MARGIN | 0.2375 | 0.9318 | 0.9163 | 0.9474 | 0.1793 | 0.9436 | 0.9348 | 0.9524 |
| PHR@NEW_MARGIN | 0.2397 | 0.9298 | 0.9191 | 0.9404 | 0.1760 | 0.9443 | 0.9376 | 0.9509 |
| PHR@X_MARGIN | 0.2315 | 0.9342 | 0.9261 | 0.9424 | 0.1705 | 0.9456 | 0.9385 | 0.9526 |
| PHR_FX@H_MARGIN | 0.2631 | 0.9275 | 0.9106 | 0.9443 | 0.1914 | 0.9420 | 0.9333 | 0.9507 |
| PHR_FX@NEW_MARGIN | 0.2702 | 0.9232 | 0.9096 | 0.9368 | 0.1906 | 0.9422 | 0.9354 | 0.9490 |
| PHR_FX@X_MARGIN | 0.2537 | 0.9296 | 0.9188 | 0.9404 | 0.1813 | 0.9445 | 0.9373 | 0.9517 |
| PHR_FXMAP@H_MARGIN | 0.2130 | 0.9275 | 0.9106 | 0.9443 | 0.1616 | 0.9420 | 0.9333 | 0.9507 |
| PHR_FXMAP@NEW_MARGIN | 0.2224 | 0.9232 | 0.9096 | 0.9368 | 0.1612 | 0.9422 | 0.9354 | 0.9490 |
| PHR_FXMAP@X_MARGIN | 0.2067 | 0.9296 | 0.9188 | 0.9404 | 0.1543 | 0.9445 | 0.9373 | 0.9517 |
| PHR_NR@H_MARGIN | 0.2314 | 0.9326 | 0.9190 | 0.9461 | 0.1762 | 0.9439 | 0.9362 | 0.9516 |
| PHR_NR@NEW_MARGIN | 0.2333 | 0.9296 | 0.9198 | 0.9395 | 0.1724 | 0.9442 | 0.9381 | 0.9502 |
| PHR_NR@X_MARGIN | 0.2261 | 0.9352 | 0.9280 | 0.9423 | 0.1677 | 0.9461 | 0.9397 | 0.9526 |
| PHR_NRMAP@H_MARGIN | 0.1832 | 0.9318 | 0.9181 | 0.9455 | 0.1507 | 0.9437 | 0.9359 | 0.9514 |
| PHR_NRMAP@NEW_MARGIN | 0.1876 | 0.9289 | 0.9192 | 0.9387 | 0.1479 | 0.9439 | 0.9379 | 0.9500 |
| PHR_NRMAP@X_MARGIN | 0.1834 | 0.9349 | 0.9277 | 0.9420 | 0.1459 | 0.9461 | 0.9396 | 0.9525 |
| SHQ_ATS_H@H_MARGIN | 0.2130 | 0.9274 | 0.9105 | 0.9444 | 0.1616 | 0.9420 | 0.9333 | 0.9508 |
| SHQ_ATS_H@NEW_MARGIN | 0.2223 | 0.9231 | 0.9093 | 0.9369 | 0.1612 | 0.9422 | 0.9353 | 0.9491 |
| SHQ_ATS_H@X_MARGIN | 0.2067 | 0.9295 | 0.9187 | 0.9404 | 0.1543 | 0.9445 | 0.9373 | 0.9517 |
| SHQ_ATS_X@H_MARGIN | 0.2223 | 0.9165 | 0.8896 | 0.9434 | 0.1712 | 0.9351 | 0.9195 | 0.9508 |
| SHQ_ATS_X@NEW_MARGIN | 0.2321 | 0.9113 | 0.8901 | 0.9324 | 0.1711 | 0.9349 | 0.9235 | 0.9464 |
| SHQ_ATS_X@X_MARGIN | 0.2103 | 0.9208 | 0.9006 | 0.9409 | 0.1600 | 0.9387 | 0.9272 | 0.9502 |

Decomposition (paired by repeat): 'model on P's queries' = same paid prefixes, different classifier; 'path' = same classifier, different query paths.

| decomposition | contrast | window | metric | mean | se | repeats_good |
|---|---|---|---|---|---|---|
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | BA | 0.0065 | 0.0015 | 7/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | log_loss | 0.0109 | 0.0040 | 1/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | sensitivity | 0.0105 | 0.0029 | 7/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | specificity | 0.0025 | 0.0012 | 6/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | BA | 0.0020 | 0.0007 | 7/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | log_loss | 0.0111 | 0.0029 | 1/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | sensitivity | 0.0028 | 0.0012 | 6/8 |
| model on NEW_MARGIN's queries: NEW − H | PHR_NR@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | specificity | 0.0012 | 0.0006 | 5/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | BA | 0.0051 | 0.0010 | 8/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | 0.0184 | 0.0030 | 0/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | 0.0085 | 0.0023 | 7/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | 0.0018 | 0.0013 | 5/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | BA | 0.0019 | 0.0002 | 8/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | 0.0146 | 0.0026 | 0/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | 0.0030 | 0.0008 | 7/8 |
| model on H_MARGIN's queries: NEW − H | PHR_NR@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | 0.0008 | 0.0008 | 6/8 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | BA | 0.0056 | 0.0007 | 8/8 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | log_loss | 0.0194 | 0.0030 | 0/8 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | sensitivity | 0.0093 | 0.0017 | 7/8 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | specificity | 0.0019 | 0.0007 | 7/8 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | BA | 0.0017 | 0.0005 | 7/8 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | log_loss | 0.0134 | 0.0021 | 0/8 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | sensitivity | 0.0024 | 0.0012 | 6/8 |
| model on X_MARGIN's queries: NEW − H | PHR_NR@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | specificity | 0.0009 | 0.0004 | 7/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | BA | -0.0043 | 0.0038 | 3/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | 0.0093 | 0.0093 | 3/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | -0.0012 | 0.0056 | 4/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | -0.0074 | 0.0055 | 4/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | BA | 0.0002 | 0.0015 | 4/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | -0.0004 | 0.0043 | 4/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | 0.0020 | 0.0018 | 5/8 |
| path: H model on NEW's vs H's queries | SHQ_ATS_H@NEW_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | -0.0017 | 0.0023 | 4/8 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | small | BA | -0.0029 | 0.0035 | 3/8 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | small | log_loss | 0.0019 | 0.0061 | 4/8 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | small | sensitivity | 0.0008 | 0.0068 | 4/8 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | small | specificity | -0.0066 | 0.0051 | 3/8 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | all | BA | 0.0002 | 0.0011 | 4/8 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | all | log_loss | -0.0038 | 0.0033 | 4/8 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | all | sensitivity | 0.0018 | 0.0022 | 6/8 |
| path: NEW model on NEW's vs H's queries | PHR_NR@NEW_MARGIN − PHR_NR@H_MARGIN | all | specificity | -0.0014 | 0.0020 | 3/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | BA | -0.0119 | 0.0025 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | log_loss | 0.0098 | 0.0030 | 1/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | sensitivity | -0.0192 | 0.0046 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | small | specificity | -0.0045 | 0.0016 | 1/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | BA | -0.0072 | 0.0014 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | log_loss | 0.0098 | 0.0013 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | sensitivity | -0.0118 | 0.0026 | 0/8 |
| model on NEW_MARGIN's queries: X − H | SHQ_ATS_X@NEW_MARGIN − SHQ_ATS_H@NEW_MARGIN | all | specificity | -0.0027 | 0.0007 | 1/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | BA | -0.0109 | 0.0023 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | 0.0093 | 0.0027 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | -0.0209 | 0.0050 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | -0.0010 | 0.0014 | 4/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | BA | -0.0069 | 0.0011 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | 0.0096 | 0.0017 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | -0.0138 | 0.0023 | 0/8 |
| model on H_MARGIN's queries: X − H | SHQ_ATS_X@H_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | -0.0000 | 0.0010 | 3/8 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | BA | -0.0088 | 0.0018 | 0/8 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | log_loss | 0.0037 | 0.0022 | 2/8 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | sensitivity | -0.0181 | 0.0036 | 1/8 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | small | specificity | 0.0006 | 0.0011 | 5/8 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | BA | -0.0058 | 0.0009 | 0/8 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | log_loss | 0.0057 | 0.0011 | 0/8 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | sensitivity | -0.0101 | 0.0020 | 1/8 |
| model on X_MARGIN's queries: X − H | SHQ_ATS_X@X_MARGIN − SHQ_ATS_H@X_MARGIN | all | specificity | -0.0014 | 0.0005 | 1/8 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | small | BA | 0.0021 | 0.0034 | 5/8 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | small | log_loss | -0.0063 | 0.0059 | 6/8 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | small | sensitivity | 0.0082 | 0.0092 | 5/8 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | small | specificity | -0.0040 | 0.0036 | 3/8 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | all | BA | 0.0024 | 0.0010 | 7/8 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | all | log_loss | -0.0073 | 0.0036 | 6/8 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | all | sensitivity | 0.0040 | 0.0034 | 6/8 |
| path: H model on X's vs H's queries | SHQ_ATS_H@X_MARGIN − SHQ_ATS_H@H_MARGIN | all | specificity | 0.0009 | 0.0024 | 3/8 |

## PHR posterior diagnostics along the physical arms' paths (means)

| arm | budget | post_residual | post_mean_tau_F | post_mean_tau_h | post_mean_sigma_r | post_mean_ell_given_res | n_configs |
|---|---|---|---|---|---|---|---|
| H_MARGIN | 8 | 0.488 | 1.764 | 2.727 | 0.557 | 1.125 | 112.000 |
| H_MARGIN | 12 | 0.486 | 1.631 | 2.826 | 0.553 | 1.126 | 112.000 |
| H_MARGIN | 16 | 0.482 | 1.485 | 2.840 | 0.545 | 1.125 | 112.000 |
| H_MARGIN | 24 | 0.498 | 1.426 | 2.723 | 0.577 | 1.117 | 112.000 |
| H_MARGIN | 40 | 0.479 | 1.408 | 2.494 | 0.527 | 1.105 | 112.000 |
| H_MARGIN | 60 | 0.341 | 1.489 | 1.983 | 0.288 | 1.146 | 112.000 |
| NEW_MARGIN | 8 | 0.488 | 1.764 | 2.727 | 0.557 | 1.125 | 112.000 |
| NEW_MARGIN | 12 | 0.484 | 1.458 | 2.874 | 0.548 | 1.121 | 112.000 |
| NEW_MARGIN | 16 | 0.477 | 1.605 | 2.741 | 0.532 | 1.119 | 112.000 |
| NEW_MARGIN | 24 | 0.478 | 1.357 | 2.824 | 0.536 | 1.112 | 112.000 |
| NEW_MARGIN | 40 | 0.474 | 1.363 | 2.524 | 0.523 | 1.100 | 112.000 |
| NEW_MARGIN | 60 | 0.342 | 1.466 | 2.086 | 0.289 | 1.151 | 112.000 |
| X_MARGIN | 8 | 0.488 | 1.764 | 2.727 | 0.557 | 1.125 | 112.000 |
| X_MARGIN | 12 | 0.485 | 1.623 | 2.791 | 0.551 | 1.125 | 112.000 |
| X_MARGIN | 16 | 0.472 | 1.553 | 2.794 | 0.523 | 1.125 | 112.000 |
| X_MARGIN | 24 | 0.460 | 1.461 | 2.752 | 0.499 | 1.119 | 112.000 |
| X_MARGIN | 40 | 0.452 | 1.509 | 2.497 | 0.481 | 1.109 | 112.000 |
| X_MARGIN | 60 | 0.411 | 1.535 | 2.127 | 0.395 | 1.152 | 112.000 |

