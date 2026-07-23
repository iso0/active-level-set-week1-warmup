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

## Paired held-out behaviour

On clean/no-Bug data ARD changes RMSE by
+10.693% and
MAE by -10.127%.
It improves 56 points, worsens
35 and ties
0 at tolerance
`1e-9`. Mean/median paired improvement is
175.775 /
174.856
timesteps.

On broad data ARD changes RMSE by
+8.243% and
MAE by +6.667%.
It improves 118 points, worsens
120 and ties
0. Mean/median
paired improvement is
-774.498 /
-17.181.

Largest clean ARD improvement:
`P-210p464738138_VX-0p237113609615_LS-6p46217439158e-05_ST-306p057190902_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-2p03451864735e-05_H-12faed80a6`
(7082.66345886
timesteps). Largest clean degradation:
`P-92p2921456709_VX-0p425581954559_LS-4p53091383738e-05_ST-356p588229582_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p13353504568e-05_H-765072ed36`
(-10468.1974049).
The corresponding broad cases are
`P-238p319282705_VX-0p253960262605_LS-5p92121677448e-05_ST-384p128817665_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p89955725889e-05_H-452de4062d`
(31890.5651052)
and
`P-194p036512211_VX-0p298398024189_LS-7p09068727373e-05_ST-343p727832606_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-1p61667310503e-05_H-7931c20f4a`
(-35827.0218303).

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
Its anisotropy ratio is
110.557. Clean LS reaches the
primary upper bound in
94.51% of folds; the ARD model has
89
folds with at least one hyperparameter at a bound.

Broad optimized kernel: `1.07**2 * Matern(length_scale=[1.43, 0.955, 0.893, 0.229], nu=1.5)`.
Its anisotropy ratio is
6.243; broad ARD has
0
bound-hit folds.

Bound-sensitivity results are reported for all five deterministic starts
under upper bounds 100 and 1000. A lengthscale moving beyond 100 under the
widened bound is interpreted as weak identification of an almost-flat
direction, not as a precisely estimated large value.

The selected clean widened-bound solution reports
`material_change` with weakly
identified component(s)
`LS`, maximum
symmetric lengthscale ratio
10.000, and LML
change 0.071697. The selected
broad solution reports
`no_material_change` with maximum ratio
1.000 and LML
change 0.000000.

## ARD RBF context

On clean/no-Bug data ARD RBF reduced RMSE from
6141.668 to
3255.022, whereas ARD Matérn
3/2 increased it from 2537.007 to
2808.296. On broad data ARD also worsened both the RBF
and Matérn 3/2 variants. The useful clean ARD effect was therefore specific
to rescuing the overly smooth isotropic RBF, not a general benefit for the
already strong Matérn 3/2 model.

## Required conclusions

1. **No-Bug RMSE:** ARD does not improve it; RMSE increases by
   10.693%.
2. **Broad RMSE:** ARD does not improve it; RMSE increases by
   8.243%.
3. **Materiality:** no stable held-out ARD advantage is established. All
   paired bootstrap intervals cross zero and both RMSE point estimates
   favour isotropic Matérn 3/2.
4. **Other metrics:** clean MAE improves, but R², NLPD and coverage worsen
   and intervals narrow from
   13861.9 to
   7223.4. Broad MAE, R², NLPD
   and coverage all worsen; interval width changes from
   58070.3 to
   55036.6.
5. **Fold stability:** broad lengthscales are stable (all reported
   coefficients of variation below 0.10). Clean P and VX are stable, but
   LS is bound-dominated and ST has occasional upper-bound outliers.
6. **Bound hits:** clean has
   89
   affected folds; broad has
   0.
7. **Widened bound:** clean LS moves from 100 to 1000 for only a small LML
   gain, revealing weak identifiability; broad is unchanged.
8. **Training-population conflict:** ARD does not resolve it. Broad-trained
   RMSE on the same 91 no-Bug points remains
   18051.785 versus
   2808.296.
9. **Runtime and complexity:** ARD is
   3.29×
   slower on clean and
   3.36×
   slower on broad. The extra complexity is not justified.
10. **Recommendation:** retain isotropic Matérn 3/2 with L-BFGS-B. The Week 5
    kernel recommendation does not change.

## Scientific interpretation

ARD improves clean RMSE: **False**. ARD improves broad RMSE:
**False**. Broad training improves ARD RMSE on the same clean
targets: **False**.

These results assess predictive robustness under the fixed first-observed
target. They do not prove exact physical transition times, label correctness,
or causal input importance. Active learning and level-set estimation remain
not started.
