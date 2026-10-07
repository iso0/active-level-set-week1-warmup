# Round 3: geometric Bayes risk, discovery, and structural assumptions

5 October 2026. Research note for the parent agent. Repository strictly read-only; no repository module was imported or executed. Results below are mathematical constructions and a bounded primary-source audit, not new empirical acquisition evidence. **PROVED** means a proof is supplied here, not a priority claim. **PRIOR ART/KNOWN** explicitly disclaims novelty. Numeric empirical statements are **NUMERICALLY CHECKED** only where read from existing machine-readable artifacts; no new acquisition run was made.

## 1. What the repository actually establishes

**NUMERICALLY CHECKED (existing artifacts, descriptive).** `outputs/week12_startup_and_transfer_development/COMPREHENSIVE_REPORT.md` gives mean paid startup 8.07 for adaptive physics8 versus 8.47 for maximin8; their q20 AULC difference is -0.000313. `outputs/week16_theory_meets_data/discovery/observed_vs_exact_discovery.csv` gives raw both-class discovery means 4.43, 4.83 and 11.32 for adaptive physics, maximin and uniform random, respectively. The exact pool-wise uniform mean is 10.6355078621115. These are different quantities: minimum-eight release time is not raw first-both time.

**KNOWN (source report, not independently replayed).** Week16 reports that the two startup arms have identical B16 query sets in 94/100 pools and identical predictions there. In six differing pools, adaptive has better B16 but worse B40 log loss. This is descriptive evidence on already-open NEW-136. It does not show a general theorem that startup speed is irrelevant.

**PROVED distinction / report wording caveat.** The enriched-subset theorem in Round2 concerns a uniform random order *within a fixed subset*. Week12 adaptive physics chooses the deterministic lowest remaining log h after conditioning on a failed B8 history. Unconditional enrichment of low-score subsets does not by itself establish the conditional success probability of that adaptive query. Week16's phrase that the adaptive benefit is “exactly” the enrichment theorem's mechanism is stronger than what that theorem proves. The actual deterministic rank and selected-history results remain valid descriptive observations.

## 2. A loss must specify its target measure and action space

Let D be current data, G a random boundary or random set, and a an admissible estimate. For any integrable nonnegative loss L(a,G), define

    R(D) = inf_a E[L(a,G) | D],
    Delta(j | D) = R(D) - E[R(D,O_j) | D].

**PROVED / KNOWN (Bayesian decision theory and SUR).** Delta is nonnegative under coherent conditioning and a fixed action space. Proof: retain a current Bayes action a_D after every outcome. Then R(D,O_j) <= E[L(a_D,G)|D,O_j]. Averaging and applying the tower identity gives E R(D,O_j) <= R(D). Approximate minimizers establish the same result when an infimum is not attained. Nonnegative one-step *expected* value neither guarantees improvement for each outcome nor an optimal multistep policy. A fantasy refit that changes the law or uses incompatible outcome weights need not satisfy this proof.

There are genuinely distinct objectives:

* volume symmetric difference of two decision regions;
* integrated vertical displacement of graph boundaries;
* mean nearest-surface distance with surface-area weighting;
* Hausdorff distance (a worst-location discrepancy);
* surface-area error or normalized surface Dice at a fixed tolerance.

Calling all these “boundary uncertainty” conceals different Bayes actions and acquisitions.

## 3. Graph boundaries give an exact, useful restricted model

Let U be a measurable subset of R^m, g,h:U -> [a,b], and A_g={(u,z): a <= z <= g(u)}. Domain side walls are not part of the boundary target; the target is Gamma_g={(u,g(u)):u in U}.

### G1. Exact volume identity and its density dependence

**PROVED / KNOWN.** For a nonnegative integrable density q(u,z),

    mu_q(A_g triangle A_h)
      = integral_U | integral_{g(u)}^{h(u)} q(u,z) dz | du.

For q(u,z)=w(u), this equals integral_U w(u)|g(u)-h(u)|du. If 0<c<=q<=C throughout the region between the graphs, it is between c ||g-h||_1 and C ||g-h||_1. Proof: at each u the symmetric difference is exactly the interval between g(u) and h(u); apply Tonelli. The density bounds follow pointwise.

Thus ordinary classification error approximates **density-weighted volume**, not uniform geometric error. The equality to unweighted integrated displacement needs a declared reference measure or density correction. A target density with zero mass in a region cannot detect boundary error there.

### G2. Bayes actions and exact graph-risk reductions

