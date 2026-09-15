# Method theory note — why boundary-conditioned coverage can help M3, and when it cannot

Phase 1.23, Part B. Audience: a Mathematics MSc reader. Everything is labelled:

- **[A] exact**: proved here (or a standard identity), under the stated model.
- **[A-cited]**: a published theorem, not ours.
- **[B] proposition under explicit simplifying assumptions**: the assumptions are part of the statement.
- **[C] empirical hypothesis**: supported by our diagnostics, not proved.

Numerical checks referenced below are in `theory_toy_checks.json` (separate toy data, not the SPH population and not the pre-registered benchmark).

---

## 1. Setting

**Pool and labels.** A finite pool $\mathcal X=\{x_1,\dots,x_N\}\subset\mathbb R^d$ ($d=4$), noise-free binary labels $y(x)\in\{0,1\}$, a known scalar *physics coordinate* $h:\mathbb R^d\to\mathbb R$ (for SPH, $\log h$ of the normalised enthalpy). We write $x=(h, z)$ loosely, with $z$ the coordinates orthogonal to $h$.

**Truth model (boundary fragment).** The simplest model of a *nearly-correct* physics coordinate is a boundary that is a graph over $z$:

$$ y(x)=\mathbf 1\{h(x) > t + g(z)\}, \qquad g \text{ small and smooth}. \tag{1}$$

$g\equiv 0$ is a pure threshold in $h$ (family F7). The user's form $f(x)=G(h(x))+\delta(x)$ with $G$ monotone reduces to (1) locally, with $g(z)\approx -\delta/G'$ whenever $\delta$ does not depend on $h$.

**M3 (as frozen).** Latent mean

$$ \mu(x)= \underbrace{w\,(h(x)-\hat t)}_{\text{physics logistic}} + r(x), \qquad \hat t=-\beta_0/w,$$

where $(\beta_0,w)$ come from an $L_2$-penalised logistic regression of the queried labels on standardised $h$ with $C=10^6$, and $r$ is the posterior mean of a zero-mean GP discrepancy with kernel $\sigma^2\,\text{Matérn}_{3/2}(\text{ARD})$ on standardised $x$, fitted by Laplace's method with the physics latent as a fixed mean, $\sigma^2\in[0.0025,1]$. With latent variance $v(x)$, the class probability is $p(x)=\mathbb E\,\sigma(F)$ with $F\sim N(\mu(x),v(x))$. M3 computes this expectation by an erf-mixture approximation.

**Plain margin** queries $\arg\min_x |p(x)-\tfrac12|$.

**The frozen rule** (`coverage_then_margin_B40`). While the budget is below 40, it restricts candidates to the *label-estimated band*

$$ B=\big[\min(k,c)-\text{pad},\ \max(k,c)+\text{pad}\big],\quad k=\min_{y=1} h,\ c=\max_{y=0} h,\quad \text{pad}=\max(0.05,\,0.25\,|k-c|),$$

and inside $B$ maximises $\operatorname{rank}(1-2|p-\tfrac12|)+\operatorname{rank}(\text{distance to nearest queried point in standardised }x)$. From B40 it is plain margin. While the queried labels are *separable in h* ($c<k$), $B$ is the gap $(c,k)$ widened by 25% of its width on each side.

---

## 2. Exact results [A]

### Lemma A1 (what margin ranks)
Let $p(\mu,v)=\mathbb E\,\sigma(\mu+\sqrt v Z)$, $Z\sim N(0,1)$. Then $|p-\tfrac12|$ is strictly increasing in $|\mu|$ for fixed $v$, and strictly decreasing in $v$ for fixed $\mu\neq0$.

*Proof.* Symmetry of $\sigma$ and of $Z$ gives $p(-\mu,v)=1-p(\mu,v)$, so $|p-\tfrac12| = p(|\mu|,v)-\tfrac12$. Also $\partial_\mu p=\mathbb E\,\sigma'(F)>0$. For the variance, the heat-equation identity $\partial_v\,\mathbb E\,\phi(\mu+\sqrt vZ)=\tfrac12\mathbb E\,\phi''(\mu+\sqrt vZ)$ with $\phi=\sigma$ gives $\partial_v p=\tfrac12\mathbb E\,\sigma''(F)$. Here $\sigma''=\sigma(1-\sigma)(1-2\sigma)$ is odd and negative on $(0,\infty)$. For $\mu>0$,
$$\mathbb E\,\sigma''(F)=\int_0^\infty \sigma''(f)\,[\varphi_v(f-\mu)-\varphi_v(f+\mu)]\,df<0,$$
because $\varphi_v(f-\mu)>\varphi_v(f+\mu)$ for $f,\mu>0$. $\square$

