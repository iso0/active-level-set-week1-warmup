# RC22 part 3 — acquisition comparison (fresh DEV repeats 43–50; predictive model PHR_NRMAP and cutoff 0.5 fixed in every arm)

SELECTOR = BALD_LAP; SIMPLE = HA_LR; arms: ['A1_MARGIN', 'A2_MARGIN_COV', 'A3_SEL_COV', 'A4_MAXIMIN', 'A5_SIMPLE'].

**Primary (A3 − A2): {"Q1": "NOT DIFFERENT (DEV)", "Q2": "NO CLEAR DIFFERENCE (DEV)", "B8_B60_BA_margin_0.010": "NOT DIFFERENT (DEV)", "SUCCESS": false}**

## Pre-declared contrasts (fold-pooled curves, paired by repeat)

| window | contrast | metric | direction | margin | mean | se | min | max | good | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| small | A3_SEL_COV − A2_MARGIN_COV | BA | higher | 0.0200 | -0.0033 | 0.0034 | -0.0166 | 0.0109 | 2/8 | NOT DIFFERENT (DEV) |
| all | A3_SEL_COV − A2_MARGIN_COV | BA | higher | 0.0200 | -0.0082 | 0.0015 | -0.0140 | -0.0003 | 0/8 | NOT DIFFERENT (DEV) |
| all | A3_SEL_COV − A2_MARGIN_COV | BA | higher | 0.0100 | -0.0082 | 0.0015 | -0.0140 | -0.0003 | 0/8 | NOT DIFFERENT (DEV) |
| small | A3_SEL_COV − A2_MARGIN_COV | log_loss | lower | 0.0100 | -0.0012 | 0.0056 | -0.0264 | 0.0211 | 4/8 | NOT DIFFERENT (DEV) |
| all | A3_SEL_COV − A2_MARGIN_COV | log_loss | lower | 0.0050 | 0.0082 | 0.0025 | -0.0017 | 0.0173 | 2/8 | NOT DIFFERENT (DEV) |
| small | A3_SEL_COV − A2_MARGIN_COV | sensitivity | higher | 0.0200 | -0.0119 | 0.0053 | -0.0376 | 0.0140 | 1/8 | NOT DIFFERENT (DEV) |
| small | A3_SEL_COV − A2_MARGIN_COV | specificity | higher | 0.0200 | 0.0054 | 0.0028 | -0.0109 | 0.0181 | 7/8 | NOT DIFFERENT (DEV) |
| small | A2_MARGIN_COV − A1_MARGIN | BA | higher | 0.0200 | -0.0022 | 0.0021 | -0.0113 | 0.0070 | 3/8 | NOT DIFFERENT (DEV) |
| all | A2_MARGIN_COV − A1_MARGIN | BA | higher | 0.0200 | -0.0004 | 0.0015 | -0.0077 | 0.0050 | 4/8 | NOT DIFFERENT (DEV) |
| all | A2_MARGIN_COV − A1_MARGIN | BA | higher | 0.0100 | -0.0004 | 0.0015 | -0.0077 | 0.0050 | 4/8 | NOT DIFFERENT (DEV) |
| small | A2_MARGIN_COV − A1_MARGIN | log_loss | lower | 0.0100 | 0.0006 | 0.0021 | -0.0110 | 0.0069 | 3/8 | NOT DIFFERENT (DEV) |
| all | A2_MARGIN_COV − A1_MARGIN | log_loss | lower | 0.0050 | 0.0002 | 0.0019 | -0.0100 | 0.0060 | 4/8 | NOT DIFFERENT (DEV) |
| small | A2_MARGIN_COV − A1_MARGIN | sensitivity | higher | 0.0200 | -0.0022 | 0.0059 | -0.0284 | 0.0218 | 4/8 | NOT DIFFERENT (DEV) |
| small | A2_MARGIN_COV − A1_MARGIN | specificity | higher | 0.0200 | -0.0022 | 0.0020 | -0.0082 | 0.0058 | 3/8 | NOT DIFFERENT (DEV) |
| small | A3_SEL_COV − A1_MARGIN | BA | higher | 0.0200 | -0.0055 | 0.0049 | -0.0259 | 0.0118 | 4/8 | NOT DIFFERENT (DEV) |
| all | A3_SEL_COV − A1_MARGIN | BA | higher | 0.0200 | -0.0086 | 0.0020 | -0.0184 | -0.0020 | 0/8 | NOT DIFFERENT (DEV) |
| all | A3_SEL_COV − A1_MARGIN | BA | higher | 0.0100 | -0.0086 | 0.0020 | -0.0184 | -0.0020 | 0/8 | NOT DIFFERENT (DEV) |
| small | A3_SEL_COV − A1_MARGIN | log_loss | lower | 0.0100 | -0.0006 | 0.0068 | -0.0258 | 0.0250 | 3/8 | NOT DIFFERENT (DEV) |
| all | A3_SEL_COV − A1_MARGIN | log_loss | lower | 0.0050 | 0.0084 | 0.0034 | -0.0105 | 0.0181 | 1/8 | WORSE (DEV) |
| small | A3_SEL_COV − A1_MARGIN | sensitivity | higher | 0.0200 | -0.0141 | 0.0100 | -0.0552 | 0.0209 | 3/8 | NOT DIFFERENT (DEV) |
| small | A3_SEL_COV − A1_MARGIN | specificity | higher | 0.0200 | 0.0032 | 0.0026 | -0.0051 | 0.0152 | 4/8 | NOT DIFFERENT (DEV) |
| small | A4_MAXIMIN − A1_MARGIN | BA | higher | 0.0200 | -0.0063 | 0.0032 | -0.0215 | 0.0044 | 3/8 | NOT DIFFERENT (DEV) |
| all | A4_MAXIMIN − A1_MARGIN | BA | higher | 0.0200 | -0.0060 | 0.0024 | -0.0166 | 0.0036 | 1/8 | NOT DIFFERENT (DEV) |
| all | A4_MAXIMIN − A1_MARGIN | BA | higher | 0.0100 | -0.0060 | 0.0024 | -0.0166 | 0.0036 | 1/8 | NOT DIFFERENT (DEV) |
| small | A4_MAXIMIN − A1_MARGIN | log_loss | lower | 0.0100 | 0.0062 | 0.0070 | -0.0157 | 0.0438 | 4/8 | NOT DIFFERENT (DEV) |
| all | A4_MAXIMIN − A1_MARGIN | log_loss | lower | 0.0050 | 0.0203 | 0.0051 | 0.0054 | 0.0504 | 0/8 | WORSE (DEV) |
| small | A4_MAXIMIN − A1_MARGIN | sensitivity | higher | 0.0200 | -0.0119 | 0.0079 | -0.0418 | 0.0164 | 3/8 | NOT DIFFERENT (DEV) |
| small | A4_MAXIMIN − A1_MARGIN | specificity | higher | 0.0200 | -0.0008 | 0.0024 | -0.0077 | 0.0099 | 3/8 | NOT DIFFERENT (DEV) |
| small | A5_SIMPLE − A1_MARGIN | BA | higher | 0.0200 | 0.0061 | 0.0031 | -0.0075 | 0.0175 | 5/8 | NOT DIFFERENT (DEV) |
| all | A5_SIMPLE − A1_MARGIN | BA | higher | 0.0200 | 0.0031 | 0.0015 | -0.0025 | 0.0095 | 6/8 | NOT DIFFERENT (DEV) |
| all | A5_SIMPLE − A1_MARGIN | BA | higher | 0.0100 | 0.0031 | 0.0015 | -0.0025 | 0.0095 | 6/8 | NOT DIFFERENT (DEV) |
| small | A5_SIMPLE − A1_MARGIN | log_loss | lower | 0.0100 | -0.0128 | 0.0044 | -0.0282 | 0.0093 | 7/8 | BETTER (DEV) |
| all | A5_SIMPLE − A1_MARGIN | log_loss | lower | 0.0050 | -0.0050 | 0.0028 | -0.0221 | 0.0030 | 6/8 | NOT DIFFERENT (DEV) |
| small | A5_SIMPLE − A1_MARGIN | sensitivity | higher | 0.0200 | 0.0108 | 0.0075 | -0.0197 | 0.0337 | 5/8 | NOT DIFFERENT (DEV) |
| small | A5_SIMPLE − A1_MARGIN | specificity | higher | 0.0200 | 0.0014 | 0.0032 | -0.0087 | 0.0192 | 4/8 | NOT DIFFERENT (DEV) |

