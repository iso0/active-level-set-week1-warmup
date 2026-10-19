# RC19B Keyhole — matched-path decomposition on the final paths (exploratory; same paid prefixes, recorded every 4 budgets)

## Matched-path decomposition on the paths of E1S (fresh repeats; every construction on the same paid prefixes)

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@E1S | 0.9410 | 0.9251 | 0.9480 | 0.1665 | 0.1549 | 0.1827 | 0.0447 | 0.0413 | 0.0496 | 0.9854 | 0.9811 | 0.9873 |
| ATSCF@E1S | 0.9310 | 0.9174 | 0.9457 | 0.1868 | 0.1767 | 0.2116 | 0.0512 | 0.0462 | 0.0585 | 0.9772 | 0.9648 | 0.9857 |
| DEPTHCF@E1S | 0.9196 | 0.8974 | 0.9337 | 0.2281 | 0.2130 | 0.2568 | 0.0622 | 0.0578 | 0.0719 | 0.9756 | 0.9637 | 0.9797 |
| E1CAL@E1S | 0.9273 | 0.9083 | 0.9383 | 0.2132 | 0.1946 | 0.2234 | 0.0552 | 0.0498 | 0.0600 | 0.9731 | 0.9649 | 0.9773 |
| E1RAW@E1S | 0.9350 | 0.9232 | 0.9407 | 0.2374 | 0.2134 | 0.2730 | 0.0528 | 0.0484 | 0.0569 | 0.9802 | 0.9737 | 0.9850 |
| G3@E1S | 0.9030 | 0.8822 | 0.9236 | 0.2926 | 0.2585 | 0.3211 | 0.0816 | 0.0702 | 0.0919 | 0.9584 | 0.9438 | 0.9713 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@E1S − E1CAL@E1S | BA_AULC | 0.0038 | 0.0038 | -0.0180 | 0.0162 | 6/8 |
| ATSCF@E1S − E1CAL@E1S | LL_AULC | -0.0263 | 0.0040 | -0.0413 | -0.0096 | 8/8 |
| ATSCF@E1S − E1CAL@E1S | Brier_AULC | -0.0040 | 0.0016 | -0.0112 | 0.0016 | 7/8 |
| ATSCF@E1S − DEPTHCF@E1S | BA_AULC | 0.0114 | 0.0048 | -0.0163 | 0.0260 | 7/8 |
| ATSCF@E1S − DEPTHCF@E1S | LL_AULC | -0.0412 | 0.0041 | -0.0561 | -0.0268 | 8/8 |
| ATSCF@E1S − DEPTHCF@E1S | Brier_AULC | -0.0110 | 0.0016 | -0.0174 | -0.0045 | 8/8 |
| DEPTHCF@E1S − E1CAL@E1S | BA_AULC | -0.0076 | 0.0033 | -0.0189 | 0.0069 | 2/8 |
| DEPTHCF@E1S − E1CAL@E1S | LL_AULC | 0.0149 | 0.0044 | -0.0033 | 0.0356 | 2/8 |
| DEPTHCF@E1S − E1CAL@E1S | Brier_AULC | 0.0070 | 0.0012 | 0.0008 | 0.0122 | 0/8 |
| E1CAL@E1S − E1RAW@E1S | BA_AULC | -0.0078 | 0.0020 | -0.0155 | -0.0002 | 0/8 |
| E1CAL@E1S − E1RAW@E1S | LL_AULC | -0.0242 | 0.0071 | -0.0580 | -0.0023 | 8/8 |
| E1CAL@E1S − E1RAW@E1S | Brier_AULC | 0.0024 | 0.0007 | -0.0011 | 0.0043 | 1/8 |
| ATSCF@E1S − ATSAPPROX@E1S | BA_AULC | -0.0099 | 0.0033 | -0.0290 | 0.0012 | 1/8 |
| ATSCF@E1S − ATSAPPROX@E1S | LL_AULC | 0.0203 | 0.0036 | 0.0061 | 0.0327 | 0/8 |
| ATSCF@E1S − ATSAPPROX@E1S | Brier_AULC | 0.0066 | 0.0014 | 0.0012 | 0.0123 | 0/8 |
| ATSCF@E1S − G3@E1S | BA_AULC | 0.0281 | 0.0054 | 0.0111 | 0.0569 | 8/8 |
| ATSCF@E1S − G3@E1S | LL_AULC | -0.1058 | 0.0074 | -0.1321 | -0.0745 | 8/8 |
| ATSCF@E1S − G3@E1S | Brier_AULC | -0.0304 | 0.0027 | -0.0388 | -0.0188 | 8/8 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@E1S | 8/8 | 17.00 | 23.50 | 20,24,36,16,28,20,24,20 |
| ATSCF@E1S | 8/8 | 19.00 | 25.00 | 20,24,36,16,28,20,36,20 |
| DEPTHCF@E1S | 8/8 | 28.50 | 36.00 | 20,36,40,28,48,28,56,32 |
| E1CAL@E1S | 8/8 | 22.00 | 29.00 | 20,32,44,32,36,20,28,20 |
| E1RAW@E1S | 8/8 | 22.50 | 26.50 | 20,32,40,24,24,20,32,20 |
| G3@E1S | 7/8 | 37.50 | 45.71 | 60,52,40,52,28,40,–,48 |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@E1S | 16 | 0.935 | 0.916 | 0.953 | 0.984 | 0.052 | 0.196 | 0.751 | 15.875 | 0.312 |
| ATSAPPROX@E1S | 24 | 0.942 | 0.927 | 0.957 | 0.987 | 0.043 | 0.163 | 0.762 | 16.500 | 0.260 |
| ATSAPPROX@E1S | 40 | 0.948 | 0.940 | 0.957 | 0.990 | 0.037 | 0.138 | 0.773 | 18.125 | 0.188 |
| ATSAPPROX@E1S | 60 | 0.955 | 0.949 | 0.961 | 0.991 | 0.033 | 0.124 | 0.794 | 18.375 | 0.292 |
| ATSCF@E1S | 16 | 0.931 | 0.912 | 0.949 | 0.980 | 0.057 | 0.216 | 0.745 | 16.500 | 0.219 |
| ATSCF@E1S | 24 | 0.939 | 0.921 | 0.957 | 0.987 | 0.045 | 0.174 | 0.753 | 15.875 | 0.260 |
| ATSCF@E1S | 40 | 0.947 | 0.936 | 0.959 | 0.990 | 0.038 | 0.145 | 0.773 | 18.000 | 0.167 |
| ATSCF@E1S | 60 | 0.952 | 0.944 | 0.960 | 0.991 | 0.035 | 0.133 | 0.785 | 18.250 | 0.229 |
| DEPTHCF@E1S | 16 | 0.890 | 0.822 | 0.958 | 0.974 | 0.084 | 0.302 | 0.707 | 8.125 | 0.698 |
| DEPTHCF@E1S | 24 | 0.919 | 0.865 | 0.972 | 0.985 | 0.059 | 0.230 | 0.718 | 8.000 | 0.677 |
| DEPTHCF@E1S | 40 | 0.938 | 0.908 | 0.968 | 0.989 | 0.046 | 0.177 | 0.770 | 12.375 | 0.656 |
| DEPTHCF@E1S | 60 | 0.947 | 0.929 | 0.964 | 0.991 | 0.037 | 0.144 | 0.775 | 13.500 | 0.500 |
| E1CAL@E1S | 16 | 0.902 | 0.882 | 0.922 | 0.964 | 0.073 | 0.282 | 0.706 | 13.000 | 0.479 |
| E1CAL@E1S | 24 | 0.932 | 0.916 | 0.949 | 0.975 | 0.055 | 0.216 | 0.745 | 14.000 | 0.552 |
| E1CAL@E1S | 40 | 0.943 | 0.930 | 0.956 | 0.985 | 0.042 | 0.154 | 0.761 | 14.750 | 0.479 |
| E1CAL@E1S | 60 | 0.947 | 0.937 | 0.957 | 0.988 | 0.036 | 0.137 | 0.769 | 15.125 | 0.417 |
| E1RAW@E1S | 16 | 0.914 | 0.926 | 0.901 | 0.967 | 0.071 | 0.346 | 0.709 | 15.875 | 0.385 |
| E1RAW@E1S | 24 | 0.938 | 0.949 | 0.928 | 0.981 | 0.052 | 0.229 | 0.750 | 17.375 | 0.427 |
| E1RAW@E1S | 40 | 0.949 | 0.952 | 0.945 | 0.989 | 0.040 | 0.160 | 0.763 | 17.250 | 0.354 |
| E1RAW@E1S | 60 | 0.952 | 0.951 | 0.954 | 0.990 | 0.036 | 0.154 | 0.781 | 17.250 | 0.396 |
| G3@E1S | 16 | 0.872 | 0.830 | 0.914 | 0.926 | 0.117 | 0.395 | 0.698 | 15.625 | 0.188 |
| G3@E1S | 24 | 0.885 | 0.845 | 0.926 | 0.954 | 0.091 | 0.325 | 0.708 | 16.000 | 0.219 |
| G3@E1S | 40 | 0.928 | 0.902 | 0.954 | 0.980 | 0.062 | 0.238 | 0.739 | 16.125 | 0.229 |
| G3@E1S | 60 | 0.943 | 0.926 | 0.960 | 0.986 | 0.046 | 0.183 | 0.768 | 17.375 | 0.302 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@E1S | 16 | 0.017 | 1.909 | 0.077 | 66 | 96 |
| ATSAPPROX@E1S | 24 | 0.014 | 1.607 | 0.053 | 71 | 96 |
| ATSAPPROX@E1S | 40 | 0.012 | 1.439 | 0.040 | 78 | 96 |
| ATSAPPROX@E1S | 60 | 0.009 | 1.300 | 0.030 | 68 | 96 |
| ATSCF@E1S | 16 | 0.028 | 1.885 | 0.084 | 75 | 96 |
| ATSCF@E1S | 24 | 0.015 | 1.721 | 0.060 | 71 | 96 |
| ATSCF@E1S | 40 | 0.013 | 1.526 | 0.044 | 80 | 96 |
| ATSCF@E1S | 60 | 0.010 | 1.437 | 0.036 | 74 | 96 |
| DEPTHCF@E1S | 16 | 0.022 | 2.942 | 0.144 | 29 | 96 |
| DEPTHCF@E1S | 24 | 0.007 | 2.638 | 0.113 | 31 | 96 |
| DEPTHCF@E1S | 40 | 0.009 | 2.194 | 0.077 | 33 | 96 |
| DEPTHCF@E1S | 60 | 0.013 | 1.799 | 0.053 | 48 | 96 |
| E1CAL@E1S | 16 | 0.032 | 0.816 | 0.070 | 50 | 96 |
| E1CAL@E1S | 24 | 0.014 | 1.047 | 0.048 | 43 | 96 |
| E1CAL@E1S | 40 | 0.009 | 1.225 | 0.037 | 50 | 96 |
| E1CAL@E1S | 60 | 0.012 | 1.225 | 0.033 | 56 | 96 |
| E1RAW@E1S | 16 | 0.040 | 0.472 | 0.062 | 59 | 96 |
| E1RAW@E1S | 24 | 0.029 | 0.551 | 0.043 | 55 | 96 |
| E1RAW@E1S | 40 | 0.016 | 0.575 | 0.031 | 62 | 96 |
| E1RAW@E1S | 60 | 0.011 | 0.571 | 0.028 | 58 | 96 |
| G3@E1S | 16 | 0.059 | 2.121 | 0.154 | 78 | 96 |
| G3@E1S | 24 | 0.037 | 2.091 | 0.122 | 75 | 96 |
| G3@E1S | 40 | 0.021 | 2.226 | 0.111 | 74 | 96 |
| G3@E1S | 60 | 0.014 | 1.862 | 0.074 | 67 | 96 |

