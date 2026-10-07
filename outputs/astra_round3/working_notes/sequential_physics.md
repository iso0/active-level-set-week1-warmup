# Round 3: sequential model error and physics level versus order

Research note, 2026-10-05. Repository inspected strictly read-only. No repository experiment, import, fit, or modification was performed. The proofs below are self-contained; statements marked PRIOR ART are attribution, not claims of novelty. PROVED means proved under the displayed assumptions, not empirically established for SPH. Proposed experiments are not executed.

## 0. Scope and live repository facts

**KNOWN, verified from current files.** Read `outputs/week16_theory_meets_data/WEEK16_REPORT.md`, `THEORY_WEEK16.md`, `ERRATUM_LAPLACE.md`, the relevant `src/week16_peer.py::Model.fit`, and `src/week12_models.py`. Week 16 explicitly separates theoretical/exact results, controlled synthetic results, and descriptive OLD/NEW results. Its physics mean is fitted to the currently revealed campaign labels: standardized-score logistic regression with `C=1`, followed by a GP with that plug-in mean; a one-class fit uses zero mean. The original M3 path also estimates a physics trend from its supplied training labels before fixing it inside the residual-GP fit. Thus “anchored physics” must distinguish a fitted within-campaign level, a level frozen during the residual fit, and an OLD-fitted level transferred unchanged to a new campaign. These are different interventions.

**KNOWN, verified claim boundary.** The Week 16 coherent one-step calculation is exact under its fitted Gaussian posterior and probit observation approximation. It is not exact conditioning under the original non-Gaussian logistic model, and refitting a Laplace posterior after a fantasy observation is a different operation. The two Week 15 gpworld m0=-4 cells have withdrawn historical values under E16-1. No theorem below restores them or converts already-open NEW-136 into external confirmation.

**KNOWN, inherited Round 2 result, not rederived.** For its fixed-N, noiseless, full-pool Hamming setting, retain the B/N lower bound and the sharp N=3, B=2 value 4/5 with the existing rational certificates. The disjoint-target/noisy-sensor examples below are explicitly outside that setting. No general sharp finite-(N,B) constant is claimed here.

## 1. Sequential simulation theorem with the two necessary error objects

### S1. Fixed-policy terminal-risk bound

**PROVED; simulation-lemma adaptation, not claimed new.** Fix a horizon B, common feasible query rules, a terminal target T, and a common loss L(d,T) in [0,1]. A policy selects A_t from H_t=(A_0,O_0,...,A_{t-1},O_{t-1}) and selects a terminal decision d(H_B). Policies may randomize with independent internal randomness. Let P be truth and Q the planning law. When a *fixed policy map* is evaluated under both laws, its action kernel is identical; only observation kernels and target posteriors change.

Write

    K_L,t(.|h,a) = L(O_t in . | H_t=h, A_t=a),   L in {P,Q},
    epsilon_t(h,a) = TV(K_P,t(.|h,a), K_Q,t(.|h,a)),
    delta(h) = TV(P(T in .|H_B=h), Q(T in .|H_B=h)),
    E_pi = sum_{t=0}^{B-1} E_P^pi[epsilon_t(H_t,A_t)],
    D_pi = E_P^pi[delta(H_B)],
    Gamma_pi = min{1, E_pi + D_pi}.

Use TV=sup_A|P(A)-Q(A)|=one half the L1 distance. Versions of Q kernels/posteriors must be specified at P-reachable histories even if Q assigns them zero probability; choosing such versions is part of specifying a deployable Q policy. Then, for every terminal rule d,

    |R_P(pi,d) - R_Q(pi,d)| <= Gamma_pi.                       (S1)

**Proof.** Let mu_t and nu_t be the P and Q distributions of H_t. The action-plus-observation kernel under each law uses the same policy action distribution. Total variation contracts through a Markov kernel, so

    TV(mu_{t+1},nu_{t+1})
      <= TV(mu_t K_P, mu_t K_Q) + TV(mu_t K_Q,nu_t K_Q)
      <= E_{mu_t,pi}[epsilon_t(H_t,A_t)] + TV(mu_t,nu_t).

Both initial histories are empty, so induction gives TV(mu_B,nu_B)<=E_pi. Define r_L(h)=E_L[L(d(h),T)|H_B=h]. Then |r_P(h)-r_Q(h)|<=delta(h) and 0<=r_Q<=1. Add and subtract E_{mu_B}r_Q:

    |E_{mu_B}r_P - E_{nu_B}r_Q|
      <= E_{mu_B}delta + TV(mu_B,nu_B) <= D_pi+E_pi.

