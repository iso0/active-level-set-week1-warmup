# RC20 sequential stage — final (fresh DEV repeats 19–26; frozen protocol PROTOCOL_RC20_FINAL.md)

**PRIMARY: model, same selector — CAND_MARGIN − ATSCF_MARGIN, log_loss AULC over the small window (lower is better, margin 0.01): BETTER (DEV)** (mean Δ -0.0383 ± 0.0067 SE; good direction in 8/8 repeats)

## Pre-declared contrasts

| role | contrast | metric | window | direction | margin | mean | se | min | max | repeats_good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PRIMARY: model, same selector | CAND_MARGIN − ATSCF_MARGIN | log_loss | small | lower | 0.0100 | -0.0383 | 0.0067 | -0.0757 | -0.0163 | 8/8 | BETTER (DEV) |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | log_loss | all | lower | 0.0050 | -0.0262 | 0.0039 | -0.0439 | -0.0126 | 8/8 | BETTER (DEV) |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | BA | all | higher | 0.0200 | 0.0077 | 0.0013 | 0.0004 | 0.0134 | 8/8 | NOT DIFFERENT (DEV) |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | BA | small | higher | 0.0200 | 0.0200 | 0.0041 | 0.0023 | 0.0376 | 8/8 | NOT DIFFERENT (DEV) |
| model, same selector | CAND_MARGIN − ATSCF_MARGIN | brier | all | lower | 0.0050 | -0.0062 | 0.0009 | -0.0111 | -0.0039 | 8/8 | BETTER (DEV) |
| selector, same posterior | CAND_ETASTRADDLE − CAND_MARGIN | log_loss | small | lower | 0.0100 | 0.0145 | 0.0042 | -0.0042 | 0.0348 | 1/8 | WORSE (DEV) |
| selector, same posterior | CAND_ETASTRADDLE − CAND_MARGIN | BA | all | higher | 0.0200 | 0.0006 | 0.0019 | -0.0091 | 0.0053 | 6/8 | NOT DIFFERENT (DEV) |
| control | CAND_MARGIN − ATSAPPROX_MARGIN | log_loss | small | lower | 0.0100 | -0.0057 | 0.0053 | -0.0300 | 0.0111 | 5/8 | NOT DIFFERENT (DEV) |
| control | CAND_MARGIN − ATSAPPROX_MARGIN | log_loss | all | lower | 0.0050 | -0.0087 | 0.0041 | -0.0222 | 0.0073 | 5/8 | NOT DIFFERENT (DEV) |
| control | CAND_MARGIN − E1CAL+straddle | log_loss | all | lower | 0.0200 | -0.0508 | 0.0087 | -0.1009 | -0.0191 | 8/8 | BETTER (DEV) |
| control | CAND_MARGIN − E1RAW+straddle | BA | all | higher | 0.0200 | 0.0068 | 0.0020 | 0.0000 | 0.0151 | 8/8 | NOT DIFFERENT (DEV) |
| control | CAND_MARGIN − G3_MARGIN | log_loss | all | lower | 0.0200 | -0.1139 | 0.0087 | -0.1552 | -0.0755 | 8/8 | BETTER (DEV) |

