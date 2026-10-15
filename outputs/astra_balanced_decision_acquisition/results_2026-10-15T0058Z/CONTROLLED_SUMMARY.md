**Controlled results: matched decision/acquisition experiment**

Status: INCOMPLETE_WITH_PRESERVED_STOPS. 72/84 trajectories complete.

| World | BA-risk minus comparator | Complete / 4 | Valid BA pairs | Mean BA-AULC difference | Seed interval |
|---|---|---:|---:|---:|---|
| informative | probability_variance | 4 | 4 | +0.0081 | [-0.0181, +0.0343] |
| informative | balanced_margin | 4 | 4 | -0.0081 | [-0.0549, +0.0386] |
| redundant | probability_variance | 4 | 4 | +0.0151 | [-0.0260, +0.0563] |
| redundant | balanced_margin | 4 | 4 | -0.0110 | [-0.0926, +0.0705] |
| harmful | probability_variance | 4 | 4 | -0.0054 | [-0.0272, +0.0165] |
| harmful | balanced_margin | 4 | 4 | +0.0011 | [-0.0172, +0.0195] |
| rare_negatives | probability_variance | 2 | 2 | +0.0466 | [-0.0007, +0.0939] |
| rare_negatives | balanced_margin | 2 | 2 | +0.0552 | [-0.8506, +0.9611] |
| locally_mixed | probability_variance | 3 | 3 | -0.0069 | [-0.0311, +0.0173] |
| locally_mixed | balanced_margin | 3 | 3 | +0.0097 | [-0.0437, +0.0631] |
| selected_fraction | probability_variance | 3 | 3 | +0.0412 | [+0.0029, +0.0796] |
| selected_fraction | balanced_margin | 3 | 3 | +0.0631 | [-0.0802, +0.2064] |
| missing_depth | probability_variance | 4 | 4 | +0.0066 | [-0.0221, +0.0354] |
| missing_depth | balanced_margin | 4 | 4 | +0.0063 | [-0.0121, +0.0247] |

Intervals describe these four generated seeds. No universal selector ranking or query-saving claim follows.

Numerical diagnostics: 128 accepted query decisions were near ties; 0 query computations stopped. Max risk tower discrepancy: 0.00114384.

All per-seed/per-budget probabilities, decisions, class counts, local errors, uncertainty intervals, paths and stops are in CONTROLLED_RESULTS.json. Startup paid/reference/true-reference fractions and decision-only contrasts are in RESULTS_SUMMARY.json.

**Terminal outcomes, same model and decision rule.** Entries below are means across completed seeds; all per-metric counts and descriptive seed intervals are in RESULTS_SUMMARY.json. Undefined recalls remain null, not zero. Proper-score and local-region losses are not suppressed when BA improves.

| World | Selector | Complete / 4 | BA | Sensitivity | Specificity | Brier | Log loss | Region error | Region positive recall | Region negative recall |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| informative | balanced_risk | 4 | +0.8194 | +0.7331 | +0.9057 | +0.1418 | +0.4370 | +0.0119 | +0.9881 | NA |
| informative | probability_variance | 4 | +0.8372 | +0.7517 | +0.9228 | +0.1314 | +0.4135 | +0.0119 | +0.9881 | NA |
| informative | balanced_margin | 4 | +0.8334 | +0.7372 | +0.9297 | +0.1520 | +0.4620 | +0.0471 | +0.9529 | NA |
| redundant | balanced_risk | 4 | +0.7436 | +0.6835 | +0.8038 | +0.1724 | +0.5228 | +0.3718 | +0.5031 | +0.8438 |
| redundant | probability_variance | 4 | +0.7688 | +0.6895 | +0.8482 | +0.1707 | +0.5206 | +0.3173 | +0.5923 | +0.8125 |
| redundant | balanced_margin | 4 | +0.7602 | +0.6884 | +0.8320 | +0.1647 | +0.5048 | +0.3170 | +0.5586 | +0.9062 |
| harmful | balanced_risk | 4 | +0.7665 | +0.8150 | +0.7179 | +0.1447 | +0.4478 | +0.0649 | NA | +0.9351 |
| harmful | probability_variance | 4 | +0.7917 | +0.8502 | +0.7331 | +0.1380 | +0.4313 | +0.0971 | NA | +0.9029 |
| harmful | balanced_margin | 4 | +0.7721 | +0.8225 | +0.7218 | +0.1438 | +0.4508 | +0.0792 | NA | +0.9208 |
| rare_negatives | balanced_risk | 2 | +0.7757 | +0.6737 | +0.8778 | +0.0809 | +0.2950 | +0.2167 | +0.0000 | +0.8708 |
| rare_negatives | probability_variance | 2 | +0.7074 | +0.6371 | +0.7778 | +0.0863 | +0.3080 | +0.2667 | +0.5000 | +0.7708 |
| rare_negatives | balanced_margin | 2 | +0.7004 | +0.6230 | +0.7778 | +0.1068 | +0.3791 | +0.2667 | +0.0000 | +0.8333 |
| locally_mixed | balanced_risk | 3 | +0.7267 | +0.6526 | +0.8009 | +0.1040 | +0.3495 | +0.5238 | +0.1667 | +0.8838 |
| locally_mixed | probability_variance | 3 | +0.7532 | +0.6320 | +0.8744 | +0.1118 | +0.3709 | +0.5087 | +0.1000 | +0.9722 |
| locally_mixed | balanced_margin | 3 | +0.7032 | +0.6243 | +0.7821 | +0.1037 | +0.3497 | +0.5581 | +0.1167 | +0.8586 |
| selected_fraction | balanced_risk | 3 | +0.7932 | +0.7470 | +0.8393 | +0.1587 | +0.4864 | +0.0806 | +0.9778 | +0.0000 |
| selected_fraction | probability_variance | 3 | +0.7511 | +0.6872 | +0.8150 | +0.1967 | +0.5675 | +0.0806 | +0.9778 | +0.0000 |
| selected_fraction | balanced_margin | 3 | +0.7403 | +0.6733 | +0.8072 | +0.1997 | +0.5770 | +0.0806 | +0.9778 | +0.0000 |
| missing_depth | balanced_risk | 4 | +0.8110 | +0.7333 | +0.8886 | +0.1404 | +0.4358 | +0.0114 | +0.9886 | NA |
| missing_depth | probability_variance | 4 | +0.8247 | +0.7255 | +0.9239 | +0.1484 | +0.4539 | +0.0114 | +0.9886 | NA |
| missing_depth | balanced_margin | 4 | +0.7969 | +0.7443 | +0.8496 | +0.1539 | +0.4636 | +0.0471 | +0.9529 | NA |

The always-defined prospective loss (1-BA or 1/2 on a one-class batch) and its paired AULC contrasts are reported separately in RESULTS_SUMMARY.json. Numerical-stop outputs remain in the raw file but are not treated as accepted endpoints.

Budget used: 374 top-level requests; 1122 component solves; 0 component solves reserved for unresolved interruptions. No query-saving endpoint was estimated.
