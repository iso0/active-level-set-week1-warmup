# RC20 model definitions (extends `opus_rc19b/MODEL_DEFINITIONS_RC19B.md`; code `src/rc20_attr.py`, `src/rc20_gp.py`, `src/rc20_final.py`)

Everything is learned from the **paid runs only**. Inputs are x = (P, VX, LS, ST), standardised on the candidate pool's public log inputs to z. Paid outcomes per run:
- the Keyhole label y;
- A = log active maximum depth (µm);
- T = T0-window median maximum temperature (K);
- S = velocity-spike log ratio;
- record quality q (a short record gets noise × 10⁴).

## The physics coordinate

log h = log P − ½ log VX − 3/2 log LS, with h = P / sqrt(VX · LS³) in W s^½ m⁻².
- LS is the Gaussian laser spot radius in metres (40–90 µm; claims C20). With a diameter convention, log h shifts only by a constant, which the standardisation absorbs.
- h~ = (log h − mean_pool) / sd_pool, where the pool statistics use public inputs only.
- h is a scaling proxy computed from public inputs. It is not a measured enthalpy and not an observed channel.

## Upstream emulators (predicted physical features m_t(x), t ∈ {A, T, S})

- **M0Q:** one GP per output, f_t ~ GP(0, s_t² Matérn-3/2-ARD(z, z'; ℓ_t)), Gaussian noise σ_t² · w_i (w_i = 10⁴ for a short record), ML-II, targets standardised on the training rows.
- **SHQ:** as M0Q, but ℓ is shared by A, T, S. It is fitted on the paid rows that have all three outputs; per-output (s_t², σ_t²) are fitted at the shared optimum.
- **SHQT (log-h mean, variant 2):** y_t = f_t(z) + β_t h~(x) + ε, with β_t ~ N(0, b_t²) integrated out, so the kernel gains b_t² h~ h~'.
  - b_t² is fitted by ML-II with the other hyperparameters inside each training subset, bounds [1e-8, 10]. At its lower bound the model equals SHQ (validated).
  - The trend uncertainty is propagated into every prediction.
  - The Matérn part keeps all four inputs (ST included), so the GP can correct an inaccurate physics trend.
- **SHQM (pilot only):** SHQ with MAP lengthscales, log ℓ ~ N(0, 1²).

## Honest cross-fitting (K = min(10, n); fold of the j-th paid run = j mod K)

For each fold k, the upstream emulator is refitted on the paid runs outside the fold. That refit covers:
- the hyperparameters;
- the shared lengthscales;
- the trend strength b²;
- the target normalisation;
- the quality weights.

The refitted fold model predicts its own fold, giving out-of-fold features F_i = (Â_i, T̂_i, Ŝ_i). Validated: a run's own outcomes never change its own F_i or its own fold model.

## Classifiers (one L2 logistic family, C = 1, features standardised with the out-of-fold training rows)

The classifier and its deployment:
- Training: η(x) = c + Σ_j w_j (u_j − μ_j) / σ_j, p = 1 / (1 + e^{−η}), where u is the feature vector and (μ, σ) its training mean and SD.
- Deployment: u = the full-paid emulator's predictive means at x (plus the exact h~(x) where used).

| name | feature vector u | upstream |
|---|---|---|
| M0Q_A (= DEPTHCF) | Â | M0Q |
| M0Q_ATS | Â, T̂, Ŝ | M0Q |
| SHQ_A | Â from the SHQ fit on A, T, S | SHQ |
| SHQ_ATS (= ATSCF) | Â, T̂, Ŝ | SHQ |
| SHQ_A_H / **SHQ_ATS_H (the RC20 candidate)** | + h~ (exact, public) | SHQ |
| SHQT_A / SHQT_ATS | Â / Â, T̂, Ŝ | SHQT |
| HONLY | h~ only | none |
| SHQ_ATS_X / SHQ_A_X (exploratory) | + the 4 standardised log inputs z (generic control for h) | SHQ |
| ATSAPPROX (RC19) | Â, T̂, Ŝ as closed-form LOO of the FULL fit (approximation) | SHQ |

The h coefficient in SHQ_ATS_H is shrunk by the same L2 penalty as every other feature. Unlike historical M3, there is no saturated C = 1e6 trend and no capped residual.

## Selectors

- **Margin:** argmax over the candidates of −|p(x) − 0.5|.
- **η-straddle (RC20):** argmax of 1.96 · sd(η(x)) − |η(x)|, with Var η(x) = Σ_t (w_t / σ_t)² v_t(x).
  - v_t is the upstream GP latent variance (no observation noise).
  - The outputs are independent given the hyperparameters, and the classifier weights are a plug-in.
  - Checked against Monte Carlo: median relative error 1.6 %.
- **E1 straddle** (controls): 1.96 σ_A − |μ_A − u|.

## Endpoints

- **AULC:** the mean over the recorded budgets of a window (small = 8–24, all = 8–60), total paid simulations including the 8-point startup.
- **Target attainment:** the level holds at b and at the second checkpoint b + 4; spend = b + 4; censored if not confirmed by B60.
- **Restricted paired spend:** censored scored 64, a lower bound.
