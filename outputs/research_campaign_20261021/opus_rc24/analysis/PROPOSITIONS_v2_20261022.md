# RC24 analysis, version 2 (dated correction 2026-10-22)

This version replaces `PROPOSITIONS.md` (v1, kept unchanged as the RC24 record) wherever the two differ. Every result below is stated with its assumptions.

**Removed or weakened from v1:**
- **P2's general asymptotic guarantee** is withdrawn. The numerical counterexample is below.
- **P1** is now conditional: correct structural coefficients are an assumption, not a result.
- **P3** is restricted to a single fixed configuration.
- **P4** is conditional, and says nothing about the real corner.
- **P5** separates finite-family members, limits and conceptual relatives.

## 0. The physics coordinate: units and its relation to normalised enthalpy

h = P / √(VX · LS³), with P in W, VX in m/s and LS (the spot radius) in m.

- **h is not dimensionless.** [h] = W · (m s⁻¹ · m³)^{-1/2} = W · s^{1/2} · m⁻². v1 and the RC24 paper draft called h a "dimensionless physics number". That is wrong.
- **Normalised enthalpy** (Hann et al. 2011; King et al. 2014) is

  ΔH / h_s = A P / (π h_s √(D VX a³)),

  where A is the absorptivity, D the thermal diffusivity, a the beam radius and h_s the enthalpy at melting, h_s = ρ c (T_m − T₀) in the usual form.
  - With a = LS, and A, D, ρ, c and T_m constant across the runs, log(ΔH / h_s) = log h + const.
  - The standardised coordinate z_h (log h standardised on the pool) is then identical to the standardised log normalised enthalpy. **z_h is dimensionless.** h itself is not.
  - The constant drops out; it would matter only if material properties varied between runs.
- **What the constant-property assumption leaves out.**
  - If h_s depends on the initial / substrate temperature (ST in our inputs, via T₀), the normalised enthalpy also depends on ST, and our h omits that term.
  - Absorptivity that varies with regime (keyhole vs conduction) is also outside this mapping.
  - These assumptions are stated, not tested.

## 1. P1, conditional: slope error of stacking under extrapolation

Working model:
- A(x) = μ + θ z_h + g(x);
- η = α_h z_h + α_A A(x) + ε;
- a linear stacked classifier η̂ = c₀ + c_h z_h + c_A Â.

**Assumption (not a result):** the stacked fit recovers c_h ≈ α_h and c_A ≈ α_A. Honest stacking does not guarantee this:
- out-of-fold features carry prediction error, which attenuates c_A;
- z_h and Â are collinear;
- the learned regularisation shrinks the coefficients.

**Under that assumption, at a point where the GP part has reverted to its prior mean:**
- with a constant-mean emulator, the slope error along z_h is −α_A θ;
- with an anchored emulator, it is α_A(θ̂ − θ).

Without the assumption, P1 is only a mechanism hypothesis. Its empirical counterpart is the matched comparison TR_PHYS vs TR_NONE vs TR_GEN on identical paid samples (`post_audit/TREND_CONTROL.md`). That comparison is evidence about this pool, not a proof.

## 2. P2, corrected: when is the trend coefficient learned?

**Setting.**
- y = θ h + r, with r ~ N(0, K): K is the GP-plus-noise covariance, without the trend.
- Prior θ ~ N(0, b²).
- The posterior mean is θ̂ = b² hᵀ(K + b² h hᵀ)⁻¹ y = b² hᵀK⁻¹y / (1 + b² q), with q = hᵀK⁻¹h (Sherman–Morrison).

**Result (exact, for any n).**
- If θ = 0, then Var(θ̂) = b⁴ q / (1 + b² q)².
- If θ ≠ 0, then E[θ̂] = θ b² q / (1 + b² q).

**Consequence.** θ̂ concentrates at the true θ only when the information q → ∞.

**This is not automatic.** When the residual covariance can itself represent a component along h, q stays bounded.

Counterexample, computed numerically (`post_audit/p2_counterexample`; b = 3, h = ±1 centred, K = I + h hᵀ):