So margin prefers small $|\mu|$ and large $v$. It is not variance-blind. Checked numerically on a grid of $(\mu,v)$ (both monotonicities hold). The lemma is for the exact expectation; M3's erf approximation was only checked numerically.

**Corollary A1′ (the variance cannot rescue a steep mean).** Under the probit approximation $p\approx\Phi(\mu/\sqrt{8/\pi+v})$, margin ranks candidates by $|\mu|/\sqrt{1+\pi v/8}$. Because M3 bounds $v\le\sigma^2\le 1$, the variance factor lies in $[1,\ 1.18]$. At most it rescales a candidate's score by 18%.

### Lemma A2 (the steep logistic on label-separable data)
Let the queried labels be separable in $h$: every $y=0$ point has $h\le a$ and every $y=1$ point has $h\ge b$, with gap $g=b-a>0$, $n_a$ points at $a$ and $n_b$ points at $b$. For the latent $w(h-\theta)$ with fixed slope $w$, the log-loss minimiser satisfies, as $w\to\infty$,
$$\theta^*(w)=\frac{a+b}{2}+\frac{\ln(n_a/n_b)}{2w}+o(1/w).$$

*Proof sketch.* For $\theta\in(a,b)$ the loss is $n_a e^{-w(\theta-a)}+n_b e^{-w(b-\theta)}$ plus terms of strictly smaller exponential order. Setting the $\theta$-derivative of the leading terms to zero gives $n_a e^{-w(\theta-a)}=n_b e^{-w(b-\theta)}$, which rearranges to the formula. $\square$

With the slope penalty $w^2/(2C)$, the leading loss at $\theta^*$ is $2\sqrt{n_an_b}\,e^{-wg/2}$. The optimal slope therefore satisfies $wg\approx 2\ln\!\big(Cg\sqrt{n_an_b}/w\big)$, which grows logarithmically in $C$. For $C=10^6$ the numerical check gives:
- fitted threshold offset from the gap midpoint: median 1.5% of the gap, 90th percentile 4.2%;
- logit change across the gap: median 10.3;
- predicted probability at the gap edges: about 0.006.

So in the separable regime the physics mean is a near-step located at the gap midpoint.

### Lemma A3 (queries inside the gap preserve separability)
If the labels are separable with gap $(a,b)$ and the next query $x$ has $h(x)\in(a,b)$, the enlarged labelled set is separable whatever the label: it becomes the new $a$ (if $y=0$) or the new $b$ (if $y=1$). $\square$

**Consequence.** A policy that always queries inside the current gap never breaks separability until the pool has no candidate left inside the gap.

### Lemma A4 (the discrepancy is switched off while the mean fits)
For the fixed-mean Laplace GPC, the posterior-mean discrepancy at any $x$ is $r(x)=k(x,X)^\top(y-\hat\pi)$ (GPML eq. 3.21 with a fixed mean), where $\hat\pi_i$ are the fitted probabilities at the queried points. Hence
$$|r(x)|\le \sigma^2\sum_i|y_i-\hat\pi_i|.$$
Moreover, if $|r|\le R$ on a region, every M3 decision-boundary point there satisfies $|h(x)-\hat t|\le R/w$.

*Proof.* The first part is the identity plus $|k|\le\sigma^2$. For the second, $\mu(x)=0$ gives $w|h-\hat t|=|r(x)|\le R$. $\square$

**Reading.** In the separable regime, A2 makes the physics mean fit every queried label up to about $\sigma(-wg/2)\approx 0.006$ at the gap edges, and far less elsewhere. A4 then forces $r\approx0$, and the M3 boundary sits in a slab of half-width $R/w\approx Rg/10$ around the physics threshold. **While labels are separable, M3 is effectively a one-dimensional threshold classifier in $h$**, whatever the true boundary looks like along $z$. This is the precise form of "the strong prior collapses the model onto a slab".

### Lemma A5 (pure threshold: bisection is optimal)
If $g\equiv0$ in (1), the labels of all pool points are determined by the rank of $t$ among the $N_{\text{gap}}$ pool values of $h$ inside the gap. Any policy needs $\lceil\log_2(N_{\text{gap}}+1)\rceil$ queries in the worst case, and binary search achieves this. $\square$

### Theorem A6 [A-cited] (Castro & Nowak, IEEE Trans. Inf. Theory 2008)
For boundary-fragment classes in $[0,1]^d$ (boundary = graph of an $\alpha$-Hölder function of the first $d-1$ coordinates, noise exponent $\kappa$), the minimax excess risk is:
- active learning: $n^{-\kappa/(2\kappa+\rho-2)}$;
- passive learning: $n^{-\kappa/(2\kappa+\rho-1)}$;