## Matched-path decomposition on the paths of ATSCF_MARGIN (fresh repeats; every construction on the same paid prefixes)

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@ATSCF_MARGIN | 0.9402 | 0.9344 | 0.9471 | 0.1653 | 0.1445 | 0.1729 | 0.0444 | 0.0396 | 0.0468 | 0.9834 | 0.9798 | 0.9881 |
| ATSCF@ATSCF_MARGIN | 0.9293 | 0.9138 | 0.9404 | 0.1860 | 0.1685 | 0.2053 | 0.0515 | 0.0453 | 0.0575 | 0.9742 | 0.9600 | 0.9836 |
| DEPTHCF@ATSCF_MARGIN | 0.9259 | 0.9103 | 0.9312 | 0.2210 | 0.2020 | 0.2454 | 0.0607 | 0.0551 | 0.0699 | 0.9723 | 0.9598 | 0.9793 |
| E1CAL@ATSCF_MARGIN | 0.9314 | 0.9192 | 0.9375 | 0.2533 | 0.2204 | 0.2895 | 0.0659 | 0.0580 | 0.0741 | 0.9686 | 0.9634 | 0.9748 |
| E1RAW@ATSCF_MARGIN | 0.9355 | 0.9289 | 0.9401 | 0.2404 | 0.2265 | 0.2866 | 0.0541 | 0.0480 | 0.0616 | 0.9747 | 0.9730 | 0.9769 |
| G3@ATSCF_MARGIN | 0.8402 | 0.8138 | 0.8785 | 0.4445 | 0.4002 | 0.5004 | 0.1396 | 0.1221 | 0.1618 | 0.9014 | 0.8719 | 0.9279 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | BA_AULC | -0.0021 | 0.0037 | -0.0237 | 0.0045 | 6/8 |
| ATSCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | LL_AULC | -0.0673 | 0.0084 | -0.1086 | -0.0313 | 8/8 |
| ATSCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | Brier_AULC | -0.0144 | 0.0024 | -0.0243 | -0.0018 | 8/8 |
| ATSCF@ATSCF_MARGIN − DEPTHCF@ATSCF_MARGIN | BA_AULC | 0.0034 | 0.0033 | -0.0147 | 0.0113 | 6/8 |
| ATSCF@ATSCF_MARGIN − DEPTHCF@ATSCF_MARGIN | LL_AULC | -0.0350 | 0.0030 | -0.0471 | -0.0254 | 8/8 |
| ATSCF@ATSCF_MARGIN − DEPTHCF@ATSCF_MARGIN | Brier_AULC | -0.0092 | 0.0011 | -0.0140 | -0.0055 | 8/8 |
| DEPTHCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | BA_AULC | -0.0055 | 0.0011 | -0.0090 | -0.0001 | 0/8 |
| DEPTHCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | LL_AULC | -0.0323 | 0.0071 | -0.0615 | -0.0046 | 8/8 |
| DEPTHCF@ATSCF_MARGIN − E1CAL@ATSCF_MARGIN | Brier_AULC | -0.0052 | 0.0019 | -0.0124 | 0.0039 | 7/8 |
| E1CAL@ATSCF_MARGIN − E1RAW@ATSCF_MARGIN | BA_AULC | -0.0042 | 0.0018 | -0.0136 | 0.0022 | 1/8 |
| E1CAL@ATSCF_MARGIN − E1RAW@ATSCF_MARGIN | LL_AULC | 0.0129 | 0.0059 | -0.0095 | 0.0369 | 2/8 |
| E1CAL@ATSCF_MARGIN − E1RAW@ATSCF_MARGIN | Brier_AULC | 0.0118 | 0.0014 | 0.0057 | 0.0169 | 0/8 |
| ATSCF@ATSCF_MARGIN − ATSAPPROX@ATSCF_MARGIN | BA_AULC | -0.0109 | 0.0037 | -0.0285 | 0.0014 | 1/8 |
| ATSCF@ATSCF_MARGIN − ATSAPPROX@ATSCF_MARGIN | LL_AULC | 0.0208 | 0.0045 | 0.0057 | 0.0335 | 0/8 |
| ATSCF@ATSCF_MARGIN − ATSAPPROX@ATSCF_MARGIN | Brier_AULC | 0.0071 | 0.0017 | 0.0017 | 0.0131 | 0/8 |
| ATSCF@ATSCF_MARGIN − G3@ATSCF_MARGIN | BA_AULC | 0.0891 | 0.0074 | 0.0614 | 0.1156 | 8/8 |
| ATSCF@ATSCF_MARGIN − G3@ATSCF_MARGIN | LL_AULC | -0.2584 | 0.0140 | -0.3141 | -0.1995 | 8/8 |
| ATSCF@ATSCF_MARGIN − G3@ATSCF_MARGIN | Brier_AULC | -0.0881 | 0.0057 | -0.1101 | -0.0646 | 8/8 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@ATSCF_MARGIN | 8/8 | 17.00 | 23.00 | 16,24,24,24,28,24,16,28 |
| ATSCF@ATSCF_MARGIN | 8/8 | 19.00 | 25.50 | 28,24,24,24,24,24,20,36 |
| DEPTHCF@ATSCF_MARGIN | 8/8 | 24.00 | 30.00 | 32,28,28,44,28,24,28,28 |
| E1CAL@ATSCF_MARGIN | 8/8 | 21.00 | 28.00 | 16,28,36,24,32,28,28,32 |
| E1RAW@ATSCF_MARGIN | 8/8 | 20.50 | 25.50 | 28,28,20,24,28,24,20,32 |
| G3@ATSCF_MARGIN | 1/8 | 56.00 | 60.00 | –,–,–,–,–,–,60,– |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@ATSCF_MARGIN | 16 | 0.929 | 0.914 | 0.945 | 0.979 | 0.055 | 0.208 | 0.724 | 16.125 | 0.229 |
| ATSAPPROX@ATSCF_MARGIN | 24 | 0.944 | 0.933 | 0.956 | 0.986 | 0.041 | 0.158 | 0.762 | 17.625 | 0.240 |
| ATSAPPROX@ATSCF_MARGIN | 40 | 0.948 | 0.935 | 0.960 | 0.988 | 0.037 | 0.136 | 0.774 | 16.500 | 0.354 |
| ATSAPPROX@ATSCF_MARGIN | 60 | 0.952 | 0.942 | 0.962 | 0.989 | 0.034 | 0.125 | 0.784 | 17.125 | 0.375 |
| ATSCF@ATSCF_MARGIN | 16 | 0.914 | 0.892 | 0.937 | 0.965 | 0.067 | 0.244 | 0.705 | 16.125 | 0.167 |
| ATSCF@ATSCF_MARGIN | 24 | 0.944 | 0.934 | 0.955 | 0.986 | 0.043 | 0.166 | 0.761 | 18.000 | 0.219 |
| ATSCF@ATSCF_MARGIN | 40 | 0.948 | 0.937 | 0.959 | 0.987 | 0.038 | 0.140 | 0.774 | 16.625 | 0.344 |
| ATSCF@ATSCF_MARGIN | 60 | 0.952 | 0.944 | 0.960 | 0.989 | 0.035 | 0.129 | 0.780 | 17.500 | 0.354 |
| DEPTHCF@ATSCF_MARGIN | 16 | 0.909 | 0.893 | 0.926 | 0.968 | 0.088 | 0.312 | 0.707 | 12.125 | 0.542 |
| DEPTHCF@ATSCF_MARGIN | 24 | 0.937 | 0.916 | 0.958 | 0.984 | 0.055 | 0.217 | 0.750 | 14.000 | 0.510 |
| DEPTHCF@ATSCF_MARGIN | 40 | 0.948 | 0.936 | 0.961 | 0.987 | 0.041 | 0.158 | 0.775 | 15.750 | 0.469 |
| DEPTHCF@ATSCF_MARGIN | 60 | 0.948 | 0.936 | 0.960 | 0.987 | 0.036 | 0.137 | 0.771 | 15.875 | 0.458 |
| E1CAL@ATSCF_MARGIN | 16 | 0.921 | 0.907 | 0.934 | 0.963 | 0.078 | 0.282 | 0.730 | 14.000 | 0.448 |
| E1CAL@ATSCF_MARGIN | 24 | 0.939 | 0.918 | 0.960 | 0.975 | 0.062 | 0.236 | 0.768 | 15.625 | 0.490 |
| E1CAL@ATSCF_MARGIN | 40 | 0.947 | 0.935 | 0.960 | 0.977 | 0.053 | 0.210 | 0.771 | 15.375 | 0.396 |
| E1CAL@ATSCF_MARGIN | 60 | 0.950 | 0.936 | 0.963 | 0.980 | 0.053 | 0.213 | 0.782 | 15.375 | 0.469 |
| E1RAW@ATSCF_MARGIN | 16 | 0.918 | 0.930 | 0.907 | 0.968 | 0.069 | 0.298 | 0.719 | 16.000 | 0.344 |
| E1RAW@ATSCF_MARGIN | 24 | 0.943 | 0.943 | 0.943 | 0.977 | 0.050 | 0.228 | 0.757 | 16.875 | 0.375 |
| E1RAW@ATSCF_MARGIN | 40 | 0.951 | 0.944 | 0.957 | 0.980 | 0.042 | 0.179 | 0.775 | 16.500 | 0.385 |
| E1RAW@ATSCF_MARGIN | 60 | 0.951 | 0.942 | 0.960 | 0.981 | 0.039 | 0.170 | 0.780 | 16.125 | 0.458 |
| G3@ATSCF_MARGIN | 16 | 0.808 | 0.796 | 0.820 | 0.866 | 0.151 | 0.475 | 0.634 | 14.375 | 0.219 |
| G3@ATSCF_MARGIN | 24 | 0.833 | 0.783 | 0.882 | 0.901 | 0.139 | 0.445 | 0.682 | 14.500 | 0.302 |
| G3@ATSCF_MARGIN | 40 | 0.845 | 0.831 | 0.859 | 0.902 | 0.146 | 0.457 | 0.670 | 14.000 | 0.281 |
| G3@ATSCF_MARGIN | 60 | 0.895 | 0.865 | 0.924 | 0.947 | 0.105 | 0.354 | 0.717 | 16.125 | 0.302 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@ATSCF_MARGIN | 16 | 0.027 | 1.648 | 0.068 | 74 | 96 |
| ATSAPPROX@ATSCF_MARGIN | 24 | 0.018 | 1.455 | 0.047 | 73 | 96 |
| ATSAPPROX@ATSCF_MARGIN | 40 | 0.011 | 1.257 | 0.031 | 62 | 96 |
| ATSAPPROX@ATSCF_MARGIN | 60 | 0.007 | 1.075 | 0.021 | 60 | 96 |
| ATSCF@ATSCF_MARGIN | 16 | 0.027 | 1.671 | 0.079 | 80 | 96 |
| ATSCF@ATSCF_MARGIN | 24 | 0.021 | 1.554 | 0.053 | 75 | 96 |
| ATSCF@ATSCF_MARGIN | 40 | 0.012 | 1.339 | 0.036 | 63 | 96 |
| ATSCF@ATSCF_MARGIN | 60 | 0.010 | 1.158 | 0.024 | 62 | 96 |
| DEPTHCF@ATSCF_MARGIN | 16 | 0.056 | 2.629 | 0.143 | 44 | 96 |
| DEPTHCF@ATSCF_MARGIN | 24 | 0.038 | 2.322 | 0.104 | 47 | 96 |
| DEPTHCF@ATSCF_MARGIN | 40 | 0.024 | 1.751 | 0.059 | 51 | 96 |
| DEPTHCF@ATSCF_MARGIN | 60 | 0.017 | 1.329 | 0.036 | 52 | 96 |
| E1CAL@ATSCF_MARGIN | 16 | 0.060 | 1.503 | 0.104 | 53 | 96 |
| E1CAL@ATSCF_MARGIN | 24 | 0.051 | 1.572 | 0.092 | 49 | 96 |
| E1CAL@ATSCF_MARGIN | 40 | 0.056 | 1.611 | 0.086 | 58 | 96 |
| E1CAL@ATSCF_MARGIN | 60 | 0.063 | 1.832 | 0.101 | 51 | 96 |
| E1RAW@ATSCF_MARGIN | 16 | 0.056 | 0.548 | 0.063 | 63 | 96 |
| E1RAW@ATSCF_MARGIN | 24 | 0.042 | 0.645 | 0.046 | 60 | 96 |
| E1RAW@ATSCF_MARGIN | 40 | 0.028 | 0.713 | 0.037 | 59 | 96 |
| E1RAW@ATSCF_MARGIN | 60 | 0.020 | 0.679 | 0.030 | 52 | 96 |
| G3@ATSCF_MARGIN | 16 | 0.101 | 1.622 | 0.149 | 75 | 96 |
| G3@ATSCF_MARGIN | 24 | 0.087 | 2.164 | 0.156 | 67 | 96 |
| G3@ATSCF_MARGIN | 40 | 0.092 | 2.430 | 0.171 | 69 | 96 |
| G3@ATSCF_MARGIN | 60 | 0.069 | 2.405 | 0.152 | 67 | 96 |

