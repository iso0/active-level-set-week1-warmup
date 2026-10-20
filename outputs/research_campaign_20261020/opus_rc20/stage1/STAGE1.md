# RC20 Stage 1 — matched-path attribution and log-h variants (DEV; the 200 RC19B final paths; budgets 8–60 every 4)

Recomputed SHQ_ATS / M0Q_A vs the cached ATSCF / DEPTHCF on every replayed budget: max |Δ| = 2.98e-08 (5600 checks).

## All-path means (mean over the 5 path types, then over 8 repeats)

| construction | LL B8–B60 | BA B8–B60 | Brier B8–B60 | AUC B8–B60 | sens B8–B60 | spec B8–B60 | LL B8–B24 | BA B8–B24 | Brier B8–B24 | AUC B8–B24 | sens B8–B24 | spec B8–B24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX | 0.1645 | 0.9403 | 0.0444 | 0.9845 | 0.9292 | 0.9513 | 0.2169 | 0.9236 | 0.0590 | 0.9769 | 0.9094 | 0.9378 |
| SHQ_ATS_H | 0.1647 | 0.9384 | 0.0456 | 0.9836 | 0.9281 | 0.9486 | 0.2254 | 0.9165 | 0.0631 | 0.9725 | 0.9031 | 0.9299 |
| SHQ_A_H | 0.1674 | 0.9452 | 0.0451 | 0.9868 | 0.9412 | 0.9492 | 0.2318 | 0.9302 | 0.0626 | 0.9807 | 0.9319 | 0.9285 |
| M0Q_ATS | 0.1835 | 0.9340 | 0.0497 | 0.9799 | 0.9197 | 0.9483 | 0.2501 | 0.9077 | 0.0699 | 0.9656 | 0.8856 | 0.9298 |
| SHQ_ATS | 0.1844 | 0.9303 | 0.0508 | 0.9763 | 0.9162 | 0.9443 | 0.2610 | 0.8973 | 0.0750 | 0.9543 | 0.8766 | 0.9181 |
| ATSCF | 0.1844 | 0.9303 | 0.0508 | 0.9763 | 0.9162 | 0.9443 | 0.2610 | 0.8973 | 0.0750 | 0.9543 | 0.8766 | 0.9181 |
| SHQT_ATS | 0.1871 | 0.9379 | 0.0499 | 0.9856 | 0.9277 | 0.9481 | 0.2458 | 0.9243 | 0.0667 | 0.9792 | 0.9164 | 0.9322 |
| SHQ_A | 0.2132 | 0.9280 | 0.0575 | 0.9764 | 0.9120 | 0.9441 | 0.3078 | 0.8955 | 0.0874 | 0.9554 | 0.8793 | 0.9117 |
| M0Q_A | 0.2209 | 0.9254 | 0.0602 | 0.9744 | 0.9076 | 0.9431 | 0.3220 | 0.8910 | 0.0927 | 0.9510 | 0.8719 | 0.9102 |
| DEPTHCF | 0.2209 | 0.9254 | 0.0602 | 0.9744 | 0.9076 | 0.9431 | 0.3220 | 0.8910 | 0.0927 | 0.9510 | 0.8719 | 0.9102 |
| SHQT_A | 0.2252 | 0.9326 | 0.0598 | 0.9847 | 0.9168 | 0.9485 | 0.3081 | 0.9139 | 0.0853 | 0.9771 | 0.9005 | 0.9274 |
| HONLY | 0.2342 | 0.9394 | 0.0613 | 0.9850 | 0.9314 | 0.9475 | 0.2909 | 0.9343 | 0.0782 | 0.9824 | 0.9346 | 0.9340 |
| E1CAL | 0.2373 | 0.9295 | 0.0615 | 0.9703 | 0.9170 | 0.9420 | 0.3170 | 0.9011 | 0.0835 | 0.9527 | 0.8928 | 0.9095 |
| E1RAW | 0.2382 | 0.9349 | 0.0534 | 0.9773 | 0.9400 | 0.9298 | 0.3478 | 0.9104 | 0.0749 | 0.9668 | 0.9309 | 0.8898 |
| G3 | 0.3679 | 0.8738 | 0.1102 | 0.9289 | 0.8490 | 0.8987 | 0.4233 | 0.8458 | 0.1287 | 0.9055 | 0.8254 | 0.8662 |

