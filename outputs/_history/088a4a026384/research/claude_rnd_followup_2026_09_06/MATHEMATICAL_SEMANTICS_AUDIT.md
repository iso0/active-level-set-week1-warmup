# MATHEMATICAL_SEMANTICS_AUDIT — exact scope of Propositions 1–3 and the XSUR semantics

Follow-up to `claude_rnd_2026_09_05/MATHEMATICAL_DEVELOPMENT.md` §9. Development data only.

## 1. Proposition 1 (information collapse) — exact scope

Setting: finite pool 𝒫, candidate x ∈ 𝒫, posterior P_n over the pool labelling Y_𝒫 after D_n, noiseless labels (the simulator is deterministic and the model treats labels as determined by its latent object).

**A. Self-including target.** I(Y_x ; Y_R | D_n) = H(Y_x | D_n) = H_b(π_x) whenever x ∈ R. Proof: Y_x is a coordinate of Y_R. As written in the previous package this is *true but weak*: the target contains the query's own label, so the "information" counted is the query's self-information. Verdict on the previous wording "margin is information-optimal for deterministic simulators": **TOO STRONG as a slogan; VALID for a precisely stated family of targets (below).**

**C. Structured targets that determine Y_x.** Let h be any object that determines every pool label (the hypothesis/labelling, the excursion set S, the threshold surface τ under a graph model, the version space element). If Y_x = g(h) deterministically, then I(Y_x ; h | D_n) = H(Y_x | D_n) − H(Y_x | h, D_n) = H(Y_x | D_n). So for the target "the boundary" or "the set S" — the thesis's actual estimand — **maximising expected information gain is exactly maximum-uncertainty sampling, π_x = ½**. This is the generalised-binary-search / version-space-bisection statement (Dasgupta 2005, "Analysis of a greedy active learning strategy"; Nowak 2011, "The geometry of generalized binary search"; Golovin & Krause 2011): with noiseless labels, the informative query is the one that most nearly halves the posterior mass of hypotheses. It is a standard consequence, not a new result. With a soft link (Y_x | g_x ~ Bernoulli(Φ(g_x)), so h = g no longer determines Y_x), I(Y_x ; g | D_n) = H_b(p_x) − E_g[H_b(Φ(g_x))] (BALD, Houlsby et al. 2011, targeting the latent/parameters), which is not exactly margin: it additionally rewards candidates whose latent is uncertain (large v_x) at equal p_x. On M3 states this second term is nearly constant across candidates (RESEARCH_DIAGNOSIS §5), so BALD ≈ margin there — an empirical, not exact, statement.

**B. Targets that exclude the queried coordinate.** I(Y_x ; Y_{R∖x} | D_n) = H(Y_x | D_n) − H(Y_x | Y_{R∖x}, D_n) ≤ H_b(π_x). The deficit H(Y_x | Y_{R∖x}, D_n) is the part of x's label uncertainty that the rest of the pool cannot explain ("idiosyncratic" uncertainty). Margin therefore gives an *upper bound* on the information a query carries about the other labels; the exact criterion prefers candidates whose label is uncertain **and** predictable from the others (redundant with the pool) and penalises uncertain-but-isolated candidates. For a Gaussian latent model, H(Y_x | Y_{R∖x}) is governed by the cross-covariances C(u,x); when those are small relative to v_x (M3's regime) the two criteria coincide. A q20-like weighted target on other points is a coarsening of Y_{R∖x} and inherits the same inequality (data-processing).

**Exact statements to retain.**
- (P1-A/C) For noiseless labels and any target that determines Y_x (hypothesis, set, boundary, pool labelling), the one-step expected information gain equals H_b(π_x); margin is its maximiser. *Known* (GBS).
- (P1-B) For the labels of other points, expected information gain = H_b(π_x) − H(Y_x | Y_{R∖x}, D_n) ≤ H_b(π_x); margin is not the maximiser in general.
- Withdraw: "BALD-type criteria cannot beat margin" (true only for the self-including/hypothesis target with noiseless labels); "only non-entropic losses can differ" (false: the excluded-target information B differs).

## 2. Proposition 2 (leverage identity) — independent re-derivation and generalisation

**General form.** Let a finite action set 𝒜 and a loss L(a, y_u) at reference point u, with Bayes risk ρ(q) = min_a Σ_y q(y) L(a,y), which is concave and piecewise-linear in the posterior q over y_u. Let the query outcome Y_x take values with probabilities P(y), and q_y = P_n(Y_u = · | Y_x = y), coherent: Σ_y P(y) q_y = q. Then the one-step expected reduction of the Bayes risk at u is

  r_u(x) = ρ(q) − Σ_y P(y) ρ(q_y) = min_a Σ_y P(y) L(a, q_y) − Σ_y P(y) min_a L(a, q_y) ≥ 0,

