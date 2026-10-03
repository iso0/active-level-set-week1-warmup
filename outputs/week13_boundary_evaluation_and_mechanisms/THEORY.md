# Week 13 — Elementary propositions for finite-pool active level-set estimation

All statements are elementary and exact; their value lies in explaining the thesis'
Weeks 8–12 observations, not in technical depth. Each is checked against
already-open data or the synthetic generator (see `theory_checks/` and `real_data/`).

Notation: a finite evaluation set S with hard predictions ŷ, majority class M, minority
class m, n_m minority and n_M majority cases, π = n_m/|S|. A *minority call* is ŷ_i = m.
C = #correct minority calls (ŷ_i = y_i = m), W = #wrong minority calls (ŷ_i = m, y_i = M).

---

## Proposition 1 — trivial-baseline identity for band accuracy

acc_S(ŷ) − acc_S(always-M) = (C − W)/|S|.

*Proof.* acc_S(ŷ)|S| = #{y = M, ŷ = M} + C and acc_S(M)|S| = #{y = M} = #{y = M, ŷ = M} + W. ∎

**Corollary 1a.** ŷ beats the trivial predictor on S iff the precision of its minority calls
C/(C+W) exceeds 1/2 — *independently of π*. For two predictors (e.g. two acquisition
policies at the same budget), Δacc = (ΔC − ΔW)/|S|.

*Real data (NEW-136, q20):* every Week 12 protocol has mean minority-call precision below
1/2 over B16–B80 (e.g. margin16: C = 2.34, W = 2.79), which is exactly why none exceeds
always-Keyhole (`real_data/new_al_mean_aulc_by_arm.csv`). On OLD (Week 8.5) margin has C = 4.62,
W = 1.18 and exceeds the trivial value (0.611) by a wide margin.

## Proposition 2 — metric-disagreement window

Let predictor 1 make more minority calls than predictor 2 (ΔC + ΔW > 0) and let
ρ = ΔC/(ΔC + ΔW) be the marginal precision of the extra calls. Then

- Δacc > 0  ⇔ ρ > 1/2,
- ΔBA  > 0  ⇔ ρ > π   (BA = balanced accuracy on S).

*Proof.* The first is Prop. 1. BA = ½[C/n_m + 1 − W/n_M], so ΔBA = ½[ΔC/n_m − ΔW/n_M] > 0
⇔ ΔC n_M > ΔW n_m ⇔ ρ/(1−ρ) > n_m/n_M ⇔ ρ > π. ∎

Accuracy and balanced accuracy therefore rank two predictors oppositely exactly when
ρ ∈ (π, ½). The window is empty for balanced S and widens as imbalance grows.

*Real data:* margin16 minus random16 on NEW-136, B16–B80 means. Full pool: π = 0.088,
ρ = 0.279 ∈ (π, ½) ⇒ accuracy favours random (−0.0036) while BA favours margin (+0.0098).
q20: π = 0.315, ρ = 0.298 < π ⇒ both favour random (Δacc −0.0111, ΔBA −0.0011). This is the
whole explanation of the "random looks competitive" observation: margin buys extra rare-class
hits at a marginal precision of ≈0.28–0.30, which balanced metrics reward and band accuracy
punishes.

## Remark 3 — nearest-opposite hubness of the q-band

The historical q20 band ranks test cases by the distance to their nearest opposite-label case.
Under imbalance, many majority cases share the same few minority neighbours. On NEW-136 each
non-Keyhole case is the nearest opposite of 10.3 Keyhole cases on average (max 47); on OLD-405
each Keyhole case is that of 4.5 non-Keyhole cases, and 47/73 are never selected. The q20 band
is thus a majority-weighted tube (majority share 0.685 NEW vs 0.611 OLD), and accuracy on it
inherits Prop. 1. Pair-based (cut-edge) metrics count each opposite-label adjacency once and
have a constant-predictor value that does not depend on π (BER = BEF1 = 0, BEBA = 1/2).

## Proposition 4 — geometric discovery certificate

