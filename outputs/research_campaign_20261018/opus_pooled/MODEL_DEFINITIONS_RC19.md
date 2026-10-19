# RC19 — model, selector and endpoint definitions (plain equations)

Pooled from scratch: one pool of 541 SPH simulations, and every revealed simulation counts (startup included).

**Inputs:** x = (P, VX, LS, ST); z = standardised log inputs (mean and SD over the candidate pool's inputs, which are known before any query).

**Budget b** = the total number of revealed simulations, including the 8-point startup.

## Physical-output models (regression; one per output t, refitted on all revealed runs after every query)

**M0 — per-output Gaussian process:**

  y_t(x) = μ_t + σ_t f_t(z) + ε,   f_t ~ GP(0, s²_t k(z, z′)),   ε ~ N(0, σ_t² s²_n,t),

with Matérn-3/2 ARD kernel k(r) = (1 + √3 r) e^(−√3 r) and r² = Σ_d (z_d − z′_d)² / ℓ²_t,d.

The hyperparameters (s², ℓ, s²_n) are fitted by ML-II on the revealed runs of output t only.

**M0Q — M0 + paid-record quality:** the noise of revealed run i is multiplied by w_i:
- w_i = 10⁴ if its record ended before 0.95 × its own planned end time (a truncated record);
- w_i = 1 otherwise.

The run keeps its cost, is still evaluated as a test point elsewhere, and only its *own* revealed quality is used.

**SHQ — shared lengthscales + quality:** one lengthscale vector ℓ for all 8 outputs, maximising Σ_t log p(y_t | ℓ, s²_t, s²_n,t), with per-output signal and noise variances, plus the Q weights.
- Rationale: the outputs of one simulation share the same input geometry, so pooling the evidence about ℓ identifies it better at small budgets.
- With isotopic outputs and a common kernel, coregionalisation would add parameters without adding predictive information.

**Prediction:** latent mean μ*(x) and latent variance v*(x); the observation variance adds the noise once.

## Selectors

| Selector | Next query |
|---|---|
| MAXIMIN | the next point of the label-free maximin path (the same path that provides the startup) |
| RANDOM | seeded uniform choice among the unrevealed candidates |
| MOIVR (regression) | argmax_x Σ_t IVR_t(x) / Var_t, with IVR_t(x) = Σ_{j ∈ pool} Cov_t(j, x)² / (v_t(x) + noise_t) |
| STRADDLE (region) | argmax 1.96 √v*(x) − \|μ*(x) − τ\| |
| TRUVAR (region; fixed settings) | argmax of the total latent-variance reduction over the unclassified set U = {\|μ* − τ\| < 1.96 √v*}; straddle if U is empty |
| MARGIN (label) | argmin \|p(x) − 0.5\| |

## Keyhole classifiers (labels and depths only from revealed runs)

**G3:** a GP classifier on x (logit link, Laplace approximation, ML-II); p(x) = P(Keyhole | x).

**E1:** a GP regression of log depth A on x, plus a depth threshold u learned from the revealed (A, label) pairs.
- u is the midpoint between the classes if they are separable, otherwise a 1-D logistic boundary.
- Then p(x) = Φ((μ_A(x) − u) / σ_A(x)).
- Its straddle selector is argmax 1.96 σ_A − |μ_A − u|.

**PHYSCF (from-scratch physical-output classifier, cross-fitted):**
1. Fit SHQ on the revealed runs for the outputs O = {log A, max temperature T0, spike log-ratio}.
2. For every revealed run i, compute the leave-one-out predicted outputs ŷ_{−i}, so that each training feature is a prediction the model made without that run.
3. Fit g = L2-logistic regression (C = 1) on (standardised ŷ_{−i}, label_i).
4. At a new x: p(x) = g(μ_O(x)), the classifier applied to the predicted outputs.

Training and deployment therefore both use predicted summaries, and the predicted outputs are never counted as measurements.

**PHYSMC (measured-trained, uncertainty-integrated ablation):** g is trained on the measured outputs of the revealed runs; then p(x) = (1/200) Σ_s g(ỹ_s), with ỹ_s ~ N(μ_O(x), v_obs,O(x)).

**One-class rule:** until both classes are revealed, every arm predicts the revealed class rate and follows the label-free path. Every query is counted, and no hidden-data threshold is used.

## Endpoints

- **R²(b):** 1 − Σ(y − μ*)² / Σ(y − ȳ)² over the test runs of a repeat (the 5 folds pooled; every run is tested once per repeat).
- **R²-AULC:** the mean of R²(b) over the recorded budgets B8, B12, …, B80.
- **BA(b):** ½ (recall_in + recall_out); BA-AULC = the mean of BA(b) over B8…B60.
- **Target endpoint at an absolute level L:**
  - first qualifying b: the first recorded b with metric ≥ L;
  - confirmed b: metric ≥ L at b and at b + 4, which spends b + 4 simulations;
  - if not reached by the horizon: censored (no number imputed).
- **Joint endpoint:** all 8 outputs at their levels at the same b.
- **Paired contrast:** Δ_r = metric(arm A, repeat r) − metric(arm B, repeat r).
  - BETTER iff mean Δ ≥ 0.02 and Δ_r > 0 in ≥ 7 of 8 repeats.
  - WORSE symmetrically.
  - Otherwise NOT DIFFERENT.
