# Physics-anchored stacking for active classification with an auxiliary response: when a known dimensionless number and a simulated side output help, and when they do not

*Draft (RC24). Every number in this draft is a development (DEV) result on one simulator pool; Stage C is a pre-registered confirmation on fresh splits of the same pool. Section 7 states the evidence limits.*

## Abstract

We study pool-based active classification of keyhole versus conduction melting in laser-welding simulations. Two kinds of information are available:
- **before a query:** a dimensionless physics coordinate, the normalised enthalpy h = P/√(VX·LS³);
- **from each query (one simulation):** the class label together with an auxiliary physical response, the active-window maximum melt depth, from the same record.

We compare, under one paid-only information contract and from 8 to 60 simulations:
- a physics-only classifier;
- historical baselines: a fixed physics-mean GP classifier (M3), a depth-threshold model (E1) and a direct ARD GP classifier (G3);
- a stacked classifier that feeds honest out-of-fold depth predictions to a learned-regularisation Laplace classifier (HA_LEAN);
- two new constructions.

The first new construction is **physics-anchored stacking (HA_TREND)**: HA_LEAN with the depth emulator's mean anchored on the physics coordinate (log A = μ + θ z_h + g, with θ integrated). The second is a family of joint, errors-in-variables models and two-observation acquisitions.

Measured results:
1. The physics coordinate alone is a strong learner. It is non-inferior in balanced-accuracy AULC, but it rarely sustains BA ≥ 0.95 and its probabilities are poor.
2. Constant-mean stacking loses the depth-carried part of the physics effect under geometric extrapolation (Proposition 1).
3. Anchoring the emulator on the physics coordinate, and not on a generic linear trend, recovers most of that loss.
4. Errors-in-variables integration and two-observation expected error reduction do not improve the classification decisions. Proposition 3 explains this for the integration; for the acquisition, we show that it fails to avoid a label-interleaved region.
5. Margin acquisition spends almost half of its queries in a 7 % region whose labels are decided by a start-up transient.

On fresh data, physics-anchored stacking was confirmed against the stacked baseline under a pre-registered rule. It is non-inferior on random splits, and better under geometric extrapolation: +0.011 BA-AULC in 8/8 block seeds, one-sided 95 % lower bound +0.008. The gain survives three controls:
- it is a model effect on identical paid samples (+0.010);
- it is insensitive to the prior width (b = 1 or 10);
- a generic linear trend does not give it (−0.013).

The physics coordinate alone remains slightly better early on random splits and under extrapolation. No model separates the label-interleaved region.

## 1. Problem and information contract

- **Pool.** A pool of N = 541 simulations with public inputs x = (P, VX, LS, ST). The batch of origin is provenance only, never a feature.
- **Query.** Querying x_i pays for one simulation and reveals three things from its record: the label y_i ∈ {0, 1}, the log active maximum depth a_i (possibly missing), and a record-quality flag q_i (the record ended before 95 % of its planned length).
- **Information.** Learning, normalisation of outcomes, calibration and acquisition use paid outcomes only. Public inputs may be standardised on the candidate pool.
- **Startup.** The first 8 queries are a label-free maximin design. Until both classes are paid, the continuation is label-free.
- **Evaluation.** Fold-pooled balanced accuracy on held-out folds, as an area under the learning curve over budgets 8–24 and 8–60. Further metrics:
  - attainment of BA targets 0.80, 0.90, 0.93 and 0.95: first budget, confirmation at b and b + 4, maintenance, censoring;
  - both recalls;
  - log loss;
  - the evaluator-only hard group.
- **Conditions.**
  - Random 5-fold splits.
  - Geometry blocks: a k-means cluster of the public log inputs is withheld from fitting and querying. This is extrapolation.

## 2. Model family

**Physics coordinate.** z_h(x) is the standardised value of log h = log P − ½ log VX − 3/2 log LS (LS is the spot radius).

**Depth emulators.** The latent log depth is

a*(x) = μ + β(x) + g(x),  g ~ GP(0, s_f² k_{3/2,ARD}).

