# Supervisor one-page summary — Week 9 Phase 1.7

## Question and model

Can a physics-dominant latent classifier improve frozen near-boundary active learning?

`f(x)=beta_0+beta_h z(log h(x))+r(x)`, with `h=P/sqrt(VX*LS^3)` and `r` a constrained isotropic Matérn-3/2 GP over standardized P,VX,LS,ST. The Bernoulli likelihood uses a logistic link and scikit-learn's Laplace approximation. This is an additive kernel, not a fifth-feature GPC: the residual kernel never sees log(h).

## Frozen primary result

- Physics-ridge residual GP q20 AULC 16–80: **0.83354**
- Canonical 4D Margin: **0.81352**
- Matched difference: **+0.02002**, repeat-block 95% CI **[+0.01407, +0.02626]**
- Predeclared decision: **PASS** (effect ≥ +0.010 and lower CI > 0)
- q30 difference: **+0.01094** [+0.00597, +0.01598]

## Budget 40 and missed Keyholes

At budget 40, q20 accuracy is 0.8341 versus 0.8171; balanced accuracy is 0.8129 versus 0.7971; Keyhole recall is 0.7281 versus 0.7110. The recall difference is descriptive rather than resolved: +0.0170, CI [-0.0112,+0.0466]. Mean missed Keyholes per 17-row q20 fold fall from 1.91 to 1.76.

The residual is small in realized magnitude: at budget 40 its q20 RMS latent correction is 0.182, versus 2.424 for the physics term. Across 100 q20 run-fold events it recovers 13 physics-trend Keyhole misses and induces 4 new misses.

## Interpretation

The primary hypothesis passes on this frozen simulator benchmark. Most of the advantage is already present at the shared budget-16 design, so the result supports the **combined model-and-margin policy**, not a pure acquisition-only claim. Relative to the Phase 1.5 h-only model/policy, the additive result is only +0.0018 AULC with CI [-0.0022,+0.0056].

## Qualification

The residual-amplitude upper/lower bounds are active in 3395/6500 and 1095/6500 active fits, the length-scale bounds in 769/6500, and optimization warnings occur in 4557/6500; no additive-model fallback occurred. Therefore the low-amplitude behavior is partly imposed by design, and the result does not establish cross-material transfer, causal physics, or industrial safety.
