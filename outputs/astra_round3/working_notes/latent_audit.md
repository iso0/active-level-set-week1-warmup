# Round 3 latent-target / Week 16 audit

Repository was read only. Scratch note created 2026-10-05. Labels PROVED concern derivations below; NUMERICALLY CHECKED concerns the explicitly reported arithmetic; implementation findings use source inspection rather than rerunning historical experiments. No relevant memory hit was found.

## Executive verdict

**CORRECT WITH CONDITIONS:** the binary-observation identity, Gaussian/probit PEER, W16-1 counterexample, and nonnegative coherent Hamming Bayes value. **GAP / interpretation too strong:** attributing H−A solely to missing model information; treating low latent sd as established low boundary uncertainty; explaining all observed decoys by the vanishing-noise-information limit; describing latent-sign-pair scores as direct tests of the target-observation moments needed by PEER. **WRONG if applied generically:** negative EBR/EBR-D scores by themselves prove Bayesian incoherence. Their risk functionals are not Hamming Bayes risk.

## 1. What is mathematically correct

**[PROVED; CORRECT] Binary observation lemma.** For T,O in {−1,+1}, write m=E T and c=E TO. The four deterministic observation-to-action rules have correlations m,−m,c,−c with T, so optimal accuracy is [1+max(|m|,|c|)]/2. Equivalently, summing min(P(T=1,O=o),P(T=−1,O=o)) gives the same answer. Thus for a fixed target set and nonnegative weights,

    V(j)=1/2 sum_i w_i (|c_ij|−|m_i|)_+.

This is exact for any coherent joint law, binary observation, coordinatewise unconstrained Hamming decisions, and fixed weights. It is not a statement about geometric boundary losses or constrained global decisions. Source: THEORY_WEEK16.md:6–20; week16_peer.py:3–14,162–183.

**[PROVED; CORRECT WITH CONDITIONS] PEER.** Given current Gaussian latent law Q=N(mu,Sigma), T_i=sign F_i, and future observation O_j=sign(F_j+eta), eta independent N(0,tau²), the standard Gaussian orthant identity gives exactly the source's c_ij, with tau²=8/pi. No new Laplace approximation is needed for this one-step joint calculation. Monte Carlo agreement only validates this Gaussian/probit working law. Logistic training at week16_peer.py:71–78 and predictive expit approximation at :55–57 are distinct from the future probit channel at :167–176. PEER is consequently exact for the declared surrogate Q, not exact for the original logistic GP posterior.

**[PROVED; useful qualification] Margin ranking is nonetheless identical between the two stored predictive approximations.** With tau²=8/pi, mu/sqrt(1+pi*v/8)=tau*mu/sqrt(v+tau²). Since expit and Phi are symmetric strictly increasing, minimizing distance to .5 produces the same candidate ranking for expit(mu/sqrt(1+pi*v/8)) and Phi(mu/sqrt(v+tau²)), aside from numerical ties. Thus the current margin selection itself is a legitimate observation-margin choice for PEER's Q; the channel mismatch affects probabilities, expected values and fantasy weighting, not this same-posterior margin ranking.

**[PROVED; CORRECT WITH CONDITIONS] Nonnegativity.** Bayes risk after an observation cannot exceed the old risk in expectation because the old action remains available. For Hamming, h(q)=min(q,1−q) is concave and E q'=q, so E h(q')<=h(q). Negative exact-Hamming values are impossible under a coherent current/future law with a fixed action space. However, nonnegative scores alone do not establish coherence. Source: THEORY_WEEK16.md:32–40; VSUR audit implementation week16_validate.py:29–40.

**[PROVED; CORRECT] W16-1.** At centered Gaussian F~N(0,s²),

    V_self = asin(s/sqrt(s²+tau²))/pi = atan(s/tau)/pi.

It tends to zero with s, while both target-sign and observed-label marginals remain exactly balanced. Independent candidates a~N(0,epsilon²) and b~N(delta,S²), with a sufficiently small fixed delta>0, make a uniquely margin-optimal while b has fixed positive self-value. Independence makes cross-target values zero, so the ratio tends to zero. Source: THEORY_WEEK16.md:42–57.

