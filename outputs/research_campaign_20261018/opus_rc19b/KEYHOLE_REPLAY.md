# RC19B Keyhole — matched-path replay (DEVELOPMENT on RC19 final repeats 3–10; every construction on the same paid prefixes)

## Paths of E1_STRADDLE

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@E1_STRADDLE | 0.9394 | 0.9336 | 0.9468 | 0.1680 | 0.1554 | 0.1840 | 0.0455 | 0.0422 | 0.0500 | 0.9844 | 0.9820 | 0.9873 |
| ATSCF@E1_STRADDLE | 0.9261 | 0.9149 | 0.9349 | 0.1927 | 0.1739 | 0.2055 | 0.0539 | 0.0485 | 0.0596 | 0.9746 | 0.9653 | 0.9809 |
| DEPTHCF@E1_STRADDLE | 0.9130 | 0.9005 | 0.9252 | 0.2306 | 0.2127 | 0.2739 | 0.0632 | 0.0588 | 0.0756 | 0.9740 | 0.9560 | 0.9827 |
| E1CAL@E1_STRADDLE | 0.9220 | 0.9083 | 0.9374 | 0.2241 | 0.1871 | 0.2614 | 0.0585 | 0.0494 | 0.0703 | 0.9683 | 0.9611 | 0.9787 |
| E1RAW@E1_STRADDLE | 0.9353 | 0.9205 | 0.9433 | 0.2539 | 0.2070 | 0.3631 | 0.0532 | 0.0456 | 0.0707 | 0.9776 | 0.9682 | 0.9818 |
| G3@E1_STRADDLE | 0.9058 | 0.8851 | 0.9264 | 0.2851 | 0.2517 | 0.3058 | 0.0792 | 0.0677 | 0.0867 | 0.9583 | 0.9472 | 0.9681 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@E1_STRADDLE − E1CAL@E1_STRADDLE | BA_AULC | 0.0041 | 0.0042 | -0.0115 | 0.0214 | 4/8 |
| ATSCF@E1_STRADDLE − E1CAL@E1_STRADDLE | LL_AULC | -0.0314 | 0.0066 | -0.0589 | -0.0014 | 8/8 |
| ATSCF@E1_STRADDLE − E1CAL@E1_STRADDLE | Brier_AULC | -0.0046 | 0.0020 | -0.0147 | 0.0009 | 6/8 |
| ATSCF@E1_STRADDLE − DEPTHCF@E1_STRADDLE | BA_AULC | 0.0130 | 0.0031 | -0.0018 | 0.0227 | 7/8 |
| ATSCF@E1_STRADDLE − DEPTHCF@E1_STRADDLE | LL_AULC | -0.0379 | 0.0064 | -0.0714 | -0.0149 | 8/8 |
| ATSCF@E1_STRADDLE − DEPTHCF@E1_STRADDLE | Brier_AULC | -0.0093 | 0.0020 | -0.0200 | -0.0013 | 8/8 |
| DEPTHCF@E1_STRADDLE − E1CAL@E1_STRADDLE | BA_AULC | -0.0090 | 0.0049 | -0.0286 | 0.0118 | 2/8 |
| DEPTHCF@E1_STRADDLE − E1CAL@E1_STRADDLE | LL_AULC | 0.0065 | 0.0083 | -0.0177 | 0.0470 | 4/8 |
| DEPTHCF@E1_STRADDLE − E1CAL@E1_STRADDLE | Brier_AULC | 0.0047 | 0.0022 | -0.0026 | 0.0126 | 3/8 |
| E1CAL@E1_STRADDLE − E1RAW@E1_STRADDLE | BA_AULC | -0.0132 | 0.0035 | -0.0313 | -0.0052 | 0/8 |
| E1CAL@E1_STRADDLE − E1RAW@E1_STRADDLE | LL_AULC | -0.0298 | 0.0121 | -0.1017 | 0.0091 | 7/8 |
| E1CAL@E1_STRADDLE − E1RAW@E1_STRADDLE | Brier_AULC | 0.0053 | 0.0017 | -0.0005 | 0.0139 | 1/8 |
| ATSCF@E1_STRADDLE − ATSAPPROX@E1_STRADDLE | BA_AULC | -0.0133 | 0.0031 | -0.0271 | -0.0022 | 0/8 |
| ATSCF@E1_STRADDLE − ATSAPPROX@E1_STRADDLE | LL_AULC | 0.0247 | 0.0033 | 0.0108 | 0.0376 | 0/8 |
| ATSCF@E1_STRADDLE − ATSAPPROX@E1_STRADDLE | Brier_AULC | 0.0084 | 0.0014 | 0.0027 | 0.0148 | 0/8 |
| ATSCF@E1_STRADDLE − G3@E1_STRADDLE | BA_AULC | 0.0203 | 0.0048 | -0.0029 | 0.0389 | 7/8 |
| ATSCF@E1_STRADDLE − G3@E1_STRADDLE | LL_AULC | -0.0924 | 0.0058 | -0.1150 | -0.0623 | 8/8 |
| ATSCF@E1_STRADDLE − G3@E1_STRADDLE | Brier_AULC | -0.0252 | 0.0023 | -0.0355 | -0.0145 | 8/8 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@E1_STRADDLE | 8/8 | 17.50 | 24.50 | 24,28,24,24,32,24,20,20 |
| ATSCF@E1_STRADDLE | 8/8 | 20.00 | 25.50 | 24,32,24,24,28,24,24,24 |
| DEPTHCF@E1_STRADDLE | 8/8 | 27.50 | 33.00 | 28,32,40,44,40,28,28,24 |
| E1CAL@E1_STRADDLE | 8/8 | 26.00 | 30.00 | 28,36,32,36,24,28,32,24 |
| E1RAW@E1_STRADDLE | 8/8 | 23.00 | 27.00 | 24,36,32,32,24,24,20,24 |
| G3@E1_STRADDLE | 8/8 | 40.50 | 49.50 | 48,48,52,52,48,44,48,56 |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@E1_STRADDLE | 16 | 0.926 | 0.899 | 0.954 | 0.982 | 0.053 | 0.201 | 0.727 | 15.250 | 0.302 |
| ATSAPPROX@E1_STRADDLE | 24 | 0.942 | 0.928 | 0.956 | 0.986 | 0.044 | 0.165 | 0.760 | 17.500 | 0.177 |
| ATSAPPROX@E1_STRADDLE | 40 | 0.949 | 0.938 | 0.960 | 0.989 | 0.038 | 0.140 | 0.773 | 17.875 | 0.177 |
| ATSAPPROX@E1_STRADDLE | 60 | 0.953 | 0.949 | 0.957 | 0.990 | 0.035 | 0.126 | 0.778 | 18.625 | 0.219 |
| ATSCF@E1_STRADDLE | 16 | 0.909 | 0.865 | 0.953 | 0.976 | 0.063 | 0.231 | 0.709 | 13.875 | 0.354 |
| ATSCF@E1_STRADDLE | 24 | 0.937 | 0.918 | 0.956 | 0.985 | 0.046 | 0.174 | 0.749 | 16.125 | 0.250 |
| ATSCF@E1_STRADDLE | 40 | 0.947 | 0.932 | 0.961 | 0.989 | 0.039 | 0.149 | 0.769 | 17.000 | 0.188 |
| ATSCF@E1_STRADDLE | 60 | 0.952 | 0.946 | 0.958 | 0.990 | 0.036 | 0.131 | 0.777 | 18.500 | 0.208 |
| DEPTHCF@E1_STRADDLE | 16 | 0.880 | 0.795 | 0.965 | 0.973 | 0.088 | 0.315 | 0.668 | 6.500 | 0.708 |
| DEPTHCF@E1_STRADDLE | 24 | 0.921 | 0.871 | 0.970 | 0.984 | 0.061 | 0.233 | 0.730 | 8.500 | 0.698 |
| DEPTHCF@E1_STRADDLE | 40 | 0.937 | 0.905 | 0.969 | 0.989 | 0.044 | 0.174 | 0.761 | 11.500 | 0.625 |
| DEPTHCF@E1_STRADDLE | 60 | 0.946 | 0.927 | 0.965 | 0.990 | 0.038 | 0.145 | 0.772 | 13.750 | 0.542 |
| E1CAL@E1_STRADDLE | 16 | 0.882 | 0.836 | 0.929 | 0.951 | 0.080 | 0.286 | 0.673 | 10.500 | 0.542 |
| E1CAL@E1_STRADDLE | 24 | 0.925 | 0.905 | 0.944 | 0.973 | 0.056 | 0.214 | 0.735 | 13.750 | 0.479 |
| E1CAL@E1_STRADDLE | 40 | 0.946 | 0.933 | 0.960 | 0.987 | 0.039 | 0.146 | 0.772 | 15.125 | 0.458 |
| E1CAL@E1_STRADDLE | 60 | 0.950 | 0.939 | 0.960 | 0.988 | 0.038 | 0.142 | 0.778 | 15.875 | 0.448 |
| E1RAW@E1_STRADDLE | 16 | 0.909 | 0.918 | 0.900 | 0.968 | 0.073 | 0.341 | 0.695 | 15.250 | 0.385 |
| E1RAW@E1_STRADDLE | 24 | 0.933 | 0.945 | 0.921 | 0.980 | 0.056 | 0.259 | 0.733 | 16.750 | 0.312 |
| E1RAW@E1_STRADDLE | 40 | 0.952 | 0.952 | 0.951 | 0.988 | 0.039 | 0.165 | 0.779 | 17.750 | 0.375 |
| E1RAW@E1_STRADDLE | 60 | 0.953 | 0.952 | 0.955 | 0.990 | 0.036 | 0.153 | 0.781 | 17.750 | 0.427 |
| G3@E1_STRADDLE | 16 | 0.879 | 0.850 | 0.909 | 0.929 | 0.111 | 0.381 | 0.699 | 16.875 | 0.146 |
| G3@E1_STRADDLE | 24 | 0.887 | 0.853 | 0.920 | 0.948 | 0.092 | 0.330 | 0.691 | 16.000 | 0.062 |
| G3@E1_STRADDLE | 40 | 0.919 | 0.883 | 0.955 | 0.977 | 0.064 | 0.243 | 0.735 | 16.000 | 0.177 |
| G3@E1_STRADDLE | 60 | 0.947 | 0.934 | 0.961 | 0.988 | 0.043 | 0.170 | 0.772 | 17.375 | 0.260 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@E1_STRADDLE | 16 | 0.012 | 1.800 | 0.074 | 67 | 96 |
| ATSAPPROX@E1_STRADDLE | 24 | 0.014 | 1.540 | 0.050 | 79 | 96 |
| ATSAPPROX@E1_STRADDLE | 40 | 0.011 | 1.378 | 0.036 | 79 | 96 |
| ATSAPPROX@E1_STRADDLE | 60 | 0.011 | 1.212 | 0.026 | 75 | 96 |
| ATSCF@E1_STRADDLE | 16 | 0.014 | 1.755 | 0.081 | 62 | 96 |
| ATSCF@E1_STRADDLE | 24 | 0.013 | 1.591 | 0.053 | 72 | 96 |
| ATSCF@E1_STRADDLE | 40 | 0.013 | 1.498 | 0.042 | 78 | 96 |
| ATSCF@E1_STRADDLE | 60 | 0.013 | 1.328 | 0.030 | 76 | 96 |
| DEPTHCF@E1_STRADDLE | 16 | 0.008 | 3.040 | 0.155 | 28 | 96 |
| DEPTHCF@E1_STRADDLE | 24 | 0.006 | 2.606 | 0.116 | 29 | 96 |
| DEPTHCF@E1_STRADDLE | 40 | 0.010 | 2.162 | 0.074 | 36 | 96 |
| DEPTHCF@E1_STRADDLE | 60 | 0.015 | 1.702 | 0.048 | 44 | 96 |
| E1CAL@E1_STRADDLE | 16 | 0.028 | 1.147 | 0.075 | 44 | 96 |
| E1CAL@E1_STRADDLE | 24 | 0.016 | 1.007 | 0.049 | 50 | 96 |
| E1CAL@E1_STRADDLE | 40 | 0.009 | 1.271 | 0.038 | 52 | 96 |
| E1CAL@E1_STRADDLE | 60 | 0.011 | 1.368 | 0.040 | 53 | 96 |
| E1RAW@E1_STRADDLE | 16 | 0.042 | 0.457 | 0.060 | 59 | 96 |
| E1RAW@E1_STRADDLE | 24 | 0.032 | 0.481 | 0.049 | 66 | 96 |
| E1RAW@E1_STRADDLE | 40 | 0.013 | 0.555 | 0.030 | 60 | 96 |
| E1RAW@E1_STRADDLE | 60 | 0.011 | 0.575 | 0.029 | 55 | 96 |
| G3@E1_STRADDLE | 16 | 0.054 | 2.092 | 0.143 | 82 | 96 |
| G3@E1_STRADDLE | 24 | 0.034 | 2.011 | 0.123 | 90 | 96 |
| G3@E1_STRADDLE | 40 | 0.016 | 1.993 | 0.098 | 79 | 96 |
| G3@E1_STRADDLE | 60 | 0.016 | 1.767 | 0.065 | 71 | 96 |

