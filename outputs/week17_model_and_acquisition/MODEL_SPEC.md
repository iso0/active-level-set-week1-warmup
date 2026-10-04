# Week 17 model specification (frozen with PREDICTIONS_AND_FREEZE.md)

Code: `src/week17_models.py` (one code path for every model), inference
`src/week17_audit_impact.py::SafeguardedFixedMeanLaplaceGPC`, look-ahead `week17_models.peer_values`.

## Common to all GP models
- Latent f = m(x) + g(x), g ~ GP(0, k); logistic likelihood p(y = 1 | f) = σ(f); labels deterministic
  simulator outcomes (real) or generator labels (synthetic).
- Inputs: x4 = (P, VX, LS, ST) (synthetic: unit-box z), standardized with a StandardScaler fitted on the
  **label-free training pool**; h = log P − ½ log VX − 3/2 log LS (synthetic: the physics score s(u) = u·w_p),
  standardized on the training pool.
- Laplace approximation; posterior mode by **safeguarded Newton** (GPML Alg. 3.1 direction, backtracking on
  Ψ(a) = −½aᵀKa + Σ log σ((2y−1)(m + Ka)), stop when |ΔΨ| < 1e-12 and the latent step < 1e-9). The fixed-point
  error |K(y − π) − g| is recorded for every fit (`fp_err`).
- Hyperparameters: ML-II on the revealed labels at every acquisition step; L-BFGS-B (maxiter 150, ftol 1e-12,
  gtol 1e-7) on the Laplace log marginal likelihood evaluated **at the true mode**, GPML Alg. 5.1 analytic
  gradients (sklearn kernel gradients), single start from the initial values, no restarts, no oracle data.
- Predictive probability: Williams–Barber logistic-Gaussian integral (as in the historical code).

## Models
| Name | m(x) | k(x, x′) | Bounds (initial = 1) | Role |
|---|---|---|---|---|
| **G3** | 0 | a² Matérn-3/2 ARD(x4) | a² ∈ [1e-3, 1e3], ℓ ∈ [1e-2, 1e2] | established generic baseline (numerically identical to the historical sklearn fit: max Δp = 0 on a NEW split) |
| **M3** | H₁e6(h): logistic regression on standardized h, C = 1e6, fitted on revealed rows | r² Matérn-3/2 ARD(x4) | r² ∈ [0.05², 1], ℓ ∈ [1e-2, 1e2] | original M3 baseline (safeguarded refit; historical fit reported separately in Phase 0) |
| **LT** (main) | 0 | s₀² + s₁² h h′ + a² Matérn-3/2 ARD(x4) | s₀², s₁², a² ∈ [1e-3, 1e3], ℓ ∈ [1e-2, 1e2] | proposed model |
| **M3_Cfree** (ablation) | H₁(h): the same logistic with C = 1 | r² Matérn-3/2 ARD(x4) | r² ∈ [1e-3, 1e3] | "regularize and uncap M3" |
| **H** | H₁e6(h) | — | — | physics-only reference (model quality only) |

**LT in words.** The physics trend is a linear function of h with Gaussian priors on intercept and slope
(variances s₀², s₁²) that are integrated out (explicit basis functions; O'Hagan 1978; Rasmussen & Williams
2006 §2.7), plus a 4-D ARD Matérn residual with free amplitude. ML-II learns how much to trust the trend
(s₁²) and how strongly to let the residual override it (a²). With s₁² → 0 it is G3; with a² small it is a
Bayesian (shrunk, uncertainty-propagating) version of H. Nothing in it is new as a model class; what is
being tested is whether replacing M3's *fixed, saturating* physics level with a *learned-strength, integrated*
physics trend fixes M3's defects without losing its benefit.

## Why these two (Phase 1 evidence; DEVELOPMENT / POST-HOC)
1. M3's C = 1e6 mean saturates (OLD B8–B16: labels separable in log h in 55–75% of prefixes, coefficient
   ≈ 20, 65–69% of the campaign at |m| > 5); log loss at NEW AL prefixes 0.686 vs 0.253 with C = 1.
2. M3's residual cap binds (median r² = 1.0) and cannot override the mean: on NEW AL prefixes the truth
   contradicts the physics sign at 10.7% of test points, M3 overrides at 0%.
3. Transfer: the physics level moved (log-h threshold 20.69 OLD → 20.82 NEW; an oracle intercept lifts M3's
   transfer BA 0.579 → 0.700) and the physics direction is weaker on NEW (AUC log h 0.857 vs VX 0.899).
4. ML-II, given the chance (LT), turns the trend off on NEW (s₁² at its lower bound) and on on OLD
   (s₁² ≈ 109) — learned prior strength.
5. Development AL (Week 13 generator + curvedMono): LT + margin NSD AULC 0.905 vs G3 0.861, M3 0.853,
   M3_Cfree 0.867; LT > G3 in 10/10 cells.

## Acquisition rules compared (identical paid startup and accounting)
margin (argmin |p − ½|), Candidate-B-like coverage → margin at B40 (synthetic: Week 13/15 rule; real: the
exact historical `external_validation.runner._select` Candidate-B selector fed with each model's p),
PEER (coherent one-step expected Hamming reduction on a 400-point reference cloud, exact Gaussian
conditioning, no refits — EER/SUR with the Letham et al. 2022 closed form), random.