## AULC, B8–B24 (mean and SE over repeats)

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.2179 | 0.0054 | 0.9223 | 0.0033 | 0.0594 | 0.0018 | 0.9742 | 0.0022 | 0.9028 | 0.0062 | 0.9417 | 0.0036 |
| ATSCF_MARGIN | 0.2505 | 0.0078 | 0.9096 | 0.0039 | 0.0692 | 0.0027 | 0.9656 | 0.0040 | 0.8841 | 0.0056 | 0.9352 | 0.0059 |
| CAND_ETASTRADDLE | 0.2267 | 0.0069 | 0.9286 | 0.0035 | 0.0612 | 0.0023 | 0.9772 | 0.0023 | 0.9216 | 0.0055 | 0.9355 | 0.0031 |
| CAND_MARGIN | 0.2122 | 0.0047 | 0.9296 | 0.0041 | 0.0573 | 0.0017 | 0.9792 | 0.0023 | 0.9183 | 0.0075 | 0.9409 | 0.0041 |
| E1CAL+straddle | 0.3286 | 0.0282 | 0.9009 | 0.0046 | 0.0795 | 0.0046 | 0.9554 | 0.0035 | 0.8957 | 0.0137 | 0.9062 | 0.0109 |
| E1RAW+straddle | 0.3886 | 0.0323 | 0.9088 | 0.0043 | 0.0778 | 0.0048 | 0.9671 | 0.0026 | 0.9339 | 0.0098 | 0.8836 | 0.0117 |
| G3_MARGIN | 0.3663 | 0.0033 | 0.8973 | 0.0043 | 0.1032 | 0.0014 | 0.9371 | 0.0023 | 0.8806 | 0.0098 | 0.9141 | 0.0066 |

## AULC, B8–B60

| arm | log_loss_mean | log_loss_se | BA_mean | BA_se | brier_mean | brier_se | AUC_mean | AUC_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 0.1623 | 0.0032 | 0.9420 | 0.0016 | 0.0434 | 0.0010 | 0.9837 | 0.0008 | 0.9320 | 0.0026 | 0.9520 | 0.0017 |
| ATSCF_MARGIN | 0.1798 | 0.0037 | 0.9383 | 0.0012 | 0.0479 | 0.0011 | 0.9812 | 0.0013 | 0.9257 | 0.0022 | 0.9510 | 0.0023 |
| CAND_ETASTRADDLE | 0.1585 | 0.0043 | 0.9466 | 0.0023 | 0.0431 | 0.0013 | 0.9864 | 0.0009 | 0.9423 | 0.0029 | 0.9510 | 0.0021 |
| CAND_MARGIN | 0.1536 | 0.0034 | 0.9460 | 0.0015 | 0.0417 | 0.0007 | 0.9869 | 0.0008 | 0.9391 | 0.0025 | 0.9529 | 0.0019 |
| E1CAL+straddle | 0.2044 | 0.0099 | 0.9336 | 0.0023 | 0.0517 | 0.0018 | 0.9767 | 0.0009 | 0.9265 | 0.0055 | 0.9407 | 0.0036 |
| E1RAW+straddle | 0.2332 | 0.0101 | 0.9393 | 0.0016 | 0.0505 | 0.0016 | 0.9820 | 0.0007 | 0.9502 | 0.0026 | 0.9283 | 0.0037 |
| G3_MARGIN | 0.2675 | 0.0059 | 0.9283 | 0.0019 | 0.0707 | 0.0016 | 0.9650 | 0.0020 | 0.9155 | 0.0051 | 0.9410 | 0.0034 |

## Target attainment and confirmation spend (total paid simulations incl. the 8-point startup; confirmation = level at b and at the second checkpoint b + 4; censored = not confirmed by B60). Held-out targets are offline benchmarks, not stopping rules.