- The kernel is Matérn-3/2 ARD on the standardised log inputs.
- The observation noise is N(0, s_n² w(q)), with w = 10⁴ for a short record.
- The hyperparameters are ML-II.
- The emulators differ in β:
  - **constant-mean**: β ≡ 0;
  - **physics-anchored**: β = θ z_h with θ ~ N(0, 3²). θ is integrated, which adds the kernel term 9 z_h z_h′ (Rasmussen & Williams 2006, §2.7), so trend uncertainty enters the predictive variance;
  - **generic-trend** control: β = θᵀ z with θ ~ N(0, 3² I) on all four standardised log inputs.

**Stacking.**
- For each paid run j, its depth feature is the honest out-of-fold prediction Â_j. Folds are j mod 10; each fold's emulator, including its hyperparameters and its normalisation, is fitted without the fold.
- At an unqueried x the feature is the full-fit predictive mean.
- The classifier is a Laplace GP classifier with a linear kernel, which is equivalent to Bayesian logistic regression on [z̃_h, Ã]:
  - priors b₀ ~ N(0, 10²), β_h ~ N(0, τ_h²), β_A ~ N(0, τ_A²);
  - (τ_A, τ_h) ∈ {0.5, 1, 2, 4}² weighted by the Laplace marginal likelihood;
  - each configuration's plug-in probability σ(m_g) is averaged.
- HA_LEAN uses the constant-mean emulator; **HA_TREND** uses the physics-anchored one.

**Structural composite (PAC, closed).**
- The classifier is trained on the posterior smoothing of the paid depths, i.e. the measured depths, instead of predictions.
- At an unqueried x the latent is integrated over a* ~ N(m(x), v(x)) by 32-node Gauss–Hermite quadrature.
- This is regression calibration with a GP covariate (Carroll et al. 2006).

**Nesting.** τ_A → 0 gives the h-only classifier. A sharp link with β_h = 0 in PAC gives E1. The historical M3 (a fixed logistic h mean with C = 10⁶ plus an amplitude-bounded ARD residual GPC) lies outside the linear family. It is ported bit-exactly as a control.

## 3. Acquisitions

- **Margin:** −|p − ½| on the arm's own model, first index on ties.
- **Straddle on HA_LEAN:** 1.96 s(x) − |logit p(x)|.
  - s² combines the Laplace latent variance, the excess depth-predictive variance propagated through the depth coefficient, and the grid spread.
  - Only the variance in excess of the honest out-of-fold error level is propagated, so in-distribution uncertainty is not counted twice.
  - The formula is exact for a Gaussian feature and was validated by Monte Carlo (median relative error 0.5 %).
- **JEER (closed):** the expected reduction of the 0-1 risk min(p, 1 − p) on the other candidate inputs.
  - It uses fantasies of the depth observation (exact rank-1 GP conditioning) and of the label (Laplace refit of every grid configuration) under PAC.
  - The queried point's own label resolution is excluded, as in EPIG.
- **Physics-margin path (HT_PHYS):** HA_TREND predicts, while the h-only classifier's margin chooses the queries.

## 4. Analysis (summary; proofs in `analysis/PROPOSITIONS.md`)

- **P1.** Under extrapolation, constant-mean stacking has a slope error α_A θ along z_h. Physics-anchored stacking has α_A(θ̂ − θ). The h-only classifier has none.
- **P2.** With θ integrated and absent (θ = 0), the extra error is O_p(n^{-1/2}). A fixed physics mean (M3) carries a saturated slope.
- **P3.** For a symmetric link and a Gaussian covariate, errors-in-variables integration cannot move one configuration's 0.5 decision.
- **P4.** Margin keeps sampling an aleatoric region. Expected error reduction on the other inputs tends to 0 there, but only if the model represents the region as aleatoric.
- **P5.** Nesting.

## 5. Experiments (DEV)

### 5.1 Stage A: fresh repeats 59–66, frozen before outcomes

