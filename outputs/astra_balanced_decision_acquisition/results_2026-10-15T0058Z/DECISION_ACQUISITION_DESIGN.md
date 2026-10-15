**A joint-posterior decision and acquisition rule for finite-batch balanced accuracy**

14 October 2026 · independent development · repository anchor `2b22c13df41ee0179d5999ff07a98c0aa36814ca`, branch `joint-depth-label-dev`.

**Execution status: COMPUTATION FINISHED; scientific review is still required.** The design and code are frozen; syntax/provenance checks have passed. A single local pipeline waits for the shared host allocation. No fit or numerical reference had executed at the 14 October, 13:48 UTC implementation freeze. This is not yet a completed empirical study. Live scheduling and attempt records are in `PIPELINE_STATE.json`, `HOST_QUEUE.json` and `ledger.jsonl`.

**Later context, not method selection:** commit `9d6f2110` appeared during preparation. Its report errata retract the paid-prevalence optimality claim and narrow identifiability/impossibility language. This review's criticism below concerns the specified anchor; the corrections are welcome and do not alter its numerical evidence. The later commit describes V2 preparation without benchmark execution. No new real-data V2 benchmark outcomes were read or used to choose this method. The shared temporal worker queue remains active.

**Purpose and claim boundary.** Use the unchanged V2 mixture to make decisions and choose simulations under the same specified loss. The selected method integrates uncertain class prevalence with the predicted probabilities; its paired-output selector minimizes expected future balanced error. It is an implementable application of established Bayes decision theory and expected-error reduction. It cannot guarantee recovery of transient Keyhole events when the loss rewards sacrificing them. It does not identify a physical regime boundary.

The practical target is a *prospective IID evaluation batch*, with its size fixed before results. The feature distribution is approximated by a fixed training-candidate reference measure. This is a stated approximation to the thesis's pooled held-out BA, **not exact optimization of the already recorded, fixed test panel**. The distinction matters with rare classes, selective acquisition and repeated cross-validation. Exact fixed-panel decisions are derived and independently checked below; they are not silently substituted for the selected inductive rule.

**What the anchor establishes.** The frozen V1 Stage M screen failed: NEW B40 J−Binary-matched BA is +0.006048, with conditional bootstrap interval [−0.052419,+0.064516], below the +0.01 practical bar. Both have specificity 0.125; J improves log loss by about 0.172 and AUC by 0.074. This establishes useful probability/ranking changes under the tested model, not a resolved negative boundary or improved acquisition. All paths were feature-only maximin. [Stage M report](evidence/STAGE_M_REPORT.md), [decision](evidence/stage_m__STAGE_M_DECISION.json), [paired tables](evidence/stage_m__paired_contrasts.csv)

EX1/EX2 then separated two changes on DEV 5–8. J_trained at 0.5 reaches BA 0.7517 and short-K sensitivity 0.675; its paid-fraction rule reaches BA 0.9059 while short-K sensitivity falls to 0.05. ACTIVE E1 and G3 at their frozen rules have BA 0.6818/0.6435 and short-K sensitivity 0.70/0.55. The gain from raising the cutoff is real on these stored predictions. It rejects the fast corner almost wholesale. The descriptive table records 9.5 of the 10 short-K positives missed per repeat by J_trained at the paid cutoff, versus 3.25 at 0.5. This is not resolution of that corner. [Exploratory report](evidence/exploratory__EXPLORATORY_REPORT.md), [EX2 table](evidence/exploratory__EX2_trained_response_prior__metrics_per_repeat.csv), [miss counts](evidence/exploratory__POSTHOC_descriptive__NEW_positive_misses_by_rule.csv)

I disagree with several stronger explanations in those reports:

