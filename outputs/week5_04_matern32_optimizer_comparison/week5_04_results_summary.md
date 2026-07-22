# Week 5 Experiment 04 results summary

## Fixed comparison

All optimized Matérn 3/2 fits used fold-local scaling, `normalize_y=True`, `alpha=1e-6`, identical bounds, the same initial point and one identical deterministic extra restart. Powell did not use gradients; L-BFGS-B and SLSQP used analytic GP gradients. The no-optimization row is a sanity baseline.

## LOO findings

| Dataset | Optimizer | RMSE | MAE | Mean NLPD | Coverage | Runtime (s) | Successful selected runs | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Clean/no-Bug | L-BFGS-B | 2537.007 | 1735.765 | 9.81563 | 90.110% | 3.39 | 91 | 0 |
| Clean/no-Bug | SLSQP | 2537.007 | 1735.765 | 9.81563 | 90.110% | 4.18 | 91 | 0 |
| Clean/no-Bug | Powell | 2537.007 | 1735.765 | 9.81563 | 90.110% | 18.86 | 91 | 0 |
| Clean/no-Bug | No optimization | 2770.378 | 1899.215 | 9.59831 | 94.505% | 0.17 | 0 | 0 |
| Broad | L-BFGS-B | 16256.261 | 11616.870 | 11.04043 | 92.857% | 76.65 | 238 | 0 |
| Broad | SLSQP | 16256.261 | 11616.869 | 11.04043 | 92.857% | 31.05 | 238 | 0 |
| Broad | Powell | 16256.261 | 11616.870 | 11.04043 | 92.857% | 184.11 | 238 | 0 |
| Broad | No optimization | 16871.409 | 11746.001 | 11.41418 | 81.092% | 0.97 | 0 | 0 |


## Recommendation

- Kernel: **Matérn 3/2**.
- Optimizer: **L-BFGS-B**.
- Broad-data performance gap resolved by optimizer choice: **False**.
- Broad Matérn 5/2 full-data results are a limited LML/convergence check, not a replacement for LOO.
- Active learning and level-set estimation were not started.
