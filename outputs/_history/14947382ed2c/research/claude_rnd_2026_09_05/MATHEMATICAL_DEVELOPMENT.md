# MATHEMATICAL_DEVELOPMENT — objects, losses, derived acquisitions, reductions

Notation. Inputs x = (P, VX, LS, ST). Physics coordinate ℓ(x) = log h = log P − ½ log VX − 3⁄2 log LS. Context z(x) = (log VX, log LS, ST), standardised on the outer training pool (label-free). The simulator is deterministic: there is a fixed set S ⊂ 𝒳 with Y(x) = 1{x ∈ S}. A finite pool 𝒫 (the 324-row outer training pool) is the only place labels can be bought; the held-out fold 𝒯 (81 rows) is never queried. D_n is the revealed data after n queries.

## 1. Decision loss first

The thesis metric is hard classification accuracy on near-boundary held-out rows. The population loss of a decision rule ŷ_n is L_n = Σ_{u∈R} w(u) 1{ŷ_n(u) ≠ Y(u)} for a reference set R with weights w. Under a posterior with q_n(u) = P(Y(u) = 1 | D_n), the Bayes rule is ŷ_n(u) = 1{q_n(u) ≥ ½} and the posterior Bayes risk is

  R_n = Σ_{u∈R} w(u) · min(q_n(u), 1 − q_n(u)).                                   (1)

The one-step (myopic) value of querying x is

  A_n(x) = R_n − E_{Y_x | D_n}[ R_{n+1}(D_n ∪ {(x, Y_x)}) ].                          (2)

Everything below is (2) for a specific choice of the pair (model, R). Because 𝒯 is unknown to the method and is exchangeable with 𝒫, the reference set is R = 𝒫 \ D_n with uniform weights ("finite-pool transductive risk"); to keep the integration geometry fixed while the query set shrinks, the frozen protocol uses R = the *whole* outer training pool including queried rows (queried rows contribute ≈0 risk and do not change rankings; see §6).

## 2. Which q: predictive label probability p versus latent-set membership π

For a latent-Gaussian classifier with g(u) | D_n ≈ N(m(u), v(u)) and a probit link with unit scale,

  p_n(u) = E[Φ(g(u)) | D_n] = Φ( m / √(1 + v) ),      π_n(u) = P(g(u) > 0 | D_n) = Φ( m / √v ).     (3)

p is the probability that a *new Bernoulli draw* at u is 1; π is the posterior probability that u lies in the latent excursion set. For a deterministic simulator the truth is a set, and the unit-scale link noise is a modelling device (it absorbs exceptions and makes the posterior tractable), not physical randomness. Two exact statements:

(a) Decisions coincide: 1{p ≥ ½} = 1{π ≥ ½} = 1{m ≥ 0}. The *point estimate* of S does not depend on the choice.

(b) Rankings coincide whenever v is (nearly) constant across candidates or |m| ≫ √v: then both |m|/√(1+v) and |m|/√v are monotone in |m|. On the saved M3 states this is what happens (Spearman of the two margins 0.82 at B16, 0.87 at B24, ≥0.98 from B32; RESEARCH_DIAGNOSIS §4). The p/π distinction is therefore *not* the missing reason for the M3 acquisition nulls; it only matters in a model whose latent variance is informative and comparable to |m|.

(c) The decomposition p(1−p) = E[Φ(g)(1−Φ(g))] + Var(Φ(g)) shows that a p-based SUR (Phase 1.18B) rewards changes in the first, non-epistemic term; the π-based risk (1) with q = π contains only reducible uncertainty. With the T model both are computed below; the frozen challenger uses q = π because the estimand is the set.