Let U be a finite pool, S_b ⊂ U a design, h_b = max_{u∈U} min_{s∈S_b}|u − s| its fill distance
and, for a minority pool case x, ρ(x) = min_{u∈U, y_u = M}|x − u|. If h_b < ρ* = max_x ρ(x), then
S_b contains a minority case.

*Proof.* Take x attaining ρ*. Some s ∈ S_b has |s − x| ≤ h_b < ρ(x), so s is not a majority
case. ∎

For farthest-point (maximin) traversal, h_b ≤ 2 h*_b where h*_b is the optimal b-point covering
radius (Gonzalez 1985). If the pool behaves like a sample of a d-dimensional region,
h*_b ≍ b^{−1/d}, so the certified discovery budget scales like (ρ*)^{−d}: geometric discovery of
small rare islands suffers from dimension.

*Real data* (`theory_checks/`): the certificate is never violated (100/100 NEW pools). OLD
pools: median ρ* = 2.45 > median h_16 = 1.91, so discovery is *certified* by B16 in 100/100
OLD pools (observed maximin discovery ≤ 6). NEW pools: median ρ* = 1.38 < median h_16 = 1.83;
the certificate arrives only at median B28 and holds by B16 in 1/100. The fitted log–log slope
of h_b is −0.49 (effective d ≈ 2). This is a structural explanation of why the frozen B16 rule,
safe on OLD, could fail on NEW (3/100 failures; the Week 11 STOP).

## Proposition 5 — score-ordered discovery (dimension-free)

After k seed queries showing only majority, query the remaining pool in a fixed score order.
The extra cost until the first minority label is 1 + #{majority ranked before the best-ranked
minority} ≤ 1 + n_M^rem (1 − AUC), AUC of the score for minority on the remaining pool.

*Proof.* The best-ranked minority is preceded by at most as many majority cases as an average
minority case, and the average count equals n_M^rem (1 − AUC). ∎

The bound is dimension-free but loose here (mean 23.4 versus observed 9.0 for the adaptive
log-h rule on the 7 NEW pools that needed it). It formalises why a physics *ordering* is
valuable for discovery even when the physics *level* is wrong.

## Proposition 6 — uniform discovery

Under uniform sampling without replacement, P(one class after b) = [C(n0,b) + C(n1,b)]/C(N,b),
and E[T_both] = Σ_{b≥0} P(one class after b); in particular E[first minority] = (N+1)/(K+1)
for K minority cases. NEW pools: analytic mean 10.6 versus the Week 12 empirical 11.3 (with an
8-query minimum); OLD pools: 5.7.

## Proposition 7 — anchoring bound for fixed-mean logistic Laplace GPC

For a logistic Laplace GPC with fixed latent mean m and kernel k, the predictive latent mean is
μ(x) = m(x) + Σ_i k(x, x_i)(y_i − π̂_i) with |y_i − π̂_i| < 1. Hence ŷ(x) = 0 requires

m(x) < Σ_{i: y_i = 0} k(x, x_i) = σ² S_0(x),

where σ² is the kernel amplitude and S_0(x) the correlation-weighted count of labelled class-0
neighbours. A capped amplitude (M3: σ² ≤ 1) therefore makes every point with m(x) ≥ S_0(x)
*certifiably unreachable* for the minority prediction, whatever the data.

*Real data:* never violated; on NEW-only full-pool M3 fits the bound certifies 46 of the 188
rare-case misses (24%). For OLD→NEW the bound is not binding (S_0 is large because the OLD
discrepancy is effectively one-dimensional in VX); the transfer failure there is due to
*cancellation* by correlated Keyhole residuals, not the bound. The proposition is a partial,
not complete, mechanism.

## Remark 8 — finite-pool exhaustion

Two policies at budget b on a pool of n share at least 2b − n labels. More importantly, once a
policy has labelled all K minority pool cases, every further query is a majority case for every
policy. On NEW, margin has labelled 8.5 of ≈9.5 pool rare cases by B40 (random: 4.1), so most of
the B16–B80 AULC window is measured after the rare-class information is exhausted.
