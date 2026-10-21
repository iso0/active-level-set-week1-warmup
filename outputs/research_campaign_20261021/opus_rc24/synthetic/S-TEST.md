# RC24 synthetic benchmark — s-test

640 units; one learner per world and split; BA-AULC (mean over seeds).

## B8_B24, split std

| family | HA_LEAN_MARGIN | HA_TREND_MARGIN | HONLY_MARGIN | PAC_MARGIN |
|---|---|---|---|---|
| T1_anchor_right_moderate | 0.8213 | 0.8334 | 0.8358 | 0.8383 |
| T2_anchor_partial25 | 0.8621 | 0.8668 | 0.8528 | 0.8620 |
| T3_anchor_partial70 | 0.8162 | 0.8157 | 0.7236 | 0.8442 |
| T4_anchor_useless_label_h | 0.7948 | 0.7665 | 0.7738 | 0.7987 |
| T5_no_aux_value | 0.8746 | 0.8724 | 0.8749 | 0.8822 |
| T6_label_residual | 0.8694 | 0.8754 | 0.8518 | 0.8680 |
| T7_balanced_noisy | 0.8212 | 0.8470 | 0.8391 | 0.8332 |
| T8_corner_partial45 | 0.8461 | 0.8434 | 0.7957 | 0.8514 |

| family | contrast | mean | se | pos |
|---|---|---|---|---|
| T1_anchor_right_moderate | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0121 | 0.0073 | 8/10 |
| T1_anchor_right_moderate | HA_TREND_MARGIN − HONLY_MARGIN | -0.0024 | 0.0112 | 5/10 |
| T1_anchor_right_moderate | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0145 | 0.0150 | 4/10 |
| T1_anchor_right_moderate | PAC_MARGIN − HA_LEAN_MARGIN | 0.0170 | 0.0106 | 8/10 |
| T1_anchor_right_moderate | PAC_MARGIN − HA_TREND_MARGIN | 0.0049 | 0.0084 | 6/10 |
| T2_anchor_partial25 | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0047 | 0.0130 | 7/10 |
| T2_anchor_partial25 | HA_TREND_MARGIN − HONLY_MARGIN | 0.0140 | 0.0125 | 8/10 |
| T2_anchor_partial25 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0094 | 0.0045 | 7/10 |
| T2_anchor_partial25 | PAC_MARGIN − HA_LEAN_MARGIN | -0.0001 | 0.0073 | 5/10 |
| T2_anchor_partial25 | PAC_MARGIN − HA_TREND_MARGIN | -0.0048 | 0.0175 | 4/10 |
| T3_anchor_partial70 | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0006 | 0.0115 | 3/10 |
| T3_anchor_partial70 | HA_TREND_MARGIN − HONLY_MARGIN | 0.0920 | 0.0227 | 9/10 |
| T3_anchor_partial70 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0926 | 0.0237 | 10/10 |
| T3_anchor_partial70 | PAC_MARGIN − HA_LEAN_MARGIN | 0.0279 | 0.0144 | 7/10 |
| T3_anchor_partial70 | PAC_MARGIN − HA_TREND_MARGIN | 0.0285 | 0.0065 | 10/10 |
| T4_anchor_useless_label_h | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0283 | 0.0139 | 2/10 |
| T4_anchor_useless_label_h | HA_TREND_MARGIN − HONLY_MARGIN | -0.0073 | 0.0137 | 3/10 |
| T4_anchor_useless_label_h | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0209 | 0.0094 | 7/10 |
| T4_anchor_useless_label_h | PAC_MARGIN − HA_LEAN_MARGIN | 0.0039 | 0.0098 | 5/10 |
| T4_anchor_useless_label_h | PAC_MARGIN − HA_TREND_MARGIN | 0.0322 | 0.0105 | 8/10 |
| T5_no_aux_value | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0022 | 0.0053 | 4/10 |
| T5_no_aux_value | HA_TREND_MARGIN − HONLY_MARGIN | -0.0025 | 0.0069 | 4/10 |
| T5_no_aux_value | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0003 | 0.0074 | 5/10 |
| T5_no_aux_value | PAC_MARGIN − HA_LEAN_MARGIN | 0.0076 | 0.0043 | 7/10 |
| T5_no_aux_value | PAC_MARGIN − HA_TREND_MARGIN | 0.0098 | 0.0035 | 8/10 |
| T6_label_residual | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0060 | 0.0084 | 4/10 |
| T6_label_residual | HA_TREND_MARGIN − HONLY_MARGIN | 0.0236 | 0.0107 | 7/10 |
| T6_label_residual | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0177 | 0.0083 | 8/10 |
| T6_label_residual | PAC_MARGIN − HA_LEAN_MARGIN | -0.0015 | 0.0072 | 5/10 |
| T6_label_residual | PAC_MARGIN − HA_TREND_MARGIN | -0.0074 | 0.0052 | 4/10 |
| T7_balanced_noisy | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0258 | 0.0066 | 10/10 |
| T7_balanced_noisy | HA_TREND_MARGIN − HONLY_MARGIN | 0.0079 | 0.0049 | 7/10 |
| T7_balanced_noisy | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0179 | 0.0072 | 1/10 |
| T7_balanced_noisy | PAC_MARGIN − HA_LEAN_MARGIN | 0.0120 | 0.0094 | 7/10 |
| T7_balanced_noisy | PAC_MARGIN − HA_TREND_MARGIN | -0.0138 | 0.0055 | 2/10 |
| T8_corner_partial45 | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0027 | 0.0060 | 5/10 |
| T8_corner_partial45 | HA_TREND_MARGIN − HONLY_MARGIN | 0.0477 | 0.0138 | 9/10 |
| T8_corner_partial45 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0504 | 0.0128 | 8/10 |
| T8_corner_partial45 | PAC_MARGIN − HA_LEAN_MARGIN | 0.0053 | 0.0061 | 7/10 |
| T8_corner_partial45 | PAC_MARGIN − HA_TREND_MARGIN | 0.0080 | 0.0069 | 8/10 |

