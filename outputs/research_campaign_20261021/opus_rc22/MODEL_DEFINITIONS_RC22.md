# RC22 definitions and equations (appendix; code in `src/rc22_common.py`, `src/rc22_eval.py`)

Public inputs x = (P, VX, LS, ST); Z = log inputs standardised on the task's candidate pool; z_h = standardised
log h, h = P / sqrt(VX · LS³) (LS = Gaussian spot radius in metres; W s^½ m⁻²). h is a deterministic public coordinate, not a
measurement. Paid outcomes only (`rc19_pool.Reveal`); test outcomes are evaluator-only.

## Upstream (unchanged RC20/RC21)

The SHQ emulator gives honest out-of-fold predictions F̃ = (log A, T, S) for the paid runs (K = 10 folds; each fold refits the
hyperparameters, shared lengthscales, normalisation and record-quality weights without its own outcomes), and the full-fit means
Ẽ(x) at deployment. Plug-in means only; the emulators' predictive variances are not propagated into any probability.

## Classifiers on [z_h, chosen F̃ columns] (features standardised on the paid rows)

* **SHQ_ATS_H** — L2 logistic, C = 1, free intercept: the MAP under w ~ N(0, I).
* **Learned-regularisation family** (PHR_NRMAP = full; HA_LR = depth only; HONLY_LR = h only).
  - Latent: η = b0 + β_h z_h + Σ_t w_t F̃_t, with b0 ~ N(0, 10²), β_h ~ N(0, τ_h²), w_t ~ N(0, τ_F²).
  - Grid: τ_F, τ_h ∈ {0.5, 1, 2, 4} (HONLY_LR: τ_h only), uniform prior.
  - Each configuration g gets a Laplace mode m_g(x), a latent variance v_g(x) and a marginal likelihood Z_g.
  - Weights ω_g ∝ Z_g; reported probability p(x) = Σ_g ω_g σ(m_g(x)) (plug-in per configuration).
  - The fast residual-free computation equals the RC21 PHR_NRMAP within 9.5e−13.
  - Identifiability: β_h and the w_t are regularised by their priors; they are not likelihood-identified against each other when F̃ varies along h (RC21 erratum).
* **SHQ_ATS_H_RECAL** — logit p′ = a + c · logit p_H.
  - Fit: (a, c) = MAP with a ~ N(0, 1²), c ~ N(1, 0.5²), on honest 5-fold out-of-fold predictions of the COMPLETE SHQ_ATS_H pipeline (upstream CF and classifier refitted without the fold).
  - Fallback: identity below 12 paid runs or 3 of a class.

## Selectors (the predictive model and the 0.5 cutoff are fixed)

* **margin** — next = argmax over unpaid candidates of −|p(x) − 0.5| (first index on ties).
* **BALD_LAP** (Houlsby et al. 2011, arXiv 1112.5745) — mutual information between the next label and the classifier's (configuration, weights) posterior, given the plug-in features:
  I(x) = H(Σ_g ω_g E σ(f_g)) − Σ_g ω_g E H(σ(f_g)), with f_g ~ N(m_g(x), v_g(x)), H(p) = −p ln p − (1 − p) ln(1 − p).
  Both expectations use 64-node Gauss–Hermite quadrature; the Monte Carlo reference agrees within MC error.
* **BALD_GRID** (partial) — H(Σ_g ω_g σ(m_g)) − Σ_g ω_g H(σ(m_g)): configuration disagreement only.
* **Coverage schedule** — query numbers q with q > 8 and (q − 8) mod 5 = 0 (13, 18, …, 58) take the candidate maximising min_j ‖Z(x) − Z(x_j)‖ over the paid runs j. This is label-free, with the cadence fixed before any outcome.
* **MAXIMIN** — every query uses that farthest-point rule.
* **One-class rule** — until both classes are paid, every arm follows the task's label-free continuation (counted).

## Tasks

* **Standard** — rc19_pool splits (seeded 5-fold); startup = the first 8 points of the label-free maximin order.
* **RAND8** — 8 pool points drawn uniformly, rng [2222, r, f, 1].
* **LOCAL8** — the 8 pool points nearest (in Z) to one random pool point, rng [2222, r, f, 2].
* **Continuation** — after RAND8 or LOCAL8: greedy farthest-point order from the startup set.
* **Blocks** — k-means (k = 5, n_init 20, seed 2222) on the log inputs standardised over all 541 runs. Block b is the test set, the other blocks form the pool, startup = maximin order of the pool (rng [2222, seed, b + 1, 3]).
* **Missing-channel stresses** — applied to paid runs' T and S only. MCAR25 / MCAR50 drop each channel with probability 0.25 / 0.50, using u(sim_id, channel) from a seeded hash, so the masks are nested over budgets. QOFF gives short records full weight. SHORTDROP removes T and S of paid short records.

## Metrics

| quantity | definition |
|---|---|
| Learner | one trajectory = one test fold (or block) |
| Fold-pooled curve | the 5 learners of a repeat or seed pooled (RC19–RC21 convention; 541 predictions per budget for blocks) |
| BA | ½ (Keyhole recall + conduction recall); undefined when the test set has one class |
| LL | mean binary log loss, p clipped to [1e−6, 1 − 1e−6] |
| AULC | mean over budgets 8–24 (small) or 8–60 (all) |
| Paired contrasts | by repeat / seed (8 units) |
| BETTER / WORSE | mean beyond the margin and direction in ≥ 7/8 |
| Target confirmation | level at b and at b + 4; spend = b + 4; censored if not confirmed by B60 (scored 64 in paired differences, a lower bound) |
| FEWER | mean ≤ −2, fewer in ≥ 6/8, no extra censoring |

Corner and short-Keyhole diagnostics are evaluator-only; no policy reads them.
