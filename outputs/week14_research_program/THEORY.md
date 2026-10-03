# Week 14 theory — structure, discovery, generalization, evaluation and headroom

Status labels: **THEOREM** (stated assumptions, full proof), **PROPOSITION** (elementary but exact),
**KNOWN** (restatement of a published result, cited), **HEURISTIC** (derivation with an
approximation step). Each item ends with *Novelty* (honest) and *Why it matters*.
Numerical/property checks: `src/tests/test_week14_*.py`.

Common notation. A finite pool U, |U| = n, labels y: U → {0,1}, minority class m with K = |R|
cases, R = {u : y(u) = m}. A *query rule* may be adaptive and randomized. T_m is the index of the
first minority answer; T_both the first index at which both classes have been observed.

---

## Part D — Discovery of the rare regime

### Theorem D1 (no free lunch for discovery). THEOREM
Assume the minority set R is uniformly distributed over the K-subsets of U, independently of the
rule's internal randomness ξ (features may be used freely). Then for every query rule, adaptive or
not,
  P(T_m > t) = C(n−t, K) / C(n, K)  for t = 0, …, n,  hence  E[T_m] = (n+1)/(K+1),
which is the law of uniform random sampling without replacement. The same holds for T_both.

*Proof.* Until T_m every answer is "majority", so on {T_m > t} the first t queries are a fixed
function q_1(ξ), …, q_t(ξ) of ξ alone. Conditional on ξ these are t distinct points and, R being
uniform and independent of ξ, P(R ∩ {q_1,…,q_t} = ∅ | ξ) = C(n−t,K)/C(n,K). Integrate over ξ.
For T_both: given ξ and the first label c, the rule follows a fixed sequence σ^c until a label
≠ c appears; conditional on y(q_1) = c the remaining labels are again a uniformly random
arrangement, so the waiting time has the same law for every σ^c. ∎

**Corollaries.** (a) Deterministic rules: an adversary placing R at the last K positions of the
all-majority sequence forces T_m = n − K + 1. (b) By Yao's principle the minimax expected cost over
randomized rules is (n+1)/(K+1), attained by random sampling. (c) Under the exchangeable null no
rule — maximin, physics-ordered, hedged — is better *or worse* than random in expectation; any
benefit must come from an assumption that couples labels to features.

*Novelty:* elementary and almost certainly folklore (rare-category-detection papers state that
guarantees need compactness/smoothness assumptions). *Why it matters:* it turns "geometry-based
initialization is not reliably better than random" (Chandra et al. 2021; Week 12/13) into a
theorem and forces every discovery claim to name its structural assumption.

### Theorem D2 (geometric structure: sharp certificate and minimax cost). THEOREM
For a design S ⊂ U let h(S) = max_{u∈U} min_{s∈S} |u − s| (fill distance) and for a labelling
let ρ* = max_{x∈R} min_{u∉R} |x − u| (largest rare-pure radius). Let 𝓛_r = {labellings with ρ* > r}.

1. S hits R for every labelling in 𝓛_r **iff** h(S) ≤ r.
2. The smallest certifying design has size N(r) = min{|S| : h(S) ≤ r} (discrete k-center /
   covering number of the pool), and farthest-first (maximin) traversal of b points has
   h ≤ 2 h*_b (Gonzalez 1985), so it certifies 𝓛_{2r} within N(r) queries.
3. For every rule (adaptive, randomized), sup over 𝓛_r of E[T_m] ≥ (M_{2r} + 1)/2, where M_{2r} is
   the largest number of pool points with pairwise distances > 2r (and M_{2r} ≥ N(2r)).
Hence the minimax discovery cost over 𝓛_r lies in [(N(2r)+1)/2, N(r)].

*Proof.* 1(⇐) Week 13 Prop. 4. 1(⇒) If h(S) > r, take u* with d(u*, S) = h(S) and R = {u : |u−u*| <
h(S)}. Then S ∩ R = ∅ and ρ(u*) = d(u*, U∖R) ≥ h(S) > r. 2 follows from 1 and Gonzalez's bound.
3: pick a 2r-separated set p_1, …, p_M and R_j = {u : |u − p_j| ≤ r}; each R_j ∈ 𝓛_r (ρ(p_j) > r
because all non-members are farther than r), the R_j are disjoint, and under a uniform choice of j
any rule hits at most one R_j per query and, before a hit, follows a ξ-determined sequence, so
P(T > t) ≥ 1 − t/M. Summing gives E[T] ≥ (M+1)/2. M_{2r} ≥ N(2r) because a maximal 2r-separated
set is a 2r-cover. ∎

