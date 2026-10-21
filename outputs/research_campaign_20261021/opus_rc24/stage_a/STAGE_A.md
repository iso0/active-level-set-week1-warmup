# RC24 Stage A — strong comparisons (fresh DEV repeats 59–66, 40 tasks per arm)

Own-query units 240; matched units 240; matched reproduction of own-path probabilities: max |Δ| = 0.0 (3920 checks).

## Fold-pooled AULC, own query (mean and SE over 8 repeats)

B8–B24:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se | brier_mean | brier_se | AUC_mean | AUC_se | BA_hard_group_mean | BA_hard_group_se | q20_BA_mean | q20_BA_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1S | 0.9115 | 0.0037 | 0.9117 | 0.0107 | 0.9113 | 0.0098 | 0.3005 | 0.0176 | 0.0732 | 0.0034 | 0.9595 | 0.0036 | 0.5291 | 0.0311 | 0.7068 | 0.0068 |
| E1S_RAW | 0.9173 | 0.0037 | 0.9430 | 0.0088 | 0.8915 | 0.0114 | 0.3715 | 0.0271 | 0.0727 | 0.0044 | 0.9689 | 0.0030 | 0.5436 | 0.0301 | 0.7073 | 0.0093 |
| G3_MARGIN | 0.9002 | 0.0034 | 0.8686 | 0.0077 | 0.9319 | 0.0066 | 0.3690 | 0.0066 | 0.1041 | 0.0025 | 0.9282 | 0.0045 | 0.5103 | 0.0295 | 0.7053 | 0.0079 |
| HA_LEAN_MARGIN | 0.9360 | 0.0028 | 0.9301 | 0.0066 | 0.9419 | 0.0015 | 0.1732 | 0.0037 | 0.0482 | 0.0012 | 0.9823 | 0.0011 | 0.5164 | 0.0136 | 0.7367 | 0.0057 |
| HA_LEAN_STRADDLE | 0.9235 | 0.0077 | 0.9186 | 0.0170 | 0.9284 | 0.0041 | 0.2097 | 0.0075 | 0.0586 | 0.0031 | 0.9781 | 0.0031 | 0.4898 | 0.0195 | 0.7101 | 0.0133 |
| HONLY_MARGIN | 0.9422 | 0.0023 | 0.9448 | 0.0059 | 0.9397 | 0.0024 | 0.1825 | 0.0054 | 0.0491 | 0.0015 | 0.9834 | 0.0011 | 0.4968 | 0.0060 | 0.7439 | 0.0034 |
| M3_MARGIN | 0.9391 | 0.0036 | 0.9385 | 0.0076 | 0.9398 | 0.0020 | 0.4734 | 0.0314 | 0.0557 | 0.0024 | 0.9652 | 0.0030 | 0.4849 | 0.0186 | 0.7390 | 0.0070 |

B8–B60:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se | brier_mean | brier_se | AUC_mean | AUC_se | BA_hard_group_mean | BA_hard_group_se | q20_BA_mean | q20_BA_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1S | 0.9344 | 0.0016 | 0.9298 | 0.0054 | 0.9391 | 0.0042 | 0.2017 | 0.0077 | 0.0512 | 0.0014 | 0.9771 | 0.0013 | 0.5641 | 0.0185 | 0.7470 | 0.0051 |
| E1S_RAW | 0.9403 | 0.0015 | 0.9530 | 0.0040 | 0.9276 | 0.0047 | 0.2388 | 0.0116 | 0.0508 | 0.0017 | 0.9818 | 0.0011 | 0.5960 | 0.0170 | 0.7528 | 0.0059 |
| G3_MARGIN | 0.9289 | 0.0029 | 0.9111 | 0.0059 | 0.9467 | 0.0035 | 0.2686 | 0.0075 | 0.0713 | 0.0025 | 0.9623 | 0.0032 | 0.5275 | 0.0282 | 0.7388 | 0.0080 |
| HA_LEAN_MARGIN | 0.9467 | 0.0018 | 0.9408 | 0.0034 | 0.9526 | 0.0012 | 0.1417 | 0.0023 | 0.0395 | 0.0008 | 0.9871 | 0.0005 | 0.5678 | 0.0084 | 0.7632 | 0.0048 |
| HA_LEAN_STRADDLE | 0.9372 | 0.0044 | 0.9330 | 0.0093 | 0.9414 | 0.0020 | 0.1709 | 0.0044 | 0.0474 | 0.0017 | 0.9841 | 0.0014 | 0.5124 | 0.0135 | 0.7380 | 0.0086 |
| HONLY_MARGIN | 0.9451 | 0.0013 | 0.9431 | 0.0026 | 0.9471 | 0.0006 | 0.1651 | 0.0041 | 0.0450 | 0.0010 | 0.9846 | 0.0007 | 0.4989 | 0.0020 | 0.7532 | 0.0029 |
| M3_MARGIN | 0.9443 | 0.0016 | 0.9383 | 0.0032 | 0.9502 | 0.0008 | 0.2663 | 0.0114 | 0.0469 | 0.0014 | 0.9795 | 0.0011 | 0.5080 | 0.0122 | 0.7550 | 0.0038 |

