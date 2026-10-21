# RC23 stage 1 — mechanism on identical saved paid prefixes (RC22 acquisition paths A1 / A5, repeats 43–50; fixed paths, NOT active learning)

Reproduction of recorded RC22 probabilities: max |Δ| = 2.98e-08 (1680 checks).

## Fold-pooled AULC (mean over the 2 path types and 8 repeats)

| construction | BA small | log_loss small | sensitivity small | specificity small | BA all | log_loss all | sensitivity all | specificity all |
|---|---|---|---|---|---|---|---|---|
| RC22 reference (PHR_NRMAP) | 0.9229 | 0.1994 | 0.9106 | 0.9353 | 0.9412 | 0.1542 | 0.9331 | 0.9492 |
| RC22 candidate, shared upstream (HA_LR) | 0.9313 | 0.1877 | 0.9254 | 0.9372 | 0.9446 | 0.1493 | 0.9390 | 0.9503 |
| fully lean h + depth (HA_LEAN) | 0.9326 | 0.1885 | 0.9252 | 0.9400 | 0.9448 | 0.1508 | 0.9389 | 0.9508 |
| h only (HONLY_LR) | 0.9337 | 0.2084 | 0.9289 | 0.9384 | 0.9393 | 0.2019 | 0.9305 | 0.9482 |

## Matched contrasts (MATERIAL iff |Δ| ≥ 0.010 in the good direction and ≥ 7/8)

| window | contrast | metric | mean | se | good | label |
|---|---|---|---|---|---|---|
| small | HA_LEAN − HA_LR | BA | 0.0013 | 0.0020 | 3/8 | NOT MATERIAL |
| small | HA_LEAN − HA_LR | log_loss | 0.0009 | 0.0026 | 3/8 | NOT MATERIAL |
| small | HA_LEAN − HA_LR | sensitivity | -0.0003 | 0.0040 | 3/8 | NOT MATERIAL |
| small | HA_LEAN − HA_LR | specificity | 0.0028 | 0.0020 | 7/8 | NOT MATERIAL |
| small | HA_LEAN − HONLY_LR | BA | -0.0010 | 0.0011 | 2/8 | NOT MATERIAL |
| small | HA_LEAN − HONLY_LR | log_loss | -0.0199 | 0.0056 | 8/8 | MATERIAL |
| small | HA_LEAN − HONLY_LR | sensitivity | -0.0037 | 0.0018 | 1/8 | NOT MATERIAL |
| small | HA_LEAN − HONLY_LR | specificity | 0.0017 | 0.0016 | 5/8 | NOT MATERIAL |
| small | HA_LEAN − PHR_NRMAP | BA | 0.0097 | 0.0029 | 7/8 | NOT MATERIAL |
| small | HA_LEAN − PHR_NRMAP | log_loss | -0.0109 | 0.0041 | 7/8 | MATERIAL |
| small | HA_LEAN − PHR_NRMAP | sensitivity | 0.0146 | 0.0074 | 5/8 | NOT MATERIAL |
| small | HA_LEAN − PHR_NRMAP | specificity | 0.0048 | 0.0039 | 5/8 | NOT MATERIAL |
| small | HA_LR − PHR_NRMAP | BA | 0.0084 | 0.0029 | 7/8 | NOT MATERIAL |
| small | HA_LR − PHR_NRMAP | log_loss | -0.0118 | 0.0028 | 8/8 | MATERIAL |
| small | HA_LR − PHR_NRMAP | sensitivity | 0.0148 | 0.0058 | 8/8 | MATERIAL |
| small | HA_LR − PHR_NRMAP | specificity | 0.0020 | 0.0025 | 5/8 | NOT MATERIAL |
| small | HONLY_LR − PHR_NRMAP | BA | 0.0107 | 0.0029 | 7/8 | MATERIAL |
| small | HONLY_LR − PHR_NRMAP | log_loss | 0.0090 | 0.0054 | 2/8 | NOT MATERIAL |
| small | HONLY_LR − PHR_NRMAP | sensitivity | 0.0183 | 0.0071 | 8/8 | MATERIAL |
| small | HONLY_LR − PHR_NRMAP | specificity | 0.0031 | 0.0040 | 5/8 | NOT MATERIAL |
| all | HA_LEAN − HA_LR | BA | 0.0002 | 0.0009 | 3/8 | NOT MATERIAL |
| all | HA_LEAN − HA_LR | log_loss | 0.0015 | 0.0010 | 2/8 | NOT MATERIAL |
| all | HA_LEAN − HA_LR | sensitivity | -0.0000 | 0.0016 | 3/8 | NOT MATERIAL |
| all | HA_LEAN − HA_LR | specificity | 0.0004 | 0.0008 | 4/8 | NOT MATERIAL |
| all | HA_LEAN − HONLY_LR | BA | 0.0055 | 0.0015 | 8/8 | NOT MATERIAL |
| all | HA_LEAN − HONLY_LR | log_loss | -0.0511 | 0.0045 | 8/8 | MATERIAL |
| all | HA_LEAN − HONLY_LR | sensitivity | 0.0085 | 0.0023 | 8/8 | NOT MATERIAL |
| all | HA_LEAN − HONLY_LR | specificity | 0.0026 | 0.0012 | 7/8 | NOT MATERIAL |
| all | HA_LEAN − PHR_NRMAP | BA | 0.0037 | 0.0011 | 7/8 | NOT MATERIAL |
| all | HA_LEAN − PHR_NRMAP | log_loss | -0.0034 | 0.0017 | 6/8 | NOT MATERIAL |
| all | HA_LEAN − PHR_NRMAP | sensitivity | 0.0058 | 0.0029 | 6/8 | NOT MATERIAL |
| all | HA_LEAN − PHR_NRMAP | specificity | 0.0015 | 0.0015 | 5/8 | NOT MATERIAL |
| all | HA_LR − PHR_NRMAP | BA | 0.0035 | 0.0011 | 7/8 | NOT MATERIAL |
| all | HA_LR − PHR_NRMAP | log_loss | -0.0049 | 0.0013 | 8/8 | NOT MATERIAL |
| all | HA_LR − PHR_NRMAP | sensitivity | 0.0058 | 0.0022 | 8/8 | NOT MATERIAL |
| all | HA_LR − PHR_NRMAP | specificity | 0.0011 | 0.0010 | 6/8 | NOT MATERIAL |
| all | HONLY_LR − PHR_NRMAP | BA | -0.0019 | 0.0018 | 3/8 | NOT MATERIAL |
| all | HONLY_LR − PHR_NRMAP | log_loss | 0.0477 | 0.0046 | 0/8 | MATERIAL HARM |
| all | HONLY_LR − PHR_NRMAP | sensitivity | -0.0027 | 0.0035 | 1/8 | NOT MATERIAL |
| all | HONLY_LR − PHR_NRMAP | specificity | -0.0011 | 0.0024 | 3/8 | NOT MATERIAL |