*Consequence.* If the pool fills a region of intrinsic dimension d, N(r) ≍ (diam/r)^d. Small,
thin or high-dimensional rare islands are expensive to certify geometrically; Week 13 measured
fill distance decaying as b^−0.49 on NEW pools. Farthest-first also preferentially selects
peripheral points (cf. the coreset "outlier" effect discussed by Yehuda et al., NeurIPS 2022), so
when rare islands sit in the density bulk it can be *worse than random* (Study 1, `islands`).

*Novelty:* the ingredients (k-center, packing) are classical; the sharp "iff" certificate and the
minimax characterization of rare-island discovery by pool covering numbers were not found in the
literature searched (rare category detection, cold-start AL, ProbCover/coreset). Moderate
confidence. *Why it matters:* explains why the frozen B16 maximin was certified on OLD (ρ* = 2.45
> h₁₆ = 1.91) and not on NEW (1.38 < 1.83), and shows that more maximin points buy certification
only polynomially in 1/r.

### Theorem D3 (order structure: Pareto-front certificate and minimax cost). THEOREM
Let ≼ be a known partial order on U and assume labels are monotone (u ≼ v ⇒ y(u) ≤ y(v)). Let Min
and Max be the minimal and maximal elements of U.

1. If class 0 occurs in U then Min contains a class-0 case; if class 1 occurs, Max contains a
   class-1 case. Hence any order that starts with Min ∪ Max observes both classes within
   |Min ∪ Max| queries, label-blind and without knowing which class is rare.
2. Lower bound: for each m ∈ Min the labelling with y(m) = 0 and y = 1 elsewhere is monotone; these
   |Min| labellings have disjoint minority sets, so every deterministic rule needs |Min| queries in
   the worst case and every randomized rule (|Min|+1)/2 in expectation (symmetrically for Max).
   The minimax cost over monotone labellings is therefore Θ(|Min| + |Max|).
3. If the pool is an iid sample of n points from a distribution with independent continuous
   coordinates on the k ordered axes, E|Max| = E|Min| = H_n^{(k−1)} (generalized harmonic number;
   Bentley, Kung, Schkolnick & Thompson 1978) ~ (ln n)^{k−1}/(k−1)!.

*Proof.* 1: take any x with y(x) = 0; the finite poset contains a minimal m ≼ x and monotonicity
gives y(m) ≤ 0. 2: a single minimal element labelled 0 cannot violate monotonicity (nothing lies
strictly below it), so the labellings are monotone, and the packing argument of D2.3 applies.
3: known. ∎

*Robustness.* Monotonicity is only needed along one chain: discovery succeeds whenever some
minority case has a minority-labelled minimal element below it; violations elsewhere are
irrelevant.

*Comparison of the three structures.* No structure: ~ n/K. Geometry: ~ (1/ρ*)^d. Order: ~ (ln n)^{k−1}.
For the LPBF order (P↑, VX↓, LS↓; k = 3) and n = 108 the order bound is ≈ 11 per side for
uniform-like pools; the observed label-free NEW-136 fronts are 6 (Min) and 9 (Max).

*Novelty:* the fact in 1 is trivial poset theory; its use as a label-blind, assumption-explicit
cold-start certificate with a matching minimax lower bound in active level-set estimation was not
found (Tao 2018/2021 treat the *learning* complexity of monotone classifiers, O(w log(n/w)) probes,
not cold-start discovery). Low–moderate confidence that this exact framing is new. *Why it matters:*
it identifies the physically reliable structure (monotone directions, which held on OLD with 3
violations in 22,050 pairs before NEW existed) that makes discovery cheap and dimension-robust.

### Proposition D4 (score structure; tight). PROPOSITION
Querying in a fixed score order, T_m ≤ 1 + #{majority ranked before the best-ranked minority}
≤ 1 + n_M (1 − AUC). The second inequality is tight (all minority cases tied in rank). Week 13 Prop. 5.

### Proposition D5 (hedging). PROPOSITION
Round-robin interleaving of J query orders, skipping already-queried points, satisfies
T ≤ J · min_j T_j for every labelling.
*Proof.* After at most J t real queries every order's first t elements have been queried. ∎
Together with D1: a hedge of structure-exploiting orders (and random) costs nothing in expectation
under the exchangeable null and is within a factor J of the best certificate whenever any one of
the structural assumptions holds. *Novelty:* the construction is Levin-style universal search /
algorithm portfolios; the application is ours. *Why it matters:* an operational, assumption-robust
startup rule replaces the brittle fixed-B16 contract.

---

## Part O — Physics as order, not as level

### Proposition O1 (dominance is the exponent-robust order). PROPOSITION
In log coordinates z = (log P, log VX, log LS) let h_w(z) = w₁z₁ − w₂z₂ − w₃z₃, w ∈ ℝ³_{>0}. For
points a, b: h_w(a) ≤ h_w(b) for every w > 0 ⟺ b₁ ≥ a₁, b₂ ≤ a₂, b₃ ≤ a₃ (signed dominance).

