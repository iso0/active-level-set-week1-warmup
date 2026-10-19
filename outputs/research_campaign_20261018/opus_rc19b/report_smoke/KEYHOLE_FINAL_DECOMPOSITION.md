# RC19B Keyhole — matched-path decomposition on the final paths (exploratory; same paid prefixes, recorded every 4 budgets)

## Matched-path decomposition on the paths of E1S (fresh repeats; every construction on the same paid prefixes)

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@E1S | 0.9420 | 0.9420 | 0.9420 | 0.1674 | 0.1674 | 0.1674 | 0.0457 | 0.0457 | 0.0457 | 0.9816 | 0.9816 | 0.9816 |
| ATSCF@E1S | 0.9420 | 0.9420 | 0.9420 | 0.1727 | 0.1727 | 0.1727 | 0.0471 | 0.0471 | 0.0471 | 0.9805 | 0.9805 | 0.9805 |
| DEPTHCF@E1S | 0.9238 | 0.9238 | 0.9238 | 0.2157 | 0.2157 | 0.2157 | 0.0591 | 0.0591 | 0.0591 | 0.9701 | 0.9701 | 0.9701 |
| E1CAL@E1S | 0.9342 | 0.9342 | 0.9342 | 0.2107 | 0.2107 | 0.2107 | 0.0515 | 0.0515 | 0.0515 | 0.9742 | 0.9742 | 0.9742 |
| E1RAW@E1S | 0.9383 | 0.9383 | 0.9383 | 0.2482 | 0.2482 | 0.2482 | 0.0524 | 0.0524 | 0.0524 | 0.9795 | 0.9795 | 0.9795 |
| G3@E1S | 0.9201 | 0.9201 | 0.9201 | 0.2797 | 0.2797 | 0.2797 | 0.0762 | 0.0762 | 0.0762 | 0.9640 | 0.9640 | 0.9640 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@E1S − E1CAL@E1S | BA_AULC | 0.0078 | – | 0.0078 | 0.0078 | 1/1 |
| ATSCF@E1S − E1CAL@E1S | LL_AULC | -0.0379 | – | -0.0379 | -0.0379 | 1/1 |
| ATSCF@E1S − E1CAL@E1S | Brier_AULC | -0.0044 | – | -0.0044 | -0.0044 | 1/1 |
| ATSCF@E1S − DEPTHCF@E1S | BA_AULC | 0.0182 | – | 0.0182 | 0.0182 | 1/1 |
| ATSCF@E1S − DEPTHCF@E1S | LL_AULC | -0.0430 | – | -0.0430 | -0.0430 | 1/1 |
| ATSCF@E1S − DEPTHCF@E1S | Brier_AULC | -0.0120 | – | -0.0120 | -0.0120 | 1/1 |
| DEPTHCF@E1S − E1CAL@E1S | BA_AULC | -0.0104 | – | -0.0104 | -0.0104 | 0/1 |
| DEPTHCF@E1S − E1CAL@E1S | LL_AULC | 0.0050 | – | 0.0050 | 0.0050 | 0/1 |
| DEPTHCF@E1S − E1CAL@E1S | Brier_AULC | 0.0076 | – | 0.0076 | 0.0076 | 0/1 |
| E1CAL@E1S − E1RAW@E1S | BA_AULC | -0.0040 | – | -0.0040 | -0.0040 | 0/1 |
| E1CAL@E1S − E1RAW@E1S | LL_AULC | -0.0375 | – | -0.0375 | -0.0375 | 1/1 |
| E1CAL@E1S − E1RAW@E1S | Brier_AULC | -0.0009 | – | -0.0009 | -0.0009 | 1/1 |
| ATSCF@E1S − ATSAPPROX@E1S | BA_AULC | -0.0001 | – | -0.0001 | -0.0001 | 0/1 |
| ATSCF@E1S − ATSAPPROX@E1S | LL_AULC | 0.0053 | – | 0.0053 | 0.0053 | 0/1 |
| ATSCF@E1S − ATSAPPROX@E1S | Brier_AULC | 0.0014 | – | 0.0014 | 0.0014 | 0/1 |
| ATSCF@E1S − G3@E1S | BA_AULC | 0.0218 | – | 0.0218 | 0.0218 | 1/1 |
| ATSCF@E1S − G3@E1S | LL_AULC | -0.1070 | – | -0.1070 | -0.1070 | 1/1 |
| ATSCF@E1S − G3@E1S | Brier_AULC | -0.0292 | – | -0.0292 | -0.0292 | 1/1 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@E1S | 1/1 | 16.00 | 20.00 | 20 |
| ATSCF@E1S | 1/1 | 16.00 | 20.00 | 20 |
| DEPTHCF@E1S | 1/1 | 20.00 | 24.00 | 24 |
| E1CAL@E1S | 1/1 | 20.00 | 24.00 | 24 |
| E1RAW@E1S | 1/1 | 16.00 | 20.00 | 20 |
| G3@E1S | 1/1 | 28.00 | 32.00 | 32 |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@E1S | 16 | 0.953 | 0.949 | 0.956 | 0.988 | 0.046 | 0.180 | 0.799 | 19.000 | 0.083 |
| ATSAPPROX@E1S | 24 | 0.947 | 0.944 | 0.951 | 0.990 | 0.041 | 0.158 | 0.790 | 20.000 | 0.000 |
| ATSAPPROX@E1S | 40 | 0.958 | 0.959 | 0.956 | 0.990 | 0.037 | 0.135 | 0.799 | 20.000 | 0.167 |
| ATSAPPROX@E1S | 60 | 0.959 | 0.964 | 0.953 | 0.992 | 0.032 | 0.122 | 0.789 | 20.000 | 0.083 |
| ATSCF@E1S | 16 | 0.938 | 0.934 | 0.942 | 0.984 | 0.052 | 0.200 | 0.763 | 17.000 | 0.083 |
| ATSCF@E1S | 24 | 0.950 | 0.944 | 0.956 | 0.989 | 0.040 | 0.159 | 0.790 | 19.000 | 0.083 |
| ATSCF@E1S | 40 | 0.959 | 0.959 | 0.959 | 0.990 | 0.037 | 0.137 | 0.808 | 20.000 | 0.250 |
| ATSCF@E1S | 60 | 0.960 | 0.964 | 0.956 | 0.992 | 0.034 | 0.129 | 0.808 | 20.000 | 0.083 |
| DEPTHCF@E1S | 16 | 0.890 | 0.878 | 0.901 | 0.963 | 0.093 | 0.326 | 0.701 | 9.000 | 0.500 |
| DEPTHCF@E1S | 24 | 0.934 | 0.904 | 0.965 | 0.985 | 0.060 | 0.234 | 0.756 | 12.000 | 0.417 |
| DEPTHCF@E1S | 40 | 0.948 | 0.934 | 0.962 | 0.989 | 0.040 | 0.156 | 0.773 | 15.000 | 0.500 |
| DEPTHCF@E1S | 60 | 0.956 | 0.949 | 0.962 | 0.992 | 0.036 | 0.141 | 0.790 | 16.000 | 0.500 |
| E1CAL@E1S | 16 | 0.925 | 0.919 | 0.930 | 0.967 | 0.056 | 0.264 | 0.699 | 14.000 | 0.250 |
| E1CAL@E1S | 24 | 0.941 | 0.934 | 0.948 | 0.974 | 0.047 | 0.203 | 0.781 | 18.000 | 0.333 |
| E1CAL@E1S | 40 | 0.948 | 0.949 | 0.948 | 0.987 | 0.042 | 0.150 | 0.753 | 16.000 | 0.500 |
| E1CAL@E1S | 60 | 0.960 | 0.964 | 0.956 | 0.991 | 0.032 | 0.125 | 0.799 | 18.000 | 0.417 |
| E1RAW@E1S | 16 | 0.935 | 0.949 | 0.922 | 0.979 | 0.055 | 0.265 | 0.725 | 18.000 | 0.250 |
| E1RAW@E1S | 24 | 0.940 | 0.959 | 0.922 | 0.980 | 0.051 | 0.246 | 0.752 | 20.000 | 0.250 |
| E1RAW@E1S | 40 | 0.951 | 0.959 | 0.942 | 0.988 | 0.043 | 0.185 | 0.762 | 18.000 | 0.417 |
| E1RAW@E1S | 60 | 0.958 | 0.964 | 0.951 | 0.992 | 0.032 | 0.127 | 0.780 | 18.000 | 0.417 |
| G3@E1S | 16 | 0.898 | 0.883 | 0.913 | 0.954 | 0.101 | 0.362 | 0.736 | 18.000 | 0.167 |
| G3@E1S | 24 | 0.916 | 0.914 | 0.919 | 0.969 | 0.081 | 0.300 | 0.735 | 19.000 | 0.000 |
| G3@E1S | 40 | 0.925 | 0.893 | 0.956 | 0.966 | 0.082 | 0.295 | 0.763 | 18.000 | 0.250 |
| G3@E1S | 60 | 0.951 | 0.939 | 0.962 | 0.990 | 0.038 | 0.156 | 0.772 | 17.000 | 0.250 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@E1S | 16 | 0.023 | 1.897 | 0.074 | 11 | 12 |
| ATSAPPROX@E1S | 24 | 0.030 | 1.616 | 0.052 | 12 | 12 |
| ATSAPPROX@E1S | 40 | 0.019 | 1.288 | 0.037 | 10 | 12 |
| ATSAPPROX@E1S | 60 | 0.017 | 1.394 | 0.040 | 11 | 12 |
| ATSCF@E1S | 16 | 0.034 | 1.845 | 0.072 | 11 | 12 |
| ATSCF@E1S | 24 | 0.027 | 1.648 | 0.054 | 11 | 12 |
| ATSCF@E1S | 40 | 0.020 | 1.329 | 0.042 | 9 | 12 |
| ATSCF@E1S | 60 | 0.018 | 1.551 | 0.038 | 11 | 12 |
| DEPTHCF@E1S | 16 | 0.041 | 2.701 | 0.131 | 6 | 12 |
| DEPTHCF@E1S | 24 | 0.014 | 2.589 | 0.117 | 7 | 12 |
| DEPTHCF@E1S | 40 | 0.019 | 1.773 | 0.060 | 6 | 12 |
| DEPTHCF@E1S | 60 | 0.016 | 2.008 | 0.057 | 6 | 12 |
| E1CAL@E1S | 16 | 0.031 | 0.758 | 0.036 | 9 | 12 |
| E1CAL@E1S | 24 | 0.030 | 0.949 | 0.036 | 8 | 12 |
| E1CAL@E1S | 40 | 0.018 | 0.854 | 0.020 | 6 | 12 |
| E1CAL@E1S | 60 | 0.022 | 1.349 | 0.029 | 7 | 12 |
| E1RAW@E1S | 16 | 0.037 | 0.459 | 0.048 | 9 | 12 |
| E1RAW@E1S | 24 | 0.041 | 0.505 | 0.047 | 9 | 12 |
| E1RAW@E1S | 40 | 0.021 | 0.486 | 0.036 | 7 | 12 |
| E1RAW@E1S | 60 | 0.022 | 0.704 | 0.033 | 7 | 12 |
| G3@E1S | 16 | 0.065 | 2.361 | 0.158 | 10 | 12 |
| G3@E1S | 24 | 0.053 | 2.235 | 0.124 | 12 | 12 |
| G3@E1S | 40 | 0.042 | 2.311 | 0.138 | 9 | 12 |
| G3@E1S | 60 | 0.023 | 1.775 | 0.062 | 9 | 12 |

