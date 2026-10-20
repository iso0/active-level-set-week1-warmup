# RC21 Stage 1 — matched-path model contribution (DEV; the 200 RC19B final paths; budgets 8–60 every 4)

Recomputed SHQ_ATS_H vs the RC20 c-replay cache on every replayed budget: max |Δ| = 2.98e-08 (2800 checks). SHQ_ATS_X and SHQ_ATS_H in the tables are the RC20 caches (not recomputed); E1RAW / E1CAL / ATSAPPROX / G3 are the RC19B caches.

**Development choice (pre-registered rule): NEW = None** (residual Δ BA-AULC B8–B24 -0.0006, Δ LL-AULC +0.0054; gate vs SHQ_ATS_H: {'LL': 'MATERIAL HARM', 'BA': 'MATERIAL'}).

## All-path means (mean over the 5 path types, then over 8 repeats)

| construction | LL B8–B24 | BA B8–B24 | sens B8–B24 | spec B8–B24 | Brier B8–B24 | q20_BA B8–B24 | LL B8–B60 | BA B8–B60 | sens B8–B60 | spec B8–B60 | Brier B8–B60 | q20_BA B8–B60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ATSAPPROX | 0.2169 | 0.9236 | 0.9094 | 0.9378 | 0.0590 | 0.7257 | 0.1645 | 0.9403 | 0.9292 | 0.9513 | 0.0444 | 0.7589 |
| PHR_FXMAP | 0.2254 | 0.9166 | 0.9032 | 0.9299 | 0.0631 | 0.7276 | 0.1647 | 0.9384 | 0.9282 | 0.9486 | 0.0456 | 0.7603 |
| SHQ_ATS_H | 0.2254 | 0.9165 | 0.9031 | 0.9299 | 0.0631 | 0.7275 | 0.1647 | 0.9384 | 0.9281 | 0.9486 | 0.0456 | 0.7602 |
| SHQ_ATS_X | 0.2291 | 0.9123 | 0.8954 | 0.9292 | 0.0650 | 0.7221 | 0.1696 | 0.9346 | 0.9212 | 0.9480 | 0.0473 | 0.7530 |
| PHR_NR | 0.2418 | 0.9268 | 0.9184 | 0.9351 | 0.0641 | 0.7353 | 0.1776 | 0.9421 | 0.9337 | 0.9504 | 0.0470 | 0.7627 |
| PHR | 0.2472 | 0.9261 | 0.9164 | 0.9358 | 0.0654 | 0.7335 | 0.1804 | 0.9416 | 0.9325 | 0.9508 | 0.0476 | 0.7614 |
| PHR_FX | 0.2677 | 0.9166 | 0.9032 | 0.9299 | 0.0719 | 0.7276 | 0.1897 | 0.9384 | 0.9282 | 0.9486 | 0.0500 | 0.7603 |
| E1CAL | 0.3170 | 0.9011 | 0.8928 | 0.9095 | 0.0835 | 0.7077 | 0.2373 | 0.9295 | 0.9170 | 0.9420 | 0.0615 | 0.7485 |
| E1RAW | 0.3478 | 0.9104 | 0.9309 | 0.8898 | 0.0749 | 0.7018 | 0.2382 | 0.9349 | 0.9400 | 0.9298 | 0.0534 | 0.7469 |
| G3 | 0.4233 | 0.8458 | 0.8254 | 0.8662 | 0.1287 | 0.6700 | 0.3679 | 0.8738 | 0.8490 | 0.8987 | 0.1102 | 0.6976 |

## Contrasts (MATERIAL iff mean Δ ≤ −0.010 in LL / Brier, ≥ +0.010 in BA / recalls, favourable in ≥ 7/8 repeats)