*Proof.* ⇐ termwise. ⇒ if b₁ < a₁ take w = (1, ε, ε) and let ε → 0 (similarly for the others). ∎

**Corollary O1a.** For the class 𝓜 of all labellings y = 1[g(z) > 0] with g coordinatewise monotone
(which contains every positive-exponent scaling law with any threshold, any increasing link, and
multi-regime laws such as min/max of such laws), the labels implied *for every member consistent
with the data* are exactly the dominance closure of the data. For the narrower class of
positive-exponent log-linear laws, the implied set is the dominance closure of the convex hulls of
the two classes (a linear-feasibility check), i.e. strictly more informative but no longer robust to
curved or multi-regime boundaries.

*Why it matters.* Week 13 found that log h transfers its *ranking* (AUC 0.991 OLD, 0.857 NEW) but
not its *level/orientation* (free exponents VX/P −0.52 on OLD vs −2.1 on NEW; NEW ≈ a VX threshold).
O1 identifies precisely what part of the physics survives every exponent change: the signed
dominance order. A fixed physics mean (M3) commits to one w; an order-constrained model commits only
to the signs. *Novelty:* elementary; the interpretation as the transfer-invariant content of a
scaling law appears new in this application but the mathematics is not.

### Heuristic O2 (why a stationary discrepancy cannot repair a localized law failure)
For a fixed-mean GP with stationary discrepancy amplitude σ² learned by marginal likelihood, the
likelihood is dominated by the bulk of the source design where the physics mean is right; a
failure confined to a region holding a small fraction of source cases contributes little, so σ̂² is
small and the posterior correction there is shrunk (Week 13 Prop. 7 bounds the correction by
σ²·S₀(x)). Evidence: uncapped M3 learns σ² = 1.9 on real OLD (cap 1) and 1.8 in the Week 13
synthetic transfer; its learned discrepancy is effectively one-dimensional (ℓ_VX ≪ others). This is a
heuristic, not a theorem: a rigorous version would need a specific kernel/design model.

---

## Part I — Information sufficiency of the rare regime

### Proposition I1 (exchangeable leave-one-out front fraction). PROPOSITION
Let rare cases r₁, …, r_{K+1} be exchangeable and let F_{K+1} be the number of them not dominated (in
the rare direction) by any other. Then the probability that a fresh rare case is certified rare by
the dominance closure of K labelled rare cases is 1 − E[F_{K+1}]/(K+1). The empirical fraction of K
labelled rare cases dominated by another labelled rare case is an unbiased estimate of this
probability at sample size K − 1.

*Proof.* By exchangeability each of the K+1 cases is equally likely to be the fresh one, and it is
certified iff it is not on the front of the K+1. ∎

*Why it matters.* It gives a label-only diagnostic of whether the labelled rare cases contain
transferable structure under the order assumption: if the rare cases form an antichain, the order
provides no generalization and more querying of the same pool cannot help. Analogous statements hold
for any conservative "version-space" learner (e.g. bounding boxes: certified iff not extreme in some
coordinate, probability ≥ 1 − 2d/(K+1)). *Novelty:* standard exchangeability argument.

---

## Part E — Evaluation

### Theorem E1 (every linear confusion metric is a precision threshold). THEOREM / KNOWN
Fix an evaluation set with n_m minority and n_M majority cases and a metric
M_w = w_m TPR_m + w_M TNR_M (w > 0; accuracy, balanced accuracy, weighted accuracy, q-band accuracy).
Compare predictors 1 and 2 with ΔC, ΔW the differences in correct and wrong minority calls.
(i) If ΔC ≥ 0 ≥ ΔW (Pareto dominance) every M_w agrees. (ii) Otherwise (say ΔC + ΔW > 0 with
ΔC, ΔW > 0) M_w prefers predictor 1 iff the marginal precision ρ = ΔC/(ΔC+ΔW) exceeds
τ_w = (w_M/n_M)/(w_M/n_M + w_m/n_m). Accuracy has τ = 1/2, balanced accuracy τ = π = n_m/(n_m+n_M).
Every non-dominated pair is reversed by some linear metric.

*Proof.* ΔM = w_m ΔC/n_m − w_M ΔW/n_M. ∎ *Novelty:* this is the iso-performance-line argument of ROC
analysis (Provost & Fawcett 2001; Drummond & Holte cost curves) re-expressed through the marginal
precision of extra minority calls; Week 13 Prop. 2 is the special case accuracy vs BA. **Not new.**
*Why it matters:* it explains every metric reversal observed in Weeks 12–13 with one number ρ and
shows that a single accuracy-type endpoint cannot certify boundary recovery under imbalance.

