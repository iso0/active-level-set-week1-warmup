# Same frozen target: queries and computation

All 14 families remain, 24 worlds each. Each arm runs to B64. Confirmation
requires the unchanged joint target at two adjacent readouts and charges
the second. Nonattainment is right-censored at 64, not called a numerical
failure. Restricted queries are mean min(T,64); they do not estimate
uncensored mean time to success. Full B64 compute is a separate quantity.
Actual compute time at T and physical simulation hours were not recorded.

| Model / selector | Families | Confirmed / worlds | Censored | Restricted queries | B64 error | B64 wall s | B64 CPU s | Selection s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EXTRATEST: structure / quota_no_surprise | 14 | 141/336 | 195 | 51.64 | 0.03377 | 47.24 | 46.77 | 42.48 |
| EXTRATEST: structure / quota_surprise | 14 | 140/336 | 196 | 51.67 | 0.03381 | 47.26 | 46.80 | 42.49 |
| TEST: mixture / blind_local | 14 | 160/336 | 176 | 48.45 | 0.06481 | 27.29 | 26.46 | 22.95 |
| TEST: mixture / boundary_regional | 14 | 161/336 | 175 | 48.39 | 0.06459 | 26.97 | 26.18 | 22.71 |
| TEST: mixture / maximin | 14 | 140/336 | 196 | 50.51 | 0.06514 | 4.63 | 4.22 | 0.60 |
| TEST: mixture / random | 14 | 125/336 | 211 | 52.69 | 0.07142 | 4.60 | 4.20 | 0.58 |
| TEST: mixture / regional | 14 | 160/336 | 176 | 48.45 | 0.06481 | 26.74 | 26.00 | 22.50 |
| TEST: mixture / straddle | 14 | 190/336 | 146 | 46.79 | 0.06108 | 4.64 | 4.21 | 0.58 |
| TEST: mixture / sur_global | 14 | 160/336 | 176 | 48.45 | 0.06481 | 27.07 | 26.28 | 22.79 |
| TEST: mixture / sur_primary | 3 | 66/72 | 6 | 38.56 | 0.02987 | 43.71 | 42.62 | 37.98 |
| TEST: mixture / ungated_local | 14 | 121/336 | 215 | 52.13 | 0.06876 | 28.15 | 26.85 | 23.11 |
| TEST: mixture / vtl | 14 | 148/336 | 188 | 50.06 | 0.06723 | 20.24 | 19.41 | 15.90 |
| TEST: simple / blind_local | 14 | 163/336 | 173 | 48.33 | 0.06456 | 15.55 | 14.97 | 11.94 |
| TEST: simple / boundary_regional | 14 | 164/336 | 172 | 48.32 | 0.06472 | 15.30 | 14.70 | 11.71 |
| TEST: simple / ca_smart_adapt | 14 | 140/336 | 196 | 50.19 | 0.06520 | 3.58 | 3.22 | 0.18 |
| TEST: simple / margin | 14 | 147/336 | 189 | 50.52 | 0.06615 | 3.57 | 3.20 | 0.15 |
| TEST: simple / maximin | 14 | 140/336 | 196 | 50.19 | 0.06533 | 3.70 | 3.26 | 0.19 |
| TEST: simple / maxvar | 14 | 138/336 | 198 | 51.19 | 0.06801 | 3.61 | 3.22 | 0.15 |
| TEST: simple / multiscale_tree | 14 | 107/336 | 229 | 53.29 | 0.08673 | 3.87 | 3.47 | 0.39 |
| TEST: simple / random | 14 | 121/336 | 215 | 53.04 | 0.07187 | 3.61 | 3.21 | 0.15 |
| TEST: simple / regional | 14 | 163/336 | 173 | 48.33 | 0.06462 | 15.23 | 14.69 | 11.69 |
| TEST: simple / straddle | 14 | 195/336 | 141 | 46.43 | 0.06103 | 3.54 | 3.18 | 0.15 |
| TEST: simple / sur_global | 14 | 163/336 | 173 | 48.33 | 0.06459 | 15.44 | 14.86 | 11.83 |
| TEST: simple / truvar | 14 | 146/336 | 190 | 50.01 | 0.06655 | 9.03 | 8.51 | 5.48 |
| TEST: simple / ungated_local | 14 | 124/336 | 212 | 52.12 | 0.06952 | 16.32 | 15.26 | 11.99 |
| TEST: simple / vtl | 14 | 149/336 | 187 | 50.48 | 0.06786 | 8.84 | 8.28 | 5.26 |
| TEST: structure / boundary_blind | 14 | 148/336 | 188 | 50.92 | 0.03195 | 51.76 | 50.63 | 46.20 |
| TEST: structure / boundary_regional | 14 | 148/336 | 188 | 50.93 | 0.03207 | 51.66 | 50.58 | 46.16 |
| TEST: structure / maximin | 14 | 57/336 | 279 | 56.01 | 0.04998 | 6.65 | 6.25 | 1.51 |
| TEST: structure / random | 14 | 70/336 | 266 | 55.62 | 0.04861 | 6.58 | 6.16 | 1.47 |
| TEST: structure / straddle | 14 | 167/336 | 169 | 51.15 | 0.02952 | 6.70 | 6.28 | 1.50 |
| TEST: structure / sur_global | 14 | 148/336 | 188 | 50.93 | 0.03210 | 51.89 | 50.79 | 46.34 |
| TEST: structure / sur_primary | 3 | 52/72 | 20 | 51.11 | 0.03470 | 100.23 | 98.60 | 90.83 |
| TEST: structure / ungated_local | 14 | 110/336 | 226 | 53.64 | 0.03591 | 51.99 | 50.39 | 45.83 |

The three-family sur_primary rows concern only multi-output worlds; do not
compare their aggregate with a 14-family row. Equal-share controls use the
same 336 TEST worlds, not another independent test sample. Pure straddle,
margin, RANDOM and literature adaptations have their declared baseline
schedules; complete-system comparisons are not isolated criterion effects.

No frozen paired query-savings flag passes. All four primary comparisons
have joint attainment below the frozen 80% requirement. H4 improves overall
error but increases restricted query burden by 2.607 [1.560,3.631]; its
attainment is 148/336 versus 164/336. These are different endpoints.
See ../final_tables/existing_paired_query_burden_contrasts.csv for every
registered paired interval, attainment fraction and operational flag.

Costs are saved trajectory accumulators, excluding setup and separate audits;
selection includes posterior/reference construction. Concurrent host load and
run order can affect timing. Largest recorded worker-lifetime RSS is 765.7 MB (not isolated-path memory or a total-host peak).

Intervals in the underlying analysis are pointwise, with the sign-flip
exchangeability/symmetry qualification in INFERENCE_AND_COMPLETION_AUDIT.md.