## B8_B24, split block

| family | HA_LEAN_MARGIN | HA_TREND_MARGIN | HONLY_MARGIN | PAC_MARGIN |
|---|---|---|---|---|
| T1_anchor_right_moderate | 0.7081 | 0.7375 | 0.7294 | 0.7276 |
| T2_anchor_partial25 | 0.8225 | 0.8476 | 0.8109 | 0.8165 |
| T3_anchor_partial70 | 0.7352 | 0.7704 | 0.6012 | 0.7392 |
| T4_anchor_useless_label_h | 0.7149 | 0.7153 | 0.7254 | 0.7623 |
| T5_no_aux_value | 0.8234 | 0.8271 | 0.8353 | 0.8293 |
| T6_label_residual | 0.8264 | 0.8270 | 0.8264 | 0.8259 |
| T7_balanced_noisy | 0.7876 | 0.7752 | 0.7774 | 0.7837 |
| T8_corner_partial45 | 0.7807 | 0.7830 | 0.6759 | 0.8020 |

| family | contrast | mean | se | pos |
|---|---|---|---|---|
| T1_anchor_right_moderate | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0293 | 0.0127 | 6/10 |
| T1_anchor_right_moderate | HA_TREND_MARGIN − HONLY_MARGIN | 0.0080 | 0.0172 | 4/10 |
| T1_anchor_right_moderate | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0213 | 0.0153 | 3/10 |
| T1_anchor_right_moderate | PAC_MARGIN − HA_LEAN_MARGIN | 0.0194 | 0.0125 | 7/10 |
| T1_anchor_right_moderate | PAC_MARGIN − HA_TREND_MARGIN | -0.0099 | 0.0089 | 3/10 |
| T2_anchor_partial25 | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0251 | 0.0160 | 7/10 |
| T2_anchor_partial25 | HA_TREND_MARGIN − HONLY_MARGIN | 0.0366 | 0.0172 | 8/10 |
| T2_anchor_partial25 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0116 | 0.0062 | 8/10 |
| T2_anchor_partial25 | PAC_MARGIN − HA_LEAN_MARGIN | -0.0060 | 0.0133 | 4/10 |
| T2_anchor_partial25 | PAC_MARGIN − HA_TREND_MARGIN | -0.0311 | 0.0131 | 2/10 |
| T3_anchor_partial70 | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0352 | 0.0261 | 6/10 |
| T3_anchor_partial70 | HA_TREND_MARGIN − HONLY_MARGIN | 0.1692 | 0.0346 | 9/10 |
| T3_anchor_partial70 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.1340 | 0.0359 | 9/10 |
| T3_anchor_partial70 | PAC_MARGIN − HA_LEAN_MARGIN | 0.0040 | 0.0271 | 4/10 |
| T3_anchor_partial70 | PAC_MARGIN − HA_TREND_MARGIN | -0.0312 | 0.0177 | 2/10 |
| T4_anchor_useless_label_h | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0004 | 0.0146 | 4/10 |
| T4_anchor_useless_label_h | HA_TREND_MARGIN − HONLY_MARGIN | -0.0101 | 0.0198 | 3/10 |
| T4_anchor_useless_label_h | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0105 | 0.0110 | 4/10 |
| T4_anchor_useless_label_h | PAC_MARGIN − HA_LEAN_MARGIN | 0.0475 | 0.0154 | 8/10 |
| T4_anchor_useless_label_h | PAC_MARGIN − HA_TREND_MARGIN | 0.0471 | 0.0152 | 9/10 |
| T5_no_aux_value | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0037 | 0.0080 | 4/10 |
| T5_no_aux_value | HA_TREND_MARGIN − HONLY_MARGIN | -0.0082 | 0.0083 | 5/10 |
| T5_no_aux_value | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0120 | 0.0076 | 4/10 |
| T5_no_aux_value | PAC_MARGIN − HA_LEAN_MARGIN | 0.0059 | 0.0107 | 5/10 |
| T5_no_aux_value | PAC_MARGIN − HA_TREND_MARGIN | 0.0022 | 0.0089 | 4/10 |
| T6_label_residual | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0006 | 0.0098 | 5/10 |
| T6_label_residual | HA_TREND_MARGIN − HONLY_MARGIN | 0.0006 | 0.0100 | 5/10 |
| T6_label_residual | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0000 | 0.0150 | 6/10 |
| T6_label_residual | PAC_MARGIN − HA_LEAN_MARGIN | -0.0006 | 0.0167 | 5/10 |
| T6_label_residual | PAC_MARGIN − HA_TREND_MARGIN | -0.0011 | 0.0133 | 6/10 |
| T7_balanced_noisy | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0124 | 0.0078 | 3/10 |
| T7_balanced_noisy | HA_TREND_MARGIN − HONLY_MARGIN | -0.0022 | 0.0109 | 5/10 |
| T7_balanced_noisy | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0102 | 0.0105 | 6/10 |
| T7_balanced_noisy | PAC_MARGIN − HA_LEAN_MARGIN | -0.0039 | 0.0050 | 4/10 |
| T7_balanced_noisy | PAC_MARGIN − HA_TREND_MARGIN | 0.0085 | 0.0070 | 7/10 |
| T8_corner_partial45 | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0022 | 0.0161 | 6/10 |
| T8_corner_partial45 | HA_TREND_MARGIN − HONLY_MARGIN | 0.1071 | 0.0230 | 10/10 |
| T8_corner_partial45 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.1049 | 0.0242 | 10/10 |
| T8_corner_partial45 | PAC_MARGIN − HA_LEAN_MARGIN | 0.0213 | 0.0178 | 8/10 |
| T8_corner_partial45 | PAC_MARGIN − HA_TREND_MARGIN | 0.0191 | 0.0105 | 7/10 |

