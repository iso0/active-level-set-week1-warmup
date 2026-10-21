# RC24 Stage C — confirmatory test on fresh data (STD repeats 67–74, BLOCK seeds 9–16)

**Primary HA_TREND + margin: CONFIRMED (DEV-confirm)** — {"std_ni_B8_B24": "PASS", "std_ni_B8_B60": "PASS", "std_spend_BA_0.95": "PASS", "block_gain_B8_B60": "PASS"}
Secondary HT_PHYS: CONFIRMED (DEV-confirm) — {"std_ni_B8_B24": "PASS", "std_ni_B8_B60": "PASS", "std_spend_BA_0.95": "PASS", "block_gain_B8_B60": "PASS"}

Against h-only (primary): {"STD_small": {"mean": -0.006012999802092994, "lower_95": -0.010710832788093542, "status": "FAIL"}, "STD_all": {"mean": 0.002102710162084631, "lower_95": -0.0012593697442237046, "status": "PASS"}, "BLOCK_small": {"mean": -0.0026412019033797557, "lower_95": -0.006836846025496718, "status": "PASS"}, "BLOCK_all": {"mean": -0.008211648983323758, "lower_95": -0.0107493137967542, "status": "FAIL"}, "dominates_both_references": false}
Against h-only (secondary): {"STD_small": {"mean": -0.0016613233210885647, "lower_95": -0.003968756915956323, "status": "PASS"}, "STD_all": {"mean": 0.0028093733503651575, "lower_95": -0.0002430304168434677, "status": "PASS"}, "BLOCK_small": {"mean": -0.006775278285083369, "lower_95": -0.011422329538749365, "status": "FAIL"}, "BLOCK_all": {"mean": -0.014316080890852872, "lower_95": -0.01765374068057286, "status": "FAIL"}, "dominates_both_references": false}

## STD

Own-query units 120; matched units 80; matched reproduction of own-path probabilities max |Δ| = 0.0 (4240 checks).

Fold-pooled AULC B8–B24:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se | brier_mean | brier_se | AUC_mean | AUC_se | BA_hard_group_mean | BA_hard_group_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN_MARGIN | 0.9322 | 0.0025 | 0.9232 | 0.0069 | 0.9412 | 0.0034 | 0.1880 | 0.0052 | 0.0517 | 0.0014 | 0.9808 | 0.0011 | 0.5228 | 0.0078 |
| HA_TREND_MARGIN | 0.9356 | 0.0020 | 0.9246 | 0.0076 | 0.9467 | 0.0048 | 0.1859 | 0.0045 | 0.0504 | 0.0013 | 0.9825 | 0.0012 | 0.5127 | 0.0318 |
| HONLY_MARGIN | 0.9416 | 0.0012 | 0.9405 | 0.0036 | 0.9428 | 0.0026 | 0.2023 | 0.0064 | 0.0531 | 0.0016 | 0.9825 | 0.0006 | 0.5047 | 0.0025 |
| HT_PHYS | 0.9400 | 0.0020 | 0.9400 | 0.0046 | 0.9400 | 0.0022 | 0.1924 | 0.0066 | 0.0517 | 0.0019 | 0.9830 | 0.0011 | 0.5125 | 0.0072 |

B8–B60:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se | brier_mean | brier_se | AUC_mean | AUC_se | BA_hard_group_mean | BA_hard_group_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN_MARGIN | 0.9464 | 0.0009 | 0.9397 | 0.0027 | 0.9532 | 0.0015 | 0.1474 | 0.0035 | 0.0404 | 0.0008 | 0.9865 | 0.0007 | 0.5827 | 0.0056 |
| HA_TREND_MARGIN | 0.9472 | 0.0015 | 0.9397 | 0.0049 | 0.9546 | 0.0024 | 0.1486 | 0.0034 | 0.0402 | 0.0008 | 0.9874 | 0.0007 | 0.5620 | 0.0203 |
| HONLY_MARGIN | 0.9451 | 0.0007 | 0.9417 | 0.0014 | 0.9484 | 0.0012 | 0.1767 | 0.0041 | 0.0468 | 0.0009 | 0.9843 | 0.0003 | 0.5022 | 0.0009 |
| HT_PHYS | 0.9479 | 0.0014 | 0.9456 | 0.0034 | 0.9502 | 0.0019 | 0.1511 | 0.0043 | 0.0408 | 0.0012 | 0.9875 | 0.0006 | 0.5523 | 0.0119 |

Individual learners B8–B24:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN_MARGIN | 0.9330 | 0.0034 | 0.9249 | 0.0084 | 0.9410 | 0.0043 | 0.1880 | 0.0068 |
| HA_TREND_MARGIN | 0.9368 | 0.0032 | 0.9268 | 0.0082 | 0.9467 | 0.0045 | 0.1859 | 0.0063 |
| HONLY_MARGIN | 0.9422 | 0.0029 | 0.9420 | 0.0061 | 0.9425 | 0.0042 | 0.2022 | 0.0088 |
| HT_PHYS | 0.9402 | 0.0029 | 0.9407 | 0.0064 | 0.9398 | 0.0041 | 0.1924 | 0.0076 |

B8–B60:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN_MARGIN | 0.9467 | 0.0027 | 0.9402 | 0.0060 | 0.9531 | 0.0032 | 0.1474 | 0.0053 |
| HA_TREND_MARGIN | 0.9477 | 0.0028 | 0.9408 | 0.0067 | 0.9546 | 0.0035 | 0.1486 | 0.0049 |
| HONLY_MARGIN | 0.9461 | 0.0027 | 0.9438 | 0.0056 | 0.9483 | 0.0036 | 0.1766 | 0.0069 |
| HT_PHYS | 0.9481 | 0.0027 | 0.9461 | 0.0055 | 0.9501 | 0.0036 | 0.1511 | 0.0057 |

Contrasts:

| comparator | window | contrast | metric | direction | margin | mean | se | min | max | good | verdict | lower_95 | observed_both_attained | attained | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0034 | 0.0024 | -0.0044 | 0.0154 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | -0.0021 | 0.0027 | -0.0124 | 0.0097 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0013 | 0.0060 | -0.0200 | 0.0328 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | 0.0055 | 0.0034 | -0.0149 | 0.0135 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0034 | – | – | – | 5/8 | PASS | -0.0011 | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0007 | 0.0011 | -0.0037 | 0.0043 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0012 | 0.0024 | -0.0109 | 0.0100 | 2/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0000 | 0.0035 | -0.0153 | 0.0126 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | 0.0014 | 0.0016 | -0.0052 | 0.0080 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0007 | – | – | – | 5/8 | PASS | -0.0013 | – | – | – |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA >= 0.90 | – | – | -0.5000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -0.5000 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA >= 0.93 | – | – | -0.7500 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -0.7500 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA >= 0.95 | – | – | 4.1250 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 1.0000 | 7/8 | PASS |
| HT_PHYS | small | HT_PHYS − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0078 | 0.0034 | -0.0071 | 0.0221 | 7/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0044 | 0.0045 | -0.0146 | 0.0236 | 3/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0168 | 0.0083 | -0.0134 | 0.0451 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0012 | 0.0034 | -0.0219 | 0.0113 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0078 | – | – | – | 7/8 | PASS | 0.0014 | – | – | – |
| HT_PHYS | all | HT_PHYS − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0014 | 0.0016 | -0.0053 | 0.0071 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0037 | 0.0026 | -0.0080 | 0.0121 | 2/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0059 | 0.0040 | -0.0079 | 0.0219 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0030 | 0.0021 | -0.0116 | 0.0038 | 3/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0014 | – | – | – | 5/8 | PASS | -0.0015 | – | – | – |
| HT_PHYS | endpoint | HT_PHYS − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HA_LEAN_MARGIN | BA >= 0.90 | – | – | -0.5000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -0.5000 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HA_LEAN_MARGIN | BA >= 0.93 | – | – | -1.6250 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -1.6250 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HA_LEAN_MARGIN | BA >= 0.95 | – | – | -1.2500 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -1.2500 | 8/8 | PASS |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0094 | 0.0032 | -0.0012 | 0.0222 | 7/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0142 | 0.0048 | -0.0012 | 0.0349 | 2/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0173 | 0.0078 | -0.0072 | 0.0508 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | 0.0016 | 0.0030 | -0.0161 | 0.0087 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0094 | – | – | – | 7/8 | PASS | 0.0034 | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | -0.0014 | 0.0012 | -0.0053 | 0.0055 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0293 | 0.0030 | 0.0184 | 0.0390 | 0/8 | WORSE (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0020 | 0.0026 | -0.0090 | 0.0119 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0048 | 0.0015 | -0.0137 | -0.0009 | 0/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | -0.0014 | – | – | – | 1/8 | PASS | -0.0036 | – | – | – |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.90 | – | – | -0.8750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -0.8750 | 8/8 | PASS |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.93 | – | – | -1.8750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -1.8750 | 8/8 | PASS |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.95 | – | – | 9.2500 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -2.8000 | 5/8 | PASS |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HONLY_MARGIN | BA | higher | 0.0200 | -0.0060 | 0.0025 | -0.0175 | 0.0021 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HONLY_MARGIN | log_loss | lower | 0.0100 | -0.0163 | 0.0049 | -0.0345 | 0.0099 | 7/8 | BETTER (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HONLY_MARGIN | sensitivity | higher | 0.0200 | -0.0159 | 0.0062 | -0.0409 | 0.0105 | 2/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HONLY_MARGIN | specificity | higher | 0.0200 | 0.0039 | 0.0035 | -0.0180 | 0.0140 | 7/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HONLY_MARGIN | BA non-inferiority | – | – | -0.0060 | – | – | – | 1/8 | FAIL | -0.0107 | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HONLY_MARGIN | BA | higher | 0.0200 | 0.0021 | 0.0018 | -0.0041 | 0.0085 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HONLY_MARGIN | log_loss | lower | 0.0100 | -0.0281 | 0.0026 | -0.0371 | -0.0152 | 8/8 | BETTER (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HONLY_MARGIN | sensitivity | higher | 0.0200 | -0.0020 | 0.0042 | -0.0173 | 0.0206 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HONLY_MARGIN | specificity | higher | 0.0200 | 0.0062 | 0.0019 | -0.0036 | 0.0122 | 7/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HONLY_MARGIN | BA non-inferiority | – | – | 0.0021 | – | – | – | 4/8 | PASS | -0.0013 | – | – | – |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HONLY_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HONLY_MARGIN | BA >= 0.90 | – | – | 0.3750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.3750 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HONLY_MARGIN | BA >= 0.93 | – | – | 1.1250 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 1.1250 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HONLY_MARGIN | BA >= 0.95 | – | – | -5.1250 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 4.4000 | 7/5 | PASS |
| HT_PHYS | small | HT_PHYS − HONLY_MARGIN | BA | higher | 0.0200 | -0.0017 | 0.0012 | -0.0060 | 0.0036 | 2/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HONLY_MARGIN | log_loss | lower | 0.0100 | -0.0098 | 0.0015 | -0.0137 | -0.0005 | 8/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HONLY_MARGIN | sensitivity | higher | 0.0200 | -0.0005 | 0.0024 | -0.0113 | 0.0075 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HONLY_MARGIN | specificity | higher | 0.0200 | -0.0028 | 0.0012 | -0.0072 | 0.0026 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HONLY_MARGIN | BA non-inferiority | – | – | -0.0017 | – | – | – | 2/8 | PASS | -0.0040 | – | – | – |
| HT_PHYS | all | HT_PHYS − HONLY_MARGIN | BA | higher | 0.0200 | 0.0028 | 0.0016 | -0.0042 | 0.0103 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HONLY_MARGIN | log_loss | lower | 0.0100 | -0.0256 | 0.0010 | -0.0292 | -0.0203 | 8/8 | BETTER (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HONLY_MARGIN | sensitivity | higher | 0.0200 | 0.0038 | 0.0033 | -0.0071 | 0.0192 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HONLY_MARGIN | specificity | higher | 0.0200 | 0.0018 | 0.0022 | -0.0108 | 0.0107 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HONLY_MARGIN | BA non-inferiority | – | – | 0.0028 | – | – | – | 6/8 | PASS | -0.0002 | – | – | – |
| HT_PHYS | endpoint | HT_PHYS − HONLY_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HONLY_MARGIN | BA >= 0.90 | – | – | 0.3750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.3750 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HONLY_MARGIN | BA >= 0.93 | – | – | 0.2500 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.2500 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HONLY_MARGIN | BA >= 0.95 | – | – | -10.5000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 3.6000 | 8/5 | PASS |

Attainment (fold-pooled):

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN_MARGIN | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | HA_TREND_MARGIN | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_MARGIN | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | HT_PHYS | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN_MARGIN | 8 | 8 | 8 | 9.00 | 3 | 12.88 | 13.00 | 1.00 |
| BA >= 0.90 | HA_TREND_MARGIN | 8 | 8 | 8 | 8.00 | 5 | 12.38 | 12.00 | 1.00 |
| BA >= 0.90 | HONLY_MARGIN | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.90 | HT_PHYS | 8 | 8 | 8 | 8.00 | 5 | 12.38 | 12.00 | 1.00 |
| BA >= 0.93 | HA_LEAN_MARGIN | 8 | 8 | 8 | 10.50 | 1 | 15.00 | 14.50 | 0.95 |
| BA >= 0.93 | HA_TREND_MARGIN | 8 | 8 | 8 | 10.00 | 1 | 14.25 | 14.00 | 0.97 |
| BA >= 0.93 | HONLY_MARGIN | 8 | 8 | 8 | 9.00 | 1 | 13.12 | 13.00 | 0.99 |
| BA >= 0.93 | HT_PHYS | 8 | 8 | 8 | 9.00 | 1 | 13.38 | 13.00 | 0.97 |
| BA >= 0.95 | HA_LEAN_MARGIN | 8 | 8 | 8 | 23.00 | 0 | 31.38 | 32.50 | 0.85 |
| BA >= 0.95 | HA_TREND_MARGIN | 8 | 8 | 7 | 22.00 | 0 | 31.86 | 33.00 | 0.81 |
| BA >= 0.95 | HONLY_MARGIN | 8 | 8 | 5 | 14.50 | 0 | 28.40 | 25.00 | 0.39 |
| BA >= 0.95 | HT_PHYS | 8 | 8 | 8 | 13.50 | 0 | 30.12 | 28.50 | 0.72 |

Attainment (individual learners):

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN_MARGIN | 40 | 40 | 40 | 8.00 | 37 | 12.10 | 12.00 | 1.00 |
| BA >= 0.80 | HA_TREND_MARGIN | 40 | 40 | 40 | 8.00 | 40 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_MARGIN | 40 | 40 | 40 | 8.00 | 38 | 12.05 | 12.00 | 1.00 |
| BA >= 0.80 | HT_PHYS | 40 | 40 | 40 | 8.00 | 40 | 12.00 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN_MARGIN | 40 | 40 | 40 | 8.00 | 24 | 12.72 | 12.00 | 0.96 |
| BA >= 0.90 | HA_TREND_MARGIN | 40 | 40 | 40 | 8.00 | 26 | 12.55 | 12.00 | 0.97 |
| BA >= 0.90 | HONLY_MARGIN | 40 | 40 | 40 | 8.00 | 30 | 12.47 | 12.00 | 0.99 |
| BA >= 0.90 | HT_PHYS | 40 | 40 | 40 | 8.00 | 26 | 12.53 | 12.00 | 0.97 |
| BA >= 0.93 | HA_LEAN_MARGIN | 40 | 40 | 39 | 9.00 | 16 | 16.15 | 13.00 | 0.87 |
| BA >= 0.93 | HA_TREND_MARGIN | 40 | 40 | 40 | 9.00 | 17 | 17.70 | 13.00 | 0.87 |
| BA >= 0.93 | HONLY_MARGIN | 40 | 40 | 35 | 8.00 | 25 | 13.74 | 12.00 | 0.94 |
| BA >= 0.93 | HT_PHYS | 40 | 40 | 39 | 9.00 | 17 | 14.54 | 13.00 | 0.87 |
| BA >= 0.95 | HA_LEAN_MARGIN | 40 | 40 | 34 | 11.00 | 8 | 22.41 | 19.50 | 0.77 |
| BA >= 0.95 | HA_TREND_MARGIN | 40 | 40 | 32 | 10.50 | 6 | 22.56 | 15.50 | 0.78 |
| BA >= 0.95 | HONLY_MARGIN | 40 | 40 | 28 | 9.00 | 10 | 15.89 | 13.00 | 0.78 |
| BA >= 0.95 | HT_PHYS | 40 | 40 | 32 | 10.00 | 6 | 20.41 | 16.50 | 0.78 |

Matched on the HA_LEAN paths (prior sensitivity, falsifying controls):

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | AUC_mean | AUC_se | BA_hard_group_mean | BA_hard_group_se |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN@HA_LEAN_MARGIN | 0.9322 | 0.0025 | 0.1880 | 0.0052 | 0.9808 | 0.0011 | 0.5228 | 0.0078 |
| HA_LEAN@HONLY_MARGIN | 0.9319 | 0.0024 | 0.2009 | 0.0078 | 0.9793 | 0.0014 | 0.5170 | 0.0086 |
| HA_TREND@HA_LEAN_MARGIN | 0.9382 | 0.0019 | 0.1835 | 0.0041 | 0.9834 | 0.0006 | 0.5397 | 0.0095 |
| HA_TREND@HONLY_MARGIN | 0.9400 | 0.0020 | 0.1924 | 0.0066 | 0.9830 | 0.0011 | 0.5125 | 0.0072 |
| HA_TREND_B10@HA_LEAN_MARGIN | 0.9381 | 0.0019 | 0.1837 | 0.0042 | 0.9834 | 0.0006 | 0.5377 | 0.0087 |
| HA_TREND_B10@HONLY_MARGIN | 0.9400 | 0.0019 | 0.1924 | 0.0065 | 0.9830 | 0.0011 | 0.5124 | 0.0080 |
| HA_TREND_B1@HA_LEAN_MARGIN | 0.9378 | 0.0019 | 0.1837 | 0.0041 | 0.9833 | 0.0006 | 0.5376 | 0.0111 |
| HA_TREND_B1@HONLY_MARGIN | 0.9396 | 0.0022 | 0.1924 | 0.0064 | 0.9829 | 0.0011 | 0.5091 | 0.0065 |
| HONLY_LR@HA_LEAN_MARGIN | 0.9392 | 0.0016 | 0.2055 | 0.0062 | 0.9821 | 0.0009 | 0.5161 | 0.0059 |
| HONLY_LR@HONLY_MARGIN | 0.9416 | 0.0012 | 0.2023 | 0.0064 | 0.9825 | 0.0006 | 0.5047 | 0.0025 |
| PAC@HA_LEAN_MARGIN | 0.9322 | 0.0026 | 0.1917 | 0.0031 | 0.9816 | 0.0006 | 0.5297 | 0.0141 |
| PAC@HONLY_MARGIN | 0.9297 | 0.0032 | 0.2049 | 0.0061 | 0.9807 | 0.0015 | 0.5391 | 0.0175 |
| PAC_GEN@HA_LEAN_MARGIN | 0.9261 | 0.0027 | 0.2016 | 0.0052 | 0.9790 | 0.0014 | 0.5543 | 0.0175 |
| PAC_GEN@HONLY_MARGIN | 0.9228 | 0.0045 | 0.2161 | 0.0079 | 0.9780 | 0.0022 | 0.5461 | 0.0252 |

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | AUC_mean | AUC_se | BA_hard_group_mean | BA_hard_group_se |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN@HA_LEAN_MARGIN | 0.9464 | 0.0009 | 0.1474 | 0.0035 | 0.9865 | 0.0007 | 0.5827 | 0.0056 |
| HA_LEAN@HONLY_MARGIN | 0.9467 | 0.0014 | 0.1464 | 0.0042 | 0.9872 | 0.0006 | 0.5681 | 0.0139 |
| HA_TREND@HA_LEAN_MARGIN | 0.9477 | 0.0010 | 0.1525 | 0.0032 | 0.9873 | 0.0005 | 0.5809 | 0.0063 |
| HA_TREND@HONLY_MARGIN | 0.9479 | 0.0014 | 0.1511 | 0.0043 | 0.9875 | 0.0006 | 0.5523 | 0.0119 |
| HA_TREND_B10@HA_LEAN_MARGIN | 0.9477 | 0.0010 | 0.1526 | 0.0032 | 0.9873 | 0.0005 | 0.5804 | 0.0062 |
| HA_TREND_B10@HONLY_MARGIN | 0.9479 | 0.0014 | 0.1512 | 0.0042 | 0.9875 | 0.0006 | 0.5520 | 0.0124 |
| HA_TREND_B1@HA_LEAN_MARGIN | 0.9473 | 0.0010 | 0.1528 | 0.0033 | 0.9872 | 0.0005 | 0.5795 | 0.0064 |
| HA_TREND_B1@HONLY_MARGIN | 0.9479 | 0.0014 | 0.1510 | 0.0042 | 0.9875 | 0.0006 | 0.5519 | 0.0114 |
| HONLY_LR@HA_LEAN_MARGIN | 0.9428 | 0.0007 | 0.2049 | 0.0046 | 0.9846 | 0.0006 | 0.5101 | 0.0034 |
| HONLY_LR@HONLY_MARGIN | 0.9451 | 0.0007 | 0.1767 | 0.0041 | 0.9843 | 0.0003 | 0.5022 | 0.0009 |
| PAC@HA_LEAN_MARGIN | 0.9419 | 0.0021 | 0.1620 | 0.0029 | 0.9856 | 0.0007 | 0.5801 | 0.0098 |
| PAC@HONLY_MARGIN | 0.9431 | 0.0025 | 0.1699 | 0.0050 | 0.9862 | 0.0011 | 0.5802 | 0.0155 |
| PAC_GEN@HA_LEAN_MARGIN | 0.9398 | 0.0019 | 0.1648 | 0.0032 | 0.9844 | 0.0009 | 0.5799 | 0.0078 |
| PAC_GEN@HONLY_MARGIN | 0.9379 | 0.0033 | 0.1779 | 0.0058 | 0.9844 | 0.0014 | 0.5763 | 0.0209 |

| window | contrast | mean | good | verdict |
|---|---|---|---|---|
| small | HA_TREND@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0060 | 7/8 | NOT DIFFERENT (DEV) |
| all | HA_TREND@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0012 | 7/8 | NOT DIFFERENT (DEV) |
| small | HA_TREND_B1@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0056 | 7/8 | NOT DIFFERENT (DEV) |
| all | HA_TREND_B1@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0009 | 5/8 | NOT DIFFERENT (DEV) |
| small | HA_TREND_B10@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0059 | 7/8 | NOT DIFFERENT (DEV) |
| all | HA_TREND_B10@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0013 | 7/8 | NOT DIFFERENT (DEV) |
| small | PAC@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | -0.0000 | 4/8 | NOT DIFFERENT (DEV) |
| all | PAC@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | -0.0045 | 1/8 | NOT DIFFERENT (DEV) |
| small | PAC_GEN@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | -0.0061 | 2/8 | NOT DIFFERENT (DEV) |
| all | PAC_GEN@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | -0.0066 | 0/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0070 | 8/8 | NOT DIFFERENT (DEV) |
| all | HONLY_LR@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | -0.0036 | 1/8 | NOT DIFFERENT (DEV) |

Hard group / corner errors:

| arm | budget | recall_shortK_NEW | spec_cond_NEW | BA_hard_group | recall_shortK_pooled | corner_cond_errors |
|---|---|---|---|---|---|---|
| HA_LEAN_MARGIN | 40 | 0.988 | 0.240 | 0.614 | 0.858 | 10.125 |
| HA_LEAN_MARGIN | 60 | 0.975 | 0.323 | 0.649 | 0.835 | 9.375 |
| HA_TREND_MARGIN | 40 | 0.963 | 0.208 | 0.585 | 0.858 | 10.500 |
| HA_TREND_MARGIN | 60 | 0.963 | 0.344 | 0.653 | 0.835 | 9.375 |
| HONLY_MARGIN | 40 | 1.000 | 0.000 | 0.500 | 0.886 | 14.250 |
| HONLY_MARGIN | 60 | 1.000 | 0.000 | 0.500 | 0.886 | 14.000 |
| HT_PHYS | 40 | 0.863 | 0.260 | 0.561 | 0.790 | 9.875 |
| HT_PHYS | 60 | 0.750 | 0.396 | 0.573 | 0.744 | 8.000 |

Corner query share and CPU:

| arm | corner_query_share | cpu_s_per_step |
|---|---|---|
| HA_LEAN_MARGIN | 0.452 | 0.247 |
| HA_TREND_MARGIN | 0.411 | 0.254 |
| HONLY_MARGIN | 0.239 | 0.009 |

## BLOCK

Own-query units 120; matched units 80; matched reproduction of own-path probabilities max |Δ| = 0.0 (4240 checks).

Fold-pooled AULC B8–B24:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se | brier_mean | brier_se | AUC_mean | AUC_se | BA_hard_group_mean | BA_hard_group_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN_MARGIN | 0.9268 | 0.0034 | 0.9395 | 0.0059 | 0.9142 | 0.0072 | 0.2123 | 0.0089 | 0.0606 | 0.0027 | 0.9776 | 0.0020 | 0.4724 | 0.0132 |
| HA_TREND_MARGIN | 0.9375 | 0.0022 | 0.9514 | 0.0050 | 0.9236 | 0.0058 | 0.1995 | 0.0073 | 0.0549 | 0.0019 | 0.9822 | 0.0013 | 0.4846 | 0.0127 |
| HONLY_MARGIN | 0.9401 | 0.0012 | 0.9525 | 0.0054 | 0.9278 | 0.0054 | 0.2082 | 0.0082 | 0.0556 | 0.0018 | 0.9826 | 0.0010 | 0.4909 | 0.0048 |
| HT_PHYS | 0.9334 | 0.0028 | 0.9569 | 0.0065 | 0.9098 | 0.0061 | 0.2088 | 0.0083 | 0.0583 | 0.0023 | 0.9822 | 0.0018 | 0.4854 | 0.0094 |

B8–B60:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se | brier_mean | brier_se | AUC_mean | AUC_se | BA_hard_group_mean | BA_hard_group_se |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HA_LEAN_MARGIN | 0.9274 | 0.0017 | 0.9568 | 0.0034 | 0.8981 | 0.0047 | 0.2004 | 0.0066 | 0.0596 | 0.0020 | 0.9810 | 0.0011 | 0.5381 | 0.0071 |
| HA_TREND_MARGIN | 0.9386 | 0.0011 | 0.9639 | 0.0018 | 0.9133 | 0.0028 | 0.1821 | 0.0039 | 0.0509 | 0.0011 | 0.9850 | 0.0006 | 0.5100 | 0.0038 |
| HONLY_MARGIN | 0.9468 | 0.0005 | 0.9515 | 0.0019 | 0.9421 | 0.0017 | 0.1851 | 0.0054 | 0.0492 | 0.0011 | 0.9835 | 0.0006 | 0.4971 | 0.0015 |
| HT_PHYS | 0.9325 | 0.0018 | 0.9693 | 0.0028 | 0.8957 | 0.0036 | 0.2072 | 0.0052 | 0.0593 | 0.0016 | 0.9833 | 0.0007 | 0.5111 | 0.0025 |

Individual learners B8–B24:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN_MARGIN | 0.6687 | 0.0174 | 0.7434 | 0.0467 | 0.6749 | 0.0563 | 0.2178 | 0.0208 |
| HA_TREND_MARGIN | 0.6827 | 0.0208 | 0.7925 | 0.0387 | 0.6582 | 0.0618 | 0.2041 | 0.0172 |
| HONLY_MARGIN | 0.6381 | 0.0199 | 0.7173 | 0.0546 | 0.6470 | 0.0640 | 0.2144 | 0.0164 |
| HT_PHYS | 0.6790 | 0.0202 | 0.7918 | 0.0442 | 0.6528 | 0.0594 | 0.2153 | 0.0186 |

B8–B60:

| arm | BA_mean | BA_se | sensitivity_mean | sensitivity_se | specificity_mean | specificity_se | log_loss_mean | log_loss_se |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN_MARGIN | 0.7225 | 0.0171 | 0.8508 | 0.0291 | 0.6752 | 0.0508 | 0.2107 | 0.0267 |
| HA_TREND_MARGIN | 0.6893 | 0.0198 | 0.8048 | 0.0423 | 0.6590 | 0.0577 | 0.1889 | 0.0188 |
| HONLY_MARGIN | 0.6268 | 0.0212 | 0.6800 | 0.0602 | 0.6590 | 0.0654 | 0.1911 | 0.0172 |
| HT_PHYS | 0.7071 | 0.0196 | 0.8636 | 0.0284 | 0.6403 | 0.0580 | 0.2175 | 0.0263 |

Contrasts:

| comparator | window | contrast | metric | direction | margin | mean | se | min | max | good | verdict | lower_95 | observed_both_attained | attained | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0107 | 0.0034 | -0.0023 | 0.0264 | 7/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | -0.0128 | 0.0060 | -0.0422 | 0.0022 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0119 | 0.0082 | -0.0137 | 0.0579 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | 0.0094 | 0.0069 | -0.0301 | 0.0310 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0107 | – | – | – | 7/8 | PASS | 0.0042 | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0112 | 0.0017 | 0.0035 | 0.0179 | 8/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | -0.0182 | 0.0054 | -0.0452 | 0.0012 | 7/8 | BETTER (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0071 | 0.0042 | -0.0093 | 0.0309 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | 0.0153 | 0.0053 | -0.0017 | 0.0387 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0112 | – | – | – | 8/8 | PASS | 0.0080 | – | – | – |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA >= 0.90 | – | – | -0.2500 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -0.2500 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA >= 0.93 | – | – | -9.3750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -9.3750 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HA_LEAN_MARGIN | BA >= 0.95 | – | – | -13.6250 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | – | 3/0 | PASS |
| HT_PHYS | small | HT_PHYS − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0065 | 0.0022 | -0.0021 | 0.0140 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | -0.0034 | 0.0041 | -0.0231 | 0.0116 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0174 | 0.0093 | -0.0212 | 0.0696 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0044 | 0.0087 | -0.0516 | 0.0210 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0065 | – | – | – | 6/8 | PASS | 0.0023 | – | – | – |
| HT_PHYS | all | HT_PHYS − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0051 | 0.0024 | -0.0070 | 0.0134 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | 0.0069 | 0.0056 | -0.0129 | 0.0347 | 3/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0125 | 0.0048 | -0.0019 | 0.0412 | 7/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HA_LEAN_MARGIN | specificity | higher | 0.0200 | -0.0024 | 0.0062 | -0.0333 | 0.0152 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0051 | – | – | – | 6/8 | PASS | 0.0005 | – | – | – |
| HT_PHYS | endpoint | HT_PHYS − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HA_LEAN_MARGIN | BA >= 0.90 | – | – | 0.1250 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.1250 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HA_LEAN_MARGIN | BA >= 0.93 | – | – | -8.3750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -8.3750 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HA_LEAN_MARGIN | BA >= 0.95 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | – | 0/0 | PASS |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0133 | 0.0031 | 0.0008 | 0.0280 | 8/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | -0.0041 | 0.0077 | -0.0475 | 0.0252 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | 0.0130 | 0.0083 | -0.0257 | 0.0564 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | 0.0136 | 0.0072 | -0.0246 | 0.0306 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | small | HONLY_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0133 | – | – | – | 8/8 | PASS | 0.0074 | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | BA | higher | 0.0200 | 0.0194 | 0.0016 | 0.0140 | 0.0254 | 8/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | log_loss | lower | 0.0100 | -0.0153 | 0.0079 | -0.0542 | 0.0166 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | sensitivity | higher | 0.0200 | -0.0053 | 0.0038 | -0.0154 | 0.0189 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | specificity | higher | 0.0200 | 0.0441 | 0.0037 | 0.0312 | 0.0595 | 8/8 | BETTER (DEV) | – | – | – | – |
| HONLY_MARGIN | all | HONLY_MARGIN − HA_LEAN_MARGIN | BA non-inferiority | – | – | 0.0194 | – | – | – | 8/8 | PASS | 0.0164 | – | – | – |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.90 | – | – | -0.3750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -0.3750 | 8/8 | PASS |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.93 | – | – | -9.3750 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | -9.3750 | 8/8 | PASS |
| HONLY_MARGIN | endpoint | HONLY_MARGIN − HA_LEAN_MARGIN | BA >= 0.95 | – | – | -27.7500 | – | – | – | – | FEWER SIMULATIONS (DEV) | – | – | 8/0 | PASS |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HONLY_MARGIN | BA | higher | 0.0200 | -0.0026 | 0.0022 | -0.0104 | 0.0066 | 3/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HONLY_MARGIN | log_loss | lower | 0.0100 | -0.0087 | 0.0038 | -0.0242 | 0.0052 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HONLY_MARGIN | sensitivity | higher | 0.0200 | -0.0012 | 0.0063 | -0.0311 | 0.0322 | 4/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HONLY_MARGIN | specificity | higher | 0.0200 | -0.0041 | 0.0044 | -0.0190 | 0.0140 | 3/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | small | HA_TREND_MARGIN − HONLY_MARGIN | BA non-inferiority | – | – | -0.0026 | – | – | – | 3/8 | PASS | -0.0068 | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HONLY_MARGIN | BA | higher | 0.0200 | -0.0082 | 0.0013 | -0.0139 | -0.0029 | 0/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HONLY_MARGIN | log_loss | lower | 0.0100 | -0.0030 | 0.0033 | -0.0159 | 0.0090 | 5/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HONLY_MARGIN | sensitivity | higher | 0.0200 | 0.0124 | 0.0021 | 0.0031 | 0.0226 | 8/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HONLY_MARGIN | specificity | higher | 0.0200 | -0.0288 | 0.0029 | -0.0416 | -0.0132 | 0/8 | WORSE (DEV) | – | – | – | – |
| HA_TREND_MARGIN | all | HA_TREND_MARGIN − HONLY_MARGIN | BA non-inferiority | – | – | -0.0082 | – | – | – | 0/8 | FAIL | -0.0107 | – | – | – |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HONLY_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HONLY_MARGIN | BA >= 0.90 | – | – | 0.1250 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.1250 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HONLY_MARGIN | BA >= 0.93 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HA_TREND_MARGIN | endpoint | HA_TREND_MARGIN − HONLY_MARGIN | BA >= 0.95 | – | – | 14.1250 | – | – | – | – | MORE SIMULATIONS (DEV) | – | -11.6667 | 3/8 | FAIL |
| HT_PHYS | small | HT_PHYS − HONLY_MARGIN | BA | higher | 0.0200 | -0.0068 | 0.0025 | -0.0213 | 0.0009 | 1/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HONLY_MARGIN | log_loss | lower | 0.0100 | 0.0006 | 0.0055 | -0.0204 | 0.0243 | 3/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HONLY_MARGIN | sensitivity | higher | 0.0200 | 0.0044 | 0.0052 | -0.0275 | 0.0188 | 6/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HONLY_MARGIN | specificity | higher | 0.0200 | -0.0180 | 0.0035 | -0.0332 | -0.0062 | 0/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | small | HT_PHYS − HONLY_MARGIN | BA non-inferiority | – | – | -0.0068 | – | – | – | 1/8 | FAIL | -0.0114 | – | – | – |
| HT_PHYS | all | HT_PHYS − HONLY_MARGIN | BA | higher | 0.0200 | -0.0143 | 0.0018 | -0.0226 | -0.0078 | 0/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HONLY_MARGIN | log_loss | lower | 0.0100 | 0.0221 | 0.0052 | -0.0040 | 0.0413 | 1/8 | WORSE (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HONLY_MARGIN | sensitivity | higher | 0.0200 | 0.0178 | 0.0019 | 0.0068 | 0.0223 | 8/8 | NOT DIFFERENT (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HONLY_MARGIN | specificity | higher | 0.0200 | -0.0465 | 0.0037 | -0.0671 | -0.0343 | 0/8 | WORSE (DEV) | – | – | – | – |
| HT_PHYS | all | HT_PHYS − HONLY_MARGIN | BA non-inferiority | – | – | -0.0143 | – | – | – | 0/8 | FAIL | -0.0177 | – | – | – |
| HT_PHYS | endpoint | HT_PHYS − HONLY_MARGIN | BA >= 0.80 | – | – | 0.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.0000 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HONLY_MARGIN | BA >= 0.90 | – | – | 0.5000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 0.5000 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HONLY_MARGIN | BA >= 0.93 | – | – | 1.0000 | – | – | – | – | NO CLEAR DIFFERENCE (DEV) | – | 1.0000 | 8/8 | PASS |
| HT_PHYS | endpoint | HT_PHYS − HONLY_MARGIN | BA >= 0.95 | – | – | 27.7500 | – | – | – | – | MORE SIMULATIONS (DEV) | – | – | 0/8 | FAIL |

Attainment (fold-pooled):

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN_MARGIN | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | HA_TREND_MARGIN | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_MARGIN | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | HT_PHYS | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN_MARGIN | 8 | 8 | 8 | 8.00 | 5 | 12.62 | 12.50 | 0.98 |
| BA >= 0.90 | HA_TREND_MARGIN | 8 | 8 | 8 | 8.00 | 5 | 12.38 | 12.00 | 1.00 |
| BA >= 0.90 | HONLY_MARGIN | 8 | 8 | 8 | 8.00 | 6 | 12.25 | 12.00 | 1.00 |
| BA >= 0.90 | HT_PHYS | 8 | 8 | 8 | 8.00 | 5 | 12.75 | 12.50 | 0.99 |
| BA >= 0.93 | HA_LEAN_MARGIN | 8 | 8 | 8 | 9.00 | 3 | 23.00 | 14.00 | 0.58 |
| BA >= 0.93 | HA_TREND_MARGIN | 8 | 8 | 8 | 9.00 | 3 | 13.62 | 13.00 | 0.93 |
| BA >= 0.93 | HONLY_MARGIN | 8 | 8 | 8 | 8.00 | 5 | 13.62 | 12.50 | 0.98 |
| BA >= 0.93 | HT_PHYS | 8 | 8 | 8 | 9.50 | 3 | 14.62 | 14.00 | 0.73 |
| BA >= 0.95 | HA_LEAN_MARGIN | 8 | 8 | 0 | 15.00 | 0 | – | – | – |
| BA >= 0.95 | HA_TREND_MARGIN | 8 | 8 | 3 | 15.00 | 0 | 24.67 | 19.00 | 0.12 |
| BA >= 0.95 | HONLY_MARGIN | 8 | 8 | 8 | 17.50 | 0 | 33.25 | 29.00 | 0.57 |
| BA >= 0.95 | HT_PHYS | 8 | 8 | 0 | 15.50 | 0 | – | – | – |

Attainment (individual learners):

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN_MARGIN | 40 | 32 | 18 | 8.00 | 12 | 22.72 | 21.00 | 0.65 |
| BA >= 0.80 | HA_TREND_MARGIN | 40 | 32 | 16 | 8.00 | 11 | 16.00 | 13.50 | 0.69 |
| BA >= 0.80 | HONLY_MARGIN | 40 | 32 | 10 | 8.00 | 11 | 14.80 | 13.00 | 0.80 |
| BA >= 0.80 | HT_PHYS | 40 | 32 | 17 | 8.00 | 11 | 19.24 | 14.00 | 0.81 |
| BA >= 0.90 | HA_LEAN_MARGIN | 40 | 32 | 8 | 8.00 | 7 | 29.25 | 30.00 | 0.85 |
| BA >= 0.90 | HA_TREND_MARGIN | 40 | 32 | 10 | 11.50 | 5 | 24.90 | 16.00 | 0.39 |
| BA >= 0.90 | HONLY_MARGIN | 40 | 32 | 2 | 8.00 | 6 | 15.50 | 15.50 | 0.12 |
| BA >= 0.90 | HT_PHYS | 40 | 32 | 11 | 12.00 | 5 | 27.36 | 33.00 | 0.58 |
| BA >= 0.93 | HA_LEAN_MARGIN | 40 | 32 | 8 | 8.00 | 5 | 29.25 | 30.00 | 0.85 |
| BA >= 0.93 | HA_TREND_MARGIN | 40 | 32 | 7 | 9.00 | 3 | 19.14 | 14.00 | 0.48 |
| BA >= 0.93 | HONLY_MARGIN | 40 | 32 | 2 | 8.00 | 5 | 15.50 | 15.50 | 0.12 |
| BA >= 0.93 | HT_PHYS | 40 | 32 | 8 | 9.00 | 3 | 25.12 | 22.50 | 0.75 |
| BA >= 0.95 | HA_LEAN_MARGIN | 40 | 32 | 8 | 9.00 | 3 | 32.38 | 34.50 | 0.90 |
| BA >= 0.95 | HA_TREND_MARGIN | 40 | 32 | 7 | 9.00 | 3 | 19.14 | 14.00 | 0.48 |
| BA >= 0.95 | HONLY_MARGIN | 40 | 32 | 2 | 8.00 | 5 | 15.50 | 15.50 | 0.12 |
| BA >= 0.95 | HT_PHYS | 40 | 32 | 8 | 9.00 | 3 | 25.12 | 22.50 | 0.75 |

Matched on the HA_LEAN paths (prior sensitivity, falsifying controls):

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | AUC_mean | AUC_se | BA_hard_group_mean | BA_hard_group_se |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN@HA_LEAN_MARGIN | 0.9268 | 0.0034 | 0.2123 | 0.0089 | 0.9776 | 0.0020 | 0.4724 | 0.0132 |
| HA_LEAN@HONLY_MARGIN | 0.9218 | 0.0057 | 0.2322 | 0.0165 | 0.9769 | 0.0038 | 0.4912 | 0.0118 |
| HA_TREND@HA_LEAN_MARGIN | 0.9370 | 0.0025 | 0.1986 | 0.0082 | 0.9815 | 0.0013 | 0.4778 | 0.0163 |
| HA_TREND@HONLY_MARGIN | 0.9334 | 0.0028 | 0.2088 | 0.0083 | 0.9822 | 0.0018 | 0.4854 | 0.0094 |
| HA_TREND_B10@HA_LEAN_MARGIN | 0.9371 | 0.0025 | 0.1985 | 0.0084 | 0.9815 | 0.0013 | 0.4788 | 0.0160 |
| HA_TREND_B10@HONLY_MARGIN | 0.9333 | 0.0027 | 0.2088 | 0.0085 | 0.9823 | 0.0018 | 0.4857 | 0.0090 |
| HA_TREND_B1@HA_LEAN_MARGIN | 0.9366 | 0.0024 | 0.1986 | 0.0081 | 0.9814 | 0.0013 | 0.4756 | 0.0158 |
| HA_TREND_B1@HONLY_MARGIN | 0.9333 | 0.0028 | 0.2089 | 0.0082 | 0.9824 | 0.0018 | 0.4843 | 0.0117 |
| HONLY_LR@HA_LEAN_MARGIN | 0.9381 | 0.0020 | 0.2057 | 0.0081 | 0.9810 | 0.0014 | 0.4841 | 0.0084 |
| HONLY_LR@HONLY_MARGIN | 0.9401 | 0.0012 | 0.2082 | 0.0082 | 0.9826 | 0.0010 | 0.4909 | 0.0048 |
| PAC@HA_LEAN_MARGIN | 0.9302 | 0.0036 | 0.2097 | 0.0075 | 0.9824 | 0.0009 | 0.4635 | 0.0156 |
| PAC@HONLY_MARGIN | 0.9288 | 0.0030 | 0.2166 | 0.0044 | 0.9823 | 0.0016 | 0.4834 | 0.0083 |
| PAC_GEN@HA_LEAN_MARGIN | 0.9105 | 0.0053 | 0.2428 | 0.0130 | 0.9760 | 0.0019 | 0.4358 | 0.0198 |
| PAC_GEN@HONLY_MARGIN | 0.9139 | 0.0039 | 0.2422 | 0.0071 | 0.9767 | 0.0026 | 0.4562 | 0.0116 |

| arm | BA_mean | BA_se | log_loss_mean | log_loss_se | AUC_mean | AUC_se | BA_hard_group_mean | BA_hard_group_se |
|---|---|---|---|---|---|---|---|---|
| HA_LEAN@HA_LEAN_MARGIN | 0.9274 | 0.0017 | 0.2004 | 0.0066 | 0.9810 | 0.0011 | 0.5381 | 0.0071 |
| HA_LEAN@HONLY_MARGIN | 0.9187 | 0.0028 | 0.2349 | 0.0096 | 0.9783 | 0.0019 | 0.5314 | 0.0030 |
| HA_TREND@HA_LEAN_MARGIN | 0.9376 | 0.0018 | 0.1819 | 0.0074 | 0.9844 | 0.0010 | 0.5097 | 0.0083 |
| HA_TREND@HONLY_MARGIN | 0.9325 | 0.0018 | 0.2072 | 0.0052 | 0.9833 | 0.0007 | 0.5111 | 0.0025 |
| HA_TREND_B10@HA_LEAN_MARGIN | 0.9376 | 0.0018 | 0.1819 | 0.0075 | 0.9844 | 0.0010 | 0.5101 | 0.0083 |
| HA_TREND_B10@HONLY_MARGIN | 0.9326 | 0.0017 | 0.2071 | 0.0053 | 0.9833 | 0.0007 | 0.5112 | 0.0024 |
| HA_TREND_B1@HA_LEAN_MARGIN | 0.9370 | 0.0019 | 0.1830 | 0.0075 | 0.9843 | 0.0010 | 0.5106 | 0.0082 |
| HA_TREND_B1@HONLY_MARGIN | 0.9318 | 0.0019 | 0.2087 | 0.0052 | 0.9831 | 0.0007 | 0.5122 | 0.0031 |
| HONLY_LR@HA_LEAN_MARGIN | 0.9428 | 0.0009 | 0.2028 | 0.0036 | 0.9828 | 0.0006 | 0.4942 | 0.0027 |
| HONLY_LR@HONLY_MARGIN | 0.9468 | 0.0005 | 0.1851 | 0.0054 | 0.9835 | 0.0006 | 0.4971 | 0.0015 |
| PAC@HA_LEAN_MARGIN | 0.9331 | 0.0032 | 0.1949 | 0.0076 | 0.9857 | 0.0008 | 0.5165 | 0.0081 |
| PAC@HONLY_MARGIN | 0.9269 | 0.0031 | 0.2177 | 0.0048 | 0.9839 | 0.0006 | 0.5103 | 0.0019 |
| PAC_GEN@HA_LEAN_MARGIN | 0.9143 | 0.0032 | 0.2316 | 0.0085 | 0.9809 | 0.0008 | 0.4880 | 0.0085 |
| PAC_GEN@HONLY_MARGIN | 0.9108 | 0.0031 | 0.2492 | 0.0064 | 0.9781 | 0.0015 | 0.4885 | 0.0057 |

| window | contrast | mean | good | verdict |
|---|---|---|---|---|
| small | HA_TREND@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0102 | 8/8 | NOT DIFFERENT (DEV) |
| all | HA_TREND@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0101 | 8/8 | NOT DIFFERENT (DEV) |
| small | HA_TREND_B1@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0097 | 8/8 | NOT DIFFERENT (DEV) |
| all | HA_TREND_B1@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0095 | 8/8 | NOT DIFFERENT (DEV) |
| small | HA_TREND_B10@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0103 | 8/8 | NOT DIFFERENT (DEV) |
| all | HA_TREND_B10@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0102 | 8/8 | NOT DIFFERENT (DEV) |
| small | PAC@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0033 | 5/8 | NOT DIFFERENT (DEV) |
| all | PAC@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0057 | 6/8 | NOT DIFFERENT (DEV) |
| small | PAC_GEN@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | -0.0163 | 1/8 | NOT DIFFERENT (DEV) |
| all | PAC_GEN@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | -0.0131 | 1/8 | NOT DIFFERENT (DEV) |
| small | HONLY_LR@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0112 | 8/8 | NOT DIFFERENT (DEV) |
| all | HONLY_LR@HA_LEAN_MARGIN − HA_LEAN@HA_LEAN_MARGIN | 0.0154 | 8/8 | NOT DIFFERENT (DEV) |

Hard group / corner errors:

| arm | budget | recall_shortK_NEW | spec_cond_NEW | BA_hard_group | recall_shortK_pooled | corner_cond_errors |
|---|---|---|---|---|---|---|
| HA_LEAN_MARGIN | 40 | 0.988 | 0.115 | 0.551 | 0.938 | 11.625 |
| HA_LEAN_MARGIN | 60 | 0.988 | 0.260 | 0.624 | 0.938 | 9.875 |
| HA_TREND_MARGIN | 40 | 0.988 | 0.052 | 0.520 | 0.915 | 12.625 |
| HA_TREND_MARGIN | 60 | 1.000 | 0.135 | 0.568 | 0.920 | 11.375 |
| HONLY_MARGIN | 40 | 1.000 | 0.000 | 0.500 | 0.909 | 14.000 |
| HONLY_MARGIN | 60 | 1.000 | 0.000 | 0.500 | 0.909 | 13.000 |
| HT_PHYS | 40 | 1.000 | 0.021 | 0.510 | 0.938 | 14.625 |
| HT_PHYS | 60 | 0.988 | 0.167 | 0.577 | 0.949 | 11.000 |

Corner query share and CPU:

| arm | corner_query_share | cpu_s_per_step |
|---|---|---|
| HA_LEAN_MARGIN | 0.427 | 0.275 |
| HA_TREND_MARGIN | 0.385 | 0.279 |
| HONLY_MARGIN | 0.247 | 0.010 |