## AULC B8–B24

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | brier_mean | brier_se |
|---|---|---|---|---|---|---|---|---|---|---|
| A1_MARGIN | 0.9289 | 0.0029 | 0.1909 | 0.0063 | 0.9180 | 0.0064 | 0.9398 | 0.0033 | 0.0534 | 0.0018 |
| A2_MARGIN_COV | 0.9267 | 0.0031 | 0.1915 | 0.0047 | 0.9158 | 0.0078 | 0.9376 | 0.0035 | 0.0542 | 0.0015 |
| A3_SEL_COV | 0.9234 | 0.0047 | 0.1902 | 0.0045 | 0.9038 | 0.0096 | 0.9430 | 0.0040 | 0.0544 | 0.0018 |
| A4_MAXIMIN | 0.9225 | 0.0043 | 0.1971 | 0.0043 | 0.9061 | 0.0116 | 0.9390 | 0.0045 | 0.0566 | 0.0014 |
| A5_SIMPLE | 0.9350 | 0.0018 | 0.1781 | 0.0050 | 0.9288 | 0.0065 | 0.9412 | 0.0039 | 0.0496 | 0.0010 |

## AULC B8–B60

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | brier_mean | brier_se |
|---|---|---|---|---|---|---|---|---|---|---|
| A1_MARGIN | 0.9434 | 0.0017 | 0.1498 | 0.0037 | 0.9360 | 0.0029 | 0.9508 | 0.0019 | 0.0422 | 0.0011 |
| A2_MARGIN_COV | 0.9430 | 0.0013 | 0.1500 | 0.0028 | 0.9358 | 0.0034 | 0.9501 | 0.0019 | 0.0424 | 0.0008 |
| A3_SEL_COV | 0.9348 | 0.0019 | 0.1582 | 0.0023 | 0.9115 | 0.0041 | 0.9580 | 0.0016 | 0.0450 | 0.0007 |
| A4_MAXIMIN | 0.9374 | 0.0027 | 0.1701 | 0.0045 | 0.9290 | 0.0068 | 0.9458 | 0.0031 | 0.0471 | 0.0012 |
| A5_SIMPLE | 0.9465 | 0.0009 | 0.1449 | 0.0032 | 0.9408 | 0.0024 | 0.9521 | 0.0022 | 0.0403 | 0.0008 |