| contrast_id | window | contrast | metric | mean | se | min | max | repeats_favourable | label | path_E1S | path_ATSCF_MARGIN | path_DEPTHCF_MARGIN | path_G3_MARGIN | path_ATSAPPROX_MARGIN |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 new combination vs RC20 candidate | B8–B24 | PHR − SHQ_ATS_H | LL | 0.0218 | 0.0039 | -0.0030 | 0.0313 | 1/8 | MATERIAL HARM | 0.0212 | 0.0197 | 0.0243 | 0.0152 | 0.0285 |
| S1 new combination vs RC20 candidate | B8–B24 | PHR − SHQ_ATS_H | BA | 0.0096 | 0.0025 | 0.0026 | 0.0224 | 8/8 | NOT MATERIAL | 0.0099 | 0.0089 | 0.0090 | 0.0106 | 0.0096 |
| S1 new combination vs RC20 candidate | B8–B24 | PHR − SHQ_ATS_H | sens | 0.0133 | 0.0037 | 0.0028 | 0.0327 | 8/8 | MATERIAL | 0.0187 | 0.0098 | 0.0107 | 0.0154 | 0.0122 |
| S1 new combination vs RC20 candidate | B8–B24 | PHR − SHQ_ATS_H | spec | 0.0059 | 0.0030 | -0.0047 | 0.0205 | 6/8 | NOT MATERIAL | 0.0011 | 0.0081 | 0.0074 | 0.0058 | 0.0070 |
| S1 new combination vs RC20 candidate | B8–B24 | PHR − SHQ_ATS_H | Brier | 0.0023 | 0.0014 | -0.0066 | 0.0065 | 1/8 | NOT MATERIAL | 0.0026 | 0.0018 | 0.0024 | 0.0007 | 0.0038 |
| S1 new combination vs RC20 candidate | B8–B60 | PHR − SHQ_ATS_H | LL | 0.0157 | 0.0016 | 0.0060 | 0.0199 | 0/8 | MATERIAL HARM | 0.0131 | 0.0161 | 0.0182 | 0.0099 | 0.0212 |
| S1 new combination vs RC20 candidate | B8–B60 | PHR − SHQ_ATS_H | BA | 0.0032 | 0.0009 | 0.0008 | 0.0079 | 8/8 | NOT MATERIAL | 0.0044 | 0.0024 | 0.0028 | 0.0038 | 0.0029 |
| S1 new combination vs RC20 candidate | B8–B60 | PHR − SHQ_ATS_H | sens | 0.0044 | 0.0012 | 0.0007 | 0.0104 | 8/8 | NOT MATERIAL | 0.0088 | 0.0021 | 0.0021 | 0.0054 | 0.0033 |
| S1 new combination vs RC20 candidate | B8–B60 | PHR − SHQ_ATS_H | spec | 0.0021 | 0.0012 | -0.0023 | 0.0081 | 7/8 | NOT MATERIAL | -0.0001 | 0.0026 | 0.0036 | 0.0021 | 0.0025 |
| S1 new combination vs RC20 candidate | B8–B60 | PHR − SHQ_ATS_H | Brier | 0.0020 | 0.0005 | -0.0013 | 0.0032 | 1/8 | NOT MATERIAL | 0.0018 | 0.0020 | 0.0022 | 0.0009 | 0.0030 |
| S2a intercept prior (nesting, expect 0) | B8–B24 | PHR_FXMAP − SHQ_ATS_H | LL | -0.0000 | 0.0000 | -0.0001 | 0.0001 | 4/8 | NOT MATERIAL | 0.0001 | -0.0000 | -0.0000 | -0.0000 | -0.0000 |
| S2a intercept prior (nesting, expect 0) | B8–B24 | PHR_FXMAP − SHQ_ATS_H | BA | 0.0001 | 0.0001 | -0.0002 | 0.0003 | 5/8 | NOT MATERIAL | 0.0003 | -0.0000 | -0.0000 | 0.0001 | -0.0000 |
| S2a intercept prior (nesting, expect 0) | B8–B24 | PHR_FXMAP − SHQ_ATS_H | sens | 0.0002 | 0.0001 | -0.0002 | 0.0004 | 4/8 | NOT MATERIAL | 0.0006 | 0.0000 | 0.0000 | 0.0001 | 0.0000 |
| S2a intercept prior (nesting, expect 0) | B8–B24 | PHR_FXMAP − SHQ_ATS_H | spec | -0.0000 | 0.0001 | -0.0003 | 0.0001 | 3/8 | NOT MATERIAL | -0.0001 | -0.0001 | -0.0001 | 0.0001 | -0.0001 |
| S2a intercept prior (nesting, expect 0) | B8–B24 | PHR_FXMAP − SHQ_ATS_H | Brier | -0.0000 | 0.0000 | -0.0001 | 0.0000 | 5/8 | NOT MATERIAL | -0.0000 | -0.0000 | -0.0000 | -0.0000 | -0.0000 |
| S2a intercept prior (nesting, expect 0) | B8–B60 | PHR_FXMAP − SHQ_ATS_H | LL | 0.0000 | 0.0000 | -0.0000 | 0.0000 | 3/8 | NOT MATERIAL | 0.0001 | -0.0000 | -0.0000 | 0.0000 | -0.0000 |
| S2a intercept prior (nesting, expect 0) | B8–B60 | PHR_FXMAP − SHQ_ATS_H | BA | 0.0000 | 0.0000 | -0.0001 | 0.0001 | 5/8 | NOT MATERIAL | 0.0001 | -0.0000 | -0.0000 | 0.0001 | -0.0000 |
| S2a intercept prior (nesting, expect 0) | B8–B60 | PHR_FXMAP − SHQ_ATS_H | sens | 0.0001 | 0.0000 | -0.0001 | 0.0002 | 5/8 | NOT MATERIAL | 0.0002 | 0.0000 | -0.0000 | 0.0002 | 0.0000 |
| S2a intercept prior (nesting, expect 0) | B8–B60 | PHR_FXMAP − SHQ_ATS_H | spec | -0.0000 | 0.0000 | -0.0001 | 0.0000 | 2/8 | NOT MATERIAL | -0.0001 | -0.0000 | -0.0000 | 0.0000 | -0.0000 |
| S2a intercept prior (nesting, expect 0) | B8–B60 | PHR_FXMAP − SHQ_ATS_H | Brier | -0.0000 | 0.0000 | -0.0000 | 0.0000 | 5/8 | NOT MATERIAL | 0.0000 | -0.0000 | -0.0000 | -0.0000 | -0.0000 |
| S2b latent integration | B8–B24 | PHR_FX − PHR_FXMAP | LL | 0.0423 | 0.0033 | 0.0213 | 0.0495 | 0/8 | MATERIAL HARM | 0.0416 | 0.0425 | 0.0428 | 0.0371 | 0.0474 |
| S2b latent integration | B8–B24 | PHR_FX − PHR_FXMAP | BA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/8 | NOT MATERIAL | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| S2b latent integration | B8–B24 | PHR_FX − PHR_FXMAP | sens | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/8 | NOT MATERIAL | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| S2b latent integration | B8–B24 | PHR_FX − PHR_FXMAP | spec | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/8 | NOT MATERIAL | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| S2b latent integration | B8–B24 | PHR_FX − PHR_FXMAP | Brier | 0.0089 | 0.0012 | 0.0017 | 0.0119 | 0/8 | NOT MATERIAL | 0.0091 | 0.0090 | 0.0086 | 0.0076 | 0.0100 |
| S2b latent integration | B8–B60 | PHR_FX − PHR_FXMAP | LL | 0.0251 | 0.0015 | 0.0165 | 0.0294 | 0/8 | MATERIAL HARM | 0.0247 | 0.0248 | 0.0263 | 0.0209 | 0.0286 |
| S2b latent integration | B8–B60 | PHR_FX − PHR_FXMAP | BA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/8 | NOT MATERIAL | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| S2b latent integration | B8–B60 | PHR_FX − PHR_FXMAP | sens | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/8 | NOT MATERIAL | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| S2b latent integration | B8–B60 | PHR_FX − PHR_FXMAP | spec | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0/8 | NOT MATERIAL | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| S2b latent integration | B8–B60 | PHR_FX − PHR_FXMAP | Brier | 0.0043 | 0.0004 | 0.0017 | 0.0054 | 0/8 | NOT MATERIAL | 0.0046 | 0.0043 | 0.0044 | 0.0035 | 0.0050 |
| S2c learned regularisation | B8–B24 | PHR_NR − PHR_FX | LL | -0.0258 | 0.0013 | -0.0332 | -0.0214 | 8/8 | MATERIAL | -0.0261 | -0.0281 | -0.0240 | -0.0270 | -0.0241 |
| S2c learned regularisation | B8–B24 | PHR_NR − PHR_FX | BA | 0.0102 | 0.0026 | 0.0026 | 0.0235 | 8/8 | MATERIAL | 0.0102 | 0.0089 | 0.0099 | 0.0112 | 0.0108 |
| S2c learned regularisation | B8–B24 | PHR_NR − PHR_FX | sens | 0.0152 | 0.0040 | 0.0032 | 0.0345 | 8/8 | MATERIAL | 0.0199 | 0.0107 | 0.0132 | 0.0171 | 0.0150 |
| S2c learned regularisation | B8–B24 | PHR_NR − PHR_FX | spec | 0.0052 | 0.0026 | -0.0043 | 0.0172 | 6/8 | NOT MATERIAL | 0.0004 | 0.0071 | 0.0065 | 0.0052 | 0.0066 |
| S2c learned regularisation | B8–B24 | PHR_NR − PHR_FX | Brier | -0.0078 | 0.0005 | -0.0107 | -0.0058 | 8/8 | NOT MATERIAL | -0.0078 | -0.0084 | -0.0075 | -0.0079 | -0.0074 |
| S2c learned regularisation | B8–B60 | PHR_NR − PHR_FX | LL | -0.0121 | 0.0005 | -0.0153 | -0.0104 | 8/8 | MATERIAL | -0.0143 | -0.0116 | -0.0111 | -0.0134 | -0.0103 |
| S2c learned regularisation | B8–B60 | PHR_NR − PHR_FX | BA | 0.0036 | 0.0009 | 0.0011 | 0.0088 | 8/8 | NOT MATERIAL | 0.0042 | 0.0026 | 0.0031 | 0.0042 | 0.0041 |
| S2c learned regularisation | B8–B60 | PHR_NR − PHR_FX | sens | 0.0055 | 0.0014 | 0.0009 | 0.0111 | 8/8 | NOT MATERIAL | 0.0091 | 0.0031 | 0.0032 | 0.0067 | 0.0053 |
| S2c learned regularisation | B8–B60 | PHR_NR − PHR_FX | spec | 0.0018 | 0.0010 | -0.0027 | 0.0066 | 6/8 | NOT MATERIAL | -0.0006 | 0.0021 | 0.0031 | 0.0017 | 0.0029 |
| S2c learned regularisation | B8–B60 | PHR_NR − PHR_FX | Brier | -0.0029 | 0.0002 | -0.0040 | -0.0025 | 8/8 | NOT MATERIAL | -0.0033 | -0.0029 | -0.0029 | -0.0030 | -0.0026 |
| S2d transverse residual | B8–B24 | PHR − PHR_NR | LL | 0.0054 | 0.0004 | 0.0033 | 0.0068 | 0/8 | NOT MATERIAL | 0.0057 | 0.0052 | 0.0056 | 0.0050 | 0.0052 |
| S2d transverse residual | B8–B24 | PHR − PHR_NR | BA | -0.0006 | 0.0003 | -0.0023 | 0.0009 | 1/8 | NOT MATERIAL | -0.0006 | 0.0001 | -0.0008 | -0.0007 | -0.0012 |
| S2d transverse residual | B8–B24 | PHR − PHR_NR | sens | -0.0020 | 0.0006 | -0.0059 | -0.0006 | 0/8 | NOT MATERIAL | -0.0019 | -0.0009 | -0.0025 | -0.0019 | -0.0028 |
| S2d transverse residual | B8–B24 | PHR − PHR_NR | spec | 0.0007 | 0.0005 | -0.0013 | 0.0031 | 5/8 | NOT MATERIAL | 0.0007 | 0.0010 | 0.0009 | 0.0004 | 0.0004 |
| S2d transverse residual | B8–B24 | PHR − PHR_NR | Brier | 0.0012 | 0.0002 | 0.0003 | 0.0019 | 0/8 | NOT MATERIAL | 0.0014 | 0.0012 | 0.0013 | 0.0011 | 0.0012 |
| S2d transverse residual | B8–B60 | PHR − PHR_NR | LL | 0.0028 | 0.0002 | 0.0020 | 0.0034 | 0/8 | NOT MATERIAL | 0.0026 | 0.0029 | 0.0030 | 0.0024 | 0.0029 |
| S2d transverse residual | B8–B60 | PHR − PHR_NR | BA | -0.0004 | 0.0002 | -0.0014 | 0.0001 | 2/8 | NOT MATERIAL | 0.0001 | -0.0003 | -0.0003 | -0.0005 | -0.0011 |
| S2d transverse residual | B8–B60 | PHR − PHR_NR | sens | -0.0012 | 0.0004 | -0.0035 | -0.0003 | 0/8 | NOT MATERIAL | -0.0005 | -0.0010 | -0.0010 | -0.0015 | -0.0020 |
| S2d transverse residual | B8–B60 | PHR − PHR_NR | spec | 0.0003 | 0.0003 | -0.0012 | 0.0015 | 6/8 | NOT MATERIAL | 0.0006 | 0.0005 | 0.0005 | 0.0004 | -0.0003 |
| S2d transverse residual | B8–B60 | PHR − PHR_NR | Brier | 0.0006 | 0.0001 | 0.0002 | 0.0008 | 0/8 | NOT MATERIAL | 0.0005 | 0.0006 | 0.0007 | 0.0005 | 0.0006 |
| S3a new vs generic exact inputs | B8–B24 | PHR − SHQ_ATS_X | LL | 0.0182 | 0.0034 | 0.0016 | 0.0268 | 0/8 | MATERIAL HARM | 0.0151 | 0.0165 | 0.0201 | 0.0148 | 0.0243 |
| S3a new vs generic exact inputs | B8–B24 | PHR − SHQ_ATS_X | BA | 0.0138 | 0.0042 | 0.0002 | 0.0376 | 8/8 | MATERIAL | 0.0151 | 0.0131 | 0.0132 | 0.0124 | 0.0152 |
| S3a new vs generic exact inputs | B8–B24 | PHR − SHQ_ATS_X | sens | 0.0210 | 0.0041 | 0.0095 | 0.0457 | 8/8 | MATERIAL | 0.0283 | 0.0154 | 0.0184 | 0.0218 | 0.0212 |
| S3a new vs generic exact inputs | B8–B24 | PHR − SHQ_ATS_X | spec | 0.0066 | 0.0047 | -0.0091 | 0.0294 | 6/8 | NOT MATERIAL | 0.0019 | 0.0108 | 0.0080 | 0.0030 | 0.0092 |
| S3a new vs generic exact inputs | B8–B24 | PHR − SHQ_ATS_X | Brier | 0.0004 | 0.0014 | -0.0076 | 0.0038 | 2/8 | NOT MATERIAL | 0.0001 | 0.0001 | 0.0006 | -0.0003 | 0.0016 |
| S3a new vs generic exact inputs | B8–B60 | PHR − SHQ_ATS_X | LL | 0.0108 | 0.0010 | 0.0062 | 0.0153 | 0/8 | MATERIAL HARM | 0.0076 | 0.0111 | 0.0130 | 0.0066 | 0.0156 |
| S3a new vs generic exact inputs | B8–B60 | PHR − SHQ_ATS_X | BA | 0.0070 | 0.0016 | 0.0009 | 0.0158 | 8/8 | NOT MATERIAL | 0.0083 | 0.0063 | 0.0068 | 0.0057 | 0.0080 |
| S3a new vs generic exact inputs | B8–B60 | PHR − SHQ_ATS_X | sens | 0.0113 | 0.0017 | 0.0050 | 0.0197 | 8/8 | MATERIAL | 0.0159 | 0.0091 | 0.0090 | 0.0109 | 0.0116 |
| S3a new vs generic exact inputs | B8–B60 | PHR − SHQ_ATS_X | spec | 0.0027 | 0.0018 | -0.0032 | 0.0119 | 6/8 | NOT MATERIAL | 0.0007 | 0.0036 | 0.0046 | 0.0004 | 0.0043 |
| S3a new vs generic exact inputs | B8–B60 | PHR − SHQ_ATS_X | Brier | 0.0003 | 0.0005 | -0.0025 | 0.0014 | 2/8 | NOT MATERIAL | -0.0002 | 0.0005 | 0.0005 | -0.0004 | 0.0009 |
| S3b generic inputs vs h (RC20 control, cached) | B8–B24 | SHQ_ATS_X − SHQ_ATS_H | LL | 0.0036 | 0.0035 | -0.0137 | 0.0201 | 2/8 | NOT MATERIAL | 0.0061 | 0.0032 | 0.0042 | 0.0004 | 0.0042 |
| S3b generic inputs vs h (RC20 control, cached) | B8–B24 | SHQ_ATS_X − SHQ_ATS_H | BA | -0.0042 | 0.0039 | -0.0170 | 0.0180 | 2/8 | NOT MATERIAL | -0.0052 | -0.0042 | -0.0042 | -0.0018 | -0.0056 |
| S3b generic inputs vs h (RC20 control, cached) | B8–B24 | SHQ_ATS_X − SHQ_ATS_H | sens | -0.0077 | 0.0051 | -0.0213 | 0.0231 | 2/8 | NOT MATERIAL | -0.0096 | -0.0056 | -0.0077 | -0.0065 | -0.0090 |
| S3b generic inputs vs h (RC20 control, cached) | B8–B24 | SHQ_ATS_X − SHQ_ATS_H | spec | -0.0007 | 0.0035 | -0.0165 | 0.0131 | 2/8 | NOT MATERIAL | -0.0008 | -0.0028 | -0.0006 | 0.0028 | -0.0022 |
| S3b generic inputs vs h (RC20 control, cached) | B8–B24 | SHQ_ATS_X − SHQ_ATS_H | Brier | 0.0019 | 0.0017 | -0.0066 | 0.0090 | 3/8 | NOT MATERIAL | 0.0026 | 0.0017 | 0.0019 | 0.0010 | 0.0022 |
| S3b generic inputs vs h (RC20 control, cached) | B8–B60 | SHQ_ATS_X − SHQ_ATS_H | LL | 0.0049 | 0.0017 | -0.0037 | 0.0123 | 1/8 | NOT MATERIAL | 0.0054 | 0.0051 | 0.0052 | 0.0033 | 0.0056 |
| S3b generic inputs vs h (RC20 control, cached) | B8–B60 | SHQ_ATS_X − SHQ_ATS_H | BA | -0.0038 | 0.0016 | -0.0083 | 0.0054 | 1/8 | NOT MATERIAL | -0.0039 | -0.0040 | -0.0040 | -0.0019 | -0.0051 |
| S3b generic inputs vs h (RC20 control, cached) | B8–B60 | SHQ_ATS_X − SHQ_ATS_H | sens | -0.0069 | 0.0021 | -0.0123 | 0.0054 | 1/8 | NOT MATERIAL | -0.0070 | -0.0069 | -0.0069 | -0.0055 | -0.0084 |
| S3b generic inputs vs h (RC20 control, cached) | B8–B60 | SHQ_ATS_X − SHQ_ATS_H | spec | -0.0006 | 0.0014 | -0.0071 | 0.0054 | 2/8 | NOT MATERIAL | -0.0008 | -0.0010 | -0.0011 | 0.0017 | -0.0018 |
| S3b generic inputs vs h (RC20 control, cached) | B8–B60 | SHQ_ATS_X − SHQ_ATS_H | Brier | 0.0017 | 0.0007 | -0.0022 | 0.0049 | 1/8 | NOT MATERIAL | 0.0019 | 0.0014 | 0.0017 | 0.0013 | 0.0021 |
| S4a vs ATSAPPROX | B8–B24 | PHR − ATSAPPROX | LL | 0.0303 | 0.0058 | 0.0096 | 0.0531 | 0/8 | MATERIAL HARM | 0.0300 | 0.0309 | 0.0310 | 0.0167 | 0.0428 |
| S4a vs ATSAPPROX | B8–B24 | PHR − ATSAPPROX | BA | 0.0025 | 0.0055 | -0.0283 | 0.0173 | 5/8 | NOT MATERIAL | 0.0036 | -0.0013 | 0.0037 | 0.0075 | -0.0010 |
| S4a vs ATSAPPROX | B8–B24 | PHR − ATSAPPROX | sens | 0.0070 | 0.0077 | -0.0268 | 0.0311 | 5/8 | NOT MATERIAL | 0.0164 | -0.0014 | 0.0077 | 0.0133 | -0.0013 |
| S4a vs ATSAPPROX | B8–B24 | PHR − ATSAPPROX | spec | -0.0019 | 0.0043 | -0.0299 | 0.0103 | 6/8 | NOT MATERIAL | -0.0091 | -0.0012 | -0.0003 | 0.0017 | -0.0008 |
| S4a vs ATSAPPROX | B8–B24 | PHR − ATSAPPROX | Brier | 0.0063 | 0.0023 | -0.0015 | 0.0174 | 2/8 | NOT MATERIAL | 0.0066 | 0.0073 | 0.0058 | 0.0023 | 0.0097 |
| S4a vs ATSAPPROX | B8–B60 | PHR − ATSAPPROX | LL | 0.0159 | 0.0021 | 0.0055 | 0.0222 | 0/8 | MATERIAL HARM | 0.0163 | 0.0158 | 0.0170 | 0.0072 | 0.0231 |
| S4a vs ATSAPPROX | B8–B60 | PHR − ATSAPPROX | BA | 0.0014 | 0.0018 | -0.0092 | 0.0068 | 6/8 | NOT MATERIAL | 0.0020 | -0.0005 | 0.0018 | 0.0033 | 0.0002 |
| S4a vs ATSAPPROX | B8–B60 | PHR − ATSAPPROX | sens | 0.0032 | 0.0027 | -0.0090 | 0.0139 | 6/8 | NOT MATERIAL | 0.0084 | 0.0000 | 0.0018 | 0.0063 | -0.0004 |
| S4a vs ATSAPPROX | B8–B60 | PHR − ATSAPPROX | spec | -0.0005 | 0.0014 | -0.0095 | 0.0034 | 4/8 | NOT MATERIAL | -0.0043 | -0.0010 | 0.0018 | 0.0002 | 0.0008 |
| S4a vs ATSAPPROX | B8–B60 | PHR − ATSAPPROX | Brier | 0.0032 | 0.0008 | 0.0003 | 0.0070 | 0/8 | NOT MATERIAL | 0.0035 | 0.0035 | 0.0031 | 0.0011 | 0.0047 |
| S4b vs E1CAL | B8–B24 | PHR − E1CAL | LL | -0.0698 | 0.0084 | -0.0966 | -0.0291 | 8/8 | MATERIAL | -0.0670 | -0.0753 | -0.0682 | -0.0667 | -0.0715 |
| S4b vs E1CAL | B8–B24 | PHR − E1CAL | BA | 0.0250 | 0.0055 | 0.0012 | 0.0554 | 8/8 | MATERIAL | 0.0310 | 0.0199 | 0.0253 | 0.0237 | 0.0250 |
| S4b vs E1CAL | B8–B24 | PHR − E1CAL | sens | 0.0236 | 0.0078 | -0.0150 | 0.0506 | 7/8 | MATERIAL | 0.0336 | 0.0146 | 0.0260 | 0.0198 | 0.0240 |
| S4b vs E1CAL | B8–B24 | PHR − E1CAL | spec | 0.0263 | 0.0062 | 0.0065 | 0.0602 | 8/8 | MATERIAL | 0.0283 | 0.0252 | 0.0245 | 0.0275 | 0.0260 |
| S4b vs E1CAL | B8–B24 | PHR − E1CAL | Brier | -0.0182 | 0.0024 | -0.0253 | -0.0075 | 8/8 | MATERIAL | -0.0152 | -0.0211 | -0.0169 | -0.0171 | -0.0205 |
| S4b vs E1CAL | B8–B60 | PHR − E1CAL | LL | -0.0570 | 0.0041 | -0.0690 | -0.0333 | 8/8 | MATERIAL | -0.0304 | -0.0723 | -0.0639 | -0.0460 | -0.0723 |
| S4b vs E1CAL | B8–B60 | PHR − E1CAL | BA | 0.0122 | 0.0020 | 0.0026 | 0.0220 | 8/8 | MATERIAL | 0.0157 | 0.0083 | 0.0133 | 0.0111 | 0.0123 |
| S4b vs E1CAL | B8–B60 | PHR − E1CAL | sens | 0.0155 | 0.0029 | 0.0015 | 0.0249 | 8/8 | MATERIAL | 0.0209 | 0.0085 | 0.0175 | 0.0152 | 0.0154 |
| S4b vs E1CAL | B8–B60 | PHR − E1CAL | spec | 0.0088 | 0.0020 | 0.0038 | 0.0204 | 8/8 | NOT MATERIAL | 0.0105 | 0.0080 | 0.0092 | 0.0070 | 0.0093 |
| S4b vs E1CAL | B8–B60 | PHR − E1CAL | Brier | -0.0139 | 0.0013 | -0.0170 | -0.0075 | 8/8 | MATERIAL | -0.0071 | -0.0180 | -0.0152 | -0.0107 | -0.0187 |
| S4c vs E1RAW | B8–B24 | PHR − E1RAW | LL | -0.1006 | 0.0127 | -0.1533 | -0.0532 | 8/8 | MATERIAL | -0.1206 | -0.1003 | -0.0944 | -0.1099 | -0.0777 |
| S4c vs E1RAW | B8–B24 | PHR − E1RAW | BA | 0.0157 | 0.0059 | -0.0096 | 0.0342 | 6/8 | NOT MATERIAL | 0.0189 | 0.0129 | 0.0139 | 0.0171 | 0.0159 |
| S4c vs E1RAW | B8–B24 | PHR − E1RAW | sens | -0.0145 | 0.0071 | -0.0418 | 0.0217 | 1/8 | MATERIAL HARM | -0.0091 | -0.0211 | -0.0132 | -0.0168 | -0.0124 |
| S4c vs E1RAW | B8–B24 | PHR − E1RAW | spec | 0.0460 | 0.0075 | 0.0213 | 0.0713 | 8/8 | MATERIAL | 0.0469 | 0.0469 | 0.0410 | 0.0509 | 0.0443 |
| S4c vs E1RAW | B8–B24 | PHR − E1RAW | Brier | -0.0095 | 0.0024 | -0.0176 | -0.0023 | 8/8 | NOT MATERIAL | -0.0106 | -0.0099 | -0.0080 | -0.0134 | -0.0057 |
| S4c vs E1RAW | B8–B60 | PHR − E1RAW | LL | -0.0578 | 0.0047 | -0.0818 | -0.0431 | 8/8 | MATERIAL | -0.0546 | -0.0594 | -0.0633 | -0.0654 | -0.0464 |
| S4c vs E1RAW | B8–B60 | PHR − E1RAW | BA | 0.0067 | 0.0021 | -0.0031 | 0.0128 | 7/8 | NOT MATERIAL | 0.0079 | 0.0041 | 0.0076 | 0.0070 | 0.0070 |
| S4c vs E1RAW | B8–B60 | PHR − E1RAW | sens | -0.0075 | 0.0024 | -0.0160 | 0.0053 | 1/8 | NOT MATERIAL | -0.0073 | -0.0109 | -0.0042 | -0.0102 | -0.0051 |
| S4c vs E1RAW | B8–B60 | PHR − E1RAW | spec | 0.0210 | 0.0028 | 0.0098 | 0.0314 | 8/8 | MATERIAL | 0.0231 | 0.0192 | 0.0193 | 0.0241 | 0.0190 |
| S4c vs E1RAW | B8–B60 | PHR − E1RAW | Brier | -0.0058 | 0.0007 | -0.0087 | -0.0026 | 8/8 | NOT MATERIAL | -0.0047 | -0.0062 | -0.0060 | -0.0079 | -0.0042 |
| S4d vs G3 | B8–B24 | PHR − G3 | LL | -0.1761 | 0.0072 | -0.2157 | -0.1488 | 8/8 | MATERIAL | -0.1448 | -0.2082 | -0.1648 | -0.1405 | -0.2222 |
| S4d vs G3 | B8–B24 | PHR − G3 | BA | 0.0803 | 0.0079 | 0.0545 | 0.1259 | 8/8 | MATERIAL | 0.0657 | 0.1030 | 0.0738 | 0.0411 | 0.1177 |
| S4d vs G3 | B8–B24 | PHR − G3 | sens | 0.0910 | 0.0081 | 0.0579 | 0.1354 | 8/8 | MATERIAL | 0.0821 | 0.1029 | 0.0883 | 0.0478 | 0.1336 |
| S4d vs G3 | B8–B24 | PHR − G3 | spec | 0.0696 | 0.0111 | 0.0228 | 0.1163 | 8/8 | MATERIAL | 0.0492 | 0.1031 | 0.0592 | 0.0344 | 0.1018 |
| S4d vs G3 | B8–B24 | PHR − G3 | Brier | -0.0634 | 0.0034 | -0.0825 | -0.0500 | 8/8 | MATERIAL | -0.0508 | -0.0771 | -0.0588 | -0.0456 | -0.0844 |
| S4d vs G3 | B8–B60 | PHR − G3 | LL | -0.1875 | 0.0060 | -0.2155 | -0.1650 | 8/8 | MATERIAL | -0.1098 | -0.2634 | -0.1782 | -0.0963 | -0.2898 |
| S4d vs G3 | B8–B60 | PHR − G3 | BA | 0.0678 | 0.0034 | 0.0551 | 0.0832 | 8/8 | MATERIAL | 0.0400 | 0.0994 | 0.0608 | 0.0198 | 0.1190 |
| S4d vs G3 | B8–B60 | PHR − G3 | sens | 0.0835 | 0.0042 | 0.0655 | 0.1045 | 8/8 | MATERIAL | 0.0575 | 0.1068 | 0.0847 | 0.0248 | 0.1437 |
| S4d vs G3 | B8–B60 | PHR − G3 | spec | 0.0521 | 0.0043 | 0.0345 | 0.0717 | 8/8 | MATERIAL | 0.0226 | 0.0921 | 0.0369 | 0.0148 | 0.0942 |
| S4d vs G3 | B8–B60 | PHR − G3 | Brier | -0.0626 | 0.0024 | -0.0736 | -0.0531 | 8/8 | MATERIAL | -0.0335 | -0.0916 | -0.0574 | -0.0261 | -0.1042 |
| ref: no-residual model vs RC20 candidate | B8–B24 | PHR_NR − SHQ_ATS_H | LL | 0.0164 | 0.0036 | -0.0064 | 0.0254 | 1/8 | MATERIAL HARM | 0.0155 | 0.0144 | 0.0187 | 0.0102 | 0.0233 |
| ref: no-residual model vs RC20 candidate | B8–B24 | PHR_NR − SHQ_ATS_H | BA | 0.0102 | 0.0026 | 0.0028 | 0.0238 | 8/8 | MATERIAL | 0.0105 | 0.0089 | 0.0098 | 0.0113 | 0.0108 |
| ref: no-residual model vs RC20 candidate | B8–B24 | PHR_NR − SHQ_ATS_H | sens | 0.0153 | 0.0040 | 0.0035 | 0.0345 | 8/8 | MATERIAL | 0.0206 | 0.0107 | 0.0132 | 0.0173 | 0.0150 |
| ref: no-residual model vs RC20 candidate | B8–B24 | PHR_NR − SHQ_ATS_H | spec | 0.0052 | 0.0027 | -0.0047 | 0.0173 | 6/8 | NOT MATERIAL | 0.0004 | 0.0070 | 0.0065 | 0.0054 | 0.0065 |
| ref: no-residual model vs RC20 candidate | B8–B24 | PHR_NR − SHQ_ATS_H | Brier | 0.0010 | 0.0013 | -0.0069 | 0.0049 | 2/8 | NOT MATERIAL | 0.0013 | 0.0006 | 0.0011 | -0.0004 | 0.0026 |
| ref: no-residual model vs RC20 candidate | B8–B60 | PHR_NR − SHQ_ATS_H | LL | 0.0129 | 0.0015 | 0.0040 | 0.0173 | 0/8 | MATERIAL HARM | 0.0105 | 0.0132 | 0.0152 | 0.0075 | 0.0183 |
| ref: no-residual model vs RC20 candidate | B8–B60 | PHR_NR − SHQ_ATS_H | BA | 0.0037 | 0.0009 | 0.0011 | 0.0090 | 8/8 | NOT MATERIAL | 0.0043 | 0.0026 | 0.0031 | 0.0043 | 0.0040 |
| ref: no-residual model vs RC20 candidate | B8–B60 | PHR_NR − SHQ_ATS_H | sens | 0.0055 | 0.0014 | 0.0009 | 0.0113 | 8/8 | NOT MATERIAL | 0.0093 | 0.0031 | 0.0031 | 0.0069 | 0.0053 |
| ref: no-residual model vs RC20 candidate | B8–B60 | PHR_NR − SHQ_ATS_H | spec | 0.0018 | 0.0011 | -0.0029 | 0.0066 | 6/8 | NOT MATERIAL | -0.0007 | 0.0021 | 0.0031 | 0.0017 | 0.0028 |
| ref: no-residual model vs RC20 candidate | B8–B60 | PHR_NR − SHQ_ATS_H | Brier | 0.0014 | 0.0005 | -0.0014 | 0.0026 | 1/8 | NOT MATERIAL | 0.0013 | 0.0014 | 0.0015 | 0.0005 | 0.0024 |