## Individual learners (AULC averaged over 40 learners)

B8–B24:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se |
|---|---|---|---|---|---|---|---|---|
| E1S | 0.9116 | 0.0061 | 0.9127 | 0.0132 | 0.9105 | 0.0093 | 0.3005 | 0.0186 |
| E1S_RAW | 0.9168 | 0.0059 | 0.9431 | 0.0104 | 0.8905 | 0.0114 | 0.3716 | 0.0332 |
| G3_MARGIN | 0.9003 | 0.0051 | 0.8690 | 0.0101 | 0.9317 | 0.0061 | 0.3690 | 0.0066 |
| HA_LEAN_MARGIN | 0.9356 | 0.0039 | 0.9298 | 0.0092 | 0.9415 | 0.0048 | 0.1731 | 0.0071 |
| HA_LEAN_STRADDLE | 0.9237 | 0.0084 | 0.9193 | 0.0193 | 0.9281 | 0.0070 | 0.2096 | 0.0094 |
| HONLY_MARGIN | 0.9418 | 0.0038 | 0.9444 | 0.0081 | 0.9393 | 0.0044 | 0.1824 | 0.0083 |
| M3_MARGIN | 0.9390 | 0.0046 | 0.9386 | 0.0107 | 0.9394 | 0.0050 | 0.4732 | 0.0372 |

B8–B60:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se |
|---|---|---|---|---|---|---|---|---|
| E1S | 0.9344 | 0.0036 | 0.9301 | 0.0078 | 0.9386 | 0.0052 | 0.2016 | 0.0100 |
| E1S_RAW | 0.9400 | 0.0034 | 0.9529 | 0.0060 | 0.9270 | 0.0062 | 0.2388 | 0.0181 |
| G3_MARGIN | 0.9288 | 0.0035 | 0.9108 | 0.0068 | 0.9467 | 0.0038 | 0.2686 | 0.0078 |
| HA_LEAN_MARGIN | 0.9466 | 0.0031 | 0.9409 | 0.0064 | 0.9524 | 0.0041 | 0.1417 | 0.0061 |
| HA_LEAN_STRADDLE | 0.9373 | 0.0052 | 0.9333 | 0.0119 | 0.9413 | 0.0050 | 0.1709 | 0.0065 |
| HONLY_MARGIN | 0.9448 | 0.0031 | 0.9427 | 0.0062 | 0.9468 | 0.0037 | 0.1651 | 0.0069 |
| M3_MARGIN | 0.9440 | 0.0029 | 0.9381 | 0.0061 | 0.9500 | 0.0040 | 0.2663 | 0.0145 |

## Contrasts against HA_LEAN + margin (RC23 D1)