## Target attainment (fold-pooled curves)

| target | arm | confirmed | spend_mean | spend_max | per_repeat |
|---|---|---|---|---|---|
| BA >= 0.93 | A1_MARGIN | 8/8 | 17.75 | 32.00 | 13,13,32,15,14,17,16,22 |
| BA >= 0.93 | A2_MARGIN_COV | 8/8 | 18.75 | 28.00 | 15,13,26,28,14,17,15,22 |
| BA >= 0.93 | A3_SEL_COV | 8/8 | 19.25 | 32.00 | 19,13,14,24,13,17,32,22 |
| BA >= 0.93 | A4_MAXIMIN | 8/8 | 20.75 | 32.00 | 32,14,31,17,13,16,17,26 |
| BA >= 0.93 | A5_SIMPLE | 8/8 | 15.75 | 19.00 | 15,14,16,19,13,13,19,17 |
| BA >= 0.95 | A1_MARGIN | 7/8 | 39.14 | 47.00 | 35,43,–,44,35,35,35,47 |
| BA >= 0.95 | A2_MARGIN_COV | 8/8 | 39.25 | 49.00 | 42,33,44,36,36,33,49,41 |
| BA >= 0.95 | A3_SEL_COV | 3/8 | 51.67 | 59.00 | –,–,–,40,59,–,56,– |
| BA >= 0.95 | A4_MAXIMIN | 3/8 | 38.67 | 45.00 | –,43,–,–,45,28,–,– |
| BA >= 0.95 | A5_SIMPLE | 8/8 | 34.25 | 57.00 | 34,33,57,28,35,23,35,29 |
| log_loss <= 0.2 | A1_MARGIN | 8/8 | 16.00 | 23.00 | 13,13,19,13,14,18,15,23 |
| log_loss <= 0.2 | A2_MARGIN_COV | 8/8 | 16.50 | 22.00 | 15,13,22,13,14,19,15,21 |
| log_loss <= 0.2 | A3_SEL_COV | 8/8 | 17.00 | 19.00 | 17,15,14,18,16,19,19,18 |
| log_loss <= 0.2 | A4_MAXIMIN | 8/8 | 18.12 | 27.00 | 27,14,16,18,14,17,17,22 |
| log_loss <= 0.2 | A5_SIMPLE | 8/8 | 15.38 | 19.00 | 15,15,13,15,14,15,17,19 |