## Matched budgets (mean over paths and repeats)

| cons | budget | BA | sensitivity | specificity | log_loss | q20_BA | spec_NEW |
|---|---|---|---|---|---|---|---|
| ATSAPPROX | 8 | 0.891 | 0.876 | 0.907 | 0.307 | 0.671 | 0.396 |
| ATSAPPROX | 12 | 0.921 | 0.907 | 0.935 | 0.237 | 0.727 | 0.290 |
| ATSAPPROX | 16 | 0.929 | 0.914 | 0.945 | 0.199 | 0.733 | 0.260 |
| ATSAPPROX | 20 | 0.936 | 0.924 | 0.949 | 0.179 | 0.746 | 0.256 |
| ATSAPPROX | 24 | 0.940 | 0.927 | 0.953 | 0.163 | 0.753 | 0.277 |
| ATSAPPROX | 40 | 0.948 | 0.939 | 0.958 | 0.137 | 0.774 | 0.281 |
| ATSAPPROX | 60 | 0.952 | 0.943 | 0.962 | 0.124 | 0.786 | 0.350 |
| E1CAL | 8 | 0.834 | 0.855 | 0.814 | 0.509 | 0.649 | 0.208 |
| E1CAL | 12 | 0.902 | 0.896 | 0.908 | 0.320 | 0.697 | 0.410 |
| E1CAL | 16 | 0.911 | 0.891 | 0.931 | 0.280 | 0.713 | 0.452 |
| E1CAL | 20 | 0.925 | 0.906 | 0.944 | 0.250 | 0.729 | 0.471 |
| E1CAL | 24 | 0.934 | 0.916 | 0.951 | 0.226 | 0.750 | 0.496 |
| E1CAL | 40 | 0.945 | 0.931 | 0.959 | 0.193 | 0.768 | 0.460 |
| E1CAL | 60 | 0.950 | 0.937 | 0.963 | 0.184 | 0.784 | 0.463 |
| E1RAW | 8 | 0.869 | 0.920 | 0.818 | 0.545 | 0.644 | 0.177 |
| E1RAW | 12 | 0.901 | 0.930 | 0.871 | 0.390 | 0.685 | 0.277 |
| E1RAW | 16 | 0.916 | 0.927 | 0.905 | 0.309 | 0.708 | 0.335 |
| E1RAW | 20 | 0.930 | 0.938 | 0.922 | 0.264 | 0.729 | 0.362 |
| E1RAW | 24 | 0.936 | 0.940 | 0.932 | 0.232 | 0.743 | 0.392 |
| E1RAW | 40 | 0.948 | 0.945 | 0.951 | 0.179 | 0.767 | 0.396 |
| E1RAW | 60 | 0.952 | 0.946 | 0.959 | 0.162 | 0.785 | 0.442 |
| G3 | 8 | 0.809 | 0.813 | 0.805 | 0.459 | 0.640 | 0.135 |
| G3 | 12 | 0.853 | 0.843 | 0.864 | 0.434 | 0.670 | 0.196 |
| G3 | 16 | 0.848 | 0.820 | 0.876 | 0.427 | 0.670 | 0.192 |
| G3 | 20 | 0.857 | 0.825 | 0.889 | 0.406 | 0.680 | 0.231 |
| G3 | 24 | 0.862 | 0.826 | 0.897 | 0.391 | 0.691 | 0.294 |
| G3 | 40 | 0.890 | 0.863 | 0.917 | 0.352 | 0.712 | 0.237 |
| G3 | 60 | 0.920 | 0.893 | 0.948 | 0.265 | 0.748 | 0.310 |
| PHR | 8 | 0.881 | 0.864 | 0.898 | 0.368 | 0.697 | 0.198 |
| PHR | 12 | 0.935 | 0.931 | 0.938 | 0.263 | 0.737 | 0.140 |
| PHR | 16 | 0.935 | 0.924 | 0.946 | 0.224 | 0.739 | 0.138 |
| PHR | 20 | 0.938 | 0.930 | 0.947 | 0.199 | 0.743 | 0.165 |
| PHR | 24 | 0.942 | 0.932 | 0.951 | 0.181 | 0.752 | 0.192 |
| PHR | 40 | 0.949 | 0.940 | 0.958 | 0.146 | 0.772 | 0.254 |
| PHR | 60 | 0.953 | 0.943 | 0.963 | 0.127 | 0.787 | 0.335 |
| PHR_FX | 8 | 0.842 | 0.813 | 0.870 | 0.408 | 0.669 | 0.292 |
| PHR_FX | 12 | 0.929 | 0.922 | 0.935 | 0.285 | 0.735 | 0.165 |
| PHR_FX | 16 | 0.933 | 0.921 | 0.946 | 0.242 | 0.739 | 0.169 |
| PHR_FX | 20 | 0.938 | 0.928 | 0.947 | 0.212 | 0.741 | 0.179 |
| PHR_FX | 24 | 0.942 | 0.932 | 0.952 | 0.191 | 0.753 | 0.225 |
| PHR_FX | 40 | 0.949 | 0.940 | 0.958 | 0.149 | 0.774 | 0.250 |
| PHR_FX | 60 | 0.953 | 0.944 | 0.962 | 0.128 | 0.789 | 0.327 |
| PHR_FXMAP | 8 | 0.842 | 0.813 | 0.870 | 0.364 | 0.669 | 0.292 |
| PHR_FXMAP | 12 | 0.929 | 0.922 | 0.935 | 0.230 | 0.735 | 0.165 |
| PHR_FXMAP | 16 | 0.933 | 0.921 | 0.946 | 0.198 | 0.739 | 0.169 |
| PHR_FXMAP | 20 | 0.938 | 0.928 | 0.947 | 0.175 | 0.741 | 0.179 |
| PHR_FXMAP | 24 | 0.942 | 0.932 | 0.952 | 0.160 | 0.753 | 0.225 |
| PHR_FXMAP | 40 | 0.949 | 0.940 | 0.958 | 0.132 | 0.774 | 0.250 |
| PHR_FXMAP | 60 | 0.953 | 0.944 | 0.962 | 0.121 | 0.789 | 0.327 |
| PHR_NR | 8 | 0.883 | 0.869 | 0.896 | 0.361 | 0.705 | 0.167 |
| PHR_NR | 12 | 0.934 | 0.933 | 0.936 | 0.256 | 0.737 | 0.125 |
| PHR_NR | 16 | 0.936 | 0.926 | 0.946 | 0.219 | 0.740 | 0.138 |
| PHR_NR | 20 | 0.939 | 0.930 | 0.947 | 0.195 | 0.743 | 0.158 |
| PHR_NR | 24 | 0.942 | 0.934 | 0.951 | 0.178 | 0.752 | 0.183 |
| PHR_NR | 40 | 0.949 | 0.941 | 0.958 | 0.144 | 0.774 | 0.252 |
| PHR_NR | 60 | 0.954 | 0.944 | 0.963 | 0.127 | 0.791 | 0.342 |
| SHQ_ATS_H | 8 | 0.842 | 0.813 | 0.870 | 0.365 | 0.670 | 0.292 |
| SHQ_ATS_H | 12 | 0.928 | 0.922 | 0.935 | 0.230 | 0.734 | 0.165 |
| SHQ_ATS_H | 16 | 0.933 | 0.920 | 0.946 | 0.198 | 0.739 | 0.171 |
| SHQ_ATS_H | 20 | 0.938 | 0.928 | 0.947 | 0.175 | 0.742 | 0.179 |
| SHQ_ATS_H | 24 | 0.942 | 0.931 | 0.952 | 0.160 | 0.753 | 0.225 |
| SHQ_ATS_H | 40 | 0.949 | 0.940 | 0.958 | 0.132 | 0.774 | 0.250 |
| SHQ_ATS_H | 60 | 0.953 | 0.944 | 0.962 | 0.121 | 0.788 | 0.327 |
| SHQ_ATS_X | 8 | 0.846 | 0.818 | 0.873 | 0.357 | 0.674 | 0.250 |
| SHQ_ATS_X | 12 | 0.917 | 0.904 | 0.930 | 0.237 | 0.720 | 0.196 |
| SHQ_ATS_X | 16 | 0.928 | 0.912 | 0.944 | 0.203 | 0.731 | 0.179 |
| SHQ_ATS_X | 20 | 0.934 | 0.921 | 0.947 | 0.182 | 0.740 | 0.196 |
| SHQ_ATS_X | 24 | 0.937 | 0.922 | 0.952 | 0.166 | 0.746 | 0.248 |
| SHQ_ATS_X | 40 | 0.945 | 0.933 | 0.957 | 0.138 | 0.762 | 0.248 |
| SHQ_ATS_X | 60 | 0.950 | 0.939 | 0.962 | 0.126 | 0.781 | 0.323 |

