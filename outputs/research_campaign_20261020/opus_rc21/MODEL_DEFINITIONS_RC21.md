# RC21 model definitions (equations; code in `src/rc21_phr.py`, `src/rc21_attr.py`)

All quantities are computed from the public inputs of the 541-run pool and the outcomes of the PAID runs only
(`src.rc19_pool.Reveal`). Inputs x = (P, VX, LS, ST); LS is the Gaussian spot radius in metres.

## Public coordinates

* Standardised log inputs: Z_i = (log x_i − m_i) / s_i, with m, s the mean and SD of log x over the task's candidate pool
  (`rc19_pool.zstd`).
* Physical coordinate: log h = log P − ½ log VX − 3/2 log LS (h = P / sqrt(VX · LS³), W s^½ m^−2);
  z_h = (log h − mean_pool) / SD_pool (`rc20_attr.hcol`).
* h direction in Z-space: a = (1, −½, −3/2, 0), d = (a ⊙ s) / ‖a ⊙ s‖. Since log h − mean = Σ_i a_i s_i Z_i, the projection
  Z·d is exactly proportional to z_h (validated: correlation 1 − 1e−16).
* Transverse coordinates: B = orthonormal basis of d^⊥ (QR of [d, I₄], columns 2–4); U = Z B ∈ R³. Moving a point along d
  leaves U unchanged (validated), so any function of U is constant along the h trend.

## Upstream physical summaries (unchanged from RC20)

SHQ: Matérn-3/2 ARD GPs on Z for (log A, T0-window maximum temperature, velocity-spike log ratio), lengthscales shared across
the three outputs, record-quality noise ×1e4 for short records, ML-II. Honest K-fold cross-fitting (K = min(10, n), fold of
the j-th paid run = j mod K): each fold refits hyperparameters, shared lengthscales, normalisation and quality weights without
its own outcomes. F̃(x_j) = out-of-fold predictive mean for paid run j (training); Ẽ(x) = full-paid fit's predictive mean
(deployment). Features standardised with the out-of-fold mean / SD.

## RC20 reference classifiers (unchanged)

* SHQ_ATS_H: logit p = b0 + w·[F̃, z_h], L2 logistic (sklearn, C = 1, free intercept) — i.e. MAP with w ~ N(0, I).
* SHQ_ATS_X: the same with the 4 exact standardised log inputs Z instead of z_h.

## PHR (the RC21 combination)

Latent score η(x) = b0 + β_h z̃_h(x) + Σ_{t=1..3} w_t F̃_t(x) + r(U(x)), Bernoulli–logistic likelihood
y_j ~ Bern(σ(η(x_j))) for the paid runs (z̃_h and F̃ standardised on the paid rows).
Priors: b0 ~ N(0, 10²); β_h ~ N(0, τ_h²); w_t ~ N(0, τ_F²); r ~ GP(0, σ_r² exp(−‖U − U′‖² / 2ℓ²)).
Integrating b0, β_h, w gives one Gaussian-process prior on η with kernel
  k(x, x′) = 10² + τ_h² z̃_h z̃_h′ + τ_F² F̃·F̃′ + σ_r² exp(−‖U − U′‖² / 2ℓ²).
Identifiability: β_h is the only term that varies along d at fixed U; the residual cannot represent or duplicate the h trend.
h is a deterministic input function and enters exactly once (there is no second "h observation", no product of h-based and
feature-based probabilities, and the emulators do not contain h).

Hyperparameters θ = (τ_F, τ_h, σ_r, ℓ) on a fixed grid G (112 points): τ_F, τ_h ∈ {0.5, 1, 2, 4};
P(σ_r = 0) = ½, P(σ_r = 0.5) = P(σ_r = 1) = P(σ_r = 2) = 1/6; ℓ ∈ {0.75, 1.5} uniform when σ_r > 0.
For each θ: Laplace approximation (Rasmussen & Williams 2006, Alg. 3.1, logistic likelihood; Newton in f = K a with step
halving): mode f̂, W = diag(π̂(1 − π̂)), B = I + W^½ K W^½ = L Lᵀ,
  log Z(θ) ≈ −½ âᵀ f̂ + Σ_j log p(y_j | f̂_j) − Σ log L_ii.
Predictive at a deployment point x*: m* = k*ᵀ (y − π̂), v* = k** − ‖L⁻¹ W^½ k*‖²,
  p_θ(x*) = ∫ σ(f) N(f; m*, v*) df   (64-node Gauss–Hermite; 3e−8 from a 200-node rule).
Posterior weights ω_θ ∝ P(θ) Z(θ); PHR(x*) = Σ_θ ω_θ p_θ(x*). Deployment features: z_h(x*), Ẽ(x*), U(x*).
Uncertainty propagated: classifier coefficients, residual and hyperparameter grid; NOT propagated (named plug-in): the
upstream emulators' predictive variance of Ẽ (same plug-in as SHQ_ATS_H).

By-products (same fits): PHR_NR = posterior average restricted to σ_r = 0; PHR_FX = θ = (1, 1, 0) with the integrated
predictive; PHR_FXMAP = θ = (1, 1, 0) with the plug-in σ(m*) — the SHQ_ATS_H classifier up to the intercept prior
(max |Δp| ≤ 1.1e−3; ≤ 1.1e−5 against the exact free-intercept optimum when the intercept prior is widened).

One-class rule (RC19): until both classes are revealed among the usable paid runs, every construction predicts the paid class
rate and the arm follows the label-free maximin path.

## Selectors

margin: next query = argmax over unpaid candidates of −|p(x) − 0.5| (first index on ties), on the arm's own construction.
E1 + straddle: unchanged RC19B (E1RAW / E1CAL report the same straddle path). G3 + margin: unchanged.