## 2. Stronger counterexamples and useful positive conditions

**[COUNTEREXAMPLE; PROVED] Exact logistic and probit construction without Gaussian integrals.** Let F_a=epsilon S, with S fair ±1, and F_b=M U, independent, with E U=2delta>0. Let E[O|F=f]=a(f), where a is odd and increasing: logistic a(f)=tanh(f/2), or probit a(f)=2Phi(f/tau)−1. Then observed margin selects a uniquely, because E O_a=0 and E O_b=2delta a(M)>0. Cross-target values vanish by independence. Therefore

    V(a)=a(epsilon)/2,
    V(b)=(a(M)−2delta)/2,
    V(a)/V(b)=a(epsilon)/(a(M)−2delta) -> 0,

provided 0<2delta<a(M). Logistic M=3, delta=.1 gives ratios .0708480, .00709065, .000709071 at epsilon=.1,.01,.001. These values were NUMERICALLY CHECKED with SciPy/Python, read-only invocation.

**[PROVED] Gaussian logistic analogue.** If F=s Z with Z standard normal, centered logistic self-value is (1/2) E tanh(s|Z|/2). It is asymptotic to s/sqrt(8pi), the same first-order value as the chosen probit approximation. Thus the W16-1 pathology is not caused solely by replacing logistic with probit.

**[COUNTEREXAMPLE; PROVED] Latent scale gauge.** For any random field G with P(G_i=0)=0, set F^(c)=cG, c>0. Its sign field, all sign-pair probabilities, zero set, and every geometric boundary uncertainty are identical for all c. Under a fixed logistic/probit channel, a(cG_j)->0 pointwise as c->0. Dominated convergence gives E[T_i O_j]->0, hence V_c(j)->0 for every finite target/candidate set. Under a Gaussian law, means scale by c and covariance by c², but mu_i/s_i is invariant. At a centered point, sign entropy remains exactly one bit for every c. The physical linearized boundary uncertainty s/|grad mu| is also invariant under scaling. Small latent sd alone therefore does not establish a well-localized boundary. A noiseless sign observation O_j=T_j has unchanged information under the same scaling.

**[COUNTEREXAMPLE; PROVED] Perfect latent-sign calibration does not identify noisy query value.** Let two independent centered Gaussian coordinates have sd (1,epsilon) under P and (epsilon,1) under Q. Their full sign laws are identical: two independent fair signs. Their noisy observation marginals are also all fair, for either fixed symmetric logistic/probit link. Yet their self-moments and best query swap; the small-sd query value tends to zero. Latent sign pair log loss cannot detect this error. Even perfect sign-pair laws plus perfect observed-label marginals are insufficient without target-observation dependence / magnitude-channel information.

**[PROVED; positive theorem] Common symmetric sign noise preserves the original 1/(N−1) guarantee.** Suppose all N candidate locations are the N unit-weight targets; O_j=T_j B_j where each B_j is independent of the entire sign field and has common E B_j=alpha in (0,1]. (Mutual independence among different B_j is unnecessary for one query.) Then observed-label margin minimizes a_j=|E T_j|, and

    V(j)=1/2 sum_i (alpha |E T_iT_j|−a_i)_+.

For any margin choice m, V(m)>=V(k)/(N−1) for every k, N>=2. Proof: let f_b(x)=(b−x)_+, s_i=f_alpha(a_i), and d_ik=f_(alpha|E TiTk|)(a_i). Since a_m<=a_k and b<=alpha,

    f_alpha(a_m)−f_alpha(a_k) >= f_b(a_m)−f_b(a_k),

so s_k+d_mk<=s_m+d_km. Every other d_ik<=s_i<=s_m. Therefore

    2V(k)<=s_m+d_km+(N−2)s_m <= (N−1) 2V(m).

