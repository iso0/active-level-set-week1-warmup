# Literature Notes: Active Level-Set Estimation with GP Classifiers
## Context: laser melt-pool Conduction/Keyhole boundary, inputs (P, VX, LS, ST), binary manual labels, physics coordinate h = P/√(VX·LS³)

Prepared via web search/fetch. Where full text was paywalled or blocked (noted explicitly), fields are filled from abstracts, secondary summaries (ResearchGate/Semantic Scholar/HAL listings), or press coverage — flagged accordingly. No formulas are invented; where a source did not give one, it is left as "not found in accessible text."

---

## 1. Keeley, Letham, Tymms, Sanders, Shvartsman (2023) — "A Semi-Parametric Model for Decision Making in High-Dimensional Sensory Discrimination Tasks"

1. **Citation**: Keeley, S., Letham, B., Tymms, C., Sanders, C., & Shvartsman, M. (2023). A Semi-Parametric Model for Decision Making in High-Dimensional Sensory Discrimination Tasks. *AAAI Conference on Artificial Intelligence* / arXiv:2302.01187. https://arxiv.org/abs/2302.01187 ; https://ojs.aaai.org/index.php/AAAI/article/view/25074
   (Note: author list confirmed from arXiv abstract page as Keeley, Letham, Tymms, Sanders, Shvartsman — the AAAI listing in the task prompt naming "Aoi, Pillow" was not corroborated; this appears to be a related but distinct NeurIPS 2021 workshop line by the same community, see below.)
2. **Model/latent object**: A classical 1-D psychometric function along the *intensity* dimension, p = σ(k·(x_intensity + c)), but the **slope k and offset/threshold c are themselves latent GPs indexed by the remaining "context" stimulus dimensions**: f_k ~ GP(m_k, Σ_k), f_c ~ GP(0, Σ_c) (RBF kernels, separate hyperparameters per GP). The combined latent surface is z(x) = f_k(x_context) ∘ (f_c(x_context) + x_intensity) (elementwise/Hadamard combination of slope-GP and offset-GP with the intensity coordinate).
3. **Observation model**: Binary forced-choice trials (2AFC/4AFC), y ~ Bernoulli(σ(z)), σ a sigmoid link (probit/logistic/Weibull-type).
4. **Acquisition function**: Two are used — (a) **ThresholdBALV**: Bayesian Active Learning by Variance applied to the posterior variance of the *implied threshold* x_r(x_context) = σ⁻¹(r)/k(x_context) − c(x_context) (i.e., variance of the psychometric threshold as a derived quantity of the two GPs); (b) **GlobalMI**, imported from Letham et al. (2022) (see below), applied over the threshold surface.
5. **Estimand**: The *threshold/boundary location* τ(x_context) itself (a derived nonlinear function of two latent GPs), not directly p or π — i.e., this is the closest example in the search set of "GP over a boundary/threshold surface with probit-linked binary observations," though the boundary here is parametrized explicitly via slope+offset GPs rather than as the zero-crossing of a single latent GP.
6. **Finite pool vs continuous**: Human psychophysics experiment; stimuli drawn from a continuous multi-dimensional context space, next-trial selection via continuous optimization of the acquisition surface (not restricted to a fixed finite pool in the main experiments, though grids are used for evaluation).
7. **Theory**: No sample-complexity or convergence theorems found in the accessible excerpt; contribution is model + empirical active-learning gains.
8. **Relation to probability margin/straddle/SUR**: Directly reuses GlobalMI from Letham et al. (2022) (an information-theoretic descendant of the straddle/SUR family); ThresholdBALV is a BALD/BALV-style variance criterion applied to the derived threshold rather than to raw p or π.
9. **Differentiator for a new method**: Keeley et al. put GPs on the *parameters* (slope, intercept) of a fixed parametric link along one privileged "intensity" axis and use human, non-deterministic binary responses; a new method for a deterministic simulator would instead put a single GP directly on the physics-normalized coordinate h (a designed 1-D sufficient statistic) with no separate slope/offset decomposition, and would exploit that repeated queries at the same input are noiseless (no trial-to-trial Bernoulli noise beyond mislabeling), changing the SUR/acquisition calculus substantially.

---

## 2. Letham, Guan, Tymms, Bakshy, Shvartsman (2022) — "Look-Ahead Acquisition Functions for Bernoulli Level Set Estimation"

