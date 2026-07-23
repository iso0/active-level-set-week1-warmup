# Week 5.05 — ARD Matérn 3/2 results summary

## Scope

This targeted extension compares the existing isotropic Matérn 3/2 GP with
an ARD Matérn 3/2 GP under the identical experiment-level LOO protocol.
The operational no-Bug dataset contains 91 simulations and the broad
dataset contains 238; three never-Conduction simulations remain excluded.

## Main LOO results

| Dataset | Kernel | MAE | RMSE | R² | Mean NLPD | 95% coverage |
|---|---|---:|---:|---:|---:|---:|
| Clean | Isotropic Matérn 3/2 | 1735.765 | 2537.007 | 0.9171 | 9.8156 | 0.901 |
| Clean | ARD Matérn 3/2 | 1559.990 | 2808.296 | 0.8984 | 10.1858 | 0.835 |
| Broad | Isotropic Matérn 3/2 | 11616.871 | 16256.262 | 0.4060 | 11.0404 | 0.929 |
| Broad | ARD Matérn 3/2 | 12391.368 | 17596.191 | 0.3040 | 11.0712 | 0.895 |

Clean paired bootstrap RMSE difference (isotropic − ARD) is
-271.289, with 95% percentile interval
[-1203.379,
617.801]. Broad difference is
-1339.929, with interval
[-2763.252,
101.824]. Positive values favour ARD.

## Same 91 no-Bug targets

ARD clean-trained RMSE is 2808.296; ARD
broad-trained RMSE on the identical targets is
18051.785. Broad training improves
15 points and
worsens 76.
The median paired improvement (clean minus broad absolute error) is
-9415.964.

## Full-data ARD diagnostics

Clean optimized kernel: `1.05**2 * Matern(length_scale=[1.78, 0.905, 100, 3.36], nu=1.5)`.

Broad optimized kernel: `1.07**2 * Matern(length_scale=[1.43, 0.955, 0.893, 0.229], nu=1.5)`.

Bound-sensitivity results are reported for all five deterministic starts
under upper bounds 100 and 1000. A lengthscale moving beyond 100 under the
widened bound is interpreted as weak identification of an almost-flat
direction, not as a precisely estimated large value.

## Scientific interpretation

ARD improves clean RMSE: **False**. ARD improves broad RMSE:
**False**. Broad training improves ARD RMSE on the same clean
targets: **False**.

These results assess predictive robustness under the fixed first-observed
target. They do not prove exact physical transition times, label correctness,
or causal input importance. Active learning and level-set estimation remain
not started.