If V(m)=0 all values are zero. The constant is sharp for every fixed alpha>0 and N>=3: take one independent fair decoy and N−1 perfectly shared signs of mean 2eta>0. Margin uniquely selects the decoy; its value is alpha/2, while a cluster query has value (N−1)(alpha−2eta)/2. Their ratio tends to 1/(N−1) as eta decreases to zero. For N=2 the bound is one and margin is optimal. This shows that noise alone does not destroy the guarantee: W16-1 uses nonuniform attenuation associated with latent magnitudes/variances. The result does not cover arbitrary unequal weights or a disjoint reference cloud.

## 3. Decoys / aleatoric interpretation

**[NUMERICALLY CHECKED; GAP] The reported sd values alone do not establish the W16-1 centered limit.** Noise sd sqrt(8/pi)=1.59577. At s=1.5, self rho=.684904 and CENTERED self-value=.240156; at s=2.6, rho=.852277 and CENTERED self-value=.324779. These are counterfactual centered values, NOT actual self-values, and must not be used to reject the empirical low-self-value mechanism. The root agent's reconstruction of actual mu from stored predictive probability and sd, read from scratch verification_results.json, gives actual median decoy self-values .005866 (curvedMono), .035687 (dev), 0 (rough), .143891 (branin), .204070 (gpworld). Thus actual low self-value is supported in several families and is heterogeneous. The narrower remaining criticism is that sd/rho alone does not determine it: standardized mean and the decision threshold matter. Decoy definition r_model<.5 concerns total weighted value relative to the best candidate. Low value on a disjoint reference cloud can also reflect cross-covariance and target weighting. A causal attribution to physical aleatoric noise is still not established.

**[PROVED; CORRECT WITH CONDITIONS] Uncertainty distinction.** In a stochastic observation model, p(O=1) near .5 can combine irreducible conditional label entropy and posterior uncertainty about F. But F~N(0,s²), s->0, retains maximal sign uncertainty; what vanishes is the informativeness of ONE fixed-noise label about that sign. Calling the true simulator uncertainty aleatoric requires genuine repeated-label randomness under the physical data-generating law. week16_cells.py:60,82,84,89 explicitly includes deterministic cells, whereas the working classifier still uses stochastic logistic/probit likelihoods. In those cells the apparent aleatoric component is a property of the working model, not established physical label noise.

**[CONJECTURE; falsifiable]** Channel/magnitude mismatch and updater approximation may materially contribute to the observed ranking failure. Existing results do not estimate their relative contributions. Test by holding the same frozen states and targets and swapping exactly one of channel, conditioning rule, or latent distribution at a time; no policy search or new empirical superiority claim is needed.

## 4. H−A is not an identified information decomposition

**[PROVED from implementation; GAP] Different quantities are compared.** `week16_headroom.py:71` computes PEER on the current Gaussian Q, closed under a probit observation experiment. `:54–63` instead averages truth error after calling `model.fit` on both fantasy labels, with probabilities `c['p_true'][j]`. `:45–51` evaluates the sign of fresh posterior means against one realized true latent field. In gpworld `week16_cells.py:71–74` uses true logistic probabilities, not the probit PEER channel. Other cells use probit noise of varying sigma or deterministic labels (:60,:82,:84,:89). Thus even the advertised well-specified gpworld is not an exact matched-posterior/matched-channel/matched-update comparison.

**[PROVED] Fixed-truth oracle is not Bayes information.** Conditional on the entire realized truth f, all T_i are deterministic. Its coherent Bayes risk and query value are zero. Week 16's V_true can nevertheless be positive because it measures the improvement of a restricted learning algorithm that does not know f. It is a valid per-world algorithmic one-step utility, but it is not the coherent Bayes VOI under the omniscient truth law.

**[PROVED] Exact updater decomposition.** For a law P over (T,O), fixed prequery decision a0, postquery algorithmic decisions A_j(O), and Hamming loss, write

    b_P = risk_P(a0)−r_P^0 >=0,
    e_P(j) = E_P loss(T,A_j(O))−r_P^j >=0.