## Pre-registered contrasts (MATERIAL iff mean Δ ≤ −0.010 in log loss / Brier, or ≥ +0.010 in BA, and favourable in ≥ 7/8 repeats)

| hypothesis | window | contrast | metric | mean | se | min | max | repeats_favourable | label | path_E1S | path_ATSCF_MARGIN | path_DEPTHCF_MARGIN | path_G3_MARGIN | path_ATSAPPROX_MARGIN |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 T/S beyond depth, identical SHQ upstream (DECISIVE) | B8–B60 | SHQ_ATS − SHQ_A | LL | -0.0288 | 0.0028 | -0.0392 | -0.0143 | 8/8 | MATERIAL | -0.0317 | -0.0259 | -0.0263 | -0.0312 | -0.0288 |
| H1 T/S beyond depth, identical SHQ upstream (DECISIVE) | B8–B60 | SHQ_ATS − SHQ_A | Brier | -0.0067 | 0.0011 | -0.0097 | -0.0005 | 8/8 | NOT MATERIAL | -0.0080 | -0.0059 | -0.0065 | -0.0068 | -0.0064 |
| H1 T/S beyond depth, identical SHQ upstream (DECISIVE) | B8–B60 | SHQ_ATS − SHQ_A | BA | 0.0022 | 0.0033 | -0.0183 | 0.0097 | 6/8 | NOT MATERIAL | 0.0085 | -0.0007 | 0.0036 | 0.0007 | -0.0010 |
| H1 T/S beyond depth, identical SHQ upstream (DECISIVE) | B8–B24 | SHQ_ATS − SHQ_A | LL | -0.0468 | 0.0074 | -0.0744 | -0.0073 | 8/8 | MATERIAL | -0.0526 | -0.0429 | -0.0433 | -0.0489 | -0.0465 |
| H1 T/S beyond depth, identical SHQ upstream (DECISIVE) | B8–B24 | SHQ_ATS − SHQ_A | Brier | -0.0124 | 0.0030 | -0.0212 | 0.0047 | 7/8 | MATERIAL | -0.0149 | -0.0114 | -0.0115 | -0.0125 | -0.0120 |
| H1 T/S beyond depth, identical SHQ upstream (DECISIVE) | B8–B24 | SHQ_ATS − SHQ_A | BA | 0.0018 | 0.0089 | -0.0543 | 0.0264 | 6/8 | NOT MATERIAL | 0.0122 | -0.0053 | 0.0027 | 0.0026 | -0.0031 |
| H1b T/S beyond depth under M0Q | B8–B60 | M0Q_ATS − M0Q_A | LL | -0.0375 | 0.0015 | -0.0438 | -0.0314 | 8/8 | MATERIAL | -0.0414 | -0.0371 | -0.0305 | -0.0396 | -0.0386 |
| H1b T/S beyond depth under M0Q | B8–B60 | M0Q_ATS − M0Q_A | Brier | -0.0105 | 0.0005 | -0.0128 | -0.0085 | 8/8 | MATERIAL | -0.0117 | -0.0106 | -0.0089 | -0.0103 | -0.0111 |
| H1b T/S beyond depth under M0Q | B8–B60 | M0Q_ATS − M0Q_A | BA | 0.0086 | 0.0009 | 0.0042 | 0.0121 | 8/8 | NOT MATERIAL | 0.0141 | 0.0070 | 0.0083 | 0.0072 | 0.0066 |
| H1b T/S beyond depth under M0Q | B8–B24 | M0Q_ATS − M0Q_A | LL | -0.0719 | 0.0040 | -0.0873 | -0.0515 | 8/8 | MATERIAL | -0.0726 | -0.0746 | -0.0625 | -0.0718 | -0.0779 |
| H1b T/S beyond depth under M0Q | B8–B24 | M0Q_ATS − M0Q_A | Brier | -0.0228 | 0.0015 | -0.0288 | -0.0159 | 8/8 | MATERIAL | -0.0230 | -0.0244 | -0.0198 | -0.0220 | -0.0247 |
| H1b T/S beyond depth under M0Q | B8–B24 | M0Q_ATS − M0Q_A | BA | 0.0166 | 0.0028 | 0.0018 | 0.0269 | 8/8 | MATERIAL | 0.0233 | 0.0155 | 0.0154 | 0.0139 | 0.0151 |
| H2a upstream sharing, A only | B8–B60 | SHQ_A − M0Q_A | LL | -0.0078 | 0.0030 | -0.0166 | 0.0070 | 6/8 | NOT MATERIAL | -0.0095 | -0.0091 | -0.0028 | -0.0036 | -0.0138 |
| H2a upstream sharing, A only | B8–B60 | SHQ_A − M0Q_A | Brier | -0.0027 | 0.0011 | -0.0057 | 0.0028 | 6/8 | NOT MATERIAL | -0.0030 | -0.0033 | -0.0012 | -0.0014 | -0.0046 |
| H2a upstream sharing, A only | B8–B60 | SHQ_A − M0Q_A | BA | 0.0027 | 0.0018 | -0.0075 | 0.0077 | 6/8 | NOT MATERIAL | 0.0029 | 0.0040 | 0.0013 | 0.0017 | 0.0035 |
| H2a upstream sharing, A only | B8–B24 | SHQ_A − M0Q_A | LL | -0.0142 | 0.0081 | -0.0371 | 0.0272 | 6/8 | NOT MATERIAL | -0.0125 | -0.0197 | -0.0087 | -0.0066 | -0.0235 |
| H2a upstream sharing, A only | B8–B24 | SHQ_A − M0Q_A | Brier | -0.0053 | 0.0029 | -0.0136 | 0.0099 | 6/8 | NOT MATERIAL | -0.0045 | -0.0079 | -0.0032 | -0.0025 | -0.0084 |
| H2a upstream sharing, A only | B8–B24 | SHQ_A − M0Q_A | BA | 0.0045 | 0.0047 | -0.0238 | 0.0160 | 6/8 | NOT MATERIAL | 0.0035 | 0.0101 | 0.0023 | -0.0003 | 0.0066 |
| H2b upstream sharing, ATS | B8–B60 | SHQ_ATS − M0Q_ATS | LL | 0.0009 | 0.0030 | -0.0107 | 0.0128 | 4/8 | NOT MATERIAL | 0.0002 | 0.0021 | 0.0014 | 0.0048 | -0.0040 |
| H2b upstream sharing, ATS | B8–B60 | SHQ_ATS − M0Q_ATS | Brier | 0.0011 | 0.0013 | -0.0035 | 0.0065 | 4/8 | NOT MATERIAL | 0.0007 | 0.0014 | 0.0012 | 0.0022 | 0.0001 |
| H2b upstream sharing, ATS | B8–B60 | SHQ_ATS − M0Q_ATS | BA | -0.0037 | 0.0032 | -0.0204 | 0.0063 | 4/8 | NOT MATERIAL | -0.0027 | -0.0036 | -0.0034 | -0.0048 | -0.0041 |
| H2b upstream sharing, ATS | B8–B24 | SHQ_ATS − M0Q_ATS | LL | 0.0108 | 0.0082 | -0.0220 | 0.0430 | 4/8 | NOT MATERIAL | 0.0075 | 0.0120 | 0.0105 | 0.0163 | 0.0079 |
| H2b upstream sharing, ATS | B8–B24 | SHQ_ATS − M0Q_ATS | Brier | 0.0050 | 0.0034 | -0.0082 | 0.0199 | 4/8 | NOT MATERIAL | 0.0036 | 0.0052 | 0.0051 | 0.0069 | 0.0043 |
| H2b upstream sharing, ATS | B8–B24 | SHQ_ATS − M0Q_ATS | BA | -0.0104 | 0.0083 | -0.0556 | 0.0179 | 3/8 | NOT MATERIAL | -0.0075 | -0.0106 | -0.0105 | -0.0115 | -0.0117 |
| H3 E1 probability map | B8–B60 | E1CAL − E1RAW | LL | -0.0009 | 0.0052 | -0.0292 | 0.0166 | 4/8 | NOT MATERIAL | -0.0242 | 0.0129 | 0.0005 | -0.0194 | 0.0259 |
| H3 E1 probability map | B8–B60 | E1CAL − E1RAW | Brier | 0.0082 | 0.0009 | 0.0038 | 0.0110 | 0/8 | NOT MATERIAL | 0.0024 | 0.0118 | 0.0092 | 0.0029 | 0.0146 |
| H3 E1 probability map | B8–B60 | E1CAL − E1RAW | BA | -0.0054 | 0.0016 | -0.0120 | 0.0002 | 1/8 | NOT MATERIAL | -0.0078 | -0.0042 | -0.0058 | -0.0041 | -0.0054 |
| H3 E1 probability map | B8–B24 | E1CAL − E1RAW | LL | -0.0308 | 0.0108 | -0.0769 | 0.0026 | 6/8 | NOT MATERIAL | -0.0536 | -0.0250 | -0.0262 | -0.0432 | -0.0062 |
| H3 E1 probability map | B8–B24 | E1CAL − E1RAW | Brier | 0.0087 | 0.0020 | 0.0030 | 0.0181 | 0/8 | NOT MATERIAL | 0.0047 | 0.0112 | 0.0089 | 0.0037 | 0.0149 |
| H3 E1 probability map | B8–B24 | E1CAL − E1RAW | BA | -0.0092 | 0.0047 | -0.0300 | 0.0063 | 2/8 | NOT MATERIAL | -0.0121 | -0.0070 | -0.0114 | -0.0066 | -0.0091 |
| H4 depth representation (calibrated) | B8–B60 | M0Q_A − E1CAL | LL | -0.0164 | 0.0032 | -0.0287 | -0.0029 | 8/8 | MATERIAL | 0.0149 | -0.0323 | -0.0329 | -0.0009 | -0.0308 |
| H4 depth representation (calibrated) | B8–B60 | M0Q_A − E1CAL | Brier | -0.0013 | 0.0010 | -0.0053 | 0.0029 | 5/8 | NOT MATERIAL | 0.0070 | -0.0052 | -0.0046 | 0.0019 | -0.0056 |
| H4 depth representation (calibrated) | B8–B60 | M0Q_A − E1CAL | BA | -0.0041 | 0.0013 | -0.0080 | 0.0026 | 1/8 | NOT MATERIAL | -0.0076 | -0.0055 | -0.0021 | -0.0040 | -0.0013 |
| H4 depth representation (calibrated) | B8–B24 | M0Q_A − E1CAL | LL | 0.0051 | 0.0065 | -0.0226 | 0.0282 | 3/8 | NOT MATERIAL | 0.0113 | 0.0069 | -0.0062 | 0.0111 | 0.0023 |
| H4 depth representation (calibrated) | B8–B24 | M0Q_A − E1CAL | Brier | 0.0092 | 0.0020 | 0.0006 | 0.0185 | 0/8 | NOT MATERIAL | 0.0133 | 0.0091 | 0.0068 | 0.0099 | 0.0069 |
| H4 depth representation (calibrated) | B8–B24 | M0Q_A − E1CAL | BA | -0.0101 | 0.0027 | -0.0191 | 0.0061 | 1/8 | MATERIAL HARM | -0.0140 | -0.0137 | -0.0076 | -0.0095 | -0.0057 |
| H5 approximation vs honest | B8–B60 | ATSAPPROX − SHQ_ATS | LL | -0.0199 | 0.0033 | -0.0333 | -0.0048 | 8/8 | MATERIAL | -0.0203 | -0.0208 | -0.0188 | -0.0174 | -0.0220 |
| H5 approximation vs honest | B8–B60 | ATSAPPROX − SHQ_ATS | Brier | -0.0064 | 0.0014 | -0.0129 | -0.0007 | 8/8 | NOT MATERIAL | -0.0066 | -0.0071 | -0.0060 | -0.0056 | -0.0068 |
| H5 approximation vs honest | B8–B60 | ATSAPPROX − SHQ_ATS | BA | 0.0100 | 0.0034 | 0.0001 | 0.0293 | 8/8 | MATERIAL | 0.0099 | 0.0109 | 0.0088 | 0.0095 | 0.0109 |
| H5 approximation vs honest | B8–B24 | ATSAPPROX − SHQ_ATS | LL | -0.0441 | 0.0096 | -0.0843 | -0.0017 | 8/8 | MATERIAL | -0.0432 | -0.0505 | -0.0410 | -0.0390 | -0.0466 |
| H5 approximation vs honest | B8–B24 | ATSAPPROX − SHQ_ATS | Brier | -0.0159 | 0.0039 | -0.0345 | 0.0001 | 7/8 | MATERIAL | -0.0157 | -0.0182 | -0.0148 | -0.0142 | -0.0167 |
| H5 approximation vs honest | B8–B24 | ATSAPPROX − SHQ_ATS | BA | 0.0263 | 0.0098 | -0.0027 | 0.0829 | 6/8 | NOT MATERIAL | 0.0256 | 0.0301 | 0.0242 | 0.0233 | 0.0283 |
| H6 V1 log h in the classifier (ATS) | B8–B60 | SHQ_ATS_H − SHQ_ATS | LL | -0.0197 | 0.0014 | -0.0256 | -0.0136 | 8/8 | MATERIAL | -0.0171 | -0.0211 | -0.0200 | -0.0202 | -0.0201 |
| H6 V1 log h in the classifier (ATS) | B8–B60 | SHQ_ATS_H − SHQ_ATS | Brier | -0.0052 | 0.0005 | -0.0069 | -0.0030 | 8/8 | NOT MATERIAL | -0.0048 | -0.0055 | -0.0051 | -0.0054 | -0.0051 |
| H6 V1 log h in the classifier (ATS) | B8–B60 | SHQ_ATS_H − SHQ_ATS | BA | 0.0081 | 0.0012 | 0.0042 | 0.0137 | 8/8 | NOT MATERIAL | 0.0076 | 0.0080 | 0.0077 | 0.0090 | 0.0083 |
| H6 V1 log h in the classifier (ATS) | B8–B24 | SHQ_ATS_H − SHQ_ATS | LL | -0.0356 | 0.0038 | -0.0476 | -0.0223 | 8/8 | MATERIAL | -0.0344 | -0.0392 | -0.0344 | -0.0376 | -0.0323 |
| H6 V1 log h in the classifier (ATS) | B8–B24 | SHQ_ATS_H − SHQ_ATS | Brier | -0.0119 | 0.0014 | -0.0165 | -0.0066 | 8/8 | MATERIAL | -0.0118 | -0.0127 | -0.0114 | -0.0126 | -0.0108 |
| H6 V1 log h in the classifier (ATS) | B8–B24 | SHQ_ATS_H − SHQ_ATS | BA | 0.0192 | 0.0033 | 0.0097 | 0.0363 | 8/8 | MATERIAL | 0.0194 | 0.0199 | 0.0188 | 0.0202 | 0.0176 |
| H6 V1 log h in the classifier (A only) | B8–B60 | SHQ_A_H − SHQ_A | LL | -0.0457 | 0.0025 | -0.0581 | -0.0394 | 8/8 | MATERIAL | -0.0459 | -0.0456 | -0.0439 | -0.0473 | -0.0459 |
| H6 V1 log h in the classifier (A only) | B8–B60 | SHQ_A_H − SHQ_A | Brier | -0.0124 | 0.0008 | -0.0165 | -0.0099 | 8/8 | MATERIAL | -0.0132 | -0.0124 | -0.0120 | -0.0125 | -0.0121 |
| H6 V1 log h in the classifier (A only) | B8–B60 | SHQ_A_H − SHQ_A | BA | 0.0172 | 0.0015 | 0.0113 | 0.0248 | 8/8 | MATERIAL | 0.0225 | 0.0144 | 0.0169 | 0.0181 | 0.0140 |
| H6 V1 log h in the classifier (A only) | B8–B24 | SHQ_A_H − SHQ_A | LL | -0.0760 | 0.0065 | -0.1045 | -0.0559 | 8/8 | MATERIAL | -0.0793 | -0.0794 | -0.0706 | -0.0774 | -0.0732 |
| H6 V1 log h in the classifier (A only) | B8–B24 | SHQ_A_H − SHQ_A | Brier | -0.0248 | 0.0023 | -0.0344 | -0.0171 | 8/8 | MATERIAL | -0.0266 | -0.0256 | -0.0230 | -0.0251 | -0.0237 |
| H6 V1 log h in the classifier (A only) | B8–B24 | SHQ_A_H − SHQ_A | BA | 0.0347 | 0.0047 | 0.0158 | 0.0530 | 8/8 | MATERIAL | 0.0448 | 0.0294 | 0.0330 | 0.0373 | 0.0288 |
| H7 V2 log-h mean emulators (ATS) | B8–B60 | SHQT_ATS − SHQ_ATS | LL | 0.0027 | 0.0037 | -0.0114 | 0.0189 | 4/8 | NOT MATERIAL | 0.0058 | 0.0026 | -0.0006 | -0.0004 | 0.0063 |
| H7 V2 log-h mean emulators (ATS) | B8–B60 | SHQT_ATS − SHQ_ATS | Brier | -0.0009 | 0.0014 | -0.0071 | 0.0049 | 4/8 | NOT MATERIAL | 0.0004 | -0.0013 | -0.0017 | -0.0015 | -0.0005 |
| H7 V2 log-h mean emulators (ATS) | B8–B60 | SHQT_ATS − SHQ_ATS | BA | 0.0077 | 0.0034 | -0.0048 | 0.0265 | 6/8 | NOT MATERIAL | 0.0018 | 0.0099 | 0.0092 | 0.0076 | 0.0097 |
| H7 V2 log-h mean emulators (ATS) | B8–B24 | SHQT_ATS − SHQ_ATS | LL | -0.0152 | 0.0092 | -0.0523 | 0.0230 | 5/8 | NOT MATERIAL | -0.0152 | -0.0197 | -0.0129 | -0.0178 | -0.0105 |
| H7 V2 log-h mean emulators (ATS) | B8–B24 | SHQT_ATS − SHQ_ATS | Brier | -0.0083 | 0.0036 | -0.0251 | 0.0055 | 6/8 | NOT MATERIAL | -0.0077 | -0.0099 | -0.0078 | -0.0085 | -0.0074 |
| H7 V2 log-h mean emulators (ATS) | B8–B24 | SHQT_ATS − SHQ_ATS | BA | 0.0269 | 0.0091 | -0.0065 | 0.0793 | 7/8 | MATERIAL | 0.0210 | 0.0312 | 0.0276 | 0.0263 | 0.0286 |
| H7 V2 log-h mean emulators (A only) | B8–B60 | SHQT_A − SHQ_A | LL | 0.0120 | 0.0038 | -0.0044 | 0.0234 | 2/8 | NOT MATERIAL | 0.0073 | 0.0162 | 0.0097 | 0.0084 | 0.0185 |
| H7 V2 log-h mean emulators (A only) | B8–B60 | SHQT_A − SHQ_A | Brier | 0.0022 | 0.0014 | -0.0040 | 0.0064 | 2/8 | NOT MATERIAL | 0.0008 | 0.0032 | 0.0016 | 0.0016 | 0.0040 |
| H7 V2 log-h mean emulators (A only) | B8–B60 | SHQT_A − SHQ_A | BA | 0.0046 | 0.0028 | -0.0052 | 0.0151 | 5/8 | NOT MATERIAL | 0.0047 | 0.0045 | 0.0059 | 0.0039 | 0.0038 |
| H7 V2 log-h mean emulators (A only) | B8–B24 | SHQT_A − SHQ_A | LL | 0.0003 | 0.0100 | -0.0394 | 0.0266 | 3/8 | NOT MATERIAL | -0.0101 | 0.0026 | 0.0038 | -0.0026 | 0.0078 |
| H7 V2 log-h mean emulators (A only) | B8–B24 | SHQT_A − SHQ_A | Brier | -0.0021 | 0.0038 | -0.0180 | 0.0078 | 3/8 | NOT MATERIAL | -0.0055 | -0.0013 | -0.0016 | -0.0025 | 0.0003 |
| H7 V2 log-h mean emulators (A only) | B8–B24 | SHQT_A − SHQ_A | BA | 0.0184 | 0.0074 | -0.0067 | 0.0481 | 6/8 | NOT MATERIAL | 0.0227 | 0.0164 | 0.0193 | 0.0185 | 0.0152 |
| ref: RC19B confounded ATSCF − DEPTHCF | B8–B60 | SHQ_ATS − M0Q_A | LL | -0.0366 | 0.0024 | -0.0451 | -0.0250 | 8/8 | MATERIAL | -0.0412 | -0.0350 | -0.0291 | -0.0348 | -0.0426 |
| ref: RC19B confounded ATSCF − DEPTHCF | B8–B60 | SHQ_ATS − M0Q_A | Brier | -0.0094 | 0.0010 | -0.0126 | -0.0053 | 8/8 | NOT MATERIAL | -0.0110 | -0.0092 | -0.0077 | -0.0081 | -0.0110 |
| ref: RC19B confounded ATSCF − DEPTHCF | B8–B60 | SHQ_ATS − M0Q_A | BA | 0.0049 | 0.0032 | -0.0135 | 0.0141 | 7/8 | NOT MATERIAL | 0.0114 | 0.0034 | 0.0049 | 0.0024 | 0.0025 |
| ref: RC19B confounded ATSCF − DEPTHCF | B8–B24 | SHQ_ATS − M0Q_A | LL | -0.0610 | 0.0058 | -0.0817 | -0.0323 | 8/8 | MATERIAL | -0.0651 | -0.0626 | -0.0520 | -0.0555 | -0.0700 |
| ref: RC19B confounded ATSCF − DEPTHCF | B8–B24 | SHQ_ATS − M0Q_A | Brier | -0.0178 | 0.0023 | -0.0246 | -0.0081 | 8/8 | MATERIAL | -0.0194 | -0.0192 | -0.0147 | -0.0151 | -0.0204 |
| ref: RC19B confounded ATSCF − DEPTHCF | B8–B24 | SHQ_ATS − M0Q_A | BA | 0.0063 | 0.0079 | -0.0417 | 0.0253 | 6/8 | NOT MATERIAL | 0.0158 | 0.0049 | 0.0049 | 0.0023 | 0.0035 |
| ref: h only vs E1RAW | B8–B60 | HONLY − E1RAW | LL | -0.0040 | 0.0049 | -0.0335 | 0.0107 | 4/8 | NOT MATERIAL | -0.0139 | 0.0049 | -0.0113 | -0.0145 | 0.0149 |
| ref: h only vs E1RAW | B8–B60 | HONLY − E1RAW | Brier | 0.0079 | 0.0008 | 0.0035 | 0.0107 | 0/8 | NOT MATERIAL | 0.0058 | 0.0099 | 0.0077 | 0.0044 | 0.0116 |
| ref: h only vs E1RAW | B8–B60 | HONLY − E1RAW | BA | 0.0045 | 0.0014 | -0.0026 | 0.0113 | 7/8 | NOT MATERIAL | 0.0016 | 0.0044 | 0.0053 | 0.0071 | 0.0041 |
| ref: h only vs E1RAW | B8–B24 | HONLY − E1RAW | LL | -0.0569 | 0.0126 | -0.1168 | -0.0118 | 8/8 | MATERIAL | -0.0835 | -0.0550 | -0.0495 | -0.0631 | -0.0333 |
| ref: h only vs E1RAW | B8–B24 | HONLY − E1RAW | Brier | 0.0033 | 0.0021 | -0.0056 | 0.0128 | 2/8 | NOT MATERIAL | 0.0005 | 0.0034 | 0.0056 | -0.0006 | 0.0076 |
| ref: h only vs E1RAW | B8–B24 | HONLY − E1RAW | BA | 0.0240 | 0.0031 | 0.0105 | 0.0361 | 8/8 | MATERIAL | 0.0209 | 0.0225 | 0.0238 | 0.0283 | 0.0242 |
| ref: SHQ_A vs E1RAW | B8–B60 | SHQ_A − E1RAW | LL | -0.0250 | 0.0038 | -0.0432 | -0.0059 | 8/8 | MATERIAL | -0.0188 | -0.0286 | -0.0351 | -0.0239 | -0.0187 |
| ref: SHQ_A vs E1RAW | B8–B60 | SHQ_A − E1RAW | Brier | 0.0042 | 0.0010 | 0.0007 | 0.0081 | 0/8 | NOT MATERIAL | 0.0064 | 0.0033 | 0.0034 | 0.0034 | 0.0043 |
| ref: SHQ_A vs E1RAW | B8–B60 | SHQ_A − E1RAW | BA | -0.0069 | 0.0019 | -0.0164 | 0.0012 | 1/8 | NOT MATERIAL | -0.0125 | -0.0056 | -0.0066 | -0.0065 | -0.0032 |
| ref: SHQ_A vs E1RAW | B8–B24 | SHQ_A − E1RAW | LL | -0.0400 | 0.0106 | -0.0878 | 0.0092 | 7/8 | MATERIAL | -0.0548 | -0.0378 | -0.0411 | -0.0387 | -0.0275 |
| ref: SHQ_A vs E1RAW | B8–B24 | SHQ_A − E1RAW | Brier | 0.0125 | 0.0026 | 0.0019 | 0.0237 | 0/8 | MATERIAL HARM | 0.0134 | 0.0124 | 0.0125 | 0.0110 | 0.0133 |
| ref: SHQ_A vs E1RAW | B8–B24 | SHQ_A − E1RAW | BA | -0.0149 | 0.0057 | -0.0434 | 0.0067 | 1/8 | MATERIAL HARM | -0.0226 | -0.0106 | -0.0166 | -0.0163 | -0.0082 |

## 2×2 decomposition of the RC19B contrast ATSCF − DEPTHCF (LL-AULC B8–B60, all-path means per repeat)

| term | mean | se | repeats_negative |
|---|---|---|---|
| total ATSCF − DEPTHCF (SHQ_ATS − M0Q_A) | -0.0366 | 0.0024 | 8/8 |
| upstream|A | -0.0078 | 0.0030 | 6/8 |
| features|SHQ | -0.0288 | 0.0028 | 8/8 |
| features|M0Q | -0.0375 | 0.0015 | 8/8 |
| upstream|ATS | 0.0009 | 0.0030 | 4/8 |
| interaction | 0.0087 | 0.0032 | 0/8 |
| main effect features (avg of orders) | -0.0331 | 0.0016 | 8/8 |
| main effect upstream (avg of orders) | -0.0034 | 0.0025 | 6/8 |