## Matched-path decomposition on the paths of DEPTHCF_MARGIN (fresh repeats; every construction on the same paid prefixes)

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@DEPTHCF_MARGIN | 0.9406 | 0.9292 | 0.9490 | 0.1652 | 0.1539 | 0.1854 | 0.0443 | 0.0404 | 0.0511 | 0.9836 | 0.9774 | 0.9868 |
| ATSCF@DEPTHCF_MARGIN | 0.9318 | 0.9147 | 0.9429 | 0.1840 | 0.1642 | 0.2031 | 0.0503 | 0.0442 | 0.0568 | 0.9756 | 0.9600 | 0.9869 |
| DEPTHCF@DEPTHCF_MARGIN | 0.9269 | 0.9164 | 0.9340 | 0.2131 | 0.1991 | 0.2343 | 0.0580 | 0.0534 | 0.0648 | 0.9736 | 0.9649 | 0.9828 |
| E1CAL@DEPTHCF_MARGIN | 0.9290 | 0.9133 | 0.9419 | 0.2460 | 0.2147 | 0.2690 | 0.0626 | 0.0532 | 0.0710 | 0.9672 | 0.9564 | 0.9738 |
| E1RAW@DEPTHCF_MARGIN | 0.9348 | 0.9266 | 0.9428 | 0.2455 | 0.2063 | 0.2754 | 0.0534 | 0.0481 | 0.0603 | 0.9752 | 0.9701 | 0.9820 |
| G3@DEPTHCF_MARGIN | 0.8816 | 0.8619 | 0.9118 | 0.3604 | 0.3000 | 0.4186 | 0.1048 | 0.0816 | 0.1268 | 0.9386 | 0.9150 | 0.9592 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | BA_AULC | 0.0028 | 0.0028 | -0.0132 | 0.0106 | 6/8 |
| ATSCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | LL_AULC | -0.0620 | 0.0078 | -0.0988 | -0.0307 | 8/8 |
| ATSCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | Brier_AULC | -0.0123 | 0.0025 | -0.0234 | -0.0037 | 8/8 |
| ATSCF@DEPTHCF_MARGIN − DEPTHCF@DEPTHCF_MARGIN | BA_AULC | 0.0049 | 0.0026 | -0.0112 | 0.0116 | 7/8 |
| ATSCF@DEPTHCF_MARGIN − DEPTHCF@DEPTHCF_MARGIN | LL_AULC | -0.0291 | 0.0016 | -0.0349 | -0.0222 | 8/8 |
| ATSCF@DEPTHCF_MARGIN − DEPTHCF@DEPTHCF_MARGIN | Brier_AULC | -0.0077 | 0.0007 | -0.0098 | -0.0047 | 8/8 |
| DEPTHCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | BA_AULC | -0.0021 | 0.0012 | -0.0088 | 0.0030 | 1/8 |
| DEPTHCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | LL_AULC | -0.0329 | 0.0068 | -0.0639 | -0.0085 | 8/8 |
| DEPTHCF@DEPTHCF_MARGIN − E1CAL@DEPTHCF_MARGIN | Brier_AULC | -0.0046 | 0.0021 | -0.0142 | 0.0022 | 5/8 |
| E1CAL@DEPTHCF_MARGIN − E1RAW@DEPTHCF_MARGIN | BA_AULC | -0.0058 | 0.0018 | -0.0133 | 0.0012 | 1/8 |
| E1CAL@DEPTHCF_MARGIN − E1RAW@DEPTHCF_MARGIN | LL_AULC | 0.0005 | 0.0101 | -0.0482 | 0.0324 | 3/8 |
| E1CAL@DEPTHCF_MARGIN − E1RAW@DEPTHCF_MARGIN | Brier_AULC | 0.0092 | 0.0018 | 0.0018 | 0.0161 | 0/8 |
| ATSCF@DEPTHCF_MARGIN − ATSAPPROX@DEPTHCF_MARGIN | BA_AULC | -0.0088 | 0.0035 | -0.0297 | 0.0018 | 2/8 |
| ATSCF@DEPTHCF_MARGIN − ATSAPPROX@DEPTHCF_MARGIN | LL_AULC | 0.0188 | 0.0031 | 0.0033 | 0.0334 | 0/8 |
| ATSCF@DEPTHCF_MARGIN − ATSAPPROX@DEPTHCF_MARGIN | Brier_AULC | 0.0060 | 0.0014 | 0.0001 | 0.0127 | 0/8 |
| ATSCF@DEPTHCF_MARGIN − G3@DEPTHCF_MARGIN | BA_AULC | 0.0502 | 0.0062 | 0.0262 | 0.0811 | 8/8 |
| ATSCF@DEPTHCF_MARGIN − G3@DEPTHCF_MARGIN | LL_AULC | -0.1764 | 0.0134 | -0.2400 | -0.1265 | 8/8 |
| ATSCF@DEPTHCF_MARGIN − G3@DEPTHCF_MARGIN | Brier_AULC | -0.0545 | 0.0049 | -0.0791 | -0.0346 | 8/8 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@DEPTHCF_MARGIN | 8/8 | 16.00 | 21.00 | 16,16,32,16,24,16,24,24 |
| ATSCF@DEPTHCF_MARGIN | 8/8 | 17.00 | 23.00 | 28,16,32,20,24,16,24,24 |
| DEPTHCF@DEPTHCF_MARGIN | 8/8 | 21.50 | 28.50 | 32,24,40,16,32,24,28,32 |
| E1CAL@DEPTHCF_MARGIN | 8/8 | 18.50 | 28.00 | 36,20,36,24,24,24,28,32 |
| E1RAW@DEPTHCF_MARGIN | 8/8 | 19.50 | 25.50 | 32,20,36,20,28,20,24,24 |
| G3@DEPTHCF_MARGIN | 1/8 | 39.00 | 60.00 | –,–,–,–,–,60,–,– |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@DEPTHCF_MARGIN | 16 | 0.927 | 0.902 | 0.951 | 0.980 | 0.051 | 0.191 | 0.734 | 15.875 | 0.250 |
| ATSAPPROX@DEPTHCF_MARGIN | 24 | 0.939 | 0.921 | 0.957 | 0.985 | 0.044 | 0.164 | 0.752 | 15.250 | 0.281 |
| ATSAPPROX@DEPTHCF_MARGIN | 40 | 0.947 | 0.939 | 0.955 | 0.987 | 0.038 | 0.142 | 0.769 | 17.250 | 0.292 |
| ATSAPPROX@DEPTHCF_MARGIN | 60 | 0.954 | 0.945 | 0.964 | 0.988 | 0.034 | 0.130 | 0.793 | 17.625 | 0.365 |
| ATSCF@DEPTHCF_MARGIN | 16 | 0.929 | 0.905 | 0.953 | 0.979 | 0.053 | 0.202 | 0.740 | 16.125 | 0.229 |
| ATSCF@DEPTHCF_MARGIN | 24 | 0.939 | 0.921 | 0.956 | 0.984 | 0.046 | 0.174 | 0.750 | 15.625 | 0.281 |
| ATSCF@DEPTHCF_MARGIN | 40 | 0.947 | 0.937 | 0.957 | 0.986 | 0.039 | 0.148 | 0.767 | 17.250 | 0.271 |
| ATSCF@DEPTHCF_MARGIN | 60 | 0.954 | 0.944 | 0.964 | 0.988 | 0.035 | 0.135 | 0.793 | 17.625 | 0.344 |
| DEPTHCF@DEPTHCF_MARGIN | 16 | 0.908 | 0.871 | 0.945 | 0.975 | 0.072 | 0.269 | 0.686 | 10.875 | 0.531 |
| DEPTHCF@DEPTHCF_MARGIN | 24 | 0.931 | 0.911 | 0.950 | 0.982 | 0.055 | 0.212 | 0.733 | 12.375 | 0.542 |
| DEPTHCF@DEPTHCF_MARGIN | 40 | 0.942 | 0.934 | 0.951 | 0.985 | 0.042 | 0.164 | 0.751 | 15.250 | 0.427 |
| DEPTHCF@DEPTHCF_MARGIN | 60 | 0.946 | 0.928 | 0.965 | 0.986 | 0.037 | 0.143 | 0.771 | 14.625 | 0.490 |
| E1CAL@DEPTHCF_MARGIN | 16 | 0.911 | 0.876 | 0.945 | 0.960 | 0.071 | 0.280 | 0.699 | 12.750 | 0.458 |
| E1CAL@DEPTHCF_MARGIN | 24 | 0.927 | 0.897 | 0.956 | 0.969 | 0.057 | 0.224 | 0.738 | 13.000 | 0.500 |
| E1CAL@DEPTHCF_MARGIN | 40 | 0.942 | 0.928 | 0.956 | 0.974 | 0.053 | 0.209 | 0.755 | 14.625 | 0.469 |
| E1CAL@DEPTHCF_MARGIN | 60 | 0.948 | 0.929 | 0.968 | 0.980 | 0.049 | 0.200 | 0.786 | 14.500 | 0.479 |
| E1RAW@DEPTHCF_MARGIN | 16 | 0.921 | 0.919 | 0.922 | 0.970 | 0.065 | 0.292 | 0.707 | 15.750 | 0.365 |
| E1RAW@DEPTHCF_MARGIN | 24 | 0.936 | 0.927 | 0.945 | 0.974 | 0.052 | 0.236 | 0.745 | 14.750 | 0.458 |
| E1RAW@DEPTHCF_MARGIN | 40 | 0.945 | 0.938 | 0.951 | 0.979 | 0.045 | 0.199 | 0.759 | 15.875 | 0.448 |
| E1RAW@DEPTHCF_MARGIN | 60 | 0.951 | 0.940 | 0.962 | 0.983 | 0.039 | 0.168 | 0.785 | 16.375 | 0.469 |
| G3@DEPTHCF_MARGIN | 16 | 0.857 | 0.825 | 0.889 | 0.906 | 0.121 | 0.408 | 0.697 | 17.375 | 0.250 |
| G3@DEPTHCF_MARGIN | 24 | 0.874 | 0.827 | 0.920 | 0.926 | 0.113 | 0.382 | 0.686 | 15.500 | 0.302 |
| G3@DEPTHCF_MARGIN | 40 | 0.895 | 0.846 | 0.944 | 0.950 | 0.095 | 0.335 | 0.712 | 16.625 | 0.188 |
| G3@DEPTHCF_MARGIN | 60 | 0.921 | 0.885 | 0.957 | 0.974 | 0.073 | 0.270 | 0.744 | 16.375 | 0.271 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@DEPTHCF_MARGIN | 16 | 0.013 | 1.579 | 0.057 | 72 | 96 |
| ATSAPPROX@DEPTHCF_MARGIN | 24 | 0.017 | 1.493 | 0.047 | 69 | 96 |
| ATSAPPROX@DEPTHCF_MARGIN | 40 | 0.015 | 1.249 | 0.031 | 68 | 96 |
| ATSAPPROX@DEPTHCF_MARGIN | 60 | 0.008 | 1.183 | 0.028 | 61 | 96 |
| ATSCF@DEPTHCF_MARGIN | 16 | 0.015 | 1.636 | 0.062 | 74 | 96 |
| ATSCF@DEPTHCF_MARGIN | 24 | 0.016 | 1.556 | 0.054 | 69 | 96 |
| ATSCF@DEPTHCF_MARGIN | 40 | 0.016 | 1.344 | 0.037 | 70 | 96 |
| ATSCF@DEPTHCF_MARGIN | 60 | 0.010 | 1.273 | 0.031 | 63 | 96 |
| DEPTHCF@DEPTHCF_MARGIN | 16 | 0.030 | 2.403 | 0.117 | 45 | 96 |
| DEPTHCF@DEPTHCF_MARGIN | 24 | 0.035 | 2.081 | 0.089 | 44 | 96 |
| DEPTHCF@DEPTHCF_MARGIN | 40 | 0.031 | 1.573 | 0.054 | 55 | 96 |
| DEPTHCF@DEPTHCF_MARGIN | 60 | 0.014 | 1.338 | 0.035 | 49 | 96 |
| E1CAL@DEPTHCF_MARGIN | 16 | 0.041 | 1.074 | 0.073 | 52 | 96 |
| E1CAL@DEPTHCF_MARGIN | 24 | 0.031 | 1.161 | 0.060 | 48 | 96 |
| E1CAL@DEPTHCF_MARGIN | 40 | 0.045 | 1.338 | 0.069 | 51 | 96 |
| E1CAL@DEPTHCF_MARGIN | 60 | 0.049 | 1.739 | 0.086 | 50 | 96 |
| E1RAW@DEPTHCF_MARGIN | 16 | 0.043 | 0.527 | 0.056 | 61 | 96 |
| E1RAW@DEPTHCF_MARGIN | 24 | 0.026 | 0.551 | 0.038 | 52 | 96 |
| E1RAW@DEPTHCF_MARGIN | 40 | 0.023 | 0.573 | 0.034 | 53 | 96 |
| E1RAW@DEPTHCF_MARGIN | 60 | 0.013 | 0.637 | 0.023 | 51 | 96 |
| G3@DEPTHCF_MARGIN | 16 | 0.072 | 1.920 | 0.139 | 72 | 96 |
| G3@DEPTHCF_MARGIN | 24 | 0.062 | 2.059 | 0.140 | 67 | 96 |
| G3@DEPTHCF_MARGIN | 40 | 0.048 | 2.196 | 0.136 | 78 | 96 |
| G3@DEPTHCF_MARGIN | 60 | 0.040 | 2.324 | 0.125 | 70 | 96 |