**PROVED / KNOWN.** Under loss L1(h,g)=integral w(u)|h(u)-g(u)|du and unrestricted measurable graph actions, a pointwise posterior median is a Bayes action. Under L2(h,g)=integral w(u)(h(u)-g(u))^2du, the posterior mean is a Bayes action. Proof: Tonelli separates the objective by u. For a scalar Z, the subgradient of E|a-Z| contains zero iff P(Z<=a)>=1/2 and P(Z>=a)>=1/2; completing the square proves the mean result. Measurable quantile choices give a measurable action. If every posterior graph is L-Lipschitz, its fixed lower-median quantile and mean are also L-Lipschitz: |g(u)-g(v)|<=L||u-v|| implies the corresponding quantile inequalities, and Jensen gives the mean bound. Arbitrary shape constraints can destroy this separability.

For squared displacement the exact value of any observation is

    Delta_2(j) = integral w(u) Var(E[g(u)|D,O_j] | D) du.

Proof: apply the conditional total-variance identity pointwise and integrate. For binary O_j in {-1,+1}, with |E O_j|<1,

    Delta_2(j) = integral w(u) Cov(g(u),O_j|D)^2 / Var(O_j|D) du.

Indeed every function of a binary variable is affine, so its conditional mean is exactly the linear regression on O_j. A deterministic observation has value zero. These are *cross-moments of boundary location and observation*, not just moments of binary labels at one arbitrarily selected height.

For L1 the exact value is the current integrated posterior absolute-deviation risk minus its outcome-weighted conditional version. It generally requires conditional CDFs/medians, not only two scalar moments. Equivalently, because G1 is a continuum of binary membership losses, it can be calculated from the joint law of O_j and every threshold event {g(u)>=z}. A finite collection of label-pair moments at one height per u does not determine these CDFs.

**PROVED restricted Gaussian illustration.** Suppose g itself has a Gaussian posterior with mean m(u), variance s(u)^2, and covariance c(u,v), and the paid observation directly reveals g(v), without noise. Then

    R_1 = sqrt(2/pi) integral w(u) s(u) du,
    Delta_1(v) = sqrt(2/pi) integral w(u)
          [s(u)-sqrt(s(u)^2-c(u,v)^2/s(v)^2)] du,
    Delta_2(v) = integral w(u)c(u,v)^2/s(v)^2 du.

Proof: the scalar Gaussian median equals its mean and its expected absolute centered value is sqrt(2/pi)s. Gaussian conditioning gives the displayed updated variance, which does not depend on the observed value. The squared-loss formula is the preceding variance identity. Take zero value when s(v)=0. The formula describes displacement of unrestricted Gaussian graphs; bounded-domain clipping changes it. It does **not** pretend that one binary SPH query directly returns a root g(v): locating that root can cost many binary evaluations. These formulas are a transparent restricted decision problem, not a proposed thesis method or a novelty claim.

### G3. Hausdorff equivalence under explicit Lipschitz conditions

**PROVED.** If g,h are L-Lipschitz on the same compact U, then

    ||g-h||_infty / sqrt(1+L^2)
      <= H(Gamma_g,Gamma_h) <= ||g-h||_infty.

Proof: the upper bound matches points with the same u. At u maximizing |g(u)-h(u)|=M, any point (v,h(v)) is at distance at least sqrt(r^2+(M-Lr)_+^2), r=||u-v||. Its minimum over r>=0 is M/sqrt(1+L^2). Compactness attains M; an approximating sequence gives the same argument without attainment. This is a graph-specific result; it does not identify integrated error with Hausdorff loss.

**PROVED explicit L1-to-uniform bound.** Let U=[0,1]^m, f=g-h be K-Lipschitz, |f|<=1, K>0, and w>=w_min>0. Let M=||f||_infty and r=min(1/2,M/(2K sqrt(m))). At a maximizer choose a one-sided coordinate box with side r inside U. Every point in the box is within sqrt(m)r and therefore |f|>=M/2. Thus

    integral w|f| >= w_min (M/2) r^m.

In the small-error regime M<=K sqrt(m), this yields

    M <= [2^(m+1) K^m m^(m/2) (integral w|f|)/w_min]^(1/(m+1)).

For K=0 the discrepancy is constant and the exact integral identity applies. The exponent 1/(m+1) is sharp in order: a K-Lipschitz cone of height M and radius M/K has L1 mass proportional to M^(m+1)/K^m. Hence classification-to-Hausdorff control requires a uniform smoothness modulus and positive coverage density, with dimension-dependent weakening.

### G4. Explicit finite approximation