## B8_B60, split std

| family | HA_LEAN_MARGIN | HA_TREND_MARGIN | HONLY_MARGIN | PAC_MARGIN |
|---|---|---|---|---|
| T1_anchor_right_moderate | 0.8590 | 0.8583 | 0.8412 | 0.8627 |
| T2_anchor_partial25 | 0.8838 | 0.8823 | 0.8562 | 0.8834 |
| T3_anchor_partial70 | 0.8621 | 0.8565 | 0.7222 | 0.8697 |
| T4_anchor_useless_label_h | 0.8231 | 0.8167 | 0.7921 | 0.8288 |
| T5_no_aux_value | 0.8813 | 0.8821 | 0.8811 | 0.8839 |
| T6_label_residual | 0.8849 | 0.8825 | 0.8669 | 0.8828 |
| T7_balanced_noisy | 0.8468 | 0.8592 | 0.8468 | 0.8509 |
| T8_corner_partial45 | 0.8859 | 0.8839 | 0.8186 | 0.8850 |

| family | contrast | mean | se | pos |
|---|---|---|---|---|
| T1_anchor_right_moderate | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0008 | 0.0047 | 6/10 |
| T1_anchor_right_moderate | HA_TREND_MARGIN − HONLY_MARGIN | 0.0170 | 0.0098 | 8/10 |
| T1_anchor_right_moderate | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0178 | 0.0113 | 8/10 |
| T1_anchor_right_moderate | PAC_MARGIN − HA_LEAN_MARGIN | 0.0037 | 0.0038 | 5/10 |
| T1_anchor_right_moderate | PAC_MARGIN − HA_TREND_MARGIN | 0.0045 | 0.0062 | 5/10 |
| T2_anchor_partial25 | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0015 | 0.0063 | 6/10 |
| T2_anchor_partial25 | HA_TREND_MARGIN − HONLY_MARGIN | 0.0261 | 0.0084 | 8/10 |
| T2_anchor_partial25 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0276 | 0.0060 | 10/10 |
| T2_anchor_partial25 | PAC_MARGIN − HA_LEAN_MARGIN | -0.0004 | 0.0053 | 3/10 |
| T2_anchor_partial25 | PAC_MARGIN − HA_TREND_MARGIN | 0.0011 | 0.0097 | 5/10 |
| T3_anchor_partial70 | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0056 | 0.0073 | 5/10 |
| T3_anchor_partial70 | HA_TREND_MARGIN − HONLY_MARGIN | 0.1343 | 0.0229 | 10/10 |
| T3_anchor_partial70 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.1399 | 0.0187 | 10/10 |
| T3_anchor_partial70 | PAC_MARGIN − HA_LEAN_MARGIN | 0.0076 | 0.0079 | 5/10 |
| T3_anchor_partial70 | PAC_MARGIN − HA_TREND_MARGIN | 0.0132 | 0.0047 | 8/10 |
| T4_anchor_useless_label_h | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0064 | 0.0088 | 4/10 |
| T4_anchor_useless_label_h | HA_TREND_MARGIN − HONLY_MARGIN | 0.0247 | 0.0113 | 8/10 |
| T4_anchor_useless_label_h | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0310 | 0.0097 | 9/10 |
| T4_anchor_useless_label_h | PAC_MARGIN − HA_LEAN_MARGIN | 0.0057 | 0.0067 | 7/10 |
| T4_anchor_useless_label_h | PAC_MARGIN − HA_TREND_MARGIN | 0.0121 | 0.0077 | 7/10 |
| T5_no_aux_value | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0008 | 0.0027 | 5/10 |
| T5_no_aux_value | HA_TREND_MARGIN − HONLY_MARGIN | 0.0010 | 0.0035 | 6/10 |
| T5_no_aux_value | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0002 | 0.0047 | 5/10 |
| T5_no_aux_value | PAC_MARGIN − HA_LEAN_MARGIN | 0.0026 | 0.0035 | 6/10 |
| T5_no_aux_value | PAC_MARGIN − HA_TREND_MARGIN | 0.0018 | 0.0021 | 6/10 |
| T6_label_residual | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0024 | 0.0046 | 4/10 |
| T6_label_residual | HA_TREND_MARGIN − HONLY_MARGIN | 0.0156 | 0.0052 | 8/10 |
| T6_label_residual | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0180 | 0.0048 | 9/10 |
| T6_label_residual | PAC_MARGIN − HA_LEAN_MARGIN | -0.0021 | 0.0027 | 3/10 |
| T6_label_residual | PAC_MARGIN − HA_TREND_MARGIN | 0.0003 | 0.0030 | 5/10 |
| T7_balanced_noisy | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0124 | 0.0028 | 9/10 |
| T7_balanced_noisy | HA_TREND_MARGIN − HONLY_MARGIN | 0.0124 | 0.0035 | 10/10 |
| T7_balanced_noisy | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0000 | 0.0024 | 5/10 |
| T7_balanced_noisy | PAC_MARGIN − HA_LEAN_MARGIN | 0.0041 | 0.0038 | 7/10 |
| T7_balanced_noisy | PAC_MARGIN − HA_TREND_MARGIN | -0.0083 | 0.0031 | 2/10 |
| T8_corner_partial45 | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0020 | 0.0053 | 4/10 |
| T8_corner_partial45 | HA_TREND_MARGIN − HONLY_MARGIN | 0.0653 | 0.0121 | 9/10 |
| T8_corner_partial45 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0673 | 0.0115 | 9/10 |
| T8_corner_partial45 | PAC_MARGIN − HA_LEAN_MARGIN | -0.0009 | 0.0028 | 4/10 |
| T8_corner_partial45 | PAC_MARGIN − HA_TREND_MARGIN | 0.0011 | 0.0043 | 6/10 |

