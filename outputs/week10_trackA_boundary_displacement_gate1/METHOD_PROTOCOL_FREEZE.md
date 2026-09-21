# Boundary-displacement Gate 1 frozen method protocol

Status: **FROZEN BEFORE FULL TRAJECTORY EVALUATION**

## Scope and hypothesis

Internal same-path model-only test. M0 is exact Phase 1.13 M3. M1 adds a centered isotropic Matérn-3/2 covariance on `(z1,z2,z3)`. M2 adds a parameter-count-matched centered isotropic Matérn-3/2 covariance on `(s,z1,z2,z3)`. No acquisition is run.

## Coordinates and reference

`uP=log(P/P0)`, `uV=log(VX/VX0)`, `uL=log(LS/LS0)`; `s=uP-0.5uV-1.5uL`; `z1=(uP+2uV)/sqrt(5)`; `z2=(6uP-3uV+5uL)/sqrt(70)`; `z3=ST`. Reference values and standardization moments use all 405 feature rows without labels. Centering uses a deterministic 32-row feature-only maximin reference, starting from population row 0; indices: `[0, 146, 119, 359, 111, 363, 184, 388, 307, 178, 102, 154, 144, 316, 398, 49, 305, 74, 177, 57, 215, 339, 118, 345, 211, 379, 243, 317, 147, 52, 30, 198]`. Coordinate validation status: `PASS`; maximum reconstruction error `2.220e-16`.

## Kernels and fitting

`K=sigma2*((1-rho)*R_M3 + rho*R_extra_centered)`. Each component has unit mean diagonal on its reference; M3 correlation already has unit diagonal. The centered component is normalized at every extra length scale. M1/M2 add exactly `rho` and one isotropic extra length scale. `rho=0` is the exact M0 boundary. Interior optimization bounds are rho `[1e-6,1-1e-6]`, extra length `[0.01,100]`; M3 amplitude/ARD bounds and fixed physics mean are unchanged. One deterministic interior L-BFGS-B fit starts at the fitted M0 parameters, rho `0.20`, extra length `1.0`. The exact fitted M0 boundary is also evaluated and selected unless the interior log marginal likelihood exceeds it by `1e-10`. M1 and M2 receive identical fitting effort. No outcome-driven restart is allowed.

## Paths and budgets

Primary: stored Phase 1.21 `early8__coverage_then_margin_B40`, repeats 61-120, five folds. Confirmation, only after primary pass: stored `early8__margin` for the same runs. Integer budgets B16-B40. Every model sees the identical stored revealed prefix.

## Endpoints and inference

Primary: q20 accuracy normalized trapezoidal AULC B16-B40. Contrasts Delta10=M1-M0 and Delta12=M1-M2. Inference unit: repeat after averaging five folds. Deterministic 20,000-draw paired percentile bootstrap. Two-sided Bonferroni 95% familywise intervals use quantiles 0.0125 and 0.9875. Guardrails: q20 mean log predictive score AULC with probabilities clipped to `[1e-12,1-1e-12]`, and q20 Keyhole-recall AULC; both M1-M0 means must be nonnegative.

## Stability

All fits report convergence, fallback, boundary hits, rho and extra length. Exact rho-zero covariance/prediction tolerance is `1e-10`. Representative optimizer-start audit uses runs `['w85__r061_f01', 'w85__r090_f01', 'w85__r120_f01']` at B16/B28/B40 and alternate start rho `0.80`, extra length `3.0`. Stability passes only with zero numerical fallbacks, maximum q20 probability difference <= `0.02`, and maximum relative posterior-covariance Frobenius difference <= `0.10`. Component rho is diagnostic only.

## Decisions

Predictive pass requires simultaneous lower bounds above zero for both contrasts, nonnegative mean guardrails, and stability pass. Confirmation then applies positive point estimates for both contrasts, nonnegative guardrails, and stability. A: both passes and primary Delta10 >= 0.01. B: both passes and 0 < Delta10 < 0.01. C: stable fits but any predictive requirement fails. D: numerical/predictive/cross-covariance instability. Only A/B permit writing a future Gate 2 plan; Gate 2 is never executed here.
