# RC24 pilot P1 (DEV, used repeats; exploratory)

## std

Own query, fold-pooled AULC (B8–B24 / B8–B60):

| arm | BA | log_loss | sensitivity | specificity | BA_hard_group |
|---|---|---|---|---|---|
| HA_LEAN | 0.9352 | 0.1844 | 0.9300 | 0.9404 | 0.5437 |
| HONLY_LR | 0.9409 | 0.2073 | 0.9399 | 0.9419 | 0.5062 |
| PAC_MARGIN | 0.9342 | 0.1839 | 0.9257 | 0.9428 | 0.5419 |

| arm | BA | log_loss | sensitivity | specificity | BA_hard_group |
|---|---|---|---|---|---|
| HA_LEAN | 0.9474 | 0.1433 | 0.9403 | 0.9544 | 0.5809 |
| HONLY_LR | 0.9440 | 0.1805 | 0.9397 | 0.9483 | 0.5024 |
| PAC_MARGIN | 0.9437 | 0.1562 | 0.9378 | 0.9497 | 0.5720 |

| window | contrast | mean | good | verdict |
|---|---|---|---|---|
| small | PAC_MARGIN − HA_LEAN | -0.0009 | 3/8 | NOT DIFFERENT (DEV) |
| small | PAC_MARGIN − HA_LEAN [LL] | -0.0005 | 4/8 | NOT DIFFERENT (DEV) |
| all | PAC_MARGIN − HA_LEAN | -0.0036 | 2/8 | NOT DIFFERENT (DEV) |
| all | PAC_MARGIN − HA_LEAN [LL] | 0.0129 | 0/8 | WORSE (DEV) |
| small | PAC_MARGIN − HONLY_LR | -0.0067 | 1/8 | NOT DIFFERENT (DEV) |
| small | PAC_MARGIN − HONLY_LR [LL] | -0.0234 | 7/8 | BETTER (DEV) |
| all | PAC_MARGIN − HONLY_LR | -0.0003 | 3/8 | NOT DIFFERENT (DEV) |
| all | PAC_MARGIN − HONLY_LR [LL] | -0.0243 | 8/8 | BETTER (DEV) |

Attainment:

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_LR | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.80 | PAC_MARGIN | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN | 8 | 8 | 8 | 8.00 | 5 | 12.38 | 12.00 | 1.00 |
| BA >= 0.90 | HONLY_LR | 8 | 8 | 8 | 8.00 | 8 | 12.00 | 12.00 | 1.00 |
| BA >= 0.90 | PAC_MARGIN | 8 | 8 | 8 | 8.00 | 5 | 12.50 | 12.00 | 1.00 |
| BA >= 0.93 | HA_LEAN | 8 | 8 | 8 | 10.00 | 0 | 15.38 | 14.00 | 0.98 |
| BA >= 0.93 | HONLY_LR | 8 | 8 | 8 | 8.00 | 6 | 13.00 | 12.50 | 0.99 |
| BA >= 0.93 | PAC_MARGIN | 8 | 8 | 8 | 10.00 | 0 | 15.50 | 14.50 | 0.95 |
| BA >= 0.95 | HA_LEAN | 8 | 8 | 8 | 18.50 | 0 | 32.12 | 31.50 | 0.83 |
| BA >= 0.95 | HONLY_LR | 8 | 8 | 3 | 19.00 | 0 | 29.00 | 25.00 | 0.30 |
| BA >= 0.95 | PAC_MARGIN | 8 | 8 | 8 | 29.00 | 0 | 38.25 | 42.00 | 0.72 |

Queries in the corner (post-startup share) and CPU s per step:

| arm | corner_share | cpu |
|---|---|---|
| HA_LEAN | 0.446 | 0.143 |
| HONLY_LR | 0.239 | 0.005 |
| PAC_MARGIN | 0.358 | 0.042 |

Hard group at B60:

| arm | recall_shortK_NEW | spec_cond_NEW | BA_hard_group |
|---|---|---|---|
| HA_LEAN | 0.950 | 0.333 | 0.642 |
| HONLY_LR | 1.000 | 0.000 | 0.500 |
| PAC_MARGIN | 0.800 | 0.385 | 0.593 |

Matched on HA_LEAN's own paths (step-4 grid):