Then the algorithm's gain is G_P^A(j)=V_P(j)+b_P−e_P(j). Hence, if j_Q maximizes model Bayes value,

    max_j G_P^A(j)−G_P^A(j_Q)
      = max_j [V_P(j)−e_P(j)]−[V_P(j_Q)−e_P(j_Q)].

Even Q=P can leave positive residual entirely because A_j fails to implement exact conditioning/Bayes action. With P degenerate at fixed f, V_P(j)=0 and the entire landscape is updater error relative to the known truth. Therefore H−A cannot be identified solely as inaccessible truth information. A correct descriptive claim is that this PEER selector did not recover the refit oracle's one-step gains on these states.

**[PROVED from implementation; CORRECT WITH CONDITIONS] Candidate cap.** headroom.py:91–96 evaluates at most 120 candidates, forcing inclusion of margin and PEER optima. Thus H is a lower bound on full-candidate oracle headroom whenever subsampling occurs. The identity H−A is exact on the evaluated candidate subset, not necessarily the full pool.

## 5. Correct Q/P one-step transfer bounds

**[PROVED] Moment transfer.** For coherent laws P,Q on the SAME target set, weights, observation actions, and loss, define m_i^R=E_R T_i, c_ij^R=E_R T_iO_j. Let

    M=sum_i w_i |m_i^P−m_i^Q|,
    C_j=sum_i w_i |c_ij^P−c_ij^Q|.

Since (|c|−|m|)_+ is one-Lipschitz separately in c and m,

    |V_P(j)−V_Q(j)| <= (M+C_j)/2.

For j_P in argmax V_P and j_Q in argmax V_Q,

    V_P(j_P)−V_P(j_Q) <= M+(C_jP+C_jQ)/2 <= M+max_j C_j.

Proof: insert V_Q(j_P)−V_Q(j_Q)<=0 between the two P-values and apply the displayed per-action bound. A small rank correlation does not imply a large absolute regret or any lower bound on calibration discrepancy. Calling rank failure a “contrapositive” application is invalid unless one first establishes a quantitatively large matching-objective regret and uses its actual moment bound.

**[PROVED] Separating observation channel from latent structure.** Assume local channels E_R[O_j|F]=a_j^R(F_j), bounded by one. Write mu_j^R=Law_R(F_j), h_ij^R(f)=E_R[T_i|F_j=f]. Then c_ij^R=integral h_ij^R a_j^R dmu_j^R. Adding and subtracting under mu_j^Q gives

    |c_ij^P−c_ij^Q|
    <= 2 TV(mu_j^P,mu_j^Q)
       + E_Q |h_ij^P(F_j)−h_ij^Q(F_j)|
       + E_Q |a_j^P(F_j)−a_j^Q(F_j)|.

The terms respectively measure candidate latent marginal error, latent conditional structure error, and observation channel error. Choose bounded versions of h^P on Q-only support; the bound is valid but may be vacuous when supports separate. Target marginal error M remains separately in the value bound. The h term is a conditional structure term, not a purely marginal-free copula distance.

**[PROVED] Alternative pure marginal/dependence separation.** Let gamma_ij^R be Law(F_i,F_j), let kappa_ij^R=gamma_ij^R−mu_i^R tensor mu_j^R, and delta_i=TV(mu_i^P,mu_i^Q). Denote full variation norm of a signed measure by ||.||_var. Then

    |c_ij^P−c_ij^Q| <= 2delta_i+2delta_j
         + ||kappa_ij^P−kappa_ij^Q||_var
         + E_Q |a_j^P(F_j)−a_j^Q(F_j)|,
    |m_i^P−m_i^Q| <=2delta_i.

Proof: fix the P channel, decompose pair-law difference into a product-marginal difference plus kappa difference; bounded integrands and TV(product measures)<=delta_i+delta_j give the result, then add channel error. This is looser but explicitly distinguishes marginal, dependence, and channel terms.