| contrast | target | restricted_mean_difference(censored=64) | fewer/equal/more | censored_a/b | per_unit | verdict |
|---|---|---|---|---|---|---|
| A3_SEL_COV − A2_MARGIN_COV | BA >= 0.93 | 0.50 | 3/3/2 | 0/0 | 19/15;13/13;14/26;24/28;13/14;17/17;32/15;22/22 | NO CLEAR DIFFERENCE (DEV) |
| A3_SEL_COV − A2_MARGIN_COV | BA >= 0.95 | 20.12 | 0/0/8 | 5/0 | –/42;–/33;–/44;40/36;59/36;–/33;56/49;–/41 | MORE SIMULATIONS (DEV) |
| A3_SEL_COV − A2_MARGIN_COV | log_loss <= 0.2 | 0.50 | 2/1/5 | 0/0 | 17/15;15/13;14/22;18/13;16/14;19/19;19/15;18/21 | NO CLEAR DIFFERENCE (DEV) |
| A2_MARGIN_COV − A1_MARGIN | BA >= 0.93 | 1.00 | 2/4/2 | 0/0 | 15/13;13/13;26/32;28/15;14/14;17/17;15/16;22/22 | NO CLEAR DIFFERENCE (DEV) |
| A2_MARGIN_COV − A1_MARGIN | BA >= 0.95 | -3.00 | 5/0/3 | 0/1 | 42/35;33/43;44/–;36/44;36/35;33/35;49/35;41/47 | NO CLEAR DIFFERENCE (DEV) |
| A2_MARGIN_COV − A1_MARGIN | log_loss <= 0.2 | 0.50 | 1/4/3 | 0/0 | 15/13;13/13;22/19;13/13;14/14;19/18;15/15;21/23 | NO CLEAR DIFFERENCE (DEV) |
| A3_SEL_COV − A1_MARGIN | BA >= 0.93 | 1.50 | 2/3/3 | 0/0 | 19/13;13/13;14/32;24/15;13/14;17/17;32/16;22/22 | NO CLEAR DIFFERENCE (DEV) |
| A3_SEL_COV − A1_MARGIN | BA >= 0.95 | 17.12 | 1/1/6 | 5/1 | –/35;–/43;–/–;40/44;59/35;–/35;56/35;–/47 | MORE SIMULATIONS (DEV) |
| A3_SEL_COV − A1_MARGIN | log_loss <= 0.2 | 1.00 | 2/0/6 | 0/0 | 17/13;15/13;14/19;18/13;16/14;19/18;19/15;18/23 | NO CLEAR DIFFERENCE (DEV) |
| A4_MAXIMIN − A1_MARGIN | BA >= 0.93 | 3.00 | 3/0/5 | 0/0 | 32/13;14/13;31/32;17/15;13/14;16/17;17/16;26/22 | NO CLEAR DIFFERENCE (DEV) |
| A4_MAXIMIN − A1_MARGIN | BA >= 0.95 | 12.25 | 1/2/5 | 5/1 | –/35;43/43;–/–;–/44;45/35;28/35;–/35;–/47 | NO CLEAR DIFFERENCE (DEV) |
| A4_MAXIMIN − A1_MARGIN | log_loss <= 0.2 | 2.12 | 3/1/4 | 0/0 | 27/13;14/13;16/19;18/13;14/14;17/18;17/15;22/23 | NO CLEAR DIFFERENCE (DEV) |
| A5_SIMPLE − A1_MARGIN | BA >= 0.93 | -2.00 | 4/0/4 | 0/0 | 15/13;14/13;16/32;19/15;13/14;13/17;19/16;17/22 | NO CLEAR DIFFERENCE (DEV) |
| A5_SIMPLE − A1_MARGIN | BA >= 0.95 | -8.00 | 6/2/0 | 0/1 | 34/35;33/43;57/–;28/44;35/35;23/35;35/35;29/47 | FEWER SIMULATIONS (DEV) |
| A5_SIMPLE − A1_MARGIN | log_loss <= 0.2 | -0.62 | 3/1/4 | 0/0 | 15/13;15/13;13/19;15/13;14/14;15/18;17/15;19/23 | NO CLEAR DIFFERENCE (DEV) |