| arm | BA-AULC B8–B24 | B8–B60 | LL B8–B60 | BA ≥ 0.95 attained |
|---|---|---|---|---|
| HA_LEAN + margin | 0.9360 | 0.9467 | 0.142 | 7/8 |
| h-only + margin | 0.9422 | 0.9451 | 0.165 | 5/8 |
| M3 + margin (historical) | 0.9391 | 0.9443 | 0.266 | 7/8 |
| E1 + straddle | 0.9115 | 0.9344 | 0.202 | 7/8 |
| G3 + margin | 0.9002 | 0.9289 | 0.269 | 6/8 |
| HA_LEAN + straddle | 0.9235 | 0.9372 | 0.171 | 5/8 |

Matched decomposition:
- E1's and G3's losses are model losses.
- The straddle loss is a pure path loss.
- h-only's early advantage is half model, half path.
- h-only's margin path is also a better path for the HA_LEAN model (+0.003).
- HA_LEAN + margin spends 45 % of its queries in the fast-scan corner (7 % of the pool). There, the short-keyhole events are start-up transients at the end of the forming phase (§5.4).

### 5.2 Stage B pilots (used repeats; exploratory)

- PAC ≈ HA_LEAN in random splits.
- In blocks, the anchor carries the gain:
  - the structural model without an anchor: −0.023;
  - a generic trend: −0.006;
  - HA_TREND (matched): +0.011, 8/8.
- HA_TREND + margin, own query:
  - random splits: +0.004 / +0.001 against HA_LEAN; non-inferior to h-only;
  - blocks: +0.013 / +0.011 (8/8), but below h-only (−0.010).
- JEER changed 99 % of the choices but neither the BA nor the corner share, at 30× the cost. It was stopped.

### 5.3 Synthetic benchmark (`synthetic/`)

Development families D1–D6 (anchor right / 45° off / useless; weak auxiliary; depth threshold; aleatoric corner) showed small, noisy effects. The pre-registered test families T1–T8, with 10 seeds, are reported in Section 6.

### 5.4 Hard region

Owner's figures verified on the RC23 records at B60 (HA_LEAN):
- recall 0.95 on the 10 NEW short-keyhole runs;
- specificity 0.33 on the 12 NEW conduction runs;
- local BA 0.64;
- recall 0.80 on the 22 pooled short-keyhole runs.

h-only predicts keyhole for every run in this group. Every keyhole frame of the short-keyhole runs lies within the forming phase plus 10 % of the record: first keyhole frame at 0.17–0.22 of the record, against a median end of forming at 0.19.

At equal depth, no available scalar separates the classes after the run. The leave-one-out AUC is 0.745 with the measured depth and does not improve with start-up-window summaries. Predicted from paid runs, these summaries add nothing (0.755).

## 6. Confirmatory test on fresh data (Stage C)

**Design (frozen before outcomes).**
- STD: random-split repeats 67–74.
- BLOCK: geometry-block seeds 9–16.
- Arms: HA_LEAN + margin (reference), h-only + margin, HA_TREND + margin (primary), and HT_PHYS (secondary).
- **Decision rule for the primary**, CONFIRMED iff all three hold:
  - STD non-inferiority in both windows: one-sided 95 % lower bound ≥ −0.010;
  - no MORE spend to BA ≥ 0.95;
  - BLOCK B8–B60 lower bound > 0.

**Results (fold-pooled BA-AULC; 8 repeats or seeds).**

| condition | system | B8–B24 | B8–B60 | LL B8–B60 | BA ≥ 0.95 attained |
|---|---|---|---|---|---|
| STD | HA_LEAN + margin | 0.9322 | 0.9464 | 0.147 | 8/8 |
| STD | **HA_TREND + margin** | 0.9356 | 0.9472 | 0.149 | 7/8 |
| STD | HT_PHYS | 0.9400 | 0.9479 | 0.151 | 8/8 |
| STD | h-only + margin | 0.9416 | 0.9451 | 0.177 | 5/8 |
| BLOCK | HA_LEAN + margin | 0.9268 | 0.9274 | 0.200 | 0/8 |
| BLOCK | **HA_TREND + margin** | 0.9375 | 0.9386 | 0.182 | 3/8 |
| BLOCK | HT_PHYS | 0.9334 | 0.9325 | 0.207 | 0/8 |
| BLOCK | h-only + margin | 0.9401 | 0.9468 | 0.185 | 8/8 |

