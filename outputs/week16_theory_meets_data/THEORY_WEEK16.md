# Week 16 theory note — Astra's query-value theory in a Gaussian-latent, noisy-label model

Equation numbers (1)–(15) refer to `outputs/astra_round1/ASTRA_ROUND1.md`. Exact checks:
`src/tests/test_week16_astra.py` (46 tests) and `src/tests/test_week16_peer.py`.

## L1. Binary-observation lemma (the generalization used here)
Let T, O ∈ {±1} have any joint law. The Bayes error for T after observing O is

  e(T | O) = (1 − max(|E T|, |E[T O]|)) / 2.

*Proof.* With O observed the Bayes rule chooses, for each value o, the more likely sign of T. Summing,
e = Σ_o min(P(T = 1, O = o), P(T = −1, O = o)) = Σ_o [P(O = o) − |E[T 1{O = o}]|]/2. Since
E[T 1{O = o}] = (E T + o E[T O])/2, e = ½[1 − (|E T + E[TO]| + |E T − E[TO]|)/2] = ½[1 − max(|E T|, |E[TO]|)]
using |x + y| + |x − y| = 2 max(|x|, |y|). ∎ (Astra §4.1 is the case O = T_j.)

Hence for targets T_i with weights w_i the exact one-step value of observing O_j is

  V(j) = ½ Σ_i w_i (|E[T_i O_j]| − |E T_i|)_+.          (L1)

A query has value for target i only if it can *flip the Bayes decision* at i (|E[T_i O_j]| > |E T_i|).

## L2. PEER: closed form under a Gaussian latent posterior
Laplace GPC posterior f ~ N(μ, Σ); targets T_i = sign f_i (the noise-free level set); observation
O_j = sign(f_j + η_j), η_j ~ N(0, 8/π) (logistic ≈ probit). Then E T_i = 2Φ(μ_i/s_i) − 1 and

  E[T_i O_j] = 4 Φ₂(μ_i/s_i, μ_j/g_j; ρ_ij) − 2Φ(μ_i/s_i) − 2Φ(μ_j/g_j) + 1,  g_j² = s_j² + 8/π,
  ρ_ij = Σ_ij/(s_i g_j),

a bivariate-normal orthant (Owen's T). No refits. Implementation `src/week16_peer.py`; equals Monte Carlo from
the same posterior (Pearson ≥ 0.996, item 0).

## L3. Coherence: exact one-step values are non-negative; Laplace refit look-aheads are not coherent
For any Bayesian model, E_O[min(q_i', 1 − q_i')] ≤ min(E_O q_i', 1 − E_O q_i') = min(q_i, 1 − q_i) by
concavity of min and the martingale identity E_O q_i' = q_i. So the exact expected reduction of the
plug-in Bayes risk is ≥ 0 for every candidate (and equals (L1)). Week 15's VSUR / EBR-D look-ahead replaces
exact conditioning by a *Laplace refit* with each fantasy label. Refits do not satisfy E_y q_i' = q_i; the
measured martingale gap Σ_i |E_y q_i' − q_i| has median 1.1 (range 0.3–4.3) over 400 targets on 18
validation states, and VSUR's refit score is negative for more than half of the candidates in 13 of 18 states. The
Week 15 look-ahead scores are therefore not the Bayes one-step values of their own model; their rank
agreement with PEER is near zero (median Spearman 0.05).

## W16-1. With noisy observations of a latent-sign target the 1/(N−1) margin guarantee fails
Astra's eq. (2) uses v_{j←j} = u_j: revealing Y_j removes all of j's own uncertainty. When the target is
the latent sign T_j and the observation is O_j = sign(f_j + η_j), the self-value at μ_j = 0 is

  V_self(j) = (1/π) arcsin( s_j / √(s_j² + 8/π) ),

which tends to 0 as the posterior sd s_j → 0, although the predictive p_j = Φ(μ_j/g_j) = ½ is exactly
margin-optimal. *Example.* Point a: μ = 0, sd ε; point b: μ = 0.3, sd 3, independent. Margin picks a;
V(a)/V(b) → 0 as ε → 0 (test `test_noisy_observation_breaks_margin_bound`). So margin's competitive ratio
under the model can be arbitrarily close to 0, not ≥ 1/(N − 1).

Interpretation: p_j ≈ ½ conflates an *aleatoric* point (latent pinned near the boundary, observation
nearly a coin flip) with an *epistemic* one (latent unknown). Margin cannot tell them apart; (L1) can.
This is the same distinction BALD draws (mutual information between O_j and f_j), now expressed in
Astra's decision-flip form. Astra's guarantee concerns noiseless revelation of the target itself; in the GPC
model labels are always noisy observations of the latent, so the guarantee does not transfer as stated.

## W16-2. Saturation (flat value landscapes)
Because (L1) counts only decision flips, a confident posterior can have V(j) ≈ 0 for every candidate
(item 0: curvedMono NEW σ = 1 at budget 24, max_j V(j) = 0.002 of 400 targets). Ratios such as r_model are then
undefined; Week 16 reports such states as *saturated* (max V < 1e-6) instead of dividing by zero.

## Corollary 6.1 in this model
Astra's regret bound Δ* − Δ_ĵ ≤ ε_m + ε_c says that control of marginals *and pairwise moments* bounds
one-step regret. For the Gaussian latent model the pairwise moments are the orthant probabilities above, so
the relevant calibration object is the model's *pairwise* predictive law of (T_i, T_k) — item 3 tests
whether its empirical quality (joint near-pair log loss) explains acquisition quality beyond marginal
calibration.
