# All families: common-prefix B48 evidence

Descriptive family means. E/H1 = preserved fixed mixture; L/H2 = local mixture and bounded two-step rule; ARD/S = learned ARD and full-pool straddle. Changes in both model and selector are complete-system comparisons. N/A is preserved. Full eight-arm metrics, pointwise uncertainty and denominators are in family_metrics.csv.

| Family | Arm | Global error | Boundary error | Positive recall | Negative recall | Island recall | Brier | Log loss |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| coordinate | existing__h1 | 0.03177 | 0.33020 | 0.96782 | 0.96860 | N/A | 0.04974 | 0.20099 |
| coordinate | local__h2 | 0.03171 | 0.33207 | 0.96777 | 0.96882 | N/A | 0.04973 | 0.20113 |
| coordinate | ard__straddle | 0.01596 | 0.23031 | 0.98377 | 0.98444 | N/A | 0.01241 | 0.04396 |
| corrupt_correlated | existing__h1 | 0.00720 | N/A | N/A | 0.99280 | N/A | 0.03503 | 0.19412 |
| corrupt_correlated | local__h2 | 0.00851 | N/A | N/A | 0.99149 | N/A | 0.03523 | 0.19435 |
| corrupt_correlated | ard__straddle | 0.01224 | N/A | N/A | 0.98776 | N/A | 0.01024 | 0.07013 |
| heavy_tail | existing__h1 | 0.05692 | 0.30183 | 0.94487 | 0.93998 | N/A | 0.08595 | 0.31461 |
| heavy_tail | local__h2 | 0.05634 | 0.29689 | 0.94651 | 0.93958 | N/A | 0.08650 | 0.31637 |
| heavy_tail | ard__straddle | 0.04315 | 0.24289 | 0.95380 | 0.95929 | N/A | 0.03335 | 0.13314 |
| heteroscedastic | existing__h1 | 0.04944 | 0.29476 | 0.95450 | 0.94559 | N/A | 0.08632 | 0.31754 |
| heteroscedastic | local__h2 | 0.04773 | 0.28966 | 0.95710 | 0.94628 | N/A | 0.08560 | 0.31589 |
| heteroscedastic | ard__straddle | 0.02747 | 0.19661 | 0.97221 | 0.97244 | N/A | 0.01990 | 0.06570 |
| island_large | existing__h1 | 0.05121 | 0.26773 | 0.82432 | 0.98833 | 0.09121 | 0.06763 | 0.25152 |
| island_large | local__h2 | 0.05059 | 0.26492 | 0.82400 | 0.98916 | 0.08768 | 0.06717 | 0.25047 |
| island_large | ard__straddle | 0.04474 | 0.26165 | 0.85582 | 0.98675 | 0.29310 | 0.03862 | 0.23814 |
| island_small | existing__h1 | 0.01883 | 0.20012 | 0.93924 | 0.99214 | 0.01251 | 0.04158 | 0.17513 |
| island_small | local__h2 | 0.01876 | 0.19950 | 0.93896 | 0.99232 | 0.00886 | 0.04140 | 0.17462 |
| island_small | ard__straddle | 0.01948 | 0.20450 | 0.93618 | 0.99217 | 0.01212 | 0.01654 | 0.13293 |
| local_scale | existing__h1 | 0.06482 | 0.32371 | 0.94510 | 0.92488 | N/A | 0.08915 | 0.32300 |
| local_scale | local__h2 | 0.06384 | 0.32025 | 0.94547 | 0.92648 | N/A | 0.08916 | 0.32298 |
| local_scale | ard__straddle | 0.04517 | 0.23141 | 0.95332 | 0.95646 | N/A | 0.03552 | 0.21279 |
| missing | existing__h1 | 0.05231 | 0.30663 | 0.95037 | 0.94483 | N/A | 0.09337 | 0.33798 |
| missing | local__h2 | 0.04904 | 0.29309 | 0.95280 | 0.94858 | N/A | 0.09370 | 0.33968 |
| missing | ard__straddle | 0.02435 | 0.17369 | 0.97408 | 0.97736 | N/A | 0.01764 | 0.05836 |
| null | existing__h1 | 0.00000 | N/A | N/A | 1.00000 | N/A | 0.02148 | 0.15331 |
| null | local__h2 | 0.00000 | N/A | N/A | 1.00000 | N/A | 0.02148 | 0.15331 |
| null | ard__straddle | 0.00000 | N/A | N/A | 1.00000 | N/A | 0.00000 | 0.00000 |
| rotated | existing__h1 | 0.49603 | 0.50773 | 0.48651 | 0.52373 | N/A | 0.31044 | 0.87583 |
| rotated | local__h2 | 0.49646 | 0.50222 | 0.48124 | 0.52798 | N/A | 0.30496 | 0.84695 |
| rotated | ard__straddle | 0.50171 | 0.49649 | 0.49287 | 0.50310 | N/A | 0.32299 | 1.02281 |
| smooth | existing__h1 | 0.04404 | 0.27110 | 0.94923 | 0.96273 | N/A | 0.08606 | 0.31775 |
| smooth | local__h2 | 0.04388 | 0.26898 | 0.95322 | 0.95845 | N/A | 0.08587 | 0.31714 |
| smooth | ard__straddle | 0.02432 | 0.16817 | 0.97817 | 0.97305 | N/A | 0.01752 | 0.05764 |