## B8_B60, split block

| family | HA_LEAN_MARGIN | HA_TREND_MARGIN | HONLY_MARGIN | PAC_MARGIN |
|---|---|---|---|---|
| T1_anchor_right_moderate | 0.7486 | 0.7735 | 0.7273 | 0.7558 |
| T2_anchor_partial25 | 0.8563 | 0.8717 | 0.8248 | 0.8530 |
| T3_anchor_partial70 | 0.7719 | 0.7884 | 0.6142 | 0.7666 |
| T4_anchor_useless_label_h | 0.7550 | 0.7551 | 0.7326 | 0.7759 |
| T5_no_aux_value | 0.8371 | 0.8413 | 0.8437 | 0.8417 |
| T6_label_residual | 0.8433 | 0.8459 | 0.8332 | 0.8448 |
| T7_balanced_noisy | 0.8036 | 0.8011 | 0.7975 | 0.8022 |
| T8_corner_partial45 | 0.8323 | 0.8224 | 0.6911 | 0.8340 |

| family | contrast | mean | se | pos |
|---|---|---|---|---|
| T1_anchor_right_moderate | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0250 | 0.0086 | 7/10 |
| T1_anchor_right_moderate | HA_TREND_MARGIN − HONLY_MARGIN | 0.0463 | 0.0192 | 7/10 |
| T1_anchor_right_moderate | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0213 | 0.0134 | 6/10 |
| T1_anchor_right_moderate | PAC_MARGIN − HA_LEAN_MARGIN | 0.0072 | 0.0059 | 7/10 |
| T1_anchor_right_moderate | PAC_MARGIN − HA_TREND_MARGIN | -0.0178 | 0.0060 | 3/10 |
| T2_anchor_partial25 | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0153 | 0.0082 | 6/10 |
| T2_anchor_partial25 | HA_TREND_MARGIN − HONLY_MARGIN | 0.0468 | 0.0164 | 9/10 |
| T2_anchor_partial25 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0315 | 0.0157 | 7/10 |
| T2_anchor_partial25 | PAC_MARGIN − HA_LEAN_MARGIN | -0.0034 | 0.0089 | 4/10 |
| T2_anchor_partial25 | PAC_MARGIN − HA_TREND_MARGIN | -0.0187 | 0.0088 | 2/10 |
| T3_anchor_partial70 | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0165 | 0.0198 | 6/10 |
| T3_anchor_partial70 | HA_TREND_MARGIN − HONLY_MARGIN | 0.1742 | 0.0334 | 9/10 |
| T3_anchor_partial70 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.1577 | 0.0363 | 9/10 |
| T3_anchor_partial70 | PAC_MARGIN − HA_LEAN_MARGIN | -0.0053 | 0.0120 | 4/10 |
| T3_anchor_partial70 | PAC_MARGIN − HA_TREND_MARGIN | -0.0217 | 0.0144 | 3/10 |
| T4_anchor_useless_label_h | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0001 | 0.0138 | 5/10 |
| T4_anchor_useless_label_h | HA_TREND_MARGIN − HONLY_MARGIN | 0.0225 | 0.0178 | 7/10 |
| T4_anchor_useless_label_h | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0225 | 0.0110 | 9/10 |
| T4_anchor_useless_label_h | PAC_MARGIN − HA_LEAN_MARGIN | 0.0209 | 0.0077 | 7/10 |
| T4_anchor_useless_label_h | PAC_MARGIN − HA_TREND_MARGIN | 0.0208 | 0.0096 | 6/10 |
| T5_no_aux_value | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0043 | 0.0024 | 7/10 |
| T5_no_aux_value | HA_TREND_MARGIN − HONLY_MARGIN | -0.0024 | 0.0045 | 4/10 |
| T5_no_aux_value | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0066 | 0.0037 | 2/10 |
| T5_no_aux_value | PAC_MARGIN − HA_LEAN_MARGIN | 0.0047 | 0.0034 | 6/10 |
| T5_no_aux_value | PAC_MARGIN − HA_TREND_MARGIN | 0.0004 | 0.0032 | 6/10 |
| T6_label_residual | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0026 | 0.0058 | 5/10 |
| T6_label_residual | HA_TREND_MARGIN − HONLY_MARGIN | 0.0127 | 0.0104 | 7/10 |
| T6_label_residual | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0101 | 0.0116 | 7/10 |
| T6_label_residual | PAC_MARGIN − HA_LEAN_MARGIN | 0.0015 | 0.0127 | 7/10 |
| T6_label_residual | PAC_MARGIN − HA_TREND_MARGIN | -0.0012 | 0.0114 | 5/10 |
| T7_balanced_noisy | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0025 | 0.0044 | 4/10 |
| T7_balanced_noisy | HA_TREND_MARGIN − HONLY_MARGIN | 0.0036 | 0.0088 | 7/10 |
| T7_balanced_noisy | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0061 | 0.0086 | 7/10 |
| T7_balanced_noisy | PAC_MARGIN − HA_LEAN_MARGIN | -0.0013 | 0.0033 | 4/10 |
| T7_balanced_noisy | PAC_MARGIN − HA_TREND_MARGIN | 0.0011 | 0.0032 | 6/10 |
| T8_corner_partial45 | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0100 | 0.0098 | 4/10 |
| T8_corner_partial45 | HA_TREND_MARGIN − HONLY_MARGIN | 0.1313 | 0.0197 | 10/10 |
| T8_corner_partial45 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.1412 | 0.0274 | 10/10 |
| T8_corner_partial45 | PAC_MARGIN − HA_LEAN_MARGIN | 0.0017 | 0.0097 | 7/10 |
| T8_corner_partial45 | PAC_MARGIN − HA_TREND_MARGIN | 0.0117 | 0.0111 | 7/10 |