## Matched-path decomposition on the paths of ATSCF_MARGIN (fresh repeats; every construction on the same paid prefixes)

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@ATSCF_MARGIN | 0.9331 | 0.9331 | 0.9331 | 0.1699 | 0.1699 | 0.1699 | 0.0465 | 0.0465 | 0.0465 | 0.9783 | 0.9783 | 0.9783 |
| ATSCF@ATSCF_MARGIN | 0.9377 | 0.9377 | 0.9377 | 0.1760 | 0.1760 | 0.1760 | 0.0474 | 0.0474 | 0.0474 | 0.9781 | 0.9781 | 0.9781 |
| DEPTHCF@ATSCF_MARGIN | 0.9191 | 0.9191 | 0.9191 | 0.2129 | 0.2129 | 0.2129 | 0.0585 | 0.0585 | 0.0585 | 0.9663 | 0.9663 | 0.9663 |
| E1CAL@ATSCF_MARGIN | 0.9266 | 0.9266 | 0.9266 | 0.2629 | 0.2629 | 0.2629 | 0.0647 | 0.0647 | 0.0647 | 0.9640 | 0.9640 | 0.9640 |
| E1RAW@ATSCF_MARGIN | 0.9306 | 0.9306 | 0.9306 | 0.2676 | 0.2676 | 0.2676 | 0.0551 | 0.0551 | 0.0551 | 0.9688 | 0.9688 | 0.9688 |
| G3@ATSCF_MARGIN | 0.8295 | 0.8295 | 0.8295 | 0.4473 | 0.4473 | 0.4473 | 0.1402 | 0.1402 | 0.1402 | 0.9023 | 0.9023 | 0.9023 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | BA_AULC | 0.0111 | – | 0.0111 | 0.0111 | 1/1 |
| ATSCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | LL_AULC | -0.0869 | – | -0.0869 | -0.0869 | 1/1 |
| ATSCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | Brier_AULC | -0.0173 | – | -0.0173 | -0.0173 | 1/1 |
| ATSCF@ATSCF_MARGIN − DEPTHCF@ATSCF_MARGIN | BA_AULC | 0.0187 | – | 0.0187 | 0.0187 | 1/1 |
| ATSCF@ATSCF_MARGIN − DEPTHCF@ATSCF_MARGIN | LL_AULC | -0.0369 | – | -0.0369 | -0.0369 | 1/1 |
| ATSCF@ATSCF_MARGIN − DEPTHCF@ATSCF_MARGIN | Brier_AULC | -0.0111 | – | -0.0111 | -0.0111 | 1/1 |
| DEPTHCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | BA_AULC | -0.0076 | – | -0.0076 | -0.0076 | 0/1 |
| DEPTHCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | LL_AULC | -0.0500 | – | -0.0500 | -0.0500 | 1/1 |
| DEPTHCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | Brier_AULC | -0.0062 | – | -0.0062 | -0.0062 | 1/1 |
| E1CAL@ATSCF_MARGIN − E1RAW@ATSCF_MARGIN | BA_AULC | -0.0040 | – | -0.0040 | -0.0040 | 0/1 |
| E1CAL@ATSCF_MARGIN − E1RAW@ATSCF_MARGIN | LL_AULC | -0.0047 | – | -0.0047 | -0.0047 | 1/1 |
| E1CAL@ATSCF_MARGIN − E1RAW@ATSCF_MARGIN | Brier_AULC | 0.0096 | – | 0.0096 | 0.0096 | 0/1 |
| ATSCF@ATSCF_MARGIN − ATSAPPROX@ATSCF_MARGIN | BA_AULC | 0.0047 | – | 0.0047 | 0.0047 | 1/1 |
| ATSCF@ATSCF_MARGIN − ATSAPPROX@ATSCF_MARGIN | LL_AULC | 0.0061 | – | 0.0061 | 0.0061 | 0/1 |
| ATSCF@ATSCF_MARGIN − ATSAPPROX@ATSCF_MARGIN | Brier_AULC | 0.0009 | – | 0.0009 | 0.0009 | 0/1 |
| ATSCF@ATSCF_MARGIN − G3@ATSCF_MARGIN | BA_AULC | 0.1082 | – | 0.1082 | 0.1082 | 1/1 |
| ATSCF@ATSCF_MARGIN − G3@ATSCF_MARGIN | LL_AULC | -0.2713 | – | -0.2713 | -0.2713 | 1/1 |
| ATSCF@ATSCF_MARGIN − G3@ATSCF_MARGIN | Brier_AULC | -0.0928 | – | -0.0928 | -0.0928 | 1/1 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@ATSCF_MARGIN | 1/1 | 28.00 | 32.00 | 32 |
| ATSCF@ATSCF_MARGIN | 1/1 | 20.00 | 24.00 | 24 |
| DEPTHCF@ATSCF_MARGIN | 1/1 | 24.00 | 28.00 | 28 |
| E1CAL@ATSCF_MARGIN | 1/1 | 24.00 | 28.00 | 28 |
| E1RAW@ATSCF_MARGIN | 1/1 | 24.00 | 28.00 | 28 |
| G3@ATSCF_MARGIN | 0/1 | – | – | – |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@ATSCF_MARGIN | 16 | 0.907 | 0.858 | 0.956 | 0.975 | 0.058 | 0.208 | 0.666 | 8.000 | 0.417 |
| ATSAPPROX@ATSCF_MARGIN | 24 | 0.926 | 0.893 | 0.959 | 0.986 | 0.044 | 0.161 | 0.710 | 11.000 | 0.500 |
| ATSAPPROX@ATSCF_MARGIN | 40 | 0.957 | 0.949 | 0.965 | 0.988 | 0.034 | 0.137 | 0.809 | 19.000 | 0.417 |
| ATSAPPROX@ATSCF_MARGIN | 60 | 0.961 | 0.954 | 0.968 | 0.990 | 0.031 | 0.120 | 0.818 | 19.000 | 0.417 |
| ATSCF@ATSCF_MARGIN | 16 | 0.911 | 0.863 | 0.959 | 0.975 | 0.058 | 0.209 | 0.665 | 9.000 | 0.333 |
| ATSCF@ATSCF_MARGIN | 24 | 0.934 | 0.904 | 0.965 | 0.985 | 0.045 | 0.172 | 0.746 | 11.000 | 0.500 |
| ATSCF@ATSCF_MARGIN | 40 | 0.962 | 0.959 | 0.965 | 0.988 | 0.035 | 0.141 | 0.817 | 20.000 | 0.417 |
| ATSCF@ATSCF_MARGIN | 60 | 0.964 | 0.959 | 0.968 | 0.990 | 0.031 | 0.121 | 0.827 | 19.000 | 0.417 |
| DEPTHCF@ATSCF_MARGIN | 16 | 0.892 | 0.853 | 0.930 | 0.966 | 0.075 | 0.267 | 0.620 | 7.000 | 0.500 |
| DEPTHCF@ATSCF_MARGIN | 24 | 0.936 | 0.904 | 0.968 | 0.986 | 0.050 | 0.190 | 0.747 | 11.000 | 0.583 |
| DEPTHCF@ATSCF_MARGIN | 40 | 0.952 | 0.939 | 0.965 | 0.988 | 0.038 | 0.156 | 0.782 | 14.000 | 0.417 |
| DEPTHCF@ATSCF_MARGIN | 60 | 0.961 | 0.954 | 0.968 | 0.989 | 0.033 | 0.129 | 0.818 | 17.000 | 0.417 |
| E1CAL@ATSCF_MARGIN | 16 | 0.892 | 0.848 | 0.936 | 0.940 | 0.085 | 0.337 | 0.629 | 8.000 | 0.500 |
| E1CAL@ATSCF_MARGIN | 24 | 0.938 | 0.914 | 0.962 | 0.968 | 0.058 | 0.227 | 0.746 | 13.000 | 0.417 |
| E1CAL@ATSCF_MARGIN | 40 | 0.950 | 0.934 | 0.965 | 0.980 | 0.048 | 0.198 | 0.773 | 13.000 | 0.417 |
| E1CAL@ATSCF_MARGIN | 60 | 0.952 | 0.934 | 0.971 | 0.980 | 0.052 | 0.222 | 0.791 | 15.000 | 0.417 |
| E1RAW@ATSCF_MARGIN | 16 | 0.896 | 0.868 | 0.924 | 0.950 | 0.078 | 0.398 | 0.646 | 9.000 | 0.500 |
| E1RAW@ATSCF_MARGIN | 24 | 0.940 | 0.924 | 0.956 | 0.981 | 0.046 | 0.194 | 0.745 | 14.000 | 0.417 |
| E1RAW@ATSCF_MARGIN | 40 | 0.957 | 0.949 | 0.965 | 0.977 | 0.040 | 0.190 | 0.800 | 16.000 | 0.417 |
| E1RAW@ATSCF_MARGIN | 60 | 0.960 | 0.954 | 0.965 | 0.980 | 0.037 | 0.177 | 0.809 | 17.000 | 0.417 |
| G3@ATSCF_MARGIN | 16 | 0.831 | 0.731 | 0.930 | 0.891 | 0.126 | 0.417 | 0.638 | 11.000 | 0.250 |
| G3@ATSCF_MARGIN | 24 | 0.815 | 0.782 | 0.849 | 0.869 | 0.150 | 0.473 | 0.592 | 9.000 | 0.500 |
| G3@ATSCF_MARGIN | 40 | 0.823 | 0.782 | 0.863 | 0.908 | 0.139 | 0.439 | 0.718 | 14.000 | 0.333 |
| G3@ATSCF_MARGIN | 60 | 0.899 | 0.873 | 0.924 | 0.955 | 0.118 | 0.398 | 0.709 | 16.000 | 0.083 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@ATSCF_MARGIN | 16 | 0.006 | 1.520 | 0.051 | 7 | 12 |
| ATSAPPROX@ATSCF_MARGIN | 24 | 0.022 | 1.470 | 0.043 | 6 | 12 |
| ATSAPPROX@ATSCF_MARGIN | 40 | 0.016 | 1.484 | 0.044 | 7 | 12 |
| ATSAPPROX@ATSCF_MARGIN | 60 | 0.007 | 1.168 | 0.019 | 7 | 12 |
| ATSCF@ATSCF_MARGIN | 16 | -0.002 | 1.543 | 0.056 | 8 | 12 |
| ATSCF@ATSCF_MARGIN | 24 | 0.024 | 1.632 | 0.059 | 6 | 12 |
| ATSCF@ATSCF_MARGIN | 40 | 0.017 | 1.590 | 0.055 | 7 | 12 |
| ATSCF@ATSCF_MARGIN | 60 | 0.009 | 1.245 | 0.025 | 7 | 12 |
| DEPTHCF@ATSCF_MARGIN | 16 | 0.022 | 1.812 | 0.086 | 6 | 12 |
| DEPTHCF@ATSCF_MARGIN | 24 | 0.024 | 2.055 | 0.077 | 5 | 12 |
| DEPTHCF@ATSCF_MARGIN | 40 | 0.027 | 1.871 | 0.068 | 7 | 12 |
| DEPTHCF@ATSCF_MARGIN | 60 | 0.016 | 1.377 | 0.037 | 7 | 12 |
| E1CAL@ATSCF_MARGIN | 16 | 0.018 | 0.589 | 0.080 | 6 | 12 |
| E1CAL@ATSCF_MARGIN | 24 | 0.024 | 1.153 | 0.064 | 7 | 12 |
| E1CAL@ATSCF_MARGIN | 40 | 0.059 | 1.575 | 0.079 | 7 | 12 |
| E1CAL@ATSCF_MARGIN | 60 | 0.066 | 2.003 | 0.120 | 7 | 12 |
| E1RAW@ATSCF_MARGIN | 16 | 0.006 | 0.350 | 0.068 | 6 | 12 |
| E1RAW@ATSCF_MARGIN | 24 | 0.009 | 0.553 | 0.032 | 7 | 12 |
| E1RAW@ATSCF_MARGIN | 40 | 0.026 | 0.648 | 0.033 | 7 | 12 |
| E1RAW@ATSCF_MARGIN | 60 | 0.019 | 0.621 | 0.027 | 7 | 12 |
| G3@ATSCF_MARGIN | 16 | 0.048 | 1.694 | 0.107 | 9 | 12 |
| G3@ATSCF_MARGIN | 24 | 0.091 | 1.821 | 0.146 | 6 | 12 |
| G3@ATSCF_MARGIN | 40 | 0.077 | 2.414 | 0.142 | 8 | 12 |
| G3@ATSCF_MARGIN | 60 | 0.069 | 3.364 | 0.195 | 11 | 12 |