| target | arm | confirmed | censored | first_mean | spend_mean | spend_median | spend_min | spend_max | spend_per_repeat |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.93 | ATSAPPROX_MARGIN | 8/8 | 0 | 12.25 | 16.62 | 17.50 | 13.00 | 20.00 | 14,19,13,18,13,17,20,19 |
| BA >= 0.93 | ATSCF_MARGIN | 8/8 | 0 | 13.38 | 19.50 | 19.50 | 13.00 | 25.00 | 13,21,23,17,18,18,21,25 |
| BA >= 0.93 | CAND_ETASTRADDLE | 8/8 | 0 | 10.75 | 16.50 | 15.50 | 12.00 | 26.00 | 26,15,13,16,12,19,16,15 |
| BA >= 0.93 | CAND_MARGIN | 8/8 | 0 | 10.25 | 15.12 | 14.50 | 12.00 | 19.00 | 14,15,12,16,19,17,14,14 |
| BA >= 0.93 | E1CAL+straddle | 8/8 | 0 | 19.12 | 23.12 | 23.00 | 20.00 | 27.00 | 24,25,22,21,20,21,25,27 |
| BA >= 0.93 | E1RAW+straddle | 8/8 | 0 | 18.50 | 22.62 | 23.50 | 17.00 | 26.00 | 24,26,17,23,20,21,25,25 |
| BA >= 0.93 | G3_MARGIN | 8/8 | 0 | 21.25 | 28.88 | 29.00 | 20.00 | 36.00 | 29,32,29,27,20,28,30,36 |
| log_loss <= 0.2 | ATSAPPROX_MARGIN | 8/8 | 0 | 16.50 | 20.50 | 20.50 | 17.00 | 24.00 | 20,23,21,24,18,17,21,20 |
| log_loss <= 0.2 | ATSCF_MARGIN | 8/8 | 0 | 17.75 | 22.50 | 22.00 | 18.00 | 27.00 | 18,27,26,20,22,22,21,24 |
| log_loss <= 0.2 | CAND_ETASTRADDLE | 8/8 | 0 | 17.50 | 22.88 | 22.50 | 19.00 | 28.00 | 25,22,23,22,19,28,21,23 |
| log_loss <= 0.2 | CAND_MARGIN | 8/8 | 0 | 14.75 | 18.75 | 19.00 | 17.00 | 20.00 | 19,19,17,20,19,19,19,18 |
| log_loss <= 0.2 | E1CAL+straddle | 8/8 | 0 | 20.00 | 24.75 | 25.00 | 20.00 | 29.00 | 24,29,22,27,20,25,25,26 |
| log_loss <= 0.2 | E1RAW+straddle | 8/8 | 0 | 23.62 | 28.50 | 27.50 | 21.00 | 38.00 | 26,35,23,38,21,25,29,31 |
| log_loss <= 0.2 | G3_MARGIN | 6/8 | 2 | 48.62 | 49.33 | 49.50 | 40.00 | 60.00 | 40,60,–,42,55,54,45,– |

Paired spend (restricted score: a censored trajectory is scored 64, a lower bound; observed differences use repeats where both confirmed):

| contrast | restricted_mean_difference(censored=64) | fewer/equal/more | both_confirmed | observed_mean_difference_both_confirmed | censored_first/second | per_repeat | verdict | target |
|---|---|---|---|---|---|---|---|---|
| CAND_MARGIN − ATSCF_MARGIN | -4.38 | 6/0/2 | 8 | -4.38 | 0/0 | 14/13;15/21;12/23;16/17;19/18;17/18;14/21;14/25 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| CAND_ETASTRADDLE − CAND_MARGIN | 1.38 | 1/2/5 | 8 | 1.38 | 0/0 | 26/14;15/15;13/12;16/16;12/19;19/17;16/14;15/14 | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| CAND_MARGIN − ATSAPPROX_MARGIN | -1.50 | 5/2/1 | 8 | -1.50 | 0/0 | 14/14;15/19;12/13;16/18;19/13;17/17;14/20;14/19 | NO CLEAR DIFFERENCE (DEV) | BA >= 0.93 |
| CAND_MARGIN − E1RAW+straddle | -7.50 | 8/0/0 | 8 | -7.50 | 0/0 | 14/24;15/26;12/17;16/23;19/20;17/21;14/25;14/25 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| CAND_MARGIN − E1CAL+straddle | -8.00 | 8/0/0 | 8 | -8.00 | 0/0 | 14/24;15/25;12/22;16/21;19/20;17/21;14/25;14/27 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| CAND_MARGIN − G3_MARGIN | -13.75 | 8/0/0 | 8 | -13.75 | 0/0 | 14/29;15/32;12/29;16/27;19/20;17/28;14/30;14/36 | FEWER SIMULATIONS (DEV) | BA >= 0.93 |
| CAND_MARGIN − ATSCF_MARGIN | -3.75 | 6/1/1 | 8 | -3.75 | 0/0 | 19/18;19/27;17/26;20/20;19/22;19/22;19/21;18/24 | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |
| CAND_ETASTRADDLE − CAND_MARGIN | 4.12 | 0/1/7 | 8 | 4.12 | 0/0 | 25/19;22/19;23/17;22/20;19/19;28/19;21/19;23/18 | MORE SIMULATIONS (DEV) | log_loss <= 0.2 |
| CAND_MARGIN − ATSAPPROX_MARGIN | -1.75 | 6/0/2 | 8 | -1.75 | 0/0 | 19/20;19/23;17/21;20/24;19/18;19/17;19/21;18/20 | NO CLEAR DIFFERENCE (DEV) | log_loss <= 0.2 |
| CAND_MARGIN − E1RAW+straddle | -9.75 | 8/0/0 | 8 | -9.75 | 0/0 | 19/26;19/35;17/23;20/38;19/21;19/25;19/29;18/31 | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |
| CAND_MARGIN − E1CAL+straddle | -6.00 | 8/0/0 | 8 | -6.00 | 0/0 | 19/24;19/29;17/22;20/27;19/20;19/25;19/25;18/26 | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |
| CAND_MARGIN − G3_MARGIN | -34.25 | 8/0/0 | 6 | -30.17 | 0/2 | 19/40;19/60;17/–;20/42;19/55;19/54;19/45;18/– | FEWER SIMULATIONS (DEV) | log_loss <= 0.2 |

