# Week 15 theory — boundary-targeted acquisition and a density-corrected boundary metric

Written before the held-out runs. Status labels as in Week 14. Tests: `src/tests/test_week15_*.py`.

Notation: Ω ⊂ ℝ^d the input box; A_f = {f > 0} the (unknown) regime set of the latent f; Â the
predicted set; for a finite cloud Z and graph G on Z, Cut_G(E) = #{(i, j) ∈ G : 1_E(z_i) ≠ 1_E(z_j)}.

## Proposition B1 (cut mismatch = perimeter of the error set). EXACT
For any graph, an edge carries a true crossing but no predicted crossing (or vice versa) iff it is cut by
the error set E = A Δ Â:
  [y_i ≠ y_j] ⊕ [ŷ_i ≠ ŷ_j] = e_i ⊕ e_j,  e = 1[y ≠ ŷ].
*Proof.* (y_i ⊕ y_j) ⊕ (ŷ_i ⊕ ŷ_j) = (y_i ⊕ ŷ_i) ⊕ (y_j ⊕ ŷ_j). ∎
Also, pointwise, cut_E = cut_A + cut_Â − 2 cut_A cut_Â.
*Consequence.* The EBR risk Σ_e P(mismatch on e) is the posterior expected graph perimeter of the error
set, whereas volume SUR (VSUR, the excursion-set/Vorob'ev family) is the posterior expected *volume*
of the same set. Perimeter, not volume, is what boundary metrics such as NSD/ASSD penalize: a spurious
island or a displaced sheet has small volume but large perimeter. The identity also shows that
boundary-mismatch counts are orientation-free (Â = Ω ∖ A has zero error perimeter), as NSD is.

## Proposition B2 (what the uniform-cloud surrogate estimates). THEOREM (consistency) + interpretation
Let Z₁, …, Z_M be iid uniform on Ω and G_r the r-graph. For fixed sets A, Â,
  2 Cut_{G_r}(E) / (M(M−1)) → |Ω|⁻² ∫∫ 1[|x−y| < r] (1_E(x)1_{E^c}(y) + 1_{E^c}(x)1_E(y)) dx dy =: c_Ω r^{d+1} Per_r(E)
almost surely (strong law for U-statistics, bounded kernel), where Per_r is the nonlocal (r-scale)
perimeter; for sets of finite perimeter Per_r(E) → c_d Per(E) as r → 0 (nonlocal-perimeter/Γ-convergence
results, e.g. García Trillos & Slepčev 2016). By linearity, the EBR risk is a consistent estimator of
E_post[Per_r(A_f Δ Â)], and the Dice-normalized risk (EBR-D) of
  E_post[Per_r(A_f Δ Â)] / (E_post[Per_r(A_f)] + Per_r(Â)) = 1 − 2 E_post[S_r(A_f, Â)] / (E_post[Per_r(A_f)] + Per_r(Â)),
with S_r the shared-cut measure (from cut_E = cut_A + cut_Â − 2 cut_A cut_Â). This is one minus a boundary
Dice coefficient at resolution r — the soft analogue of NSD, whose tolerance plays the role of r. The
kNN graph on a uniform cloud gives the same limit up to a constant because the density is constant.
*Caveats.* Ratio of expectations, not expectation of the ratio; edge probabilities use the Laplace
Gaussian posterior with exact pairwise correlations (bivariate normal orthants).

## Proposition B3 (unnormalized boundary risk prefers erasing the boundary). EXACT counterexample
Let the true boundary be a flat sheet of area a whose location is uncertain with posterior spread s ≫ r,
and let Â be the plug-in predictor (a sheet at the posterior location). Then
E_post[Per_r(A_f Δ Â)] ≈ 2 c a (two disjoint sheets except on an event of probability O(r/s)), whereas the
constant predictor Â₀ ≡ majority has E_post[Per_r(A_f Δ Â₀)] = E_post[Per_r(A_f)] = c a. Hence the
unnormalized risk ranks "no boundary" above "correct shape, uncertain location", and an acquisition that
minimizes it is rewarded for pushing the posterior toward small or absent predicted boundaries.
Under the Dice normalization both configurations score 2ca/(ca + ca) = ca/(ca + 0) = 1: the incentive
disappears. *Why it matters:* this is exactly the development failure of EBR (NEW-like cell, σ = 1:
NSD AULC 0.267 vs margin 0.747; the final models nearly constant, dense BA ≈ 0.59), and it motivates the
single principled revision EBR-D.

## Proposition B4 (decomposition of oracle headroom). THEOREM (one step)
Fix a state D. For a candidate c, a truth f and a label y let G(c, y, f) be the gain in the evaluation
metric after adding (c, y). Define the one-step values
  V_R = E_f E_{(y_c)} [max_c G(c, y_c, f)]               (realized-label oracle; y_c ~ P(·|c, f))
  V_E = E_f [max_c Ē(c, f)],  Ē(c, f) = E_{y|c,f} G(c, y, f)  (expectation oracle, knows f)
  V_B = max_c E_f [Ē(c, f)]                               (Bayes one-step rule), f ~ posterior.
Then V_R ≥ V_E ≥ V_B ≥ the value of any non-anticipating rule, when the posterior is the true posterior.
*Proof.* E[max] ≥ max E twice (Jensen for the convex function max), first over the label realizations,
then over f; V_B is optimal among rules that see neither y_c nor f. ∎
V_R − V_E is the expected value of perfect information about the label (peeking), V_E − V_B the value of
knowing the truth; only the gap between V_B and a practical rule is addressable by method design.
*Empirical status (development):* peeking was small (Week 13 generator: 0.003 / 0.000 / 0.028 NSD AULC);
V_E − margin was 0.05–0.08 NSD AULC; in a well-specified 3-D GP world the exact one-step Bayes rule
(posterior-sampled NSD) captured ≈ 24% of the oracle's per-step gain, margin's per-step expected gain
was negative, and EBR-D captured about half of the Bayes rule's gain.

## Proposition M1 (DC-BD estimates the uniform-cloud boundary Dice). THEOREM + caveats
Let X₁, …, X_n be iid with density p on Ω, bounded below by p_min > 0 and continuous, and let the
weights be w_ij = 1/(p(X_i) p(X_j)). For fixed A, Â and fixed r, each of W_T, W_P, W_B divided by
n(n−1)/2 converges a.s. to the corresponding pair integral under **Lebesgue** measure on Ω (U-statistic
with kernel h(x,y) 1[|x−y|<r]/(p(x)p(y)), bounded because p ≥ p_min), hence
DC-BD → 2 S_r(A, Â)/(Per_r(A) + Per_r(Â)), the r-scale boundary Dice of a *uniform* cloud — independent of
the sampling density. With a k-NN density estimate p̂ that is uniformly consistent on Ω (k → ∞, k/n → 0,
p continuous and bounded below), the plug-in estimator is consistent (continuous mapping).
*Caveats.* (i) The fixed trimming of weights at their 95th percentile introduces a bias toward the
sampling-weighted version where p̂ is extreme. (ii) Consistency needs p smooth at the graph scale; thin
high-density bands (Week 14 designs) violate this, and correction is then incomplete. (iii) Labels are
the observed labels: under label noise the estimand includes noise-induced cuts (Week 14 C4).
*Relation to Week 14:* the length-weighted Gabriel metric (wBER/wBEF1) is a heuristic of the same kind
without a proof; DC-BD is the version with a stated estimand.