**PROVED.** Let cells C_k partition U with diameter at most h, representatives u_k, and masses w_k=nu(C_k). If g,h have Lipschitz constants L_g,L_h and nu is a probability measure, then

    |integral |g-h|dnu - sum_k w_k |g(u_k)-h(u_k)||
       <= (L_g+L_h)h.

Proof: |g-h| has Lipschitz constant at most L_g+L_h; integrate its deviation from each representative. For a base-domain h-net, the sampled graph cloud approximates Gamma_g in Hausdorff distance by at most h sqrt(1+L_g^2); therefore the difference between the cloud-to-cloud and graph-to-graph Hausdorff distances is at most h[sqrt(1+L_g^2)+sqrt(1+L_h^2)]. This is a constructive continuous-to-finite bridge distinct from Round2's crossing-edge theorem. It requires graph heights, not merely finite labels with unknown between-point roots.

**COUNTEREXAMPLE.** With only labels, any unsampled interval can contain two different thresholds that agree at every observed pool point but have different boundary locations. In higher-dimensional domains, an arbitrarily narrow smooth bump between sample sites gives the same phenomenon. Smoothness without a uniform derivative bound is insufficient. An epsilon-net together with a specified uniform modulus limits these alternatives; an arbitrary finite pool does not.

## 4. Beyond graph coordinates: normal displacement and scale

### G5. Tubular geometry and density weighting

**PROVED under the following regularity assumptions.** Let S be a compact oriented C2 hypersurface with injective normal coordinates F(s,t)=s+t n(s) for |t|<r, and principal curvatures bounded by K. Let a<r, aK<1, and let another region differ only by moving each boundary point normally by delta(s), |delta|<=a, without added components or changed orientation. The symmetric difference is exactly the normal strip. For a Lipschitz density q with bound Q and Lipschitz constant L_q in the tube,

    mu_q(A triangle B)
      = integral_S | integral_0^{delta(s)} q(F(s,t)) J(s,t) dt | dA(s),
    J(s,t) = product_{i=1}^m (1-t kappa_i(s)).

The signs of curvatures depend on convention but not the bounds. The normal-coordinate change-of-variables proves the identity. Since

    |J-1| <= m K |t|(1+aK)^(m-1),
    |J| <= (1+aK)^m,

one obtains

    |mu_q(A triangle B) - integral_S q(s)|delta(s)|dA(s)|
       <= (C/2) integral_S delta(s)^2 dA(s),
    C=L_q(1+aK)^m + QmK(1+aK)^(m-1).

Proof of the product bound: telescope the product and bound all other factors by 1+aK. Integrate the resulting C|t| bound. Thus small-displacement classification error weights boundary area by local input density. A uniform geometric objective, a deployment-density objective and the empirical campaign distribution answer different questions.

### G6. Small latent variance is not small boundary-location uncertainty

**PROVED exact counterexample supplied by root, expanded here.** For f_c(x)=c(x-Theta), c>0, Theta~N(m,sigma^2), the random boundary is {Theta} for every c. At each x, sd(f_c(x))=c sigma ->0 as c->0, while boundary posterior sd remains sigma and squared boundary Bayes risk remains sigma^2. The normal derivative is c, so the scale-invariant ratio sd(f)/|partial_n f| equals sigma.

A deterministic sign query at x=m reveals sign(m-Theta), independently of c. Its reduction of squared boundary risk is 2 sigma^2/pi: the two posterior means are m +/- sigma sqrt(2/pi). If instead the model observation is sign(f_c(m)+eta), eta~N(0,tau^2) independent, the corresponding value is

    2 c^2 sigma^4 / [pi(c^2 sigma^2+tau^2)],

which tends to zero as c->0. Proof: for jointly Gaussian X=Theta-m and Z=-cX+eta, E[X|sign Z]=Cov(X,Z)/sd(Z) sqrt(2/pi) sign Z; apply total variance. This separates geometric uncertainty from an assumed fixed observation-noise channel. It does not deny Week16's channel-specific calculation.

**PROVED local approximation with assumptions.** If f and a perturbation f+e have a single corresponding root along a normal line, |partial_n f|>=a0>0 near the root, and first derivatives vary continuously, Taylor expansion/implicit-function differentiation gives delta approximately -e/partial_n f. More precisely, for f_t=f+t e and a differentiable root x(t), x'(0)=-e(x(0))/partial_n f(x(0)). The implicit function theorem supplies the local root and differentiability. A bound on e alone cannot give a uniform positional bound without a derivative lower bound and a no-extra-components condition. The quotient is unchanged under multiplication of f and e by a positive constant.