## Paths of PHYSCF_ATS_MARGIN

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@PHYSCF_ATS_MARGIN | 0.9392 | 0.9338 | 0.9441 | 0.1666 | 0.1544 | 0.1820 | 0.0447 | 0.0406 | 0.0476 | 0.9829 | 0.9773 | 0.9853 |
| ATSCF@PHYSCF_ATS_MARGIN | 0.9259 | 0.9063 | 0.9373 | 0.2064 | 0.1895 | 0.2374 | 0.0569 | 0.0495 | 0.0674 | 0.9719 | 0.9530 | 0.9847 |
| DEPTHCF@PHYSCF_ATS_MARGIN | 0.9270 | 0.9002 | 0.9379 | 0.2355 | 0.2050 | 0.2691 | 0.0635 | 0.0546 | 0.0735 | 0.9745 | 0.9614 | 0.9828 |
| E1CAL@PHYSCF_ATS_MARGIN | 0.9293 | 0.9143 | 0.9392 | 0.2794 | 0.2446 | 0.3091 | 0.0736 | 0.0614 | 0.0840 | 0.9656 | 0.9529 | 0.9698 |
| E1RAW@PHYSCF_ATS_MARGIN | 0.9375 | 0.9287 | 0.9445 | 0.2307 | 0.2003 | 0.2646 | 0.0512 | 0.0449 | 0.0588 | 0.9744 | 0.9685 | 0.9778 |
| G3@PHYSCF_ATS_MARGIN | 0.8296 | 0.7799 | 0.8637 | 0.4702 | 0.4156 | 0.5338 | 0.1505 | 0.1283 | 0.1766 | 0.8896 | 0.8317 | 0.9250 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@PHYSCF_ATS_MARGIN − E1CAL@PHYSCF_ATS_MARGIN | BA_AULC | -0.0034 | 0.0037 | -0.0214 | 0.0085 | 3/8 |
| ATSCF@PHYSCF_ATS_MARGIN − E1CAL@PHYSCF_ATS_MARGIN | LL_AULC | -0.0729 | 0.0105 | -0.1071 | -0.0151 | 8/8 |
| ATSCF@PHYSCF_ATS_MARGIN − E1CAL@PHYSCF_ATS_MARGIN | Brier_AULC | -0.0167 | 0.0035 | -0.0277 | 0.0016 | 7/8 |
| ATSCF@PHYSCF_ATS_MARGIN − DEPTHCF@PHYSCF_ATS_MARGIN | BA_AULC | -0.0012 | 0.0031 | -0.0094 | 0.0157 | 3/8 |
| ATSCF@PHYSCF_ATS_MARGIN − DEPTHCF@PHYSCF_ATS_MARGIN | LL_AULC | -0.0291 | 0.0082 | -0.0738 | -0.0078 | 8/8 |
| ATSCF@PHYSCF_ATS_MARGIN − DEPTHCF@PHYSCF_ATS_MARGIN | Brier_AULC | -0.0067 | 0.0028 | -0.0219 | 0.0011 | 7/8 |
| DEPTHCF@PHYSCF_ATS_MARGIN − E1CAL@PHYSCF_ATS_MARGIN | BA_AULC | -0.0023 | 0.0042 | -0.0276 | 0.0137 | 4/8 |
| DEPTHCF@PHYSCF_ATS_MARGIN − E1CAL@PHYSCF_ATS_MARGIN | LL_AULC | -0.0438 | 0.0090 | -0.0835 | -0.0057 | 8/8 |
| DEPTHCF@PHYSCF_ATS_MARGIN − E1CAL@PHYSCF_ATS_MARGIN | Brier_AULC | -0.0100 | 0.0029 | -0.0246 | 0.0022 | 7/8 |
| E1CAL@PHYSCF_ATS_MARGIN − E1RAW@PHYSCF_ATS_MARGIN | BA_AULC | -0.0082 | 0.0025 | -0.0221 | 0.0001 | 1/8 |
| E1CAL@PHYSCF_ATS_MARGIN − E1RAW@PHYSCF_ATS_MARGIN | LL_AULC | 0.0487 | 0.0099 | -0.0032 | 0.0781 | 1/8 |
| E1CAL@PHYSCF_ATS_MARGIN − E1RAW@PHYSCF_ATS_MARGIN | Brier_AULC | 0.0223 | 0.0028 | 0.0097 | 0.0327 | 0/8 |
| ATSCF@PHYSCF_ATS_MARGIN − ATSAPPROX@PHYSCF_ATS_MARGIN | BA_AULC | -0.0134 | 0.0036 | -0.0347 | -0.0007 | 0/8 |
| ATSCF@PHYSCF_ATS_MARGIN − ATSAPPROX@PHYSCF_ATS_MARGIN | LL_AULC | 0.0398 | 0.0062 | 0.0246 | 0.0751 | 0/8 |
| ATSCF@PHYSCF_ATS_MARGIN − ATSAPPROX@PHYSCF_ATS_MARGIN | Brier_AULC | 0.0122 | 0.0023 | 0.0059 | 0.0248 | 0/8 |
| ATSCF@PHYSCF_ATS_MARGIN − G3@PHYSCF_ATS_MARGIN | BA_AULC | 0.0963 | 0.0113 | 0.0616 | 0.1518 | 8/8 |
| ATSCF@PHYSCF_ATS_MARGIN − G3@PHYSCF_ATS_MARGIN | LL_AULC | -0.2638 | 0.0146 | -0.3440 | -0.2261 | 8/8 |
| ATSCF@PHYSCF_ATS_MARGIN − G3@PHYSCF_ATS_MARGIN | Brier_AULC | -0.0936 | 0.0058 | -0.1254 | -0.0787 | 8/8 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@PHYSCF_ATS_MARGIN | 8/8 | 16.50 | 21.50 | 16,20,24,28,24,20,24,16 |
| ATSCF@PHYSCF_ATS_MARGIN | 8/8 | 20.00 | 26.00 | 20,20,28,28,36,28,20,28 |
| DEPTHCF@PHYSCF_ATS_MARGIN | 8/8 | 21.00 | 28.50 | 28,28,28,24,28,44,24,24 |
| E1CAL@PHYSCF_ATS_MARGIN | 8/8 | 20.00 | 25.00 | 28,28,24,24,28,24,20,24 |
| E1RAW@PHYSCF_ATS_MARGIN | 8/8 | 18.00 | 23.00 | 28,28,24,20,16,24,20,24 |
| G3@PHYSCF_ATS_MARGIN | 0/8 | – | – | –,–,–,–,–,–,–,– |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@PHYSCF_ATS_MARGIN | 16 | 0.931 | 0.914 | 0.947 | 0.981 | 0.053 | 0.200 | 0.755 | 16.250 | 0.323 |
| ATSAPPROX@PHYSCF_ATS_MARGIN | 24 | 0.943 | 0.926 | 0.960 | 0.987 | 0.041 | 0.157 | 0.771 | 16.750 | 0.312 |
| ATSAPPROX@PHYSCF_ATS_MARGIN | 40 | 0.951 | 0.942 | 0.960 | 0.989 | 0.036 | 0.135 | 0.780 | 16.875 | 0.312 |
| ATSAPPROX@PHYSCF_ATS_MARGIN | 60 | 0.953 | 0.944 | 0.963 | 0.990 | 0.033 | 0.123 | 0.787 | 16.750 | 0.354 |
| ATSCF@PHYSCF_ATS_MARGIN | 16 | 0.921 | 0.905 | 0.938 | 0.974 | 0.068 | 0.251 | 0.730 | 16.375 | 0.250 |
| ATSCF@PHYSCF_ATS_MARGIN | 24 | 0.941 | 0.921 | 0.961 | 0.986 | 0.045 | 0.179 | 0.766 | 16.625 | 0.292 |
| ATSCF@PHYSCF_ATS_MARGIN | 40 | 0.948 | 0.937 | 0.959 | 0.986 | 0.042 | 0.165 | 0.773 | 17.125 | 0.250 |
| ATSCF@PHYSCF_ATS_MARGIN | 60 | 0.954 | 0.946 | 0.962 | 0.988 | 0.036 | 0.136 | 0.794 | 17.750 | 0.302 |
| DEPTHCF@PHYSCF_ATS_MARGIN | 16 | 0.896 | 0.876 | 0.916 | 0.969 | 0.094 | 0.332 | 0.693 | 12.250 | 0.479 |
| DEPTHCF@PHYSCF_ATS_MARGIN | 24 | 0.939 | 0.918 | 0.961 | 0.985 | 0.059 | 0.233 | 0.770 | 13.750 | 0.604 |
| DEPTHCF@PHYSCF_ATS_MARGIN | 40 | 0.947 | 0.933 | 0.961 | 0.987 | 0.046 | 0.184 | 0.770 | 14.500 | 0.479 |
| DEPTHCF@PHYSCF_ATS_MARGIN | 60 | 0.950 | 0.938 | 0.962 | 0.988 | 0.037 | 0.147 | 0.781 | 15.750 | 0.458 |
| E1CAL@PHYSCF_ATS_MARGIN | 16 | 0.904 | 0.860 | 0.947 | 0.963 | 0.089 | 0.307 | 0.731 | 13.500 | 0.490 |
| E1CAL@PHYSCF_ATS_MARGIN | 24 | 0.941 | 0.923 | 0.960 | 0.974 | 0.068 | 0.255 | 0.772 | 15.750 | 0.531 |
| E1CAL@PHYSCF_ATS_MARGIN | 40 | 0.948 | 0.931 | 0.964 | 0.977 | 0.064 | 0.247 | 0.783 | 14.500 | 0.500 |
| E1CAL@PHYSCF_ATS_MARGIN | 60 | 0.952 | 0.941 | 0.963 | 0.979 | 0.060 | 0.236 | 0.785 | 15.625 | 0.438 |
| E1RAW@PHYSCF_ATS_MARGIN | 16 | 0.930 | 0.935 | 0.924 | 0.975 | 0.057 | 0.234 | 0.736 | 16.625 | 0.396 |
| E1RAW@PHYSCF_ATS_MARGIN | 24 | 0.941 | 0.940 | 0.943 | 0.979 | 0.046 | 0.201 | 0.758 | 17.500 | 0.438 |
| E1RAW@PHYSCF_ATS_MARGIN | 40 | 0.953 | 0.947 | 0.959 | 0.982 | 0.040 | 0.167 | 0.790 | 16.375 | 0.458 |
| E1RAW@PHYSCF_ATS_MARGIN | 60 | 0.954 | 0.947 | 0.960 | 0.982 | 0.038 | 0.166 | 0.789 | 16.750 | 0.427 |
| G3@PHYSCF_ATS_MARGIN | 16 | 0.802 | 0.760 | 0.845 | 0.868 | 0.151 | 0.477 | 0.637 | 14.750 | 0.302 |
| G3@PHYSCF_ATS_MARGIN | 24 | 0.804 | 0.760 | 0.847 | 0.862 | 0.159 | 0.491 | 0.632 | 13.000 | 0.375 |
| G3@PHYSCF_ATS_MARGIN | 40 | 0.805 | 0.800 | 0.810 | 0.872 | 0.173 | 0.522 | 0.660 | 15.125 | 0.271 |
| G3@PHYSCF_ATS_MARGIN | 60 | 0.891 | 0.871 | 0.912 | 0.955 | 0.108 | 0.361 | 0.721 | 16.125 | 0.260 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@PHYSCF_ATS_MARGIN | 16 | 0.026 | 1.802 | 0.071 | 65 | 96 |
| ATSAPPROX@PHYSCF_ATS_MARGIN | 24 | 0.013 | 1.584 | 0.048 | 66 | 96 |
| ATSAPPROX@PHYSCF_ATS_MARGIN | 40 | 0.015 | 1.372 | 0.037 | 66 | 96 |
| ATSAPPROX@PHYSCF_ATS_MARGIN | 60 | 0.009 | 1.137 | 0.022 | 62 | 96 |
| ATSCF@PHYSCF_ATS_MARGIN | 16 | 0.034 | 2.077 | 0.100 | 72 | 96 |
| ATSCF@PHYSCF_ATS_MARGIN | 24 | 0.019 | 1.874 | 0.071 | 68 | 96 |
| ATSCF@PHYSCF_ATS_MARGIN | 40 | 0.021 | 1.712 | 0.059 | 72 | 96 |
| ATSCF@PHYSCF_ATS_MARGIN | 60 | 0.016 | 1.360 | 0.037 | 67 | 96 |
| DEPTHCF@PHYSCF_ATS_MARGIN | 16 | 0.062 | 3.406 | 0.171 | 50 | 96 |
| DEPTHCF@PHYSCF_ATS_MARGIN | 24 | 0.042 | 2.685 | 0.119 | 38 | 96 |
| DEPTHCF@PHYSCF_ATS_MARGIN | 40 | 0.035 | 2.101 | 0.085 | 50 | 96 |
| DEPTHCF@PHYSCF_ATS_MARGIN | 60 | 0.028 | 1.609 | 0.051 | 52 | 96 |
| E1CAL@PHYSCF_ATS_MARGIN | 16 | 0.064 | 1.791 | 0.126 | 49 | 96 |
| E1CAL@PHYSCF_ATS_MARGIN | 24 | 0.070 | 1.889 | 0.117 | 45 | 96 |
| E1CAL@PHYSCF_ATS_MARGIN | 40 | 0.073 | 2.071 | 0.126 | 48 | 96 |
| E1CAL@PHYSCF_ATS_MARGIN | 60 | 0.082 | 2.057 | 0.124 | 54 | 96 |
| E1RAW@PHYSCF_ATS_MARGIN | 16 | 0.049 | 0.681 | 0.052 | 58 | 96 |
| E1RAW@PHYSCF_ATS_MARGIN | 24 | 0.043 | 0.720 | 0.047 | 54 | 96 |
| E1RAW@PHYSCF_ATS_MARGIN | 40 | 0.028 | 0.742 | 0.033 | 52 | 96 |
| E1RAW@PHYSCF_ATS_MARGIN | 60 | 0.026 | 0.717 | 0.032 | 55 | 96 |
| G3@PHYSCF_ATS_MARGIN | 16 | 0.085 | 1.725 | 0.128 | 67 | 96 |
| G3@PHYSCF_ATS_MARGIN | 24 | 0.088 | 1.857 | 0.142 | 60 | 96 |
| G3@PHYSCF_ATS_MARGIN | 40 | 0.109 | 3.569 | 0.189 | 70 | 96 |
| G3@PHYSCF_ATS_MARGIN | 60 | 0.080 | 2.705 | 0.159 | 71 | 96 |