## Matched-path decomposition on the paths of DEPTHCF_MARGIN (fresh repeats; every construction on the same paid prefixes)

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@DEPTHCF_MARGIN | 0.9356 | 0.9356 | 0.9356 | 0.1617 | 0.1617 | 0.1617 | 0.0451 | 0.0451 | 0.0451 | 0.9809 | 0.9809 | 0.9809 |
| ATSCF@DEPTHCF_MARGIN | 0.9336 | 0.9336 | 0.9336 | 0.1649 | 0.1649 | 0.1649 | 0.0461 | 0.0461 | 0.0461 | 0.9805 | 0.9805 | 0.9805 |
| DEPTHCF@DEPTHCF_MARGIN | 0.9263 | 0.9263 | 0.9263 | 0.1988 | 0.1988 | 0.1988 | 0.0555 | 0.0555 | 0.0555 | 0.9704 | 0.9704 | 0.9704 |
| E1CAL@DEPTHCF_MARGIN | 0.9322 | 0.9322 | 0.9322 | 0.2122 | 0.2122 | 0.2122 | 0.0526 | 0.0526 | 0.0526 | 0.9724 | 0.9724 | 0.9724 |
| E1RAW@DEPTHCF_MARGIN | 0.9392 | 0.9392 | 0.9392 | 0.2232 | 0.2232 | 0.2232 | 0.0501 | 0.0501 | 0.0501 | 0.9781 | 0.9781 | 0.9781 |
| G3@DEPTHCF_MARGIN | 0.9051 | 0.9051 | 0.9051 | 0.3149 | 0.3149 | 0.3149 | 0.0871 | 0.0871 | 0.0871 | 0.9552 | 0.9552 | 0.9552 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | BA_AULC | 0.0013 | – | 0.0013 | 0.0013 | 1/1 |
| ATSCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | LL_AULC | -0.0473 | – | -0.0473 | -0.0473 | 1/1 |
| ATSCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | Brier_AULC | -0.0066 | – | -0.0066 | -0.0066 | 1/1 |
| ATSCF@DEPTHCF_MARGIN − DEPTHCF@DEPTHCF_MARGIN | BA_AULC | 0.0073 | – | 0.0073 | 0.0073 | 1/1 |
| ATSCF@DEPTHCF_MARGIN − DEPTHCF@DEPTHCF_MARGIN | LL_AULC | -0.0340 | – | -0.0340 | -0.0340 | 1/1 |
| ATSCF@DEPTHCF_MARGIN − DEPTHCF@DEPTHCF_MARGIN | Brier_AULC | -0.0094 | – | -0.0094 | -0.0094 | 1/1 |
| DEPTHCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | BA_AULC | -0.0060 | – | -0.0060 | -0.0060 | 0/1 |
| DEPTHCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | LL_AULC | -0.0133 | – | -0.0133 | -0.0133 | 1/1 |
| DEPTHCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | Brier_AULC | 0.0029 | – | 0.0029 | 0.0029 | 0/1 |
| E1CAL@DEPTHCF_MARGIN − E1RAW@DEPTHCF_MARGIN | BA_AULC | -0.0070 | – | -0.0070 | -0.0070 | 0/1 |
| E1CAL@DEPTHCF_MARGIN − E1RAW@DEPTHCF_MARGIN | LL_AULC | -0.0111 | – | -0.0111 | -0.0111 | 1/1 |
| E1CAL@DEPTHCF_MARGIN − E1RAW@DEPTHCF_MARGIN | Brier_AULC | 0.0025 | – | 0.0025 | 0.0025 | 0/1 |
| ATSCF@DEPTHCF_MARGIN − ATSAPPROX@DEPTHCF_MARGIN | BA_AULC | -0.0020 | – | -0.0020 | -0.0020 | 0/1 |
| ATSCF@DEPTHCF_MARGIN − ATSAPPROX@DEPTHCF_MARGIN | LL_AULC | 0.0032 | – | 0.0032 | 0.0032 | 0/1 |
| ATSCF@DEPTHCF_MARGIN − ATSAPPROX@DEPTHCF_MARGIN | Brier_AULC | 0.0010 | – | 0.0010 | 0.0010 | 0/1 |
| ATSCF@DEPTHCF_MARGIN − G3@DEPTHCF_MARGIN | BA_AULC | 0.0285 | – | 0.0285 | 0.0285 | 1/1 |
| ATSCF@DEPTHCF_MARGIN − G3@DEPTHCF_MARGIN | LL_AULC | -0.1500 | – | -0.1500 | -0.1500 | 1/1 |
| ATSCF@DEPTHCF_MARGIN − G3@DEPTHCF_MARGIN | Brier_AULC | -0.0410 | – | -0.0410 | -0.0410 | 1/1 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@DEPTHCF_MARGIN | 1/1 | 20.00 | 24.00 | 24 |
| ATSCF@DEPTHCF_MARGIN | 1/1 | 24.00 | 28.00 | 28 |
| DEPTHCF@DEPTHCF_MARGIN | 1/1 | 28.00 | 32.00 | 32 |
| E1CAL@DEPTHCF_MARGIN | 1/1 | 28.00 | 32.00 | 32 |
| E1RAW@DEPTHCF_MARGIN | 1/1 | 16.00 | 20.00 | 20 |
| G3@DEPTHCF_MARGIN | 1/1 | 36.00 | 40.00 | 40 |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@DEPTHCF_MARGIN | 16 | 0.927 | 0.888 | 0.965 | 0.986 | 0.050 | 0.183 | 0.729 | 11.000 | 0.500 |
| ATSAPPROX@DEPTHCF_MARGIN | 24 | 0.943 | 0.924 | 0.962 | 0.989 | 0.040 | 0.151 | 0.764 | 17.000 | 0.333 |
| ATSAPPROX@DEPTHCF_MARGIN | 40 | 0.944 | 0.929 | 0.959 | 0.989 | 0.035 | 0.124 | 0.772 | 17.000 | 0.250 |
| ATSAPPROX@DEPTHCF_MARGIN | 60 | 0.958 | 0.954 | 0.962 | 0.989 | 0.032 | 0.121 | 0.817 | 19.000 | 0.333 |
| ATSCF@DEPTHCF_MARGIN | 16 | 0.924 | 0.883 | 0.965 | 0.986 | 0.051 | 0.187 | 0.729 | 11.000 | 0.583 |
| ATSCF@DEPTHCF_MARGIN | 24 | 0.939 | 0.919 | 0.959 | 0.990 | 0.040 | 0.150 | 0.755 | 16.000 | 0.250 |
| ATSCF@DEPTHCF_MARGIN | 40 | 0.947 | 0.934 | 0.959 | 0.990 | 0.036 | 0.126 | 0.781 | 18.000 | 0.250 |
| ATSCF@DEPTHCF_MARGIN | 60 | 0.949 | 0.939 | 0.959 | 0.989 | 0.032 | 0.120 | 0.781 | 17.000 | 0.250 |
| DEPTHCF@DEPTHCF_MARGIN | 16 | 0.922 | 0.888 | 0.956 | 0.981 | 0.066 | 0.251 | 0.719 | 11.000 | 0.583 |
| DEPTHCF@DEPTHCF_MARGIN | 24 | 0.930 | 0.904 | 0.956 | 0.983 | 0.051 | 0.194 | 0.728 | 11.000 | 0.500 |
| DEPTHCF@DEPTHCF_MARGIN | 40 | 0.948 | 0.934 | 0.962 | 0.989 | 0.038 | 0.141 | 0.791 | 15.000 | 0.417 |
| DEPTHCF@DEPTHCF_MARGIN | 60 | 0.960 | 0.949 | 0.971 | 0.991 | 0.031 | 0.117 | 0.818 | 17.000 | 0.500 |
| E1CAL@DEPTHCF_MARGIN | 16 | 0.927 | 0.904 | 0.951 | 0.972 | 0.050 | 0.208 | 0.719 | 13.000 | 0.417 |
| E1CAL@DEPTHCF_MARGIN | 24 | 0.923 | 0.883 | 0.962 | 0.976 | 0.048 | 0.179 | 0.729 | 7.000 | 0.500 |
| E1CAL@DEPTHCF_MARGIN | 40 | 0.951 | 0.939 | 0.962 | 0.986 | 0.038 | 0.146 | 0.800 | 16.000 | 0.500 |
| E1CAL@DEPTHCF_MARGIN | 60 | 0.959 | 0.944 | 0.974 | 0.991 | 0.036 | 0.147 | 0.818 | 16.000 | 0.500 |
| E1RAW@DEPTHCF_MARGIN | 16 | 0.941 | 0.934 | 0.948 | 0.978 | 0.049 | 0.215 | 0.772 | 17.000 | 0.417 |
| E1RAW@DEPTHCF_MARGIN | 24 | 0.939 | 0.934 | 0.945 | 0.982 | 0.047 | 0.178 | 0.745 | 14.000 | 0.333 |
| E1RAW@DEPTHCF_MARGIN | 40 | 0.950 | 0.944 | 0.956 | 0.988 | 0.038 | 0.151 | 0.800 | 17.000 | 0.500 |
| E1RAW@DEPTHCF_MARGIN | 60 | 0.963 | 0.954 | 0.971 | 0.991 | 0.033 | 0.131 | 0.827 | 17.000 | 0.500 |
| G3@DEPTHCF_MARGIN | 16 | 0.855 | 0.792 | 0.919 | 0.921 | 0.126 | 0.423 | 0.701 | 12.000 | 0.500 |
| G3@DEPTHCF_MARGIN | 24 | 0.918 | 0.914 | 0.922 | 0.962 | 0.087 | 0.326 | 0.689 | 15.000 | 0.083 |
| G3@DEPTHCF_MARGIN | 40 | 0.935 | 0.909 | 0.962 | 0.981 | 0.055 | 0.222 | 0.764 | 15.000 | 0.250 |
| G3@DEPTHCF_MARGIN | 60 | 0.928 | 0.893 | 0.962 | 0.978 | 0.067 | 0.257 | 0.746 | 16.000 | 0.250 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@DEPTHCF_MARGIN | 16 | -0.004 | 1.944 | 0.070 | 6 | 12 |
| ATSAPPROX@DEPTHCF_MARGIN | 24 | 0.013 | 1.599 | 0.042 | 8 | 12 |
| ATSAPPROX@DEPTHCF_MARGIN | 40 | 0.009 | 1.155 | 0.024 | 9 | 12 |
| ATSAPPROX@DEPTHCF_MARGIN | 60 | 0.008 | 1.074 | 0.014 | 8 | 12 |
| ATSCF@DEPTHCF_MARGIN | 16 | -0.009 | 1.962 | 0.074 | 5 | 12 |
| ATSCF@DEPTHCF_MARGIN | 24 | 0.010 | 1.571 | 0.044 | 9 | 12 |
| ATSCF@DEPTHCF_MARGIN | 40 | 0.011 | 1.244 | 0.031 | 9 | 12 |
| ATSCF@DEPTHCF_MARGIN | 60 | 0.008 | 1.215 | 0.028 | 9 | 12 |
| DEPTHCF@DEPTHCF_MARGIN | 16 | 0.008 | 2.488 | 0.113 | 5 | 12 |
| DEPTHCF@DEPTHCF_MARGIN | 24 | 0.020 | 1.897 | 0.079 | 6 | 12 |
| DEPTHCF@DEPTHCF_MARGIN | 40 | 0.018 | 1.510 | 0.040 | 7 | 12 |
| DEPTHCF@DEPTHCF_MARGIN | 60 | 0.011 | 1.364 | 0.028 | 6 | 12 |
| E1CAL@DEPTHCF_MARGIN | 16 | 0.004 | 0.740 | 0.020 | 7 | 12 |
| E1CAL@DEPTHCF_MARGIN | 24 | 0.014 | 1.039 | 0.040 | 6 | 12 |
| E1CAL@DEPTHCF_MARGIN | 40 | 0.021 | 1.015 | 0.029 | 6 | 12 |
| E1CAL@DEPTHCF_MARGIN | 60 | 0.036 | 1.585 | 0.055 | 6 | 12 |
| E1RAW@DEPTHCF_MARGIN | 16 | 0.009 | 0.553 | 0.031 | 7 | 12 |
| E1RAW@DEPTHCF_MARGIN | 24 | 0.029 | 0.742 | 0.038 | 8 | 12 |
| E1RAW@DEPTHCF_MARGIN | 40 | 0.018 | 0.669 | 0.019 | 6 | 12 |
| E1RAW@DEPTHCF_MARGIN | 60 | 0.016 | 0.767 | 0.020 | 6 | 12 |
| G3@DEPTHCF_MARGIN | 16 | 0.065 | 2.394 | 0.162 | 6 | 12 |
| G3@DEPTHCF_MARGIN | 24 | 0.064 | 2.384 | 0.163 | 11 | 12 |
| G3@DEPTHCF_MARGIN | 40 | 0.042 | 1.911 | 0.094 | 9 | 12 |
| G3@DEPTHCF_MARGIN | 60 | 0.039 | 2.319 | 0.124 | 9 | 12 |