## 5. Geometric quantities that must remain separate

**COUNTEREXAMPLE (area).** On U=[0,1], let h=0 and g_k(u)=k^(-1) sin(k^2 u). Uniform displacement, Hausdorff distance and symmetric-difference area tend to zero, but graph length is at least integral_0^1 k|cos(k^2u)|du, which grows as (2/pi)k. Every graph is smooth; there is no common Lipschitz or curvature bound. Surface area is not determined by small volume error.

**COUNTEREXAMPLE (NSD).** Two parallel equal-area flat boundaries separated by d have normalized surface Dice at tolerance tau equal to one when d<=tau and zero when d>tau (under the usual within-tolerance convention). Meanwhile Hausdorff distance is d and graph volume error is area*d. NSD is a useful tolerance-based endpoint, but is neither a metric nor a continuously calibrated estimator of displacement. Its tolerance and physical-coordinate scaling must be fixed.

**PROVED comparison (directed average distance).** For L_h-Lipschitz h,

    |g(u)-h(u)|/sqrt(1+L_h^2)
      <= dist((u,g(u)),Gamma_h) <= |g(u)-h(u)|.

This is the G3 argument pointwise. Averaging on Gamma_g weights u by sqrt(1+||grad g(u)||^2) and divides by the surface area. Hence average surface distance is comparable to an appropriately area-weighted graph displacement under bounded slopes, but is not generally the same integral.

**COUNTEREXAMPLE / impossibility.** Arbitrary q20/Hamming success does not imply geometric success. Round2 already supplies an explicit q20 ranking reversal; do not relabel that result as new. Two further obstructions are (i) a region of zero target density, where boundaries can move without affecting classification loss, and (ii) narrow spikes, where volume can vanish while Hausdorff error stays fixed unless regularity is controlled. Conversely, a dense fixed regular grid with regularity and correct target weights permits G3/G4 bounds. The statement is conditional, not “classification can never inform geometry.”

## 6. Pairwise binary moments can be insufficient for geometric acquisition

### G7. An explicit Hausdorff one-step counterexample (not Round2's cut-Hamming example)

**COUNTEREXAMPLE / PROVED.** Use three separated columns with bases u_1,u_2,u_3 at pairwise distances at least 3. A boundary consists of one graph point (u_i,B_i) in each column, with B in {0,1}^3. Admissible estimates use heights h_i in [0,1]. Euclidean Hausdorff distance between these graph sets is exactly ||h-B||_infty: a point in another column is farther away than the point at the same base. This can also be viewed as three separate experimental strata. Query i at height 1/2 reveals B_i.

Define two posterior laws on the eight binary triples:

| B | P_plus(B) | P_minus(B) |
|---|---:|---:|
|000|34/70|22/70|
|001|0|12/70|
|010|0|12/70|
|011|12/70|0|
|100|0|12/70|
|101|12/70|0|
|110|12/70|0|
|111|0|12/70|

Both have P(B_i=1)=24/70 and P(B_i=B_j=1)=12/70 for all i!=j, so all first and pairwise binary moments agree. The difference is a pure parity perturbation; summing over any omitted bit cancels it.

**Lemma.** For any law P on {0,1}^m, allowing estimates h in [0,1]^m,

    inf_h E||h-B||_infty = min(1/2, 1-max_b P(B=b)).

Proof: the cube center has loss 1/2 in every world, and a most-probable vertex has expected loss 1-p_max. For any h, round it to a closest vertex v and put r=||h-v||_infty<=1/2. Every other vertex is at distance at least 1-r. Therefore expected loss is at least p_v r+(1-p_v)(1-r), whose minimum over r in [0,1/2] is min(1/2,1-p_v), at least min(1/2,1-p_max). This matches the two explicit actions.

Before querying, p_max<1/2 for both laws, so R=1/2=35/70. After observing B_1, the branch B_1=0 has mass 46/70 and the branch B_1=1 mass 24/70. Under P_plus the branch-zero MAP mass is 34/70, so its unnormalized Bayes risk is min(23/70,12/70)=12/70; branch-one risk is 12/70. Therefore R_after=24/70 and Delta_plus=11/70. Under P_minus the branch-zero MAP mass is 22/70<23/70, so its risk is 23/70; branch-one risk is 12/70. Therefore R_after=35/70 and Delta_minus=0.