1. **Citation**: Letham, B., Guan, P., Tymms, C., Bakshy, E., & Shvartsman, M. (2022). Look-Ahead Acquisition Functions for Bernoulli Level Set Estimation. *AISTATS 2022*, PMLR 151. https://proceedings.mlr.press/v151/letham22a/letham22a.pdf ; arXiv:2203.09751 (https://arxiv.org/abs/2203.09751); code: https://github.com/facebookresearch/bernoulli_lse
2. **Model/latent object**: Latent GP f(x) ~ GP(0,k) with RBF kernel; inference via variational GP classification (Hensman et al. 2015 style).
3. **Observation model**: y ~ Bernoulli(z(x)), z(x) = Φ(f(x)) (probit link).
4. **Acquisition function**: All target the **level-set posterior** π(x) = P(f(x) > γ | D) = Φ(μ(x)/√(1+σ(x)²)) type expression, using **Theorem 1**, a closed-form look-ahead posterior for π after a hypothetical new observation:
   π(x_q | D_{n+1}(x*,y*=1)) = BvN(a*, b_q; −σ_{q*}/(σ_q√(1+σ*²))) / Φ(a*),
   with a* = √(μ*/(1+σ*²)), b_q = (γ−μ_q)/σ_q, BvN = bivariate normal CDF. From this:
   - **LocalSUR**: min(π(x*),1−π(x*)) − E_{y*}[misclassification at x* after observing y*] (one-step lookahead of the local classification-error/probability-margin objective).
   - **GlobalSUR**: Σ_{x_q∈G}[min(π(x_q),1−π(x_q))] − E_{y*}[Σ_{x_q∈G} min(π,1−π) after observing (x*,y*)] (global, integrated over a reference set G).
   - **LocalMI**: H_b(π(x*)) − E_{y*}[H_b(π(x*|D_{n+1}))], binary entropy reduction at the candidate itself.
   - **GlobalMI**: Σ_{x_q∈G} H_b(π(x_q)) − E_{y*}[Σ_{x_q∈G} H_b(π(x_q|D_{n+1}))], i.e. expected reduction in total entropy of the level-set indicator over G.
   - **EAVC** (Expected Absolute Volume Change): E_{y*}[|V_ε(D_n) − V_ε(D_{n+1})|], the expected absolute change in the volume of the estimated excursion set {π > ½} (or a Vorob'ev-style level ε).
5. **Estimand**: All five target the **posterior latent-set membership π(x) = P(f(x) > γ)** (i.e. an epistemic quantity about the *classifier's own set*, not the aleatoric predictive label probability p = E_x[σ(f)]).
6. **Finite pool vs continuous**: Continuous domains (ℝ^d, d = 2, 6, 8 tested); acquisition optimized by gradient-based continuous optimization over x*, with a reference set G (a fixed/quasi-random point set) used only to evaluate the "global" summary, not to restrict candidates.
7. **Theory**: No sample-complexity bounds; the paper's main formal result is the closed-form look-ahead posterior (Theorem 1) enabling fast (non-nested-Monte-Carlo) computation of all five acquisition functions via qMC integration.
8. **Relation to probability margin/straddle/SUR**: LocalSUR/GlobalSUR are explicitly SUR (stepwise uncertainty reduction, à la Bect et al. 2012 / Chevalier et al. 2014) criteria built on the *misclassification-probability margin* min(π,1−π); the paper's key empirical finding is that **local (pointwise) versions—closest in spirit to the classic "straddle" heuristic—pathologically over-sample near the domain boundary in higher dimensions**, and that global (integrated) look-ahead is needed.
9. **Differentiator**: Letham et al. treat π(x) (or 1−π(x)) symmetrically as a set-membership uncertainty and use a fixed reference-set G for global summaries; a physics-coordinate approach could instead define the reference measure directly along h (a 1-D sufficient physics statistic) rather than over the full 4-D (P,VX,LS,ST) space, potentially making GlobalSUR/GlobalMI cheaper and more targeted to the actual boundary manifold.

---

## 3. Zhao, Dougherty, Yoon, Alexander, Qian (2021) — "Efficient Active Learning for Gaussian Process Classification by Error Reduction"

1. **Citation**: Zhao, G., Dougherty, E. R., Yoon, B.-J., Alexander, F. J., & Qian, X. (2021). Efficient Active Learning for Gaussian Process Classification by Error Reduction. *NeurIPS 2021*. https://proceedings.neurips.cc/paper/2021/hash/50d2e70cdf7dd05be85e1b8df3f8ced4-Abstract.html ; PDF: https://proceedings.neurips.cc/paper/2021/file/50d2e70cdf7dd05be85e1b8df3f8ced4-Paper.pdf ; code: https://github.com/QianLab/NR_SMOCU_SGD_GPC
2. **Model/latent object**: Standard binary GPC: f ~ GP(μ,k), posterior approximated by Expectation Propagation (EP).
3. **Observation model**: p(y=1|x,f)=Φ(f(x)); the paper also explicitly models **noisy/mislabeled observations** (constant label-flip probabilities 0.0–0.2 in experiments), which is directly relevant to a "binary manual labels" setting.
4. **Acquisition function**: Minimizes **SMOCU** (Smooth MOCU, a differentiable surrogate for Mean Objective Cost of Uncertainty), replacing MOCU's max operator with LogSumExp:
   U^S(x*) = E_{x_s}{ E_{y*|x*}[ LogSumExp(k·p(y_s|x_s,x*,y*))/k ] − LogSumExp(k·p(y_s|x_s))/k }.
   This is optimized both over a finite pool and, via gradient-based query synthesis, over continuous input.
5. **Estimand**: **Classification error** (MOCU = expected increase in Bayes classification error due to model uncertainty) — a decision-theoretic, 0/1-loss-flavored estimand, distinct from both p and π, and closer to the "finite-pool expected 0-1 error reduction" family (Roy & McCallum-style) but adapted to GPC with EP.
6. **Finite pool vs continuous**: Both — pool-based sampling and continuous query synthesis are demonstrated.
7. **Theory**: No formal sample-complexity/regret bounds; contribution is computational (constant/low-order-time approximation of the joint predictive integral vs. naive O(n³) EP updates) plus robustness to label noise.
8. **Relation to probability margin/straddle/SUR**: MOCU/SMOCU generalizes "expected error reduction" style criteria (cf. Roy & McCallum 2001) to the GPC/EP setting; conceptually related to SUR (both are one-step-lookahead expected-loss-reduction criteria) but the loss is the *Bayes decision cost* rather than the excursion-probability margin.
9. **Differentiator**: SMOCU explicitly handles noisy/flipped labels via a decision-theoretic (MOCU) objective rather than a geometric/entropy objective on π or p; a physics-coordinate method could adopt this robustness-to-mislabeling machinery while replacing MOCU's implicit finite-label-set decision cost with a boundary-location loss (e.g., expected squared error in the estimated crossing point τ along h).

---

## 4. Bect, Ginsbourger, Li, Picheny, Vazquez (2012) — "Sequential design of computer experiments for the estimation of a probability of failure"

1. **Citation**: Bect, J., Ginsbourger, D., Li, L., Picheny, V., & Vazquez, E. (2012). Sequential design of computer experiments for the estimation of a probability of failure. *Statistics and Computing*, 22(3), 773–793. https://link.springer.com/article/10.1007/s11222-011-9241-4 ; arXiv:1009.5177 (https://arxiv.org/abs/1009.5177); HAL: https://hal.science/hal-00689580 (full-text blocked by bot-protection on fetch; extracted from arXiv PDF instead).
2. **Model/latent object**: GP prior on the (assumed deterministic) simulator output f; excursion set Γ = {x : f(x) > u}; probability of failure α = P(X ∈ Γ) under a known input measure.
3. **Observation model**: **Deterministic, noiseless** simulator evaluations — the paper explicitly frames f as "expensive-to-evaluate" but exact, not a Bernoulli-labeled classifier.
4. **Acquisition function**: SUR criteria of the general form (Eq. 26 in the paper):
   X_{n+1} = argmin_{1≤k≤m} Σ_i Σ_q w_q' v_{n+1}(Y_j; Y_k, z_{n+1,q}(Y_k)),
   where v_{n+1} is a **one-step-lookahead expectation of a global uncertainty functional** — either the integrated **misclassification probability** τ_n(x) = min(p_n(x), 1−p_n(x)) (p_n(x) = current GP-based probability that f(x)>u) or the **variance of the excursion-set-indicator / excursion volume**. Four concrete SUR variants are derived (based on which uncertainty functional — misclassification probability vs. variance of the excess/excursion indicator — is integrated).
5. **Estimand**: Primarily the **scalar probability of failure α** (an integral over the input measure of the excursion-set indicator), with the excursion set Γ and its Vorob'ev-type volume as an intermediate object — i.e., a *global scalar/measure* target, not a pointwise p or π, and not directly the boundary location per se (though minimizing τ_n(x)=min(p,1−p) concentrates sampling at the decision frontier).
6. **Finite pool vs continuous**: Continuous domain ℝ^d with a known probability measure; SUR criterion optimized continuously (candidate set can be continuous or a large discretization for numerical optimization).
7. **Theory**: No formal convergence rate; the paper instead gives an empirical illustration that Monte Carlo alone needs ~1/(δ²α) evaluations for standard deviation δ on α (e.g., 50,000 evaluations for α ≈ 0.002), motivating the sequential-design alternative; ~36 evaluations suffice on benchmark problems to get <1% relative error after a modest initial design.
8. **Relation to probability margin/straddle/SUR**: This is the **origin paper of the "SUR" framework** for excursion/level-set problems; its misclassification-probability criterion τ_n(x)=min(p_n,1−p_n) is exactly the "probability margin" quantity that later straddle-family and Letham-style LocalSUR/GlobalSUR criteria build on and generalize to explicit Bernoulli-observation settings.
9. **Differentiator**: Bect et al. assume **noiseless, deterministic** f-evaluations and target a scalar probability of failure α (an *integral* functional), not a per-point Bernoulli label; a physics-coordinate method for binary manual labels needs the Bernoulli/probit observation model of Letham et al. layered onto (or in place of) Bect et al.'s SUR machinery, and should target the boundary/threshold τ(h) rather than α.

---

## 5. Shekhar & Javidi (2019) — "Multiscale Gaussian Process Level Set Estimation"

1. **Citation**: Shekhar, S., & Javidi, T. (2019). Multiscale Gaussian Process Level Set Estimation. *AISTATS 2019*, PMLR 89:3283–3291. https://proceedings.mlr.press/v89/shekhar19a.html ; arXiv:1902.09682 (https://arxiv.org/abs/1902.09682).
2. **Model/latent object**: f ~ GP prior over 𝒳 = [0,1]^D; a hierarchical sequence of spatial partitions (multiscale tree) used to adaptively refine resolution near the estimated boundary.
3. **Observation model**: Noisy continuous regression: y = f(x) + N(0,σ²), σ² known — **not** a Bernoulli/probit classifier model.
4. **Acquisition function**: At each level, points are chosen to maximize max({ū_t(x)−τ}, {τ−l̄_t(x)}) where ū_t, l̄_t are upper/lower confidence bounds combining posterior mean/variance and a variation bound over the local partition cell — a **multiscale generalization of the straddle rule** (the authors explicitly relate their rule to Bryan et al.'s straddle heuristic).
5. **Estimand**: The level set S_τ = {x : f(x) > τ} and its **boundary discrepancy** L(Ŝ_τ, S_τ) (a set-symmetric-difference-type loss), i.e., boundary/set-location accuracy rather than pointwise p or π.
6. **Finite pool vs continuous**: Continuous domain [0,1]^D, discretized adaptively via the multiscale partition (not a fixed finite pool).
7. **Theory**: **Theorem 1** gives high-probability bounds on the discrepancy loss: (i) dimension-dependent Õ(n^{−α/(D̃+2α)}) and (ii) information-gain-dependent Õ(β_n√(J_n/n)), under standard GP-bandit-style kernel conditions (SE/Matérn/Rational-Quadratic covariance families, conditions C1–C2 on smoothness), claimed strictly tighter than prior generic maximum-information-gain bounds because they exploit the *structured* (multiscale, non-i.i.d.) sampling pattern.
8. **Relation to probability margin/straddle/SUR**: Direct multiscale extension of the straddle heuristic (Bryan et al. 2005/Gotovos et al. 2013), adding hierarchical partitioning for improved high-probability guarantees; not framed as SUR.
9. **Differentiator**: This is a **regression-noise, continuous-output** level-set method with formal minimax-flavored rates; a physics-coordinate method for **binary manual labels** would need either a Bernoulli/probit reformulation of these multiscale confidence bounds, or would instead motivate exactly the "censored continuous-output depth regression" alternative (using an underlying continuous quantity — e.g. simulated melt-pool depth/keyhole depth ratio — with the binary label as a censored/thresholded observation of it) so that Shekhar–Javidi-style regression-based guarantees become directly applicable.

---

## 6. Mason, Camilleri, Mukherjee, Jamieson, Nowak, Jain (2022) — "Nearly Optimal Algorithms for Level Set Estimation"

1. **Citation**: Mason, B., Camilleri, R., Mukherjee, S., Jamieson, K., Nowak, R., & Jain, L. (2022). Nearly Optimal Algorithms for Level Set Estimation. *AISTATS 2022*, PMLR 151. https://proceedings.mlr.press/v151/mason22a.html ; arXiv:2111.01768 (https://arxiv.org/abs/2111.01768).
2. **Model/latent object**: RKHS-bandit-style linear/kernel model: f(x) ≈ ⟨θ*, φ(x)⟩_ℋ with an allowed model-misspecification slack h ≥ 0 (not a full nonparametric GP posterior — an RKHS/linear-bandit reduction).
3. **Observation model**: Noisy scalar regression y = f(x) + η, η zero-mean, E[η²] ≤ σ², f bounded in [−B,B] (not Bernoulli).
4. **Acquisition function**: **G-optimal (and a "MILK" pairwise-difference) experimental design**: λ* = argmin_λ max_x ‖φ(x)‖²_{A(λ)⁻¹}; two algorithms, **MELK** (explicit-threshold level-set estimation) and **MILK** (implicit level-set / pairwise-comparison design over difference features φ(x)−(1−ε)φ(x')), both phased (successive elimination) designs.
5. **Estimand**: Correct ε-accurate classification of each finite-pool point relative to a threshold α (explicit) or relative to the max/implicit level (MILK) — i.e., a **per-point, finite-pool 0/1 classification accuracy** target with an (ε,δ)-PAC guarantee, not p or π and not a continuous boundary curve.
6. **Finite pool vs continuous**: **Explicitly pool-based**: finite X ⊂ ℝ^d.
7. **Theory**: Instance-dependent, non-asymptotic sample-complexity bound (Theorem 3.3):
   T_δ ≤ (B²+σ²)·min_λ max_x ‖φ(x)‖²_{A(λ)⁻¹} / max{(φ(x)ᵀθ*−α)², β̃²} · log((Δ_min∨β̃)⁻¹) · log(|X|/δ),
   claimed to **match information-theoretic lower bounds** in the linear-kernel regime; assumptions are boundedness of f, sub-Gaussian-type noise variance bound, and (for the RKHS extension) a bounded misspecification term h.
8. **Relation to probability margin/straddle/SUR**: Not framed via straddle/SUR language; instead an experimental-design/bandit (G-optimal design + elimination) framework, giving PAC-style finite-sample guarantees that the straddle/SUR literature generally lacks.
9. **Differentiator**: This gives the field's most rigorous **finite-pool sample-complexity theory**, but for continuous (regression) observations, not Bernoulli/manual binary labels; a "finite-pool expected 0-1 error reduction for GPC" method would need to adapt this G-optimal/elimination machinery (or its information-theoretic lower bound) to the Bernoulli-GPC observation model instead of linear/RKHS regression.

---

## 7. Rodríguez & Ludkovski (2020) — "Probabilistic Bisection with Spatial Metamodels"

1. **Citation**: Rodríguez, S., & Ludkovski, M. (2020). Probabilistic bisection with spatial metamodels. *European Journal of Operational Research*, 286(2), 588–603. https://www.sciencedirect.com/science/article/abs/pii/S0377221720302630 ; arXiv:1807.00095 (https://arxiv.org/abs/1807.00095, https://arxiv.org/pdf/1807.00095).
2. **Model/latent object**: A **Probabilistic Bisection Algorithm (PBA)** root-finder, generalized ("G-PBA") to a spatial setting where the oracle's error probability is unknown and location-dependent, estimated online via a **spatial metamodel** — options explored include Binomial GPs (B-GP), and polynomial/kernel/spline logistic regression for the oracle's local Bernoulli success-probability surface.
3. **Observation model**: **Binary, noisy oracle comparisons** ("is the root to the left or right of query point x?") — Bernoulli responses whose success probability varies smoothly with x (the "spatial" oracle), directly analogous to binary regime-classification labels with a location-dependent reliability.
4. **Acquisition function**: A family of **sampling policies balancing learning the oracle's spatial reliability vs. learning the root location**; one variant is explicitly built from "active learning with B-GPs," including a **look-ahead predictive-variance criterion** analogous to one-step SUR for the root/threshold location (exact formula not recovered from accessible excerpt).
5. **Estimand**: **Root/boundary location** τ directly (a 1-D or low-dimensional root-finding target under noisy binary comparisons), making this one of the closer analogues in the search set to "locate a 1-D threshold τ(h) from binary comparisons."
6. **Finite pool vs continuous**: Framed for continuous 1-D (or low-D) root search with a sequential bisection-style sampling scheme, not a fixed finite pool.
7. **Theory**: No explicit convergence-rate result found in the accessible excerpt (full PDF not deeply parsed); PBA classically has geometric contraction of the root's posterior credible interval under a fixed known oracle-error rate, and the paper's contribution is relaxing that fixed-rate assumption via the spatial metamodel — a formal rate for the generalized (unknown, spatial) case was not confirmed here.
8. **Relation to probability margin/straddle/SUR**: Conceptually a decision-theoretic sequential-design problem like SUR (choose next query to most reduce root-location uncertainty), but developed independently within the operations-research PBA tradition rather than the kriging/GP-classification SUR literature; not tied to "straddle."
9. **Differentiator**: PBA/G-PBA models the *oracle's reliability* as spatially varying and unknown — directly relevant if manual labels near h ≈ τ are noisier/less reliable than labels far from the boundary; a physics-coordinate method could adopt this oracle-reliability model instead of assuming a fixed Bernoulli/probit noise level uniform in x.

---

## 8. Li & Ghosal (2017) — "Bayesian Detection of Image Boundaries"

1. **Citation**: Li, M., & Ghosal, S. (2017). Bayesian detection of image boundaries. *The Annals of Statistics*, 45(5), 2190–2217. doi:10.1214/16-AOS1523. https://arxiv.org/abs/1508.05847 ; https://projecteuclid.org/euclid.aos/1509436832
2. **Model/latent object**: A **nonparametric Bayesian prior directly on the boundary function** itself: the boundary of a 2D region is represented as a function on the circle 𝕊¹ (radius as a function of angle, i.e., a star-shaped boundary curve), given a prior via a (rescaled) squared-exponential GP or finite random series on 𝕊^{d−1} for general dimension d.
3. **Observation model**: Not confirmed precisely from the accessible excerpt (noisy image observations are referenced, but whether these are per-pixel intensities with additive noise, or the binary inside/outside indicator with flip noise, was not stated in the retrieved text) — flagged as **unconfirmed**; the framework is presented generally as boundary detection from noisy image data.
4. **Acquisition function**: **None** — this is a static (non-sequential/non-active-learning) Bayesian estimation paper; no acquisition function exists here.
5. **Estimand**: The **boundary curve/manifold itself**, τ(angle) — i.e., a direct GP-type prior on the boundary location function, which is conceptually the closest analogue in the whole search list to "a GP over the boundary location τ(z)" (here z = angle rather than a physics coordinate), though with no sequential-design or classifier-likelihood component.
6. **Finite pool vs continuous**: N/A (not an active-learning paper); works with a fixed observed image/dataset.
7. **Theory**: The paper's central contribution is **posterior contraction rate theory**: derives (near-)minimax-optimal contraction rates for the boundary estimator, adaptive to the (Hölder-type) smoothness of the true boundary, under the nonparametric GP/series prior.
8. **Relation to probability margin/straddle/SUR**: Not related; this is a frequentist-Bayesian nonparametric-statistics contraction-rate paper, not an active-learning/acquisition-function paper.
9. **Differentiator**: Li & Ghosal directly parametrize and place a prior on the **boundary function** rather than on a latent classifier surface whose zero-crossing implies a boundary; a "GP over τ(h)" method for the melt-pool problem is structurally exactly this idea (boundary-as-GP) but would need to (a) add a genuine observation/likelihood model connecting binary labels to τ(h) [e.g., y=1 iff h < τ, observed with noise] and (b) add a sequential acquisition rule, both of which are provided by other papers here (Letham et al.; Bect et al.) but absent in Li & Ghosal.

---

## 9. Riihimäki & Vehtari (2010) — "Gaussian Processes with Monotonicity Information"

1. **Citation**: Riihimäki, J., & Vehtari, A. (2010). Gaussian processes with monotonicity information. *AISTATS 2010*, PMLR 9. http://proceedings.mlr.press/v9/riihimaki10a/riihimaki10a.pdf ; https://proceedings.mlr.press/v9/riihimaki10a.html
2. **Model/latent object**: Standard GP prior on f, augmented with a **joint GP over f and its derivative** ∂f/∂x (derivative and function-value covariances derived jointly from the same, e.g. squared-exponential, kernel).
3. **Observation model**: Ordinary data likelihood (Gaussian for regression or probit/logit for classification) **plus virtual derivative "observations"** enforcing monotonicity via a probit-type likelihood on the derivative: p(m_d^{(i)} | ∂f^{(i)}/∂x_d^{(i)}) = Φ(∂f^{(i)}/∂x_d^{(i)} / ν), soft-constraining the derivative sign with slack ν.
4. **Acquisition function**: **None** — virtual monotonicity points are placed at fixed pre-chosen locations (grid points or the observed inputs), not chosen adaptively; this is not an active-learning paper.
5. **Estimand**: The full regression/classification function f itself, regularized to (approximately) respect known monotonicity in one or more inputs; inference via Expectation Propagation.
6. **Finite pool vs continuous**: N/A (no active-learning component).
7. **Theory**: None (methodological/inference paper).
8. **Relation to probability margin/straddle/SUR**: Not related directly, but methodologically relevant: the melt-pool problem likely has known monotonicity in P (higher power → more likely Keyhole) or in the physics coordinate h itself; Riihimäki–Vehtari's virtual-derivative-observation machinery is a candidate mechanism for injecting that physics prior (monotonicity of the label probability in h) into a GPC, independent of and complementary to any acquisition-function choice.
9. **Differentiator**: A new method could use Riihimäki–Vehtari-style virtual monotonicity constraints along h to make the GP classifier's implied boundary τ(h) provably single-crossing/well-defined, then layer an active/SUR acquisition rule (from Letham et al. or Bect et al.) on top — something none of these individual papers already combine for this deterministic-simulator setting.

---

## 10. Hardcastle, O'Mullan, Arróyave, Vela (2025) — "Physics-informed Gaussian process classification for constraint-aware alloy design"

1. **Citation**: Hardcastle, C., O'Mullan, R., Arróyave, R., & Vela, B. (2025). Physics-informed Gaussian process classification for constraint-aware alloy design. *Digital Discovery* (RSC), DOI: 10.1039/D5DD00084J. https://pubs.rsc.org/en/content/articlelanding/2025/dd/d5dd00084j ; open-access full text: https://pubs.rsc.org/en/content/articlehtml/2025/dd/d5dd00084j ; arXiv:2502.11369 (https://arxiv.org/abs/2502.11369, https://arxiv.org/html/2502.11369v1).
2. **Model/latent object**: GPC built by training a standard **GP regressor** on binary labels remapped to {−5,+5} (a Gaussian-likelihood surrogate for the true Bernoulli likelihood — a Laplace/least-squares-style approximation rather than EP/probit GPC), then passing the posterior mean through a **logistic sigmoid**; crucially, the **GP prior mean function is physics-informed** — set from CALPHAD phase-stability predictions or a Curtin–Maresca strength model — rather than zero.
3. **Observation model**: Binary class labels y ∈ {−5,+5} fit with a Gaussian (not Bernoulli/probit) likelihood as a computational convenience; multi-class handled by one-vs-rest + softmax normalization.
4. **Acquisition function**: **Maximum Shannon entropy** of the predictive class-probability distribution (a standard entropy-based active-learning criterion, not SUR/straddle/MI-lookahead).
5. **Estimand**: The **predictive label probability** p(class | x, D) directly (sigmoid of the latent posterior mean) — i.e., this targets p, not π, and has no explicit boundary-location object.
6. **Finite pool vs continuous**: Both demonstrated — ternary/quaternary alloy composition pools (discretized at 5 at% resolution) and a continuous strength-space (W–Nb–Ta) case.
7. **Theory**: None — purely a modeling + entropy-acquisition empirical demonstration; the paper explicitly substitutes a Gaussian likelihood for the intractable sigmoid likelihood as a heuristic approximation to standard GPC.
8. **Relation to probability margin/straddle/SUR**: Uses plain entropy sampling, not straddle/SUR; the **novelty is the physics-informed mean function**, not the acquisition function.
9. **Differentiator**: This paper's central idea — injecting known physics as the **GP prior mean** rather than modifying the kernel/coordinate — is directly transferable to the melt-pool problem (e.g., prior mean = sign(h − h₀) for a known approximate threshold h₀) and is complementary to (not competing with) a genuinely probit-likelihood GPC with a SUR/straddle acquisition function, which this paper does not use.

---

## 11. Masinelli et al. (2025) — "Autonomous exploration of the PBF-LB parameter space: An uncertainty-driven algorithm for automated processing map generation"

1. **Citation**: Masinelli, G. et al. (2025). Autonomous exploration of the PBF-LB parameter space: An uncertainty-driven algorithm for automated processing map generation. *Additive Manufacturing*, DOI: 10.1016/j.addma.2025.104677. https://www.sciencedirect.com/science/article/pii/S2214860425000417 (full text blocked by publisher robots.txt/paywall on all fetch attempts — details below drawn only from press coverage: EPFL/Empa press release via ScienceDaily https://www.sciencedaily.com/releases/2025/05/250527124629.htm and EurekAlert https://www.eurekalert.org/news-releases/1085181).
2. **Model/latent object**: **Not independently confirmed from primary text** (blocked). Press material describes "a machine learning algorithm" that learns to classify the laser processing regime (**conduction vs. keyhole mode**, i.e. exactly the melting/vaporization distinction in this project) from **optical/photodiode sensor signals** already present on production laser machines, and that sequentially chooses the next experimental parameter setting.
3. **Observation model**: Binary conduction/keyhole classification of each trial run (analogous structure to this project's setup), inferred from process sensor signals rather than post-hoc manual labeling — **exact likelihood model (GP probit vs. other classifier) not confirmed from accessible text**.
4. **Acquisition function**: Press material names it an "uncertainty-driven algorithm" that picks the next preliminary experiment's parameters based on current classification uncertainty; reported to **cut the number of required preliminary experiments by roughly two-thirds**. Exact functional form not available (paywalled).
5. **Estimand**: The **conduction/keyhole process-map boundary** — directly the same physical target as this project, making this the single closest applied-domain match found. Whether it targets p, π, or boundary location explicitly could not be confirmed from accessible text.
6. **Finite pool vs continuous**: Not confirmed (real experimental laser trials — likely a continuous parameter search over machine-controllable settings, i.e., "continuous" in nature though physically discretized by machine resolution).
7. **Theory**: Not confirmed; no indication of formal sample-complexity results in secondary coverage.
8. **Relation to probability margin/straddle/SUR**: Not confirmed from accessible text.
9. **Differentiator**: Masinelli et al. appear to close the loop with **real-time sensor-based** (not manually/post-hoc labeled) classification and hardware (FPGA) deployment for in-process control, whereas this project's binary labels come from **manual, offline** inspection of a **deterministic simulator** (no measurement noise, but human labeling effort is the bottleneck) — a genuinely different observation-cost/noise regime that should be stated explicitly as the point of departure. **Caveat: full methodological comparison is not possible without primary-text access; this entry should be revisited if paywalled access becomes available.**

---

## 12. Zhu et al. (2024) — "Active Learning for Discovering Complex Phase Diagrams with Gaussian Processes"

1. **Citation**: Zhu et al. (2024). Active Learning for Discovering Complex Phase Diagrams with Gaussian Processes. arXiv:2409.07042. https://arxiv.org/abs/2409.07042 ; https://arxiv.org/html/2409.07042
2–8. **Not confirmed in detail**: WebFetch of the HTML full text returned only a partial/generic summary (a "Bayesian active learning algorithm" with "a novel acquisition function that assesses both the impact and likelihood of the next observation"; baselines include SVM-based methods and grid search; the method is said to extend to higher-dimensional, multi-phase diagrams). The precise GP model (classification vs. regression), observation model, exact acquisition formula, estimand (p vs. π vs. boundary), finite-pool-vs-continuous framing, and any theory were **not retrievable from the accessible excerpt** and should be treated as open/unconfirmed pending a direct read of the PDF.
9. **Differentiator (tentative)**: Framed for materials phase diagrams (potentially multi-class, not strictly binary), so even before confirming details, a difference from this project is the assumption of a designed, continuous, typically low-noise phase-map generation process (e.g., DFT/CALPHAD) versus this project's deterministic-simulator-with-manual-binary-labeling setup.

---

## 13. Fan et al. (2026) — "Bayesian active learning to accelerate high throughput phase diagram exploration" (BALPI)

1. **Citation**: Fan, M., Wang, Y., Vazquez, G., Zhou, R., Karaman, I., Arróyave, R., & Qian, X. (2026). Bayesian active learning to accelerate high throughput phase diagram exploration. *Digital Discovery* (RSC), DOI: 10.1039/D5DD00459D. https://pubs.rsc.org/dd/article/5/6/2478/1259050 ; open-access HTML: https://pubs.rsc.org/en/content/articlehtml/2026/dd/d5dd00459d
2. **Model/latent object**: "BALPI" = modular platform offering **two interchangeable latent models**: (a) a GP **classifier** on binary phase labels y ∈ {0,1}, and (b) a GP **regressor** on continuous phase-fraction scores s ∈ [0,1], both with RBF kernels and empirical-Bayes hyperparameters.
3. **Observation model**: (a) Bernoulli likelihood with sigmoid link for the classifier variant; (b) Gaussian likelihood for the continuous phase-fraction variant.
4. **Acquisition function**: Two strategies — **S-MOCU** (Soft-MOCU, LogSumExp-relaxed decision-theoretic cost — directly descended from Zhao et al. 2021 above, and cited as such) and an **extended straddle ("e-straddle")**: U_{e-straddle}(x) = −g(|μ(x) − τ|) + β·σ(x), where τ is the decision threshold, β an exploration weight, and g(·) a transform — i.e., a generalized version of the classic straddle formula with a nonlinear transform on the margin term.
5. **Estimand**: The **phase stability boundary/landscape** — i.e., boundary location, addressed operationally through the S-MOCU (decision-cost) and e-straddle (margin) criteria.
6. **Finite pool vs continuous**: **Continuous domain** — acquisition optimized densely over compositional/thermodynamic space, not restricted to a fixed discretized pool.
7. **Theory**: Framed via a Bayesian decision-theoretic objective (minimizing an integrated epistemic-uncertainty functional, "minimize ∫σ²(x)dx" as a stated relaxation), but the paper is explicit that **no formal theoretical guarantees are proven** — the approach is heuristic/empirical.
8. **Relation to probability margin/straddle/SUR**: Directly and explicitly builds on both the **straddle** heuristic (generalizing it to "e-straddle") and **MOCU/SMOCU** (Zhao et al. 2021), i.e., is one of the few works in this set that self-consciously bridges the two families.
9. **Differentiator**: BALPI offers a direct template for **dual classifier/regressor latent models with switchable acquisition (S-MOCU vs. e-straddle)** for a materials phase-boundary problem; a melt-pool method could adopt this dual-model design but would need to add (i) a genuine physics-coordinate (h) reduction of the input space, which BALPI does not use (it works in raw composition/T/P space), and (ii) the Letham-style closed-form π(x) look-ahead machinery, which BALPI does not use (S-MOCU/e-straddle are not full SUR criteria on π).

---

## 14. Menz, Munoz-Zuniga, Sinoquet — "Estimation of simulation failure set with active learning based on Gaussian Process classifiers and random set theory"

1. **Citation**: Menz, M., Munoz-Zuniga, M., & Sinoquet, D. Estimation of simulation failure set with active learning based on Gaussian Process classifiers and random set theory. *Structural Safety* (Elsevier, ISSN 0167-4730), 2025, DOI/pii S0167473025000359. https://www.sciencedirect.com/science/article/abs/pii/S0167473025000359 (paywalled/robots-blocked on fetch); preprint/HAL: https://hal.science/hal-03848238 and https://ifp.hal.science/hal-05293017v1 (both blocked by Anubis bot-protection on fetch); associated software: CRAN package **ARCHISSUR** ("Active Recovery of a Constrained and Hidden Set by Stepwise Uncertainty Reduction Strategy"), https://cran.r-project.org/web/packages/ARCHISSUR/ ; talk abstract accessible at https://l2s.centralesupelec.fr/en/events/uqsay-71/.
2. **Model/latent object**: A GP classifier used to model a **hidden binary constraint** (e.g., "does the simulation crash/fail?") as a latent GP with a classification likelihood; the failure/hidden-constraint set is treated via **random set theory** (i.e., as a random closed set whose expectation, e.g. Vorob'ev expectation, and variability are estimated from the GPC posterior — consistent with the Bect/Chevalier/Azzimonti excursion-set tradition, extended here to the classification/binary-observation case).
3. **Observation model**: **Binary observations only** (success/failure of the simulation) — explicitly noted in the talk abstract: "an adaptive strategy to learn the hidden constraint at a reduced numerical cost based only on a limited number of binary observations," matching this project's Bernoulli/manual-label setting closely.
4. **Acquisition function**: **Stepwise Uncertainty Reduction (SUR)** adapted to classification, with "a numerically effective formulation of the enrichment criterion suited for classification" (i.e., a SUR criterion computed via the GPC posterior rather than a GPR posterior as in Bect et al. 2012/Chevalier et al. 2014) — exact closed-form not retrievable due to paywall/bot-block.
5. **Estimand**: The **hidden constraint/failure set** itself (a random-set object), extended to downstream use in metamodeling and constrained optimization under the hidden constraint.
6. **Finite pool vs continuous**: Framed for continuous input domains (as with the rest of the SUR/excursion-set literature; simulation runs are chosen by continuous optimization of the SUR criterion), not a fixed finite pool.
7. **Theory**: Not confirmed from accessible text (both HAL preprints were blocked); no explicit note of formal convergence theory found in secondary sources.
8. **Relation to probability margin/straddle/SUR**: This is **the direct classification-likelihood extension of the Bect et al. (2012)/Chevalier et al. (2014)/Azzimonti et al. (2021) SUR-for-excursion-sets lineage**, replacing GP-regression-based excursion estimation with GP-classification-based random-set estimation from purely binary data — arguably the single closest prior-art match in this entire list to "SUR-based active learning for a binary-labeled level set," short of Letham et al. (2022).
9. **Differentiator**: Menz et al. target a general **hidden constraint/failure region** in arbitrary input dimension without a physics-informed coordinate reduction; a melt-pool method would add the h = P/√(VX·LS³) reduction and could directly compare against Menz et al.'s GPC-SUR criterion as a strong non-physics-informed baseline.

---

## 15. Wu, Sanders, Letham, Guan (2025) — "Mixed Likelihood Variational Gaussian Processes"

1. **Citation**: Wu, K., Sanders, C., Letham, B., & Guan, P. (2025). Mixed Likelihood Variational Gaussian Processes. arXiv:2503.04138. https://arxiv.org/abs/2503.04138 ; https://arxiv.org/pdf/2503.04138
2. **Model/latent object**: A single shared latent GP f(x) whose outputs feed **multiple different likelihoods simultaneously** (e.g., Bernoulli for one data type, Gaussian for another, plus a newly proposed Likert-scale likelihood), combined in one ELBO: log-likelihood decomposed as a sum across T heterogeneous data "types" sharing the same latent function.
3. **Observation model**: Explicitly heterogeneous/mixed — e.g., some observations y^(1) are continuous regression labels, others y^(2) are binary classification labels, all explained by the same underlying f.
4. **Acquisition function**: Reuses **GlobalMI** and **EAVC** from Letham et al. (2022) directly, now applied to the mixed-likelihood posterior, to do **Bernoulli level-set active learning while also exploiting auxiliary continuous or ordinal data** to accelerate convergence.
5. **Estimand**: Same as Letham et al. (2022) — the **latent-set membership π(x) = P(f(x) > γ)** for the binary/level-set task — but now informed by additional non-binary "side" observations sharing the same latent surface.
6. **Finite pool vs continuous**: Continuous domain, consistent with the Letham et al. (2022) experimental framework this paper extends.
7. **Theory**: None beyond the ELBO derivation; empirical demonstration of variance/label-efficiency gains from mixing likelihood types.
8. **Relation to probability margin/straddle/SUR**: Directly builds on and reuses Letham et al.'s GlobalMI/EAVC SUR-family criteria; the paper's novelty is the **mixed-likelihood latent-sharing model**, not a new acquisition function.
9. **Differentiator**: This is highly relevant if any **auxiliary continuous measurement** exists alongside the binary conduction/keyhole label (e.g., a simulated melt-pool depth, aspect ratio, or an internally computed physics quantity related to h) — a mixed-likelihood GP could jointly use continuous simulator outputs and manual binary labels on the same latent surface, which none of the pure-Bernoulli-GPC papers above (Letham et al.; Gotovos et al.; Bect et al.) do.

---

## 16. Park (2022) — "Jump Gaussian Process Model for Estimating Piecewise Continuous Regression Functions"

1. **Citation**: Park, C. (2022). Jump Gaussian Process Model for Estimating Piecewise Continuous Regression Functions. *Journal of Machine Learning Research*, 23(278), 1–37. https://www.jmlr.org/papers/v23/21-1472.html ; PDF: https://www.jmlr.org/papers/volume23/21-1472/21-1472.pdf
2. **Model/latent object**: For each test location, a **local GP fit on a locally-adaptive neighborhood** determined by a **local data-partitioning function** (e.g. locally linear/polynomial), which decides which nearby training points belong to the "same regime" as the test point — the discontinuity/regime structure is thus implicit in a per-point partition-membership function rather than a single global latent surface.
3. **Observation model**: Continuous regression y = f_k(x) + noise, where the function switches between regimes k with a hard (or probabilistic, via a partition function) discontinuity — **not** a binary-label classification model per se, though the partition membership indicator is itself binary/probabilistic.
4. **Acquisition function**: **None in the base 2022 paper** — this is a modeling (not active-learning) contribution.
5. **Estimand**: The **piecewise-continuous regression function** f itself, including correctly locating the discontinuity/regime boundary as a byproduct of accurate local partitioning.
6. **Finite pool vs continuous**: N/A (static regression paper).
7. **Theory**: Not confirmed beyond model construction and likelihood-based joint optimization of the partition function and local GP hyperparameters.
8. **Relation to probability margin/straddle/SUR**: Not related (no acquisition function in this paper).
9. **Differentiator**: Jump GP models the **regime membership as a latent partitioning variable driving separate local GPs on a continuous response**, which is conceptually close to "one-sided censored continuous-output regression to locate a regime boundary" if the continuous response were, e.g., a physically meaningful depth/energy quantity whose regime (conduction vs keyhole) determines which local trend applies — but Park (2022) itself has no active-learning or censoring component.

---

## 17. Park, Gramacy, Waelder, Maruyama, Kang, Hong (2025) — "Active Learning of Piecewise Gaussian Process Surrogates" (Technometrics, forthcoming/2025)

1. **Citation**: Park, C., Gramacy, R. B., Waelder, M., Maruyama, N., Kang, S., & Hong, J. Active Learning of Piecewise Gaussian Process Surrogates. *Technometrics* (2025), DOI 10.1080/00401706.2025.2561746. https://www.tandfonline.com/doi/full/10.1080/00401706.2025.2561746 ; arXiv:2301.08789 (https://arxiv.org/abs/2301.08789, full text: https://arxiv.org/html/2301.08789v4).
2. **Model/latent object**: The **Jump GP (JGP)** model above, formalized as f(x) = Σ_k f_k(x)·**1**_{X_k}(x), with regime membership driven by a **latent binary indicator Z_i** through a sigmoid link: P(Z_i=1 | x_i, ω) = π(g(x_i,ω)) — i.e., there is an explicit latent classification-style sigmoid governing which regime a point belongs to, fit jointly with the per-regime GPs via a Classification-EM (CEM) algorithm.
3. **Observation model**: Continuous regression y_i ~ N(f(x_i), σ²) (the *response* is continuous), while regime membership Z_i is a latent Bernoulli variable inferred (not directly observed) via CEM.
4. **Acquisition function**: Three criteria — (a) **Maximum MSPE**: x_{N+1}=argmax [Bias² + Variance]; (b) **Minimum IMSPE**: integrate the same bias+variance MSPE reduction over the domain via Monte Carlo quadrature; (c) **Maximum Variance** (a pure-exploration baseline, ignoring bias). The **bias term is explicitly what concentrates sampling near the regime boundary** (bias is largest where a test point sits near a boundary but is fit using neighbor data from the "wrong" side).
5. **Estimand**: **Regression accuracy (MSPE)** with the boundary-location accuracy emerging as a side-effect of bias-aware sampling — a hybrid regression/boundary target, not a direct P(f>0)-type estimand.
6. **Finite pool vs continuous**: **Hybrid**: theory developed for continuous domain, but the actual algorithm and all examples (including a real 500-point candidate-pool carbon-nanotube-yield application) use a **finite candidate pool X_C**.
7. **Theory**: An explicit **upper bound on the bias** at a candidate point in terms of the between-regime mean gap δ = max|μ_j − μ_k| and neighbor regime-membership probabilities p̂_j, p̂_i:
   Bias ≤ δ·Σ_j α_j{(1−p̂_j)p̂_* + p̂_j(1−p̂_*)} + δ·Σ_{i,j} α_j β_i{(1−p̂_j)p̂_i + p̂_j(1−p̂_i)};
   **no convergence-rate or minimax-optimality guarantee** is provided (explicitly noted as absent).
8. **Relation to probability margin/straddle/SUR**: Not framed via straddle/SUR/MI; instead a **bias-variance MSPE decomposition** specific to piecewise/discontinuous GPs — a genuinely different acquisition philosophy from the Bernoulli-classification SUR/MI literature (Letham et al., Bect et al., Menz et al.) even though the underlying goal (sample near a hidden boundary) is the same.
9. **Differentiator**: This is the closest existing analogue in the search set to **"one-sided censored continuous-output regression to locate a regime boundary"** *if* the continuous response is reinterpreted as a censored depth/energy signal, but as published it is an **uncensored, fully-observed piecewise-regression** setting with latent (not censored) regime membership inferred via CEM — the censoring mechanism itself (bounding rather than fully observing the continuous quantity on one side of the boundary) is not present here and would be a genuine addition.

---

## 18. Booth, Cooper, et al. (2025) — "Contour Location for Reliability in Airfoil Simulation Experiments using Deep Gaussian Processes"

1. **Citation**: Booth, A. S., Cooper, A. (& coauthors). Contour Location for Reliability in Airfoil Simulation Experiments using Deep Gaussian Processes. *Annals of Applied Statistics* (AOAS), DOI 10.1214/24-AOAS1951. https://projecteuclid.org/journals/annals-of-applied-statistics/volume-19/issue-1/Contour-location-for-reliability-in-airfoil-simulation-experiments-using-deep/10.1214/24-AOAS1951.short (full text blocked by bot-protection/Incapsula on fetch); arXiv preprint: Booth & Cooper, "Contour Location for Reliability in Airfoil Simulation Experiments using Deep Gaussian Processes," arXiv:2308.04420 (https://arxiv.org/abs/2308.04420, https://arxiv.org/pdf/2308.04420, https://arxiv.org/html/2308.04420).
2. **Model/latent object**: A **Bayesian deep Gaussian process (DGP)** (a composition of GP layers) used as the surrogate for a **nonstationary** aerospace-simulation response, replacing the stationary single-layer GP of the classical contour/excursion-set literature.
3. **Observation model**: Continuous regression response (simulation output), with contour(s) defined as level sets separating "efficient" from "inefficient"/failing flight conditions.
4. **Acquisition function**: A **hybrid criterion exploring the Pareto front of (predictive) entropy and (predictive) uncertainty**, evaluated at candidate points from a triangulation of the input space (rather than continuous derivative-based optimization, since DGP posteriors are not smoothly differentiable end-to-end in the same way).
5. **Estimand**: The **contour/boundary location** separating reliable vs. unreliable operating regimes — a direct boundary-location target, analogous in spirit to π-based level-set estimation but built on a DGP rather than a shallow GP or GPC.
6. **Finite pool vs continuous**: Effectively continuous domain, discretized for acquisition-function evaluation via a triangulation-based candidate scheme (not a literal finite fixed pool, but not a smooth continuous optimizer either).
7. **Theory**: No formal convergence/sample-complexity theory found (deep GPs generally lack such guarantees); contribution is empirical, targeting nonstationary response surfaces where single-layer GP contour methods (Bect et al.-style) are known to struggle.
8. **Relation to probability margin/straddle/SUR**: Not a SUR/straddle criterion; entropy+uncertainty Pareto-front selection is a distinct (multi-objective, non-lookahead) acquisition philosophy, explicitly motivated as an alternative to expensive derivative-based / nested-Monte-Carlo lookahead criteria that don't scale well to DGPs.
9. **Differentiator**: Booth et al. address **nonstationarity in the response surface itself** (e.g., abrupt change in variance or smoothness across the domain) via a deep/compositional GP; if the conduction/keyhole boundary in (P,VX,LS,ST)-space (or along h) has strongly nonstationary behavior (e.g., much sharper transition at high P than low P), a DGP-based classifier layer could be substituted for the single-layer probit-GPC assumed by Letham et al./Gotovos et al., at the cost of losing their closed-form look-ahead machinery.

---

## 19. Gotovos, Casati, Hitz, Krause (2013) — "Active Learning for Level Set Estimation"

1. **Citation**: Gotovos, A., Casati, N., Hitz, G., & Krause, A. (2013). Active Learning for Level Set Estimation. *IJCAI 2013*, 1344–1350. https://www.ijcai.org/Proceedings/13/Papers/202.pdf ; long version: https://las.inf.ethz.ch/files/gotovos13active-long.pdf
2. **Model/latent object**: f ~ GP(μ,k), standard zero-mean GP with a smoothness-encoding kernel.
3. **Observation model**: Noisy regression: y_t = f(x_t) + n_t, n_t ~ N(0,σ²) i.i.d. — **not** Bernoulli.
4. **Acquisition function**: The canonical **straddle** rule (generalized with a confidence multiplier β_t):
   a'_t(x) = β_t^{1/2}·σ_{t−1}(x) − |μ_{t−1}(x) − h|,
   which reduces to the classic straddle heuristic when β_t^{1/2}=1.96 — the point with the largest "confidence interval straddling the threshold h, weighted by proximity" is queried next.
5. **Estimand**: **Level-set classification of every point in a finite domain**: H = {x∈D : f(x)>h} vs. L = {x∈D : f(x)≤h} — an explicit finite-pool, per-point classification accuracy target with an (ε,δ) guarantee, closest in spirit to a finite-pool "0/1-loss reduction" objective, though the acquisition itself is a heuristic (not a direct 0-1-error-reduction computation).
6. **Finite pool vs continuous**: **Explicitly finite pool**: "D is a finite subset of ℝ^d."
7. **Theory**: **Theorem 1**: the algorithm halts after T rounds with T/√(β_T γ_T) ≥ C₁/ε² (roughly), returning an ε-accurate classification with probability ≥1−δ, where γ_T is the maximum-information-gain quantity from the GP-UCB/bandit literature — **no distributional assumption beyond the GP prior and standard information-gain bounds** (e.g., bounded γ_T growth for common kernels).
8. **Relation to probability margin/straddle/SUR**: **This is the origin of the modern "straddle" formalization for level-set estimation** (generalizing Bryan et al. 2005's original straddle heuristic with formal β_t-scheduled confidence and an information-gain-based stopping guarantee); it is the noisy-regression, finite-pool sibling of Bect et al. (2012)'s SUR-based, continuous-domain, noiseless-simulator approach, and a direct ancestor of Letham et al. (2022)'s Bernoulli-adapted LocalSUR/GlobalSUR criteria.
9. **Differentiator**: Straddle uses **regression noise and a fixed threshold h on the mean function**, not a Bernoulli/probit-labeled classifier; adapting it to this project's binary-label setting is exactly what Letham et al. (2022) and Menz et al. do — so a new method should be explicit about whether it is "straddle for Bernoulli-GPC" (already covered by Letham et al.) or something structurally new (e.g., straddle directly on the physics coordinate h with a boundary-GP rather than a value-GP).

---

## 20. Bryan, Nichol, Genovese, Schneider, Freeman, Frieman (2005) — "Active Learning For Identifying Function Threshold Boundaries"

1. **Citation**: Bryan, B., Nichol, R. C., Genovese, C. R., Schneider, J., Freeman, W. J., & Frieman, J. A. (2005). Active Learning For Identifying Function Threshold Boundaries. *NeurIPS 2005 (NIPS 18)*. https://papers.nips.cc/paper/2940-active-learning-for-identifying-function-threshold-boundaries ; https://proceedings.neurips.cc/paper/2005/hash/8e930496927757aac0dbd2438cb3f4f6-Abstract.html ; PDF: https://proceedings.neurips.cc/paper_files/paper/2005/file/8e930496927757aac0dbd2438cb3f4f6-Paper.pdf
2. **Model/latent object**: **Ordinary kriging** (Gaussian-process-equivalent) with a linear semivariogram: E[K(s_i,s_j)] = k²[Σ_ℓ α_ℓ(s_iℓ−s_jℓ)²]^{1/2} + c.
3. **Observation model**: Noisy regression — samples assumed Normal with mean the true function value and variance the sampling noise.
4. **Acquisition function**: The **original "straddle" heuristic**:
   straddle(s_q) = 1.96·σ̂_q − |f̂(s_q) − t|,
   selecting points that are both near the threshold t and highly uncertain, from candidate points chosen uniformly at random over the continuous input space.
5. **Estimand**: The **threshold boundary set** S' = {s∈S : f(s)≥t} — a direct boundary/level-set target.
6. **Finite pool vs continuous**: **Continuous domain**, no fixed grid — candidates drawn uniformly at random from the input space at each step.
7. **Theory**: **No formal guarantees**; purely empirical, showing straddle needs roughly **50% fewer experiments than variance-minimization (pure exploration)** to reach 99% classification accuracy on their test functions.
8. **Relation to probability margin/straddle/SUR**: **This is the original straddle paper**, predating and directly motivating Gotovos et al. (2013)'s formalized/theoretically-grounded version and, more distally, the entire Bernoulli-adapted SUR/straddle lineage (Letham et al. 2022; Fan et al. 2026's "e-straddle").
9. **Differentiator**: The 2005 straddle is the simplest, non-Bayesian-decision-theoretic ancestor of everything else in this list; a new method's contribution should be stated relative to the *modern, Bernoulli-adapted* descendants (Letham et al.; Fan et al.), not this original regression-noise version, since the manual-binary-label setting here structurally differs from Bryan et al.'s continuous noisy-regression setting.

---

## 21. Chevalier, Bect, Ginsbourger, Vazquez, Picheny, Richet (2014) — "Fast Parallel Kriging-Based Stepwise Uncertainty Reduction With Application to the Identification of an Excursion Set"

1. **Citation**: Chevalier, C., Bect, J., Ginsbourger, D., Vazquez, E., Picheny, V., & Richet, Y. (2014). Fast Parallel Kriging-Based Stepwise Uncertainty Reduction With Application to the Identification of an Excursion Set. *Technometrics*, 56(4), 455–465. https://www.tandfonline.com/doi/abs/10.1080/00401706.2013.860918 ; HAL: https://hal.science/hal-00641108 (blocked by bot-protection on fetch — details below from search-result abstract snippets only).
2. **Model/latent object**: GP/kriging model of a deterministic (or noisy/batch) simulator, as in Bect et al. (2012); this paper's contribution is **parallelizing (batch) SUR** — selecting q>1 points simultaneously.
3. **Observation model**: Deterministic or noisy simulator evaluations, extended explicitly to **batch (parallel) evaluation** scenarios.
4. **Acquisition function**: **Batch SUR criteria** with fast, closed-form (non-nested-Monte-Carlo) update formulas for the multi-point look-ahead uncertainty functional (variance of excursion volume / misclassification-probability integral, as in Bect et al. 2012), making q-point batch selection computationally tractable.
5. **Estimand**: The **excursion set** {x : f(x)>u} (same as Bect et al. 2012), now estimated with parallel/batch sampling.
6. **Finite pool vs continuous**: Continuous domain (kriging-based), as in the rest of the SUR-for-excursion-sets lineage.
7. **Theory**: Not confirmed beyond computational-tractability claims (fast closed-form batch updates); no sample-complexity bound found.
8. **Relation to probability margin/straddle/SUR**: Direct sequel to Bect et al. (2012), extending single-point SUR to **batch/parallel SUR** — relevant if a melt-pool method needs to propose multiple simulation queries per iteration (e.g., to batch manual-labeling effort).
9. **Differentiator**: Adds **batch parallelism** to SUR, a practical concern (labeling several simulator points per "batch" of manual review) not addressed by Letham et al. (2022) or Menz et al., who are single-point; combining Letham et al.'s Bernoulli-π SUR criteria with Chevalier et al.'s batch/parallel fast-update machinery is a plausible, currently-absent combination.

---

## 22. Azzimonti, Ginsbourger, Chevalier, Bect, Richet (2021) — "Adaptive Design of Experiments for Conservative Estimation of Excursion Sets"

1. **Citation**: Azzimonti, D., Ginsbourger, D., Chevalier, C., Bect, J., & Richet, Y. (2021). Adaptive Design of Experiments for Conservative Estimation of Excursion Sets. *Technometrics*, 63(1), 13–26. https://www.tandfonline.com/doi/full/10.1080/00401706.2019.1693427 ; arXiv:1611.07256 (https://arxiv.org/abs/1611.07256).
2. **Model/latent object**: GP model of f, with the excursion set estimated via a **Vorob'ev-expectation-based** conservative estimator (biased toward controlling false negatives or false positives asymmetrically, rather than a symmetric 50/50 threshold).
3. **Observation model**: Not fully detailed in accessible excerpt; consistent with the Bect et al./Chevalier et al. lineage (GP surrogate of an expensive deterministic or noisy function).
4. **Acquisition function**: A **SUR-family criterion adapted for conservative estimation** — sequentially selecting evaluations to reduce uncertainty specifically on the **conservative estimate** of the excursion set (i.e., minimizing false negatives at the cost of accepting more false positives, or vice versa, depending on the application's risk asymmetry), rather than symmetric misclassification-probability minimization.
5. **Estimand**: A **risk-asymmetric (conservative) version of the excursion set**, not a symmetric decision boundary — directly relevant if, in the melt-pool application, false "Conduction" labels (missing a Keyhole defect) are more costly than false "Keyhole" labels, or vice versa.
6. **Finite pool vs continuous**: Continuous domain, consistent with the rest of this lineage.
7. **Theory**: Not confirmed in detail from accessible excerpt; the paper's focus is the conservative-estimator construction and its associated adapted SUR criterion, not sample-complexity bounds.
8. **Relation to probability margin/straddle/SUR**: Direct SUR-family member, generalizing the Bect et al./Chevalier et al. symmetric misclassification-probability SUR criterion to an **asymmetric-risk** setting.
9. **Differentiator**: If the manual labeling process for this project has an inherent asymmetry (e.g., a "Keyhole" label carries downstream cost implications different from a "Conduction" label, or the manual labeler is more conservative near ambiguous cases), Azzimonti et al.'s risk-asymmetric SUR framework is directly relevant and not addressed by the symmetric-loss Letham et al. or Menz et al. criteria.

---

## 23. Ranjan, Bingham, Michailidis (2008) — "Sequential Experiment Design for Contour Estimation From Complex Computer Codes"

1. **Citation**: Ranjan, P., Bingham, D., & Michailidis, G. (2008). Sequential Experiment Design for Contour Estimation From Complex Computer Codes. *Technometrics*, 50(4), 527–541. https://www.tandfonline.com/doi/abs/10.1198/004017008000000541 ; errata: http://www.acadiau.ca/~pranjan/research/Errata_RBM_contour_paper.pdf
2. **Model/latent object**: Ordinary/universal **kriging** surrogate of a deterministic computer-code output ŷ(x), with kriging (predictive) variance s²(x).
3. **Observation model**: Deterministic computer-code evaluations (no observation noise), consistent with the broader computer-experiments/kriging contour literature.
4. **Acquisition function**: A **weighted expected-improvement-style criterion** targeting proximity to a target contour level a, with corrected closed form (per the errata):
   E[I(x)] = [ε² − (ŷ(x)−a)² − s²(x)]·(Φ(u₂)−Φ(u₁)) + s²(x)·(u₂φ(u₂)−u₁φ(u₁)) + 2(ŷ(x)−a)·s(x)·(φ(u₂)−φ(u₁)),
   with ε=α·s(x) a tolerance band and u₁,u₂ standardized integration bounds — this **balances local refinement near the current estimated contour against global exploration** of high-variance regions.
5. **Estimand**: The **contour {x : f(x)=a}** directly — a boundary-location target, in the classic kriging/computer-experiments tradition (predecessor to Bect et al. 2012's probabilistic/SUR reframing of the same problem).
6. **Finite pool vs continuous**: Continuous domain, deterministic-simulator setting — methodologically the closest classical precedent to this project's own deterministic-simulator setup, though using a continuous kriging surrogate rather than a Bernoulli/probit GPC (i.e., it implicitly assumes the *continuous* function value f(x) is directly observable, not just a binary label).
7. **Theory**: No formal convergence-rate theorem found; the criterion is an EI-style heuristic, validated empirically.
8. **Relation to probability margin/straddle/SUR**: A **precursor** to the "probability margin" framing — the weighted-EI criterion is conceptually the *contour-estimation* analogue of expected improvement in optimization, playing a similar historical role to what SUR/straddle later formalized probabilistically for binary/level-set settings.
9. **Differentiator**: Ranjan et al. assume **direct, continuous, noiseless access to f(x)** (the classic deterministic-computer-experiment assumption) — exactly this project's simulator characteristic — but do **not** address the case where only a **binary, possibly effortful/manual** label of f(x)'s regime is available rather than f(x) itself; bridging this EI-style contour criterion to a Bernoulli-labeled setting is effectively what Bect et al. (2012) and then Letham et al. (2022) do next in the lineage.

---

## 24. Picheny, Ginsbourger, Roustant, Haftka, Kim (2010) — targeted-IMSE ("tIMSE") for target-region approximation

1. **Citation**: Picheny, V., Ginsbourger, D., Roustant, O., Haftka, R. T., & Kim, N.-H. (2010). Adaptive Designs of Experiments for Accurate Approximation of a Target Region. *Journal of Mechanical Design* (ASME), 132(7). (ResearchGate record: https://www.researchgate.net/publication/29623261 — full text repeatedly returned HTTP 429 on fetch; details below drawn from secondary references, e.g. its citation within the `KrigInv` R-package documentation, https://www.rdocumentation.org/packages/KrigInv/versions/1.4.1/topics/EGI, and its comparison context in Bect et al. 2012.)
2. **Model/latent object**: Kriging/GP surrogate of the simulator output; the **targeted Integrated Mean Squared Error (tIMSE)** criterion reweights the standard IMSE-reduction integrand by a **weight function concentrated near the threshold/target region** (e.g., a Gaussian-shaped weight peaked at the level of interest), rather than integrating uniformly over the whole domain.
3. **Observation model**: Deterministic (or possibly noisy) computer-experiment output, consistent with the kriging/computer-experiments tradition.
4. **Acquisition function**: **tIMSE**: minimize (over candidate x) the integral of the *posterior-updated* predictive variance weighted by a target-proximity weight function W(x) (peaked near the threshold), i.e. a "targeted" version of classical (I)MSE-reduction design criteria — exact formula not independently re-derived here due to fetch failures, but its defining idea (weighting IMSE reduction toward the region of interest) is corroborated across all secondary sources found.
5. **Estimand**: Accurate approximation of the **contour/target region** (analogous to Ranjan et al. 2008 and Bect et al. 2012), via a variance-reduction (frequentist-flavored, not probability-of-misclassification) objective.
6. **Finite pool vs continuous**: Continuous domain, kriging-based, consistent with this literature family.
7. **Theory**: Not confirmed (fetch blocked); presented in the literature primarily as an empirically-validated design criterion.
8. **Relation to probability margin/straddle/SUR**: A **variance-weighted alternative to SUR/straddle** — instead of directly targeting the misclassification-probability margin, tIMSE targets *predictive variance* weighted toward the threshold, making it conceptually intermediate between plain IMSE space-filling designs and full misclassification-probability SUR criteria (Bect et al. 2012 explicitly compares against it).
9. **Differentiator**: tIMSE requires **direct continuous f(x) access** like Ranjan et al. (2008); for the manual-binary-label setting here it would need the same Bernoulli-adaptation step as Bect et al./Letham et al., and in practice the field has favored probability-margin-based SUR/straddle criteria over variance-weighted tIMSE-style criteria once binary/Bernoulli observations are involved (since predictive variance of a probit-GP latent surface does not translate as directly into decision-relevant uncertainty as a probability margin does).

---

## 25. Additional / adjacent works found during search

- **Roy & McCallum (2001)**, "Toward Optimal Active Learning through Sampling Estimation of Error Reduction," *ICML 2001*. https://www.lri.fr/~sebag/Examens/Active/roy01toward.pdf ; https://dl.acm.org/doi/10.5555/645530.655646. **Model**: model-agnostic (demonstrated on naive Bayes, but stated to generalize to "any learning method in which incremental training is efficient," e.g. SVMs). **Acquisition**: pool-based **expected future error** minimization, Error = Σ_{x∈pool} P(label|x)·Loss(true dist., predicted dist.), with **log-loss** and **0-1-loss** variants — this is the canonical origin of "finite-pool expected 0-1 error reduction," directly relevant to point (iii) of the summary below, though it predates and is independent of the GP-classification literature (no GP/kernel machinery, no probit link).
- **Cutforth, Yang, Fan, Guillas, Darve (2025)**, "Multi-fidelity Batch Active Learning for Gaussian Process Classifiers." https://arxiv.org/html/2510.08865v1. Introduces **BPMI (Bernoulli Parameter Mutual Information)**, a batch acquisition function using a first-order (Taylor/linearized) approximation of mutual information **directly in predictive-probability space** p=Φ(f) (multi-fidelity GPC with f_H=ρf_L+δ), explicitly contrasted with information/entropy criteria computed in **latent space**; uses submodularity of MI for a (1−1/e)-approximate greedy batch-selection guarantee. This is the clearest example found of a method that explicitly and self-consciously targets **p (predictive label probability) rather than π (latent-set membership)**, directly relevant to distinguishing estimands in this project.
- **Akbari et al., "SL-RF+"** (sequential learning framework for melt-pool defect classification in LPBF, incl. keyhole/balling/lack-of-fusion classes), arXiv:2411.10822 (https://arxiv.org/abs/2411.10822). Uses a **Random Forest classifier** (not GP) with **Least-Confidence Sampling** (1 − max_y P(y|x)) over a **finite pool** (460 candidate points) combined with Sobol-sequence synthetic sampling — a directly comparable applied LPBF process-map active-learning pipeline, but non-Bayesian/non-GP, useful as a finite-pool baseline reference for this project even though it is not GP-based.
- **Groot & Lucas (2012)**, "Gaussian process regression with censored data using expectation propagation." Confirmed to exist (ResearchGate/Academia.edu records: https://www.researchgate.net/publication/236176050 ; https://www.academia.edu/14536076) but **exact venue/full text not retrieved** (fetch of ResearchGate/Academia pages did not yield full citation metadata in this session — flagged as needing direct verification). Establishes GP regression with a **Tobit-type censored-Gaussian likelihood**, solved via EP — directly the classical reference for "one-sided censored continuous-output regression" with a GP, though **not** framed around active learning or level-set/boundary estimation.
- **Gammelli, Rodrigues et al. (2022)**, "Generalized Multi-Output Gaussian Process Censored Regression," *Pattern Recognition*, DOI 10.1016/j.patcog.2022.108751; arXiv:2009.04822 (https://arxiv.org/abs/2009.04822). A **heteroscedastic, multi-output GP** with a variational (SVI-style) treatment of an "arbitrary" censoring likelihood, using correlation across outputs to de-bias censored estimates. No active learning or level-set component found in the accessible abstract-level text; relevant purely as the modern (variational, scalable) alternative to Groot & Lucas's EP-based censored GP regression, for point (ii) of the summary below.

---

# Summary: Closest Prior Art to Three Target Concepts (10 lines)

1. **(i) "GP over the boundary location τ(z) in a physics coordinate z=h, with probit observations."** No paper found puts a GP *directly and only* on a scalar boundary-location function indexed by a designed physics coordinate with a probit-Bernoulli likelihood on binary labels straddling it.
2. The two closest pieces jointly cover the idea but not combined: **Li & Ghosal (2017)** puts a GP prior *directly on the boundary function* τ(angle) (nonparametric-Bayesian, with minimax contraction-rate theory) but has no active-learning/acquisition step and no physics-coordinate reduction; **Keeley et al. (2023)** derives a boundary/threshold x_r(x_context) = σ⁻¹(r)/k(x_context) − c(x_context) as a *nonlinear function of two GPs* (slope+offset) with binary/probit observations and active-learning acquisition (ThresholdBALV, GlobalMI), but the boundary is not itself the GP.
3. **Letham et al. (2022)** and **Menz et al. (2025)** give the probit-Bernoulli-GPC + SUR/MI machinery needed for the acquisition side, but their latent object is a value-surface f(x) whose zero-crossing implies the boundary, not a boundary-indexed GP.
4. **A genuinely new method would be the first found here to collapse the 4-D input to a 1-D physics coordinate h and place the GP directly on τ(h)**, using Letham-et-al.-style closed-form probit look-ahead machinery for the acquisition function.

5. **(ii) "One-sided censored continuous-output (depth) regression to locate a regime boundary."** No paper in this search combines censored-GP regression with active learning for boundary/level-set location.
6. **Groot & Lucas (2012)** and **Gammelli et al. (2022)** give Tobit-type censored-GP-regression likelihoods (EP-based and variational/multi-output respectively) but neither has an active-learning or level-set/boundary target.
7. **Park (2022)/Park et al. (2025 Technometrics)** Jump-GP models a *fully-observed* (uncensored) piecewise-continuous response with a latent regime indicator and (in the 2025 paper) a bias-aware active-learning criterion that naturally concentrates near regime boundaries — structurally the closest analogue, but with no censoring mechanism.
8. **A new method combining a Tobit/censored likelihood (Groot & Lucas / Gammelli) with the Jump-GP active-learning bias-variance acquisition (Park et al. 2025), or with SUR/straddle, for boundary location, was not found and appears open.**

9. **(iii) "Finite-pool expected 0-1 error reduction for GPC."** **Roy & McCallum (2001)** is the canonical origin (pool-based, 0-1-loss and log-loss expected-error-reduction, but model-agnostic/non-GP); **Mason et al. (2022)** gives the strongest finite-pool theory (PAC sample-complexity bounds matching information-theoretic lower bounds) but for linear/RKHS-regression, not Bernoulli-GPC; **Zhao et al. (2021)** (SMOCU/MOCU) and **Gotovos et al. (2013)** (straddle with an (ε,δ) finite-pool guarantee) are the closest GP-flavored analogues, targeting a Bayes-decision-cost or level-set-classification error respectively, in a pool (Gotovos) or pool-and-continuous (Zhao) setting, but neither directly instantiates Roy & McCallum's *literal* 0-1-loss expected-error-reduction functional inside a Bernoulli-GPC/EP framework with a formal finite-pool sample-complexity bound.
10. **A method giving Mason-et-al.-style finite-pool sample-complexity guarantees for literal 0-1-loss expected-error reduction under a probit-linked GPC observation model (rather than linear-RKHS regression or the MOCU/straddle surrogates) was not found and appears to be a genuine gap.**