| n | q = n / (1 + n) | Var(θ̂), formula | Var(θ̂), Monte Carlo |
|---|---|---|---|
| 10 | 0.909 | 0.873 | 0.850 |
| 100 | 0.990 | 0.816 | 0.794 |
| 1000 | 0.999 | 0.811 | 0.820 |
| 4000 | 0.9998 | 0.810 | 0.833 |

With K = I instead, q = n and Var(θ̂) ≈ 1/n.

**Relevance here.** The Matérn residual with long lengthscales can approximate a linear function along z_h over the sampled range. The physics trend and the residual are then only weakly separated: q grows slowly or stays bounded.

**What can be claimed.**
- Under extrapolation, the anchored predictive mean far from the data is μ + θ̂ z_h. It depends on θ̂, and therefore on the prior b and on how much of the trend the GP residual has absorbed.
- Absent a growth condition on q, there is **no general guarantee** that the anchor is harmless when the physics trend is absent.
- The synthetic family results (S2: cost ≤ 0.006 when the anchor is wrong or useless) and the prior-sensitivity results (b = 1, 3, 10 nearly identical on the real pool) are **finite-sample evidence on these designs only**.

## 3. P3, restricted: errors-in-variables integration and a single configuration's decision

**Assumptions.**
- One FIXED configuration: fixed weights, fixed features.
- A latent affine in a Gaussian covariate a ~ N(m̄, v).
- A symmetric, strictly increasing link.

**Result.** E[σ(m₀ + c(a − m̄))] ≥ ½ if and only if m₀ ≥ 0.

**What does not follow.** The statement does not extend to the whole system. In the full system, the grid weights and the features are refitted at every budget, the mixture over configurations can move the 0.5 decision, and the integrated probabilities change the margin ranking and therefore the paid set.

The RC24 pilot observation (PAC ≈ PAC_PLUG in BA) is an empirical observation, not a consequence of P3.

## 4. P4, conditional: margin and an aleatoric region

**Assumptions.**
- A region R where the TRUE P(y = 1 | x) = ½.
- A model consistent on R.
- New labels in R that do not change predictions outside R.

**Result.** Under these assumptions, margin keeps assigning queries to R, while the expected error reduction on other inputs tends to 0 for candidates in R.

**What P4 does not show.**
- P4 is **not evidence that the real fast-scan corner is aleatoric.** Its true conditional probability is unknown.
- The corrected timing diagnostic (`post_audit/TIMING_CORRECTION.md`) describes a label ordering. It does not establish randomness.
- The synthetic S5 result shows that an aleatoric box away from the model's boundary is *not* over-sampled. The real corner's 45 % share therefore reflects its position on the decision boundary, whatever its true label noise.

## 5. P5, corrected: what is nested, what is a limit, what is only similar

**The finite family actually fitted.**
- The Laplace classifier on [z_h, Â], with (τ_A, τ_h) ∈ {0.5, 1, 2, 4}² weighted by the marginal likelihood.
- τ_A = 0 is **not** in the grid. The h-only classifier (HONLY_LR) is therefore **not a member** of the finite HA_LEAN / HA_TREND family.
- h-only is a limit (τ_A → 0) and a separately fitted control. A small depth coefficient is the closest the grid can get.

**Limits.**
- E1 (a depth threshold integrated over the depth GP) is the limit β_h = 0, τ_A → ∞ of the structural composite PAC. It is not a member of the stacked family.

**Conceptual relatives, not members.**
- The historical M3: a fixed saturated logistic h mean plus an amplitude-bounded ARD residual GPC.
- Hardcastle et al. 2025: a fixed physics prior mean in a GPC.
- Ziatdinov et al. 2021: a parametric physics mean with HMC.
- These share the idea "physics in the GP mean", but differ in where the mean enters (classifier vs auxiliary emulator), in whether it is fixed or learned, and in inference.

**Within the stacked family, the exact nesting is:**
- TR_NONE ≡ HA_LEAN (verified bit-for-bit);
- TR_PHYS ≡ HA_TREND (bit-for-bit);
- TR_PHYS ⊂ TR_GEN as the direction-constrained special case θ = c · d_h. The direction d_h is a fixed vector in standardised log-input space, because log h is linear in the log inputs.