## Matched-path decomposition on the paths of G3_MARGIN (fresh repeats; every construction on the same paid prefixes)

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@G3_MARGIN | 0.9374 | 0.9235 | 0.9456 | 0.1646 | 0.1523 | 0.1772 | 0.0452 | 0.0417 | 0.0498 | 0.9848 | 0.9802 | 0.9875 |
| ATSCF@G3_MARGIN | 0.9279 | 0.9150 | 0.9423 | 0.1820 | 0.1622 | 0.1930 | 0.0508 | 0.0435 | 0.0553 | 0.9774 | 0.9650 | 0.9873 |
| DEPTHCF@G3_MARGIN | 0.9255 | 0.9094 | 0.9349 | 0.2169 | 0.2035 | 0.2409 | 0.0589 | 0.0532 | 0.0668 | 0.9759 | 0.9632 | 0.9853 |
| E1CAL@G3_MARGIN | 0.9296 | 0.9152 | 0.9400 | 0.2177 | 0.1943 | 0.2409 | 0.0570 | 0.0507 | 0.0648 | 0.9733 | 0.9662 | 0.9789 |
| E1RAW@G3_MARGIN | 0.9337 | 0.9276 | 0.9392 | 0.2372 | 0.2205 | 0.2706 | 0.0542 | 0.0505 | 0.0617 | 0.9794 | 0.9763 | 0.9827 |
| G3@G3_MARGIN | 0.9209 | 0.8988 | 0.9361 | 0.2680 | 0.2431 | 0.2951 | 0.0724 | 0.0630 | 0.0816 | 0.9634 | 0.9498 | 0.9730 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@G3_MARGIN − E1CAL@G3_MARGIN | BA_AULC | -0.0017 | 0.0034 | -0.0208 | 0.0117 | 4/8 |
| ATSCF@G3_MARGIN − E1CAL@G3_MARGIN | LL_AULC | -0.0357 | 0.0058 | -0.0590 | -0.0106 | 8/8 |
| ATSCF@G3_MARGIN − E1CAL@G3_MARGIN | Brier_AULC | -0.0063 | 0.0017 | -0.0124 | 0.0025 | 7/8 |
| ATSCF@G3_MARGIN − DEPTHCF@G3_MARGIN | BA_AULC | 0.0024 | 0.0034 | -0.0144 | 0.0175 | 5/8 |
| ATSCF@G3_MARGIN − DEPTHCF@G3_MARGIN | LL_AULC | -0.0348 | 0.0031 | -0.0495 | -0.0194 | 8/8 |
| ATSCF@G3_MARGIN − DEPTHCF@G3_MARGIN | Brier_AULC | -0.0081 | 0.0013 | -0.0144 | -0.0017 | 8/8 |
| DEPTHCF@G3_MARGIN − E1CAL@G3_MARGIN | BA_AULC | -0.0040 | 0.0010 | -0.0078 | -0.0001 | 0/8 |
| DEPTHCF@G3_MARGIN − E1CAL@G3_MARGIN | LL_AULC | -0.0009 | 0.0054 | -0.0229 | 0.0213 | 4/8 |
| DEPTHCF@G3_MARGIN − E1CAL@G3_MARGIN | Brier_AULC | 0.0019 | 0.0015 | -0.0058 | 0.0086 | 2/8 |
| E1CAL@G3_MARGIN − E1RAW@G3_MARGIN | BA_AULC | -0.0041 | 0.0022 | -0.0159 | 0.0017 | 2/8 |
| E1CAL@G3_MARGIN − E1RAW@G3_MARGIN | LL_AULC | -0.0194 | 0.0065 | -0.0457 | 0.0080 | 6/8 |
| E1CAL@G3_MARGIN − E1RAW@G3_MARGIN | Brier_AULC | 0.0029 | 0.0016 | -0.0012 | 0.0103 | 3/8 |
| ATSCF@G3_MARGIN − ATSAPPROX@G3_MARGIN | BA_AULC | -0.0095 | 0.0034 | -0.0293 | 0.0012 | 1/8 |
| ATSCF@G3_MARGIN − ATSAPPROX@G3_MARGIN | LL_AULC | 0.0174 | 0.0033 | 0.0028 | 0.0325 | 0/8 |
| ATSCF@G3_MARGIN − ATSAPPROX@G3_MARGIN | Brier_AULC | 0.0056 | 0.0014 | 0.0002 | 0.0130 | 0/8 |
| ATSCF@G3_MARGIN − G3@G3_MARGIN | BA_AULC | 0.0070 | 0.0042 | -0.0064 | 0.0298 | 6/8 |
| ATSCF@G3_MARGIN − G3@G3_MARGIN | LL_AULC | -0.0860 | 0.0055 | -0.1191 | -0.0691 | 8/8 |
| ATSCF@G3_MARGIN − G3@G3_MARGIN | Brier_AULC | -0.0216 | 0.0020 | -0.0333 | -0.0152 | 8/8 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@G3_MARGIN | 8/8 | 21.50 | 25.50 | 16,20,36,32,24,24,20,32 |
| ATSCF@G3_MARGIN | 8/8 | 21.50 | 25.50 | 20,20,36,32,20,24,20,32 |
| DEPTHCF@G3_MARGIN | 8/8 | 25.50 | 35.50 | 28,36,40,36,48,32,28,36 |
| E1CAL@G3_MARGIN | 8/8 | 22.00 | 31.00 | 28,24,28,40,40,32,20,36 |
| E1RAW@G3_MARGIN | 8/8 | 22.50 | 30.50 | 32,32,32,32,32,24,32,28 |
| G3@G3_MARGIN | 8/8 | 28.00 | 35.00 | 52,28,44,40,24,24,28,40 |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@G3_MARGIN | 16 | 0.919 | 0.907 | 0.931 | 0.980 | 0.057 | 0.208 | 0.719 | 15.125 | 0.312 |
| ATSAPPROX@G3_MARGIN | 24 | 0.930 | 0.917 | 0.943 | 0.984 | 0.048 | 0.174 | 0.726 | 14.875 | 0.292 |
| ATSAPPROX@G3_MARGIN | 40 | 0.949 | 0.938 | 0.959 | 0.989 | 0.036 | 0.134 | 0.773 | 16.000 | 0.281 |
| ATSAPPROX@G3_MARGIN | 60 | 0.949 | 0.937 | 0.962 | 0.991 | 0.033 | 0.120 | 0.781 | 15.125 | 0.385 |
| ATSCF@G3_MARGIN | 16 | 0.919 | 0.900 | 0.938 | 0.980 | 0.059 | 0.218 | 0.724 | 15.375 | 0.302 |
| ATSCF@G3_MARGIN | 24 | 0.929 | 0.918 | 0.940 | 0.983 | 0.050 | 0.182 | 0.721 | 15.125 | 0.260 |
| ATSCF@G3_MARGIN | 40 | 0.948 | 0.935 | 0.961 | 0.989 | 0.037 | 0.140 | 0.773 | 15.750 | 0.302 |
| ATSCF@G3_MARGIN | 60 | 0.948 | 0.935 | 0.962 | 0.991 | 0.033 | 0.124 | 0.780 | 14.875 | 0.385 |
| DEPTHCF@G3_MARGIN | 16 | 0.913 | 0.888 | 0.937 | 0.980 | 0.073 | 0.274 | 0.710 | 9.875 | 0.573 |
| DEPTHCF@G3_MARGIN | 24 | 0.926 | 0.900 | 0.952 | 0.981 | 0.060 | 0.228 | 0.738 | 10.500 | 0.667 |
| DEPTHCF@G3_MARGIN | 40 | 0.943 | 0.921 | 0.965 | 0.988 | 0.043 | 0.168 | 0.770 | 12.250 | 0.573 |
| DEPTHCF@G3_MARGIN | 60 | 0.952 | 0.940 | 0.965 | 0.991 | 0.034 | 0.132 | 0.792 | 14.875 | 0.500 |
| E1CAL@G3_MARGIN | 16 | 0.922 | 0.914 | 0.929 | 0.972 | 0.066 | 0.249 | 0.717 | 13.500 | 0.406 |
| E1CAL@G3_MARGIN | 24 | 0.928 | 0.913 | 0.943 | 0.974 | 0.058 | 0.218 | 0.729 | 13.000 | 0.510 |
| E1CAL@G3_MARGIN | 40 | 0.946 | 0.929 | 0.963 | 0.981 | 0.047 | 0.182 | 0.781 | 14.000 | 0.542 |
| E1CAL@G3_MARGIN | 60 | 0.954 | 0.942 | 0.965 | 0.986 | 0.039 | 0.152 | 0.797 | 15.500 | 0.490 |
| E1RAW@G3_MARGIN | 16 | 0.919 | 0.941 | 0.898 | 0.977 | 0.067 | 0.284 | 0.707 | 16.000 | 0.281 |
| E1RAW@G3_MARGIN | 24 | 0.924 | 0.938 | 0.910 | 0.978 | 0.060 | 0.253 | 0.706 | 15.625 | 0.302 |
| E1RAW@G3_MARGIN | 40 | 0.948 | 0.945 | 0.951 | 0.984 | 0.042 | 0.178 | 0.766 | 16.500 | 0.396 |
| E1RAW@G3_MARGIN | 60 | 0.954 | 0.952 | 0.957 | 0.987 | 0.037 | 0.154 | 0.792 | 16.750 | 0.427 |
| G3@G3_MARGIN | 16 | 0.890 | 0.860 | 0.919 | 0.932 | 0.109 | 0.381 | 0.693 | 16.000 | 0.135 |
| G3@G3_MARGIN | 24 | 0.926 | 0.913 | 0.939 | 0.969 | 0.080 | 0.301 | 0.719 | 15.625 | 0.219 |
| G3@G3_MARGIN | 40 | 0.940 | 0.931 | 0.948 | 0.978 | 0.059 | 0.232 | 0.755 | 16.250 | 0.281 |
| G3@G3_MARGIN | 60 | 0.952 | 0.938 | 0.965 | 0.988 | 0.039 | 0.157 | 0.785 | 15.875 | 0.396 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@G3_MARGIN | 16 | 0.029 | 1.774 | 0.071 | 66 | 96 |
| ATSAPPROX@G3_MARGIN | 24 | 0.022 | 1.442 | 0.048 | 68 | 96 |
| ATSAPPROX@G3_MARGIN | 40 | 0.014 | 1.296 | 0.030 | 69 | 96 |
| ATSAPPROX@G3_MARGIN | 60 | 0.011 | 1.214 | 0.028 | 59 | 96 |
| ATSCF@G3_MARGIN | 16 | 0.028 | 1.972 | 0.082 | 67 | 96 |
| ATSCF@G3_MARGIN | 24 | 0.023 | 1.498 | 0.053 | 71 | 96 |
| ATSCF@G3_MARGIN | 40 | 0.016 | 1.421 | 0.036 | 67 | 96 |
| ATSCF@G3_MARGIN | 60 | 0.012 | 1.359 | 0.033 | 59 | 96 |
| DEPTHCF@G3_MARGIN | 16 | 0.042 | 2.685 | 0.130 | 41 | 96 |
| DEPTHCF@G3_MARGIN | 24 | 0.029 | 2.218 | 0.098 | 32 | 96 |
| DEPTHCF@G3_MARGIN | 40 | 0.021 | 1.916 | 0.068 | 41 | 96 |
| DEPTHCF@G3_MARGIN | 60 | 0.018 | 1.657 | 0.044 | 48 | 96 |
| E1CAL@G3_MARGIN | 16 | 0.053 | 1.263 | 0.073 | 57 | 96 |
| E1CAL@G3_MARGIN | 24 | 0.037 | 1.265 | 0.057 | 47 | 96 |
| E1CAL@G3_MARGIN | 40 | 0.028 | 1.453 | 0.061 | 44 | 96 |
| E1CAL@G3_MARGIN | 60 | 0.031 | 1.356 | 0.047 | 49 | 96 |
| E1RAW@G3_MARGIN | 16 | 0.059 | 0.531 | 0.064 | 69 | 96 |
| E1RAW@G3_MARGIN | 24 | 0.045 | 0.565 | 0.053 | 67 | 96 |
| E1RAW@G3_MARGIN | 40 | 0.027 | 0.648 | 0.032 | 58 | 96 |
| E1RAW@G3_MARGIN | 60 | 0.019 | 0.676 | 0.027 | 55 | 96 |
| G3@G3_MARGIN | 16 | 0.086 | 2.158 | 0.158 | 83 | 96 |
| G3@G3_MARGIN | 24 | 0.075 | 2.270 | 0.148 | 75 | 96 |
| G3@G3_MARGIN | 40 | 0.057 | 1.875 | 0.106 | 69 | 96 |
| G3@G3_MARGIN | 60 | 0.030 | 1.564 | 0.058 | 58 | 96 |

