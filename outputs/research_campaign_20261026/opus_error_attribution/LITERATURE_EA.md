# Nearest literature for the EA candidate and the limit of the contribution (2026-10-26)

**How the sources were checked:**
- This session, at abstract / proceedings-record level: Karvonen & Oates 2023, Hvarfner et al. 2024, Snoek et al. 2012.
- This session, at document level: the Stan User's Guide GP chapter. Betancourt's case study itself was not retrieved.
- In RC24 (`opus_rc24/post_audit/ORIGINALITY_AND_LITERATURE.md`): universal kriging, stacking and margin sampling.
- No method here was reimplemented from a paper.

## 1. Known components of C1 (HA_TREND + MAP hyperparameters under a fixed weak hyperprior)

| component | known from | note |
|---|---|---|
| GP with an explicit basis-function trend whose Gaussian coefficient is integrated out (universal kriging) | O'Hagan 1978; Kennedy & O'Hagan 2001; Rasmussen & Williams 2006 §2.7 | HA_TREND: one basis function, standardised log h |
| maximum-likelihood (ML-II) estimation of GP hyperparameters can be ill-posed | Karvonen & Oates 2023, *JMLR* 24(120): 1–47 (arXiv 2203.09179) | they prove failures of well-posedness for stationary kernels with lengthscales estimated by ML, in the noiseless setting. Our measured symptom: at b ≤ 16 the noise variance collapses to its lower bound and lengthscales run to bounds, i.e. the fit interpolates |
| priors on GP hyperparameters, or integration over them, instead of point optimisation | Snoek, Larochelle & Adams 2012, NeurIPS 25 (fully Bayesian treatment preferred over optimisation); Hvarfner, Hellsten & Nardi 2024, ICML, PMLR 235: 20793–20817 (a dimension-scaled LogNormal lengthscale prior makes vanilla BO strong, especially at low budgets) | C1 uses fixed independent log-normal priors and the posterior mode. It is a standard, weaker form of these ideas |
| weakly informative lengthscale priors because of identification problems | Stan User's Guide, GP chapter (inverse-gamma example; "the identification issues are real") | |
| stacking and margin sampling | Wolpert 1992; Lewis & Gale 1994 | unchanged |

## 2. What is ours (measured, DEV, one 541-run pool)

**1. An error attribution on the same query paths and paid data.** Its rungs:
- true test depth, true depth on both sides;
- an "unlimited-data emulator";
- a hyperparameter oracle;
- the flexible family and the representation controls.

It shows that:
- the early gap is mostly an **information limit** of b paid depths;
- the classifier family, the representation and the selector are not the bottleneck;
- the late window is close to the input-only ceiling of this emulator family.

**2. A specific measured mechanism.** The physics-trend model's known mid / late-budget loss and its log-loss penalty (EL, RC24P) are artefacts of ML-II hyperparameter estimation at small n, not of the trend. With full-pool hyperparameters the trend model is better at every budget (evaluator-only D2T).

**3. A deployable fix, validated on fresh IDs.** Fixed weak hyperpriors and the MAP estimate, with mechanism controls:
- the same prior without the trend fails, −0.038 early;
- more optimiser starts without the prior do not reproduce it.

Against HA_LEAN + margin it gives:
- early BA-AULC +0.0056 [+0.0038];
- a restricted-mean saving of +2.0 simulations to BA 0.95 on this test;
- log loss equal to HA_LEAN's;
- 1.2× CPU.

## 3. Not ours, or not shown

- **Not a new statistical method.** MAP under a weak hyperprior is standard practice.
- **No claim of superiority over published methods.** None was reimplemented, and their settings differ: BO and regression benchmarks vs a stacked active classifier.
- **Not stable across repeat sets at the 0.95 target:**
  - the 0.95 keeping result changed sign between the DEV set and the fresh test;
  - only the early gain is replicated across two independent sets of 40 repeats.
- **No external physical validation.** The prior was chosen after the full-pool ML-II values had been seen (disclosed); new splits of the same pool cannot detect a prior that suits this pool by luck.
- **Under geometric extrapolation to the old five regions**, C1 keeps the per-region weakness of trend models (−0.049).