| comparator | window | contrast | metric | direction | margin | mean | se | min | max | good | verdict | lower_95 | observed_both_attained | attained | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0062 | 0.0017 | -0.0001 | 0.0134 | 7/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0093 | 0.0033 | -0.0090 | 0.0174 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0147 | 0.0047 | 0.0009 | 0.0367 | 8/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0022 | 0.0024 | -0.0123 | 0.0077 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0062 | – | – | – | 7/8 | PASS | 0.0030 | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0016 | 0.0013 | -0.0072 | 0.0019 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0234 | 0.0034 | 0.0081 | 0.0363 | 0/8 | WORSE (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0023 | 0.0025 | -0.0079 | 0.0146 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0055 | 0.0013 | -0.0113 | -0.0002 | 0/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0016 | – | – | – | 4/8 | PASS | -0.0041 | – | – | – |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.90 | – | – | -0.2500 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -0.2500 | 8/8 | PASS |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.93 | – | – | -1.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -1.0000 | 8/8 | PASS |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.95 | – | – | 6.1250 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -2.0000 | 5/7 | PASS |
| M3_MARGIN | small | M3_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0031 | 0.0022 | -0.0056 | 0.0135 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| M3_MARGIN | small | M3_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.3003 | 0.0317 | 0.1783 | 0.4254 | 0/8 | WORSE (DEV) | – | – | – | – |
| M3_MARGIN | small | M3_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0084 | 0.0044 | -0.0063 | 0.0269 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| M3_MARGIN | small | M3_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0021 | 0.0015 | -0.0099 | 0.0041 | 3/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| M3_MARGIN | small | M3_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0031 | – | – | – | 5/8 | PASS | -0.0010 | – | – | – |
| M3_MARGIN | all | M3_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0024 | 0.0009 | -0.0063 | 0.0009 | 2/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| M3_MARGIN | all | M3_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.1247 | 0.0119 | 0.0680 | 0.1680 | 0/8 | WORSE (DEV) | – | – | – | – |
| M3_MARGIN | all | M3_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | -0.0025 | 0.0021 | -0.0117 | 0.0059 | 3/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| M3_MARGIN | all | M3_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0023 | 0.0010 | -0.0056 | 0.0030 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| M3_MARGIN | all | M3_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0024 | – | – | – | 2/8 | PASS | -0.0041 | – | – | – |
| M3_MARGIN | endpoint | M3_MARGIN − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| M3_MARGIN | endpoint | M3_MARGIN − HA_LEAN_MARGIN | BA >= 0.90 | – | – | -0.3750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -0.3750 | 8/8 | PASS |
| M3_MARGIN | endpoint | M3_MARGIN − HA_LEAN_MARGIN | BA >= 0.93 | – | – | 1.2500 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 1.2500 | 8/8 | PASS |
| M3_MARGIN | endpoint | M3_MARGIN − HA_LEAN_MARGIN | BA >= 0.95 | – | – | -4.3750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -5.0000 | 7/7 | PASS |
| E1S | small | E1S − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0245 | 0.0032 | -0.0347 | -0.0124 | 0/8 | WORSE (DEV) | – | – | – | – |
| E1S | small | E1S − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.1273 | 0.0165 | 0.0645 | 0.1983 | 0/8 | WORSE (DEV) | – | – | – | – |
| E1S | small | E1S − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | -0.0184 | 0.0062 | -0.0385 | 0.0078 | 2/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| E1S | small | E1S − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0307 | 0.0089 | -0.0754 | -0.0029 | 0/8 | WORSE (DEV) | – | – | – | – |
| E1S | small | E1S − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0245 | – | – | – | 0/8 | FAIL | -0.0306 | – | – | – |
| E1S | all | E1S − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0122 | 0.0018 | -0.0235 | -0.0080 | 0/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| E1S | all | E1S − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0600 | 0.0070 | 0.0371 | 0.0889 | 0/8 | WORSE (DEV) | – | – | – | – |
| E1S | all | E1S − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | -0.0110 | 0.0047 | -0.0293 | 0.0177 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| E1S | all | E1S − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0135 | 0.0037 | -0.0337 | -0.0042 | 0/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| E1S | all | E1S − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0122 | – | – | – | 0/8 | FAIL | -0.0157 | – | – | – |
| E1S | endpoint | E1S − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.1250 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.1250 | 8/8 | PASS |
| E1S | endpoint | E1S − HA_LEAN_MARGIN | BA >= 0.90 | – | – | 2.0000 | – | – | – | – | MORE SIMULATIONS (DEV) | – | 2.0000 | 8/8 | FAIL |
| E1S | endpoint | E1S − HA_LEAN_MARGIN | BA >= 0.93 | – | – | 8.2500 | – | – | – | – | MORE SIMULATIONS (DEV) | – | 8.2500 | 8/8 | FAIL |
| E1S | endpoint | E1S − HA_LEAN_MARGIN | BA >= 0.95 | – | – | 4.2500 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 4.8571 | 7/7 | PASS |
| G3_MARGIN | small | G3_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0357 | 0.0033 | -0.0496 | -0.0243 | 0/8 | WORSE (DEV) | – | – | – | – |
| G3_MARGIN | small | G3_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.1958 | 0.0073 | 0.1756 | 0.2385 | 0/8 | WORSE (DEV) | – | – | – | – |
| G3_MARGIN | small | G3_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | -0.0615 | 0.0035 | -0.0845 | -0.0534 | 0/8 | WORSE (DEV) | – | – | – | – |
| G3_MARGIN | small | G3_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0100 | 0.0060 | -0.0371 | 0.0103 | 2/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| G3_MARGIN | small | G3_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0357 | – | – | – | 0/8 | FAIL | -0.0419 | – | – | – |
| G3_MARGIN | all | G3_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0178 | 0.0026 | -0.0329 | -0.0117 | 0/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| G3_MARGIN | all | G3_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.1269 | 0.0076 | 0.1026 | 0.1675 | 0/8 | WORSE (DEV) | – | – | – | – |
| G3_MARGIN | all | G3_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | -0.0297 | 0.0042 | -0.0538 | -0.0125 | 0/8 | WORSE (DEV) | – | – | – | – |
| G3_MARGIN | all | G3_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0058 | 0.0031 | -0.0217 | 0.0029 | 2/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| G3_MARGIN | all | G3_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0178 | – | – | – | 0/8 | FAIL | -0.0227 | – | – | – |
| G3_MARGIN | endpoint | G3_MARGIN − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| G3_MARGIN | endpoint | G3_MARGIN − HA_LEAN_MARGIN | BA >= 0.90 | – | – | 3.7500 | – | – | – | – | MORE SIMULATIONS (DEV) | – | 3.7500 | 8/8 | FAIL |
| G3_MARGIN | endpoint | G3_MARGIN − HA_LEAN_MARGIN | BA >= 0.93 | – | – | 15.1250 | – | – | – | – | MORE SIMULATIONS (DEV) | – | 15.1250 | 8/8 | FAIL |
| G3_MARGIN | endpoint | G3_MARGIN − HA_LEAN_MARGIN | BA >= 0.95 | – | – | 8.8750 | – | – | – | – | MORE SIMULATIONS (DEV) | – | 9.5000 | 6/7 | FAIL |
| HA_LEAN_STRADDLE | small | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0125 | 0.0062 | -0.0534 | 0.0017 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_LEAN_STRADDLE | small | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0365 | 0.0068 | 0.0214 | 0.0775 | 0/8 | WORSE (DEV) | – | – | – | – |
| HA_LEAN_STRADDLE | small | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | -0.0115 | 0.0122 | -0.0953 | 0.0084 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_LEAN_STRADDLE | small | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0136 | 0.0033 | -0.0268 | 0.0019 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_LEAN_STRADDLE | small | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0125 | – | – | – | 1/8 | FAIL | -0.0242 | – | – | – |
| HA_LEAN_STRADDLE | all | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0095 | 0.0040 | -0.0356 | -0.0003 | 0/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_LEAN_STRADDLE | all | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0293 | 0.0040 | 0.0193 | 0.0553 | 0/8 | WORSE (DEV) | – | – | – | – |
| HA_LEAN_STRADDLE | all | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | -0.0078 | 0.0076 | -0.0581 | 0.0159 | 2/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_LEAN_STRADDLE | all | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0111 | 0.0024 | -0.0214 | -0.0020 | 0/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_LEAN_STRADDLE | all | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0095 | – | – | – | 0/8 | FAIL | -0.0170 | – | – | – |
| HA_LEAN_STRADDLE | endpoint | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HA_LEAN_STRADDLE | endpoint | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | BA >= 0.90 | – | – | 3.3750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 3.3750 | 8/8 | PASS |
| HA_LEAN_STRADDLE | endpoint | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | BA >= 0.93 | – | – | 5.6250 | – | – | – | – | MORE SIMULATIONS (DEV) | – | 5.6250 | 8/8 | FAIL |
| HA_LEAN_STRADDLE | endpoint | HA_LEAN_STRADDLE − HA_LEAN_MARGIN | BA >= 0.95 | – | – | 11.5000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 11.0000 | 5/7 | PASS |
| E1S_RAW | small | E1S_RAW − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0187 | 0.0050 | -0.0375 | 0.0024 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| E1S_RAW | small | E1S_RAW − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.1984 | 0.0273 | 0.1000 | 0.3391 | 0/8 | WORSE (DEV) | – | – | – | – |
| E1S_RAW | small | E1S_RAW − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0129 | 0.0071 | -0.0170 | 0.0406 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| E1S_RAW | small | E1S_RAW − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0504 | 0.0102 | -0.1021 | -0.0227 | 0/8 | WORSE (DEV) | – | – | – | – |
| E1S_RAW | small | E1S_RAW − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0187 | – | – | – | 1/8 | FAIL | -0.0283 | – | – | – |
| E1S_RAW | all | E1S_RAW − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0063 | 0.0027 | -0.0206 | 0.0045 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| E1S_RAW | all | E1S_RAW − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0971 | 0.0118 | 0.0593 | 0.1606 | 0/8 | WORSE (DEV) | – | – | – | – |
| E1S_RAW | all | E1S_RAW − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0122 | 0.0051 | -0.0130 | 0.0314 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| E1S_RAW | all | E1S_RAW − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0249 | 0.0040 | -0.0475 | -0.0149 | 0/8 | WORSE (DEV) | – | – | – | – |
| E1S_RAW | all | E1S_RAW − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0063 | – | – | – | 1/8 | FAIL | -0.0114 | – | – | – |
| E1S_RAW | endpoint | E1S_RAW − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| E1S_RAW | endpoint | E1S_RAW − HA_LEAN_MARGIN | BA >= 0.90 | – | – | 2.5000 | – | – | – | – | MORE SIMULATIONS (DEV) | – | 2.5000 | 8/8 | FAIL |
| E1S_RAW | endpoint | E1S_RAW − HA_LEAN_MARGIN | BA >= 0.93 | – | – | 7.7500 | – | – | – | – | MORE SIMULATIONS (DEV) | – | 7.7500 | 8/8 | FAIL |
| E1S_RAW | endpoint | E1S_RAW − HA_LEAN_MARGIN | BA >= 0.95 | – | – | -6.7500 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -2.5714 | 8/7 | PASS |

## Target attainment (fold-pooled)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | E1S | 8 | 8 | 8 | 8.000 | 7 | 12.125 | 12.000 | 0.995 |
| BA >= 0.80 | E1S_RAW | 8 | 8 | 8 | 8.000 | 8 | 12.000 | 12.000 | 1.000 |
| BA >= 0.80 | G3_MARGIN | 8 | 8 | 8 | 8.000 | 8 | 12.000 | 12.000 | 0.993 |
| BA >= 0.80 | HA_LEAN_MARGIN | 8 | 8 | 8 | 8.000 | 8 | 12.000 | 12.000 | 1.000 |
| BA >= 0.80 | HA_LEAN_STRADDLE | 8 | 8 | 8 | 8.000 | 8 | 12.000 | 12.000 | 1.000 |
| BA >= 0.80 | HONLY_MARGIN | 8 | 8 | 8 | 8.000 | 8 | 12.000 | 12.000 | 1.000 |
| BA >= 0.80 | M3_MARGIN | 8 | 8 | 8 | 8.000 | 8 | 12.000 | 12.000 | 1.000 |
| BA >= 0.90 | E1S | 8 | 8 | 8 | 10.500 | 2 | 14.625 | 15.000 | 0.978 |
| BA >= 0.90 | E1S_RAW | 8 | 8 | 8 | 10.500 | 3 | 15.125 | 15.000 | 0.983 |
| BA >= 0.90 | G3_MARGIN | 8 | 8 | 8 | 10.000 | 1 | 16.375 | 16.500 | 0.944 |
| BA >= 0.90 | HA_LEAN_MARGIN | 8 | 8 | 8 | 8.000 | 5 | 12.625 | 12.000 | 1.000 |
| BA >= 0.90 | HA_LEAN_STRADDLE | 8 | 8 | 8 | 8.000 | 5 | 16.000 | 12.000 | 0.995 |
| BA >= 0.90 | HONLY_MARGIN | 8 | 8 | 8 | 8.000 | 7 | 12.375 | 12.000 | 0.998 |
| BA >= 0.90 | M3_MARGIN | 8 | 8 | 8 | 8.000 | 6 | 12.250 | 12.000 | 0.995 |
| BA >= 0.93 | E1S | 8 | 8 | 8 | 17.000 | 0 | 22.750 | 21.000 | 0.943 |
| BA >= 0.93 | E1S_RAW | 8 | 8 | 8 | 17.000 | 0 | 22.250 | 21.500 | 0.979 |
| BA >= 0.93 | G3_MARGIN | 8 | 8 | 8 | 22.500 | 0 | 29.625 | 26.500 | 0.956 |
| BA >= 0.93 | HA_LEAN_MARGIN | 8 | 8 | 8 | 10.000 | 2 | 14.500 | 14.000 | 0.973 |
| BA >= 0.93 | HA_LEAN_STRADDLE | 8 | 8 | 8 | 14.000 | 2 | 20.125 | 18.000 | 0.950 |
| BA >= 0.93 | HONLY_MARGIN | 8 | 8 | 8 | 8.500 | 4 | 13.500 | 12.500 | 0.998 |
| BA >= 0.93 | M3_MARGIN | 8 | 8 | 8 | 8.500 | 4 | 15.750 | 12.500 | 0.989 |
| BA >= 0.95 | E1S | 8 | 8 | 7 | 26.500 | 0 | 40.429 | 37.000 | 0.609 |
| BA >= 0.95 | E1S_RAW | 8 | 8 | 8 | 25.000 | 0 | 32.000 | 30.500 | 0.689 |
| BA >= 0.95 | G3_MARGIN | 8 | 8 | 6 | 36.000 | 0 | 43.167 | 44.000 | 0.772 |
| BA >= 0.95 | HA_LEAN_MARGIN | 8 | 8 | 7 | 16.000 | 0 | 35.571 | 38.000 | 0.906 |
| BA >= 0.95 | HA_LEAN_STRADDLE | 8 | 8 | 5 | 32.000 | 0 | 43.800 | 42.000 | 0.810 |
| BA >= 0.95 | HONLY_MARGIN | 8 | 8 | 5 | 18.500 | 0 | 35.200 | 29.000 | 0.365 |
| BA >= 0.95 | M3_MARGIN | 8 | 8 | 7 | 17.000 | 0 | 30.571 | 34.000 | 0.407 |

## Target attainment (individual learners)

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | E1S | 40 | 40 | 40 | 8.000 | 36 | 12.300 | 12.000 | 0.992 |
| BA >= 0.80 | E1S_RAW | 40 | 40 | 40 | 8.000 | 35 | 12.350 | 12.000 | 0.996 |
| BA >= 0.80 | G3_MARGIN | 40 | 40 | 40 | 8.000 | 33 | 12.525 | 12.000 | 0.989 |
| BA >= 0.80 | HA_LEAN_MARGIN | 40 | 40 | 40 | 8.000 | 38 | 12.100 | 12.000 | 1.000 |
| BA >= 0.80 | HA_LEAN_STRADDLE | 40 | 40 | 40 | 8.000 | 38 | 12.750 | 12.000 | 0.999 |
| BA >= 0.80 | HONLY_MARGIN | 40 | 40 | 40 | 8.000 | 38 | 12.100 | 12.000 | 0.999 |
| BA >= 0.80 | M3_MARGIN | 40 | 40 | 40 | 8.000 | 38 | 12.200 | 12.000 | 0.999 |
| BA >= 0.90 | E1S | 40 | 40 | 40 | 8.000 | 22 | 15.950 | 13.500 | 0.940 |
| BA >= 0.90 | E1S_RAW | 40 | 40 | 40 | 8.000 | 21 | 16.200 | 13.000 | 0.982 |
| BA >= 0.90 | G3_MARGIN | 40 | 40 | 39 | 9.000 | 18 | 17.103 | 14.000 | 0.929 |
| BA >= 0.90 | HA_LEAN_MARGIN | 40 | 40 | 40 | 8.000 | 29 | 13.275 | 12.000 | 0.966 |
| BA >= 0.90 | HA_LEAN_STRADDLE | 40 | 40 | 40 | 8.000 | 29 | 13.625 | 12.000 | 0.944 |
| BA >= 0.90 | HONLY_MARGIN | 40 | 40 | 39 | 8.000 | 33 | 12.359 | 12.000 | 0.995 |
| BA >= 0.90 | M3_MARGIN | 40 | 40 | 39 | 8.000 | 35 | 12.923 | 12.000 | 0.989 |
| BA >= 0.93 | E1S | 40 | 40 | 39 | 11.000 | 9 | 20.487 | 18.000 | 0.801 |
| BA >= 0.93 | E1S_RAW | 40 | 40 | 39 | 10.500 | 10 | 20.154 | 18.000 | 0.866 |
| BA >= 0.93 | G3_MARGIN | 40 | 40 | 34 | 14.000 | 7 | 25.765 | 24.500 | 0.930 |
| BA >= 0.93 | HA_LEAN_MARGIN | 40 | 40 | 38 | 9.000 | 19 | 16.447 | 13.000 | 0.913 |
| BA >= 0.93 | HA_LEAN_STRADDLE | 40 | 40 | 38 | 9.000 | 19 | 19.132 | 15.000 | 0.842 |
| BA >= 0.93 | HONLY_MARGIN | 40 | 40 | 37 | 8.000 | 26 | 13.243 | 12.000 | 0.908 |
| BA >= 0.93 | M3_MARGIN | 40 | 40 | 39 | 8.000 | 23 | 15.615 | 12.000 | 0.908 |
| BA >= 0.95 | E1S | 40 | 40 | 30 | 16.500 | 5 | 24.000 | 24.000 | 0.644 |
| BA >= 0.95 | E1S_RAW | 40 | 40 | 32 | 14.500 | 6 | 22.844 | 21.500 | 0.726 |
| BA >= 0.95 | G3_MARGIN | 40 | 40 | 23 | 25.000 | 1 | 28.826 | 29.000 | 0.832 |
| BA >= 0.95 | HA_LEAN_MARGIN | 40 | 40 | 31 | 11.000 | 4 | 23.129 | 19.000 | 0.811 |
| BA >= 0.95 | HA_LEAN_STRADDLE | 40 | 40 | 28 | 14.000 | 4 | 28.071 | 21.000 | 0.827 |
| BA >= 0.95 | HONLY_MARGIN | 40 | 40 | 27 | 9.000 | 13 | 15.519 | 13.000 | 0.736 |
| BA >= 0.95 | M3_MARGIN | 40 | 40 | 32 | 9.000 | 10 | 20.188 | 14.000 | 0.713 |

## Pre-registered decisions

- **Q1 (h alone sufficient?)** H-ONLY NOT SUFFICIENT (DEV) — {"noninferiority": ["PASS", "PASS"], "spend_BA_0.95": {"window": "endpoint", "contrast": "HONLY_MARGIN \u2212 HA_LEAN_MARGIN", "metric": "BA >= 0.95", "mean": 6.125, "observed_both_attained": -2.0, "attained": "5/7", "verdict": "NO CLEAR DIFFERENCE (DEV)", "status": "PASS"}, "attained_0.95": {"HONLY_MARGIN": 5, "HA_LEAN_MARGIN": 7}}
- **Q2 M3_MARGIN** SIMILAR (non-inferior, DEV) — {"BA_verdicts": ["NOT DIFFERENT (DEV)", "NOT DIFFERENT (DEV)"], "noninferiority": ["PASS", "PASS"]}
- **Q2 E1S** WORSE (DEV) — {"BA_verdicts": ["WORSE (DEV)", "NOT DIFFERENT (DEV)"], "noninferiority": ["FAIL", "FAIL"]}
- **Q2 G3_MARGIN** WORSE (DEV) — {"BA_verdicts": ["WORSE (DEV)", "NOT DIFFERENT (DEV)"], "noninferiority": ["FAIL", "FAIL"]}
- **Q2 E1S_RAW** NON-INFERIORITY NOT SHOWN (DEV) — {"BA_verdicts": ["NOT DIFFERENT (DEV)", "NOT DIFFERENT (DEV)"], "noninferiority": ["FAIL", "FAIL"]}
- **Q3 (straddle vs margin on HA_LEAN)** NON-INFERIORITY NOT SHOWN (DEV) — {"BA_verdicts": ["NOT DIFFERENT (DEV)", "NOT DIFFERENT (DEV)"], "noninferiority": ["FAIL", "FAIL"]}
- Straddle discriminability audit: {"steps": 2080, "share_choice_differs_from_margin": 0.8605769230769231, "share_numerically_indistinguishable_top2": 0.0, "median_s_at_choice": 1.9593611377646045, "median_abs_eta_at_choice": 1.1166201555322015, "median_s_over_candidates": 1.9200875090259748, "median_share_rows_with_excess_depth_variance": 0.08063030176609651}

## Q4 decomposition (matched matrix, BA-AULC on the step-4 grid)

- HONLY_MARGIN [small]: total +0.0060 = model on X path +0.0041 + path for HA_LEAN +0.0019; model on HA_LEAN path +0.0023, path for X +0.0038, interaction +0.0019
- HONLY_MARGIN [all]: total -0.0015 = model on X path -0.0047 + path for HA_LEAN +0.0032; model on HA_LEAN path -0.0056, path for X +0.0041, interaction +0.0009
- M3_MARGIN [small]: total +0.0036 = model on X path +0.0058 + path for HA_LEAN -0.0022; model on HA_LEAN path +0.0021, path for X +0.0016, interaction +0.0037
- M3_MARGIN [all]: total -0.0021 = model on X path -0.0038 + path for HA_LEAN +0.0016; model on HA_LEAN path -0.0066, path for X +0.0044, interaction +0.0028
- E1S [small]: total -0.0194 = model on X path -0.0184 + path for HA_LEAN -0.0010; model on HA_LEAN path -0.0405, path for X +0.0211, interaction +0.0221
- E1S [all]: total -0.0109 = model on X path -0.0106 + path for HA_LEAN -0.0004; model on HA_LEAN path -0.0180, path for X +0.0071, interaction +0.0074
- G3_MARGIN [small]: total -0.0392 = model on X path -0.0389 + path for HA_LEAN -0.0003; model on HA_LEAN path -0.1282, path for X +0.0890, interaction +0.0893
- G3_MARGIN [all]: total -0.0189 = model on X path -0.0188 + path for HA_LEAN -0.0001; model on HA_LEAN path -0.1262, path for X +0.1072, interaction +0.1074
- HA_LEAN_STRADDLE [small]: total -0.0107 = model on X path +0.0000 + path for HA_LEAN -0.0107; model on HA_LEAN path +0.0000, path for X -0.0107, interaction +0.0000
- HA_LEAN_STRADDLE [all]: total -0.0085 = model on X path +0.0000 + path for HA_LEAN -0.0085; model on HA_LEAN path +0.0000, path for X -0.0085, interaction +0.0000

## Hard region (own query; evaluator-only memberships)

| arm | budget | recall_shortK_NEW | spec_cond_NEW | BA_hard_group | recall_shortK_pooled | corner_cond_errors | corner_key_errors |
|---|---|---|---|---|---|---|---|
| E1S | 24 | 0.762 | 0.365 | 0.564 | 0.739 | 8.625 | 5.500 |
| E1S | 40 | 0.688 | 0.458 | 0.573 | 0.722 | 7.500 | 6.000 |
| E1S | 60 | 0.750 | 0.448 | 0.599 | 0.699 | 7.500 | 5.375 |
| E1S_RAW | 24 | 0.900 | 0.250 | 0.575 | 0.858 | 10.375 | 2.750 |
| E1S_RAW | 40 | 0.912 | 0.417 | 0.665 | 0.864 | 8.000 | 2.625 |
| E1S_RAW | 60 | 0.825 | 0.385 | 0.605 | 0.801 | 8.375 | 4.000 |
| G3_MARGIN | 24 | 0.775 | 0.229 | 0.502 | 0.716 | 11.500 | 4.000 |
| G3_MARGIN | 40 | 0.800 | 0.281 | 0.541 | 0.761 | 9.750 | 3.875 |
| G3_MARGIN | 60 | 0.762 | 0.344 | 0.553 | 0.733 | 9.000 | 4.375 |
| HA_LEAN_MARGIN | 24 | 0.900 | 0.188 | 0.544 | 0.818 | 11.500 | 1.875 |
| HA_LEAN_MARGIN | 40 | 0.912 | 0.292 | 0.602 | 0.807 | 9.500 | 2.375 |
| HA_LEAN_MARGIN | 60 | 0.900 | 0.333 | 0.617 | 0.790 | 9.000 | 2.875 |
| HA_LEAN_STRADDLE | 24 | 0.925 | 0.094 | 0.509 | 0.818 | 13.125 | 2.125 |
| HA_LEAN_STRADDLE | 40 | 0.975 | 0.073 | 0.524 | 0.892 | 12.500 | 0.750 |
| HA_LEAN_STRADDLE | 60 | 0.925 | 0.135 | 0.530 | 0.864 | 11.625 | 1.750 |
| HONLY_MARGIN | 24 | 1.000 | 0.000 | 0.500 | 0.898 | 14.750 | 0.125 |
| HONLY_MARGIN | 40 | 1.000 | 0.000 | 0.500 | 0.881 | 14.250 | 0.500 |
| HONLY_MARGIN | 60 | 1.000 | 0.000 | 0.500 | 0.864 | 13.375 | 0.625 |
| M3_MARGIN | 24 | 1.000 | 0.062 | 0.531 | 0.852 | 13.625 | 0.875 |
| M3_MARGIN | 40 | 0.925 | 0.094 | 0.509 | 0.847 | 11.875 | 1.500 |
| M3_MARGIN | 60 | 0.900 | 0.198 | 0.549 | 0.801 | 10.625 | 1.750 |

## Compute (CPU s per step)

| arm | mean | median |
|---|---|---|
| E1S | 0.591 | 0.603 |
| G3_MARGIN | 0.162 | 0.145 |
| HA_LEAN_MARGIN | 0.239 | 0.246 |
| HA_LEAN_STRADDLE | 0.276 | 0.284 |
| HONLY_MARGIN | 0.008 | 0.008 |
| M3_MARGIN | 0.084 | 0.085 |