## Paths of E1_MAXIMIN

AULC over B8–B60 (every 4) (mean, min, max over repeats):

| arm | BA_AULC_mean | BA_AULC_min | BA_AULC_max | LL_AULC_mean | LL_AULC_min | LL_AULC_max | Brier_AULC_mean | Brier_AULC_min | Brier_AULC_max | AUC_AULC_mean | AUC_AULC_min | AUC_AULC_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@E1_MAXIMIN | 0.9313 | 0.9187 | 0.9414 | 0.1772 | 0.1656 | 0.1922 | 0.0483 | 0.0444 | 0.0526 | 0.9839 | 0.9816 | 0.9868 |
| ATSCF@E1_MAXIMIN | 0.9229 | 0.9076 | 0.9325 | 0.1911 | 0.1802 | 0.2136 | 0.0535 | 0.0502 | 0.0594 | 0.9771 | 0.9704 | 0.9818 |
| DEPTHCF@E1_MAXIMIN | 0.9068 | 0.8649 | 0.9228 | 0.2436 | 0.2249 | 0.3051 | 0.0660 | 0.0593 | 0.0877 | 0.9728 | 0.9419 | 0.9812 |
| E1CAL@E1_MAXIMIN | 0.9216 | 0.9058 | 0.9312 | 0.2208 | 0.1878 | 0.2532 | 0.0572 | 0.0503 | 0.0690 | 0.9699 | 0.9598 | 0.9756 |
| E1RAW@E1_MAXIMIN | 0.9263 | 0.9136 | 0.9334 | 0.3125 | 0.2540 | 0.3860 | 0.0621 | 0.0535 | 0.0758 | 0.9783 | 0.9722 | 0.9828 |
| G3@E1_MAXIMIN | 0.9172 | 0.9029 | 0.9313 | 0.2747 | 0.2443 | 0.2959 | 0.0725 | 0.0627 | 0.0805 | 0.9686 | 0.9584 | 0.9769 |

