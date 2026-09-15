# Week 9 Phase 1.7 — final physics-ridge residual GP report

## Executive decision

**PASS.** Under the exact frozen Week 8.5 protocol, the additive physics-ridge residual classifier improves Fold-B1-q20 accuracy AULC 16–80 by +0.020018, with repeat-block 95% CI [+0.014071, +0.026264], relative to canonical 4D Binary Margin. This satisfies the predeclared PASS rule.

## Exact implementation

The binary latent model is

`y_i | f_i ~ Bernoulli(sigmoid(f_i))`

`f_i = beta_0 + beta_h z(log h_i) + r(x_i)`

with independent priors `beta_0,beta_h ~ N(0,25)` and `r ~ GP(0,a_r^2 Matern_3/2,ell)` over pool-standardized `(P,VX,LS,ST)`. `a_r` is optimized inside `[0.05,1.0]` latent-logit SD and the single isotropic length scale inside `[0.25,4]`, with zero optimizer restarts. The combined additive kernel is fitted by scikit-learn's Laplace logistic GPC. At every active budget both scalers use training-pool features only; only currently revealed labels enter posterior fitting. Acquisition is ordinary combined-model Binary Margin: choose the unqueried training-pool point whose predictive probability is closest to 0.5.

This differs mathematically from Phase 1.5's 5D GPC: the log(h) component is strictly linear/additive and the residual kernel sees only the four original coordinates, with no h–4D interaction kernel.

## Baseline and information-flow gates

The frozen gate reproduced 100/100 exact splits and initial designs, 4D Margin AULC 0.813520, and matched Random 0.776220. No test rows, hidden pool labels, B1/q flags, or external h thresholds enter acquisition.

## Active-learning results

| Endpoint | Additive | 4D Margin | Difference | 95% repeat-block CI |
|---|---:|---:|---:|---:|
| q20 accuracy AULC 16–80 | 0.833539 | 0.813520 | +0.020018 | [+0.014071,+0.026264] |
| q30 accuracy AULC 16–80 | 0.877056 | 0.866116 | +0.010941 | [+0.005966,+0.015978] |

At budget 40, q20 accuracy is 0.834118 versus 0.817059; balanced accuracy 0.812943 versus 0.797113; Keyhole recall 0.728079 versus 0.711044; FN 1.76 versus 1.91; FP 1.06 versus 1.20. The matched q20 accuracy difference is +0.017059 [+0.003529,+0.029412]. The recall difference is +0.017036 [-0.011247,+0.046565], so missed-Keyhole improvement at this single budget is not statistically resolved.

At budget 80, q20 accuracy is 0.845882 versus 0.832941; Keyhole recall is nearly tied at 0.732853 versus 0.732381, while additive FP is lower (0.87 versus 1.10).

The additive model's advantage over the Phase 1.5 h-only model/policy is only +0.001801, CI [-0.002183,+0.005598]. Thus the residual does not establish a resolved AULC improvement beyond h-only; the clear primary gain is versus canonical 4D Margin.

## Does the residual genuinely correct h failures?

Yes, but modestly. At budget 40, among 100 q20 run-fold events the residual changes 41 class decisions: 21 become correct and 20 become wrong. Specifically, it recovers 13 Keyholes missed by the physics trend and induces 4 new Keyhole misses. At budget 80 these counts are 37 corrected, 21 worsened, 14 Keyholes recovered, and 2 new Keyhole misses.

At budget 40, residual q20 RMS is 0.182 versus physics-term RMS 2.424; at budget 80 they are 0.309 and 3.022. The realized correction is therefore low amplitude even though the residual prior SD often reaches its imposed upper bound.

### Representative budget-40 q20 residual cases

These rows summarize repeated held-out occurrences; they are examples, not independent physical experiments.

| P (W) | VX (m/s) | LS (um) | ST (K) | log(h) | h-only p | residual | combined p | truth | corrected occurrences |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 140.5 | 0.256 | 45.0 | 300.0 | 20.641 | 0.449 | +0.138 | 0.483 | 1 | 6 |
| 211.8 | 0.521 | 48.1 | 318.7 | 20.596 | 0.384 | +0.154 | 0.429 | 1 | 5 |
| 336.4 | 0.857 | 51.5 | 367.7 | 20.707 | 0.604 | -0.176 | 0.555 | 0 | 3 |
| 149.2 | 0.206 | 48.7 | 365.1 | 20.688 | 0.556 | -0.209 | 0.504 | 0 | 2 |
| 140.1 | 0.223 | 45.0 | 300.0 | 20.706 | 0.545 | +0.132 | 0.568 | 1 | 2 |

## Static diagnostic

| Model | Full ROC-AUC | Full PR-AUC | Full balanced accuracy | q20 balanced accuracy | q20 Keyhole recall |
|---|---:|---:|---:|---:|---:|
| h logistic | 0.989697 | 0.950055 | 0.922196 | 0.810431 | 0.709549 |
| Additive ridge-residual | 0.990993 | 0.956724 | 0.925716 | 0.819493 | 0.717183 |
| Canonical 4D GPC | 0.992587 | 0.968286 | 0.925087 | 0.815909 | 0.732327 |

The additive static model lies between h and the 4D GPC in ranking/recall, while its fixed-threshold balanced accuracy is slightly higher. This is diagnostic, not the primary endpoint.

## PCA diagnostic

PCA is fitted without labels on standardized P,VX,LS,ST. PC1+PC2 explain 58.42% of feature variance. Residual magnitude is spread through the sampled space rather than defining a clean physical boundary in PC1–PC2. The plot is descriptive only.

## Safe thesis claim

“On the frozen 405-simulation Ti-6Al-4V benchmark, using the physics-inspired h coordinate as an additive latent trend with a constrained 4D Matérn residual improved Fold-B1-q20 accuracy AULC 16–80 relative to canonical 4D Binary Margin.”

This does not imply a universal physical boundary, acquisition-only superiority, cross-material transfer, prospective experimental validation, causality, safety, or guaranteed query savings.

## Main limitation

Because log(h) is algebraically determined by P,VX,LS, the residual GP can in principle imitate the physics trend. Dominance is enforced by the amplitude cap rather than statistically identifiable from this single dataset. The upper/lower amplitude bounds bind frequently (3395/6500 and 1095/6500 active fits; length-scale bounds 769/6500; 4557 convergence warnings), so the PASS is benchmark-specific and conditional on this predeclared constrained model.