Risks are in [0,1], giving the cap. The proof handles adaptive and randomized policies because their common action kernel cancels. QED.

**PROVED, weighted-Hamming refinement.** If T=(T_i), predictions are binary, and L=sum_i w_i 1{d_i != T_i}, w_i>=0, sum_i w_i=1, replace delta(h) throughout S1 by

    delta_H(h) = sum_i w_i |P(T_i=1|h)-Q(T_i=1|h)|.             (S1-H)

For a fixed binary decision, its conditional error is either p_i or 1-p_i, hence the difference is bounded by |p_P,i-p_Q,i|. Sum and use the same history-law argument. Joint target-posterior TV is unnecessary for this terminal loss. This does not make initial marginal calibration sufficient: the marginals must be correct *after the adaptively selected history*.

### S2. Regret of a Q-optimal sequential policy deployed under P

**PROVED.** Let (pi_Q,d_Q) be beta-optimal under Q among a common policy/decision class, and let (pi_P,d_P) minimize risk under P in that class. Then

    R_P(pi_Q,d_Q)-R_P(pi_P,d_P)
      <= beta + Gamma_{pi_Q} + Gamma_{pi_P}.                  (S2)

The same bound holds with S1-H for weighted Hamming. In particular, uniform epsilon_t(h,a)<=e_t and delta(h)<=d give regret at most beta+2(sum_t e_t+d), capped by 1.

**Proof.** Insert R_Q(pi_Q,d_Q) and R_Q(pi_P,d_P). The first and last differences are bounded by S1, and the middle difference is at most beta. QED.

**PROVED, occupancy interpretation.** Only error along the trajectories of the two compared policies enters S2; uniform control everywhere is sufficient but stronger than necessary. Measuring discrepancies only along the old margin trajectories does not control Gamma_{pi_Q} if a new policy visits different histories. The P-optimal-policy term is also unknown unless a controlled model permits it to be calculated.

**PROVED, coupling refinement.** Under uniform kernel errors e_t in [0,1], couple identical histories using maximal couplings at each observation and identical policy randomness. Their probability of staying identical through B is at least product_t(1-e_t). If full target-posterior TV is also uniformly at most d, couple targets after an identical terminal history. Consequently

    |R_P(pi,d)-R_Q(pi,d)|
       <= 1-(1-d) product_t(1-e_t).                           (S2-C)

This is a terminal-loss result. For cumulative losses, one must sum the corresponding prefix bounds; the usual additional horizon factor can then appear. Do not import a cumulative-reward B-squared constant into a single normalized terminal loss.

### S3. Relative-entropy form

**PROVED.** Subject to absolute continuity (otherwise read the bound as infinite), let

    J_pi = sum_t E_P^pi KL(K_P,t(.|H_t,A_t) || K_Q,t(.|H_t,A_t))
           + E_P^pi KL(P(T|H_B) || Q(T|H_B)).

The chain rule and cancellation of the common action kernels give

    KL(P^pi_{H_B,T} || Q^pi_{H_B,T}) = J_pi.

Pinsker's inequality gives |R_P(pi,d)-R_Q(pi,d)|<=sqrt(J_pi/2). Thus the regret in S2 is also at most beta+sqrt(J_piQ/2)+sqrt(J_piP/2), capped by 1. This form exposes that a good aggregate log score on *the wrong history distribution* is not the required quantity.