Paired contrasts (per repeat; 'better' = higher BA or lower loss):

| contrast | metric | mean | se | min | max | repeats_better |
|---|---|---|---|---|---|---|
| ATSCF@E1_MAXIMIN − E1CAL@E1_MAXIMIN | BA_AULC | 0.0013 | 0.0039 | -0.0121 | 0.0162 | 4/8 |
| ATSCF@E1_MAXIMIN − E1CAL@E1_MAXIMIN | LL_AULC | -0.0297 | 0.0052 | -0.0405 | -0.0006 | 8/8 |
| ATSCF@E1_MAXIMIN − E1CAL@E1_MAXIMIN | Brier_AULC | -0.0037 | 0.0017 | -0.0099 | 0.0033 | 5/8 |
| ATSCF@E1_MAXIMIN − DEPTHCF@E1_MAXIMIN | BA_AULC | 0.0161 | 0.0057 | 0.0007 | 0.0479 | 8/8 |
| ATSCF@E1_MAXIMIN − DEPTHCF@E1_MAXIMIN | LL_AULC | -0.0525 | 0.0060 | -0.0915 | -0.0348 | 8/8 |
| ATSCF@E1_MAXIMIN − DEPTHCF@E1_MAXIMIN | Brier_AULC | -0.0125 | 0.0024 | -0.0285 | -0.0062 | 8/8 |
| DEPTHCF@E1_MAXIMIN − E1CAL@E1_MAXIMIN | BA_AULC | -0.0148 | 0.0047 | -0.0409 | 0.0027 | 1/8 |
| DEPTHCF@E1_MAXIMIN − E1CAL@E1_MAXIMIN | LL_AULC | 0.0229 | 0.0070 | 0.0007 | 0.0520 | 0/8 |
| DEPTHCF@E1_MAXIMIN − E1CAL@E1_MAXIMIN | Brier_AULC | 0.0088 | 0.0019 | 0.0029 | 0.0187 | 0/8 |
| E1CAL@E1_MAXIMIN − E1RAW@E1_MAXIMIN | BA_AULC | -0.0047 | 0.0025 | -0.0154 | 0.0057 | 2/8 |
| E1CAL@E1_MAXIMIN − E1RAW@E1_MAXIMIN | LL_AULC | -0.0917 | 0.0079 | -0.1328 | -0.0662 | 8/8 |
| E1CAL@E1_MAXIMIN − E1RAW@E1_MAXIMIN | Brier_AULC | -0.0049 | 0.0010 | -0.0087 | -0.0012 | 8/8 |
| ATSCF@E1_MAXIMIN − ATSAPPROX@E1_MAXIMIN | BA_AULC | -0.0084 | 0.0017 | -0.0146 | -0.0020 | 0/8 |
| ATSCF@E1_MAXIMIN − ATSAPPROX@E1_MAXIMIN | LL_AULC | 0.0139 | 0.0022 | 0.0048 | 0.0218 | 0/8 |
| ATSCF@E1_MAXIMIN − ATSAPPROX@E1_MAXIMIN | Brier_AULC | 0.0052 | 0.0008 | 0.0016 | 0.0083 | 0/8 |
| ATSCF@E1_MAXIMIN − G3@E1_MAXIMIN | BA_AULC | 0.0057 | 0.0030 | -0.0066 | 0.0191 | 6/8 |
| ATSCF@E1_MAXIMIN − G3@E1_MAXIMIN | LL_AULC | -0.0836 | 0.0062 | -0.1072 | -0.0557 | 8/8 |
| ATSCF@E1_MAXIMIN − G3@E1_MAXIMIN | Brier_AULC | -0.0190 | 0.0021 | -0.0271 | -0.0093 | 8/8 |