Thus identical marginal and all pairwise label probabilities can coexist with a positive versus zero exact value of the same query for a genuine geometric Hausdorff loss. The difference persists with unrestricted intermediate graph heights, rather than being an artifact of forcing the output to be a posterior sample. In a general finite problem the full joint law is sufficient; this example establishes failure of pairwise sufficiency, not that every geometry problem requires all orders. A fully specified Gaussian *latent* law is of course determined by its own mean/covariance; that is different from knowing finitely many binary label-pair moments.

## 7. Optimal discovery can be arbitrarily bad for later geometry

### D1. Equal paid budget, optimal continuation, only half a query extra expected startup

**COUNTEREXAMPLE / PROVED.** Fix any k>=1 and M=k+1 independent fair bits Theta_1,...,Theta_M. The geometric target has M separated graph columns, heights H Theta_i, with bases separated by at least 3H. Candidate q_i is a noiseless membership query at height H/2 in column i and reveals Theta_i. Include two paid certification anchors a_0,a_1 with fixed labels 0 and 1. Both labels occur in every world. The operational startup rule requires actually observed labels of both classes, even for structurally reliable anchors.

Policy A queries the anchors first. It has T_both=2 surely, the smallest possible value of T_both for any policy. Give it optimal continuation and total paid budget Q=k+2. Only k of the M independent boundary bits can then be queried. At least one remains fair and independent, so its optimal final expected Hausdorff loss is H/2. Proof: a fair unknown column alone has minimum expected absolute error H/2; set every unresolved height to H/2 to attain global Hausdorff loss H/2. Even adaptive choices cannot infer an independent unqueried bit.

Policy B queries q_1,q_2. If their labels differ, both classes have already appeared at cost 2. If they agree, query the anchor with opposite label, completing startup at cost 3. Thus E T_both=2.5 and T_both<=3. Then query all remaining M-2=k-1 geometric bits. This costs at most 3+(k-1)=Q and identifies the whole boundary. If startup ended at 2, use or leave the extra available query; all paid comparisons can be padded to Q. Final geometric risk is zero.

Therefore a startup policy globally optimal for first-both discovery can have positive geometric risk after *any prescribed number k of optimally chosen refinement queries*, while a policy spending only 0.5 more queries on average for startup has zero risk at the same total budget. The ratio of residual risks is unbounded; scaling H makes the absolute difference arbitrarily large when the physical domain is not normalized. On a fixed unit-height domain the gap is 1/2 versus zero. This refutes a universal implication from discovery-time optimality to later geometric optimality. It does not show that deliberately slower startup is always preferable or that a particular thesis startup is poor.

The anchors are a formal way of implementing a paid two-class prerequisite. If an application allows a known structural anchor to substitute for a paid observation, that changes the startup decision problem. The counterexample explicitly retains the actual-observation contract that motivates the thesis's startup stage.

### D2. Discovery alone has no boundary-location guarantee

**PROVED implication of D1.** Any universal bound on later geometry that depends only on the distribution of T_both and total remaining budget, without restrictions on the information content of query histories, fails. In D1 the optimal T_both history learns no geometric bits; a slightly different startup learns two. The sufficient statistical object is the distribution of the posterior/state at release, not the release time alone.

The previous Round2 stopping-time information bound remains relevant but is not new here. D1 strengthens the basic same-time/different-information observation by giving equal final paid budgets, an optimal continuation for the fast-startup policy, an arbitrary refinement horizon, and an explicit geometric loss.

### D3. State coalescence bounds any later effect

**PROVED (root insight, expanded).** Couple two policies on the same truth and continuation seed. If by budget b their complete sufficient states coalesce with probability at least 1-delta, and the subsequent transition/prediction rule is identical, then their paths and predictions remain identical on that event. For any later endpoint Z in [a,a+L],

    |E Z_A-E Z_B| <= L delta.

Proof: the difference is zero on the coalescence event and has absolute value at most L elsewhere. For AULC with nonnegative normalized weights lambda_t, if delta_t bounds the probability of noncoalescence at budget t, the bound is L sum_t lambda_t delta_t. If only coalescence by b is known, use one for earlier budgets and delta for later budgets. Same query sets suffice only when the fitting and continuation states are order-invariant, share random seeds, and do not retain different history-dependent state.

Applied descriptively to 94/100 identical B16 states, the empirical average difference in any [0,1]-valued later endpoint is at most 0.06 **if** the common deterministic continuation truly coalesces. This bounds the maximum effect; it does not predict -0.000313 or show discovery is universally unimportant. Counts of identical query sets alone are not enough if optimizer state, query-order dependence or stochastic seeds differ.