## Matched budgets (mean over repeats)

| arm | budget | BA | sensitivity | specificity | log_loss | brier | AUC | q20_BA | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 8 | 0.838 | 0.789 | 0.887 | 0.371 | 0.114 | 0.914 | 0.678 | 0.469 |
| ATSAPPROX_MARGIN | 12 | 0.917 | 0.892 | 0.943 | 0.244 | 0.065 | 0.975 | 0.741 | 0.260 |
| ATSAPPROX_MARGIN | 16 | 0.934 | 0.917 | 0.951 | 0.205 | 0.055 | 0.980 | 0.741 | 0.271 |
| ATSAPPROX_MARGIN | 20 | 0.944 | 0.935 | 0.952 | 0.171 | 0.045 | 0.985 | 0.760 | 0.208 |
| ATSAPPROX_MARGIN | 24 | 0.945 | 0.934 | 0.957 | 0.157 | 0.041 | 0.986 | 0.761 | 0.271 |
| ATSAPPROX_MARGIN | 40 | 0.953 | 0.952 | 0.955 | 0.135 | 0.035 | 0.988 | 0.788 | 0.292 |
| ATSAPPROX_MARGIN | 60 | 0.955 | 0.951 | 0.958 | 0.122 | 0.033 | 0.990 | 0.795 | 0.333 |
| ATSCF_MARGIN | 8 | 0.781 | 0.744 | 0.819 | 0.483 | 0.153 | 0.845 | 0.630 | 0.417 |
| ATSCF_MARGIN | 12 | 0.902 | 0.879 | 0.925 | 0.281 | 0.079 | 0.967 | 0.729 | 0.406 |
| ATSCF_MARGIN | 16 | 0.929 | 0.902 | 0.957 | 0.222 | 0.057 | 0.981 | 0.735 | 0.271 |
| ATSCF_MARGIN | 20 | 0.938 | 0.925 | 0.951 | 0.199 | 0.051 | 0.984 | 0.744 | 0.208 |
| ATSCF_MARGIN | 24 | 0.942 | 0.930 | 0.955 | 0.180 | 0.046 | 0.986 | 0.758 | 0.292 |
| ATSCF_MARGIN | 40 | 0.952 | 0.944 | 0.960 | 0.144 | 0.037 | 0.988 | 0.780 | 0.281 |
| ATSCF_MARGIN | 60 | 0.956 | 0.952 | 0.960 | 0.127 | 0.034 | 0.990 | 0.797 | 0.292 |
| CAND_ETASTRADDLE | 8 | 0.866 | 0.851 | 0.880 | 0.349 | 0.104 | 0.932 | 0.668 | 0.302 |
| CAND_ETASTRADDLE | 12 | 0.930 | 0.925 | 0.935 | 0.246 | 0.066 | 0.978 | 0.724 | 0.146 |
| CAND_ETASTRADDLE | 16 | 0.940 | 0.940 | 0.940 | 0.215 | 0.056 | 0.982 | 0.743 | 0.125 |
| CAND_ETASTRADDLE | 20 | 0.943 | 0.944 | 0.943 | 0.186 | 0.049 | 0.984 | 0.748 | 0.115 |
| CAND_ETASTRADDLE | 24 | 0.943 | 0.941 | 0.944 | 0.169 | 0.045 | 0.987 | 0.738 | 0.115 |
| CAND_ETASTRADDLE | 40 | 0.955 | 0.952 | 0.958 | 0.126 | 0.034 | 0.991 | 0.795 | 0.271 |
| CAND_ETASTRADDLE | 60 | 0.958 | 0.957 | 0.960 | 0.110 | 0.031 | 0.992 | 0.801 | 0.260 |
| CAND_MARGIN | 8 | 0.866 | 0.851 | 0.880 | 0.349 | 0.104 | 0.932 | 0.668 | 0.302 |
| CAND_MARGIN | 12 | 0.928 | 0.911 | 0.944 | 0.239 | 0.063 | 0.981 | 0.750 | 0.156 |
| CAND_MARGIN | 16 | 0.935 | 0.922 | 0.947 | 0.190 | 0.050 | 0.984 | 0.749 | 0.229 |
| CAND_MARGIN | 20 | 0.944 | 0.933 | 0.955 | 0.173 | 0.045 | 0.986 | 0.760 | 0.198 |
| CAND_MARGIN | 24 | 0.949 | 0.947 | 0.951 | 0.155 | 0.041 | 0.988 | 0.770 | 0.167 |
| CAND_MARGIN | 40 | 0.953 | 0.946 | 0.959 | 0.126 | 0.034 | 0.991 | 0.779 | 0.260 |
| CAND_MARGIN | 60 | 0.959 | 0.956 | 0.961 | 0.118 | 0.033 | 0.991 | 0.806 | 0.312 |
| E1CAL+straddle | 8 | 0.849 | 0.829 | 0.870 | 0.537 | 0.117 | 0.919 | 0.661 | 0.333 |
| E1CAL+straddle | 12 | 0.863 | 0.864 | 0.861 | 0.438 | 0.107 | 0.923 | 0.669 | 0.417 |
| E1CAL+straddle | 16 | 0.908 | 0.911 | 0.905 | 0.297 | 0.073 | 0.964 | 0.703 | 0.323 |
| E1CAL+straddle | 20 | 0.936 | 0.950 | 0.923 | 0.213 | 0.054 | 0.978 | 0.749 | 0.406 |
| E1CAL+straddle | 24 | 0.944 | 0.939 | 0.949 | 0.182 | 0.046 | 0.983 | 0.777 | 0.500 |
| E1CAL+straddle | 40 | 0.950 | 0.940 | 0.959 | 0.140 | 0.037 | 0.988 | 0.785 | 0.438 |
| E1CAL+straddle | 60 | 0.954 | 0.946 | 0.962 | 0.133 | 0.034 | 0.988 | 0.800 | 0.427 |
| E1RAW+straddle | 8 | 0.868 | 0.890 | 0.847 | 0.635 | 0.113 | 0.934 | 0.662 | 0.302 |
| E1RAW+straddle | 12 | 0.889 | 0.919 | 0.859 | 0.517 | 0.096 | 0.956 | 0.660 | 0.260 |
| E1RAW+straddle | 16 | 0.911 | 0.938 | 0.885 | 0.355 | 0.074 | 0.972 | 0.698 | 0.208 |
| E1RAW+straddle | 20 | 0.934 | 0.964 | 0.904 | 0.263 | 0.059 | 0.983 | 0.734 | 0.312 |
| E1RAW+straddle | 24 | 0.949 | 0.963 | 0.935 | 0.205 | 0.044 | 0.987 | 0.773 | 0.385 |
| E1RAW+straddle | 40 | 0.956 | 0.959 | 0.953 | 0.155 | 0.036 | 0.990 | 0.800 | 0.396 |
| E1RAW+straddle | 60 | 0.958 | 0.961 | 0.955 | 0.147 | 0.035 | 0.990 | 0.802 | 0.396 |
| G3_MARGIN | 8 | 0.821 | 0.822 | 0.820 | 0.449 | 0.139 | 0.898 | 0.645 | 0.271 |
| G3_MARGIN | 12 | 0.902 | 0.871 | 0.933 | 0.376 | 0.105 | 0.937 | 0.717 | 0.219 |
| G3_MARGIN | 16 | 0.909 | 0.887 | 0.931 | 0.363 | 0.100 | 0.937 | 0.710 | 0.198 |
| G3_MARGIN | 20 | 0.928 | 0.912 | 0.945 | 0.318 | 0.083 | 0.960 | 0.735 | 0.240 |
| G3_MARGIN | 24 | 0.929 | 0.915 | 0.944 | 0.290 | 0.075 | 0.969 | 0.724 | 0.250 |
| G3_MARGIN | 40 | 0.937 | 0.931 | 0.942 | 0.233 | 0.060 | 0.977 | 0.746 | 0.271 |
| G3_MARGIN | 60 | 0.950 | 0.937 | 0.963 | 0.172 | 0.043 | 0.985 | 0.776 | 0.375 |

