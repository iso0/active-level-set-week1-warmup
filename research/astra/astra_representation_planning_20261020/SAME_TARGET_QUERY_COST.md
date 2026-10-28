# Same target, paid-query burden and measured computation

All means and attainment percentages weight the eleven families equally. Counts are raw completed paths; these are different denominators. Failed paths are separate, never assigned B48 success or censoring. No arm reaches the registered 80% overall attainment requirement for a query-saving claim.

| Panel / model / rule | Complete / planned | Attained; complete censored | Weighted attainment | Restricted queries | Decision CPU s | Total CPU s | Peak MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| prefix / ard__straddle | 336/336 | 104; 232 | 57.81% | 42.812 | 0.318 | 2.230 | 125.4 |
| prefix / existing__h1 | 336/336 | 36; 300 | 20.45% | 45.750 | 1.420 | 2.930 | 134.1 |
| prefix / existing__h2 | 335/336 | 37; 298 | 21.06% | 45.795 | 8.373 | 9.938 | 134.5 |
| prefix / existing__mixture_h1 | 336/336 | 37; 299 | 21.02% | 45.750 | 5.748 | 7.588 | 138.1 |
| prefix / local__h1 | 336/336 | 36; 300 | 20.45% | 45.750 | 4.662 | 7.840 | 169.3 |
| prefix / local__h2 | 335/336 | 37; 298 | 21.02% | 45.795 | 11.738 | 15.015 | 168.9 |
| prefix / local__mixture_h1 | 336/336 | 37; 299 | 21.02% | 45.750 | 15.513 | 19.714 | 183.6 |
| prefix / local__straddle | 336/336 | 42; 294 | 23.86% | 45.591 | 4.652 | 7.916 | 167.0 |
| e2e / ard__h1 | 176/176 | 114; 62 | 64.77% | 33.682 | 1.360 | 5.620 | 132.2 |
| e2e / ard__straddle | 176/176 | 111; 65 | 63.07% | 33.568 | 0.762 | 4.998 | 132.1 |
| e2e / existing__h1 | 176/176 | 47; 129 | 26.70% | 40.659 | 2.852 | 6.052 | 143.1 |
| e2e / existing__h2 | 175/176 | 50; 125 | 28.41% | 40.682 | 20.933 | 24.279 | 143.4 |
| e2e / existing__straddle | 176/176 | 71; 105 | 40.34% | 39.614 | 2.233 | 5.365 | 141.6 |
| e2e / local__h1 | 176/176 | 49; 127 | 27.84% | 40.773 | 8.308 | 14.127 | 177.5 |
| e2e / local__h2 | 176/176 | 49; 127 | 27.84% | 40.864 | 26.316 | 32.331 | 177.4 |
| e2e / local__straddle | 176/176 | 63; 113 | 35.80% | 40.091 | 7.801 | 13.672 | 176.1 |

Prefix means B32 feature-only paid startup continued to B48; e2e means B8 to B48. The target needs two consecutive four-query readouts. All complete paths buy 48 queries even after attainment. Restricted burden is min(T,48), not demonstrated savings. CPU excludes world generation/import/supervisor time; interrupted pre-checkpoint CPU may be under-recorded. Peak memory is worker process lifetime. No physical runtime was measured.

Source: results/analysis/same_target_query_cost.csv; its pointwise intervals and all per-family rows remain authoritative.