## 8. Exact monotonicity, stochastic monotonicity and robust rank guarantees

### D4. What exact structural monotonicity permits

**PROVED / KNOWN.** For a binary deterministic monotone function on a partially ordered pool, an observed positive label permits inference of positive labels at every dominating point, and an observed negative label permits the analogous downward inference. On a totally ordered pool with one threshold, opposite anchors and noiseless comparisons permit binary search. These are logical consequences of the exact constraint, not consequences of a high AUC or a monotone marginal probability curve.

**COUNTEREXAMPLE (stochastic monotonicity).** Independent labels with probabilities p_1=0.49<=p_2=0.51 satisfy monotonicity of class probability but have P(Y_1=1,Y_2=0)=0.49^2=0.2401. Thus a positive observation at the first point does not certify the second label. Posterior mean monotonicity similarly does not establish monotonicity of every possible deterministic world.

### D5. One violation can break elimination; count what “one” means

**COUNTEREXAMPLE / PROVED.** On a chain of N points, truth (1,0,...,0,1) differs at only its first entry from the monotone threshold (0,...,0,1). Querying that single exceptional point and propagating its positive label upward incorrectly infers N-2 labels and can remove every unqueried negative from the search. The contamination fraction is 1/N yet the erroneous-elimination fraction approaches one. This example has N-2 violating *pairs*.

If “one violation” literally means exactly one reversed comparable pair, use (0,...,0,1,0,1,...,1) with adjacent 1,0. Propagating from that 1 already deletes the true 0. Zero-error guarantees fail from even one pair, but it would be false to attribute N-scale erroneous propagation to exactly one pair: each erroneous comparable propagation witnesses a violation pair. Always distinguish point contamination, pair inversion count, and stochastic observation noise.

### D6. Tight discovery bound from ranking errors, without hard propagation

**PROVED.** Rank N items from most to least promising for a designated rare class, with r>=1 rare items. Let V be the number of common-before-rare pairs (ranking inversions), with no ties, and D the first rare rank. Every one of the D-1 preceding common items lies ahead of all r rare items. Hence

    V >= r(D-1),
    D <= 1+floor(V/r)
      = 1+floor((1-AUC)(N-r)).

The bound is tight whenever V=kr: place k common items first, then all r rare items, then the remaining common items. Intermediate V can be generated by inversions later in the sequence without changing the first-hit rank, subject to available counts. For a top-M subset with s rare items,

    V >= (M-s)(r-s),

because each of its M-s common items precedes every one of the r-s rare items outside. In particular V<Mr guarantees a rare item in the first M. Proof is direct pair counting. With ties, choose a declared deterministic tie order and count its inversions; half-credit AUC alone does not determine its first-hit rank.

This is a robust rank-error guarantee for deterministic ordered discovery, unlike the uniform-in-tail law. It tolerates violations but does not certify labels. AUC near one can still permit a substantial startup delay when N-r is large. The full NEW descriptive AUC about 0.8569, if interpreted as a fixed rare-oriented ordering without ties, only yields a coarse bound around rank 18 for N-r=124; the observed first rare rank is much better. The exact empirical inversion count should be used before quoting an integer bound from rounded AUC.

**PROVED boundary limitation.** None of these rank inequalities controls the informativeness of found points about the geometry. D1 can place reliable class anchors at extreme score ranks while the independent boundary bits remain unobserved. Likewise, enriched tails may contain only easy interior positives, rather than locations that localize a boundary.

## 9. Primary-source priority audit

This is a bounded audit, not a claim to have exhaustively established novelty. Each source is summarized briefly; the proofs above are supplied directly rather than attributed to these papers without verification.

