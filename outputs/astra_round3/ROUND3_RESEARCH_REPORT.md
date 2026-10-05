# Round 3 — Decision-relevant uncertainty for deterministic boundary learning

Research audit, 5 October 2026. Repository: iso0/active-level-set-week1-warmup, local checkout C:/Users/ozgur/Documents/thesis, inspected read-only. All new calculations and deliverables are outside the repository.

Tags apply to the entire paragraph or table row: **PROVED** means a mathematical statement with the stated assumptions and a proof in the appendix; **KNOWN/PRIOR ART** identifies an established principle or literature result; **COUNTEREXAMPLE** is an explicit refutation, with proof; **NUMERICALLY CHECKED** identifies computations or source-audited implementation facts, not new empirical confirmation; **CONJECTURE** identifies an interpretation or prediction requiring a new test. A proof does not establish that its assumptions hold for OLD or NEW.

## 1. Answer to the empirical puzzle

**NUMERICALLY CHECKED.** The principal Week 16 descriptive calculations reproduce. Across 908 nonsaturated physics-like states, margin's value divided by the best Gaussian/probit PEER value has median **0.4060359167**. Across all 1,197 states there is one declared saturated state. The fraction of evaluated truth-refit oracle headroom captured by PEER is approximately −0.059 in development, −0.0036 in curvedMono, 0.160 in rough, −0.083 in branin4d, and 0.098 in gpworld. Independent reconstruction is in verification_results.json and independent_week16_summary.csv.

**PROVED.** These observations are mathematically compatible. Optimizing a decision criterion under Q need not improve its true performance under P. Even when P=Q, a score derived for exact conditioning need not optimize the performance of an approximate refitting algorithm. Improving one-step Hamming value also need not improve multistep boundary distance.

**PROVED; interpretation requires revision.** Week 16 does not identify the residual oracle gap as exclusively, or primarily, missing model information. It compares a coherent current-Gaussian/probit experiment with truth-weighted fresh logistic Laplace refits. Its oracle additionally conditions on the realized truth field. The difference combines the latent law, observation channel, updating algorithm, and sometimes evaluation objective. A truth-knowing refit oracle is an algorithmic performance benchmark, not the coherent Bayes information value of a truth-knowing posterior.

**CONJECTURE.** Model formulation remains a plausible route to improvement, especially campaign-level calibration and the treatment of deterministic observations. The present evidence does not prove a model-level breakthrough, an impossibility for G3 + margin, or the superiority of a regularized physics mean. The immediate priority is to separate these explanations on common saved states before another policy comparison.

### 1.1 Independent numerical reconstruction

| Tag | Family | States | Median model ratio | Sum A / sum H | Mean PEER − margin, errors out of 400 | Median model/true rank correlation |
|---|---|---:|---:|---:|---:|---:|
| NUMERICALLY CHECKED | development | 432 | 0.4461 | −0.05873 | −0.09509 | 0.06785 |
| NUMERICALLY CHECKED | curvedMono | 384 | 0.4436 | −0.00355 | −0.00450 | 0.11245 |
| NUMERICALLY CHECKED | rough | 93 | 0.1690 | 0.16000 | 0.38710 | 0.04123 |
| NUMERICALLY CHECKED | branin4d | 96 | 0.3895 | −0.08255 | −0.31963 | 0.02743 |
| NUMERICALLY CHECKED | gpworld | 192 | 0.3591 | 0.09804 | 0.66136 | −0.06011 |

**NUMERICALLY CHECKED.** The report's positive gpworld mean contrast has a cluster-bootstrap interval that includes zero. The rough headroom fraction exceeds the gpworld fraction. Consequently “the gap becomes smaller in well-specified worlds” is a qualified descriptive observation about particular comparisons, not a universal ordering or an established positive PEER effect. Moreover gpworld matches the generating GP prior and logistic channel, while PEER uses a Gaussian posterior approximation and a probit future channel. It is not an exact P=Q benchmark for the entire inference/acquisition system.

**NUMERICALLY CHECKED.** The independent work recomputed aggregates and finite-law checks; it did not rerun the historical GP trajectories or reproduce every bootstrap interval. Source files and input tables used for the audit are SHA-256 recorded. Exact verification covered 1,819 rational binary joint laws, the negative-score counterexamples, initial pairwise equality in the sequential parity example, and 2,036 ranked binary sequences. Two thousand random joint-law pairs satisfied the sharper moment regret bound. Finite numerical checks supplement, and do not replace, the proofs.

## 2. Latent boundary, observations, and the meaning of uncertainty

