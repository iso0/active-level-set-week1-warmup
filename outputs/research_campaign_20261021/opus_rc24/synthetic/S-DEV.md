# RC24 synthetic benchmark — s-dev

192 units; one learner per world and split; BA-AULC (mean over seeds).

## B8_B24, split std

| family | HA_LEAN_MARGIN | HA_TREND_MARGIN | HONLY_MARGIN | PAC_MARGIN |
|---|---|---|---|---|
| D1_anchor_right | 0.8645 | 0.8771 | 0.8658 | 0.8770 |
| D2_anchor_partial45 | 0.8774 | 0.8807 | 0.7847 | 0.8883 |
| D3_anchor_useless | 0.5742 | 0.6105 | 0.6308 | 0.6444 |
| D4_weak_aux | 0.9316 | 0.9264 | 0.9268 | 0.9294 |
| D5_depth_threshold | 0.9000 | 0.8802 | 0.8732 | 0.8958 |
| D6_aleatoric_corner | 0.8675 | 0.8911 | 0.8801 | 0.8887 |

| family | contrast | mean | se | pos |
|---|---|---|---|---|
| D1_anchor_right | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0126 | 0.0140 | 2/4 |
| D1_anchor_right | HA_TREND_MARGIN − HONLY_MARGIN | 0.0113 | 0.0138 | 2/4 |
| D1_anchor_right | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0013 | 0.0203 | 1/4 |
| D1_anchor_right | PAC_MARGIN − HA_LEAN_MARGIN | 0.0125 | 0.0140 | 3/4 |
| D1_anchor_right | PAC_MARGIN − HA_TREND_MARGIN | -0.0001 | 0.0127 | 2/4 |
| D2_anchor_partial45 | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0034 | 0.0147 | 2/4 |
| D2_anchor_partial45 | HA_TREND_MARGIN − HONLY_MARGIN | 0.0960 | 0.0229 | 4/4 |
| D2_anchor_partial45 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0926 | 0.0221 | 4/4 |
| D2_anchor_partial45 | PAC_MARGIN − HA_LEAN_MARGIN | 0.0109 | 0.0216 | 3/4 |
| D2_anchor_partial45 | PAC_MARGIN − HA_TREND_MARGIN | 0.0076 | 0.0133 | 3/4 |
| D3_anchor_useless | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0363 | 0.0573 | 3/4 |
| D3_anchor_useless | HA_TREND_MARGIN − HONLY_MARGIN | -0.0203 | 0.0311 | 2/4 |
| D3_anchor_useless | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0566 | 0.0418 | 1/4 |
| D3_anchor_useless | PAC_MARGIN − HA_LEAN_MARGIN | 0.0701 | 0.0299 | 4/4 |
| D3_anchor_useless | PAC_MARGIN − HA_TREND_MARGIN | 0.0338 | 0.0330 | 3/4 |
| D4_weak_aux | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0052 | 0.0064 | 1/4 |
| D4_weak_aux | HA_TREND_MARGIN − HONLY_MARGIN | -0.0004 | 0.0082 | 2/4 |
| D4_weak_aux | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0048 | 0.0141 | 2/4 |
| D4_weak_aux | PAC_MARGIN − HA_LEAN_MARGIN | -0.0022 | 0.0058 | 1/4 |
| D4_weak_aux | PAC_MARGIN − HA_TREND_MARGIN | 0.0030 | 0.0059 | 2/4 |
| D5_depth_threshold | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0198 | 0.0104 | 1/4 |
| D5_depth_threshold | HA_TREND_MARGIN − HONLY_MARGIN | 0.0071 | 0.0140 | 3/4 |
| D5_depth_threshold | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0268 | 0.0103 | 4/4 |
| D5_depth_threshold | PAC_MARGIN − HA_LEAN_MARGIN | -0.0043 | 0.0076 | 2/4 |
| D5_depth_threshold | PAC_MARGIN − HA_TREND_MARGIN | 0.0155 | 0.0035 | 4/4 |
| D6_aleatoric_corner | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0236 | 0.0200 | 3/4 |
| D6_aleatoric_corner | HA_TREND_MARGIN − HONLY_MARGIN | 0.0110 | 0.0120 | 3/4 |
| D6_aleatoric_corner | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0126 | 0.0175 | 2/4 |
| D6_aleatoric_corner | PAC_MARGIN − HA_LEAN_MARGIN | 0.0212 | 0.0158 | 3/4 |
| D6_aleatoric_corner | PAC_MARGIN − HA_TREND_MARGIN | -0.0023 | 0.0126 | 1/4 |