## Individual learners: confirmed own-fold BA ≥ 0.93 by B60

| arm | learners | defined | attained | spend_mean_attainers | spend_median_attainers |
|---|---|---|---|---|---|
| A1_MARGIN | 40 | 40 | 40 | 16.85 | 13.50 |
| A2_MARGIN_COV | 40 | 40 | 39 | 18.67 | 13.00 |
| A3_SEL_COV | 40 | 40 | 35 | 16.80 | 13.00 |
| A4_MAXIMIN | 40 | 40 | 38 | 19.37 | 15.00 |
| A5_SIMPLE | 40 | 40 | 40 | 15.60 | 13.00 |

## Discovery vs learning (evaluator-defined corner VX > 0.85 m/s, P > 330 W; never used by any policy) and selection CPU

| arm | first_corner_query | first_corner_conduction_hit | corner_share_B24 | corner_share_B60 | coverage_queries | cpu_s_per_step |
|---|---|---|---|---|---|---|
| A1_MARGIN | 3.50 | 9.50 | 0.24 | 0.40 | 0.00 | 0.47 |
| A2_MARGIN_COV | 3.50 | 9.50 | 0.19 | 0.30 | 10.00 | 0.45 |
| A3_SEL_COV | 3.50 | 9.50 | 0.16 | 0.20 | 10.00 | 0.43 |
| A4_MAXIMIN | 3.50 | 8.50 | 0.11 | 0.07 | 0.00 | 0.50 |
| A5_SIMPLE | 3.50 | 11.00 | 0.26 | 0.42 | 0.00 | 0.49 |

## Matched budgets (fold-pooled, mean over repeats)