## 3. The threshold-surface probit model T

  τ(z) = μ + βᵀz + u(z),  μ ~ N(μ₀, s_μ²),  β ~ N(0, s_β² I₃),  u ~ GP(0, s_u² k_{3/2}(z, z'; ℓ_s)),      (4)
  P(Y = 1 | τ, x) = Φ( c · (ℓ(x) − τ(z(x))) ),   c = 1/s.                                                     (5)

For fixed (c, s_u, ℓ_s) this is a probit GPC on the latent g(x) = c(ℓ − τ(z)) with known mean c(ℓ − μ₀) and kernel c²[s_μ² + s_β² z·z' + s_u² k(z,z')] that depends on z only. It is a structured special case of GPC (Keeley et al. 2023 is the closest prior model: contextual threshold and slope GPs with binary observations). The structural content is: (i) single crossing in ℓ at every context (graph restriction), (ii) the ℓ-coefficient is tied to the label softness s, so the residual's capacity to move the boundary is s_u in log-h units *independently of how sharp the link is* — in M3 that capacity is (residual sd ≤ 1)/(Stage-1 slope ≈ 4–21), i.e. 0.05–0.25 log-h units and shrinking exactly when the slope is most separable; (iii) uncertainty is available directly in boundary units:

  τ(z) | D_n ~ N( ℓ − m(x)/c ,  v(x)/c² )   for any x with context z.                                   (6)

Hyperparameters. Type-II ML for (c, s_u, ℓ_s) with 16–40 binary labels is degenerate (development runs: c → lower bound and s_u → upper bound at B16–40; c → 30 in 25% of full-pool fits). The challenger therefore freezes (c, s_u, ℓ_s) at values determined on the old 405 cases (full-pool marginal likelihood: c = 7.0 ⇒ s = 0.143 log-h units, s_u = 0.41, ℓ_s = (1.70, ≥30, ≥30) in standardised (log VX, log LS, ST); the LS and ST length scales are effectively infinite, so τ is a smooth function of VX only) and lets the posterior over (μ, β, u) do all within-run learning. s_μ = 3, s_β = 1 (log-h units per standardised context unit) are broad and fixed; μ₀ is the mean ℓ of the revealed points (label-free). With frozen hyperparameters the model has *no* per-fit optimiser, no bound-hitting, and identical behaviour on old and new pools.

Inference: Laplace approximation (probit likelihood is log-concave, Newton converges in <20 steps); posterior mean and full covariance over any set of locations follow from the standard GPC formulas. Development check against a sampling reference is in OLD_DATA_RND_REPORT.

## 4. One-step look-ahead under T (exact moment update, then risk)

For a candidate x with g(x) ~ N(m_x, v_x), let t = m_x/√(1+v_x), so P(Y_x = 1 | D_n) = Φ(t). Conditioning a Gaussian on one probit observation has closed-form first two moments (Rasmussen–Williams §3.9): with r₁ = φ(t)/Φ(t) and r₀ = φ(t)/Φ(−t),

  Y_x = 1:  m'(u) = m(u) + C(u,x) r₁/√(1+v_x),   v'(u) = v(u) − C(u,x)² r₁(r₁ + t)/(1+v_x),
  Y_x = 0:  m'(u) = m(u) − C(u,x) r₀/√(1+v_x),   v'(u) = v(u) − C(u,x)² r₀(r₀ − t)/(1+v_x),              (7)

where C(u,x) = Cov(g(u), g(x) | D_n) is the joint Laplace posterior cross-covariance (it is the c²-scaled cross-covariance of τ over contexts, minus the data-explained part). The frozen challenger acquisition is (2) with (1), q = π, R = outer training pool:

  A^{SUR-π}_n(x) = Σ_u min(π_n(u), 1−π_n(u)) − Σ_{y∈{0,1}} P(Y_x=y | D_n) Σ_u min(π'_y(u), 1−π'_y(u)),   π'_y = Φ(m'_y/√v'_y).   (8)

This is Letham et al.'s GlobalSUR functional (posterior-membership misclassification risk) evaluated on a finite reference set with the exact two-outcome expectation, under the T posterior. The moment update (7) is exact for the *marginal* of one probit site; recursing it inside a Laplace posterior is the same approximation Letham et al. make. Cost: one O(n³) factorisation per step, then O(|𝒫|²) for the cross-covariance and O(|𝒫|) per candidate; ≈0.2 s per step for |𝒫| = 324.

The threshold-variance criterion (the previous review's proposal) is (2) with squared boundary-location loss, R_n = Σ_u Var[τ(z_u)] = c⁻² Σ_u v(u). Averaging the two variance rows of (7) with weights Φ(t), 1−Φ(t) gives Φ(t)r₁(r₁+t) + (1−Φ(t))r₀(r₀−t) = φ(t)²/(Φ(t)(1−Φ(t))), hence

  A^{TV}_n(x) = [ φ(t)² / (Φ(t)(1−Φ(t)) (1+v_x)) ] · Σ_u C(u,x)².                                             (9)

It factorises into a local weight maximised at t = 0 (the current mean boundary) and a global leverage term. It is outcome-independent (as in any Gaussian-linear design), whereas (8) is not.

## 5. Reductions — when do (8) and (9) collapse to already-tested rankings?

(R1) If cross-covariances are negligible relative to own variance (C(u,x) ≈ 0 for u ≠ x), (8) reduces to the local expected risk reduction at x itself, min(π,1−π) − E[min(π',1−π')], a monotone function of |t| → probability margin. (9) reduces to φ(t)²v_x²/(Φ(1−Φ)(1+v_x)) → margin when v_x is constant.

(R2) If v(u) is constant across the pool and the kernel is isotropic in the 4-D standardised space, Σ_u C(u,x)² is a kernel-density estimate at x, and (9) ≈ margin-weight × local pool density; (8) ≈ margin × (number of uncertain neighbours). This is the regime the repulsion audit (1.16) already probed with a distance penalty; the sign of the density effect is opposite to repulsion's (SUR *prefers* dense uncertain neighbourhoods; repulsion avoids queried neighbourhoods) — the two are not the same ranking, but neither is guaranteed to beat margin.

(R3) Under M3 (capped residual amplitude, two of four length scales at their upper bound, latent variance ≈ 0.85 for all candidates, |m| ≫ √v), C(u,x) is a near-1-D function of ΔVX with amplitude ≤ 1 while |m| is O(10): (7) moves no reference point across zero except the candidate itself, so (8) → margin and (9) → margin × (density along VX). This is the proof-by-mechanism of RESEARCH_DIAGNOSIS §5, consistent with all committed ranking correlations (0.977–0.999).

(R4) Under T with frozen s_u = 0.41 log-h units and c = 7, c²s_u² ≈ 8.2 is comparable to |m|² for band candidates at B16–B32; τ's posterior variance differs by a factor 3–10 between well-sampled and unsampled VX regions in development fits. Both (8) and (9) then rank differently from T-margin: development Spearman, top-1 and top-5 statistics are reported in OLD_DATA_RND_REPORT.md. The necessary condition for a non-redundant acquisition (ρ < 0.98) is satisfied by construction only in this regime.

(R5) Exact-fixed p(1−p) SUR (1.18B) vs (8): they differ by the choice q = p vs π and by the model; under T, q = p adds the term E[Φ(g)(1−Φ(g))] that rewards pushing means to the extremes; the two are computed and compared in development (`acq_global_sur_p` vs `acq_global_sur_pi`).

## 6. Reference set and the finite-pool objective

Let R be the whole outer training pool. Queried rows have m(u) = ±large and v → small so min(π,1−π) ≈ 0 and their contribution to (8) is O(10⁻⁶); including them keeps R fixed across the trajectory, so A_n values at different steps are comparable and no candidate-removal artefact enters. The held-out fold is never in R. The candidate set is 𝒫 \ D_n. No provisional labels are ever assigned (contrast 1.19B).

## 7. The auxiliary-output model tested and killed: censored-depth level set (CDL)

Latent y*(u) = log of the *conduction-side* maximum melt depth as a GP with linear mean in (ℓ, log VX, log LS, ST) plus ARD Matérn-3/2, Gaussian noise; observation: if Y = 0, log D observed; if Y = 1, y* ≥ log D* (right-censored at the depth separator D*, soft probit scale). Regime posterior π(u) = P(y*(u) ≥ log D*). This is a Tobit GP (Groot & Lucas 2012; Gammelli et al. 2022) whose level set is the boundary; it is *not* the Week 7 global depth regressor (no fit through the depth jump or the 300 µm floor). Development facts: conduction-side log depth is nearly linear in the log coordinates (R² 0.914, residual sd 0.096) so each C query carries a continuous measurement of ℓ − τ(z) with sd ≈ 0.14 log-h units — in principle far more than one bit. Full-information ceiling with all 324 depths: q20 0.853 (D* = 95–105 µm) vs M3 0.868 on the same folds; the extrapolated level set of the C-side surface does not coincide with the manual boundary better than M3 does (the depth response accelerates before the jump; D* is not context-free). Same-path early-budget results in OLD_DATA_RND_REPORT.md; the candidate is retained only if it beats T and M3 there.

## 8. What is and is not new here (mathematically)

Not new: (4)–(5) (Keeley et al. 2023; Chu–Ghahramani-type probit GPs); (7)–(8) (Letham et al. 2022 GlobalSUR; Bect et al. 2012 SUR; Menz et al. GPC random-set SUR); (9) (a targeted-IMSE/variance-reduction criterion; Picheny et al. 2010; the previous review's derivation); the Tobit GP.

Defensible as contributions if the development results hold: (i) the collapse-to-margin mechanism for physics-mean + capped-residual GPCs (R3) with its empirical confirmation on nine committed acquisitions; (ii) the ceiling decomposition (13 exception cases set the endpoint) and the resulting zero-headroom bound on late-window AULC contrasts, which explains a chain of published nulls quantitatively; (iii) the identification that the only feasible lever is an early-window, boundary-unit posterior, and a frozen, blinded, crossed model×acquisition test of it on an independently generated pool.

## 9. Exact results for deterministic simulators (added after the development replays)

The replays of §4 used the moment-matched look-ahead (7). The results in OLD_DATA_RND_REPORT §4 (T-SUR-π harmful, T-TV marginal) prompted a check of what a *coherent* one-step computation must satisfy. The following statements are exact; they do not depend on the kernel, the physics coordinate, or the Laplace approximation, only on the posterior being a probability law over the pool labelling.

**Setting.** Y_R ∈ {0,1}^R is the (unknown) labelling of a finite reference set R; the posterior law after D_n is P_n. For a candidate x ∈ 𝒫, write π_x = P_n(Y_x = 1), π_u = P_n(Y_u = 1), and π'_y(u) = P_n(Y_u = 1 | Y_x = y). Coherence means π_x π'_1(u) + (1−π_x) π'_0(u) = π_u (martingale property).

**Proposition 1 (information collapse for noiseless labels).** If x ∈ R, then I(Y_x ; Y_R | D_n) = H(Y_x | D_n) = H_b(π_x). *Proof.* Y_x is a coordinate of Y_R, so H(Y_x | Y_R, D_n) = 0. ∎
Consequences. For a deterministic simulator the joint information a query carries about the pool labelling is exactly its own binary entropy; the information-optimal one-step rule is π_x = ½, i.e. maximum-uncertainty sampling. BALD-type and joint-entropy set criteria cannot differ from margin; only *non-entropic* losses (0-1 risk on a reference set, boundary-location variance) can. Marginal-entropy sums (Letham's GlobalMI) are not information measures and fall under the next proposition's logic rather than this one.

**Proposition 2 (leverage identity for the 0-1 set risk).** Let r_u(x) = min(π_u, 1−π_u) − Σ_y P_n(Y_x = y) min(π'_y(u), 1−π'_y(u)) be the one-step expected reduction of the Bayes 0-1 risk at u. Under coherence:
(i) r_u(x) = 0 unless the Bayes decision at u differs between the two outcomes ("u is flippable by x");
(ii) if u is flippable, 0 < r_u(x) ≤ min(π_x, 1−π_x, π_u, 1−π_u).
*Proof.* Write a = P(Y_u=1, Y_x=1), b = P(Y_u=1, Y_x=0), p = π_x, so π_u = a+b, π'_1 = a/p, π'_0 = b/(1−p), e_0 = min(a+b, 1−a−b), e_1 = min(a, p−a) + min(b, 1−p−b). Suppose w.l.o.g. a+b ≤ ½. If a ≤ p−a and b ≤ 1−p−b (no flip) then e_1 = a+b = e_0, proving (i). If a > p−a and b ≤ 1−p−b, then e_0 − e_1 = 2a − p, which is ≤ p (since a ≤ p) and ≤ 1−p (since a ≤ ½ − b ≤ ½), and ≤ e_0 trivially; the case b > 1−p−b is symmetric; both cannot hold since that would give e_0 − e_1 = 2(a+b) − 1 ≤ 0 while each term is positive. ∎
Consequences. (a) The exact finite-pool set-directed acquisition is A(x) = Σ_{u flippable by x} r_u(x) ≤ N_flip(x)·min(π_x, 1−π_x): **a set-directed rule can prefer a less uncertain candidate only through a larger number of decision-flippable reference points.** (b) When no reference decision can be flipped by any single query (the late regime of the old pool: 0.1 candidates with 0.2<p<0.8 at B80), every coherent one-step 0-1 set criterion is identically zero — an exact statement of saturation. (c) The moment-matched update (7) does **not** preserve coherence: π'_y = Φ(m'_y/√v'_y) changes through the variance shrinkage even when no decision flips, so eq. (8) credits candidates with risk reduction that a coherent posterior assigns zero. Numerically, on T states along margin paths, 57–204 of ≈300 candidates per state violate the bound N_flip·min(π_x,1−π_x) (`results/leverage_bound_check.csv`); this is the mechanism by which T-SUR-π chose out-of-band, p≈0.3 candidates with large variance shrinkage and lost 0.03 AULC. The same non-coherence affects any Laplace/EP hypothetical-refit SUR that scores by a smooth functional of the refitted probabilities (Phase 1.18B's p(1−p) objective is of this kind), which is a reason those objectives can change paths without improving decisions.

**Proposition 3 (coherent computation under a Gaussian latent).** If (g_u, g_x) | D_n is bivariate normal with means m, variances v and covariance c, then with t = m/√v, ρ = c/√(v_u v_x): P_n(Y_u=1, Y_x=1) = Φ₂(t_u, t_x; ρ) (a standard bivariate normal orthant probability), so π'_1(u) = Φ₂/Φ(t_x), π'_0(u) = (Φ(t_u) − Φ₂)/(1−Φ(t_x)), which is coherent by construction. Φ₂ is computed to machine precision with Owen's T-function (`xsur.py`, validated against `scipy.stats.multivariate_normal.cdf`, max error 2·10⁻¹⁶). This is Letham et al.'s Theorem 1 restricted to a pool; its numerical cost is O(|𝒫|·|R|) Owen-T evaluations per step, ≈0.5 s here. Reference points with current risk below 10⁻⁶ are skipped (exact to within Σ of their risks, by Prop. 2(ii)).

**Corollary (flip-weighted margin).** The exact set-directed acquisition is A_XSUR(x) = Σ_{u flippable} r_u(x). It is margin multiplied by an effective count of reference decisions the outcome would change, each weighted by ≤ 1. It is the unique one-step Bayes-optimal rule for the transductive 0-1 loss, and it is the acquisition tested as "T-XSUR" in OLD_DATA_RND_REPORT §7.

**Proposition 4 (endpoint headroom — conditional).** Let c⁺ = sup over admissible training subsets of the accuracy of the model class on the evaluation subset, and L_A(b) the accuracy of policy A at budget b. For any two policies A, B, AULC_{[a,b]}(A) − AULC_{[a,b]}(B) ≤ (b−a)⁻¹ ∫_a^b (c⁺ − L_B(t)) dt. *Proof.* L_A ≤ c⁺ pointwise. ∎ The 324-label accuracy c* = 0.8565 is **not** c⁺: the test-label oracle of OLD_DATA_RND_REPORT §7 reaches 0.93–0.94 with 8–24 selected labels, so c⁺ ≥ 0.94 and the early-window bound is ≥ 0.10, not 0.031. What c* does bound is the late window empirically: every label-free policy tested (margin, T-margin, TV, SUR, XSUR, Random at B160) is within 0.005 of c* by B60–80, and the oracle itself falls back to c*+0.02 once margin resumes. The zero-late-headroom statement is therefore an empirical regularity of label-free policies on this pool (predictions P3–P6 test it), not a theorem.

**Proposition 5 (exception identity for the q20 endpoint).** Let E be the set of population rows misclassified by the full-information classifier in every fold in which they are held out, and s_e the number of q20 evaluation slots row e occupies across the 100 folds. Then 1 − c* = Σ_e s_e / Σ_all s + (residual from rows misclassified in some but not all folds). On the old pool: 13 rows with error ≥ 0.5 occupy 14.1% of q20 slots; 1 − c* = 14.35%; the residual is 0.25%.