| arm | BA | log_loss | BA_hard_group |
|---|---|---|---|
| HA_LEAN@HA_LEAN_path | 0.9287 | 0.1928 | 0.5456 |
| HA_TREND@HA_LEAN_path | 0.9356 | 0.1902 | 0.5390 |
| PAC@HA_LEAN_path | 0.9303 | 0.1975 | 0.5679 |
| PAC_FLAT@HA_LEAN_path | 0.9289 | 0.2011 | 0.5869 |
| PAC_GEN@HA_LEAN_path | 0.9257 | 0.2048 | 0.6060 |
| PAC_PLUG@HA_LEAN_path | 0.9302 | 0.1848 | 0.5690 |

| arm | BA | log_loss | BA_hard_group |
|---|---|---|---|
| HA_LEAN@HA_LEAN_path | 0.9446 | 0.1474 | 0.5806 |
| HA_TREND@HA_LEAN_path | 0.9456 | 0.1539 | 0.5702 |
| PAC@HA_LEAN_path | 0.9431 | 0.1629 | 0.6070 |
| PAC_FLAT@HA_LEAN_path | 0.9450 | 0.1606 | 0.6177 |
| PAC_GEN@HA_LEAN_path | 0.9408 | 0.1659 | 0.6176 |
| PAC_PLUG@HA_LEAN_path | 0.9430 | 0.1545 | 0.6074 |

- matched PAC − HA_LEAN [small] BA +0.0016 (3/8) NOT DIFFERENT (DEV)
- matched PAC − HA_LEAN [all] BA -0.0014 (1/8) NOT DIFFERENT (DEV)
- matched PAC_PLUG − HA_LEAN [small] BA +0.0014 (3/8) NOT DIFFERENT (DEV)
- matched PAC_PLUG − HA_LEAN [all] BA -0.0015 (1/8) NOT DIFFERENT (DEV)
- matched PAC_FLAT − HA_LEAN [small] BA +0.0002 (2/8) NOT DIFFERENT (DEV)
- matched PAC_FLAT − HA_LEAN [all] BA +0.0004 (3/8) NOT DIFFERENT (DEV)
- matched PAC_GEN − HA_LEAN [small] BA -0.0030 (2/8) NOT DIFFERENT (DEV)
- matched PAC_GEN − HA_LEAN [all] BA -0.0037 (2/8) NOT DIFFERENT (DEV)
- matched HA_TREND − HA_LEAN [small] BA +0.0069 (6/8) NOT DIFFERENT (DEV)
- matched HA_TREND − HA_LEAN [all] BA +0.0010 (5/8) NOT DIFFERENT (DEV)

## block

Own query, fold-pooled AULC (B8–B24 / B8–B60):

| arm | BA | log_loss | sensitivity | specificity | BA_hard_group |
|---|---|---|---|---|---|
| HA_LEAN | 0.9228 | 0.2114 | 0.9331 | 0.9124 | 0.4604 |
| HONLY_LR | 0.9364 | 0.2098 | 0.9416 | 0.9312 | 0.4854 |
| PAC_MARGIN | 0.9308 | 0.2020 | 0.9432 | 0.9185 | 0.4497 |

| arm | BA | log_loss | sensitivity | specificity | BA_hard_group |
|---|---|---|---|---|---|
| HA_LEAN | 0.9251 | 0.2035 | 0.9549 | 0.8953 | 0.5073 |
| HONLY_LR | 0.9454 | 0.1854 | 0.9486 | 0.9423 | 0.4953 |
| PAC_MARGIN | 0.9354 | 0.1884 | 0.9640 | 0.9068 | 0.4945 |

| window | contrast | mean | good | verdict |
|---|---|---|---|---|
| small | PAC_MARGIN − HA_LEAN | 0.0081 | 6/8 | NOT DIFFERENT (DEV) |
| small | PAC_MARGIN − HA_LEAN [LL] | -0.0095 | 6/8 | NOT DIFFERENT (DEV) |
| all | PAC_MARGIN − HA_LEAN | 0.0103 | 7/8 | NOT DIFFERENT (DEV) |
| all | PAC_MARGIN − HA_LEAN [LL] | -0.0151 | 6/8 | NOT DIFFERENT (DEV) |
| small | PAC_MARGIN − HONLY_LR | -0.0056 | 2/8 | NOT DIFFERENT (DEV) |
| small | PAC_MARGIN − HONLY_LR [LL] | -0.0078 | 5/8 | NOT DIFFERENT (DEV) |
| all | PAC_MARGIN − HONLY_LR | -0.0100 | 1/8 | NOT DIFFERENT (DEV) |
| all | PAC_MARGIN − HONLY_LR [LL] | 0.0030 | 3/8 | NOT DIFFERENT (DEV) |

Attainment:

| target | arm | units | defined | attained | first_median | at_startup | spend_mean_attainers | spend_median_attainers | sustained_share_mean |
|---|---|---|---|---|---|---|---|---|---|
| BA >= 0.80 | HA_LEAN | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.80 | HONLY_LR | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.80 | PAC_MARGIN | 8 | 8 | 8 | 8.00 | 7 | 12.12 | 12.00 | 1.00 |
| BA >= 0.90 | HA_LEAN | 8 | 8 | 8 | 9.00 | 2 | 13.00 | 13.00 | 0.96 |
| BA >= 0.90 | HONLY_LR | 8 | 8 | 8 | 8.50 | 4 | 12.75 | 12.50 | 1.00 |
| BA >= 0.90 | PAC_MARGIN | 8 | 8 | 8 | 9.50 | 3 | 13.25 | 13.50 | 1.00 |
| BA >= 0.93 | HA_LEAN | 8 | 8 | 7 | 9.50 | 1 | 15.43 | 14.00 | 0.52 |
| BA >= 0.93 | HONLY_LR | 8 | 8 | 8 | 8.50 | 4 | 13.50 | 12.50 | 0.99 |
| BA >= 0.93 | PAC_MARGIN | 8 | 8 | 8 | 10.50 | 2 | 14.62 | 14.50 | 0.79 |
| BA >= 0.95 | HA_LEAN | 8 | 8 | 0 | 12.00 | 0 | – | – | – |
| BA >= 0.95 | HONLY_LR | 8 | 8 | 8 | 17.50 | 0 | 37.75 | 35.00 | 0.59 |
| BA >= 0.95 | PAC_MARGIN | 8 | 8 | 3 | 14.00 | 0 | 17.67 | 18.00 | 0.30 |

Queries in the corner (post-startup share) and CPU s per step:

| arm | corner_share | cpu |
|---|---|---|
| HA_LEAN | 0.434 | 0.137 |
| HONLY_LR | 0.247 | 0.005 |
| PAC_MARGIN | 0.376 | 0.050 |

Matched on HA_LEAN's own paths (step-4 grid):

| arm | BA | log_loss | BA_hard_group |
|---|---|---|---|
| HA_LEAN@HA_LEAN_path | 0.9129 | 0.2226 | 0.4508 |
| HA_TREND@HA_LEAN_path | 0.9247 | 0.2073 | 0.4429 |
| PAC@HA_LEAN_path | 0.9178 | 0.2166 | 0.4181 |
| PAC_FLAT@HA_LEAN_path | 0.8896 | 0.2697 | 0.4331 |
| PAC_GEN@HA_LEAN_path | 0.9059 | 0.2368 | 0.4462 |
| PAC_PLUG@HA_LEAN_path | 0.9178 | 0.2144 | 0.4202 |

| arm | BA | log_loss | BA_hard_group |
|---|---|---|---|
| HA_LEAN@HA_LEAN_path | 0.9220 | 0.2067 | 0.5048 |
| HA_TREND@HA_LEAN_path | 0.9325 | 0.1859 | 0.4872 |
| PAC@HA_LEAN_path | 0.9288 | 0.1971 | 0.4811 |
| PAC_FLAT@HA_LEAN_path | 0.9104 | 0.2469 | 0.5269 |
| PAC_GEN@HA_LEAN_path | 0.9164 | 0.2239 | 0.4990 |
| PAC_PLUG@HA_LEAN_path | 0.9287 | 0.2119 | 0.4822 |

- matched PAC − HA_LEAN [small] BA +0.0049 (5/8) NOT DIFFERENT (DEV)
- matched PAC − HA_LEAN [all] BA +0.0068 (7/8) NOT DIFFERENT (DEV)
- matched PAC_PLUG − HA_LEAN [small] BA +0.0049 (5/8) NOT DIFFERENT (DEV)
- matched PAC_PLUG − HA_LEAN [all] BA +0.0067 (7/8) NOT DIFFERENT (DEV)
- matched PAC_FLAT − HA_LEAN [small] BA -0.0233 (0/8) WORSE (DEV)
- matched PAC_FLAT − HA_LEAN [all] BA -0.0116 (0/8) NOT DIFFERENT (DEV)
- matched PAC_GEN − HA_LEAN [small] BA -0.0070 (1/8) NOT DIFFERENT (DEV)
- matched PAC_GEN − HA_LEAN [all] BA -0.0056 (2/8) NOT DIFFERENT (DEV)
- matched HA_TREND − HA_LEAN [small] BA +0.0118 (8/8) NOT DIFFERENT (DEV)
- matched HA_TREND − HA_LEAN [all] BA +0.0106 (8/8) NOT DIFFERENT (DEV)