1. **PRIOR ART:** Bect, Ginsbourger, Li, Picheny and Vazquez, *Sequential design of computer experiments for the estimation of a probability of failure*, Statistics and Computing 22 (2012), 773–793. [Author preprint](https://arxiv.org/abs/1009.5177), [publisher](https://doi.org/10.1007/s11222-011-9241-4). Explicitly studies a deterministic expensive real-valued function under a GP epistemic prior, a known input measure, Bayesian decision theory, and SUR for excursion probability. The distinction between epistemic GP uncertainty and a stochastic physical oracle is already explicit. The real-valued observation contract differs from binary-label GPC acquisition. Bayes-risk reduction and “deterministic simulator plus GP” are not novel here.

2. **PRIOR ART:** Chevalier, Bect, Ginsbourger, Vazquez, Picheny and Richet, *Fast Parallel Kriging-Based Stepwise Uncertainty Reduction With Application to the Identification of an Excursion Set*, Technometrics 56 (2014), 455–465. [Publisher](https://doi.org/10.1080/00401706.2013.860918). Introduces efficient multipoint SUR criteria and closed-form computations for excursion-set identification. Any computational novelty claim for refit-free Gaussian excursion acquisition must compare against this literature, not only classifier active learning.

3. **PRIOR ART:** Bect, Bachoc and Ginsbourger, *A supermartingale approach to Gaussian process based sequential design of experiments*, Bernoulli 25 (2019), 2883–2919. [Author preprint](https://arxiv.org/abs/1608.01118), [DOI](https://doi.org/10.3150/18-BEJ1074). Develops uncertainty functionals, supermartingale reasoning, and consistency of SUR, including excursion-set objectives. Generic nonnegative expected risk reduction or posterior-risk supermartingale arguments should be classified as established decision theory/SUR, not as a new acquisition theorem.

4. **PRIOR ART:** Ranjan, Bingham and Michailidis, *Sequential Experiment Design for Contour Estimation From Complex Computer Codes*, Technometrics 50 (2008), 527–541. [Author PDF](https://acadiau.ca/~pranjan/research/Ranjan_Bingham_Michailidis.pdf), [publisher](https://doi.org/10.1198/004017008000000541). Designs expensive simulator trials for contour estimation using GP uncertainty and a contour-specific criterion. A generic proposal to “focus on contours instead of classification” is established prior art; a new loss/guarantee would need precise differentiation.

5. **PRIOR ART:** Azzimonti, Bect, Chevalier and Ginsbourger, *Quantifying uncertainties on excursion sets under a Gaussian random field prior*, SIAM/ASA Journal on Uncertainty Quantification (2016). [Author preprint](https://arxiv.org/abs/1501.03659), [publisher](https://doi.org/10.1137/141000749). Uses distance in measure and distance-transform-based excursion uncertainty, with conditional simulation/reconstruction. Geometry-aware posterior summaries beyond marginal probabilities are established; the specific finite Hausdorff parity counterexample above is not asserted to appear there.

6. **PRIOR ART:** Castro and Nowak, *Minimax Bounds for Active Learning*, COLT 2007. [Author PDF](https://nowak.ece.wisc.edu/COLT07.pdf), [publisher](https://doi.org/10.1007/978-3-540-72927-3_3). Uses boundary-fragment classes and explicit smoothness/noise/density conditions. The graph-boundary restriction and the need for positive density bounds are classical. Any minimax-rate claim should check the journal version and errata before reuse; this note imports no rate theorem.

7. **PRIOR ART:** Barile and Feelders, *Active Learning with Monotonicity Constraints*, SDM 2012, 756–767. [Publisher](https://doi.org/10.1137/1.9781611972825.65). Exploits monotonicity to infer labels of ordered objects and select queries. Hard monotone propagation itself is prior art; the assumptions for propagating deterministic labels must be distinguished from stochastic monotone probabilities. The exact degree of robustness in their algorithms was not inspected beyond the primary abstract, so no claim is made about their treatment of violations.

8. **PRIOR ART (adjacent, not a boundary theorem):** Sugiyama, *Active Learning in Approximately Linear Regression Based on Conditional Expectation of Generalization Error*, JMLR 7 (2006), 141–166. [Primary article](https://www.jmlr.org/papers/v7/sugiyama06a.html), [PDF](https://www.jmlr.org/papers/volume7/sugiyama06a/sugiyama06a.pdf). Explicitly treats active-design covariate shift and importance-weighted loss under misspecification. Importance weighting requires overlap and a target density; it does not itself supply a surface-distance or Hausdorff guarantee.

Conservative novelty position: the generic SUR principle, posterior median under L1, mean under L2, graph-boundary models, and the density issue are known. The explicit G7 parity/Hausdorff and D1 equal-paid-budget discovery constructions, D6 rank count, and their synthesis with Week12/16 may be useful exposition or propositions. No priority claim is established. No empirical method advantage follows.

## 10. Falsifiable experiment/check rows

These are bounded checks to preregister if used, not authorization to begin another acquisition search. Every useful proposition above has a statistic and a failure condition.

| Result | Design and exact statistic | Falsifier / required interpretation |
|---|---|---|
| G1 volume identity | Fixed graph pairs, exact/dense integral of q across vertical strips; report absolute difference from weighted graph displacement when q=w(u). | Nonvanishing discrepancy beyond quadrature error falsifies implementation or graph/measure assumptions; q varying with z requires the full strip integral. |
| G2 median/mean actions | Finite graph posterior; enumerate actions for L1 and L2 and compare risk to coordinate medians/means. | Lower admissible risk than claimed optimum falsifies derivation/implementation; constrained actions require a separate optimization. |
| G2 exact Gaussian values | Small Gaussian graph posterior; compare analytic Delta1/Delta2 with high-precision conditional integration under the same law. | Difference outside numerical tolerance; binary membership observations are a different experiment. |
| G3 L1-to-Hausdorff | Cone family with known K and w_min; report M, weighted L1, and ratio L1/M^(m+1). | Violation of explicit inequality under verified assumptions; if K grows or density vanishes the theorem is inapplicable. |
| G4 finite bridge | Refine an h-net for fixed Lipschitz graphs; report maximum integral/cloud-distance error divided by h. | Error exceeding declared constants; arbitrary unlabeled pool coverage is insufficient. |
| G5 tube expansion | Known smooth surface and normal displacement; calculate remainder divided by integral delta^2. | Remainder exceeds C/2 with assumptions checked; topology changes/extra components are excluded. |
| G6 scale invariance | Fix random thresholds, vary c; report boundary risk, latent sd, sd/gradient, and one-query value for deterministic-sign versus fixed-noise channels. | Geometric risk varying with c in the identical threshold law, or formulas disagreeing under exact integration. |
| Area/NSD separation | Oscillating graph sequence and parallel planes; report volume, Hausdorff, length, and NSD at one frozen tau. | Claimed formulas fail numerically; does not test superiority of any metric. |
| G7 moment insufficiency | Enumerate eight worlds and conditional L-infinity Bayes actions for both laws; report moments, R=1/2, Delta_plus=11/70, Delta_minus=0. | Any first/pair moment mismatch or risk/value mismatch invalidates the example. |
| D1 discovery/refinement | Enumerate fair-bit worlds for small k; compare T laws and final optimal Hausdorff risk at common Q=k+2. | A achieving risk below H/2 with only k individual independent-bit queries, or B failing to identify all bits by Q. |
| D3 path coalescence | Replay *stored* states/ledgers only; define complete state equality and delta_t; report absolute AULC difference and L sum lambda_t delta_t. | Difference exceeding bound after true coupling indicates hidden state/randomness or an implementation error. |
| D4/D5 monotonicity | Enumerate true order violations, contaminated-point count and falsely propagated labels separately. | Any inference outside the exact monotone contract; zero-error success cannot be extrapolated from average AUC. |
| D6 ranking bound | Exact deterministic tie-broken ranking; count V, r and first rare D; report r(D-1)<=V and tail count inequality. | An inequality violation falsifies counting/ranking implementation. Use empirical exact V, not rounded AUC. |
| Tail enrichment versus selected history | At each actual failed B8 prefix, record remaining tail, selected extreme, rare count, deterministic rank and conditional modeling assumption. | Unconditional tail enrichment alone cannot validate a selected-history success claim. |
| Geometry under covariate shift | Hold the same truth and predictions fixed, change only reference density; report each risk and exact importance-weighted equality where support overlaps. | Geometric truth changing would confound the test; absent overlap makes a reweighting guarantee unavailable. |

## 11. Scope and memory provenance

**NUMERICALLY CHECKED (new exact scratch computation, no repository modules).** Pure Python standard-library rational arithmetic verified G7 by enumerating all 27 height actions in {0,1/2,1}^3: risks before/after/gain were (1/2,12/35,11/70) and (1/2,1/2,0), and all six first/pair moments agreed. D6 and its top-M inequality passed exhaustive enumeration of 8,166 nonconstant binary sequences of lengths 2 through 12. D1's startup expectation 5/2 and budget count passed all 1,020 worlds for k=1,...,8. These checks support the formulas; their full proofs are above. The command used the existing Python interpreter with bytecode disabled and imported no repository modules.

Complete proof-only LaTeX fragment: `C:\Users\ozgur\AppData\Local\Temp\codex-round3-theory-20261005\geometry_proofs.tex` (no preamble/document; root combines it). The fragment includes only proved statements, with explicit assumptions.

The initial memory lookup pointed to the deterministic discovery failure and prior harmful hard-monotone propagation; all current empirical claims above were instead checked against the live Week12/16 text/artifacts. Relevant lookup: `C:\Users\ozgur\.codex\memories\MEMORY.md`, lines 74 and 96–98. The parent should include the prescribed memory citation if relying on this provenance. No memory was edited.