with L(a,q) := Σ_{y_u} q(y_u) L(a,y_u) linear in q. It equals zero **iff** one action a* attains min_a L(a, q_y) for every outcome y with P(y) > 0 — i.e. iff the Bayes decision at u is the same under both outcomes. This is the classical expected-value-of-sample-information statement (Raiffa & Schlaifer 1961; Howard 1966), made explicit for Bayes classification risk as MOCU (Yoon, Dougherty & Qian 2013; Zhao et al. 2021, "Bayesian active learning by soft MOCU", AISTATS, Lemma 2). **Not new.**

Upper bound. If the decision flips, exactly one outcome y_f carries the non-optimal action (with two outcomes, both cannot be non-optimal for a* since a* is optimal for the mixture), so r_u(x) = P(y_f)·[L(a*, q_{y_f}) − L(a_{y_f}, q_{y_f})] ≤ P(y_f)·Δ_u, Δ_u = the regret range. For symmetric 0-1 loss on a binary Y_u, the previous package's bound r_u ≤ min(π_x, 1−π_x, π_u, 1−π_u) holds (re-derived: with a = P(Y_u=1,Y_x=1), b = P(Y_u=1,Y_x=0), p = P(Y_x=1) and Y_u=1 the overall minority, a flip under y=1 gives r = 2a − p ≤ p and ≤ 1−p because a ≤ ½; symmetric for y=0). For asymmetric costs (c_FN, c_FP) the flip criterion is unchanged (threshold c_FP/(c_FN+c_FP)) and the bound becomes r_u ≤ P(y_f)·max(c_FN, c_FP).

Weighted reference sets, reference sets excluding x, q20-like fixed weights: the identity is termwise, so A(x) = Σ_u w_u r_u(x) with the same flip condition for every u; including or excluding x changes only the single term u = x (for which the "flip" is the query resolving its own label; r_x = min(π_x,1−π_x) under the noiseless-observation semantics, less under a noisy one).

**What Proposition 2 closes and does not close.**