## Compute: GP / decision CPU (seconds) separately from the paid-simulation count

| arm | trajectories | cpu_s_mean | cpu_s_total | decision_cpu_s_per_step | paid_simulations_per_trajectory |
|---|---|---|---|---|---|
| ATSAPPROX_MARGIN | 40 | 3.30 | 131.93 | – | 60.00 |
| ATSCF_MARGIN | 40 | 28.25 | 1130.13 | – | 60.00 |
| CAND_ETASTRADDLE | 40 | 32.47 | 1298.64 | 0.61 | 60.00 |
| CAND_MARGIN | 40 | 29.72 | 1188.62 | 0.56 | 60.00 |
| E1S | 40 | 24.27 | 970.88 | – | 60.00 |
| G3_MARGIN | 40 | 7.03 | 281.38 | – | 60.00 |

## Exploratory: same paid prefixes on the candidate's own paths (recorded every 4 budgets)

| arm | log_loss | BA | brier |
|---|---|---|---|
| HONLY@CAND_ETASTRADDLE | 0.2294 | 0.9415 | 0.0599 |
| HONLY@CAND_MARGIN | 0.2458 | 0.9401 | 0.0638 |
| SHQ_A@CAND_ETASTRADDLE | 0.2247 | 0.9259 | 0.0613 |
| SHQ_A@CAND_MARGIN | 0.2164 | 0.9277 | 0.0587 |
| SHQ_ATS@CAND_ETASTRADDLE | 0.1948 | 0.9312 | 0.0536 |
| SHQ_ATS@CAND_MARGIN | 0.1905 | 0.9309 | 0.0522 |
| SHQ_ATS_H@CAND_ETASTRADDLE | 0.1631 | 0.9445 | 0.0446 |
| SHQ_ATS_H@CAND_MARGIN | 0.1589 | 0.9436 | 0.0435 |
| SHQ_ATS_X@CAND_ETASTRADDLE | 0.1711 | 0.9376 | 0.0474 |
| SHQ_ATS_X@CAND_MARGIN | 0.1664 | 0.9379 | 0.0461 |
| SHQ_A_H@CAND_ETASTRADDLE | 0.1663 | 0.9498 | 0.0444 |
| SHQ_A_H@CAND_MARGIN | 0.1640 | 0.9477 | 0.0441 |