## B8_B24, split block

| family | HA_LEAN_MARGIN | HA_TREND_MARGIN | HONLY_MARGIN | PAC_MARGIN |
|---|---|---|---|---|
| D1_anchor_right | 0.8335 | 0.8333 | 0.8222 | 0.8138 |
| D2_anchor_partial45 | 0.8172 | 0.8181 | 0.6736 | 0.8367 |
| D3_anchor_useless | 0.4980 | 0.5388 | 0.5274 | 0.5546 |
| D4_weak_aux | 0.8914 | 0.8882 | 0.8969 | 0.8966 |
| D5_depth_threshold | 0.8119 | 0.8285 | 0.8175 | 0.8352 |
| D6_aleatoric_corner | 0.8212 | 0.8073 | 0.8114 | 0.8266 |

| family | contrast | mean | se | pos |
|---|---|---|---|---|
| D1_anchor_right | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0002 | 0.0091 | 1/4 |
| D1_anchor_right | HA_TREND_MARGIN − HONLY_MARGIN | 0.0111 | 0.0157 | 3/4 |
| D1_anchor_right | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0113 | 0.0128 | 3/4 |
| D1_anchor_right | PAC_MARGIN − HA_LEAN_MARGIN | -0.0197 | 0.0108 | 1/4 |
| D1_anchor_right | PAC_MARGIN − HA_TREND_MARGIN | -0.0195 | 0.0188 | 1/4 |
| D2_anchor_partial45 | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0009 | 0.0183 | 2/4 |
| D2_anchor_partial45 | HA_TREND_MARGIN − HONLY_MARGIN | 0.1445 | 0.0372 | 4/4 |
| D2_anchor_partial45 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.1436 | 0.0260 | 4/4 |
| D2_anchor_partial45 | PAC_MARGIN − HA_LEAN_MARGIN | 0.0195 | 0.0205 | 3/4 |
| D2_anchor_partial45 | PAC_MARGIN − HA_TREND_MARGIN | 0.0186 | 0.0270 | 2/4 |
| D3_anchor_useless | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0407 | 0.0145 | 4/4 |
| D3_anchor_useless | HA_TREND_MARGIN − HONLY_MARGIN | 0.0114 | 0.0097 | 3/4 |
| D3_anchor_useless | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0293 | 0.0181 | 0/4 |
| D3_anchor_useless | PAC_MARGIN − HA_LEAN_MARGIN | 0.0566 | 0.0039 | 4/4 |
| D3_anchor_useless | PAC_MARGIN − HA_TREND_MARGIN | 0.0159 | 0.0139 | 3/4 |
| D4_weak_aux | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0032 | 0.0172 | 2/4 |
| D4_weak_aux | HA_TREND_MARGIN − HONLY_MARGIN | -0.0088 | 0.0163 | 2/4 |
| D4_weak_aux | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0056 | 0.0039 | 1/4 |
| D4_weak_aux | PAC_MARGIN − HA_LEAN_MARGIN | 0.0052 | 0.0058 | 2/4 |
| D4_weak_aux | PAC_MARGIN − HA_TREND_MARGIN | 0.0084 | 0.0172 | 2/4 |
| D5_depth_threshold | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0166 | 0.0196 | 3/4 |
| D5_depth_threshold | HA_TREND_MARGIN − HONLY_MARGIN | 0.0110 | 0.0274 | 2/4 |
| D5_depth_threshold | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0056 | 0.0357 | 2/4 |
| D5_depth_threshold | PAC_MARGIN − HA_LEAN_MARGIN | 0.0233 | 0.0322 | 2/4 |
| D5_depth_threshold | PAC_MARGIN − HA_TREND_MARGIN | 0.0067 | 0.0206 | 2/4 |
| D6_aleatoric_corner | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0139 | 0.0333 | 2/4 |
| D6_aleatoric_corner | HA_TREND_MARGIN − HONLY_MARGIN | -0.0041 | 0.0164 | 3/4 |
| D6_aleatoric_corner | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0098 | 0.0190 | 3/4 |
| D6_aleatoric_corner | PAC_MARGIN − HA_LEAN_MARGIN | 0.0054 | 0.0326 | 2/4 |
| D6_aleatoric_corner | PAC_MARGIN − HA_TREND_MARGIN | 0.0193 | 0.0542 | 2/4 |

## B8_B60, split std