## Same-path agreement of the lean system with the shared-upstream candidate (HA_LEAN vs HA_LR)

| budget | test_decision_disagree | cand_decision_disagree | spearman_margin | top1_same | logit_slope |
|---|---|---|---|---|---|
| 8.000 | 0.037 | 0.039 | 0.972 | 0.100 | 0.986 |
| 12.000 | 0.023 | 0.021 | 0.988 | 0.100 | 0.988 |
| 16.000 | 0.010 | 0.010 | 0.990 | 0.125 | 0.982 |
| 20.000 | 0.009 | 0.007 | 0.991 | 0.188 | 0.992 |
| 24.000 | 0.010 | 0.006 | 0.991 | 0.287 | 0.977 |
| 28.000 | 0.009 | 0.004 | 0.985 | 0.325 | 0.987 |
| 32.000 | 0.007 | 0.002 | 0.982 | 0.400 | 0.971 |
| 36.000 | 0.009 | 0.002 | 0.977 | 0.362 | 0.991 |
| 40.000 | 0.008 | 0.001 | 0.980 | 0.487 | 0.991 |
| 44.000 | 0.007 | 0.000 | 0.982 | 0.463 | 0.978 |
| 48.000 | 0.005 | 0.000 | 0.983 | 0.487 | 0.996 |
| 52.000 | 0.006 | 0.000 | 0.979 | 0.475 | 0.995 |
| 56.000 | 0.007 | 0.000 | 0.977 | 0.537 | 1.002 |
| 60.000 | 0.007 | 0.000 | 0.979 | 0.575 | 1.009 |