- A proper prior does not make a fitted model calibrated to either the paid mix or the target population. Reliability bins indicate probability error where negatives occur. Calibration of a score alone also does not imply that it uses every informative input.
- The trained response prior reduces held-out depth error, including in fast scans, and improves BA at the unchanged 0.5 cutoff. A decision-loss explanation is therefore incomplete; response-model restriction is supported separately.
- Similar-depth examples, small ablation changes and near-chance performance of these models do not establish that all four-input predictors fail or that 11/12 is a data-imposed specificity ceiling. An all-negative rule trivially has specificity one; what matters is its sensitivity cost. No impossibility theorem for the SPH channels follows.
- Numerical stationarity is not posterior accuracy. The saved V1 slice reference has a maximum probability discrepancy as large as 0.0918 in one fold, although only two decisions change across the five folds at 0.5. A new loss/decision contour can expose errors that did not cross 0.5. [Mechanisms](evidence/MECHANISM_REPORT.md), [slice comparison](evidence/mechanism__laplace_error_NEW_r1_B40_ess.csv)

The defensible diagnosis is **a demonstrated decision-rule effect plus demonstrated response-model restriction; unknown reference-distribution error; unresolved local probability/model/information limits**. The magnitudes do not identify a unique historical cause. V2 already withdraws harmful global sharing in controlled cases, but did not generalize rare negatives adequately. Its variance selector won BA-AULC in only 2/9 earlier pairs. Nine heterogeneous cases neither support concealment of that failure nor establish a universal ranking.

**Three different targets.** Canonical Y is “at least one observed manually labelled Keyhole frame.” Its probability eta(x) concerns the recorded outcome under the specified observation and annotation process. A loss-optimal decision surface is the set where the expected cost of positive and negative decisions is equal. A latent/physical boundary concerns a separately defined physical quantity or morphology. A change in class weights can move the second without changing either the first probability map or the physics. q20 remains an evaluator-defined subset, not a physical contour oracle. Short-K membership remains evaluator-only; even paid Y and A do not reveal frame counts under the current contract.

**Population BA, and what the cutoff-pi statement actually says.** Let mu be the *target* feature distribution, eta(x)=Pr(Y=1|X=x) its true conditional probability, and pi=integral eta dmu with 0<pi<1. For a deterministic action d,

$$
\mathrm{BA}_\mu(d;\eta)=\frac12\left[
\frac{\int\eta(x)d(x)\,d\mu(x)}{\pi}
+\frac{\int(1-\eta(x))(1-d(x))\,d\mu(x)}{1-\pi}\right].
$$