| family | HA_LEAN_MARGIN | HA_TREND_MARGIN | HONLY_MARGIN | PAC_MARGIN |
|---|---|---|---|---|
| D1_anchor_right | 0.8921 | 0.8967 | 0.8802 | 0.9060 |
| D2_anchor_partial45 | 0.9161 | 0.9166 | 0.8005 | 0.9229 |
| D3_anchor_useless | 0.6713 | 0.6949 | 0.6246 | 0.7035 |
| D4_weak_aux | 0.9405 | 0.9379 | 0.9375 | 0.9361 |
| D5_depth_threshold | 0.9253 | 0.9092 | 0.8850 | 0.9173 |
| D6_aleatoric_corner | 0.8975 | 0.9006 | 0.8882 | 0.9022 |

| family | contrast | mean | se | pos |
|---|---|---|---|---|
| D1_anchor_right | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0046 | 0.0069 | 2/4 |
| D1_anchor_right | HA_TREND_MARGIN − HONLY_MARGIN | 0.0164 | 0.0041 | 4/4 |
| D1_anchor_right | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0119 | 0.0092 | 3/4 |
| D1_anchor_right | PAC_MARGIN − HA_LEAN_MARGIN | 0.0139 | 0.0089 | 3/4 |
| D1_anchor_right | PAC_MARGIN − HA_TREND_MARGIN | 0.0093 | 0.0059 | 3/4 |
| D2_anchor_partial45 | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0004 | 0.0026 | 2/4 |
| D2_anchor_partial45 | HA_TREND_MARGIN − HONLY_MARGIN | 0.1161 | 0.0116 | 4/4 |
| D2_anchor_partial45 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.1157 | 0.0125 | 4/4 |
| D2_anchor_partial45 | PAC_MARGIN − HA_LEAN_MARGIN | 0.0067 | 0.0038 | 3/4 |
| D2_anchor_partial45 | PAC_MARGIN − HA_TREND_MARGIN | 0.0063 | 0.0053 | 3/4 |
| D3_anchor_useless | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0236 | 0.0372 | 2/4 |
| D3_anchor_useless | HA_TREND_MARGIN − HONLY_MARGIN | 0.0703 | 0.0447 | 3/4 |
| D3_anchor_useless | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0467 | 0.0395 | 3/4 |
| D3_anchor_useless | PAC_MARGIN − HA_LEAN_MARGIN | 0.0322 | 0.0161 | 4/4 |
| D3_anchor_useless | PAC_MARGIN − HA_TREND_MARGIN | 0.0085 | 0.0235 | 2/4 |
| D4_weak_aux | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0026 | 0.0017 | 0/4 |
| D4_weak_aux | HA_TREND_MARGIN − HONLY_MARGIN | 0.0004 | 0.0033 | 2/4 |
| D4_weak_aux | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0030 | 0.0046 | 2/4 |
| D4_weak_aux | PAC_MARGIN − HA_LEAN_MARGIN | -0.0044 | 0.0020 | 1/4 |
| D4_weak_aux | PAC_MARGIN − HA_TREND_MARGIN | -0.0018 | 0.0021 | 2/4 |
| D5_depth_threshold | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0160 | 0.0051 | 0/4 |
| D5_depth_threshold | HA_TREND_MARGIN − HONLY_MARGIN | 0.0242 | 0.0131 | 3/4 |
| D5_depth_threshold | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0402 | 0.0091 | 4/4 |
| D5_depth_threshold | PAC_MARGIN − HA_LEAN_MARGIN | -0.0079 | 0.0048 | 0/4 |
| D5_depth_threshold | PAC_MARGIN − HA_TREND_MARGIN | 0.0081 | 0.0035 | 3/4 |
| D6_aleatoric_corner | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0030 | 0.0075 | 3/4 |
| D6_aleatoric_corner | HA_TREND_MARGIN − HONLY_MARGIN | 0.0123 | 0.0069 | 3/4 |
| D6_aleatoric_corner | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0093 | 0.0085 | 3/4 |
| D6_aleatoric_corner | PAC_MARGIN − HA_LEAN_MARGIN | 0.0047 | 0.0019 | 4/4 |
| D6_aleatoric_corner | PAC_MARGIN − HA_TREND_MARGIN | 0.0017 | 0.0074 | 1/4 |

## B8_B60, split block