with $\rho=(d-1)/\alpha$. The active rate is attained, up to a log factor, by an algorithm that:
1. places a grid of lines over the first $d-1$ coordinates;
2. runs a 1D probabilistic bisection (Burnashev–Zigangirov) search along the remaining coordinate on each line;
3. interpolates the line estimates piecewise-polynomially.

**Relevance.** For model (1), the optimal active design is *spread over $z$, bisect along $h$*. Our rule is a heuristic, pool-based, label-adaptive approximation of this structure, not a new principle.

---

## 3. Propositions under explicit assumptions [B]

### Proposition B1 (slab concentration of margin)
**Assumptions.**
- The probit approximation of Corollary A1′ holds.
- $|r|\le R$ on the pool.
- $v\le 1$ (true for M3).
- $\delta^\circ=\min_{\text{candidates}}|h-\hat t|$.

**Statement.** The margin choice $x^*$ satisfies
$$|h(x^*)-\hat t|\ \le\ 1.18\,\delta^\circ+2.18\,R/w .$$

*Derivation.* $|\mu(x^*)|/1.18\le |\mu(x^*)|/\sqrt{1+\pi v^*/8}\le |\mu(x^\circ)|\le w\delta^\circ+R$, and $|\mu(x^*)|\ge w|h(x^*)-\hat t|-R$. $\square$

In the separable regime ($w\approx 10/g$, $R$ small by A4), the chosen point lies within a slab of order $\delta^\circ+0.2Rg$ around the gap midpoint. Toy check (4D M3, 1D truth, 60 separable states): the margin choice was the 2nd-closest candidate to the midpoint in $h$ at the median, within the closest 4 in 90% of states, and never beyond rank 14 of 384. **Under a steep physics mean, margin behaves as bisection in $h$ and uses $z$ only as a tie-breaker.**

### Proposition B2 (what the separable phase can and cannot learn)
**Model.**
- The truth is (1) with $z$ split into $K$ cells of equal pool mass.
- $g=g_k$ is constant on cell $k$; write $c_k=t+g_k$.
- Queries of the separable phase are inside the gap (A3), with $z$ independent of the cell (B1: $z$ only breaks ties).

**Statements.**
- (i) A query at level $h$ in cell $k$ returns one bit, $\mathbf 1\{h>c_k\}$. A second query in the same cell at a level on the same side of $c_k$ carries no information.
- (ii) After $m$ such queries, the expected number of distinct cells visited is $K\big(1-(1-1/K)^m\big)$, against $\min(m,K)$ for a covering rule. For $K=16$: 6.4 vs 8 after 8 queries, 10.3 vs 16 after 16. For $K=27$: 12.2 vs 16 after 16, 16.1 vs 24 after 24.
- (iii) A query at level $h<a$ in cell $k$ breaks separability iff $c_k<h$. A query at $h>b$ breaks it iff $c_k>h$. A gap policy never breaks it (A3). A band policy's pad queries break it with probability equal to the share of cells whose boundary lies beyond the queried level.
- (iv) If $g\equiv0$, pad queries never break separability and their labels are implied by the current data: they are wasted.

*Proof.* (i), (iii) and (iv) are direct from (1) and noise-free labels. (ii) is the coupon-collector expectation. $\square$

### Proposition B3 (why breaking separability is the lever)
Combine A2–A4. While labels are separable, $w$ is huge and the discrepancy is inert, so M3 cannot represent $g$. Once some pair of queried labels contradicts every threshold in $h$:
- the logistic MLE exists and $w$ drops to a finite value, of order (logit scale)/(width of the overlap region);
- the slab half-width $R/w$ in A4 becomes comparable to the band;
- the misfits $y_i-\hat\pi_i$ are no longer tiny, so $r$ can learn $g$.

Therefore, *under model (1) with $g\not\equiv0$*, a policy that produces a contradicting pair earlier lets M3 start learning $g$ earlier. By B2(iii), band coverage produces such pairs through its pad and its spread along $z$; plain margin, by A3, does not until the gap runs out of candidates.

This is a mechanism, not an optimality statement. Nothing here says the frozen score, the 25% pad or the B40 switch are good choices.

### Proposition B4 (why the benefit should fade)
*Assumption:* after the discrepancy has been learned (small $v$ along the band, $\hat g\approx g$), M3's $\mu$ depends on $z$ through $r$. Margin then queries where $|h-\hat t-\hat g(z)|$ is small, which is local bisection along $h$ at each $z$ (the Castro–Nowak structure). Continuing to reward distance would pull queries away from where $\hat g$ is still wrong. Semi-formal: coverage is useful for **finding** the heterogeneity, margin for **refining** it. The switch at B40 is an SPH-tuned choice with no theoretical justification.

