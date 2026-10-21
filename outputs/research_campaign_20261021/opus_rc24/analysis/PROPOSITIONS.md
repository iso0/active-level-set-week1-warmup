# RC24 analytic propositions (working model; assumptions stated per result)

## Working model

The working model is linear-Gaussian. It is a simplification used for the analysis; the real learners are fitted on the real pool.

- **Physics coordinate.** z = z_h(x) is the known standardised log normalised enthalpy.
- **Auxiliary response (depth).** A(x) = μ + θ z + g(x), where g is a zero-mean process.
- **Label latent.** η(x) = α_h z + α_A A(x) + ε, with ε symmetric noise and the label y = 1[η > 0].
- **Emulators.**
  - Constant-mean emulator: Â_c(x) = E[A(x) | paid data] under a zero-trend GP.
  - Physics-anchored emulator: Â_p(x) = E[A(x) | paid data] under the same GP plus a trend θ z, where θ ~ N(0, b²) is integrated out.
  - "Far" means that the posterior covariance between g(x) and every paid point vanishes. This is extrapolation, as in a held-out geometry block.

## P1. Constant-mean stacking loses the depth-carried part of the physics effect under extrapolation

**Assumption.** A linear stacked classifier η̂ = c₀ + c_h z + c_A Â has been fitted with c_h → α_h and c_A → α_A. This holds when paid z and g vary independently and n is large.

**Claim.** At a far point:
- the constant-mean emulator gives Â_c → μ̄, a constant;
- the latent error is therefore η̂ − E[η | z] = −α_A θ (z − z̄) + const. This is a slope error along z of size |α_A θ|.
- The physics-anchored emulator gives Â_p → μ̄ + θ̂ z, so the slope error is α_A(θ̂ − θ). It vanishes when θ̂ → θ.
- The h-only classifier (c_A ≡ 0) fits the total slope α_h + α_A θ and has no slope error.

**Proof.** At a far point the GP part of either emulator reverts to its prior mean (0). The constant-mean emulator then predicts the training mean of A. The anchored emulator predicts the training mean plus the posterior-mean trend θ̂ z (Rasmussen & Williams 2006, §2.7, explicit basis functions). Substituting into η̂ and subtracting E[η | z] = α_h z + α_A(μ + θ z) gives the stated slope errors. ∎

**Measured on DEV (k-means geometry blocks, seeds 1–8, matched on the RC23 HA_LEAN paths, BA-AULC B8–B60):**

| model | BA-AULC |
|---|---|
| constant-mean stacking (HA_LEAN) | 0.9220 |
| anchored stacking (HA_TREND) | 0.9325 |
| h-only | 0.9392 |

- The anchor closes about 60 % of the gap to h-only.
- A generic linear trend in all four log inputs (PAC_GEN) does not close it (structural form: −0.006 against HA_LEAN). The useful direction is the physics direction, not just "any trend".

## P2. The anchor costs little when the physics trend is absent

**Assumption.** θ = 0, and θ is integrated with prior N(0, b²) (not fixed).

**Claim.**
- The posterior mean θ̂ = b² hᵀ(K + b² h hᵀ)⁻¹ y is O_p(n^{-1/2}).
- So the extra far-point slope error is |α_A θ̂| = O_p(n^{-1/2}).
- By contrast, a FIXED physics mean, such as the historical M3 (logistic h mean at C = 1e6, frozen), carries its full fitted slope into every prediction. With nearly separable paid labels that slope is very large: 29.3 on standardised log h at B8 (RC24 T1 state). The predicted probabilities saturate.

**Proof.** θ̂ is the GLS estimate shrunk by the prior. Under θ = 0 it has mean 0 and variance O(1/n) (a standard random-effects result). ∎

**Measured on fresh repeats 59–66.** M3 is BA-similar to HA_LEAN (non-inferior) but its log loss is worse by +0.30 (B8–B24) and +0.12 (B8–B60). The synthetic families T4 ("anchor useless") and T5 ("no auxiliary value") test this proposition out of sample (`synthetic/`).

## P3. Errors-in-variables integration does not move a single configuration's 0.5 decision

**Assumption.** The latent is affine in the uncertain covariate, m(a) = m₀ + c(a − m̄). The covariate is a ~ N(m̄, v). The link σ is continuous, strictly increasing and symmetric (σ(−t) = 1 − σ(t)).

**Claim.** p = E[σ(m(a))] ≥ 1/2 if and only if m₀ ≥ 0.

**Proof.**
1. p(m₀) = E[σ(m₀ + c√v U)] with U ~ N(0, 1).
2. p is strictly increasing in m₀.
3. By the symmetry of U and σ, p(0) = E[σ(c√v U)] = 1/2.
4. Hence p ≥ 1/2 ⇔ m₀ ≥ 0. ∎

**Corollaries.**
- Integration changes calibration and the margin ranking −|p − 1/2|, which becomes a variance-scaled margin.
- A mixture over configurations can still move the decision slightly.
- The DEV matched pilot agrees: PAC and PAC_PLUG differ by ≤ 0.0002 BA-AULC in every condition.

## P4. Margin keeps sampling an aleatoric region; the expected error reduction on other inputs does not

**Assumptions.**
- In a region R the true conditional probability is P(y = 1 | x) = 1/2 for every x in R (an aleatoric region).
- The classifier is consistent on R.
- New labels in R do not change the predictions outside R in the limit.

**Claim.**
- Margin, s(x) = −|p̂(x) − 1/2|, tends to its maximum 0 on R. Margin therefore keeps assigning queries to R, and its query rate there does not tend to 0.
- The expected reduction of the 0-1 risk on the OTHER inputs, EER_−c(x_c) = Σ_{x≠x_c} [r(p̂(x)) − E r(p̂′(x))] with r(p) = min(p, 1 − p), tends to 0 for x_c in R. Neither the predictions inside R nor those outside it change.

**Proof.**
- Consistency gives p̂ → 1/2 on R, so s → 0 = max s.
- A fantasy label at x_c in R changes p̂′ on R by o(1), because the limit is already 1/2, and by o(1) outside R, by assumption. r is Lipschitz, so the difference tends to 0. ∎

**Remark.** Excluding the own-label term is essential. EER including x_c's own resolution contains r(p̂(x_c)) ≈ 1/2 on R and is attracted to R like margin. The attraction exists only on the pool: test points are never queried, so resolving the pool point itself does not reduce test error.

**Measured.**
- HA_LEAN + margin spends 45 % of its post-startup queries in the fast-scan corner (7 % of the pool), against 24 % for h-only + margin (fresh repeats 59–66).
- The corner's NEW conduction specificity stays near 0.33 at B60.
- The short-Keyhole events there are start-up transients at the end of the forming phase (`hard_region/HARD_MECHANISM.json`). This is the empirical counterpart of R.

## P5. Nesting

The learned-regularisation family on [z_h, Â] contains the following cases:
- **h-only:** the limit τ_A → 0.
- **Stacked HA_LEAN:** constant-mean emulator, honest out-of-fold features.
- **Anchored stacking (HA_TREND):** physics-anchored emulator.
- **E1:** the structural composite PAC with β_h = 0 and a sharp link, i.e. a depth threshold integrated over the depth GP.
- **Historical M3:** a fixed h mean with a residual GP, not in the linear family; it corresponds to τ_h → ∞ with a saturated slope plus a bounded-amplitude residual.

The RC24 comparisons are therefore comparisons inside one family, plus M3, G3 and E1 as historical external controls.