**[PROVED] Required calibration object.** PEER needs (T_i,O_j), not merely (T_i,T_k). THEORY_WEEK16.md:64–69 names the latter; calibration.py:43–71 implements latent-sign pairs. These are potentially useful diagnostics, but do not by themselves estimate the transfer-bound moments. Its variants also run different paths (calibration.py:88–95), so raw score/outcome comparisons are not controlled same-state mechanism tests. Expected excess pair log loss against the true pair law is KL; raw empirical joint log loss contains outcome entropy and cannot be substituted directly for KL.

## 6. Negative EBR/EBR-D values do not prove incoherence

**[PROVED from implementation; WRONG if generalized]** `week15_ebr.py:103–112` predicts edge cuts by XOR of marginal-sign Bayes actions. That is not generally a Bayes action for edge misclassification loss. `:115–128` uses a ratio of expectations, E W_err/(E W_true+W_pred), not the posterior expectation of a fixed loss minimized over actions. Therefore neither generally has the Bayes-risk concavity used in L3. VSUR does (:131–133). The measured martingale gap for VSUR is evidence of incoherent refit look-ahead; a negative EBR-D score alone is not.

**[COUNTEREXAMPLE; PROVED, arithmetic checked] Exact coherent EBR can be negative.** Assign probabilities (2,2,2,3)/9 to binary target states (00,01,10,11). Both marginal modes are 1, so predicted edge is uncut and edge-error risk is 4/9. Observe O=1 iff the state is 01. That branch is known exactly and has zero edge error. On O=0 (probability 7/9), target marginal modes are (1,0), so predicted cut has error 5/7. Expected postquery error is 5/9, giving reduction −1/9 despite exact conditioning and strict marginal decisions.

**[COUNTEREXAMPLE; PROVED, arithmetic checked] Exact coherent EBR-D can be negative.** Use masses (1,1,2,1)/5 on the same states and same observation. Prior marginal modes (1,0) predict a cut, true-cut probability is 3/5, and Dice ratio is (2/5)/(1+3/5)=1/4. The O=1 branch has zero error. On O=0 (probability 4/5), true-cut probability is 1/2, marginal modes remain (1,0), and ratio is (1/2)/(1+1/2)=1/3. Expected future ratio is 4/15, giving reduction −1/60. The code's 1e−9 denominator guard changes only negligible decimals, not the sign.

## 7. What the Laplace correction does and does not establish

**[PROVED from implementation; CORRECT WITH CONDITIONS]** RobustLaplaceGPC backtracks on the logistic log posterior (peer.py:60–98), addressing failure to reach its mode. It retains a Gaussian Laplace approximation, fresh projection after every label, fixed/empirically fitted mean rules, and an approximate logistic predictive integral. Correct convergence of the mode does not imply sequential posterior martingale consistency. Its `converged` attribute (:96–97) is computed but Model.fit (:158–159) does not raise on nonconvergence; a numerical audit should check it in all relevant base/fantasy fits.

**[CORRECT WITH CONDITIONS; repository-reported numerical evidence not independently rerun here]** ERRATUM_LAPLACE.md:19–25 records the audited failure scope; :32–45 withdraws the two m0=−4 historical-cell results, retains the frozen verdict because unaffected failing cells suffice, and explicitly says corrected held-out policy reruns were not done. One may retain that frozen tested-procedure verdict. One may not claim the corrected policy comparison or exact Bayesian decision rule failed in those cells.

## 8. Minimal falsifiable next tests, without a new acquisition search