**PRIOR ART.** The general model-error-to-policy-value strategy is the simulation-lemma tradition; see Kearns and Singh, *Near-Optimal Reinforcement Learning in Polynomial Time*, Machine Learning 49 (2002), 209–232, [primary paper PDF](https://people.eecs.berkeley.edu/~pabbeel/cs287-fa09/readings/KearnsSingh_E3_2002.pdf). S1–S3 spell out the posterior-target term needed for this thesis's observation/latent-target distinction.

**Experiment row S1–S3 (proposal, not run).** Observable prediction: a small bound on *both* errors prevents large sequential regret; zero observation error alone need not. Model/data: a fully specified finite latent/sensor law or small discretized GP world with exact enumeration, B=2–4; P and Q, losses, feasible actions and tie-breaking fixed in advance. Exact statistic: enumerate R_P(pi_Q)-R_P(pi_P), each occupancy-weighted TV/KL term, and the signed slack bound-minus-regret. Falsifier: negative slack beyond exact-arithmetic/numerical certification tolerance refutes the claimed implementation or proof application. On real data, latent-target posteriors and counterfactual P kernels are not directly observable, so the same row cannot be called an empirical certification from one realized label per point.

## 2. One-step superiority does not order long-horizon policies

### S4. Exact parity/sensor counterexample, including identical initial pairwise laws

**COUNTEREXAMPLE, PROVED.** Let A,B be independent fair signs, T=AB, and E an independent sign with P(E=1)=1/2+eta, 0<eta<1/2. There are three queries revealing A, B, or C=TE, each at most once. The sole target is T and the loss is its classification error. The budget is two. This is a disjoint-target sensor problem with one noisy observation, not noiseless full-pool Hamming.

Initially A and B each have zero one-step value for T, while C has value eta. A true-law myopic rule therefore selects C. Either remaining query is independent of (T,C), so its second one-step value is zero. The myopic total gain is eta. Querying A and B gives T exactly and total gain 1/2. The gain ratio is 2 eta, arbitrarily close to zero; the initially *strictly better* one-step query starts the worse two-step policy.

Now define planning law Q with independent fair T,A,B and the same C=TE. Under P and Q, all individual marginals and all pairs among T,A,B,C are identical. In particular all initial one-step target-query values agree exactly. Also every observation transcript of length at most two has exactly the same law under P and Q: every pair of distinct sensor observations is independent fair, so adaptive branching does not change this equality. Therefore all e_t needed through budget two are zero. But after A,B, P(T=AB|A,B)=1 while Q(T=1|A,B)=1/2; terminal delta=1/2. Under Q an optimal two-query policy includes C, with P risk 1/2-eta, whereas the P-optimal A,B policy has risk zero.

**Proof details.** A is independent of T=AB because B is fair, and independent of (T,E), hence of (T,C); similarly for B. T and C have agreement probability 1/2+eta in both laws. Each observed two-sensor pair has joint probability 1/4 in both laws. Conditional on A,B the two target posterior laws stated above are immediate. These facts prove every value and equality without asymptotics or simulation. QED.

**PROVED implication.** Initial target-observation pairwise correctness is enough for initial binary one-step values, but does not determine posterior target beliefs after two observations. Higher-order structure reappears as conditional structure at later histories. This is exactly why the terminal-posterior term in S1 cannot be discarded, even if all observation transcript kernels through B are correct.

**Experiment row S4 (proposal, exact construction).** Observable prediction: myopic gain eta, optimal gain 1/2, initial pairwise discrepancy zero, terminal discrepancy after A,B equal 1/2. Model/data: the eight or sixteen finite sign worlds specified above, eta=1/10 or another rational value. Exact statistic: rationally enumerate one-step values, the B=2 decision trees, pairwise-law differences, and final risk. Falsifier: any nonzero claimed-equal initial pair or a different terminal risk; this is an algebra/software check, not a thesis dataset experiment.

### S5. When a long-horizon greedy guarantee is available

**KNOWN / PRIOR ART.** A nonnegative normalized realization utility f(S,phi) is *adaptively monotone* if every feasible conditional expected marginal gain Delta(e|psi) is nonnegative, and *adaptively submodular* if Delta(e|psi)>=Delta(e|psi') whenever psi is extended to psi' and e is still unqueried. For unit costs and budget B, exact greedy achieves at least 1-(1-1/B)^B >= 1-1/e of the optimal expected gain under the same law. The standard published statement uses the weaker 1-exp(-1) form; see Golovin and Krause, *Adaptive Submodularity: Theory and Applications in Active Learning and Stochastic Optimization*, JAIR 42 (2011), [primary full paper](https://arxiv.org/pdf/1003.3967), Theorem 5 in this PDF version. Approximate-greedy and unequal-budget forms are also given there.

**PROVED, recurrence behind the bound.** After the greedy partial history, adaptive submodularity bounds the conditional incremental value of any B-query continuation by B times the largest current marginal gain. Adaptive monotonicity allows comparison with the concatenation of the current policy and an optimal B-query policy, with redundant queries omitted. Writing expected greedy gain G_t and optimal gain OPT gives OPT-G_t<=B(G_{t+1}-G_t). Hence OPT-G_{t+1}<=(1-1/B)(OPT-G_t), and iterate from G_0=0. These steps need the stated properties for the particular utility and law, not merely an informal diminishing-returns intuition. QED.

**COUNTEREXAMPLE, PROVED.** S4 violates adaptive submodularity: Delta(B|empty)=0 but Delta(B|A=a)=1/2. General posterior classification-risk reduction therefore has no automatic adaptive-submodularity certificate. A theorem about version-space elimination or another surrogate is not automatically a theorem about Hamming, NSD, DC-BD, or q20. Likewise a property proved under Q need not hold under P.

**PROVED sufficient special case.** Independent target labels, noiseless self-observation, and fixed nonnegative Hamming weights give adaptive modularity: querying i always reduces expected risk by w_i min(p_i,1-p_i), unaffected by previous labels. Sorting those fixed values is fully optimal for every B. With equal weights this is ideal margin. Correlation or observation noise removes this particular argument; it does not logically prove that every such problem fails adaptive submodularity.

**Experiment row S5 (proposal).** Observable prediction: exact greedy satisfies the bound in finite models certified adaptively monotone/submodular; parity violates the diminishing-gain premise. Model/data: independent noiseless coordinates as a positive control and S4 as a negative control. Exact statistic: maximum over all nested reachable histories and unused e of [Delta(e|psi')-Delta(e|psi)], plus greedy/optimal gain. Falsifier: a positive maximum invalidates the submodularity premise; a below-bound ratio despite a verified premise invalidates the computation. Sampling a few histories can find a counterexample but cannot certify the universal premise.

## 3. Physics level, campaign shift, and normal-normal shrinkage

### P1. Exact bias-variance tradeoff

**PROVED in an explicit model.** Assume an informative physics score s orders the target monotonically, with a campaign threshold theta=theta_0+Delta. theta_0 is an OLD or external anchor. At a fixed paid budget, suppose current-campaign information is summarized by

    Z = theta + epsilon,  epsilon ~ N(0,v), v>0,

independent of the campaign shift. This is an exact normal-location experiment. Treating a threshold estimate from binary logistic labels as such a Z would be an additional approximation, not part of this theorem. Consider

    theta_hat_w = theta_0 + w(Z-theta_0),  0<=w<=1.

w=0 fixes the OLD level, w=1 discards OLD level information while retaining the common score direction, and intermediate w weakens level borrowing. Conditional squared threshold error is

    R_Delta(w) = (1-w)^2 Delta^2 + w^2 v.                     (P1)

**Proof.** theta_hat_w-theta=-(1-w)Delta+w epsilon. The cross term has zero expectation and E epsilon^2=v. QED.

**PROVED consequences.** The fixed anchor has risk Delta^2 and the current-only rule has risk v: anchoring is harmful exactly when Delta^2>v. At Delta=0 the anchor has zero error while current-only pays v, demonstrating the in-domain efficiency price of discarding a correct level. For w<1, borrowing is worse than current-only exactly when

    Delta^2 > v(1+w)/(1-w).

For 0<=w<w'<=1, weakening borrowing from w to w' improves risk exactly when

    Delta^2 > v(w+w')/(2-w-w'),

with the denominator positive unless both weights equal one. These are risk statements for the displayed experiment and loss, not universal classification rankings.

### P2. Bounded-shift minimax within affine rules

**PROVED.** Suppose |Delta|<=D is known. Then

    sup_{|Delta|<=D} R_Delta(w) = (1-w)^2 D^2 + w^2 v,
    w_D = D^2/(D^2+v),
    inf_{0<=w<=1} sup_{|Delta|<=D} R_Delta(w)
       = D^2 v/(D^2+v).                                      (P2)

For D>0 this is strictly below both endpoint worst-case risks D^2 and v. Differentiating the convex quadratic proves the unique optimum. D=0 gives w_D=0. Larger admissible shifts increase w_D: robustness here means less borrowing of the old threshold.

**PROVED limitation: affine minimax is not unrestricted bounded-parameter minimax.** Clip theta_hat_wD to [theta_0-D,theta_0+D]. Projection onto an interval cannot increase squared distance to any theta in that interval and strictly reduces it on a positive-probability Gaussian tail when D,v>0. Thus an unrestricted bounded-parameter minimax claim for the un-clipped affine rule would be false.

### P3. Exact robust-Bayes interpretation under a moment ambiguity set

**KNOWN / PRIOR ART, proved here for the campaign interpretation.** This is the classical univariate second-moment minimax calculation, explicitly treated in Johnstone, *Gaussian Estimation: Sequence and Wavelet Models*, subsection on univariate moment bounds and the Gaussian least favorable distribution: [author's primary PDF](https://imjohnstone.su.domains/GE_08_09_17.pdf). No novelty is claimed. Now the uncertainty class is a set of *shift distributions*

    Gamma_D = {nu: E_nu[Delta^2] <= D^2},

with no bounded-support requirement. Noise remains independent N(0,v). Among **all measurable estimators**, the Gamma-minimax integrated squared-error risk is

    inf_a sup_{nu in Gamma_D} E_{nu,epsilon}[(a(Z)-theta)^2]
       = D^2 v/(D^2+v),                                      (P3)

attained by a_D(Z)=theta_0+w_D(Z-theta_0). A least favorable prior is Delta~N(0,D^2).

**Proof, upper bound.** P1 integrated over any nu in Gamma_D gives risk at most (1-w)^2D^2+w^2v. At w=w_D this equals D^2v/(D^2+v).

**Proof, matching lower bound.** The normal prior nu_*=N(0,D^2) belongs to Gamma_D. Completing the square in the normal likelihood and prior gives

    Delta | Z=z ~ N( w_D(z-theta_0), D^2v/(D^2+v) ).

The posterior mean minimizes conditional squared error over every measurable estimator, and its integrated Bayes risk is the constant posterior variance D^2v/(D^2+v). Therefore every estimator has worst-prior risk at least this value. The upper-bound estimator attains it. QED.

**PROVED distinction.** The same algebraic weight solves P2's bounded-shift *affine* problem and P3's moment-class *unrestricted* problem, but their uncertainty classes and minimax claims differ. A normal prior with variance D^2 has positive mass outside [-D,D], so it cannot supply P2's unrestricted lower bound.

**PROVED normal-normal Bayes form.** With an actual prior Delta~N(0,tau^2), posterior weight is tau^2/(tau^2+v) and posterior variance tau^2v/(tau^2+v). Choosing tau^2=D^2 recovers P3. Selecting an arbitrary smaller prior variance is not robustness: it assumes tighter campaign stability and increases bias under larger shifts.

**PROVED unrestricted-shift limit.** Over all deterministic shifts Delta in R, current-only Z has constant risk v and is minimax among all measurable estimators. Lower bound: the Bayes risks for N(0,M^2) priors approach v as M tends to infinity. Every fixed affine w<1 has infinite worst-case risk, because its squared bias grows without bound. This formalizes a worst-case transfer advantage of discarding the OLD level when no finite shift assumption is defensible.

**PROVED design limitation.** If a design affects only the known variance v(d) in this one-dimensional model, P3's optimal risk D^2v/(D^2+v) is increasing in v. Robust and nonrobust design rankings that merely minimize v therefore coincide. P3 proves an inference/borrowing result; it does not by itself prove an improved acquisition policy. A new design claim needs a model in which bias, uncertainty geometry, or information varies nontrivially by design.

**Experiment row P1–P3 (proposal).** Observable prediction: the risk curve is the displayed quadratic, crosses current-only at the stated shift, and the worst-case affine envelope is minimized at w_D. Model/data: fresh normal-location simulations with predeclared v, D, and shifts, or exact analytic expectations; use a separately frozen binary-threshold experiment only to test an approximation. Exact statistic: mean squared threshold error minus [(1-w)^2Delta^2+w^2v], and the maximum risk over the prespecified shift set; separately compare the clipped affine estimator for P2. Falsifier: a systematic discrepancy in the exact normal experiment, a purported universal benefit at all shifts, or claiming P2's un-clipped affine rule beats its clipping would invalidate the claim. For SPH, failure of the normal approximation or of order preservation rejects applicability, not the algebra.

## 4. An exact order-only finite-pool model

### P4. Threshold rank can transfer while absolute threshold does not

**PROVED / KNOWN binary-search mechanism.** Let N distinct score values be ordered s_1<...<s_N, with noiseless labels y_i=1{i>k}, k in {0,...,N}. A strict OLD-level prediction k_0 has normalized full-pool Hamming error |k-k_0|/N. Any strictly increasing transformation of s leaves the ordered pool and labels' single-threshold structure unchanged, even when the threshold rank changes across campaigns.

An order-only learner maintains the contiguous set of feasible k and queries the score index that divides it as evenly as possible. Starting with N+1 possible thresholds, after B labels at most

    m_B = ceil((N+1)/2^B)

remain. A median feasible threshold has worst-case Hamming error at most floor(m_B/2)/N. Exact identification requires and is achieved by ceil(log_2(N+1)) labels in the worst case.

**Proof.** Querying i returns whether k<i, a binary cut in the ordered threshold set. Balanced cuts halve its cardinality up to a ceiling. A set of m consecutive integer thresholds spans m-1 positions; a median is at distance at most ceil((m-1)/2)=floor(m/2) from either endpoint. For exact identification, a deterministic binary decision tree of depth B has at most 2^B leaves, so B>=ceil(log_2(N+1)); balanced search attains the bound. QED.

**PROVED tradeoff example.** Take N=7, old threshold k_0=2, B=1. Query i=4 and use the lower median of the remaining feasible thresholds. In-domain k=2 gives feasible k in {0,1,2,3}, final estimate 1, and error 1/7, whereas the correct OLD anchor has error zero. Over all transferred k in {0,...,7}, this order-only rule's worst-case error is 2/7; the fixed old anchor's is 5/7. Thus a model exists with a strict in-domain efficiency cost and strict worst-case transfer benefit, under exactly the same monotone order assumption.

**PRIOR ART.** Binary-search active learning of a realizable one-dimensional threshold is standard; see Dasgupta, *Analysis of a greedy active learning strategy*, NIPS 2004 / author version 2005, [primary paper](https://cseweb.ucsd.edu/~dasgupta/papers/greedy.pdf), introduction and Figure 1. P4 supplies explicit finite-pool error and transfer comparisons for the present argument; no priority is claimed.

**PROVED limits.** These guarantees require exact monotonicity, distinct ordered scores, and noiseless labels. The real log-h ranges overlap and the repository permits local discrepancy, so P4 is a transparent model, not an established description of SPH. A label inversion is a direct witness against the noiseless single-threshold model. Order-only protects against changes of level and monotone score transformations; it does not protect against a reversed ranking, a nonmonotone boundary, or unmodeled label noise.

**Experiment row P4 (proposal).** Observable prediction: worst remaining threshold-set size <=ceil((N+1)/2^B), exact identification by the logarithmic budget, and the N=7 risk contrast above. Model/data: enumerate all k on a fixed sorted synthetic pool, then separately add a prespecified inversion/noise stress test. Exact statistic: maximum normalized Hamming error over k and feasible-set size by budget; for an observed real pool, inversion count sum_{i<j}1{y_i=1,y_j=0}. Falsifier: any violation of the bound in the noiseless enumerated model; for real applicability, any inversion falsifies exact one-threshold realizability (without proving that a noisy monotone tendency is absent).

## 5. What coefficient regularization does and does not establish

### P5. Positive attenuation of the whole physics mean cannot move its threshold

**PROVED.** For an affine mean m(s)=b_0+b_1 s, b_1!=0, multiplying both coefficients by lambda>0 preserves its zero crossing -b_0/b_1. Therefore attenuating lambda m(s) alone cannot correct a pure campaign threshold shift. It can change probability confidence, interaction with a fitted residual, and hence subsequent acquisition; those are different mechanisms.

**PROVED.** A free campaign intercept c in m_new(s)=b_0+b_1s+c moves the threshold to -(b_0+c)/b_1. A threshold prior theta_new~N(theta_0,tau^2), or a prior on c with an explicitly specified scale, expresses uncertain transfer of level while retaining score order when b_1's sign is fixed. Regularizing only b_1 with a free intercept can also change the crossing, but it is not algebraically equivalent to shrinking theta without an explicit parameterization and prior.

**KNOWN / model-identification caution.** L2-penalized logistic regression can be viewed as a MAP estimate under a particular coefficient prior, subject to the loss normalization, standardization, intercept-penalty convention, and solver. A `C=1` setting does not define a shift-radius D, an ambiguity set, a least favorable prior, or a minimax theorem. Thus Week 16's regularized physics mean is not automatically an implementation of P3 or of robust Bayesian experimental design.

**PROVED inferential distinction.** A plug-in mean fit and a joint hierarchical Bayesian model need not yield the same posterior. Plug-in fitting treats estimated b_0,b_1 as fixed in the next stage and omits their posterior uncertainty. Reusing the same labels to fit the trend and the residual can be a deliberate empirical-Bayes/composite fitting procedure, but its two-stage output is not justified by pretending that a data-dependent prior mean was an independent pre-data prior. Joint inference would include one likelihood for the labels and propagate uncertainty of the trend and discrepancy parameters together. None of this proves that the plug-in predictor must be poor; it prevents claiming full-Bayes calibration from the fitting architecture alone.

**CONJECTURE, plausible mechanism requiring a matched test.** A campaign-specific threshold/intercept with appropriately weakened OLD borrowing may preserve useful physics ordering while reducing transfer bias. A regularized current-campaign trend may be more stable than a nearly unpenalized trend when startup labels are few or almost separated. The algebra above does not establish this for M3, and the Week 16 comparison changes more than one feature relative to strict OLD transfer.

**Experiment row P5 (proposal).** Observable prediction: lambda>0 mean-only attenuation leaves the zero crossing fixed; allowing campaign intercept changes it. Model/data: a predeclared logistic threshold-shift family, same paid labels and acquisition path for all inference variants, explicit fixed/updated intercept, slope penalty, and residual flexibility. Exact statistic: threshold bias and variance separately; final-risk contrast with intervals; rank agreement and calibration as secondary outcomes. Falsifier: a pure mean-only attenuation claimed to move the crossing, or a robustness claim that vanishes when intercept freedom and residual flexibility are matched. Frozen selection and a later independent campaign are needed for a real transfer claim.

## 6. OLD-only selection: what is identifiable

### P6. No universal OLD-only choice without a relation between campaigns

**PROVED, two-world indistinguishability.** Let OLD labeled data have exactly the same law in two worlds, and let target score X~Uniform[0,1] in both. In world 0 the target label is 1{X>theta_0}; in world 1 it is 1{X>theta_1}, theta_0<theta_1. The learner has OLD labels and any quantity of unlabeled target scores, but no target labels. Its output distribution must be identical in the two worlds. For any possibly randomized classifier, the sum of its target risks in the two worlds is at least theta_1-theta_0; hence its worst-world risk is at least (theta_1-theta_0)/2.

**Proof.** On (theta_0,theta_1], the two true labels are opposite. For each fixed x there, a randomized binary prediction's two error probabilities sum to one. Integrating over that interval gives the inequality. OLD and unlabeled target observations are identical in law, so they cannot select the correct world. QED.

**PROVED corollary for P1.** OLD-only evidence cannot determine the realized new shift Delta or universally choose its oracle affine weight Delta^2/(Delta^2+v). Identical OLD evidence is compatible with Delta=0, where w=0 is optimal in P1, and an arbitrarily large shift, where substantial updating is necessary. This does not prohibit a useful OLD-calibrated rule under declared exchangeability, bounded-shift, or structural assumptions; it establishes why those assumptions are necessary.

**PRIOR ART.** Broader domain-adaptation impossibility results formalize the need for relationships between source and target laws: Ben-David, Lu, Luu and Pal, *Impossibility Theorems for Domain Adaptation*, AISTATS 2010, [primary proceedings page and PDF](https://proceedings.mlr.press/v9/david10a.html). P6 is a direct threshold-specific proof, and importantly its shift changes P(Y|X): it is a conditional/concept shift, not pure covariate shift. Reweighting the unchanged X distribution cannot identify it.

**Experiment row P6 (proposal).** Observable prediction: all OLD-only and unlabeled-target diagnostics are identical in the two worlds while best target thresholds differ. Model/data: paired worlds with shared OLD dataset and target score pool, two predeclared target thresholds. Exact statistic: sum of target errors minus the threshold-disagreement mass, and equality of the inputs supplied to model selection. Falsifier: negative slack under the identical-input construction. A method distinguishing the worlds must have used additional information, in which case it tests a different premise.

### Defensible calibration without NEW-outcome tuning

**PROVED limitation.** Random splits within one OLD campaign measure within-campaign prediction/sampling behavior; without a relationship assumption they cannot supply a coverage guarantee for a new campaign's shift radius D. Feature-space pseudo-campaigns may be useful stress tests, but are not automatically independent draws of campaign shifts.

**CONJECTURE / defensible protocol option.** If multiple genuinely distinct OLD campaigns exist and future campaigns are assumed exchangeable with them, estimate between-campaign threshold variability while accounting for estimation noise, then choose a conservative predeclared borrowing rule by nested leave-one-campaign-out evaluation. The calibration unit is the campaign, not a random row. Propagate uncertainty of the OLD anchor as well as the between-campaign spread. This option requires those campaigns and that assumption; it is not available merely by renaming OLD-405 folds.

**PROVED illustrative calibration formula under explicit assumptions.** If theta_0 is externally known, G independent historical campaign estimates obey Z_g-theta_0~N(0,tau^2+v_0) with known equal v_0, then S=sum_g(Z_g-theta_0)^2 satisfies S/(tau^2+v_0)~chi-square_G. Consequently

    tau_U^2 = max{0, S/chi-square_{alpha,G} - v_0}

is a one-sided (at least) 1-alpha upper confidence bound for tau^2. A normal-normal rule using this upper bound borrows less strongly than one using a smaller variance. If theta_0 is estimated from these same campaigns, the displayed degrees of freedom and future-prediction variance are not valid without modification. The formula is an illustration of assumption-explicit calibration, not an estimate from this repository.

**CONJECTURE / defensible protocol option.** With only one OLD campaign, fix a physically justified shift range or a transparent sensitivity grid *before* any target-outcome assessment; report performance over that grid without choosing D from NEW outcomes. Ordinary OLD cross-validation can choose a prediction penalty for OLD-like deployment, but cannot by itself justify a new-campaign robustness radius. If no finite shift constraint is supportable, report that fact and use a level-agnostic baseline instead of presenting a tuned radius as measured.

**KNOWN operational distinction.** A previously frozen algorithm may update its threshold using newly paid campaign labels and count them in its budget. That is online learning, not prohibited outcome tuning. Choosing the algorithm, its radius, or its penalty after observing its NEW endpoint is retrospective development. Because NEW-136 is already open, a new procedure selected using it remains development and needs a separate future campaign for independent transfer assessment.

## 7. Primary literature map and boundary of novelty

Every entry below is **PRIOR ART**, with only its directly relevant claim summarized. The independent proofs above are adaptations or illustrative constructions; no claim of research priority follows from this limited search.

| Source | What it supports | What it does not establish here |
|---|---|---|
| [Kearns & Singh 2002](https://people.eecs.berkeley.edu/~pabbeel/cs287-fa09/readings/KearnsSingh_E3_2002.pdf) | Simulation bounds connect model error to policy value. | A posterior-latent-target certificate for the actual GP fits without checking its kernels and targets. |
| [Golovin & Krause 2011](https://arxiv.org/pdf/1003.3967) | Adaptive monotonicity/submodularity yields adaptive-greedy guarantees; properties are law and objective dependent. | Automatic submodularity of posterior Hamming, NSD, or historical q20. |
| [Dasgupta 2004/2005](https://cseweb.ucsd.edu/~dasgupta/papers/greedy.pdf) | Realizable one-dimensional threshold learning by ordered binary search. | Robustness to arbitrary SPH rank violations or label noise. |
| [Ben-David et al. 2010](https://proceedings.mlr.press/v9/david10a.html) | Source/target relations are needed for domain adaptation; indistinguishable inputs can conceal different target tasks. | That all adaptation fails, or that covariate shift and threshold/concept shift are the same. |
| [Go & Isaac 2022](https://proceedings.mlr.press/v180/go22a.html), [full paper](https://proceedings.mlr.press/v180/go22a/go22a.pdf) | Robust expected-information-gain design using a KL ambiguity set and an affine relaxation; prior perturbations can change experiment ranking. | That logistic coefficient regularization equals this robust design objective, or that EIG superiority implies Hamming superiority. |
| [Sloman, Oppenheimer, Broomell & Shalizi, arXiv:2205.13698, version 2](https://arxiv.org/abs/2205.13698) | Model misspecification can interact with adaptive sampling to produce active-learning bias; studied linear and nonlinear examples. | A demonstrated causal explanation of the Week 16 rankings or a universal remedy. |
| [Barlas, Sloman & Kaski, arXiv:2511.07671](https://arxiv.org/abs/2511.07671) | Generalized-Bayes experimental design replaces likelihood updating with a loss-based construction; empirical robustness studied for outliers/noise misspecification. | Equivalence to standard penalized logistic regression or a proved threshold-transfer guarantee for M3. |

**PROVED / synthesis.** A coherent one-step value is only one component of a useful sequential policy: truth-aligned conditional predictions must persist along future histories. Physics can retain ranking information while its absolute level changes, so there is a coherent mathematical reason to retain an order prior and weaken a level prior. Neither observation proves that a new SPH acquisition method will win. The actionable research claim is a narrowly specified mechanism test with a frozen target, shift class, inference rule, acquisition path comparison, and falsifier.