## Hard fast-scan corner (NEW-batch conduction runs predicted Keyhole, summed over paths and repeats) and calibration

| cons | budget | cal_slope | ECE | corner_errors | corner_n |
|---|---|---|---|---|---|
| ATSAPPROX | 24 | 1.497 | 0.048 | 347 | 480 |
| ATSAPPROX | 60 | 1.173 | 0.026 | 312 | 480 |
| E1CAL | 24 | 1.336 | 0.071 | 242 | 480 |
| E1CAL | 60 | 1.609 | 0.075 | 258 | 480 |
| E1RAW | 24 | 0.589 | 0.044 | 292 | 480 |
| E1RAW | 60 | 0.655 | 0.028 | 268 | 480 |
| G3 | 24 | 2.117 | 0.141 | 339 | 480 |
| G3 | 60 | 2.104 | 0.113 | 331 | 480 |
| PHR | 24 | 1.716 | 0.068 | 388 | 480 |
| PHR | 60 | 1.384 | 0.034 | 319 | 480 |
| PHR_FX | 24 | 1.952 | 0.081 | 372 | 480 |
| PHR_FX | 60 | 1.459 | 0.037 | 323 | 480 |
| PHR_FXMAP | 24 | 1.478 | 0.046 | 372 | 480 |
| PHR_FXMAP | 60 | 1.189 | 0.024 | 323 | 480 |
| PHR_NR | 24 | 1.658 | 0.063 | 392 | 480 |
| PHR_NR | 60 | 1.376 | 0.033 | 316 | 480 |
| SHQ_ATS_H | 24 | 1.478 | 0.046 | 372 | 480 |
| SHQ_ATS_H | 60 | 1.188 | 0.024 | 323 | 480 |
| SHQ_ATS_X | 24 | 1.339 | 0.040 | 361 | 480 |
| SHQ_ATS_X | 60 | 1.122 | 0.023 | 325 | 480 |

