# RC20 exploratory h-specificity control (registered after Stage 1; the same 200 paths and paid prefixes)

SHQ_*_X replaces log h~ by the 4 standardised exact log inputs in the same L2 logistic classifier (C = 1).

| construction | LL B8–B60 | BA B8–B60 | LL B8–B24 | BA B8–B24 |
|---|---|---|---|---|
| SHQ_A | 0.2132 | 0.9280 | 0.3078 | 0.8955 |
| SHQ_ATS | 0.1844 | 0.9303 | 0.2610 | 0.8973 |
| SHQ_ATS_H | 0.1647 | 0.9384 | 0.2254 | 0.9165 |
| SHQ_ATS_X | 0.1696 | 0.9346 | 0.2291 | 0.9123 |
| SHQ_A_H | 0.1674 | 0.9452 | 0.2318 | 0.9302 |
| SHQ_A_X | 0.1753 | 0.9368 | 0.2401 | 0.9169 |

| comparison | window | contrast | metric | mean | se | min | max | repeats_favourable | label | path_E1S | path_ATSCF_MARGIN | path_DEPTHCF_MARGIN | path_G3_MARGIN | path_ATSAPPROX_MARGIN |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| generic inputs vs log h (ATS) | B8–B60 | SHQ_ATS_X − SHQ_ATS_H | LL | 0.0049 | 0.0017 | -0.0037 | 0.0123 | 1/8 | NOT MATERIAL | 0.0054 | 0.0051 | 0.0052 | 0.0033 | 0.0056 |
| generic inputs vs log h (ATS) | B8–B60 | SHQ_ATS_X − SHQ_ATS_H | BA | -0.0038 | 0.0016 | -0.0083 | 0.0054 | 1/8 | NOT MATERIAL | -0.0039 | -0.0040 | -0.0040 | -0.0019 | -0.0051 |
| generic inputs vs log h (ATS) | B8–B24 | SHQ_ATS_X − SHQ_ATS_H | LL | 0.0036 | 0.0035 | -0.0137 | 0.0201 | 2/8 | NOT MATERIAL | 0.0061 | 0.0032 | 0.0042 | 0.0004 | 0.0042 |
| generic inputs vs log h (ATS) | B8–B24 | SHQ_ATS_X − SHQ_ATS_H | BA | -0.0042 | 0.0039 | -0.0170 | 0.0180 | 2/8 | NOT MATERIAL | -0.0052 | -0.0042 | -0.0042 | -0.0018 | -0.0056 |
| generic inputs vs log h (A) | B8–B60 | SHQ_A_X − SHQ_A_H | LL | 0.0079 | 0.0011 | 0.0042 | 0.0136 | 0/8 | NOT MATERIAL | 0.0097 | 0.0087 | 0.0081 | 0.0048 | 0.0083 |
| generic inputs vs log h (A) | B8–B60 | SHQ_A_X − SHQ_A_H | BA | -0.0084 | 0.0013 | -0.0163 | -0.0050 | 0/8 | NOT MATERIAL | -0.0093 | -0.0080 | -0.0078 | -0.0082 | -0.0089 |
| generic inputs vs log h (A) | B8–B24 | SHQ_A_X − SHQ_A_H | LL | 0.0082 | 0.0027 | 0.0016 | 0.0223 | 0/8 | NOT MATERIAL | 0.0118 | 0.0086 | 0.0083 | 0.0034 | 0.0091 |
| generic inputs vs log h (A) | B8–B24 | SHQ_A_X − SHQ_A_H | BA | -0.0132 | 0.0032 | -0.0294 | 0.0007 | 1/8 | MATERIAL HARM | -0.0153 | -0.0133 | -0.0112 | -0.0119 | -0.0146 |
| generic inputs vs none (ATS) | B8–B60 | SHQ_ATS_X − SHQ_ATS | LL | -0.0148 | 0.0016 | -0.0208 | -0.0090 | 8/8 | MATERIAL | -0.0117 | -0.0160 | -0.0149 | -0.0169 | -0.0144 |
| generic inputs vs none (ATS) | B8–B60 | SHQ_ATS_X − SHQ_ATS | BA | 0.0044 | 0.0024 | -0.0023 | 0.0191 | 6/8 | NOT MATERIAL | 0.0037 | 0.0040 | 0.0037 | 0.0071 | 0.0032 |
| generic inputs vs none (ATS) | B8–B24 | SHQ_ATS_X − SHQ_ATS | LL | -0.0319 | 0.0043 | -0.0461 | -0.0150 | 8/8 | MATERIAL | -0.0283 | -0.0361 | -0.0302 | -0.0371 | -0.0280 |
| generic inputs vs none (ATS) | B8–B24 | SHQ_ATS_X − SHQ_ATS | BA | 0.0150 | 0.0065 | -0.0005 | 0.0543 | 7/8 | MATERIAL | 0.0142 | 0.0157 | 0.0147 | 0.0184 | 0.0120 |
| log h vs none (ATS), recomputed | B8–B60 | SHQ_ATS_H − SHQ_ATS | LL | -0.0197 | 0.0014 | -0.0256 | -0.0136 | 8/8 | MATERIAL | -0.0171 | -0.0211 | -0.0200 | -0.0202 | -0.0201 |
| log h vs none (ATS), recomputed | B8–B60 | SHQ_ATS_H − SHQ_ATS | BA | 0.0081 | 0.0012 | 0.0042 | 0.0137 | 8/8 | NOT MATERIAL | 0.0076 | 0.0080 | 0.0077 | 0.0090 | 0.0083 |
| log h vs none (ATS), recomputed | B8–B24 | SHQ_ATS_H − SHQ_ATS | LL | -0.0356 | 0.0038 | -0.0476 | -0.0223 | 8/8 | MATERIAL | -0.0344 | -0.0392 | -0.0344 | -0.0376 | -0.0323 |
| log h vs none (ATS), recomputed | B8–B24 | SHQ_ATS_H − SHQ_ATS | BA | 0.0192 | 0.0033 | 0.0097 | 0.0363 | 8/8 | MATERIAL | 0.0194 | 0.0199 | 0.0188 | 0.0202 | 0.0176 |