### Theorem E2 (consistency and meaning of cut-edge recovery on r-graphs). THEOREM (part 1) / HEURISTIC (part 2)
Let X₁, …, X_n be iid with density p on Ω ⊂ ℝ^d, A the true set with C² boundary Γ, Â a fixed
predicted set, and G_r the graph with edges |X_i − X_j| < r. Let CUT_n be the number of edges with
endpoints on different sides of A and RES_n those whose endpoints are also correctly classified by
Â, and BER_n = RES_n / CUT_n.

1. BER_n → BER(r) = E[φψ] / E[φ] almost surely, with φ(x,y) = 1[|x−y|<r] 1[x∈A, y∉A] and
   ψ(x,y) = 1[x∈Â, y∉Â] (strong law for U-statistics, Hoeffding 1961). A constant predictor gives
   BER(r) = 0 for every p and A.
2. If AΔÂ is a sliver along Γ of local width δ(x) and r → 0 with δ = O(r),
   BER(r) ≈ 1 − ∫_Γ p² q(δ/r) dS / ∫_Γ p² dS,
   where q(t) ∈ [0,1], q(0) = 0, q(t) = 1 for t ≥ 1, is the fraction of interface-straddling pairs of
   length < r with an endpoint within distance t r of the interface (flat-interface approximation).
   Errors farther than r from Γ do not affect BER (BEF1 penalizes them through spurious cut edges).

*Interpretation.* BER is a **soft boundary recall at tolerance ≈ graph edge length, weighted by p²**
(r-graph). For kNN graphs the cut functional converges to a p^{(d−1)/d}-weighted surface integral
(Maier, Hein & von Luxburg, NIPS 2008) and the tolerance adapts as p^{−1/d}; Gabriel graphs behave
like scale-adaptive graphs empirically. *Consequences (all checked in COUNTEREXAMPLES.md):* (a) BER is
blind to boundary displacements smaller than the local point spacing; (b) its weighting follows the
sampling density, so the same predictor can rank differently under two campaign densities;
(c) under label noise the observed cut set contains noise-induced edges and even the Bayes boundary
scores well below 1. *Novelty:* part 1 is a direct application of classical results; the
interpretation of cut-edge recovery as a density-weighted tolerance boundary recall and its use as
an evaluation metric for finite-pool level-set estimation were not found in the literature
searched (closest: S² of Dasarathy et al. 2015 uses cut edges for *acquisition*; boundary-F1 and
NSD in segmentation use pixel grids). Moderate confidence.

---

## Part H — Acquisition headroom

### Proposition H1 (headroom is bounded by learner sensitivity and pool exhaustion). PROPOSITION
Let M be a metric of a learner A on a fixed evaluation set and β_b the replace-one sensitivity
β_b = sup{|M(A(L)) − M(A(L − x + z))| : |L| = b, x ∈ L, z ∈ U∖L}. For any two acquisition rules with
labelled sets of size b, |ΔM(b)| ≤ β_b |L₁ ∖ L₂| ≤ β_b min(b, n − b), and the AULC difference over
[b₀, B] is at most the average of β_b min(b, n − b).

*Proof.* |L₁∖L₂| = |L₂∖L₁|; swap one element at a time (every intermediate set has size b) and
apply the triangle inequality; |L₁ ∩ L₂| ≥ 2b − n gives |L₁∖L₂| ≤ n − b. ∎

### Counterexample H2 (no stability-free version). See COUNTEREXAMPLES.md C6: for an interpolating
learner and an isolated influential case, |ΔM(n−1)| can equal the full metric range, so headroom
need not vanish as b/n → 1 without a sensitivity bound. *Why H1/H2 matter:* "acquisition rules
become indistinguishable late in the budget" is true exactly to the extent that the learner is
insensitive to the remaining unlabelled cases; rare-class exhaustion (Week 13: margin labels 8.5 of
≈9.6 NEW rare cases by B40) is the mechanism that removes the high-sensitivity cases.
*Novelty:* elementary stability argument (cf. Bousquet & Elisseeff 2002); its use as a headroom
bound for acquisition benchmarking appears not to be standard.

---

## Part L — An accounting identity, not a decomposition

For a reference ladder Bayes ≥ ceiling(full pool) ≥ …, the gap of a protocol π at budget b admits
the telescoping identity
  Bayes − M(π, b) = [Bayes − M(full)] + [M(full) − M(rand, b)] − [M(π, b) − M(rand, b)],
i.e. model/information limit + sample limit − acquisition gain. It is exact but reference-dependent:
discovery, model and metric effects interact (changing the startup changes which model errors
occur), so no unique additive attribution exists (a 2×2 example with an interaction is given in
COUNTEREXAMPLES.md C9). We therefore recommend reporting the ledger with fixed, pre-declared
references rather than claiming a causal decomposition.