## PHR posterior diagnostics by budget (means over paths and repeats)

| budget | post_residual | post_mean_tau_F | post_mean_tau_h | post_mean_sigma_r | post_mean_ell_given_res | n_configs |
|---|---|---|---|---|---|---|
| 8.000 | 0.490 | 1.798 | 2.681 | 0.560 | 1.124 | 112.000 |
| 12.000 | 0.478 | 1.805 | 2.707 | 0.535 | 1.124 | 112.000 |
| 16.000 | 0.472 | 1.669 | 2.733 | 0.523 | 1.123 | 112.000 |
| 20.000 | 0.469 | 1.597 | 2.748 | 0.516 | 1.124 | 112.000 |
| 24.000 | 0.466 | 1.564 | 2.716 | 0.509 | 1.123 | 112.000 |
| 28.000 | 0.457 | 1.547 | 2.697 | 0.490 | 1.122 | 112.000 |
| 32.000 | 0.452 | 1.510 | 2.612 | 0.481 | 1.120 | 112.000 |
| 36.000 | 0.441 | 1.565 | 2.551 | 0.458 | 1.121 | 112.000 |
| 40.000 | 0.426 | 1.595 | 2.451 | 0.431 | 1.126 | 112.000 |
| 44.000 | 0.410 | 1.556 | 2.384 | 0.403 | 1.129 | 112.000 |
| 48.000 | 0.395 | 1.534 | 2.298 | 0.376 | 1.132 | 112.000 |
| 52.000 | 0.377 | 1.500 | 2.252 | 0.346 | 1.136 | 112.000 |
| 56.000 | 0.361 | 1.543 | 2.181 | 0.320 | 1.142 | 112.000 |
| 60.000 | 0.353 | 1.582 | 2.141 | 0.306 | 1.148 | 112.000 |

## CPU per paid state (s, all RC21 constructions)

| budget | mean | max |
|---|---|---|
| 8.000 | 0.583 | 0.969 |
| 12.000 | 0.674 | 1.141 |
| 16.000 | 0.668 | 1.188 |
| 20.000 | 0.660 | 1.078 |
| 24.000 | 0.674 | 1.109 |
| 28.000 | 0.713 | 1.047 |
| 32.000 | 0.730 | 1.172 |
| 36.000 | 0.765 | 1.188 |
| 40.000 | 0.806 | 1.359 |
| 44.000 | 0.842 | 1.406 |
| 48.000 | 0.870 | 1.359 |
| 52.000 | 0.912 | 1.422 |
| 56.000 | 0.972 | 1.578 |
| 60.000 | 1.023 | 1.594 |