**KNOWN/PRIOR ART.** Fix a domain, a latent field F, its sign T(x)=sign F(x), and its zero boundary Γ(F). A posterior over F expresses uncertainty about the deterministic but unknown field. A stochastic channel specifies a different object: O(x)|F, for example P(O=1|F)=σ(F) or Φ(F/τ). Conditional on F, T is deterministic while O can still be random. A deterministic physical oracle instead returns O=T. This distinction is standard GP classification and Bayesian experimental design; a logistic working likelihood alone does not demonstrate physical label noise. See [GPML, Chapter 3](https://gaussianprocess.org/gpml/chapters/RW3.pdf) and [Bickford Smith et al., 2025](https://arxiv.org/abs/2412.20892).

**KNOWN/PRIOR ART.** Within one declared stochastic model,

H(O)=E[H(O|F)]+I(O;F).

The first term is conditional observation entropy; the second is information about the latent field from that observation. Neither is automatically the value for estimating Γ. For latent-sign Hamming loss the relevant uncertainty is Bayes error; for squared boundary displacement it is a conditional variance of the boundary coordinate. These are different losses and different target random variables. BALD uses I(O;F); EPIG uses prediction-target information; neither equals Hamming PEER in general. See [Houlsby et al.](https://arxiv.org/abs/1112.5745) and [EPIG](https://proceedings.mlr.press/v206/bickfordsmith23a.html).

### 2.1 Exact binary value

**PROVED [L1].** For binary spins T,O∈{−1,+1}, m=E T and c=E TO,

e(T|O) = [1−max(|m|,|c|)]/2.

For fixed target weights w_i≥0, Σw_i=1, the expected reduction of coordinatewise Hamming Bayes risk is

V(j)=½ Σ_i w_i (|c_ij|−|m_i|)_+.

It is zero exactly when |c_ij|≤|m_i| for every positive-weight target. Thus a binary query has classification value precisely when some target's optimal decision can change with a strictly positive improvement. Information that changes confidence without changing the optimal classification action can have zero Hamming value.

**PROVED [R6; exact limiting criterion].** For a sequence of such experiments with fixed finite positive target weights, predictive-label margin tends to 1/2 exactly when E O_j→0. At the same time, latent-sign Hamming value tends to zero exactly when every positive-weight excess (|E T_iO_j|−|E T_i|)_+ tends to zero. For squared graph displacement, when E O_j→0, value tends to zero exactly when ∫w Cov(g(u),O_j)²du tends to zero. Thus balanced observed labels and vanishing decision value are compatible without requiring the boundary itself to be known.

**PROVED [L2].** For F∼N(μ,Σ), T_i=sign F_i, and O_j=sign(F_j+η_j), η_j∼N(0,τ²) independent,

m_i=2Φ(μ_i/s_i)−1,

c_ij=4Φ₂(μ_i/s_i, μ_j/g_j; ρ_ij)−2Φ(μ_i/s_i)−2Φ(μ_j/g_j)+1,

g_j²=s_j²+τ², ρ_ij=Σ_ij/(s_i g_j).

This makes PEER exact for this current Gaussian/probit experiment. Week 16 sets τ²=8/π. It is not exact posterior inference for a logistic GP. Degenerate variances are handled by limits or deterministic signs.

### 2.2 Exact failure of a universal margin guarantee

**PROVED [L3].** At a centered Gaussian query, predictive observation probability and latent-sign probability both equal 1/2, while

V_self=arctan(s/τ)/π.

For fixed τ>0 this tends to zero exactly as s/τ→0. The latent sign still has one bit of entropy for every positive s. What vanishes is the information supplied by one fixed-noise observation, not sign uncertainty itself.

**COUNTEREXAMPLE [C1].** Two independent coordinates suffice. Let F_a=εS, with S a fair sign, and F_b=MU, with E U=2δ>0. Let a(f)=E[O|F=f] be the odd logistic response tanh(f/2), or the probit response 2Φ(f/τ)−1. If 0<2δ<a(M), observed-label margin uniquely chooses a, but its ratio to the best one-step latent-sign value is

a(ε)/[a(M)−2δ] → 0.

Cross-coordinate values vanish by independence. This uses the same two points as targets and queries, equal weights, and exact Bayesian updating. A Gaussian version takes F_a∼N(0,ε²), F_b∼N(δ,S²) with small fixed δ>0. Thus the sharp universal nonnegative competitive constant in this class is **zero**. Random tie-breaking cannot fix this strict-margin example.

**COUNTEREXAMPLE [C2, scale invariance].** Replacing a field G by F_c=cG, c>0, preserves every sign, every sign-joint law and the entire zero boundary. Under a fixed logistic/probit channel, E[T_i O_j]→0 as c→0, so every finite-pool Hamming query value tends to zero. For any fixed loss in [0,1], its Bayes information value also tends to zero: comparison with an independent fair coin bounds it by E|P(O=1|G)−1/2|, at most c E|G_j|/4 for logistic and c E|G_j|/(τ√(2π)) for probit. This can occur while geometric boundary uncertainty remains unchanged.

**PROVED.** Small geometric uncertainty is a separate sufficient reason for small geometric value: expected reduction cannot exceed the current Bayes risk. For the one-dimensional random threshold F(x)=x−εZ, squared boundary risk is ε²Var(Z), while at x=0 and symmetric Z the predictive margin is 1/2. Conversely F_c(x)=c(x−Θ) has the same boundary Θ for every c: latent variance shrinks, but geometric variance does not. The physically relevant local scale, where a nonzero normal derivative exists, is uncertainty in field value divided by the normal slope, not field standard deviation alone.

### 2.3 Positive guarantees: what must be added

**PROVED [L4].** Noise by itself does not destroy the Round 1 bound. If the N unit-weight targets are also the queries and O_j=T_jB_j, with B_j independent of the whole sign field and common E B_j=α>0, then observed-label margin retains the sharp bound

V(margin) ≥ V(opt)/(N−1).

The proof and sharpness construction are in the appendix. The Gaussian fixed-noise example fails this common sign-reliability assumption because attenuation depends on latent magnitude.

**PROVED [R1].** A more general, weaker-useful sufficient condition is observable self-information. Put b_j=min(P(O_j=1),P(O_j=−1)). Every normalized binary-target Hamming value satisfies V(j)≤b_j. Suppose every candidate is a positive-weight target and its self-value satisfies v_jj≥α b_j for α>0. Then an observed-label margin choice m satisfies

V(m)≥α w_m max_j V(j)≥α w_min V(opt).

Only the selected candidate's self-information inequality is needed. This is not claimed to be the uniquely weakest assumption: “weakest” has no invariant meaning without specifying an admissible model class. It gives a computable sufficient condition and identifies why missing target overlap or vanishing reliability removes the guarantee. At all-centered Gaussian candidates, a lower bound on s_j/τ gives such an α. Away from centering, a variance lower bound alone is insufficient; the positive-part threshold must also be checked.

**COUNTEREXAMPLE.** If targets are disjoint from candidates, a fair uninformative candidate can be uniquely most uncertain while a slightly biased candidate reveals the target. Even noiseless observations then give ratio zero. A positive guarantee requires a relationship between query uncertainty and information about the evaluation targets, not merely certainty that the queried point is learned.

**NUMERICALLY CHECKED.** The observed Week 16 decoys do show lower self-value in several families, but they do not uniformly instantiate s→0. Reconstructing μ from the stored margin probability and s, then integrating the declared probit channel, gives median decoy self-values 0.00587 (curvedMono), 0.03569 (development), 0 (rough), 0.14389 (branin), and 0.20407 (gpworld). These are unweighted single-target values, not the total reference-cloud score. Centered arcsine values at the same s would be different and cannot refute this evidence. Neither low self-value nor low s establishes that the true geometric boundary is already localized.

## 3. When coherent look-ahead improvement transfers from Q to P

**PROVED [L5].** Fix the same target set, weights, query experiments, and terminal Hamming action space for P and Q. Let m_i^R=E_R T_i and c_ij^R=E_R T_iO_j. Define

M=Σw_i|m_i^P−m_i^Q|, C_j=Σw_i|c_ij^P−c_ij^Q|,

D_j=Σw_i max(|m_i^P−m_i^Q|, |c_ij^P−c_ij^Q|).

Then |V_P(j)−V_Q(j)|≤(M+C_j)/2. The P-value regret from choosing the Q-optimal query is at most M+max_j C_j. This controls query selection with a P-Bayes terminal action.

**PROVED [L5, stronger terminal-decision form].** For a binary rule g_i(O), write α_i=[g_i(+1)+g_i(−1)]/2 and β_i=[g_i(+1)−g_i(−1)]/2. Its terminal risk is

F_P(g,j)=½Σw_i[1−α_i m_i^P−β_i c_ij^P].

Because one of α_i,β_i is zero and the other is ±1, |F_P(g,j)−F_Q(g,j)|≤D_j/2. If j_Q and its terminal rule jointly optimize Q, while j_P and its rule optimize P, their true terminal-risk regret is at most

(D_jQ+D_jP)/2 ≤ max_j D_j ≤ M+max_j C_j.

Thus if M≤ε_m and max C_j≤ε_c, regret≤ε_m+ε_c, now including the Q-based terminal decision. These ε's are **spin-moment errors**, not unscaled probability errors.

**PROVED [L5, improvement certificate].** Let γ=V_Q(j_Q)−V_Q(j_margin). Using the corresponding Q-Bayes terminal rules, true improvement is at least

γ−(D_jQ+D_jmargin)/2.

For actual refitted decisions, subtract ζ_jQ+ζ_jmargin, where ζ_j is their P-weighted disagreement probability with the coherent Q decision, summed over targets. This isolates three statements: a positive model-internal gap γ; sufficiently small decision-relevant law error D; and a sufficiently faithful updater ζ. A large γ alone establishes only the first.

### 3.1 Marginals, dependence, and the observation channel

**PROVED [L6].** Write n_j^R=E_R O_j and k_ij^R=Cov_R(T_i,O_j). Since c_ij=m_i n_j+k_ij,

|δc_ij|≤|δm_i|+|δn_j|+|δk_ij|.

If both types of spin marginals have error at most ε_m and the weighted covariance discrepancy is at most ε_c per query, the preceding terminal regret is at most 2ε_m+ε_c. This is a direct marginal-versus-dependence version, with explicit constants.

**PROVED [L6].** To separate latent structure from observation modeling, let μ_j^R be the distribution of F_j, h_ij^R(f)=E_R[T_i|F_j=f], and a_j^R(f)=E_R[O_j|F_j=f]. Under a local channel,

|δc_ij| ≤ 2 TV(μ_j^P,μ_j^Q)
             + E_Q|h_ij^P(F_j)−h_ij^Q(F_j)|
             + E_Q|a_j^P(F_j)−a_j^Q(F_j)|.

These are respectively candidate latent-marginal, conditional target-structure, and channel errors. Conditional versions must be defined on the compared supports. This decomposition explains why calibrated sign probabilities cannot substitute for a model of how the observation depends on latent magnitude.

**PROVED [R2].** Expected excess log score for the actual binary target-observation joint law is KL(P_ij||Q_ij). Pinsker gives

D_j≤Σw_i sqrt(2 KL(P_ij||Q_ij))≤sqrt(2Σw_i KL(P_ij||Q_ij)).

Hence uniform weighted pair KL K bounds terminal regret by sqrt(2K). The statistic needed is expected **excess** log loss at common states and actual target/candidate pairs. Raw pair log loss is not KL, and a correlation of average log loss with endpoint performance is not this bound.

**COUNTEREXAMPLE [C3].** Minimal marginal failure uses one fair binary target and two observations. Under P, O_a is an independent fair sign and O_b=T; under Q their roles swap. Every target and observation marginal is perfectly calibrated. Q uniquely selects a, whose true value is zero; P selects b, whose value is 1/2. In a Gaussian/probit version, swap two independent centered latent standard deviations (1,ε) between P and Q. The *entire latent-sign joint law*, as well as every observed-label marginal, is then identical, but the useful query swaps. Good marginal calibration alone cannot certify acquisition performance.

**NUMERICALLY CHECKED.** Week 16 synthetic joint calibration scores (T_i,T_k), real-data pair diagnostics score observation-style pairs, and PEER needs (T_i,O_j). These diagnostics are useful but different. Their model variants also follow different acquisition histories. The near-perfect correlation between joint and marginal log-loss rankings therefore does not refute the role of dependence. Indeed [Wang, Sun & Grosse, 2021](https://proceedings.mlr.press/v130/wang21g.html) explicitly report that joint log likelihood can be dominated by marginal quality and introduce more targeted predictive-correlation diagnostics.

### 3.2 The refit-oracle identity

**PROVED [L7].** For any fixed prequery predictor a_0 and updater A_j(O), let b_P be its initial excess risk over the P-Bayes action and e_P(j) its expected postquery excess risk. Then

G_P^A(j)=V_P(j)+b_P−e_P(j).

Accordingly the residual between its oracle query and j_Q is

max_j[V_P(j)−e_P(j)]−[V_P(j_Q)−e_P(j_Q)].

It is not generally V_P(opt)−V_P(j_Q). If P conditions on the full realized truth field, V_P(j)=0 for every query, and the whole refit landscape is the updater's error relative to that truth.

**PROVED.** A good decision-relevant model can still yield low rank correlation when all values are tiny. Conversely a large correctly matched absolute regret gives a lower bound on an upper-bounding discrepancy term. The report's use of “contrapositive” from poor rank agreement to deficient joint information is invalid without a quantitative regret, matching targets/updates, and the corresponding error inequality.

## 4. Sequential decisions and accumulated misspecification

**KNOWN/PRIOR ART.** Retain Round 2's G_margin(B)≥(B/N)G_opt(B), and the sharp 4/5 at N=3,B=2, only in their fixed-pool, noiseless, full-pool Hamming, ideal-update setting. They do not apply unchanged to disjoint targets, noisy latent observations, approximate updates, or geometric losses. This round does not claim a new sharp general finite-(N,B) constant.

**PROVED [S1–S3].** For a fixed adaptive policy π and loss in [0,1], define ε_t(h,a) as TV between P and Q observation kernels at the reached history, and δ(h) as TV between terminal target posteriors. Then

|R_P(π)−R_Q(π)|≤Γ_π
=min{1, Σ_t E_P^π ε_t(H_t,A_t)+E_P^π δ(H_B)}.

For weighted Hamming, δ can be replaced by the weighted difference between terminal target-label probabilities. If the Q policy is β-optimal under Q, its true regret against the P-optimal policy is at most β+Γ_πQ+Γ_πP, capped by 1. Uniform bounds ε_t≤e_t, δ≤d yield β+2(Σe_t+d); a full-TV coupling sharpens Γ to 1−(1−d)Π_t(1−e_t).

**PROVED.** Error is needed at the future histories of the policies being compared. Calibration only along old margin trajectories cannot certify a policy that visits different histories. Initial pairwise correctness is also insufficient: higher-order structure becomes conditional dependence after observations. The KL chain-rule alternative is Γ_π≤sqrt(J_π/2), where J_π sums reached-history observation KL and terminal target-posterior KL. These are simulation-lemma specializations, not novelty claims.

**COUNTEREXAMPLE [C4].** Let independent fair signs A,B define target T=AB; query sensors A,B,C, where C=TE and P(E=1)=1/2+η. With budget two, myopic exact EER first queries C and gains only η overall. Querying A then B reveals T, gaining 1/2. The ratio 2η tends to zero. No tie-breaking randomization among current greedy maxima repairs this strict first choice. The initially useless B has value 1/2 after A, violating adaptive submodularity.

**COUNTEREXAMPLE [C4, model-error extension].** Let Q instead make T,A,B independent while retaining C=TE. P and Q agree on every initial first- and second-order law and on every observation transcript through two queries. Yet after A,B their target posteriors differ by TV=1/2. Therefore an observation-kernel-only sequential bound would be false. The terminal-target term is indispensable.

**KNOWN/PRIOR ART; conditional theorem.** If the actual utility and law satisfy adaptive monotonicity and adaptive submodularity, the usual greedy guarantee is at least 1−1/e of the optimal adaptive gain. The relevant hypotheses must be checked for the actual loss. They are not implied by Bayesian coherence or by a GP covariance. Approximate-submodularity results similarly require a positive, verified ratio; the parity example has zero initial marginal gains and defeats a universal positive ratio. See [Golovin & Krause](https://arxiv.org/abs/1003.3967) and [Fujii & Sakaue](https://proceedings.mlr.press/v97/fujii19a/fujii19a.pdf).

**PROVED [R3, restricted positive result].** Partition a noiseless target pool into blocks whose labels are identical within each block and independent between blocks. Let W_b be total target weight and u_b its sign Bayes error. One query resolves its entire block; conditional expected gains are the fixed numbers W_b u_b. EER sorts these numbers and is optimal for every budget. Margin sorts u_b and can be substantially worse when block weights differ. With two independent fair singleton decoys and an independent M-point block of error 1/2−η, B=2 margin gains 1/(M+2), whereas EER gains [M(1/2−η)+1/2]/(M+2), provided M(1/2−η)>1/2. Thus correct specification does allow a multistep EER advantage; it is not universally guaranteed.

**PROVED.** For one known law, randomization cannot improve the optimum over finite decision trees: risk is affine in randomized mixtures, so some deterministic policy is at least as good. Randomization can protect a minimax selector against an unknown adversary or enforce exploration, but that is a different optimization problem. Comparing one-step policies at one shared state does not establish domination of their later, different histories.

## 5. Physics as level, physics as order, and robust shrinkage

**PROVED [P1–P4].** An exact transfer model is T(x)=sign(h(x)−θ_c), with campaign-specific θ_c and a stable score direction. An OLD level θ_0 can fail after a threshold shift although the ranking remains perfect. For sorted finite scores, exact monotonicity permits balanced binary search over N+1 threshold positions; after B queries at most ceil((N+1)/2^B) remain. A median estimate has worst-case Hamming error at most floor(ceil((N+1)/2^B)/2)/N. A fixed OLD rank k_0 instead has error |k−k_0|/N. Thus retaining order can cost in-domain efficiency and improve worst-case transfer. These are standard threshold-search facts specialized to the thesis question.

**PROVED [P1–P3].** In the exact normal-location experiment Z=θ_0+Δ+ε, ε∼N(0,v), consider θ̂_w=θ_0+w(Z−θ_0). Its squared threshold risk is

R_Δ(w)=(1−w)²Δ²+w²v.

For |Δ|≤D the best affine weight is w_D=D²/(D²+v), with worst-case risk D²v/(D²+v). This is only affine minimax on a bounded parameter interval: clipping to that interval improves the rule.

**KNOWN/PRIOR ART; PROVED specialization.** Over the prior ambiguity class {ν:E_νΔ²≤D²}, the same rule is minimax over **all** measurable estimators. The Gaussian shift prior N(0,D²) is least favorable, and its Bayes posterior variance equals D²v/(D²+v). Thus robust-Bayes shrinkage is a valid mathematical interpretation when the shift parameter, likelihood, loss, and ambiguity class are specified. This classical normal-mean result is closely documented in [Johnstone's Gaussian estimation text](https://mathweb.ucsd.edu/~jbradic/math281a/Johnstone.pdf); the campaign interpretation is a specialization.

**PROVED.** Without a finite shift restriction, current-only Z is minimax with risk v; every fixed w<1 has unbounded worst-case squared bias. Stronger allowable shift therefore requires weaker borrowing of the old level. This does not say that discarding physics order is desirable. If design changes only v, robust and ordinary variance-minimizing designs rank queries identically: the shrinkage theorem is an inference result, not an acquisition breakthrough.

**PROVED [P5].** Attenuating the entire physics mean λ(b_0+b_1h), λ>0, does **not** move its zero threshold −b_0/b_1. A free campaign intercept, a threshold-shift parameter, or a sufficiently flexible discrepancy is needed to change the level. Mean attenuation can change confidence and the residual fit, but cannot by itself correct a pure level shift.

**NUMERICALLY CHECKED.** Original M3 fits a nearly unpenalized physics logistic mean to supplied training labels (C=10^6), then fixes that mean during the discrepancy GP fit; its residual standard deviation is capped at 1. Week 16's physics mean uses C=1 on standardized score and currently revealed labels, with a zero-mean one-class fallback. “Anchoring” therefore has three meanings that must be distinguished: a learned within-campaign level, freezing that learned level inside stage two, and transferring an OLD-fitted level unchanged. The Week 16 variant is not simply the original M3 with one regularization knob changed.

**KNOWN/PRIOR ART.** L2 logistic regularization has a coefficient-MAP interpretation under a specified prior and likelihood normalization. It does not automatically implement an ambiguity class over campaign shifts, account for fitted-mean uncertainty, or give a robust design theorem. Two-stage plug-in trend/residual fitting is not the same posterior as joint hierarchical inference with one likelihood. [Go & Isaac's robust experimental design](https://proceedings.mlr.press/v180/go22a.html) is a distinct, explicit ambiguity-set construction.

**CONJECTURE.** A model with an uncertain campaign intercept/threshold, stable score direction and a flexible residual can reduce transfer bias relative to a strongly fixed level. Regularizing a near-separated current-campaign logistic trend may also improve stability. These mechanisms should be distinguished experimentally; neither has been established as an improvement over G3 + margin.

### 5.1 Choosing strength from OLD

**PROVED [P6].** OLD data and an unlabeled NEW score distribution cannot identify unrestricted NEW threshold shift. Two worlds can have identical OLD data and identical NEW scores but target thresholds θ_0<θ_1. Every OLD-only classifier then has summed target error across the two worlds at least the probability mass between the thresholds, hence worst-world error at least half that mass. This is conditional/concept shift, not pure covariate shift; importance weighting alone cannot identify it.

**CONJECTURE; protocol proposal.** If genuinely separate historical campaigns are available and future campaigns are assumed exchangeable with them, nested leave-one-campaign-out evaluation can set a borrowing rule before NEW outcomes are inspected. A shift-radius choice must account for the uncertainty of campaign threshold estimates and the OLD anchor. With only one campaign, a physically justified radius or a predeclared sensitivity range is defensible; row-level OLD cross-validation does not establish robustness to arbitrary campaign shifts.

**PROVED [P6, calibration example].** If the external anchor is known and G independent campaign estimates satisfy Z_g−θ_0∼N(0,τ²+v_0), with known v_0, then max{0,Σ_g(Z_g−θ_0)²/χ²_{α,G}−v_0} is an at-least-(1−α) upper confidence bound on τ². Its assumptions and degrees of freedom do not survive estimating θ_0 from the same observations without modification. This is an example of principled strength selection, not an estimate from OLD-405.

**PROVED; scope.** A frozen algorithm may update its threshold using newly paid campaign labels. That is online learning. Selecting its penalty or radius after comparing NEW endpoints is retrospective development. A candidate chosen from the already opened NEW-136 requires another campaign for independent transfer evidence.

## 6. Rare-class discovery is a different decision problem

**PROVED [D1].** Time to physically observe both classes, T_both, is a stopping cost. Subsequent boundary risk is a loss on the posterior state at release. Neither determines the other.

**COUNTEREXAMPLE [C5; equal final budgets].** For any k≥1, take k+1 independent fair boundary bits, represented as heights 0 or H on separated columns. One binary query reveals one column's bit. There are also two paid anchors with fixed opposite labels; the startup contract requires actual observations. Querying the anchors is globally optimal for T_both, which equals 2. After k further, optimally chosen queries, at total budget k+2, at least one independent boundary bit remains unknown. Optimal expected Hausdorff risk is H/2.

**COUNTEREXAMPLE [C5 continued].** Instead query two geometric bits. If they differ, discovery finishes at 2; if they agree, query the opposite anchor and finish at 3. Expected discovery time is only 2.5. At the same final budget k+2 this policy can reveal every boundary bit, giving zero geometric risk. The ratio of residual risks is unbounded. On a fixed unit-height domain the contrast is 1/2 versus zero. This construction includes optimal continuation for the fast-discovery policy, so the failure is not caused by giving it a deliberately poor refinement rule.

**PROVED [D2].** If two startups reach the same complete sufficient state by budget b with probability at least 1−δ and use the same continuation and random seed, their later paths coalesce on that event. Any endpoint with range length L differs in expectation by at most Lδ. For normalized AULC weights λ_t and noncoalescence probabilities δ_t, the bound is LΣλ_tδ_t. Same query sets suffice only for an order-invariant model and continuation with no hidden differing state.

**NUMERICALLY CHECKED.** Week 16 reports raw first-both means 4.43 for adaptive physics, 4.83 for maximin and 11.32 for uniform startup; the exact poolwise uniform benchmark is approximately 10.6355. Week 12's minimum-eight paid release costs are different quantities: 8.07 versus 8.47. The two adaptive/maximin startup arms have identical B16 query sets and predictions in 94/100 pools; only six can contribute to a later difference if the continuation fully coalesces. This gives a descriptive upper bound 0.06 on a later [0,1] endpoint mean difference, not a prediction of the observed −0.000313 q20 AULC contrast.

**CONJECTURE.** The Week 12 combination of a shorter discovery tail and little downstream difference is consistent with early paths coalescing and with tail queries mainly revealing easy class anchors. A diagnostic should compare the full release posterior, geometric information and coalescence budget, not only T_both. The six noncoalescing paths do not identify a population mechanism.

### 6.1 Physics guarantees that survive imperfect order

**KNOWN/PRIOR ART; PROVED finite-pool calculation [D3].** For a fixed pool with r designated rare items among N, uniform sampling without replacement has first-hit survival C(N−r,k)/C(N,k) and mean (N+1)/(r+1). For a fixed tail subset of size M containing s rare items, uniform sampling within that subset has survival C(M−s,k)/C(M,k) until exhaustion and mean (M+1)/(s+1), when s>0. Enrichment s/M≥r/N gives stochastic improvement over full-pool uniform first discovery. This concerns a designated class, not both classes without an observed anchor.

**PROVED [D4].** For a deterministic tie-broken ranking, let V count common-before-rare inversion pairs and D the first rare rank. Then

r(D−1)≤V, hence D≤1+floor(V/r)
=1+floor((1−AUC)(N−r)).

The bound is tight when V=kr: place k common items, then all r rare items, then the remaining common items. A top-M subset containing s rare items also satisfies V≥(M−s)(r−s). In particular V<Mr guarantees a rare item among the first M. These are rank guarantees, not label-propagation rules.

**PROVED; comparison condition.** Against a comparator guaranteed to discover by rank d, a physics ordering cannot take longer unless V≥rd. The converse is false: many inversions can occur after the first rare item. There is no universal numerical violation count for “worse than generic geometry/margin,” because their discovery cost and subsequent risk depend on the geometry and posterior. An exact count is available only after specifying that comparator and loss.

**COUNTEREXAMPLE [C6].** Stochastic monotonicity is weaker than deterministic order. Independent labels with positive probabilities 0.49 and 0.51 are stochastically increasing but have an inversion with probability 0.2401. One contaminated point relative to a deterministic threshold, in the sequence (1,0,…,0,1), can make hard upward propagation mislabel N−2 points. This is one point violation but N−2 pair inversions. Even one adjacent inversion pair suffices to invalidate a zero-error elimination guarantee. AUC does not authorize inferred labels.

**PROVED.** Tail enrichment has no boundary-learning consequence without an information/geometry condition: all enriched tails can consist of easy interior anchors while relevant boundary bits remain independent. Under exact noiseless monotonicity, by contrast, both-class discovery creates a valid bracket and binary search gives geometric/threshold guarantees if score-to-position regularity is supplied.

**NUMERICALLY CHECKED; scope correction.** Week 12 adaptive startup selects an extreme after a failed B8 history; it is not uniform sampling in a fixed tail. Week 16's unconditional enrichment verifies a useful property but does not make the uniform-tail theorem an exact causal explanation of that adaptive policy. Count the realized conditional remaining-tail ranks or posit and test a conditional success model.

## 7. A boundary objective must specify the geometry it values

**KNOWN/PRIOR ART.** Bayesian SUR already supplies the general acquisition principle:

R(D)=inf_a E[L(a,Γ)|D],  Δ(j|D)=R(D)−E[R(D,O_j)|D].

The task is to choose and justify L, its target measure and action space, then compute this objective coherently. Changing a score's name to “boundary risk” does not establish geometric alignment. Deterministic computer-experiment SUR, contour design and excursion-set uncertainty predate this work; see the literature table.

| Tag and estimand | Bayes decision / acquisition | Required information | Density and geometric limits |
|---|---|---|---|
| PROVED [G1–G2]: integrated vertical displacement of graph boundary Γ_g={(u,g(u))}, loss ∫w(u)|a(u)−g(u)|du | Pointwise posterior median; expected reduction of integrated posterior absolute deviation | Conditional root distributions, or all threshold-event/observation pairs along each vertical line | Base measure w is explicit; equals volume Hamming only for vertically constant density. Requires a single graph in each line |
| PROVED [G2]: squared graph displacement ∫w(a−g)² | Posterior mean; Δ₂(j)=∫w Var(E[g|O_j]) | Boundary-coordinate/observation joint law; for binary O, Δ₂=∫w Cov(g,O)²/Var(O) | Not Hausdorff; large local errors receive squared penalties. Vertical coordinates must have physical meaning |
| PROVED [R4]: weighted graph-edge disagreement | Bayes cut estimate minimizes expected weighted edge error; independent edge modes are valid only if action constraints allow them | Current edge moments E[T_iT_k]; one binary look-ahead additionally needs E[T_iT_kO_j] | Edge lengths, graph construction and sampling density matter; counts of cuts do not measure displacement |
| KNOWN/PRIOR ART: fixed surface-weighted classification loss | Weighted Hamming Bayes action and weighted EER | Fixed weights and target/observation pairs | Weights must be fixed before the fantasy outcome or defined as part of a single loss. Unknown true surface weights require a posterior model |
| PROVED / finite decision formulation: Hausdorff loss | Fréchet Bayes action argmin_a E H(a,Γ); optimize conditional risk for acquisition | Generally joint boundary samples/distribution; pairwise binary label laws are insufficient | Independent of input multiplicity as a geometric metric, but its finite approximation requires coverage and regularity |
| KNOWN/PRIOR ART: fixed-tolerance surface Dice deficit | Bayes action for E[1−NSD_τ(a,Γ)], then its expected decrease | Joint surface law, fixed physical metric and τ, conventions for empty surfaces | Tolerance-dependent; not identical to a ratio of expected cut counts |

### 7.1 Exact continuous bridges

**PROVED [G1].** For two graph regions A_g={(u,z):z≤g(u)} and A_a with density q,

μ_q(A_g△A_a)=∫|∫_{g(u)}^{a(u)}q(u,z) dz|du.

If q(u,z)=w(u), this is exactly integrated weighted vertical displacement. If 0<c≤q≤C between graphs, it is bounded between c||g−a||₁ and C||g−a||₁. Thus Hamming can be a legitimate geometric surrogate under explicit conditions; arbitrary campaign density is not uniform surface weighting.

**PROVED [G3–G4].** If two graph functions share a compact base and Lipschitz constant L,

||g−a||∞/sqrt(1+L²) ≤ H(Γ_g,Γ_a) ≤ ||g−a||∞.

On U=[0,1]^m, if g−a is K-Lipschitz and w≥w_min>0, small integrated absolute error controls the sup error with exponent 1/(m+1). Explicitly, for M=||g−a||∞≤K√m,

M ≤ [2^(m+1) K^m m^(m/2) ∫w|g−a| / w_min]^(1/(m+1)).

This exponent is attained in order by narrow Lipschitz cones. Finite quadrature on cells of diameter h has error at most (L_g+L_a)h for probability weights. Sampled graph-cloud Hausdorff error is at most h[sqrt(1+L_g²)+sqrt(1+L_a²)].

**PROVED [G5].** For a C² surface with an injective normal tube, uniformly bounded curvatures, and a corresponding normal displacement δ(s) with no added components, classification disagreement mass equals ∫_Γ q(s)|δ(s)|dA up to a remainder bounded by a constant times ∫δ²dA. The appendix gives the Jacobian formula and constant. This makes the input-density dependence explicit. Uniform surface displacement and deployment-distribution classification answer different questions.

**COUNTEREXAMPLE [C7].** A finite set of labels cannot determine an unconstrained continuous boundary: an unsampled interval admits multiple thresholds agreeing on every point; smooth narrow bumps between sample sites give the higher-dimensional counterpart. Without a common derivative/regularity bound and coverage condition, no finite-pool surrogate can universally guarantee continuous geometric recovery.

**COUNTEREXAMPLE [C8].** Two parallel boundaries separated by d have Hausdorff distance d, but their surface Dice at tolerance τ jumps from 1 to 0 as d crosses τ. Smooth graphs k^−1 sin(k²u) converge in displacement to zero while their lengths diverge. Boundary area, average displacement, Hausdorff distance, tolerance-based NSD and q20 are not interchangeable. Graph cut disagreement for two separated parallel cuts likewise does not encode their separation once the cuts cease to overlap.

**COUNTEREXAMPLE [C9; higher-order geometric information].** On three separated columns, boundary heights B∈{0,1}³ have two laws:

| B | P+ numerator / 70 | P− numerator / 70 |
|---|---:|---:|
| 000 | 34 | 22 |
| 001 | 0 | 12 |
| 010 | 0 | 12 |
| 011 | 12 | 0 |
| 100 | 0 | 12 |
| 101 | 12 | 0 |
| 110 | 12 | 0 |
| 111 | 0 | 12 |

**PROVED [G7].** All first and pairwise label laws agree, yet observing B₁ has exact Hausdorff Bayes value 11/70 under P+ and zero under P−. Columns are sufficiently separated that Hausdorff distance is ||a−B||∞, and estimates may use any heights in [0,1]³. The Bayes risk of a cube-vertex law is min(1/2,1−largest atom), giving the stated values. Thus the insufficiency is not an artifact of forcing the estimate to be a posterior sample. A fully specified latent Gaussian law is a separate matter: its continuous mean/covariance determine its full joint law.

**CONJECTURE; computational candidate.** A posterior over boundaries represented as graphs, where physically defensible, permits loss-specific coherent acquisition by posterior sample reweighting after candidate labels. The posterior representation, admissible geometry and loss must be fixed first. No result here establishes that this procedure beats G3 + margin, or that a general SPH boundary is a single graph.

## 8. Week 16 cross-audit and minimal fixes

**NUMERICALLY CHECKED.** Source inspection covered week16_peer.py, week16_headroom.py, week16_cells.py, week16_validate.py, week16_calibration.py, week16_real.py, week15_ebr.py, the Week 16 report/theory/erratum and the cited result tables. The verdicts below distinguish exact mathematics from implementation/evidence scope.

| Item | Verdict | Tagged reason | Minimal fix |
|---|---|---|---|
| General binary-observation lemma | CORRECT | PROVED: exact under binary target/observation and unconstrained coordinatewise Hamming actions | State weights, target set, and conditioning law |
| PEER derivation | CORRECT WITH CONDITIONS | PROVED: exact for a current Gaussian law and independent Gaussian future noise; logistic posterior and refits are approximations | Call it Gaussian/probit coherent one-step EER |
| W16-1 zero margin ratio | CORRECT WITH CONDITIONS | COUNTEREXAMPLE: ratio zero under variable effective sign reliability; noise alone is insufficient | Add common-BSC positive theorem and target-overlap qualification |
| “This is the regime of every GPC in the thesis” | GAP | PROVED / NUMERICALLY CHECKED: a stochastic working likelihood is not evidence of stochastic physical observations | Distinguish P-deterministic oracle from Q-stochastic channel |
| “Pinned latent, hence boundary known” | GAP | COUNTEREXAMPLE: positive rescaling changes latent sd without changing boundary law; centered sign entropy stays maximal | Report root-position uncertainty or sd/normal-gradient plus regularity |
| All low-ratio picks are aleatoric decoys / not extrapolation | GAP | NUMERICALLY CHECKED: lower self-values support part of the story; geometry, covariance, targets and hull baselines remain confounded | Use common-state self/cross-value decomposition and explicit alternative explanations |
| Coherent Bayes expected risk reduction cannot be negative | CORRECT WITH CONDITIONS | PROVED: fixed loss, fixed action space, actual Bayes action and one coherent update | State these conditions; expectation, not every realized outcome |
| Negative VSUR + measured martingale discrepancy | CORRECT WITH CONDITIONS | NUMERICALLY CHECKED: validates failure of the implemented Hamming refit construction as one coherent experiment | Compare exact same-law conditionals; report numerical tolerances |
| Negative EBR/EBR-D implies incoherent updating | WRONG | COUNTEREXAMPLE: plug-in marginal-sign cuts and ratios of expectations can increase under exact conditioning | Separate action suboptimality/functional nonconcavity from update error |
| Graph-cut Dice ratio equals geometric surface-Dice/NSD deficit | WRONG as an identity | COUNTEREXAMPLE: two nonoverlapping parallel cuts can have the same cut disagreement at different physical separations, while fixed-tolerance surface Dice changes | Name the graph estimand; prove a separate geometric approximation under an explicit resolution/tolerance regime |
| Headroom identity H=A+(H−A) | CORRECT WITH CONDITIONS | PROVED: algebra on evaluated candidates, targets and specified updater | Identify candidate cap and all components of utility |
| H−A identifies inaccessible truth/model information | WRONG as identification; GAP as hypothesis | PROVED: updater-excess-risk decomposition; truth-conditioned Bayes value is zero | Say PEER did not recover the truth-weighted refit oracle's gain |
| Pairwise calibration test directly tests the regret theorem | GAP | PROVED / NUMERICALLY CHECKED: required pair is (T_i,O_j); tested pairs and states differ | Same states, correct target-query pair law, proper excess score |
| “Corollary operates in its contrapositive” | WRONG | PROVED: poor rank correlation does not imply large absolute regret or certify moment error | Use a matched regret bound and quantified discrepancy |
| Saturation example in THEORY_WEEK16 | WRONG numerical illustration | NUMERICALLY CHECKED: 0.002 is above the declared 10^−6 threshold; actual flagged state is B48 | Replace stale B24 illustration or call it small-but-nonsaturated |
| Martingale gap “max 4.3” | CORRECT WITH CONDITIONS | NUMERICALLY CHECKED: 4.268 is maximum of state medians; candidatewise maximum is 7.158 | Name the aggregation explicitly |
| Enrichment exactly explains adaptive startup | GAP | PROVED: fixed uniform-tail law differs from history-conditioned extreme selection | Add conditional-rank analysis and maintain discovery/refinement distinction |
| Model formulation matters more than acquisition sophistication | GAP as established ordering; CONJECTURE as research direction | PROVED / NUMERICALLY CHECKED: current audit has not controlled channel, updater and loss simultaneously | Run discriminating factorial tests; avoid causal ranking of bottlenecks |
| Regularized physics mean is an established replacement | WRONG if asserted | NUMERICALLY CHECKED: descriptive candidate, distinct fitting architecture | Retain candidate status and require a matched future transfer test |
| Laplace convergence correction | CORRECT WITH CONDITIONS | NUMERICALLY CHECKED: two affected cells materially change; coherent-conditioning issue remains | Withdraw all affected historical policy/oracle numbers; do not infer unrun corrected comparisons |

### 8.1 Two explicit negative-score refutations

**COUNTEREXAMPLE [C10].** Put masses (2,2,2,3)/9 on target states (00,01,10,11) and observe whether the state is 01. XOR of marginal Bayes labels has prior edge risk 4/9 and expected postquery edge risk 5/9: coherent EBR is −1/9. With masses (1,1,2,1)/5 and the same observation, the code-style Dice ratio has prior risk 1/4 and expected future risk 4/15: coherent EBR-D is −1/60. All relevant marginal decisions are strict.

**COUNTEREXAMPLE [R5].** Even optimizing the ratio-of-expectations action does not fix its nonconcavity. With one always-cut edge and one random cut of probability p, predict both cuts. At p=3/4 its optimal ratio risk is 1/15. A coherent observation yielding posterior p=1/2 or 1, each with probability 1/2, increases expected optimal ratio risk to 1/14. Reduction is −1/210. Expected *fixed* Dice loss, minimized over actions, would instead obey Bayes nonnegativity. This separates a ratio-of-expectations defect from a plug-in-action defect.

### 8.2 What the Laplace correction changes

**NUMERICALLY CHECKED.** The saved convergence audit has 16 affected paths, all from the two gpworld m0=−4 cells, with no base-fit failures among the other 184 paths. Corrected margin mean NSD is 0.6134607 instead of 0.0636513 for pool 108, and 0.5976201 instead of 0.0128758 for pool 324. The table records zero maximum trace change outside those cells. This confirms the erratum's main numerical scope from saved artifacts, not by independently refitting every GP.

**PROVED; interpretation.** Reaching the logistic posterior mode corrects an optimization defect. It does not turn a Gaussian Laplace approximation into the exact posterior, make repeated projection a posterior martingale, match a probit surrogate to a logistic truth channel, or validate the Bayes action for a geometric loss. The unchanged frozen Week 15 verdict remains a statement about its tested procedure and unaffected failures. Corrected unrun policy/oracle comparisons remain unknown. Model.fit also needs its convergence diagnostic checked in every base and fantasy fit; computing a flag without enforcing or auditing it is not a universal convergence guarantee.

**NUMERICALLY CHECKED; additional mathematical validation.** The final check also verified the geometric parity example exactly, the optimized negative Dice ratio, 2,700 common-BSC law/channel combinations, 200 sequential P/Q pairs with all 12 two-query sensor policy maps, and the discovery construction for k=1,…,6. Independent quadrature of the Gaussian random-threshold geometric value agreed with its formula to 8.3×10^−15. These are mathematical/control checks, not new SPH performance evidence.

## 9. Literature and priority audit

**KNOWN/PRIOR ART; audit scope.** Primary papers, author manuscripts and proceedings pages were searched around deterministic simulator level sets, SUR, contour design, EER, target-oriented information, predictive dependence, Bayesian misspecification, robust design, monotonicity and domain shift. This is a serious bounded comparison, not an exhaustive priority search. “No matching theorem located” below is not a novelty claim. The 2023 equivalent-loss paper has later revisions; its original version and current version must not be silently conflated.

| Tag | Closest source | Relevant established result / difference from this report | Conservative priority verdict |
|---|---|---|---|
| KNOWN/PRIOR ART | [Roy & McCallum, 2001](https://groups.csail.mit.edu/rrg/papers/icml01.pdf) | Expected future-error reduction through candidate outcomes | EER as a principle is established; the binary moment identity is an elementary specialization |
| KNOWN/PRIOR ART | [Mussmann & Liang, 2018](https://proceedings.mlr.press/v80/mussmann18a/mussmann18a.pdf) | Asymptotic data efficiency of a logistic-regression uncertainty-sampling variant | Different sample-complexity/asymptotic question; does not directly establish this finite-joint-law competitive constant |
| KNOWN/PRIOR ART | [Mussmann et al., 2022](https://arxiv.org/abs/2211.09283) | Bayesian, parameter-sampling formulation of EER avoids repeated model training | Refit-free expected-error selection is not new here; compare PEER as a tractable binary Gaussian specialization |
| KNOWN/PRIOR ART | [Liu & Li, 2023 original](https://arxiv.org/abs/2307.02719v1), [revised equivalent-loss paper](https://arxiv.org/abs/2307.02719) | Uncertainty weighting induces an equivalent optimization loss and statistical guarantees | Different learning dynamics; no inference that our unrestricted finite-prior constants or noisy-target guarantees follow |
| KNOWN/PRIOR ART | [Houlsby et al., 2011](https://arxiv.org/abs/1112.5745) | BALD distinguishes observation entropy from latent information | The noise/epistemic distinction is established; Hamming and geometric values are different losses |
| KNOWN/PRIOR ART | [Bickford Smith et al., EPIG, 2023](https://proceedings.mlr.press/v206/bickfordsmith23a.html) | Prediction-target information, including target-input relevance | Target-aware acquisition is established; PEER optimizes 0–1 risk rather than entropy |
| KNOWN/PRIOR ART | [Hübotter et al., 2024](https://arxiv.org/abs/2402.15898) | Transductive learning with restricted accessible queries and separate prediction targets, with regularity-dependent convergence | Disjoint targets and accessible-information limits are established; not a universal margin/Hausdorff guarantee |
| KNOWN/PRIOR ART | [Wang, Sun & Grosse, 2021](https://proceedings.mlr.press/v130/wang21g.html) | Predictive correlations, transductive active learning, meta-correlations and cross-normalized likelihood | Closest direct warning about joint log loss being dominated by marginals; Week 16 P4 is not a negative result about dependence in general |
| KNOWN/PRIOR ART | [Wen et al., 2021/2022](https://arxiv.org/abs/2107.09224) | Good decisions can require joint predictive distributions even when marginals are accurate | Broad principle already established; our binary swap/parity examples make the needed joint object explicit |
| KNOWN/PRIOR ART | [Bickford Smith et al., 2025](https://arxiv.org/abs/2412.20892) | Decision-theoretic treatment of uncertainty and criticism of an undifferentiated aleatoric/epistemic split | Closest conceptual source; do not claim the uncertainty taxonomy as new |
| KNOWN/PRIOR ART | [Bect et al., 2012](https://arxiv.org/abs/1009.5177) | Bayesian SUR for excursion probability of expensive deterministic functions under a known input measure | Deterministic simulator plus epistemic GP, explicit target measure and SUR are established; real-valued observations differ from binary labels |
| KNOWN/PRIOR ART | [Chevalier et al., 2014](https://doi.org/10.1080/00401706.2013.860918) | Efficient closed-form and multipoint GP excursion-set SUR | Gaussian/refit-free computation has substantial prior art; no generic computational novelty claim |
| KNOWN/PRIOR ART | [Bect, Bachoc & Ginsbourger, 2019](https://arxiv.org/abs/1608.01118) | Supermartingale analysis and consistency of GP SUR | Bayes-risk supermartingale/nonnegative expected value is established |
| KNOWN/PRIOR ART | [Ranjan, Bingham & Michailidis, 2008](https://doi.org/10.1198/004017008000000541) | Sequential GP design for computer-code contours | “Target the contour” is established; a new claim would require a different estimand or guarantee |
| KNOWN/PRIOR ART | [Azzimonti et al., 2016](https://arxiv.org/abs/1501.03659) | Excursion-set uncertainty, distance in measure and distance-based summaries | Geometry beyond marginal classification is established; our finite Hausdorff counterexample is illustrative, priority unresolved |
| KNOWN/PRIOR ART | [Gotovos et al., 2013](https://people.csail.mit.edu/alkisg/files/gotovos13active.pdf) | GP confidence-based level-set estimation with sample-complexity assumptions | Positive guarantees require explicit observation and regularity contracts; no transfer to binary likelihoods by name alone |
| KNOWN/PRIOR ART | [Castro & Nowak, 2007](https://nowak.ece.wisc.edu/COLT07.pdf) | Boundary-fragment active learning under smoothness/noise conditions | Graph restrictions and density/noise assumptions are classical; no rate theorem is imported without its precise conditions |
| KNOWN/PRIOR ART | [Cuong, Ye & Lee, 2016](https://arxiv.org/abs/1603.09050) | Approximate Bayesian active-learning robustness for prior-Lipschitz utilities; mixtures of priors | Closest prior for model-law perturbation bounds. Our moment-specific and terminal-target forms are specializations/refinements, priority not established |
| KNOWN/PRIOR ART | [Sloman et al., 2022](https://arxiv.org/abs/2205.13698) | Misspecification can induce active-learning bias in Bayesian adaptive design | Supports the possibility, not the causal identification, of Week 16's model explanation |
| KNOWN/PRIOR ART | [Tang, Sloman & Kaski, 2026](https://proceedings.mlr.press/v300/tang26d.html) | Representative sampling, information and misspecification-error amplification | Current related theory already studies more than information gain; no direct evidence for a specific SPH remedy |
| KNOWN/PRIOR ART | [Go & Isaac, 2022](https://proceedings.mlr.press/v180/go22a.html) | Robust EIG via a KL ambiguity set and affine relaxation | Robust design is established; C=1 logistic fitting does not automatically implement it |
| KNOWN/PRIOR ART | [Johnstone, Gaussian estimation](https://mathweb.ucsd.edu/~jbradic/math281a/Johnstone.pdf), univariate Bayes minimax section | Second-moment ambiguity and least-favorable Gaussian prior yield shrinkage | Our normal-threshold robust-Bayes result is known decision theory with a campaign interpretation |
| KNOWN/PRIOR ART | [Golovin & Krause, 2011](https://arxiv.org/abs/1003.3967), [Fujii & Sakaue, 2019](https://proceedings.mlr.press/v97/fujii19a/fujii19a.pdf) | Adaptive-submodular and ratio-based greedy guarantees | Conditions must hold for the actual loss; parity rules out an automatic Hamming guarantee |
| KNOWN/PRIOR ART | [Kearns & Singh, 2002](https://people.eecs.berkeley.edu/~pabbeel/cs287-fa09/readings/KearnsSingh_E3_2002.pdf) | Model simulation bounds for policy values | Sequential error accumulation is prior art; explicitly separating terminal latent-target error is the useful adaptation here |
| KNOWN/PRIOR ART | [Riihimäki & Vehtari, 2010](https://proceedings.mlr.press/v9/riihimaki10a.html), [Barile & Feelders, 2012](https://doi.org/10.1137/1.9781611972825.65) | Monotonicity-informed GPs; monotonicity-based active learning | Order information and propagation are established; our violation-count examples clarify assumptions, not a new general method |
| KNOWN/PRIOR ART | [Ben-David et al., 2010](https://proceedings.mlr.press/v9/david10a.html), [Sugiyama, 2006](https://www.jmlr.org/papers/v7/sugiyama06a.html) | Domain-adaptation impossibilities; active-design covariate shift and importance weighting | Threshold-transfer indistinguishability is a simple specialization; threshold/concept shift differs from covariate shift |

### 9.1 Result-level priority verdicts

| Tag | This round's result | Closest established idea | Verdict |
|---|---|---|---|
| PROVED | Binary-observation error formula and Gaussian/probit evaluation | Binary Bayes decision theory, EER, Gaussian orthants | Elementary identity/specialization; no novelty claim |
| PROVED | Common-BSC sharp 1/(N−1) extension | Round 1 finite-pool bound; noisy Bayesian active learning | Exact extension proved here; literature-wide priority unresolved |
| PROVED | D_j terminal regret and explicit channel split | Prior-Lipschitz active-learning robustness and bounded-loss perturbation | Useful decision-specific refinement; no originality established |
| PROVED | Refit gain = Bayes value + initial excess − future excess | Standard excess-risk decomposition | Elementary identity; important for this audit, not a new general principle |
| PROVED | Sequential kernel plus target-posterior bound | Simulation lemmas, TV contraction, KL chain rule | Specialization; no novelty claim |
| COUNTEREXAMPLE | Coherent negative EBR/EBR-D; optimized negative ratio | Non-Bayes actions and nonconcave uncertainty functionals | Explicit audit counterexamples; priority unresolved |
| COUNTEREXAMPLE | Equal-budget discovery optimum versus geometry | Decision-specific experimental design | Sharpened explicit construction; priority unresolved |
| COUNTEREXAMPLE | Equal binary pair moments, unequal Hausdorff VOI | Higher-order dependence; joint predictions for decisions | Explicit geometric construction; priority unresolved |
| PROVED | Rank-inversion discovery bound | Pair counting / AUC interpretation | Elementary sharp combinatorial bound; no novelty claim |
| KNOWN/PRIOR ART | Graph median/mean risks, density and regularity bridges | Excursion-set decision theory; boundary-fragment analysis | Known ingredients with explicit constants and scope |
| KNOWN/PRIOR ART | Robust-Bayes threshold shrinkage | Normal means under moment ambiguity | Known theorem; thesis-specific interpretation only |

## 10. Experiment-prediction table for Claude Code / Opus

**CONJECTURE; proposed research protocol.** These are discriminating tests, not executed acquisition experiments. Begin with fixed saved states and exact synthetic controls; hold targets, loss, candidate set, tie-breaking and paid budget constant. Report absolute gains alongside ratios, and separate the realized-truth algorithmic utility from posterior-averaged Bayes value. Synthetic theorem checks can falsify an implementation/application; an empirical mechanism needs its own predeclared effect size and uncertainty assessment.

| Theory result | Observable prediction | Required model/data | Exact statistic | What would falsify it |
|---|---|---|---|---|
| PROVED L1–L2: binary/PEER identity | Analytic value equals exact conditioning under the same declared law | Small finite posterior or current Gaussian/probit Q; fixed targets | Maximum absolute error between formula and outcome-weighted Bayes risk; MC interval when integration is sampled | Certified error exceeding numerical/integration tolerance |
| PROVED R1, L4: positive margin guarantees | Common-BSC ratio ≥1/(N−1); self-information condition gives αw_min | Finite sign laws; common α; full-pool targets | Minimum gain-ratio minus claimed lower bound; record self reliability and weights | Negative slack while every premise is verified |
| COUNTEREXAMPLE C1–C2: observation/channel and scale | Sign probabilities and boundaries invariant under positive rescaling; fixed-noise PEER shrinks | Frozen Gaussian states scaled (μ,Σ)→(cμ,c²Σ); also Gaussian random thresholds | Maximum sign-pair change; V_j(c); boundary risk; σ_f/normal slope | Changed geometric law under pure rescaling, or nonzero limiting fixed-noise value with integrability |
| CONJECTURE: label-margin decoys may reflect channel mismatch | Hard-sign and stochastic-channel scores select different candidates despite identical current Q | Same Week 16 states; deterministic, logistic, true-probit, τ²=8/π channels | Query disagreement, Kendall/Spearman, absolute value regret, diagonal versus cross-target score contributions | No material score/action/value change in the predeclared affected stratum weakens this mechanism |
| PROVED / CONJECTURE: separate exact conditioning from refit | Coherent Bayes VOI is nonnegative; updater discrepancy may explain oracle residual | Same Q and channel; pair-derived exact conditional marginals versus safeguarded fantasy fits | Martingale residual and branch-weighted target decision disagreement ζ_j; oracle-minus-policy difference before/after replacing updater | Persistent large residual after verified update/channel alignment falsifies an updater-dominant explanation, not the transfer theorem |
| COUNTEREXAMPLE C10/R5: negative boundary scores | Exact coherent plug-in EBR and Dice ratio can be negative | Rational 4-world and 2-edge examples | Gains −1/9, −1/60 and −1/210 | Any exact arithmetic mismatch |
| PROVED L5/R2: calibrated acquisition transfer | Matching pair moments/KL bound true terminal regret | Repeated controlled worlds with known conditional P; actual (T_i,O_j) pairs | Regret −(D_jQ+D_jP)/2 and regret −sqrt(2K_max); Q-gap γ and transfer slack | Positive certified excess over the bound |
| CONJECTURE: Week 16's pair diagnostic misses acquisition-relevant error | Correct target-observation pairs explain ranking errors better than latent-sign pairs in amplitude/channel stress tests | Common states; independent Gaussian amplitude-swap controls and small GP worlds | Pair log-score excess relative to true P, weighted C_j/D_j; ranking at fixed marginal quality | Equal acquisition performance across amplitude swaps would refute the construction; lack of added diagnostic value in GP cells limits its empirical relevance |
| PROVED S1–S3: sequential error accumulation | Small reached-history kernel and terminal-target errors prevent large terminal regret | Exact finite decision trees B=2–4; known P,Q | R_P(π_Q)−R_P(π_P), Γ_Q+Γ_P+β, KL chain sum; signed slack | Negative bound slack; initial-only diagnostics do not test this theorem |
| COUNTEREXAMPLE C4: myopia / initial pair sufficiency | Greedy gain η, B=2 optimum 1/2 despite identical initial pairs | Parity-sensor law, rational η; optionally embed boundary bit in a separated stratum | Exact tree risks; Δ(B given A)−Δ(B); terminal target TV | Mismatch in rational values; positive diminishing-return violation rejects submodularity |
| PROVED R3: EER can compound under correct specification | Independent-block EER is optimal at all budgets, margin underweights large blocks | Finite copy-block posterior with fixed Hamming weights | Exact B-step gain of EER/margin/optimal DP; compare with sorted W_bu_b | EER below DP under verified block independence |
| CONJECTURE: original M3 versus regularized mean | Separating coefficient stability, threshold adaptation and residual freedom distinguishes their mechanisms | Shared paid labels and shared paths; original M3, C=1 trend with matched residual, free campaign intercept, whole-mean attenuation, G3; fresh threshold-shift controls | Threshold bias and variance; within-state disagreement; paired q20/NSD AULC contrasts with campaign-level intervals | An alleged attenuation-only threshold change is impossible; a regularization benefit disappearing after matching intercept/residual contradicts a penalty-specific claim |
| PROVED P1–P3: robust-Bayes shrinkage | Risk follows quadratic and worst affine risk minimized at w_D | Exact normal-location controls; frozen v,D and shift grid; clipped control | E(θ̂−θ)²−[(1−w)²Δ²+w²v]; maximum over grid; crossing thresholds | Systematic analytic mismatch; normal approximation failure limits SPH applicability |
| CONJECTURE: level shifts, order survives | Campaign intercept/threshold changes while rare-oriented ranking remains useful | Genuinely separate campaigns; fixed score direction and preprocessing | Threshold difference with uncertainty; exact pair inversion count V; AUC; tail enrichment and overlap | Widespread rank reversal or nonmonotonicity contradicts order preservation; stable threshold contradicts a level-shift explanation |
| PROVED P5–P6: no universal OLD-only strength | Whole-mean attenuation preserves crossing; identical OLD and unlabeled target inputs cannot reveal opposite shifts | Paired target-threshold worlds; identical OLD; predeclared selection rule | Zero-crossing invariance; sum of two target risks minus disagreement mass | Negative indistinguishability-bound slack or an unexplained use of target outcomes |
| PROVED P6: campaign-variance calibration | Stated upper bound has at least 1−α coverage under its exact normal campaign assumptions | Independent simulated historical campaigns with known external anchor, τ² and v_0 | Fraction of τ²≤τ_U², with binomial interval; analytic chi-square coverage | Coverage significantly below 1−α under the exact declared experiment; estimated-anchor reuse tests a different formula |
| PROVED D1–D2: discovery versus refinement | Startup optimal for T_both can have worse final geometry; coalescence limits later effects | Independent-column construction; stored Week 12 paired ledgers and complete fitting states | T_both, minimum-eight release cost separately; final Hausdorff risk; δ_t; absolute AULC contrast versus Σλ_tδ_t | Construction mismatch, or empirical bound violation after genuine state/seed equality |
| PROVED D3–D4: enriched tails and imperfect ranks | Uniform tail law and deterministic inversion bound hold under their distinct sampling contracts | Fixed pool counts, deterministic tie-broken physics ranking; failed-B8 strata separately | Hypergeometric survivor; r(D−1)−V; (M−s)(r−s)−V | Positive inequality slack; an unconditional tail rate cannot falsify or confirm a conditional selector |
| COUNTEREXAMPLE C6: order violation amplification | One contaminated point can corrupt many hard-propagated labels | Exact threshold stress test with one exception | Point-contamination count, pair inversions and incorrect removals separately | N-scale propagation attributed to exactly one pair would be a counting error |
| PROVED G1–G5: geometry and density | Hamming equals strip-volume integral; geometry bridge scales with coverage/slope constants | Known smooth graph/tube worlds; fixed physical coordinates; reweighted reference clouds | Exact strip integral; weighted displacement; Hausdorff; quadrature error/h; tube remainder/∫δ² | Exceeding explicit bounds with verified density, slope, coverage and topology premises |
| PROVED G2: restricted Gaussian graph observation | Absolute/squared-displacement values match Gaussian conditional-variance formulas | Small Gaussian posterior over graph heights; a query actually reveals a real-valued height | Analytic value versus independent conditional integration for both losses | A difference beyond integration tolerance; substituting a binary label for an observed height invalidates the experiment |
| COUNTEREXAMPLE G7: geometric moments | Same first/pair moments but Hausdorff values 11/70 and zero | Eight-world separated-column law | Pair-law equality; current risk 1/2; exact posterior Bayes risks | Any moment/risk mismatch |
| CONJECTURE: latent-boundary objective versus predictive-label margin | Boundary displacement uncertainty may discriminate candidates missed by margin | GP posterior samples with a justified single-root coordinate; independent known-boundary controls first | Posterior root variance; root/observation covariance score; actual squared-displacement reduction; compare sd alone and sd/gradient | Poor root representation or no predictive advantage of displacement moments rejects applicability/benefit |
| NUMERICALLY CHECKED / diagnostic: Laplace repair scope | Corrected mode fixes affected paths; it need not fix coherence | Saved convergence tables; future fits with mode and gradient checks | Mode residual, objective monotonicity, convergence flag; martingale gap after mode convergence | Residual failures or unflagged failures invalidate claimed convergence; nonzero martingale gap does not contradict mode convergence |

**CONJECTURE; recommended order.** The highest-value first test is a same-state factorial separating latent law, channel and updater, with identical targets and loss. Next test the physical-level hypothesis using matched M3/G3 inference controls and frozen synthetic campaign shifts. Only after these mechanisms are distinguished should an independent campaign compare fully specified policies. A stronger acquisition score under Q is not itself a reason to replace the current empirical endpoint.

## 11. Explicit assumptions table

| Tag | Result family | Pool / target | Observation and update | Essential assumption; consequence if absent |
|---|---|---|---|---|
| PROVED | Binary moment identity / one-step transfer | Fixed finite targets, weights fixed; queries may differ | Binary observations; coherent joint P or Q; unconstrained binary coordinate decisions | Other losses or label-coupled decisions require their own Bayes action |
| PROVED | Sharp common-noise margin | N≥2, queries equal all equally weighted targets | Common independent sign-noise attenuation α>0; ideal conditioning | Different reliabilities or disjoint targets can have zero ratio |
| PROVED | Self-information ratio | Each query is a target of positive weight | Binary observations; self gain ≥α observation uncertainty | No uniform positive constant if self reliability or minimum target weight vanishes |
| PROVED | Q/P regret certificates | Same loss, target, candidates and feasible rules | Correctly defined laws at the compared history | Model fit quality on different states is not the theorem's discrepancy |
| PROVED | Sequential simulation | Common finite horizon and action contract; loss in [0,1] | Kernels at reached histories and terminal posteriors; null-history versions specified | Initial pair calibration alone is insufficient |
| KNOWN/PRIOR ART | Adaptive greedy horizon bound | Common realization utility and unit costs | Actual-law adaptive monotonicity and submodularity | Coherence alone supplies neither diminishing returns nor 1−1/e |
| PROVED | Block EER optimum | Fixed Hamming weights, independent copy blocks | Noiseless block revelation | Coupled blocks/noisy channels need new analysis |
| PROVED / KNOWN/PRIOR ART | Threshold shrinkage | Scalar threshold and squared error | Exact normal-location observation | Binary GP fitting is not automatically this experiment |
| PROVED | Bounded shift / moment robust Bayes | Known anchor; declared D | Independent Gaussian noise | Bounded-support affine minimax and moment-class global minimax are different claims |
| PROVED | Order-only binary search | Distinct scalar scores; realizable one-threshold labels | Noiseless label revelation | Stochastic monotonicity and high AUC do not justify elimination |
| PROVED | Discovery laws | Fixed finite class counts | Uniform ordering in stated pool/subset, or a fixed ranked ordering | History-conditioned extreme selection is a different policy |
| PROVED | Coalescence | Same truth and sufficient state | Identical future transitions/seeds | Same query set alone can be insufficient for order-dependent fits |
| PROVED | Graph displacement | Single graph per base coordinate; declared base measure | Posterior over roots, legitimate graph actions | Multiple roots/topology changes invalidate this representation |
| PROVED | Continuous geometry bridge | Uniform coverage, bounded slopes; positive density for L1-to-sup | Labels/graph positions related by stated reconstruction | Sparse arbitrary pools cannot guarantee geometry between samples |
| PROVED | Normal-tube expansion | Injective tube, bounded curvature, corresponding surfaces | No additional components; density Lipschitz | Small volume error alone cannot control topology or Hausdorff |
| NUMERICALLY CHECKED | Empirical Week 16 audit | Existing saved states and reference clouds | Safeguarded logistic Laplace fits plus declared PEER surrogate | Reproduction of aggregates is not a new confirmatory trajectory experiment |

## 12. Counterexample catalogue

| Tag | ID | Small construction | Claim it refutes |
|---|---|---|---|
| COUNTEREXAMPLE | C1 | Two independent latent coordinates, one arbitrarily small amplitude | Positive universal predictive-margin ratio for latent-sign recovery with a fixed noisy link |
| COUNTEREXAMPLE | C2 | F_c=cG with unchanged sign/zero set | Small latent sd implies small geometric uncertainty |
| COUNTEREXAMPLE | C3 | One target, two swapped informative/independent observations; Gaussian amplitude swap variant | Marginal calibration, or even sign-pair calibration, suffices for noisy-query selection |
| COUNTEREXAMPLE | C4 | T=AB, weak sensor C, budget two | Myopic superiority compounds; initial pair correctness certifies multistep behavior |
| COUNTEREXAMPLE | C5 | Paid class anchors and independent boundary columns, equal final budget | Optimal both-class discovery implies good downstream boundary learning |
| COUNTEREXAMPLE | C6 | One point exception to a threshold; adjacent single inversion variant | Almost-monotone order permits safe hard propagation |
| COUNTEREXAMPLE | C7 | Two thresholds inside one unsampled gap | Arbitrary finite-pool labels guarantee continuous geometry |
| COUNTEREXAMPLE | C8 | Parallel surfaces; narrow oscillating graph | Surface Dice, area, Hamming and distance are equivalent losses |
| COUNTEREXAMPLE | C9 | Eight worlds on three separated columns | First/pair binary moments determine Hausdorff acquisition |
| COUNTEREXAMPLE | C10 | Four-state coherent posterior and deterministic observation | A negative plug-in edge or Dice score proves posterior incoherence |
| COUNTEREXAMPLE | R5 | Two nonempty cut configurations, posterior cut probability 1/2 or 1 | Optimizing a ratio of expectations automatically restores Bayes-risk nonnegativity |
| COUNTEREXAMPLE | P6 | Identical OLD/target features, two different NEW thresholds | OLD alone can select universally robust prior strength without a campaign relation |

## 13. Unresolved conjectures and open problems

**CONJECTURE O1.** Channel misspecification and repeated Laplace projection account for a material fraction of the Week 16 residual. The proposed factorial, not the current H−A arithmetic, can test their contributions. They may prove small.

**CONJECTURE O2.** Allowing a campaign intercept while retaining useful score order improves transfer more reliably than attenuating an entire fixed physics mean. The comparison must match residual capacity, fitting budget and acquisition path. It may lose to G3.

**CONJECTURE O3.** Boundary-coordinate/observation calibration predicts geometric query value beyond marginal label calibration on physically appropriate graph regimes. Root existence, continuity, multimodality and Monte Carlo error must be checked. No claim covers arbitrary four-dimensional SPH boundaries.

**CONJECTURE O4.** A tractable approximate-submodularity certificate may hold in restricted, sufficiently regular GP level-set problems away from synergy and threshold effects. The unrestricted parity counterexample rules out deriving it from Bayesian coherence alone.

**CONJECTURE O5.** A robust prior over level, slope and discrepancy could improve decision calibration without destroying the useful physics order. The normal-location theorem supplies an interpretable prototype, not a proof for logistic GPs or a rule for choosing a real-world shift radius.

**KNOWN/PRIOR ART; open here.** The sharp sequential margin constant for general finite N,B under the original noiseless full-pool assumptions remains unresolved in this package beyond the inherited B/N guarantee and N=3,B=2 result. Tight constants for noisy heterogeneous channels, geometric losses and constrained actions are separate problems. No closed form is asserted.

**PROVED; evidence limitation.** Single realized deterministic labels on a fixed pool do not reveal the true posterior dependence structure at every counterfactual history. A data-only certificate of the displayed model-law bounds therefore needs additional structural assumptions, repeated controlled worlds, or a justified uncertainty class. Marginal reliability plots cannot supply it.

## 14. What this changes in Burak’s thesis.

**NUMERICALLY CHECKED.** Keep the empirical statement that PEER can be much better than margin under its own Gaussian/probit criterion yet fail to recover the truth-weighted refit oracle's gains. The numerical finding survives independent reconstruction.

**PROVED.** Replace “the remaining gap is model information” with the narrower conclusion that the tested model, observation assumption, update procedure and acquisition objective do not jointly turn model-internal value into the desired boundary improvement. This identifies a missing attribution experiment rather than proving that acquisition is exhausted.

**PROVED.** Separate physical determinism, posterior sign uncertainty, and the stochastic working likelihood. A probability near 1/2 is not a single kind of uncertainty, and a small latent variance is not a geometric certificate. This distinction is central to interpreting a classifier used to recover a deterministic boundary.

**PROVED.** Treat startup and refinement as separate decision problems. Faster discovery can be operationally valuable even when later q20 performance is unchanged; the exact equal-budget counterexample and coalescence bound explain why no contradiction arises.

**CONJECTURE.** Present a regularized or hierarchical physics mean as a motivated, falsifiable candidate. Its defensible rationale is controlled borrowing of a potentially shifted level while retaining useful order, with explicit uncertainty and residual flexibility. It is not an established replacement for G3 + margin and not robust Bayes merely because its coefficient is penalized.

**KNOWN/PRIOR ART; contribution scope.** The strongest thesis contribution here is an assumption-explicit diagnosis connecting known decision theory/SUR to exact finite-pool counterexamples and real implementation audits. None of the literature search, internal tests or current NEW results justifies a novelty or external-validation overclaim.

FUNDAMENTAL INTERPRETATION NEEDS REVISION