### Proposition B5 (predicted failure modes)
- **Pure threshold ($g\equiv0$, F7).** By A5 and B2(iv), coverage cannot beat bisection. A uniform-in-gap query shrinks the gap by an expected factor $\mathbb E\max(U,1-U)=3/4$, against 1/2 for bisection, and pad queries shrink it by 0. **Prediction:** equivalent or slightly worse, concentrated early.
- **Physics coordinate wrong (F6).** The label-estimated band spans most of the $h$ range, so the rule degenerates to global uncertainty + diversity. The mechanism of B3 does not apply. **No prediction** against margin.
- **Exceptions away from the band (F5).** The band excludes them before B40, so nothing is gained. **Prediction:** equivalent.
- **Heterogeneity finer than the budget ($K\gg$ budget).** Neither policy resolves $g$, and differences shrink. Coarse, strong heterogeneity is where coverage should help.
- **Label noise.** A3 fails (noise creates contradictions at random), so the mechanism changes. **Not tested.**

---

## 4. Empirical hypotheses from SPH diagnostics [C]

From Phase 1.21 (repeats 61–120, post-hoc, 300 outer CV runs per rule on the same 405 simulations):

| quantity | M3 margin | frozen coverage (A) | early8 + coverage (B) |
|---|---:|---:|---:|
| runs with queried labels still separable in log h, B16 | 50% | 50% | 9% |
| same, B20 | 38% | 27% | 1% |
| same, B24 | 8% | 3% | 1% |
| nearest-neighbour distance of queried points, B24 (standardised x) | 1.48 | 1.59 | 1.23 |
| q20 false positives per run, B16–40 | 1.19 | 1.08 | 0.99 |
| q20 false negatives per run, B16–40 | 1.82 | 1.80 | 1.77 |
| final 80-point set identical to margin's | — | 211 / 300 | — |

**C1.** On SPH, margin keeps the queried labels separable for several queries after B16, and coverage breaks separability sooner. This is consistent with A3, B2(iii) and B3.

**C2.** The early gain comes mostly from fewer false positives near the boundary, consistent with learning where the boundary sits lower than the global log-h threshold in some regions. Post-hoc, not tested.

**C3.** Coverage mostly changes the **order** of boundary queries, not the final set. That fits B4: once the heterogeneity has been found, margin reaches the same points.

---

## 5. Toy example (illustration only)

`figures/concept_margin_vs_boundary_coverage.png`:
- **Setup:** 400 uniform points in $[0,1]^2$, $h=x_1$, boundary $x_1=0.55+0.12\sin(2\pi x_2)$, 8-point maximin seed, and a 2D version of M3.
- **Single seed:** margin's first active queries clump near one level of $h$ in one section of $x_2$; the coverage rule spreads early queries along the band.
- **Across 40 toy seeds, the difference is modest in 2D:**
  - median first budget with non-separable labels: margin B15, coverage B14;
  - share still separable at B24: 5% vs 0%;
  - distinct $x_2$ octants among the first 16 active queries: 7.2 vs 7.7 of 8.

This is what B2(ii) predicts. With only $K=8$ sections, uniform sampling already covers almost everything within 16 queries. The covering advantage grows with $K$, which in 4D grows as $(1/\ell)^{d-1}$. **The toy should not be shown as evidence that coverage wins.** It shows *where* the two rules query.

---

## 6. What the theory does not establish

- No rate or guarantee for the frozen rule. It is not the Castro–Nowak algorithm; it only shares its spread-over-$z$ / bisect-along-$h$ structure.
- No derivation of pad 0.25, pad floor 0.05 (absolute and scale-dependent), equal rank weights or the B40 switch.
- No statement about noisy labels, heteroscedastic simulators, or batch acquisition.
- Nothing about why early8 helps beyond the obvious: more of the budget is spent actively before B16, and the seed is less likely to leave both classes unobserved.
- B1–B3 rely on the fragment model (1) and on $|r|$ being small in the separable phase. Whether real SPH boundaries follow (1) is itself only suggested (C1–C3).

## 7. Predictions carried into the pre-registered stress test

`PHASE1_23_SYNTHETIC_PROTOCOL.json`, `predictions_from_theory_note` (frozen before any synthetic trajectory):
- P1: no help for the pure threshold (A5, B5).
- P2: no material help for tiny $g$.
- P3: help for $a\ge0.3$, growing with amplitude and with heterogeneity dimension.
- P4: fading after B40 (B4).
- P5 and P6: no systematic help for a wrong $h$ or for off-band islands.
- P8: value of the band over global diversity.
- P9: the early-start effect is partly initial design.
- P10: straddle ≈ margin under a steep mean.