1. **[PROVED test specification] Same-state channel test:** hold current Gaussian Q and target loss fixed; compute exact target-observation moments for deterministic sign, true probit sigma, logistic, and PEER probit 8/pi channels. Report absolute value/rank changes and query disagreement, especially in sigma=0/rough cells. Logistic moments can be quadrature or MC; deterministic/probit moments have Gaussian orthant formulas.
2. **[PROVED test specification] Same-Q update test:** derive Q(T_i=1|O_j=o) from its binary pair probabilities, and compare to each fantasy-refitted q'_i. Measure branch-weighted action excess risk, not only the martingale residual. This isolates update approximation while Q and channel stay fixed.
3. **[PROVED test specification] Scale test:** transform (mu,Sigma) to (c mu,c² Sigma) on frozen states. Sign scores must remain invariant, while fixed-noise PEER generally changes. This directly detects the scale blindness of sign-pair calibration.
4. **[PROVED test specification] Coherent-vs-refit factorial:** compare Bayes decisions from exact conditioning of the same Q to fresh fits under the same label weights; separately evaluate both against truth. Do not label the remaining difference missing information unless the channel and update factors are controlled.
5. **[PROVED test specification] Calibration audit:** score target-observation joint laws on the actual target/candidate pairs, on common states. Retain latent-sign pair scores as an auxiliary quantity. Monte Carlo from a model validates formulas, not real calibration.

## 9. Verified primary literature and novelty boundary

- **[KNOWN/PRIOR ART]** Roy & McCallum (2001), *Toward Optimal Active Learning through Monte Carlo Estimation of Error Reduction*, directly targets expected future error including 0–1 and log loss. Therefore “choose expected error reduction” is prior art; the useful local result is the binary-observation moment formula and its audit role. https://groups.csail.mit.edu/rrg/papers/icml01.pdf
- **[KNOWN/PRIOR ART]** Houlsby et al. (2011), *Bayesian Active Learning for Classification and Preference Learning*, expresses information gain through predictive entropies for GPCs (BALD). It supports the observation-entropy versus latent-information distinction, not equality of BALD and Hamming VOI. https://arxiv.org/abs/1112.5745
- **[KNOWN/PRIOR ART]** Bickford Smith et al. (2023), *Prediction-Oriented Bayesian Active Learning*, introduces EPIG, targeting information gain in predictions rather than parameters and incorporating target relevance. PEER is a target-weighted 0–1 Bayes-error objective, not an invention of prediction-oriented acquisition. https://proceedings.mlr.press/v206/bickfordsmith23a.html
- **[KNOWN/PRIOR ART]** Wen et al. (2021/2022), *From Predictions to Decisions: The Importance of Joint Predictive Distributions*, establishes that good marginals need not support good decisions; precise decision-relevant joint objects matter. https://arxiv.org/abs/2107.09224
- **[KNOWN/PRIOR ART]** Rasmussen & Williams (2006), *Gaussian Processes for Machine Learning*, Chapter 3, distinguishes logistic/probit likelihoods, exact posterior inference, and Gaussian Laplace approximations. The current-Gaussian/probit qualification above follows these standard distinctions. https://gaussianprocess.org/gpml/chapters/RW3.pdf
- **[KNOWN/PRIOR ART]** Hullermeier & Waegeman (2021), *Aleatoric and epistemic uncertainty in machine learning*, discusses model uncertainty and model misspecification separately from data stochasticity. A fitted stochastic likelihood does not empirically establish physical aleatoric noise. https://doi.org/10.1007/s10994-021-05946-3
- **[KNOWN/PRIOR ART]** Tang, Sloman & Kaski (2026), *Representative, Informative, and De-Amplifying: Requirements for Robust Bayesian Active Learning under Model Misspecification*, analyzes how misspecification and acquired-data shift affect generalization. Relevant context, not evidence that the specific Week 16 residual is identified. https://proceedings.mlr.press/v300/tang26d.html
- **[KNOWN/PRIOR ART]** Fudenberg, Romanyuk & Strack (2017), *Active learning with a misspecified prior*, studies Bayesian information acquisition when the true state has zero prior probability. Establishes prior work on subjective information and objective performance separation. https://economics.mit.edu/sites/default/files/2022-09/Active%20learning%20with%20a%20misspecified%20prior.pdf

No claim of literature-wide novelty is made for the elementary transfer bound, scale construction, common-noise extension, or finite counterexamples. Their role here is to make the thesis's interpretation falsifiable and correctly scoped.