## Matched-path decomposition on the paths of G3_MARGIN (fresh repeats; every construction on the same paid prefixes)

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@G3_MARGIN | 0.9330 | 0.9330 | 0.9330 | 0.1757 | 0.1757 | 0.1757 | 0.0475 | 0.0475 | 0.0475 | 0.9802 | 0.9802 | 0.9802 |
| ATSCF@G3_MARGIN | 0.9317 | 0.9317 | 0.9317 | 0.1830 | 0.1830 | 0.1830 | 0.0491 | 0.0491 | 0.0491 | 0.9791 | 0.9791 | 0.9791 |
| DEPTHCF@G3_MARGIN | 0.9157 | 0.9157 | 0.9157 | 0.2244 | 0.2244 | 0.2244 | 0.0599 | 0.0599 | 0.0599 | 0.9698 | 0.9698 | 0.9698 |
| E1CAL@G3_MARGIN | 0.9242 | 0.9242 | 0.9242 | 0.2040 | 0.2040 | 0.2040 | 0.0546 | 0.0546 | 0.0546 | 0.9742 | 0.9742 | 0.9742 |
| E1RAW@G3_MARGIN | 0.9333 | 0.9333 | 0.9333 | 0.2210 | 0.2210 | 0.2210 | 0.0522 | 0.0522 | 0.0522 | 0.9776 | 0.9776 | 0.9776 |
| G3@G3_MARGIN | 0.9258 | 0.9258 | 0.9258 | 0.2573 | 0.2573 | 0.2573 | 0.0694 | 0.0694 | 0.0694 | 0.9631 | 0.9631 | 0.9631 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@G3_MARGIN − E1CAL@G3_MARGIN | BA_AULC | 0.0075 | – | 0.0075 | 0.0075 | 1/1 |
| ATSCF@G3_MARGIN − E1CAL@G3_MARGIN | LL_AULC | -0.0211 | – | -0.0211 | -0.0211 | 1/1 |
| ATSCF@G3_MARGIN − E1CAL@G3_MARGIN | Brier_AULC | -0.0055 | – | -0.0055 | -0.0055 | 1/1 |
| ATSCF@G3_MARGIN − DEPTHCF@G3_MARGIN | BA_AULC | 0.0160 | – | 0.0160 | 0.0160 | 1/1 |
| ATSCF@G3_MARGIN − DEPTHCF@G3_MARGIN | LL_AULC | -0.0414 | – | -0.0414 | -0.0414 | 1/1 |
| ATSCF@G3_MARGIN − DEPTHCF@G3_MARGIN | Brier_AULC | -0.0108 | – | -0.0108 | -0.0108 | 1/1 |
| DEPTHCF@G3_MARGIN − E1CAL@G3_MARGIN | BA_AULC | -0.0085 | – | -0.0085 | -0.0085 | 0/1 |
| DEPTHCF@G3_MARGIN − E1CAL@G3_MARGIN | LL_AULC | 0.0203 | – | 0.0203 | 0.0203 | 0/1 |
| DEPTHCF@G3_MARGIN − E1CAL@G3_MARGIN | Brier_AULC | 0.0053 | – | 0.0053 | 0.0053 | 0/1 |
| E1CAL@G3_MARGIN − E1RAW@G3_MARGIN | BA_AULC | -0.0091 | – | -0.0091 | -0.0091 | 0/1 |
| E1CAL@G3_MARGIN − E1RAW@G3_MARGIN | LL_AULC | -0.0169 | – | -0.0169 | -0.0169 | 1/1 |
| E1CAL@G3_MARGIN − E1RAW@G3_MARGIN | Brier_AULC | 0.0024 | – | 0.0024 | 0.0024 | 0/1 |
| ATSCF@G3_MARGIN − ATSAPPROX@G3_MARGIN | BA_AULC | -0.0013 | – | -0.0013 | -0.0013 | 0/1 |
| ATSCF@G3_MARGIN − ATSAPPROX@G3_MARGIN | LL_AULC | 0.0073 | – | 0.0073 | 0.0073 | 0/1 |
| ATSCF@G3_MARGIN − ATSAPPROX@G3_MARGIN | Brier_AULC | 0.0016 | – | 0.0016 | 0.0016 | 0/1 |
| ATSCF@G3_MARGIN − G3@G3_MARGIN | BA_AULC | 0.0059 | – | 0.0059 | 0.0059 | 1/1 |
| ATSCF@G3_MARGIN − G3@G3_MARGIN | LL_AULC | -0.0744 | – | -0.0744 | -0.0744 | 1/1 |
| ATSCF@G3_MARGIN − G3@G3_MARGIN | Brier_AULC | -0.0203 | – | -0.0203 | -0.0203 | 1/1 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@G3_MARGIN | 1/1 | 16.00 | 28.00 | 28 |
| ATSCF@G3_MARGIN | 1/1 | 16.00 | 40.00 | 40 |
| DEPTHCF@G3_MARGIN | 1/1 | 36.00 | 40.00 | 40 |
| E1CAL@G3_MARGIN | 1/1 | 36.00 | 40.00 | 40 |
| E1RAW@G3_MARGIN | 1/1 | 16.00 | 28.00 | 28 |
| G3@G3_MARGIN | 1/1 | 28.00 | 32.00 | 32 |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@G3_MARGIN | 16 | 0.938 | 0.914 | 0.962 | 0.988 | 0.046 | 0.176 | 0.773 | 16.000 | 0.417 |
| ATSAPPROX@G3_MARGIN | 24 | 0.932 | 0.898 | 0.965 | 0.986 | 0.046 | 0.171 | 0.756 | 14.000 | 0.583 |
| ATSAPPROX@G3_MARGIN | 40 | 0.948 | 0.934 | 0.962 | 0.986 | 0.040 | 0.152 | 0.791 | 17.000 | 0.417 |
| ATSAPPROX@G3_MARGIN | 60 | 0.951 | 0.934 | 0.968 | 0.994 | 0.029 | 0.113 | 0.791 | 15.000 | 0.417 |
| ATSCF@G3_MARGIN | 16 | 0.938 | 0.909 | 0.968 | 0.987 | 0.047 | 0.178 | 0.783 | 16.000 | 0.583 |
| ATSCF@G3_MARGIN | 24 | 0.926 | 0.883 | 0.968 | 0.985 | 0.048 | 0.177 | 0.738 | 13.000 | 0.667 |
| ATSCF@G3_MARGIN | 40 | 0.948 | 0.934 | 0.962 | 0.985 | 0.042 | 0.161 | 0.791 | 17.000 | 0.417 |
| ATSCF@G3_MARGIN | 60 | 0.954 | 0.939 | 0.968 | 0.993 | 0.030 | 0.122 | 0.791 | 15.000 | 0.417 |
| DEPTHCF@G3_MARGIN | 16 | 0.917 | 0.858 | 0.977 | 0.985 | 0.062 | 0.240 | 0.739 | 9.000 | 0.583 |
| DEPTHCF@G3_MARGIN | 24 | 0.905 | 0.827 | 0.983 | 0.987 | 0.058 | 0.228 | 0.686 | 2.000 | 0.750 |
| DEPTHCF@G3_MARGIN | 40 | 0.942 | 0.914 | 0.971 | 0.987 | 0.046 | 0.184 | 0.792 | 13.000 | 0.667 |
| DEPTHCF@G3_MARGIN | 60 | 0.956 | 0.944 | 0.968 | 0.992 | 0.035 | 0.140 | 0.800 | 16.000 | 0.417 |
| E1CAL@G3_MARGIN | 16 | 0.922 | 0.878 | 0.965 | 0.975 | 0.058 | 0.202 | 0.738 | 13.000 | 0.333 |
| E1CAL@G3_MARGIN | 24 | 0.920 | 0.863 | 0.977 | 0.985 | 0.047 | 0.173 | 0.730 | 5.000 | 0.750 |
| E1CAL@G3_MARGIN | 40 | 0.942 | 0.919 | 0.965 | 0.988 | 0.038 | 0.143 | 0.765 | 12.000 | 0.583 |
| E1CAL@G3_MARGIN | 60 | 0.952 | 0.939 | 0.965 | 0.992 | 0.034 | 0.128 | 0.782 | 15.000 | 0.417 |
| E1RAW@G3_MARGIN | 16 | 0.931 | 0.924 | 0.939 | 0.983 | 0.050 | 0.194 | 0.736 | 16.000 | 0.333 |
| E1RAW@G3_MARGIN | 24 | 0.938 | 0.919 | 0.956 | 0.986 | 0.043 | 0.160 | 0.773 | 13.000 | 0.417 |
| E1RAW@G3_MARGIN | 40 | 0.954 | 0.954 | 0.953 | 0.987 | 0.037 | 0.157 | 0.809 | 18.000 | 0.417 |
| E1RAW@G3_MARGIN | 60 | 0.960 | 0.954 | 0.965 | 0.991 | 0.033 | 0.125 | 0.809 | 18.000 | 0.417 |
| G3@G3_MARGIN | 16 | 0.922 | 0.888 | 0.956 | 0.940 | 0.096 | 0.354 | 0.746 | 18.000 | 0.167 |
| G3@G3_MARGIN | 24 | 0.889 | 0.807 | 0.971 | 0.954 | 0.089 | 0.325 | 0.757 | 12.000 | 0.667 |
| G3@G3_MARGIN | 40 | 0.946 | 0.939 | 0.953 | 0.984 | 0.047 | 0.182 | 0.772 | 18.000 | 0.333 |
| G3@G3_MARGIN | 60 | 0.955 | 0.939 | 0.971 | 0.992 | 0.036 | 0.147 | 0.800 | 16.000 | 0.500 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@G3_MARGIN | 16 | 0.003 | 1.926 | 0.062 | 7 | 12 |
| ATSAPPROX@G3_MARGIN | 24 | -0.002 | 1.688 | 0.048 | 5 | 12 |
| ATSAPPROX@G3_MARGIN | 40 | 0.010 | 1.354 | 0.033 | 7 | 12 |
| ATSAPPROX@G3_MARGIN | 60 | 0.010 | 1.579 | 0.039 | 7 | 12 |
| ATSCF@G3_MARGIN | 16 | -0.001 | 1.942 | 0.067 | 5 | 12 |
| ATSCF@G3_MARGIN | 24 | -0.004 | 1.707 | 0.057 | 4 | 12 |
| ATSCF@G3_MARGIN | 40 | 0.009 | 1.465 | 0.044 | 7 | 12 |
| ATSCF@G3_MARGIN | 60 | 0.015 | 1.785 | 0.043 | 7 | 12 |
| DEPTHCF@G3_MARGIN | 16 | 0.002 | 2.748 | 0.114 | 5 | 12 |
| DEPTHCF@G3_MARGIN | 24 | -0.004 | 2.730 | 0.115 | 3 | 12 |
| DEPTHCF@G3_MARGIN | 40 | 0.013 | 1.967 | 0.074 | 4 | 12 |
| DEPTHCF@G3_MARGIN | 60 | 0.020 | 1.964 | 0.056 | 7 | 12 |
| E1CAL@G3_MARGIN | 16 | 0.010 | 1.338 | 0.046 | 8 | 12 |
| E1CAL@G3_MARGIN | 24 | 0.006 | 1.759 | 0.055 | 3 | 12 |
| E1CAL@G3_MARGIN | 40 | 0.023 | 1.402 | 0.043 | 5 | 12 |
| E1CAL@G3_MARGIN | 60 | 0.022 | 1.383 | 0.040 | 7 | 12 |
| E1RAW@G3_MARGIN | 16 | 0.022 | 0.562 | 0.036 | 8 | 12 |
| E1RAW@G3_MARGIN | 24 | 0.014 | 0.707 | 0.028 | 7 | 12 |
| E1RAW@G3_MARGIN | 40 | 0.018 | 0.607 | 0.022 | 7 | 12 |
| E1RAW@G3_MARGIN | 60 | 0.017 | 0.749 | 0.025 | 7 | 12 |
| G3@G3_MARGIN | 16 | 0.076 | 2.334 | 0.185 | 10 | 12 |
| G3@G3_MARGIN | 24 | 0.060 | 2.324 | 0.148 | 4 | 12 |
| G3@G3_MARGIN | 40 | 0.048 | 1.706 | 0.073 | 8 | 12 |
| G3@G3_MARGIN | 60 | 0.029 | 1.650 | 0.057 | 6 | 12 |