Pointwise comparison gives d=1 iff eta(x)>=pi, up to ties of zero loss difference. This is a population Bayes statement for true probabilities and the correct target distribution, unrestricted pointwise binary actions and equal weights on the two class recalls. It is not a license to substitute any training fraction for pi. A score calibrated on mu supports an analogous optimum among actions measurable with respect to that score; it need not be the Bayes rule using all X. The consistency result of [Menon et al. (2013)](https://proceedings.mlr.press/v28/menon13a.html) requires a consistent prevalence estimator; its empirical-threshold argument does not establish that maximin/adaptively selected labels provide one.

Under posterior uncertainty, the population action compares

$$A_\infty(x)=E[\eta(x)/\pi\mid D],\qquad
B_\infty(x)=E[(1-\eta(x))/(1-\pi)\mid D].$$

Generally E[eta/pi] is not E[eta]/E[pi]. A local expansion includes −Cov(eta,pi)/E[pi]^2 and E[eta]Var(pi)/E[pi]^3; the remainder and the analogous negative-class terms matter near extreme prevalence. This expansion is explanatory, not used in the implementation. Exact two-state calculations quantify the plug-in error in the numerical results.

Feature-only maximin deliberately changes sampling density. Adaptive queries can depend on previous outcomes as well. “Train-only” defines information access, not unbiasedness. Known random inclusion probabilities can sometimes support design-based correction, but deterministic maximin/adaptive selection need not provide positive, known inclusion probabilities for every target case. This package instead makes a model-based assumption: conditional predictions extrapolate from paid observations to a **fixed feature-only reference**, whose weights are independent of the paid composition. That removes the direct substitution error; it cannot remove model misspecification or an inappropriate target reference.

**Selected construction: a finite prospective evaluation batch.** The initial population-only proposal was corrected for a mathematical reason *before any numerical result*: inverse prevalence can make extrapolated action coefficients unstable away from the reference atoms. [The prospective amendment](AMENDMENT_00_BEFORE_RESULTS.md) preserves the original freeze and code. No prior, world, seed or tolerance was chosen from outcomes.

Define a future batch of m independent identities, X_l drawn from mu and Y_l conditionally Bernoulli with probability eta(X_l). Conditional on a latent eta function, examples are IID; integrating eta induces dependence. Set loss to 1−BA when both classes occur, and to the **action-independent constant 1/2** when one class is absent. Missing-class BA itself is reported undefined. Fix m=96 for all controlled worlds, including worlds whose realized evaluator batch happens to be one-class.

The admissible policy is an inductive pointwise rule d_D(x). It cannot condition a decision on the other realized features in the future batch. A transductive action using the complete batch's inputs solves a different conditional problem. This restriction and the fixed empirical reference are deliberate because the future handoff must operate from training information; they limit the claim of exact optimality.

For one specified example with X_i=x, the other m−1 positive labels have S~Binomial(m−1,pi). Its positive correct-call coefficient, restricted to both-class events, is

$$
\eta(x)\left[E\frac1{1+S}-\frac{\pi^{m-1}}m\right]
=\frac{\eta(x)}{m\pi}\{1-(1-\pi)^m-\pi^m\}.
$$

The negative coefficient follows by interchanging classes. Thus, with
$$w_m(\pi)=1-\pi^m-(1-\pi)^m,$$
select
$$
A_m(x)=E\!\left[\frac{w_m(\pi)\eta(x)}{\pi}\mid D\right],\quad
B_m(x)=E\!\left[\frac{w_m(\pi)(1-\eta(x))}{1-\pi}\mid D\right],\qquad
d_m(x)=\mathbf1\{A_m(x)\ge B_m(x)\}.
$$

The optimized risk is
$$R_m(D)=\tfrac12 E[1-w_m(\pi)\mid D]
+\tfrac12\int\min\{A_m(x),B_m(x)\}\,d\mu(x).$$

The first term is action-independent. The second is called the *decision-sensitive risk* in code. The factors w_m/pi and w_m/(1−pi) are at most m, so the coefficients are finite even for out-of-reference predictions. Stable log-tail arithmetic evaluates them without a prevalence floor. This is a finite evaluation-loss construction, not arbitrary clipping.

Limiting cases clarify the assumptions. For known eta, w_m is a common positive scalar and the cutoff remains pi. Known pi but uncertain eta likewise gives cutoff E[eta|D]>=pi. For m=2 the factors are 2(1−pi) and 2pi. As m grows, they approach the population factors wherever both classes have positive mass; exchanging this limit with expectations requires integrability. If there is effectively no class contrast, every action can tie; a deterministic positive tie is recorded, not interpreted as evidence of Keyhole.

The implementation uses mu_Q, uniform on all fixed training-candidate inputs Q, as quadrature for the intended target feature distribution. It never replaces mu_Q by the acquired subset. Held-out X enters only prediction, never the reference weights or selector. Paid labels condition the GP and are fixed historical observations; the future-batch model does not overwrite them. This inductive target treats new evaluation identities as exchangeable given eta. That is a working statistical assumption, not evidence of physical randomness. Fixed SPH records and cross-fold pooled predictions do not literally form a fresh IID batch under one posterior. **Reference approximation, finite-record versus prospective-batch interpretation, and cross-fold pooling are explicit limits on “target alignment.”**

**Fixed recorded-label pools are a different decision problem.** If the target instead is a particular finite panel I of n recorded labels, define E={0<N_1<n}, N_1=sum_i Y_i, N_0=n−N_1. For its posterior joint label law,
$$a_i=E[\mathbf1_EY_i/N_1\mid D],\qquad
b_i=E[\mathbf1_E(1-Y_i)/N_0\mid D].$$
With the same constant loss on E-complement, expected loss is
$$\tfrac12P(E^c\mid D)+\tfrac12\sum_i\{a_i(1-d_i)+b_i d_i\}.$$
Therefore d_i=1 iff a_i>=b_i. All observed paid target labels must be fixed in every posterior state; they are not newly sampled Bernoulli outcomes. Full posterior dependence in labels and totals remains relevant. If P(E)=0, conditional BA is undefined and every action has the declared constant loss. If optimizing conditional-on-E risk, divide the decision-sensitive terms by P(E); actions are unchanged, but lookahead must average future observations under P(O|D,E), not P(O|D). Otherwise the usual information-value identity need not hold.

This fixed-panel formula is derived from its actual random denominators. It need not be a scalar threshold on marginal probabilities. [Exact enumeration code](independent_checks.py) checks every action, fixes paid labels, handles zero-class events, and checks a paired discrete observation channel. It is a validation/reference API, not the main sequential target. Deploying it on the actual held-out fixed panel would be an explicitly transductive protocol with a joint label law, including dependence across predictions; it is not obtained by copying the population cutoff.

**Unchanged model, explicit approximate lookahead.** V2 has h=rho f+sqrt(1−rho^2)g−theta+delta, rho in {0,0.5,1} with equal initial masses, unchanged fixed kernels/priors, Gaussian paid log-depth and probit canonical labels. The marginal prior of h is invariant across rho. The current fitted posterior is a mixture of EP Gaussian components, with the preserved whole-mixture Laplace fallback. This package changes neither capacity nor priors. [Preserved model](joint_model_v2.py), [V1 dependency](v1_reference.py)

For candidate j, let its future observation be O_j=(Z_j,Y_j), with missing depth handled by the declared availability model. Within component k, Gaussian conditioning on future z updates all h-reference means and covariances using Cov(h,f_j), and changes component masses to
$$\omega_k(z)\propto\omega_k\,N(z;\mu_{f_j,k},V_{f_j,k}+\sigma_z^2).$$
For each resulting joint h draw, compute eta, pi, w_m, c_i^+=w_m eta_i/pi and c_i^−=w_m(1−eta_i)/(1−pi). With ell_y(h_j)=eta_j^y(1−eta_j)^{1−y}, define **unnormalized** branch coefficients
$$A_i^y(z)=\sum_k\omega_k(z)E_k[c_i^+\ell_y\mid z,D],\qquad
B_i^y(z)=\sum_k\omega_k(z)E_k[c_i^-\ell_y\mid z,D].$$
Normalizing each by Pr(Y_j=y|z,D), taking its Bayes risk, then averaging over y cancels that denominator because min is homogeneous. The selected score is consequently
$$a_m(j)=\frac12\sum_i v_i\min(A_i,B_i)
-\frac12E_{Z_j\mid D}\sum_i v_i\sum_{y=0}^1\min\{A_i^y(Z_j),B_i^y(Z_j)\}.$$
The zero-class term cancels by total expectation. Both future z and y reweight mixture components. Whole-function draws retain within-component correlations, between-component variation and eta–pi dependence. Averaging separate component utilities would be wrong because a single future action must be selected from the updated mixture.

Missing depth is not a free pre-query indicator. The missing-depth world freezes an independent availability probability 0.75, revealed after payment; its score is 0.75 times paired value plus 0.25 times label-only value. Every query costs one. Informative missingness would require a different missingness model; this study does not infer it from held-out monitors.

The lookahead multiplies the **current approximate posterior** by the exact future likelihood; it does not re-project each fantasy into an EP Gaussian or re-optimize priors. After a real paid query, the same unchanged V2 is refitted from its prior. These operations can disagree because EP is approximate. No number of Sobol points proves exact posterior inference. A one-label V2 quadrature reference measures this approximation separately from numerical integration; a Gaussian-mixture fixture independently tests the paired score and its ranking.

**Matched selector controls.** All three primary selectors have the same V2 model, finite-batch decision rule, B6 startup, reference measure, future-output contract and actual outcomes:

| Selector | What the next query values |
|---|---|
| New balanced-risk lookahead | Expected reduction in the optimized finite-batch BA loss above |
| Existing V2 variance lookahead | Expected integrated variance reduction of canonical-label probability, with the same mixture and output availability |
| Aligned margin | Small absolute (A_m−B_m)/(A_m+B_m) at the candidate |

Historical 0.5, paid-fraction and posterior-mean-pi cutoffs are decision-only readouts on the same fitted probabilities. They never select queries here. Comparing them isolates a rule change; comparing the three sequential arms isolates selection conditional on the chosen model/rule. There is no simultaneous new-model/new-selector attribution and no historical 0.5-margin acquisition arm.

**Numerical acceptance and controlled evidence.** [Final manifest](MANIFEST.json), [initial selection](PROSPECTIVE_SELECTION.md), [pre-result amendment](AMENDMENT_00_BEFORE_RESULTS.md), [ledger](ATTEMPT_LEDGER.md), [independent checks](INDEPENDENT_CHECKS.json), [complete results](CONTROLLED_RESULTS.json).

Seven prespecified four-input worlds include informative, redundant and harmful depth; rare negatives; a locally mixed region; covariate-selected paid sets; and missing depth. The analytic laws are outside the fitted V2 family. Four fixed seeds, 24 candidates and 96 independent evaluator inputs per world; identical feature-only startup at B6, then four sequential queries. Region memberships and future outcomes stay outside the chooser. The selected-fraction world uses unequal feature density and a covariate-only startup that favors high first-coordinate values; neither maximin nor that startup is claimed prevalence-representative.

Sobol integration uses four independent scrambles, common normal draws across candidate/depth comparisons and separate component particles. Conditioning analytically on depth avoids importance collapse from a 0.03-noise likelihood. Future-label ESS includes component weights; low-ESS branch mass, refinement differences, near ties and selected IDs are saved. Numerical settings change only through the frozen convergence ladder. A Jensen construction computes the before/after risk from the same quadrature table; its nonnegative score does not establish posterior correctness. After the pre-computation audit, tower differences against independently integrated current risk must be <=0.002 and outcome normalization error <=1e-8. Numerical errors and posterior approximation errors are separate quantities. Four-scramble error estimates and adjacent-order agreement are diagnostics, not rigorous error bounds.

[Implementation amendment 01](AMENDMENT_01_NUMERICAL_AUDIT.md) records independent geometric-sum tail arithmetic, per-section reference caching, ledger-based accounting, additional acceptance gates and zero-class loss reporting. All preceded computation. Indeterminate decision signs are flagged; the code uses the sign of its estimate, with a positive action only on an exact zero. The initial selection note's broader wording about a positive numerical tie was imprecise; no decision rule was changed. Acquisition near ties use their separately frozen lowest-ID rule.

The planned ceiling is 420 main fit requests plus at most 24 validation fits; absolute ceilings are 600 top-level requests and **1,500 component solves** including failures/fallbacks. Up to 30 separately named independent-reference groups and 12 million independent-reference states were budgeted. Production QMC checks against those references have a separate 10-million component-draw-node ceiling, prospectively recorded in amendment 01. One numerical worker uses one BLAS/OpenMP thread and waits while the shared four-thread allocation is occupied. No external compute is purchased. Cached results, all failure records and path divergences are preserved; no seed replacement or retrospective tolerance tuning is allowed.

<!-- RESULTS_BEGIN -->
**Controlled results: matched decision/acquisition experiment**

Status: INCOMPLETE_WITH_PRESERVED_STOPS. 72/84 trajectories complete.

| World | BA-risk minus comparator | Complete / 4 | Valid BA pairs | Mean BA-AULC difference | Seed interval |
|---|---|---:|---:|---:|---|
| informative | probability_variance | 4 | 4 | +0.0081 | [-0.0181, +0.0343] |
| informative | balanced_margin | 4 | 4 | -0.0081 | [-0.0549, +0.0386] |
| redundant | probability_variance | 4 | 4 | +0.0151 | [-0.0260, +0.0563] |
| redundant | balanced_margin | 4 | 4 | -0.0110 | [-0.0926, +0.0705] |
| harmful | probability_variance | 4 | 4 | -0.0054 | [-0.0272, +0.0165] |
| harmful | balanced_margin | 4 | 4 | +0.0011 | [-0.0172, +0.0195] |
| rare_negatives | probability_variance | 2 | 2 | +0.0466 | [-0.0007, +0.0939] |
| rare_negatives | balanced_margin | 2 | 2 | +0.0552 | [-0.8506, +0.9611] |
| locally_mixed | probability_variance | 3 | 3 | -0.0069 | [-0.0311, +0.0173] |
| locally_mixed | balanced_margin | 3 | 3 | +0.0097 | [-0.0437, +0.0631] |
| selected_fraction | probability_variance | 3 | 3 | +0.0412 | [+0.0029, +0.0796] |
| selected_fraction | balanced_margin | 3 | 3 | +0.0631 | [-0.0802, +0.2064] |
| missing_depth | probability_variance | 4 | 4 | +0.0066 | [-0.0221, +0.0354] |
| missing_depth | balanced_margin | 4 | 4 | +0.0063 | [-0.0121, +0.0247] |

Intervals describe these four generated seeds. No universal selector ranking or query-saving claim follows.

Numerical diagnostics: 128 accepted query decisions were near ties; 0 query computations stopped. Max risk tower discrepancy: 0.00114384.

All per-seed/per-budget probabilities, decisions, class counts, local errors, uncertainty intervals, paths and stops are in CONTROLLED_RESULTS.json. Startup paid/reference/true-reference fractions and decision-only contrasts are in RESULTS_SUMMARY.json.

**Terminal outcomes, same model and decision rule.** Entries below are means across completed seeds; all per-metric counts and descriptive seed intervals are in RESULTS_SUMMARY.json. Undefined recalls remain null, not zero. Proper-score and local-region losses are not suppressed when BA improves.

| World | Selector | Complete / 4 | BA | Sensitivity | Specificity | Brier | Log loss | Region error | Region positive recall | Region negative recall |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| informative | balanced_risk | 4 | +0.8194 | +0.7331 | +0.9057 | +0.1418 | +0.4370 | +0.0119 | +0.9881 | NA |
| informative | probability_variance | 4 | +0.8372 | +0.7517 | +0.9228 | +0.1314 | +0.4135 | +0.0119 | +0.9881 | NA |
| informative | balanced_margin | 4 | +0.8334 | +0.7372 | +0.9297 | +0.1520 | +0.4620 | +0.0471 | +0.9529 | NA |
| redundant | balanced_risk | 4 | +0.7436 | +0.6835 | +0.8038 | +0.1724 | +0.5228 | +0.3718 | +0.5031 | +0.8438 |
| redundant | probability_variance | 4 | +0.7688 | +0.6895 | +0.8482 | +0.1707 | +0.5206 | +0.3173 | +0.5923 | +0.8125 |
| redundant | balanced_margin | 4 | +0.7602 | +0.6884 | +0.8320 | +0.1647 | +0.5048 | +0.3170 | +0.5586 | +0.9062 |
| harmful | balanced_risk | 4 | +0.7665 | +0.8150 | +0.7179 | +0.1447 | +0.4478 | +0.0649 | NA | +0.9351 |
| harmful | probability_variance | 4 | +0.7917 | +0.8502 | +0.7331 | +0.1380 | +0.4313 | +0.0971 | NA | +0.9029 |
| harmful | balanced_margin | 4 | +0.7721 | +0.8225 | +0.7218 | +0.1438 | +0.4508 | +0.0792 | NA | +0.9208 |
| rare_negatives | balanced_risk | 2 | +0.7757 | +0.6737 | +0.8778 | +0.0809 | +0.2950 | +0.2167 | +0.0000 | +0.8708 |
| rare_negatives | probability_variance | 2 | +0.7074 | +0.6371 | +0.7778 | +0.0863 | +0.3080 | +0.2667 | +0.5000 | +0.7708 |
| rare_negatives | balanced_margin | 2 | +0.7004 | +0.6230 | +0.7778 | +0.1068 | +0.3791 | +0.2667 | +0.0000 | +0.8333 |
| locally_mixed | balanced_risk | 3 | +0.7267 | +0.6526 | +0.8009 | +0.1040 | +0.3495 | +0.5238 | +0.1667 | +0.8838 |
| locally_mixed | probability_variance | 3 | +0.7532 | +0.6320 | +0.8744 | +0.1118 | +0.3709 | +0.5087 | +0.1000 | +0.9722 |
| locally_mixed | balanced_margin | 3 | +0.7032 | +0.6243 | +0.7821 | +0.1037 | +0.3497 | +0.5581 | +0.1167 | +0.8586 |
| selected_fraction | balanced_risk | 3 | +0.7932 | +0.7470 | +0.8393 | +0.1587 | +0.4864 | +0.0806 | +0.9778 | +0.0000 |
| selected_fraction | probability_variance | 3 | +0.7511 | +0.6872 | +0.8150 | +0.1967 | +0.5675 | +0.0806 | +0.9778 | +0.0000 |
| selected_fraction | balanced_margin | 3 | +0.7403 | +0.6733 | +0.8072 | +0.1997 | +0.5770 | +0.0806 | +0.9778 | +0.0000 |
| missing_depth | balanced_risk | 4 | +0.8110 | +0.7333 | +0.8886 | +0.1404 | +0.4358 | +0.0114 | +0.9886 | NA |
| missing_depth | probability_variance | 4 | +0.8247 | +0.7255 | +0.9239 | +0.1484 | +0.4539 | +0.0114 | +0.9886 | NA |
| missing_depth | balanced_margin | 4 | +0.7969 | +0.7443 | +0.8496 | +0.1539 | +0.4636 | +0.0471 | +0.9529 | NA |

The always-defined prospective loss (1-BA or 1/2 on a one-class batch) and its paired AULC contrasts are reported separately in RESULTS_SUMMARY.json. Numerical-stop outputs remain in the raw file but are not treated as accepted endpoints.

Budget used: 374 top-level requests; 1122 component solves; 0 component solves reserved for unresolved interruptions. No query-saving endpoint was estimated.

Independent references: exact fixed-pool action error 5.55e-17; IID-batch enumeration error 5.55e-16; Gaussian-mixture acquisition error 6.14532e-05. The one-label V2 EP probability/risk errors are 0.0167755/0.0160641; its paired-score discrepancy is 0.00724152, with reference refinement difference 0.00141147. These separate posterior error from integration error. The two-state posterior-mean-prevalence approximation incurs risk regret 0.0542589.

The known-probability mixed-cell counterexample reaches BA 0.8630 while retaining zero positives in that cell. The fixed 80% cell-recall safeguard lowers BA to 0.5726; it does not identify individuals.

<!-- RESULTS_END -->

**Why this need not protect transient positives.** Consider a target with 80% of features in an easy cell with eta=0.98 and 20% in a mixed cell with eta=0.55. Its prevalence is 0.894. Even with perfectly known probabilities, BA calls the mixed cell negative. Thus a loss-aligned query can rationally stop spending on a scientifically interesting region once the posterior believes its best BA action is uniformly negative. Exact arithmetic in the additional-idea reference reports the BA, local recall and local irreducible error. This is a constructed-world limitation, not an impossibility result for SPH.

The single additional idea is deliberately bounded: a predeclared feature-cell positive-recall safeguard. One two-variable linear program imposes 80% expected positive recall within the mixed cell. Its probabilities constitute a point-mass posterior in this perfect-information counterexample, not hidden evaluator truth supplied to a sequential learner. It protects expected cell recall at a calculable BA cost, but it cannot identify which individuals are positive when their available-channel distributions coincide. The constraint uses a feature cell and probabilities, not hidden short-K/q20 membership. No fourth sequential method or constraint sweep is run. Actual short-K guarantees would require legitimate information that predicts that subgroup, a scientifically justified loss, or separately purchased frame-level targets. The latter changes the oracle and must be manifested separately.

**Prior work and what is contributed.** Bayes decisions under class-weighted loss are established, as is prevalence-threshold consistency under appropriate sampling/estimation assumptions. Expected-error-reduction acquisition predates this thesis: [Roy & McCallum (2001)](https://groups.csail.mit.edu/rrg/papers/icml01.pdf). Decision-theoretic treatment of nondecomposable metrics explicitly distinguishes expected finite-sample utility from population measures: [Natarajan et al. (2015)](https://arxiv.org/abs/1505.01802). Gaussian/probit lookahead and global LSE acquisitions are also established: [Letham et al. (2022)](https://proceedings.mlr.press/v151/letham22a.html). None proves superiority for this mixture, target or SPH dataset.

Repository [Week 13 theory](https://github.com/iso0/active-level-set-week1-warmup/blob/2b22c13df41ee0179d5999ff07a98c0aa36814ca/outputs/week13_boundary_evaluation_and_mechanisms/THEORY.md) already derives the accuracy/BA metric-disagreement window and warns about q20 composition. Phase 1.18B's exact-fixed SUR [primary decision](https://github.com/iso0/active-level-set-week1-warmup/blob/2b22c13df41ee0179d5999ff07a98c0aa36814ca/outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark/primary_decision.json) returned `GLOBAL_SUR_NO_GAIN`, and its [saving test](https://github.com/iso0/active-level-set-week1-warmup/blob/2b22c13df41ee0179d5999ff07a98c0aa36814ca/outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark/sample_efficiency_decision.json) returned `LABEL_SAVING_NOT_SUPPORTED`; changed paths alone were explicitly insufficient. This package is not a claim that global SUR has now become novel or universally superior. The implementation contribution is a coherent finite-batch BA decision and paired depth/label mixture lookahead, bounded uncertain-class weights, exact fixed-panel checks, and controlled attribution against matched variance/margin selectors. Any claim of a genuinely new combination is local to this implementation; no exhaustive priority claim is made.

**Interpretation and next discriminating experiment.** A decision rule can change which errors are valuable without learning anything new. The strongest competing explanation is that local response/probability structure, or limited paid observations there, remains inadequate after the global rule is corrected. The cheapest discriminating real-data step is to export full joint component posteriors from Opus's completed V2 checkpoints, once available, and compare decision rules on the exact same fits/paths, without new model fitting. If BA changes while short-K retention collapses and local proper scores remain weak, the gain is primarily loss reallocation. If reference-weight correction stabilizes decisions under selective paid composition and improves both local recalls, it supports the proposed decision/reference mechanism. If the same posterior cannot separate the local cases under any scientifically acceptable loss, compare the already planned J_trained/stump and temporal evidence before changing acquisition or model capacity. [Precise bounded handoff](OPUS_DECISION_ACQUISITION_REQUEST.md)

C3 remains spent. C4 and real-data Stage A remain unexecuted here. Fresh random partitions of these inspected simulations can test stability conditional on the dataset and frozen procedure; they are not independent new data. Prospective generalization, observation-window validity and physical-boundary claims require genuinely new simulations/annotations under a predeclared observation process. No label, exclusion, input, q20 or paid-output definition changes; no q30 is introduced.

<!-- TURKISH_BEGIN -->
**Türkçe açıklama.** Yenilik, modelin olasılıklarını ve sınıf oranı belirsizliğini aynı karar hesabında tutmak ve sonraki simülasyonu aynı BA kaybında beklenen azalmaya göre seçmek. V2 modeli değişmedi. Ücretli örneklerdeki pozitif oranı hedef kitlenin oranı sayılmadı. Matematiksel karşı örnek, kusursuz olasılıklarla bile yüksek BA uğruna karışık bölgedeki bütün pozitiflerin feda edilebildiğini gösteriyor. Bu yüzden yeni kural fiziksel sınırı bulma garantisi vermiyor. Sentetik sonuçlar yukarıda kayıpları ve sayısal duruşlarıyla birlikte verildi; SPH üstünlüğü veya sorgu tasarrufu kanıtlanmış değil. En ayırt edici sonraki adım, Opus'un tamamlanan V2 kayıtlarında yalnızca karar kuralını değiştirip BA ile kısa-Keyhole yakalamayı birlikte karşılaştırmak; yerel ayrım zayıf kalırsa sorun yalnızca eşik değildir.
<!-- TURKISH_END -->