**Primary HA_TREND + margin: CONFIRMED.**
- STD against HA_LEAN: +0.0034 (lower bound −0.0011) and +0.0007 (−0.0013).
- Spend to BA ≥ 0.95: no clear difference.
- BLOCK: +0.0112 (8/8, lower bound +0.0080).
- The mean spend to BA ≥ 0.93 in the blocks falls from 23.0 to 13.6 simulations.

**Secondary HT_PHYS: also CONFIRMED.**
- STD, B8–B24: +0.0078 (lower bound +0.0014).
- BLOCK: +0.0051 (+0.0005).
- It is below HA_TREND + margin in the blocks, and it loses short-keyhole recall (0.75 vs 0.96).

**Against h-only.** Neither system dominates.
- HA_TREND: −0.006 at B8–B24 on STD, −0.008 at B8–B60 on BLOCK.
- HT_PHYS: non-inferior on STD, −0.007 and −0.014 on BLOCK.

**Matched controls (identical paid samples on the HA_LEAN paths, BLOCK).**

| construction | difference against HA_LEAN (B8–B24 / B8–B60) |
|---|---|
| HA_TREND | +0.0102 / +0.0101 (8/8) |
| prior b = 1 | +0.0097 / +0.0095 |
| prior b = 10 | +0.0103 / +0.0102 |
| generic trend, structural (PAC_GEN) | −0.016 / −0.013 |
| structural PAC | +0.003 / +0.006 |
| h-only predictor on the same paths | +0.011 / +0.015 |

- AUC rises from 0.981 to 0.985, so the gain is not a threshold artefact.
- **Local cost:** in the blocks, the specificity on the 12 NEW conduction runs falls from 0.26 to 0.14 at B60.

**Synthetic test families (10 seeds each; pre-registered).**

| hypothesis | result | numbers |
|---|---|---|
| S2: an estimated anchor costs little when wrong or useless | supported | cost ≤ 0.006 |
| S3: an irrelevant auxiliary output buys nothing | supported | |
| S1: positive extrapolation gain where the anchor is right or near-right | not supported as registered | means +0.025 and +0.015, but 6/10 seeds in T2 |
| S4: no change in the balanced, noisy family | not supported | the anchor helped by +0.012 |
| S5: margin over-samples an aleatoric box | not observed | it does so only when the region lies on the decision boundary (P4) |

## 7. Evidence limits

- One simulator pool, DEV evidence only. There is no physical validation.
- Superiority margins (0.020 BA) were never reached. The non-inferiority and lower-bound criteria were pre-registered.
- The geometry blocks are one extrapolation design.
- The hard region is not solved by any model.
- A concrete physical-data proposal is in `FINAL_REPORT_RC24.md` §9: replicated corner runs, to test whether the start-up transient is deterministic.

## References

Astudillo & Frazier (ICML 2019; NeurIPS 2021); Bect et al. (Stat. Comput. 2012); Bickford Smith et al. (AISTATS 2023); Breiman (1996); Bryan et al. (NIPS 2005); Bryan & Schneider (ICML 2008); Carroll, Ruppert, Stefanski & Crainiceanu (2006); Gotovos, Casati, Hitz & Krause (IJCAI 2013); Hardcastle, O'Mullan, Arróyave & Vela (Digital Discovery 2025, 10.1039/D5DD00084J); Hernández-Lobato et al. (NeurIPS 2014); Houlsby et al. (2011); King et al. (J. Mater. Process. Technol. 2014); Menz, Munoz-Zuniga & Sinoquet (2023; ARCHISSUR 2025); Meng & Zhang (JOM 2020); Moreno-Muñoz, Artés & Álvarez (NeurIPS 2018); Rasmussen & Williams (2006); Roy & McCallum (ICML 2001); van der Laan, Polley & Hubbard (2007); Vapnik & Vashist (2009); Wolpert (1992); Ziatdinov, Ghosh & Kalinin (arXiv 2108.10280, 2021).