| arm | budget | BA | sensitivity | specificity | log_loss | spec_NEW | q20_BA | corner_cond_errors | corner_key_errors |
|---|---|---|---|---|---|---|---|---|---|
| A1_MARGIN | 8 | 0.879 | 0.865 | 0.894 | 0.292 | 0.188 | 0.670 | 12.500 | 3.750 |
| A1_MARGIN | 12 | 0.925 | 0.911 | 0.938 | 0.204 | 0.177 | 0.717 | 12.000 | 3.625 |
| A1_MARGIN | 16 | 0.937 | 0.927 | 0.947 | 0.177 | 0.115 | 0.734 | 13.125 | 3.250 |
| A1_MARGIN | 20 | 0.937 | 0.924 | 0.951 | 0.162 | 0.146 | 0.742 | 12.375 | 3.125 |
| A1_MARGIN | 24 | 0.938 | 0.924 | 0.952 | 0.156 | 0.198 | 0.747 | 11.125 | 3.875 |
| A1_MARGIN | 32 | 0.948 | 0.944 | 0.951 | 0.140 | 0.229 | 0.764 | 10.750 | 2.125 |
| A1_MARGIN | 40 | 0.952 | 0.948 | 0.956 | 0.126 | 0.229 | 0.777 | 10.250 | 2.125 |
| A1_MARGIN | 60 | 0.953 | 0.946 | 0.961 | 0.119 | 0.323 | 0.785 | 9.125 | 3.000 |
| A2_MARGIN_COV | 8 | 0.879 | 0.865 | 0.894 | 0.292 | 0.188 | 0.670 | 12.500 | 3.750 |
| A2_MARGIN_COV | 12 | 0.925 | 0.911 | 0.938 | 0.204 | 0.177 | 0.717 | 12.000 | 3.625 |
| A2_MARGIN_COV | 16 | 0.929 | 0.921 | 0.936 | 0.189 | 0.135 | 0.715 | 12.750 | 4.375 |
| A2_MARGIN_COV | 20 | 0.937 | 0.928 | 0.947 | 0.165 | 0.146 | 0.742 | 11.750 | 3.750 |
| A2_MARGIN_COV | 24 | 0.940 | 0.931 | 0.949 | 0.156 | 0.177 | 0.745 | 12.125 | 3.000 |
| A2_MARGIN_COV | 32 | 0.948 | 0.940 | 0.955 | 0.141 | 0.188 | 0.768 | 11.750 | 2.625 |
| A2_MARGIN_COV | 40 | 0.952 | 0.947 | 0.956 | 0.128 | 0.208 | 0.776 | 10.750 | 1.500 |
| A2_MARGIN_COV | 60 | 0.954 | 0.949 | 0.959 | 0.118 | 0.250 | 0.785 | 10.000 | 2.500 |
| A3_SEL_COV | 8 | 0.879 | 0.865 | 0.894 | 0.292 | 0.188 | 0.670 | 12.500 | 3.750 |
| A3_SEL_COV | 12 | 0.919 | 0.896 | 0.942 | 0.206 | 0.167 | 0.702 | 12.000 | 4.125 |
| A3_SEL_COV | 16 | 0.924 | 0.900 | 0.948 | 0.179 | 0.177 | 0.711 | 11.500 | 5.125 |
| A3_SEL_COV | 20 | 0.935 | 0.918 | 0.952 | 0.161 | 0.125 | 0.737 | 11.750 | 3.375 |
| A3_SEL_COV | 24 | 0.936 | 0.916 | 0.955 | 0.153 | 0.188 | 0.746 | 10.875 | 3.750 |
| A3_SEL_COV | 32 | 0.938 | 0.914 | 0.962 | 0.154 | 0.260 | 0.758 | 10.000 | 3.750 |
| A3_SEL_COV | 40 | 0.941 | 0.917 | 0.966 | 0.144 | 0.375 | 0.774 | 8.375 | 4.000 |
| A3_SEL_COV | 60 | 0.944 | 0.921 | 0.966 | 0.130 | 0.406 | 0.779 | 8.000 | 5.250 |
| A4_MAXIMIN | 8 | 0.879 | 0.865 | 0.894 | 0.292 | 0.188 | 0.670 | 12.500 | 3.750 |
| A4_MAXIMIN | 12 | 0.919 | 0.903 | 0.934 | 0.207 | 0.208 | 0.702 | 11.375 | 4.625 |
| A4_MAXIMIN | 16 | 0.933 | 0.918 | 0.948 | 0.180 | 0.188 | 0.739 | 11.875 | 2.750 |
| A4_MAXIMIN | 20 | 0.928 | 0.912 | 0.944 | 0.179 | 0.188 | 0.717 | 11.625 | 4.750 |
| A4_MAXIMIN | 24 | 0.933 | 0.918 | 0.949 | 0.172 | 0.292 | 0.734 | 10.250 | 4.000 |
| A4_MAXIMIN | 32 | 0.943 | 0.938 | 0.949 | 0.161 | 0.188 | 0.758 | 11.250 | 2.250 |
| A4_MAXIMIN | 40 | 0.945 | 0.943 | 0.947 | 0.156 | 0.135 | 0.758 | 12.375 | 1.375 |
| A4_MAXIMIN | 60 | 0.948 | 0.945 | 0.952 | 0.149 | 0.125 | 0.767 | 12.250 | 1.125 |
| A5_SIMPLE | 8 | 0.899 | 0.905 | 0.893 | 0.272 | 0.167 | 0.671 | 12.750 | 3.625 |
| A5_SIMPLE | 12 | 0.928 | 0.914 | 0.941 | 0.193 | 0.198 | 0.732 | 11.500 | 4.625 |
| A5_SIMPLE | 16 | 0.940 | 0.934 | 0.945 | 0.164 | 0.198 | 0.745 | 11.375 | 3.875 |
| A5_SIMPLE | 20 | 0.944 | 0.937 | 0.952 | 0.154 | 0.188 | 0.754 | 11.125 | 3.000 |
| A5_SIMPLE | 24 | 0.945 | 0.939 | 0.951 | 0.151 | 0.208 | 0.763 | 10.750 | 2.000 |
| A5_SIMPLE | 32 | 0.951 | 0.947 | 0.955 | 0.136 | 0.250 | 0.774 | 10.375 | 1.875 |
| A5_SIMPLE | 40 | 0.954 | 0.949 | 0.958 | 0.128 | 0.250 | 0.786 | 10.125 | 1.500 |
| A5_SIMPLE | 60 | 0.953 | 0.946 | 0.961 | 0.120 | 0.312 | 0.786 | 9.375 | 2.750 |

Export acceptance: {"cells": 2120, "cells_table": 2120, "BA": 0.0, "log_loss": 0.0, "sensitivity": 0.0, "specificity": 0.0, "brier": 0.0, "PASS": true}