## Matched-path decomposition on the paths of ATSAPPROX_MARGIN (fresh repeats; every construction on the same paid prefixes)

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@ATSAPPROX_MARGIN | 0.9422 | 0.9357 | 0.9473 | 0.1609 | 0.1480 | 0.1719 | 0.0435 | 0.0403 | 0.0465 | 0.9852 | 0.9818 | 0.9869 |
| ATSCF@ATSAPPROX_MARGIN | 0.9313 | 0.9174 | 0.9419 | 0.1829 | 0.1720 | 0.1986 | 0.0503 | 0.0459 | 0.0560 | 0.9768 | 0.9657 | 0.9848 |
| DEPTHCF@ATSAPPROX_MARGIN | 0.9288 | 0.9205 | 0.9324 | 0.2256 | 0.1910 | 0.2421 | 0.0614 | 0.0520 | 0.0677 | 0.9746 | 0.9621 | 0.9788 |
| E1CAL@ATSAPPROX_MARGIN | 0.9301 | 0.9251 | 0.9363 | 0.2564 | 0.2099 | 0.2786 | 0.0670 | 0.0531 | 0.0747 | 0.9693 | 0.9612 | 0.9752 |
| E1RAW@ATSAPPROX_MARGIN | 0.9355 | 0.9316 | 0.9408 | 0.2305 | 0.2023 | 0.2519 | 0.0524 | 0.0487 | 0.0564 | 0.9770 | 0.9731 | 0.9804 |
| G3@ATSAPPROX_MARGIN | 0.8235 | 0.7803 | 0.8477 | 0.4739 | 0.4089 | 0.5593 | 0.1524 | 0.1261 | 0.1875 | 0.8826 | 0.8400 | 0.9184 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | BA_AULC | 0.0012 | 0.0023 | -0.0113 | 0.0079 | 5/8 |
| ATSCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | LL_AULC | -0.0734 | 0.0079 | -0.1013 | -0.0378 | 8/8 |
| ATSCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | Brier_AULC | -0.0166 | 0.0022 | -0.0237 | -0.0048 | 8/8 |
| ATSCF@ATSAPPROX_MARGIN − DEPTHCF@ATSAPPROX_MARGIN | BA_AULC | 0.0025 | 0.0028 | -0.0109 | 0.0131 | 5/8 |
| ATSCF@ATSAPPROX_MARGIN − DEPTHCF@ATSAPPROX_MARGIN | LL_AULC | -0.0426 | 0.0039 | -0.0574 | -0.0190 | 8/8 |
| ATSCF@ATSAPPROX_MARGIN − DEPTHCF@ATSAPPROX_MARGIN | Brier_AULC | -0.0110 | 0.0014 | -0.0167 | -0.0037 | 8/8 |
| DEPTHCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | BA_AULC | -0.0013 | 0.0013 | -0.0075 | 0.0032 | 3/8 |
| DEPTHCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | LL_AULC | -0.0308 | 0.0058 | -0.0555 | -0.0065 | 8/8 |
| DEPTHCF@ATSAPPROX_MARGIN − E1CAL@ATSAPPROX_MARGIN | Brier_AULC | -0.0056 | 0.0012 | -0.0106 | -0.0011 | 8/8 |
| E1CAL@ATSAPPROX_MARGIN − E1RAW@ATSAPPROX_MARGIN | BA_AULC | -0.0054 | 0.0018 | -0.0121 | 0.0031 | 2/8 |
| E1CAL@ATSAPPROX_MARGIN − E1RAW@ATSAPPROX_MARGIN | LL_AULC | 0.0259 | 0.0072 | -0.0139 | 0.0508 | 1/8 |
| E1CAL@ATSAPPROX_MARGIN − E1RAW@ATSAPPROX_MARGIN | Brier_AULC | 0.0146 | 0.0017 | 0.0045 | 0.0187 | 0/8 |
| ATSCF@ATSAPPROX_MARGIN − ATSAPPROX@ATSAPPROX_MARGIN | BA_AULC | -0.0109 | 0.0033 | -0.0299 | 0.0015 | 1/8 |
| ATSCF@ATSAPPROX_MARGIN − ATSAPPROX@ATSAPPROX_MARGIN | LL_AULC | 0.0220 | 0.0035 | 0.0051 | 0.0367 | 0/8 |
| ATSCF@ATSAPPROX_MARGIN − ATSAPPROX@ATSAPPROX_MARGIN | Brier_AULC | 0.0068 | 0.0014 | 0.0002 | 0.0136 | 0/8 |
| ATSCF@ATSAPPROX_MARGIN − G3@ATSAPPROX_MARGIN | BA_AULC | 0.1078 | 0.0071 | 0.0834 | 0.1371 | 8/8 |
| ATSCF@ATSAPPROX_MARGIN − G3@ATSAPPROX_MARGIN | LL_AULC | -0.2909 | 0.0153 | -0.3820 | -0.2368 | 8/8 |
| ATSCF@ATSAPPROX_MARGIN − G3@ATSAPPROX_MARGIN | Brier_AULC | -0.1021 | 0.0063 | -0.1386 | -0.0778 | 8/8 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@ATSAPPROX_MARGIN | 8/8 | 14.50 | 20.50 | 16,20,24,24,20,16,24,20 |
| ATSCF@ATSAPPROX_MARGIN | 8/8 | 16.50 | 21.50 | 20,28,24,24,20,16,16,24 |
| DEPTHCF@ATSAPPROX_MARGIN | 8/8 | 21.50 | 30.50 | 32,24,36,28,32,28,32,32 |
| E1CAL@ATSAPPROX_MARGIN | 8/8 | 19.50 | 26.00 | 28,24,24,24,24,28,28,28 |
| E1RAW@ATSAPPROX_MARGIN | 8/8 | 21.50 | 25.50 | 16,24,24,24,24,28,32,32 |
| G3@ATSAPPROX_MARGIN | 0/8 | 60.00 | – | –,–,–,–,–,–,–,– |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@ATSAPPROX_MARGIN | 16 | 0.936 | 0.930 | 0.943 | 0.983 | 0.051 | 0.191 | 0.736 | 17.000 | 0.198 |
| ATSAPPROX@ATSAPPROX_MARGIN | 24 | 0.944 | 0.938 | 0.951 | 0.988 | 0.042 | 0.158 | 0.763 | 16.875 | 0.312 |
| ATSAPPROX@ATSAPPROX_MARGIN | 40 | 0.950 | 0.944 | 0.957 | 0.989 | 0.036 | 0.134 | 0.780 | 17.500 | 0.292 |
| ATSAPPROX@ATSAPPROX_MARGIN | 60 | 0.951 | 0.942 | 0.960 | 0.990 | 0.034 | 0.123 | 0.779 | 16.625 | 0.333 |
| ATSCF@ATSAPPROX_MARGIN | 16 | 0.938 | 0.933 | 0.943 | 0.979 | 0.057 | 0.217 | 0.736 | 17.625 | 0.135 |
| ATSCF@ATSAPPROX_MARGIN | 24 | 0.944 | 0.937 | 0.951 | 0.987 | 0.045 | 0.171 | 0.764 | 16.875 | 0.302 |
| ATSCF@ATSAPPROX_MARGIN | 40 | 0.948 | 0.938 | 0.957 | 0.988 | 0.039 | 0.147 | 0.768 | 17.000 | 0.292 |
| ATSCF@ATSAPPROX_MARGIN | 60 | 0.950 | 0.940 | 0.960 | 0.989 | 0.035 | 0.128 | 0.778 | 16.625 | 0.312 |
| DEPTHCF@ATSAPPROX_MARGIN | 16 | 0.914 | 0.904 | 0.924 | 0.972 | 0.085 | 0.308 | 0.706 | 13.250 | 0.458 |
| DEPTHCF@ATSAPPROX_MARGIN | 24 | 0.935 | 0.926 | 0.945 | 0.984 | 0.059 | 0.228 | 0.757 | 15.250 | 0.479 |
| DEPTHCF@ATSAPPROX_MARGIN | 40 | 0.944 | 0.933 | 0.956 | 0.987 | 0.045 | 0.173 | 0.768 | 15.625 | 0.417 |
| DEPTHCF@ATSAPPROX_MARGIN | 60 | 0.951 | 0.944 | 0.959 | 0.988 | 0.037 | 0.141 | 0.782 | 17.000 | 0.438 |
| E1CAL@ATSAPPROX_MARGIN | 16 | 0.901 | 0.876 | 0.927 | 0.951 | 0.086 | 0.308 | 0.715 | 14.125 | 0.469 |
| E1CAL@ATSAPPROX_MARGIN | 24 | 0.942 | 0.938 | 0.946 | 0.976 | 0.064 | 0.238 | 0.769 | 16.250 | 0.427 |
| E1CAL@ATSAPPROX_MARGIN | 40 | 0.945 | 0.932 | 0.959 | 0.980 | 0.054 | 0.209 | 0.774 | 15.500 | 0.417 |
| E1CAL@ATSAPPROX_MARGIN | 60 | 0.950 | 0.939 | 0.962 | 0.980 | 0.054 | 0.217 | 0.785 | 16.000 | 0.458 |
| E1RAW@ATSAPPROX_MARGIN | 16 | 0.906 | 0.916 | 0.896 | 0.965 | 0.073 | 0.323 | 0.699 | 16.375 | 0.302 |
| E1RAW@ATSAPPROX_MARGIN | 24 | 0.940 | 0.945 | 0.936 | 0.980 | 0.050 | 0.213 | 0.756 | 16.750 | 0.396 |
| E1RAW@ATSAPPROX_MARGIN | 40 | 0.948 | 0.944 | 0.952 | 0.982 | 0.042 | 0.178 | 0.773 | 17.000 | 0.396 |
| E1RAW@ATSAPPROX_MARGIN | 60 | 0.952 | 0.944 | 0.959 | 0.983 | 0.039 | 0.166 | 0.785 | 16.750 | 0.458 |
| G3@ATSAPPROX_MARGIN | 16 | 0.815 | 0.790 | 0.840 | 0.878 | 0.152 | 0.477 | 0.625 | 14.000 | 0.167 |
| G3@ATSAPPROX_MARGIN | 24 | 0.792 | 0.763 | 0.820 | 0.855 | 0.164 | 0.503 | 0.658 | 12.125 | 0.427 |
| G3@ATSAPPROX_MARGIN | 40 | 0.842 | 0.806 | 0.878 | 0.888 | 0.163 | 0.498 | 0.686 | 15.000 | 0.208 |
| G3@ATSAPPROX_MARGIN | 60 | 0.891 | 0.848 | 0.934 | 0.946 | 0.109 | 0.362 | 0.725 | 15.875 | 0.281 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@ATSAPPROX_MARGIN | 16 | 0.030 | 1.631 | 0.062 | 77 | 96 |
| ATSAPPROX@ATSAPPROX_MARGIN | 24 | 0.025 | 1.490 | 0.048 | 66 | 96 |
| ATSAPPROX@ATSAPPROX_MARGIN | 40 | 0.015 | 1.272 | 0.032 | 68 | 96 |
| ATSAPPROX@ATSAPPROX_MARGIN | 60 | 0.009 | 1.095 | 0.023 | 64 | 96 |
| ATSCF@ATSAPPROX_MARGIN | 16 | 0.037 | 1.738 | 0.081 | 83 | 96 |
| ATSCF@ATSAPPROX_MARGIN | 24 | 0.029 | 1.625 | 0.060 | 67 | 96 |
| ATSCF@ATSAPPROX_MARGIN | 40 | 0.020 | 1.457 | 0.043 | 68 | 96 |
| ATSCF@ATSAPPROX_MARGIN | 60 | 0.012 | 1.232 | 0.028 | 66 | 96 |
| DEPTHCF@ATSAPPROX_MARGIN | 16 | 0.063 | 2.723 | 0.149 | 52 | 96 |
| DEPTHCF@ATSAPPROX_MARGIN | 24 | 0.046 | 2.420 | 0.108 | 50 | 96 |
| DEPTHCF@ATSAPPROX_MARGIN | 40 | 0.034 | 1.924 | 0.072 | 56 | 96 |
| DEPTHCF@ATSAPPROX_MARGIN | 60 | 0.022 | 1.496 | 0.042 | 54 | 96 |
| E1CAL@ATSAPPROX_MARGIN | 16 | 0.069 | 1.332 | 0.099 | 51 | 96 |
| E1CAL@ATSAPPROX_MARGIN | 24 | 0.064 | 1.636 | 0.098 | 55 | 96 |
| E1CAL@ATSAPPROX_MARGIN | 40 | 0.060 | 1.686 | 0.087 | 56 | 96 |
| E1CAL@ATSAPPROX_MARGIN | 60 | 0.068 | 1.896 | 0.106 | 52 | 96 |
| E1RAW@ATSAPPROX_MARGIN | 16 | 0.057 | 0.534 | 0.069 | 67 | 96 |
| E1RAW@ATSAPPROX_MARGIN | 24 | 0.040 | 0.631 | 0.041 | 58 | 96 |
| E1RAW@ATSAPPROX_MARGIN | 40 | 0.030 | 0.723 | 0.035 | 58 | 96 |
| E1RAW@ATSAPPROX_MARGIN | 60 | 0.026 | 0.715 | 0.030 | 52 | 96 |
| G3@ATSAPPROX_MARGIN | 16 | 0.092 | 1.962 | 0.147 | 80 | 96 |
| G3@ATSAPPROX_MARGIN | 24 | 0.085 | 1.999 | 0.138 | 55 | 96 |
| G3@ATSAPPROX_MARGIN | 40 | 0.090 | 3.109 | 0.203 | 76 | 96 |
| G3@ATSAPPROX_MARGIN | 60 | 0.073 | 2.366 | 0.158 | 69 | 96 |