| Loss on the reference set | Zero without decision flips? | Reason |
|---|---|---|
| posterior Bayes 0-1 risk Σ w_u min(q_u, 1−q_u), any costs | **yes** | piecewise-linear concave risk (above) |
| symmetric-difference set loss with plug-in set Ŝ = {q ≥ ½} | **yes** | equals the 0-1 risk |
| Brier risk Σ q_u(1−q_u) | no | expected reduction = Σ_u Var(q_u^{(Y_x)}) = E[(q'−q)²] > 0 whenever the posterior at u moves |
| log loss / entropy Σ H_b(q_u) | no | expected reduction = Σ_u I(Y_u; Y_x | D_n) > 0 whenever dependent |
| threshold-location variance Σ Var(τ_u), eq. (9) | no | reduction ∝ Σ C(u,x)² > 0 whenever correlated |
| Hausdorff / boundary-location losses under a Gaussian posterior | no | continuous functionals of the posterior moments |

So Proposition 2 explains why *plug-in set / 0-1* criteria (XSUR, exact SUR-of-misclassification, MOCU) can be identically zero late and why they can prefer less uncertain candidates only through flips; it says nothing against variance/entropy-type criteria (TV, GlobalMI, Brier-SUR), which are positive whenever the posterior moves. The previous package's sentence "every coherent one-step 0-1 set criterion is identically zero when nothing is flippable" is **VALID AS WRITTEN** for 0-1/plug-in-set losses and must not be read as covering the other rows.

**Numerical verification** (exact joint probabilities from the Gaussian latent via bivariate-normal orthants, `xsur.py`): on synthetic states with random posteriors, reduction ≥ 0, exactly 0 whenever no flip, and ≤ N_flip·min(π_x,1−π_x) in every case (200 random states); on six saved T-posterior states along margin paths the same holds for the coherent computation (previous `results/leverage_bound_check.csv` documents the *violations* of the moment-matched approximation, 57–204 per state).

## 3. Proposition 3 / XSUR — probabilistic semantics

Under the T model the latent is g(x) = c(ℓ − τ(z)) with a Laplace-Gaussian posterior, and the observation model is P(Y = 1 | g) = Φ(g), i.e. Y_x = 1{g_x + ε_x > 0}, ε_x ~ N(0,1) independent. Three different coherent joint laws exist for (target at u, query at x):

| Semantics | target at u | query outcome at x | joint | previous XSUR used |
|---|---|---|---|---|
| S1 | Z_u = 1{g_u > 0} (latent membership) | Z_x = 1{g_x > 0} (latent sign) | (g_u, g_x) ~ N₂; P(Z_u=1,Z_x=1) = Φ₂(m_u/√v_u, m_x/√v_x; c/√(v_u v_x)) | **yes** |
| S2 | Z_u = 1{g_u > 0} | Y_x = 1{g_x + ε_x > 0} (the label the simulator actually returns under the model) | (g_u, g_x+ε_x): variances (v_u, v_x+1), corr c/√(v_u(v_x+1)); P(Y_x=1) = Φ(m_x/√(1+v_x)) = p_x | no |
| S3 | Y_u = 1{g_u + ε_u > 0} (future label at u) | Y_x | variances (v_u+1, v_x+1), corr c/√((v_u+1)(v_x+1)); current risk min(p_u, 1−p_u) | no |

S1 is coherent for a model in which the query returns the latent sign — which is *not* the T model's observation model; it overstates both the outcome probability's sharpness (Φ(m_x/√v_x) instead of Φ(m_x/√(1+v_x))) and the correlation with reference latents. S2 is the correct semantics for "learn the latent set from probit-observed labels" (this is exactly Letham et al.'s look-ahead of π under a probit observation; their Theorem 1 uses the (v_x+1) normalisation). S3 is the correct semantics for "reduce the expected number of misclassified *future labels*" (the finite-pool analogue of Roy–McCallum/MOCU under the model's own label law). For the deterministic simulator, the thesis's estimand is the set, so S2 is the primary corrected form; S3 is reported because the endpoint is measured on labels. All three are implemented in `xsur.py::acq_xsur_semantics` (Owen's T; validated: S1 reproduces the previous scores exactly; all three are non-negative, zero without flips, and bounded by the flip count × margin). Rank correlation between S1 and S2/S3 scores on synthetic states is ≈0.90, so the previous replay was not the corrected criterion; §4 reports the corrected replays.

**Terminology to use from now on.** "Coherent one-step expected reduction of the posterior 0-1 set risk under the Gaussian latent posterior with semantics S2 (probit-observed query, latent-membership target)" — not "exact Bayes-optimal". The exactness is (i) exact bivariate-normal orthant probabilities and (ii) exact two-outcome expectation, *given* the Laplace-Gaussian posterior and the stated observation semantics; the Laplace approximation itself and the frozen hyperparameters remain approximations, and the criterion is one-step (myopic).

## 4. Corrected XSUR replays (100 runs, M3 evaluator; `results/xsur_semantics_replay.csv`)

Same frozen T posterior (c=7, s_u=0.41, ℓ_s=(1.7,30,30)), same 100 outer runs and B16 designs, reference set = outer training pool, risk floor 10⁻⁶, one-step, tie-break smallest index; M3 evaluated on the resulting paths; paired repeat-block bootstrap (10,000 draws).

| Contrast (q20 accuracy AULC) | 16–32 | 16–40 | 16–48 | 16–80 |
|---|---|---|---|---|
| S1 (latent signs; previous) − M3-margin | −0.0258 [−0.0383, −0.0140] | −0.0284 [−0.0405, −0.0173] | −0.0299 | −0.0303 |
| **S2 (probit query, latent target)** − M3-margin | −0.0269 [−0.0390, −0.0154] | **−0.0281 [−0.0410, −0.0153]** (4/16) | −0.0295 | −0.0327 |
| **S3 (probit query, label target)** − M3-margin | −0.0272 [−0.0396, −0.0150] | **−0.0287 [−0.0415, −0.0163]** (5/15) | −0.0303 | −0.0321 |
| S2 − T-margin (same posterior) | −0.0248 | −0.0247 [−0.0350, −0.0144] | −0.0256 | −0.0259 |
| S3 − T-margin | −0.0250 | −0.0254 [−0.0357, −0.0154] | −0.0264 | −0.0253 |

Selection behaviour is the same under all three semantics (early steps: same top-1 as margin 5–8%, Spearman 0.76–0.78, selected in the physical band 49–51%, selected p ≈ 0.36). **The negative result survives the corrected semantics unchanged**; the previous package's numbers were computed under the wrong (latent-sign) query semantics, but the correction moves the contrast by < 0.003. The statement to carry forward: "under the frozen T posterior, the coherent one-step reduction of the posterior 0-1 set risk (semantics S2, and S3) is dominated by probability margin by ≈0.03 q20-AULC on this pool." The mechanism stands: the criterion spends half of its queries outside the physical band on candidates with many model-expected decision flips (49 per early step versus 19 for margin's choice) that are not realised on held-out rows.

