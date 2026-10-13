# Mechanism report — why the joint model ranks NEW well but does not classify its negatives at p ≥ 0.5

**Sources:** Stage M cache and `mechanism/*.csv` (`python -m src.jdl_mechanism`).
- **Pre-declared:** every diagnostic except the threshold-alignment table.
- **POST-HOC:** the threshold-alignment table was added after the Stage M result was seen and is marked as such.
- **Evaluation-only strata:** labels, fast scans, short-K and support classes never reach a model.
- **Run names:** H codes are shorthand. `errors_by_full_id.csv` and `NEW_negatives_by_arm.csv` carry full simulation IDs.

## 1. Who is misclassified (OBS; NEW, B40, both repeats)

| Stratum (n) | J error rate | Binary_matched | ACTIVE_E1 | G3 | Mean p (J) |
|---|---:|---:|---:|---:|---:|
| Negatives (12) | 0.875 | 0.875 | **0.500** | 0.708 | 0.687 |
| Positives (124) | **0.020** | 0.032 | 0.040 | 0.056 | 0.921 |
| Fast scans, VX > 0.85 (23) | 0.522 | 0.543 | 0.435 | 0.630 | 0.639 |
| Short-K positives (10) | **0.250** | 0.300 | 0.400 | 0.600 | 0.618 |
| A missing (1: H-e7dbd8e5ce, a negative) | 1.000 | 1.000 | 1.000 | 1.000 | 0.983 |
| Early-ending records (79) | 0.025 | 0.025 | 0.019 | 0.025 | 0.959 |

- **Where the negatives are.** Eleven of the 12 NEW negatives are fast scans (VX 0.90–0.98 m/s). The twelfth, H-e7dbd8e5ce, is a slow scan with no A. It sits among deep positives, and every arm calls it positive.
- **Hard cases.** Among the fast-scan negatives, J's mean p at B40 ranges from 0.40 (G5, H-b302fc6cbd) to 0.82 (H-29cf03a279).
- **Correct calls.** Only three of the 24 negative predictions fall below 0.5: G5 (0.275) and H-1d4ea0f649 (0.434) in repeat 1, and H-6f28bdc6c9 (0.479) in repeat 2.

## 2. Where the label–depth disagreement goes: into θ, into δ, or nowhere? (OBS; `latent_decomposition_by_class.csv`)

NEW, B40: the latent margin h = f − θ + δ, averaged per class.

| Arm | Class | f (predicted log(A/111)) | θ | δ | h | Share with p ≥ 0.5 |
|---|---|---:|---:|---:|---:|---:|
| J | negatives | 0.268 | −0.014 | +0.018 | 0.300 | 0.875 |
| J | positives | 0.855 | 0.000 | −0.005 | 0.850 | 0.980 |
| J_no_delta | negatives | 0.269 | −0.010 | — | 0.278 | 0.833 |
| Binary_matched | negatives | 0.035 | −0.188 | −0.032 | 0.191 | 0.875 |

- **Not absorbed into θ.** θ stays at about 0 (posterior SD 0.155), and removing δ hardly moves it (J_no_delta θ −0.010).
- **Not represented by δ.** Its posterior means are tiny: |δ| 0.04–0.06 against a prior SD of 0.35.
- **Left unresolved.** The negatives keep h ≈ 0.30 > 0, so p ≈ 0.69. Ranking still works: the mean h is 0.30 for negatives and 0.85 for positives, and AUC is 0.873.
- **The depth prediction is too deep for fast-scan negatives.**
  - Predicted f is 0.10 to 0.42. Observed z = log(A/111) is −0.33 to +0.17, i.e. 79–131 µm.
  - The response GP, with lengthscale 1.5 on standardized log inputs, smooths the slow-scan depths into the fast-scan corner.
- **Held-out A would help, but not fully.** The response-oracle diagnostic (§4) shows that even the true A only partly separates the fast-scan negatives.
- **None of this proves morphology or annotation error.** It is a statement about this prior's capacity.

## 3. Threshold uncertainty: Astra's θ-conditioning diagnostic vs a fixed-θ refit (OBS; `theta_conditioning_vs_fixed_theta_refit.csv`)

| Population, B | θ-conditioned: max \|Δp\| | Decision changes | J_fixed_theta refit: max \|Δp\| | Decision changes (on negatives) |
|---|---:|---:|---:|---|
| NEW 16 | 0.017 | 0 | 0.047 | 3 (2) |
| NEW 40 | 0.017 | 0 | 0.046 | 0 |
| OLD 16 | 0.041 | 0 | 0.092 | 14 (6) |
| OLD 40 | 0.030 | 0 | 0.095 | 9 (5) |
| POOLED 16 | 0.046 | 0 | 0.119 | 12 (10) |
| POOLED 40 | 0.026 | 0 | 0.058 | 3 (2) |

- **The two quantities are different.** Conditioning the fitted joint posterior on θ̂ removes only the local contribution of θ uncertainty to Var(h), and it never changes a decision. Refitting with θ fixed at the prior mean changes the fit itself (other components re-balance), and it changes up to 14 decisions.
- **The posterior on θ is informative but stays centred near 0 (111 µm).** Its mean is −0.15 to +0.10 and its SD 0.14–0.27, down from 0.35.

## 4. The same simulations through two lenses: GP prediction vs response oracle (held-out A, NOT deployable; `oracle_response_vs_gp_same_simulations.csv`)

BA on the 135 NEW runs with A (11 negatives), repeat 1 / repeat 2:

| | J, GP | J + held-out z | ACTIVE_E1, GP | ACTIVE_E1 + held-out A ≥ u |
|---|---|---|---|---|
| NEW B16 | 0.632 / 0.545 | 0.757 / 0.723 | 0.620 / 0.624 | 0.674 / 0.670 |
| NEW B40 | 0.579 / 0.537 | **0.790 / 0.719** | 0.794 / 0.711 | 0.740 / 0.715 |
| OLD B40 | 0.947 / 0.907 | 0.985 / 0.963 | 0.952 / 0.932 | 0.979 / 0.967 |

- **What the response carries.** Observing the held-out A would raise J's NEW BA by about 0.2, so the response does carry label information.
- **Where J loses.** J's loss is in predicting A for the fast-scan negatives, not in how it uses A.
- **ACTIVE_E1 is already near its oracle.** Its decision depth-threshold u sits where the paid labels change, so its GP decisions are close to its own oracle.

## 5. Ranking, probability scores and decisions are different things (PRED)

| NEW, B40 | AUC (ranking) | Log loss | Brier (scores) | BA at 0.5 (decisions) |
|---|---:|---:|---:|---:|
| J | 0.873 | **0.212** | 0.063 | 0.552 |
| ACTIVE_E1 | **0.893** | 0.799 | 0.070 | **0.730** |
| G3 | 0.819 | 0.307 | 0.091 | 0.618 |
| Binary_matched | 0.800 | 0.384 | 0.108 | 0.546 |

**Reliability (`reliability_bins.csv`, NEW B40, both repeats, 272 predictions, 24 negative predictions):**
- **J:** 200 predictions fall in [0.9, 1.0], with an observed positive rate of 0.99 (2 negatives). The 21 predictions in [0.7, 0.8) have an observed rate of only 0.57 (9 negatives). J is over-confident exactly where the fast-scan negatives sit.
- **ACTIVE_E1:** 243 predictions are ≥ 0.9 (observed rate 0.963, 9 negatives), and 15 are below 0.1 (observed rate 0.47). Seven positives get p ≈ 0.007, which explains its poor log loss.
- **Caveat:** with 12 negatives these calibration statements are coarse. A better Brier score alone does not prove better calibration.

## 6. Decision-rule alignment (**POST-HOC**; `POSTHOC_threshold_alignment.csv`)

The comparison: p ≥ 0.5 vs p ≥ the paid-label prevalence of the same checkpoint (train-only) vs the held-out-optimal threshold (NOT deployable; an upper reference).

| NEW | BA at 0.5 | BA at paid prevalence | Optimal (reference) | Specificity at 0.5 → at prevalence |
|---|---:|---:|---:|---|
| J, B16 | 0.581 | **0.819** | 0.822 | 0.167 → 0.917 |
| J, B40 | 0.552 | **0.870** | 0.878 | 0.125 → 0.917 |
| ACTIVE_E1, B40 | 0.730 | 0.784 | 0.883 | 0.500 → 0.625 |
| G3, B40 | 0.618 | 0.722 | 0.775 | 0.292 → 1.000 |
| Binary_matched, B40 | 0.546 | 0.504 | 0.802 | 0.125 → 1.000 |

- **Why it matters.** For a calibrated probability, BA is maximised at p = the class prior, not at 0.5. NEW's paid prevalence is about 0.9.
- **J is ready for the prevalence threshold.** Its probabilities are sharp enough that the threshold lands between its negatives and positives.
- **Binary_matched is not.** Its probabilities, which lack depth information, are compressed below the prevalence, so the same rule calls everything negative.
- **OLD and POOLED.** Prevalence 0.18 and 0.36: the rule leaves J roughly unchanged (OLD B40 0.927 → 0.932) and hurts Binary_matched.
- **Status.** This was seen after the Stage M result and it does **not** change the frozen decision. It is tested prospectively in `exploratory/EX1` on DEV repeats J has never been fitted on.

## 7. Approximation, conditioning and prior diagnostics (OBS)

- **Laplace error** (`laplace_error_NEW_r1_B40_ess.csv`): elliptical slice sampling of the J posterior, NEW repeat 1, B40, folds 1–5, 10,000 samples each, Monte Carlo SE ≤ 0.0045.
  - Maximum |Δp| per fold: 0.023, 0.092, 0.019, 0.035, 0.039. Mean |Δp| per fold: 0.007–0.021.
  - Decision changes per fold: 0, 0, 1, 0, 1 (one of them on a negative).
  - The approximation is adequate for decisions at 0.5 but not negligible for probabilities.
- **Conditioning** (`conditioning_and_convergence.csv`): every J-family fit converged in a few Newton steps. The whitened Hessian's minimum eigenvalue is ≥ 1 by construction. No numerical failure.
- **Positive-depth coupling (HYP).** The fixed coefficient of 1 is helpful on OLD and POOLED. On NEW, fast-scan positives and negatives share depths around 110 µm, so the coupling cannot separate them; that work is left to δ, which under this prior is too smooth and too small.
  - A trained (paid-data-only) or less smooth discrepancy prior would be a separately manifested development step, never one selected on held-out BA.

## 8. Diagnosis of the failed Stage M screen
- **Not numerical, not an adverse trade-off.** Specificity is unchanged and log loss and AUC are clearly better.
- **Insufficient precision.** With 12 negatives, one negative moves BA by 0.042 per repeat, and the +0.01 criterion cannot be resolved.
- **Decision rule.** p ≥ 0.5 is misaligned with BA at 91 % prevalence. This is the largest single factor (POST-HOC, under test).
- **Prior restriction.** A smooth fixed δ and over-smoothed depth predictions in the fast-scan corner.