BA ≥ 0.93 (confirmation spend = b + 4 for the first b with BA ≥ 0.93 at b and b + 4; total revealed simulations):

| arm | completed | first_mean | spend_mean | spend_per_repeat |
|---|---|---|---|---|
| ATSAPPROX@E1_MAXIMIN | 8/8 | 21.00 | 32.50 | 20,48,52,28,28,16,24,44 |
| ATSCF@E1_MAXIMIN | 8/8 | 25.50 | 36.50 | 20,48,52,28,32,28,32,52 |
| DEPTHCF@E1_MAXIMIN | 3/8 | 33.33 | 41.33 | 52,–,–,–,–,32,40,– |
| E1CAL@E1_MAXIMIN | 7/8 | 26.86 | 38.29 | 40,48,48,32,–,24,32,44 |
| E1RAW@E1_MAXIMIN | 8/8 | 25.50 | 34.50 | 44,28,44,28,36,24,32,40 |
| G3@E1_MAXIMIN | 8/8 | 35.50 | 41.00 | 32,44,48,36,44,32,32,60 |

Matched budgets (mean over repeats):

| arm | budget | BA | sensitivity | specificity | AUC | brier | log_loss | q20_BA | shortK_pooled_captured | spec_NEW |
|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX@E1_MAXIMIN | 16 | 0.928 | 0.905 | 0.951 | 0.983 | 0.054 | 0.205 | 0.742 | 13.250 | 0.479 |
| ATSAPPROX@E1_MAXIMIN | 24 | 0.935 | 0.913 | 0.957 | 0.986 | 0.046 | 0.176 | 0.755 | 13.250 | 0.438 |
| ATSAPPROX@E1_MAXIMIN | 40 | 0.940 | 0.923 | 0.958 | 0.989 | 0.041 | 0.153 | 0.758 | 14.750 | 0.354 |
| ATSAPPROX@E1_MAXIMIN | 60 | 0.946 | 0.931 | 0.960 | 0.990 | 0.037 | 0.136 | 0.775 | 15.750 | 0.302 |
| ATSCF@E1_MAXIMIN | 16 | 0.930 | 0.908 | 0.952 | 0.982 | 0.055 | 0.210 | 0.748 | 14.125 | 0.438 |
| ATSCF@E1_MAXIMIN | 24 | 0.931 | 0.907 | 0.956 | 0.986 | 0.048 | 0.181 | 0.740 | 12.875 | 0.458 |
| ATSCF@E1_MAXIMIN | 40 | 0.940 | 0.921 | 0.958 | 0.988 | 0.042 | 0.156 | 0.755 | 14.750 | 0.365 |
| ATSCF@E1_MAXIMIN | 60 | 0.943 | 0.926 | 0.960 | 0.990 | 0.038 | 0.137 | 0.767 | 15.375 | 0.312 |
| DEPTHCF@E1_MAXIMIN | 16 | 0.904 | 0.881 | 0.928 | 0.969 | 0.084 | 0.303 | 0.697 | 9.750 | 0.583 |
| DEPTHCF@E1_MAXIMIN | 24 | 0.919 | 0.875 | 0.963 | 0.982 | 0.063 | 0.244 | 0.720 | 7.875 | 0.646 |
| DEPTHCF@E1_MAXIMIN | 40 | 0.922 | 0.879 | 0.964 | 0.985 | 0.051 | 0.200 | 0.720 | 7.875 | 0.646 |
| DEPTHCF@E1_MAXIMIN | 60 | 0.929 | 0.887 | 0.970 | 0.987 | 0.043 | 0.169 | 0.740 | 7.250 | 0.646 |
| E1CAL@E1_MAXIMIN | 16 | 0.904 | 0.908 | 0.900 | 0.959 | 0.073 | 0.289 | 0.698 | 13.125 | 0.458 |
| E1CAL@E1_MAXIMIN | 24 | 0.924 | 0.911 | 0.938 | 0.976 | 0.052 | 0.204 | 0.719 | 12.250 | 0.500 |
| E1CAL@E1_MAXIMIN | 40 | 0.937 | 0.925 | 0.948 | 0.982 | 0.045 | 0.164 | 0.749 | 13.625 | 0.500 |
| E1CAL@E1_MAXIMIN | 60 | 0.944 | 0.931 | 0.957 | 0.982 | 0.042 | 0.160 | 0.775 | 13.375 | 0.490 |
| E1RAW@E1_MAXIMIN | 16 | 0.900 | 0.930 | 0.871 | 0.972 | 0.084 | 0.391 | 0.689 | 15.000 | 0.385 |
| E1RAW@E1_MAXIMIN | 24 | 0.929 | 0.940 | 0.918 | 0.982 | 0.059 | 0.285 | 0.722 | 15.250 | 0.417 |
| E1RAW@E1_MAXIMIN | 40 | 0.941 | 0.951 | 0.930 | 0.987 | 0.051 | 0.255 | 0.745 | 17.250 | 0.354 |
| E1RAW@E1_MAXIMIN | 60 | 0.947 | 0.952 | 0.942 | 0.988 | 0.046 | 0.251 | 0.767 | 16.375 | 0.385 |
| G3@E1_MAXIMIN | 16 | 0.890 | 0.871 | 0.908 | 0.936 | 0.104 | 0.366 | 0.699 | 17.125 | 0.156 |
| G3@E1_MAXIMIN | 24 | 0.919 | 0.900 | 0.937 | 0.971 | 0.076 | 0.292 | 0.720 | 15.000 | 0.271 |
| G3@E1_MAXIMIN | 40 | 0.936 | 0.920 | 0.952 | 0.986 | 0.054 | 0.224 | 0.738 | 14.750 | 0.323 |
| G3@E1_MAXIMIN | 60 | 0.941 | 0.926 | 0.956 | 0.988 | 0.049 | 0.204 | 0.751 | 15.250 | 0.240 |