## Matched-path decomposition on the paths of ATSAPPROX_MARGIN (fresh repeats; every construction on the same paid prefixes)

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@ATSAPPROX_MARGIN | 0.9431 | 0.9431 | 0.9431 | 0.1472 | 0.1472 | 0.1472 | 0.0410 | 0.0410 | 0.0410 | 0.9832 | 0.9832 | 0.9832 |
| ATSCF@ATSAPPROX_MARGIN | 0.9441 | 0.9441 | 0.9441 | 0.1561 | 0.1561 | 0.1561 | 0.0426 | 0.0426 | 0.0426 | 0.9830 | 0.9830 | 0.9830 |
| DEPTHCF@ATSAPPROX_MARGIN | 0.9293 | 0.9293 | 0.9293 | 0.1933 | 0.1933 | 0.1933 | 0.0523 | 0.0523 | 0.0523 | 0.9740 | 0.9740 | 0.9740 |
| E1CAL@ATSAPPROX_MARGIN | 0.9341 | 0.9341 | 0.9341 | 0.2243 | 0.2243 | 0.2243 | 0.0556 | 0.0556 | 0.0556 | 0.9710 | 0.9710 | 0.9710 |
| E1RAW@ATSAPPROX_MARGIN | 0.9421 | 0.9421 | 0.9421 | 0.2195 | 0.2195 | 0.2195 | 0.0478 | 0.0478 | 0.0478 | 0.9746 | 0.9746 | 0.9746 |
| G3@ATSAPPROX_MARGIN | 0.8589 | 0.8589 | 0.8589 | 0.4042 | 0.4042 | 0.4042 | 0.1223 | 0.1223 | 0.1223 | 0.9166 | 0.9166 | 0.9166 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | BA_AULC | 0.0100 | – | 0.0100 | 0.0100 | 1/1 |
| ATSCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | LL_AULC | -0.0682 | – | -0.0682 | -0.0682 | 1/1 |
| ATSCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | Brier_AULC | -0.0130 | – | -0.0130 | -0.0130 | 1/1 |
| ATSCF@ATSAPPROX_MARGIN − DEPTHCF@ATSAPPROX_MARGIN | BA_AULC | 0.0148 | – | 0.0148 | 0.0148 | 1/1 |
| ATSCF@ATSAPPROX_MARGIN − DEPTHCF@ATSAPPROX_MARGIN | LL_AULC | -0.0372 | – | -0.0372 | -0.0372 | 1/1 |
| ATSCF@ATSAPPROX_MARGIN − DEPTHCF@ATSAPPROX_MARGIN | Brier_AULC | -0.0098 | – | -0.0098 | -0.0098 | 1/1 |
| DEPTHCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | BA_AULC | -0.0048 | – | -0.0048 | -0.0048 | 0/1 |
| DEPTHCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | LL_AULC | -0.0310 | – | -0.0310 | -0.0310 | 1/1 |
| DEPTHCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | Brier_AULC | -0.0032 | – | -0.0032 | -0.0032 | 1/1 |
| E1CAL@ATSAPPROX_MARGIN − E1RAW@ATSAPPROX_MARGIN | BA_AULC | -0.0080 | – | -0.0080 | -0.0080 | 0/1 |
| E1CAL@ATSAPPROX_MARGIN − E1RAW@ATSAPPROX_MARGIN | LL_AULC | 0.0048 | – | 0.0048 | 0.0048 | 0/1 |
| E1CAL@ATSAPPROX_MARGIN − E1RAW@ATSAPPROX_MARGIN | Brier_AULC | 0.0078 | – | 0.0078 | 0.0078 | 0/1 |
| ATSCF@ATSAPPROX_MARGIN − ATSAPPROX@ATSAPPROX_MARGIN | BA_AULC | 0.0010 | – | 0.0010 | 0.0010 | 1/1 |
| ATSCF@ATSAPPROX_MARGIN − ATSAPPROX@ATSAPPROX_MARGIN | LL_AULC | 0.0089 | – | 0.0089 | 0.0089 | 0/1 |
| ATSCF@ATSAPPROX_MARGIN − ATSAPPROX@ATSAPPROX_MARGIN | Brier_AULC | 0.0016 | – | 0.0016 | 0.0016 | 0/1 |
| ATSCF@ATSAPPROX_MARGIN − G3@ATSAPPROX_MARGIN | BA_AULC | 0.0851 | – | 0.0851 | 0.0851 | 1/1 |
| ATSCF@ATSAPPROX_MARGIN − G3@ATSAPPROX_MARGIN | LL_AULC | -0.2481 | – | -0.2481 | -0.2481 | 1/1 |
| ATSCF@ATSAPPROX_MARGIN − G3@ATSAPPROX_MARGIN | Brier_AULC | -0.0797 | – | -0.0797 | -0.0797 | 1/1 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@ATSAPPROX_MARGIN | 1/1 | 16.00 | 20.00 | 20 |
| ATSCF@ATSAPPROX_MARGIN | 1/1 | 16.00 | 20.00 | 20 |
| DEPTHCF@ATSAPPROX_MARGIN | 1/1 | 24.00 | 28.00 | 28 |
| E1CAL@ATSAPPROX_MARGIN | 1/1 | 16.00 | 28.00 | 28 |
| E1RAW@ATSAPPROX_MARGIN | 1/1 | 16.00 | 20.00 | 20 |
| G3@ATSAPPROX_MARGIN | 0/1 | – | – | – |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@ATSAPPROX_MARGIN | 16 | 0.940 | 0.929 | 0.951 | 0.987 | 0.044 | 0.162 | 0.781 | 19.000 | 0.250 |
| ATSAPPROX@ATSAPPROX_MARGIN | 24 | 0.957 | 0.949 | 0.965 | 0.991 | 0.036 | 0.135 | 0.827 | 20.000 | 0.333 |
| ATSAPPROX@ATSAPPROX_MARGIN | 40 | 0.958 | 0.944 | 0.971 | 0.993 | 0.029 | 0.106 | 0.809 | 16.000 | 0.333 |
| ATSAPPROX@ATSAPPROX_MARGIN | 60 | 0.963 | 0.954 | 0.971 | 0.994 | 0.027 | 0.100 | 0.827 | 18.000 | 0.417 |
| ATSCF@ATSAPPROX_MARGIN | 16 | 0.939 | 0.924 | 0.953 | 0.988 | 0.046 | 0.173 | 0.790 | 19.000 | 0.333 |
| ATSCF@ATSAPPROX_MARGIN | 24 | 0.958 | 0.944 | 0.971 | 0.991 | 0.038 | 0.154 | 0.827 | 18.000 | 0.417 |
| ATSCF@ATSAPPROX_MARGIN | 40 | 0.958 | 0.944 | 0.971 | 0.993 | 0.031 | 0.115 | 0.809 | 16.000 | 0.333 |
| ATSCF@ATSAPPROX_MARGIN | 60 | 0.963 | 0.954 | 0.971 | 0.993 | 0.027 | 0.103 | 0.827 | 18.000 | 0.417 |
| DEPTHCF@ATSAPPROX_MARGIN | 16 | 0.923 | 0.878 | 0.968 | 0.986 | 0.066 | 0.254 | 0.738 | 7.000 | 0.583 |
| DEPTHCF@ATSAPPROX_MARGIN | 24 | 0.938 | 0.898 | 0.977 | 0.992 | 0.045 | 0.189 | 0.784 | 9.000 | 0.750 |
| DEPTHCF@ATSAPPROX_MARGIN | 40 | 0.952 | 0.934 | 0.971 | 0.994 | 0.033 | 0.132 | 0.801 | 15.000 | 0.500 |
| DEPTHCF@ATSAPPROX_MARGIN | 60 | 0.963 | 0.954 | 0.971 | 0.994 | 0.027 | 0.106 | 0.827 | 17.000 | 0.500 |
| E1CAL@ATSAPPROX_MARGIN | 16 | 0.931 | 0.893 | 0.968 | 0.965 | 0.071 | 0.275 | 0.765 | 11.000 | 0.500 |
| E1CAL@ATSAPPROX_MARGIN | 24 | 0.931 | 0.893 | 0.968 | 0.981 | 0.043 | 0.187 | 0.747 | 8.000 | 0.667 |
| E1CAL@ATSAPPROX_MARGIN | 40 | 0.951 | 0.939 | 0.962 | 0.985 | 0.037 | 0.149 | 0.782 | 16.000 | 0.417 |
| E1CAL@ATSAPPROX_MARGIN | 60 | 0.954 | 0.934 | 0.974 | 0.984 | 0.042 | 0.181 | 0.801 | 15.000 | 0.417 |
| E1RAW@ATSAPPROX_MARGIN | 16 | 0.930 | 0.919 | 0.942 | 0.976 | 0.051 | 0.222 | 0.736 | 16.000 | 0.417 |
| E1RAW@ATSAPPROX_MARGIN | 24 | 0.952 | 0.954 | 0.951 | 0.980 | 0.041 | 0.192 | 0.790 | 17.000 | 0.500 |
| E1RAW@ATSAPPROX_MARGIN | 40 | 0.954 | 0.949 | 0.959 | 0.984 | 0.036 | 0.153 | 0.790 | 17.000 | 0.417 |
| E1RAW@ATSAPPROX_MARGIN | 60 | 0.959 | 0.949 | 0.968 | 0.985 | 0.031 | 0.143 | 0.818 | 17.000 | 0.417 |
| G3@ATSAPPROX_MARGIN | 16 | 0.864 | 0.858 | 0.869 | 0.921 | 0.123 | 0.417 | 0.708 | 17.000 | 0.083 |
| G3@ATSAPPROX_MARGIN | 24 | 0.809 | 0.761 | 0.858 | 0.902 | 0.129 | 0.420 | 0.710 | 15.000 | 0.500 |
| G3@ATSAPPROX_MARGIN | 40 | 0.756 | 0.731 | 0.782 | 0.804 | 0.186 | 0.550 | 0.664 | 11.000 | 0.333 |
| G3@ATSAPPROX_MARGIN | 60 | 0.918 | 0.883 | 0.953 | 0.974 | 0.068 | 0.257 | 0.746 | 16.000 | 0.500 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@ATSAPPROX_MARGIN | 16 | -0.002 | 1.619 | 0.049 | 9 | 12 |
| ATSAPPROX@ATSAPPROX_MARGIN | 24 | 0.013 | 1.490 | 0.038 | 8 | 12 |
| ATSAPPROX@ATSAPPROX_MARGIN | 40 | 0.007 | 1.315 | 0.023 | 8 | 12 |
| ATSAPPROX@ATSAPPROX_MARGIN | 60 | 0.008 | 1.194 | 0.029 | 7 | 12 |
| ATSCF@ATSAPPROX_MARGIN | 16 | -0.004 | 1.853 | 0.058 | 8 | 12 |
| ATSCF@ATSAPPROX_MARGIN | 24 | 0.015 | 1.857 | 0.064 | 7 | 12 |
| ATSCF@ATSAPPROX_MARGIN | 40 | 0.010 | 1.538 | 0.032 | 8 | 12 |
| ATSCF@ATSAPPROX_MARGIN | 60 | 0.008 | 1.243 | 0.023 | 7 | 12 |
| DEPTHCF@ATSAPPROX_MARGIN | 16 | 0.018 | 3.085 | 0.136 | 5 | 12 |
| DEPTHCF@ATSAPPROX_MARGIN | 24 | 0.024 | 2.613 | 0.100 | 3 | 12 |
| DEPTHCF@ATSAPPROX_MARGIN | 40 | 0.019 | 2.043 | 0.057 | 6 | 12 |
| DEPTHCF@ATSAPPROX_MARGIN | 60 | 0.015 | 1.551 | 0.040 | 6 | 12 |
| E1CAL@ATSAPPROX_MARGIN | 16 | 0.038 | 0.862 | 0.084 | 6 | 12 |
| E1CAL@ATSAPPROX_MARGIN | 24 | 0.027 | 1.347 | 0.059 | 4 | 12 |
| E1CAL@ATSAPPROX_MARGIN | 40 | 0.034 | 1.307 | 0.049 | 7 | 12 |
| E1CAL@ATSAPPROX_MARGIN | 60 | 0.057 | 1.797 | 0.087 | 7 | 12 |
| E1RAW@ATSAPPROX_MARGIN | 16 | 0.030 | 0.625 | 0.030 | 7 | 12 |
| E1RAW@ATSAPPROX_MARGIN | 24 | 0.034 | 0.671 | 0.039 | 6 | 12 |
| E1RAW@ATSAPPROX_MARGIN | 40 | 0.029 | 0.828 | 0.036 | 7 | 12 |
| E1RAW@ATSAPPROX_MARGIN | 60 | 0.024 | 0.797 | 0.026 | 7 | 12 |
| G3@ATSAPPROX_MARGIN | 16 | 0.089 | 2.292 | 0.180 | 11 | 12 |
| G3@ATSAPPROX_MARGIN | 24 | 0.072 | 1.797 | 0.112 | 6 | 12 |
| G3@ATSAPPROX_MARGIN | 40 | 0.093 | 1.714 | 0.123 | 8 | 12 |
| G3@ATSAPPROX_MARGIN | 60 | 0.052 | 2.132 | 0.111 | 6 | 12 |

