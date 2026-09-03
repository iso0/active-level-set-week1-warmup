# Acquisition definitions

- **M3_MARGIN:** `1-2|p_M3-0.5|`; point-local. `p_M3` integrates latent Gaussian variance, so this is not variance-blind. It does not separately reward epistemic variance or global expected reduction.
- **M3_STRADDLE:** `1.96 sigma_f-|mu_f|`; point-local latent-Gaussian adaptation of the canonical experimental Gotovos score. The 1.96 value is fixed, not outcome-tuned; Laplace classification does not inherit the original Gaussian-noise theory.
- **M3_EMI:** `sigma phi(|mu|/sigma)-|mu|Phi(-|mu|/sigma)`; point-local expected latent incorrectness relative to zero.
- **M3_SMOCU_APPROX:** expected finite-pool reduction of `k^-1 log(exp(kp)+exp(k(1-p)))`, `k=10`, using a disclosed logistic-Laplace rank-one moment update.
- **M3_SUR_APPROX:** expected finite-pool reduction in mean `p(1-p)` under the same update.
- **M3_TMES_GSUR:** local posterior variance reduction multiplied by latent contour-density weight `phi(mu/sigma)/sigma`.
- **PA_TVR_CANDIDATE:** local variance-reduction proxy times the supplied physics-gradient gate. It is neither a demonstrated tangent integral nor a global look-ahead.

All scores are maximized. Exact and approximate labels are retained in names and reports.