Reliability (mean over repeats; slope 1 and intercept 0 = calibrated) and the hard corner as error COUNTS summed over repeats (NEW-batch conduction runs predicted Keyhole / all of them):

| arm | budget | cal_in_large | cal_slope | ECE | hard_errors | hard_n |
|---|---|---|---|---|---|---|
| ATSAPPROX@E1_MAXIMIN | 16 | 0.026 | 1.909 | 0.074 | 50 | 96 |
| ATSAPPROX@E1_MAXIMIN | 24 | 0.019 | 1.712 | 0.056 | 54 | 96 |
| ATSAPPROX@E1_MAXIMIN | 40 | 0.016 | 1.519 | 0.044 | 62 | 96 |
| ATSAPPROX@E1_MAXIMIN | 60 | 0.010 | 1.347 | 0.034 | 67 | 96 |
| ATSCF@E1_MAXIMIN | 16 | 0.020 | 1.908 | 0.079 | 54 | 96 |
| ATSCF@E1_MAXIMIN | 24 | 0.016 | 1.701 | 0.057 | 52 | 96 |
| ATSCF@E1_MAXIMIN | 40 | 0.016 | 1.525 | 0.045 | 61 | 96 |
| ATSCF@E1_MAXIMIN | 60 | 0.009 | 1.351 | 0.035 | 66 | 96 |
| DEPTHCF@E1_MAXIMIN | 16 | 0.040 | 2.608 | 0.133 | 40 | 96 |
| DEPTHCF@E1_MAXIMIN | 24 | 0.025 | 2.451 | 0.110 | 34 | 96 |
| DEPTHCF@E1_MAXIMIN | 40 | 0.019 | 2.133 | 0.084 | 34 | 96 |
| DEPTHCF@E1_MAXIMIN | 60 | 0.010 | 1.892 | 0.067 | 34 | 96 |
| E1CAL@E1_MAXIMIN | 16 | 0.049 | 0.859 | 0.060 | 52 | 96 |
| E1CAL@E1_MAXIMIN | 24 | 0.023 | 0.853 | 0.034 | 48 | 96 |
| E1CAL@E1_MAXIMIN | 40 | 0.015 | 0.975 | 0.027 | 48 | 96 |
| E1CAL@E1_MAXIMIN | 60 | 0.006 | 0.893 | 0.027 | 49 | 96 |
| E1RAW@E1_MAXIMIN | 16 | 0.065 | 0.369 | 0.080 | 59 | 96 |
| E1RAW@E1_MAXIMIN | 24 | 0.037 | 0.380 | 0.052 | 56 | 96 |
| E1RAW@E1_MAXIMIN | 40 | 0.030 | 0.380 | 0.046 | 62 | 96 |
| E1RAW@E1_MAXIMIN | 60 | 0.021 | 0.353 | 0.043 | 59 | 96 |
| G3@E1_MAXIMIN | 16 | 0.071 | 2.050 | 0.148 | 81 | 96 |
| G3@E1_MAXIMIN | 24 | 0.059 | 2.198 | 0.133 | 70 | 96 |
| G3@E1_MAXIMIN | 40 | 0.043 | 2.130 | 0.108 | 65 | 96 |
| G3@E1_MAXIMIN | 60 | 0.041 | 1.964 | 0.095 | 73 | 96 |