| family | HA_LEAN_MARGIN | HA_TREND_MARGIN | HONLY_MARGIN | PAC_MARGIN |
|---|---|---|---|---|
| D1_anchor_right | 0.8413 | 0.8512 | 0.8299 | 0.8409 |
| D2_anchor_partial45 | 0.8544 | 0.8413 | 0.6754 | 0.8498 |
| D3_anchor_useless | 0.5597 | 0.5597 | 0.5321 | 0.5701 |
| D4_weak_aux | 0.8986 | 0.8977 | 0.9021 | 0.9009 |
| D5_depth_threshold | 0.8323 | 0.8487 | 0.8384 | 0.8648 |
| D6_aleatoric_corner | 0.8714 | 0.8571 | 0.8465 | 0.8838 |

| family | contrast | mean | se | pos |
|---|---|---|---|---|
| D1_anchor_right | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0099 | 0.0170 | 2/4 |
| D1_anchor_right | HA_TREND_MARGIN − HONLY_MARGIN | 0.0213 | 0.0114 | 3/4 |
| D1_anchor_right | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0114 | 0.0251 | 3/4 |
| D1_anchor_right | PAC_MARGIN − HA_LEAN_MARGIN | -0.0004 | 0.0047 | 3/4 |
| D1_anchor_right | PAC_MARGIN − HA_TREND_MARGIN | -0.0103 | 0.0205 | 2/4 |
| D2_anchor_partial45 | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0131 | 0.0121 | 2/4 |
| D2_anchor_partial45 | HA_TREND_MARGIN − HONLY_MARGIN | 0.1659 | 0.0360 | 4/4 |
| D2_anchor_partial45 | HA_LEAN_MARGIN − HONLY_MARGIN | 0.1790 | 0.0293 | 4/4 |
| D2_anchor_partial45 | PAC_MARGIN − HA_LEAN_MARGIN | -0.0046 | 0.0151 | 1/4 |
| D2_anchor_partial45 | PAC_MARGIN − HA_TREND_MARGIN | 0.0086 | 0.0219 | 1/4 |
| D3_anchor_useless | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0001 | 0.0104 | 2/4 |
| D3_anchor_useless | HA_TREND_MARGIN − HONLY_MARGIN | 0.0276 | 0.0136 | 3/4 |
| D3_anchor_useless | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0275 | 0.0215 | 3/4 |
| D3_anchor_useless | PAC_MARGIN − HA_LEAN_MARGIN | 0.0104 | 0.0104 | 3/4 |
| D3_anchor_useless | PAC_MARGIN − HA_TREND_MARGIN | 0.0103 | 0.0120 | 2/4 |
| D4_weak_aux | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0010 | 0.0079 | 2/4 |
| D4_weak_aux | HA_TREND_MARGIN − HONLY_MARGIN | -0.0044 | 0.0064 | 3/4 |
| D4_weak_aux | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0034 | 0.0037 | 1/4 |
| D4_weak_aux | PAC_MARGIN − HA_LEAN_MARGIN | 0.0023 | 0.0018 | 3/4 |
| D4_weak_aux | PAC_MARGIN − HA_TREND_MARGIN | 0.0033 | 0.0086 | 2/4 |
| D5_depth_threshold | HA_TREND_MARGIN − HA_LEAN_MARGIN | 0.0164 | 0.0095 | 3/4 |
| D5_depth_threshold | HA_TREND_MARGIN − HONLY_MARGIN | 0.0103 | 0.0317 | 2/4 |
| D5_depth_threshold | HA_LEAN_MARGIN − HONLY_MARGIN | -0.0061 | 0.0287 | 2/4 |
| D5_depth_threshold | PAC_MARGIN − HA_LEAN_MARGIN | 0.0325 | 0.0260 | 3/4 |
| D5_depth_threshold | PAC_MARGIN − HA_TREND_MARGIN | 0.0161 | 0.0188 | 2/4 |
| D6_aleatoric_corner | HA_TREND_MARGIN − HA_LEAN_MARGIN | -0.0143 | 0.0237 | 2/4 |
| D6_aleatoric_corner | HA_TREND_MARGIN − HONLY_MARGIN | 0.0106 | 0.0125 | 3/4 |
| D6_aleatoric_corner | HA_LEAN_MARGIN − HONLY_MARGIN | 0.0248 | 0.0172 | 2/4 |
| D6_aleatoric_corner | PAC_MARGIN − HA_LEAN_MARGIN | 0.0124 | 0.0183 | 3/4 |
| D6_aleatoric_corner | PAC_MARGIN − HA_TREND_MARGIN | 0.0267 | 0.0399 | 2/4 |

