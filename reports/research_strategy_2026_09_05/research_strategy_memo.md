# From predictive classification to identifiable boundary learning

**Independent research strategy memo | 5 September 2026**  
**For:** TUM Mathematics MSc thesis, *Sample-Efficient Active Level-Set Estimation, with an Application to Melt-Pool Regime Boundaries*  
**Evidence cut:** published research branch through `bf4782881bc27fe1ec5256dc3ba0516478a1ed13`, with the separate temporal branch examined explicitly.

## Decision in brief

**Primary recommendation: use the independently generated new finite pool as a locked external test of physics-coordinate threshold-surface learning, with M3 as the incumbent and a same-model acquisition contrast. Do not assume that a new pool fixes the old pool's coverage or depletion limitations.**

**Corrected operational premise:** the new simulations have already been run. Their locations cannot be chosen. The supervisor is manually labelling them this weekend, and the labels have not yet been observed by the research workflow. Consequently, continuous query generation, custom power sweeps and new matched observation windows are **not available interventions in this study**. Their mathematics remains useful for identifying what a finite pool cannot resolve, but they are not the recommended next action.

The immediate scientific asset is a pool generated independently of the acquisition methods whose labels can still be kept out of development. Freeze the models, oracle interface, metrics, query budgets and success rule before inspecting those labels. The important distinction is between **independently generated data** and **necessarily distribution-shifted data**: the first is given; the second must be checked from inputs and metadata.

Three corrections to the historical story remain essential.

1. **Active learning has already succeeded narrowly.** Week 8.5 established Binary-GPC margin versus matched Random on the frozen offline q20 endpoint. What remains unresolved is M3's incremental acquisition benefit beyond its supported same-path predictive benefit.
2. **The negative SUR experiment did not exhaust level-set objectives.** Phase 1.18B tested a finite-pool predictive-probability functional, not Letham et al.'s posterior level-set-membership GlobalSUR.
3. **Direct threshold GPs have close prior art.** Keeley et al. (2023) already model contextual threshold/intercept and slope with binary observations and threshold-specific acquisition. The fixed-slope probit model is a structured GPC special case. Novelty must come from a sharper result, not that model name. [Frozen confirmation][R85]; [Phase 1.18B][R18B]; [applicability audit][RLetham]; [Keeley et al.][LKeeley].

My diagnosis is an **experimental-support and estimand bottleneck, compounded by posterior limitations**. The new pool permits a fresh test of whether that diagnosis transfers. It cannot retroactively provide continuous boundary ground truth or a prospective reduction in already-incurred simulation cost.

This memo develops three serious options. The primary option is a structured threshold model evaluated through a frozen finite-pool protocol. The fallback is coherent general random-set estimation if the graph restriction is inadequate. All new outputs must be hidden until the associated query in the simulator-information replay; otherwise the task becomes active manual annotation with free simulation outputs, a different cost claim. Sections 9–10 specify the corrected finite-pool design without assuming a pool size or controllable simulation settings.

## 1. Evidence provenance and branch reconstruction

I inspected committed reports, claim ledgers, red-team reports, validation reports, relevant model/evaluation code, and machine-readable outputs. I checked live remote branch heads against the local objects. The latest Phase 1.19B head matches the remote. The Week 9 Phase 1 chain is sequential through 1.19B, including the external-validation and closure work. The default repository branch is not a reliable entry point to current science: it contains much earlier work. The local main checkout also contains unrelated edits; none were changed.

The separate temporal branch, `codex/week9-phase2-temporal-width-dynamics`, ends at `da913797d14b171bec55d3708f96aa87f09a4f94` and diverges at Phase 1.8 commit `f74c6252bbb48d503f969ef5300f20894079301b`. Its corrected transverse-width conclusions must be read separately; they are not an update to M3's later acquisition results. [Temporal report][RTemporal].

The reported validation counts for Phases 1.14, 1.15A, 1.16, 1.17A, 1.18A, 1.18B0, 1.18B, 1.19A and 1.19B are respectively 56, 32, 31, 27, 32, 28, 44, 27 and 27 passing checks. These are **repository-reported validations**, inspected here, not experiment reruns performed for this memo. I independently recomputed the depletion diagnostics in Section 4 from saved candidate states. I did not rerun GP trajectories or the SPH simulator.

The owner profile was accessible, but a live read of the `sph_v2` dataset page failed. Data conclusions therefore rest on the repository's pinned extracts and audits, not an independently re-downloaded current Hugging Face population. Search coverage includes primary literature through the accessible 2026 publications; inaccessible material is not treated as verified full text.

### Compact chronology

| Stage | Scientific question and result | What it does not establish |
|---|---|---|
| Weeks 1–4, synthetic | Progression from simple latent regression on signs through acquisition comparisons, multidimensional boundaries and GPC/SUR work. Known synthetic functions permit boundary-oriented evaluation. | A synthetic advantage does not transfer automatically to SPH. |
| Week 7, physical proxies | Observed Max-Depth is a strong manual-regime separator; physical G3 is informative but less transfer-stable. Regression of boundary-near depth and hybrid acquisition did not dominate Binary. | An oracle output separator is not an accurate process-input surrogate. |
| Week 8 and 8.5 | Frozen 405-row benchmark; 20 repeat blocks × five folds, paired starts and Random continuations. Binary margin q20 accuracy AULC 0.8135 versus Random 0.7762; difference +0.0373, 95% interval [0.0301, 0.0444]. | No universal simulation-saving multiplier or verified continuous physical-boundary accuracy. |
| Week 9, 1.5–1.9 | Strong h-coordinate discrimination; early physics-guided modelling; crossed model/path comparisons separate predictor benefit from path benefit; generic-direction controls interrogate specificity. | Physics-guided improvement is not automatically acquisition improvement. |
| 1.10 and closure | External experiments support discrimination by a physics coordinate, but theoretical exponent specificity is not established. Results depend on transition labels and regularization. | No external validation of the full M3 active-learning pipeline. |
| 1.11–1.13 | Isotropic discrepancy is insufficient; ARD and bound-matched controls lead to M3. M3's same-path gain over H is supported. | The residual is not an identified physical correction. |
| 1.14 | M3-margin versus M3 evaluated on the old A0 path: overall q20 difference +0.002132, interval [−0.001167, 0.005621]; late gain only. | Overall q20 sample-efficiency superiority is unresolved. |
| 1.15A | Residual correction is near-margin-enriched but highly redundant with margin; no new trajectory. | No independent committee signal or acquisition gain. |
| 1.16 | Repulsion changes geometry. All five overall q20 intervals cross zero; q30 has small positive secondary effects. | No robust performance scale or supported label saving. |
| 1.17A | Added distance is mixed: physical tangent 42.9%, normal 30.1%, ST 26.9% of positive extra squared-distance energy. | Neither normal escape nor ST escape is a sufficient explanation. |
| 1.18A/B0 | PA-TVR rejected; small posterior approximation error does not preserve SUR rankings; FAST rank-one gate fails. | Distinct rankings alone are not a useful acquisition. |
| 1.18B | Exact-fixed and physics-refit finite-pool probability SUR fail to improve primary q20. | Not a rejection of every random-set or Bernoulli-LSE SUR objective. |
| 1.19A | Configuration/window sensitivity, likely floor censoring, low-budget separation, and strong approximate partial order are documented. | No causal attribution to windows or proof of continuous monotonicity. |
| 1.19B | New full-pool/composite task: monotonic inference and candidate removal harm balanced-accuracy AULC; class-direction safety fails. | Its very high pool accuracy cannot be compared with earlier held-out q20 as if the endpoint were unchanged. |

Sources: [Week 8.5][R85], [Week 7 benchmark][R7], [Phase 1.13][R13], [1.14][R14], [1.15A][R15], [1.16][R16], [1.17A][R17], [1.18A][R18A], [1.18B0][R18B0], [1.18B][R18B], [1.19A][R19A], [1.19B][R19B]. Earlier-stage numerical details and nomenclature qualifications follow below.

### What M3 actually is

Let (x=(P,VX,LS,ST)), with ST denoting **substrate temperature**. The feature is

\[
h(x)=\frac{P}{\sqrt{VX\,LS^3}}.
\]

M3 first fits a nearly unpenalized logistic regression to standardized \(\log h\), using only the revealed labels:

\[
m_{h,n}(x)=\widehat a_n+\widehat b_n\,s_n(\log h(x)).
\]

It then freezes that fitted mean during Stage 2 and fits

\[
f(x)=m_{h,n}(x)+r(x),\qquad
r\sim GP(0,k_{\mathrm{ARD\ Mat\acute ern}\,3/2}),\qquad
Y\mid f\sim\operatorname{Bernoulli}(\operatorname{logistic}f).
\]

The discrepancy uses standardized raw **P, VX, LS, ST**, not an additional log-h coordinate. The residual SD is constrained to 0.05–1 and four length scales to 0.01–100 in the primary implementation; the Stage-1 logistic setting is C=10⁶. Stage 2 uses Laplace inference and empirical-Bayes optimization. Prediction integrates the approximate Gaussian latent posterior. Consequently, probability margin depends on both latent mean and latent variance. Calling M3-margin “variance blind” is incorrect. Stage-1 estimation uncertainty is **not** propagated. [M3 posterior semantics][RSemantics]; [M3 construction and controls][R13].

M3 is therefore a **two-stage plug-in physics mean plus flexible residual classifier**. It is neither a fully Bayesian decomposition nor an orthogonally identified physics/discrepancy model. Because h is derived from the residual's inputs, both components can describe overlapping structure. A bound on prior SD is also not a hard bound on every GP realization.

### Why the predictive improvement is credible

On exactly the same A0 query paths, q20 accuracy AULC is H 0.830813, ordinary GPC 0.813520, standalone ARD GPC 0.826595, isotropic hybrid M2 0.830230, and M3 0.842491. M3−H is +0.011677 [0.007201, 0.016149], with 18/20 repeat contrasts positive. Against bound-matched isotropic M2W, the difference is +0.012261 [0.007624, 0.016609]. The latter control matters: the result cannot simply be attributed to giving M3 a wider scalar length-scale range. [Phase 1.13][R13].

The mechanism is consistent with a strong low-dimensional prior followed by useful anisotropic corrections as labels accumulate. Relative to H, M3 changes only 1.1%, 4.2% and 5.5% of q20 decisions at B16, B40 and B80; among changed decisions, beneficial fractions are 47.4%, 66.2% and 71.3%. The residual helps especially once enough exceptions have been seen. These are explanatory associations, not causal identification of a physical correction. The q20 M3−H AULC gain is +0.004436 early and +0.016094 late. At B80, standalone ARD GPC has better KH recall than M3 despite similar accuracy. Thus “best” must retain its metric and budget scope. [Phase 1.13][R13].

## 2. Verification of the supplied hypotheses

Here “supported” means supported within the inspected experiment, not established for all simulator configurations or continuous domains.

| Hypothesis | Verdict | Evidence and qualification |
|---|---|---|
| M3 is the strongest supported predictive hybrid | **SUPPORTED** | Preferred hybrid on the same-path frozen endpoints. Not best on every metric, subgroup or budget. |
| Predictive gain over physics-only H is statistically supported | **SUPPORTED** | M3−H q20 AULC +0.011677 [0.007201, 0.016149]. |
| M3-margin has no clear overall q20 gain | **SUPPORTED** | +0.002132 [−0.001167, 0.005621] versus same M3 on A0; late and q30 benefits remain qualified secondary findings. |
| Residual/disagreement information is highly redundant with margin | **SUPPORTED** | Correction magnitude versus margin Spearman −0.951; proposed score versus original score +0.983. H and M3 are nested, not independent committee members. |
| Repulsion gives no robust q20 gain | **SUPPORTED** | All five primary intervals include zero; no Holm-supported overall winner. |
| Exact finite-pool probability-uncertainty SUR does not beat margin | **SUPPORTED** | Exact-fixed ΔAULC −0.001379 [−0.003801, 0.000726]. “Exact” refers to the numerical Laplace update with specified fixed parameters, not exact Bayesian inference. |
| Physics-refit SUR changes paths but does not help | **SUPPORTED** | Δ versus margin −0.004453 [−0.010703, 0.001627]; B80 P2/P1 Jaccard 0.662. |
| Near-monotonic structure is real but hard propagation harms AL | **SUPPORTED** | Three violations among 22,050 comparable pairs; Phase 1.19B primary harm and directional inference errors. Only empirical order structure is verified. |
| Low-budget Stage-1 mean can be too sharp/separable | **SUPPORTED** | At B16, 55% exact separability; coefficient median 20.978. Probability-quality conclusion remains mixed. |
| Overconfidence does not fully explain acquisition failure | **PARTIALLY SUPPORTED** | Plausible because failures persist beyond the early-separation period and path changes fail to help. No decisive fully Bayesian or calibration intervention isolates its causal contribution. |
| Informative boundary-near candidates become depleted | **PARTIALLY SUPPORTED** | Strong late collapse of model-uncertain candidates; substantial physical-band candidates still remain at B40/B60. Informativeness itself is not observed. |
| Observed Max-Depth separates well but is harder to predict near the boundary | **SUPPORTED** | Physical-proxy and regression and physical-proxy acquisition history support the distinction; oracle discrimination does not establish an exploitable query signal. |
| 405 simulations mix configurations and windows | **SUPPORTED** | Three exact configurations: 364, 27 and 14 rows; 167/405 flagged as ending before 90% domain traversal. |
| Depth has censoring/floor issues | **SUPPORTED** | Strong empirical evidence: 39 KH rows in a depth pile around 301–312 µm. The pile is a likely physical-domain limitation, not a verified universal censor threshold. |

Sources: [R13][R13], [R14][R14], [R15][R15], [R16][R16], [R18B][R18B], [R19A][R19A], [R19B][R19B], and the independent saved-state calculation in Section 4. The two “partially supported” verdicts intentionally resist treating a plausible mechanism as causally established.

## 3. The bottleneck: what is established, and what is not

### Prediction and experimental utility are different mathematical quantities

A better predictor at a fixed dataset means lower loss \(L(M_3,D_n)\). A better query requires a larger expected *change* in that loss:

\[
V(x;D_n)=L(D_n)-\mathbb E[L(D_n\cup\{(x,Y_x)\})\mid D_n].
\]

There is no implication from lower \(L\) to larger variation of \(V(x;D_n)\) across available x. A strong physics mean can improve all paths while reducing the number of decisions that any extra label can change. When candidate values are similar or tiny, elaborate ranking has little room to help. The earlier model/path decomposition and the Phase 1.13/1.14 separation directly illustrate this distinction.

### The tested probability objective differs from the boundary object

For a probabilistic latent classifier distinguish

\[
p_n(x)=\mathbb E[\sigma(f(x))\mid D_n],\qquad
\pi_n(x)=\Pr(f(x)>0\mid D_n).
\]

The first predicts a label under the surrogate observation model. The second describes posterior membership in the latent positive set. For a probit link and Gaussian latent posterior \(N(m,v)\),

\[
p_n=\Phi\!\left(\frac m{\sqrt{1+v}}\right),\qquad
\pi_n=\Phi\!\left(\frac m{\sqrt v}\right).
\]

These can differ greatly. At a fixed small positive m, as v tends to zero, set membership becomes certain, while predictive-label probability can remain near one half. The decomposition

\[
p_n(1-p_n)=\mathbb E[\sigma(f)(1-\sigma(f))\mid D_n]
+\operatorname{Var}(\sigma(f)\mid D_n)
\]

shows the mixture of likelihood-level uncertainty and reducible epistemic uncertainty. For this deterministic simulator, likelihood noise is a modelling approximation; it must not be mistaken for physical randomness. A model that represents a deterministic threshold directly avoids introducing an irreducible response-noise floor unless one is deliberately added for discrepancy or annotation effects.

A coherent level-set decision loss is instead

\[
R_n=\int\min\{\pi_n(u),1-\pi_n(u)\}\,d\mu(u),
\qquad a_n(x)=R_n-\mathbb E[R_{n+1}\mid D_n,x].
\]

That distinction is precisely why the Phase 1.18B result is not a test of all Bernoulli-LSE approaches. [Repository applicability audit][RLetham]; [Letham et al. 2022][LLetham]. It is a reason to define the random object and loss first, not a prediction that replacing one criterion will win.

There is a second issue. Phase 1.18B integrates over the **currently unqueried** pool and removes each hypothetical candidate from the next average. Thus the reference measure changes. Under a coherent joint predictive distribution for binary variables, with N remaining points, \(v_j=\operatorname{Var}(Y_j\mid D_n)\), \(U=N^{-1}\sum v_j\), and \(c_{jx}=\operatorname{Cov}(Y_j,Y_x\mid D_n)\), the corresponding expected reduction equals

\[
\Delta_x=\frac{v_x-U}{N-1}
+\frac1{N-1}\sum_{j\ne x}\frac{c_{jx}^2}{v_x}.
\]

This follows from the law of total variance for a binary conditioning variable. One term rewards removal of the candidate's own uncertainty; another measures learning elsewhere. It is not purely geometric boundary learning. M3's empirical-Bayes refits and Laplace approximation need not obey this identity exactly, so this is an explanation of the objective's structure, not a reproduction of its numerical scores. A fixed reference design makes the intended domain loss much clearer.

### Posterior limitations are plausible contributors, not the proven sole cause

M3 omits uncertainty in \(\widehat a_n,\widehat b_n\). With standardized physics coordinate t and approximate boundary t₀, a small residual perturbation moves the root by

\[
\Delta t\simeq-\frac{r(t_0,z)}{\widehat b_n+\partial_t r(t_0,z)}.
\]

A large Stage-1 slope and regularized residual can make substantial boundary movement unlikely. This is a real structural concern. But high coefficients can also be appropriate for a deterministic sharp transition; confidence is not automatically miscalibration. Stage-1 separation falls from 55% at B16 to 9% at B24. No inspected experiment establishes that integrating slope uncertainty fixes the acquisition result. [Stage-1 audit][R19A].

The FAST validation supplies a separate lesson: probability errors of roughly 10⁻⁵–10⁻⁴ can alter rankings of tiny differences in integrated uncertainty. Its median rank correlation with exact-fixed scoring was 0.4813, top-1 agreement 44%, and sign-reversal rate 28.7%. Numerical posterior accuracy and decision accuracy require different tolerances. [Phase 1.18B0][R18B0].

### Ranked assessment of the proposed bottlenecks

| Candidate limitation | Assessment |
|---|---|
| C/E: finite support and insufficient boundary sampling | Strongest actionable limitation, especially late. Cannot determine continuous boundary resolution from this static pool. |
| F/G: acquisition objective and q20/LSE mismatch | Mathematically definite distinction. Its contribution to the observed numerical failure is not experimentally isolated. |
| B: posterior calibration | Credible early contributor; Stage-1 uncertainty omission is real. Causal dominance unproven. |
| I: configuration/window/label definition | Real data-design issue. Must be fixed before interpreting a physical boundary. Existing sensitivity does not prove it explains most errors. |
| A/K: generic-classifier bias versus direct boundary structure | Worth a structural test. M3 is already strong, and a graph restriction can be wrong. |
| D: four inputs cannot explain exceptions | **Not established.** Varying configuration, observation exposure, numerical effects and sparse design are competing explanations. |
| H: binary labels discard useful information | True information-theoretically as a possibility; useful *conditional* auxiliary information has not been established. |
| J: nonstationary or discontinuous geometry | Plausible, not demonstrated by ARD lengths or a few exceptions. Requires controlled local cross-sections. |
| L: repeated use of one benchmark | Important inferential limitation. Frozen within-phase tests do not make the repeatedly inspected dataset untouched across the whole research programme. |

The current evidence cannot justify a uniquely identified dominant *physical* mechanism. It does justify a label-blinded support/configuration audit and a locked external test. Because the new runs are already complete, normal crossing, tangent variation and exposure can only be examined where the fixed pool supplies the necessary comparisons.

## 4. Finite-pool depletion: a measured effect with an important limit

I recomputed candidate counts from the **100 primary L100 M3-margin trajectories at six saved checkpoints** in Phase 1.18A. A retrospective physical overlap band was defined transparently as

\[
\mathcal H=[\min_{i:Y_i=1}h_i,\max_{i:Y_i=0}h_i]
=[6.96844519\times10^8,1.69905492\times10^9].
\]

It contains **83 of 405 simulations**. This uses all historical labels and is strictly a retrospective diagnostic. It must not be passed to the historical chooser or described as a previously frozen acquisition band. Numerical h values use the repository's W, m/s and m units.

| Budget | Mean remaining pool | Mean remaining in physical h band | Mean with p in [0.1,0.9] | Mean with p in [0.2,0.8] | Median with p in [0.4,0.6] |
|---:|---:|---:|---:|---:|---:|
| 16 | 308 | 62.00 | 46.02 | 25.88 | 5 |
| 24 | 300 | 54.11 | 43.48 | 22.43 | 3 |
| 32 | 292 | 46.32 | 42.13 | 19.08 | 1 |
| 40 | 284 | 38.45 | 41.75 | 16.53 | 0 |
| 60 | 264 | 20.95 | 12.81 | 1.28 | 0 |
| 80 | 244 | 8.74 | 0.28 | 0.12 | 0 |

Source inputs: [saved pre-reveal candidate states][RStates] and [configuration/population table][RConfigTable]. Counts are descriptive averages across correlated outer runs, not new confidence intervals. No simulations or paths were added.

**Interpretation:** the proposed O(50–70) informative subset is plausible as an order of magnitude, but it is not a uniquely established subset of truly informative points. After B16, an average of 62 unqueried physical-band points remain; by B60 roughly 41 of them have been queried, while 21 remain. Model uncertainty becomes scarce sooner than physical overlap disappears. We must distinguish useful-point exhaustion from a model becoming confidently wrong.

If a fixed genuinely informative subset S has K points, querying all K leaves no new information *of that kind* in the pool. But this does not prove that other points cannot inform kernel scales, exceptions or global geometry. Nor does it prove that all algorithms reach the same state. The late saturation argument is conditional, not an impossibility theorem for every acquisition.

For an AULC over [16,80], suppose two policies have the same loss after Bₛ. Then

\[
|\Delta\mathrm{AULC}|\le\frac{B_s-16}{64}
\sup_{16\le b\le B_s}|L_A(b)-L_B(b)|.
\]

For example, a two-percentage-point early advantage lasting only to B40 contributes at most 0.75 percentage points overall. However, if policies differ after Bₛ because their training sets differ, the late difference need not disappear. “Late AULC is pool dominated” is a plausible interpretation, not an automatic mathematical conclusion.

The more fundamental limitation is **resolution**. On one fixed tangent context, if all available powers below a gap are C and all above it are KH, every threshold inside that gap is observationally indistinguishable from the pool labels. Without new interior queries, worst-case threshold error cannot be reduced below half the gap. In multiple dimensions, unmeasured tangent regions permit different boundary surfaces agreeing at every observed point. Smoothness assumptions can bound these gaps; the 405 labels alone cannot.

The experiment is legitimately **pool-based active learning**, not “merely ranking” in a pejorative sense. But it establishes an adaptive label-revelation advantage on an archived design. It does not establish that a continuous simulator boundary is localized more efficiently when arbitrary new settings can be requested. Continuous query synthesis and multiscale candidate refinement already have substantial prior art. [Zhao et al. 2021][LZhao]; [Shekhar and Javidi 2019][LShekhar].

## 5. Direct boundary representation: precise formulation and falsification

The model applies to the available finite pool. The continuous bracketing calculations below explain identifiability and resolution limits; they are a counterfactual design analysis, not an instruction to choose locations for the already-run simulations.

### Coordinates and the physical object

Use dimensionless logarithms. Choose reference values P₀=200 W, V₀=0.6 m/s, L₀=60 µm and T₀=350 K, and define

\[
u=(\log(P/P_0),\log(VX/V_0),\log(LS/L_0)),\quad
a=(1,-1/2,-3/2),\quad \ell=a^Tu=\log(h/h_0).
\]

Here \(h_0=P_0/\sqrt{V_0L_0^3}\). Taking the log of bare dimensional h only implicitly fixes units; the ratio makes that choice explicit. LS is the verified laser spot-radius parameter, not an arbitrary diameter convention. Changing reference units shifts the intercept, not the boundary physics.

Two valid coordinate charts serve different purposes:

**Operational chart:**
\[
z=(\log(VX/V_0),\log(LS/L_0),(ST-T_0)/50),\quad
P=P_0\exp(\ell+z_1/2+3z_2/2).
\]

Holding z fixed makes a boundary search a power sweep. This chart is invertible. Its constant-ell coordinate directions lie in the physics contour, although the chart is not orthogonal in log-input Euclidean distance.

**Orthogonal geometry chart:** choose
\[
q_1=(1,2,0)/\sqrt5,\quad q_2=(6,-3,5)/\sqrt{70},\quad
Q=(q_1,q_2),\quad z_T=Q^Tu.
\]

Then \(Q^Ta=0\), \(Q^TQ=I\), and
\[
u=\frac a{a^Ta}\ell+Qz_T.
\]

Add standardized ST as the third context coordinate. This separates normal and tangent directions exactly in the chosen **log-input metric**. It is not the earlier standardized raw-input geometry, and neither normal is automatically the true regime-boundary normal. I recommend the operational chart for modelling the available pool, and the orthogonal chart as an old-data sensitivity analysis. No coordinates of the new simulations would be changed.

The proposed object is

\[
\mathcal B=\{(\ell,z):\ell=\tau(z)\},\qquad
S=\{(\ell,z):\ell>\tau(z)\},
\]

for a specified material, simulator configuration, observation exposure and label rule. This asserts a **single crossing along the chosen normal coordinate**. It permits complex tangent variation, including ST effects. It does not require monotonicity in every tangent coordinate. If a power sweep at fixed VX, LS, ST has reliable C→KH→C transitions, a single graph is false there.

### Model, identification and inference

For hard deterministic labels,

\[
\tau\sim GP(m_\tau,k_\tau),\quad
Y_i=\mathbf1\{\ell_i>\tau(z_i)\},
\]
\[
p(\tau_D\mid D)\propto\phi_K(\tau_D-m_D)
\prod_{i:Y_i=1}\mathbf1\{\tau_i<\ell_i\}\prod_{i:Y_i=0}\mathbf1\{\tau_i\ge\ell_i\}.
\]

At repeated context z, negatives imply a lower bound and positives an upper bound:

\[
L(z)=\max_{i:z_i=z,Y_i=0}\ell_i
\le\tau(z)<
U(z)=\min_{i:z_i=z,Y_i=1}\ell_i.
\]

The finite-dimensional posterior is truncated Gaussian, not ordinary conjugate GP regression. Merge repeated contexts into their tightest consistent bounds. Empty intervals falsify the hard model; they are not a numerical nuisance to hide. Truncated-normal sampling or constrained latent-Gaussian methods are appropriate. With soft probit inequalities,

\[
Y_i\mid\tau\sim\operatorname{Bernoulli}
\left[\Phi\left(\frac{\ell_i-\tau(z_i)}s\right)\right],
\]

Laplace or EP can supply an initial approximation; for n≤405, compare threshold quantiles with a whitened latent-variable MCMC reference on a small set of prefixes. Probit augmentation introduces \(w_i=\ell_i-\tau_i+s\epsilon_i\) truncated according to Y. Conditional Gaussian updates then alternate with truncated w updates. Hyperparameter uncertainty requires integration or explicit sensitivity, not merely refitting a maximum. Skew-GP work provides related exact posterior structure for affine probit inequalities. [Benavoli et al.][LSkew]; [Takeno et al.][LTakeno]; [Chu and Ghahramani][LOrdinal].

Finite labels identify brackets, not unique thresholds. Outside sampled contexts, inference rests on the prior and coverage assumptions. A GP prior regularizes an underdetermined problem; it does not create empirical identifiability. Free context-dependent slope and threshold can be weakly identified without several ell levels per context. Begin with a fixed observation scale in the soft sensitivity model, or a small number of pooled scales, rather than another GP for every nuisance parameter.

For a deterministic fixed-configuration simulator, s>0 represents discrepancy, unresolved inputs or annotation uncertainty. It is not automatically repeat-run physical noise. Repeating identical deterministic simulations cannot estimate a Bernoulli probability. The threshold is a physical boundary only when the hard single-crossing model is credible; otherwise the probit threshold is a conditional 50% transition under the chosen observation model.

### Is this meaningfully different from GPC?

Yes as a structural restriction; no as a new general model family. For fixed s, define

\[
g(\ell,z)=(\ell-\tau(z))/s.
\]

It is exactly a GP with mean \((\ell-m_\tau(z))/s\) and covariance \(k_\tau(z,z')/s^2\), independent of ell except through its known mean. Thus the soft model is structured probit GPC with a known positive ell coefficient and lower-dimensional covariance. It pools evidence along power sweeps and expresses uncertainty in log-power/threshold units. This can be useful without being novel.

It removes the specific need to estimate an almost-unbounded Stage-1 logit slope before permitting a residual correction. It does **not** eliminate overconfidence from wrong smoothness, omitted configuration, a falsely imposed graph, or a poor approximate posterior. With fixed s, far-from-boundary likelihoods still saturate; that is often appropriate. Near-boundary placement, rather than a different sigmoid alone, supplies the new information.

### Exact boundary-variance objective

For squared threshold error under a fixed context measure \(\nu\), the posterior Bayes risk is

\[
V_n=\int\operatorname{Var}_n[\tau(z')]\,d\nu(z').
\]

For any current posterior and binary Y, total variance gives

\[
A_n(z,\ell)=V_n-\mathbb E[V_{n+1}\mid D_n,z,\ell]
=p(1-p)\int[m_1(z')-m_0(z')]^2d\nu(z'),
\]

where \(m_y(z')=\mathbb E[\tau(z')\mid D_n,Y_{z,\ell}=y]\). This is the exact objective, with posterior expectations computed analytically or by sampling.

If the **current** threshold posterior is Gaussian with mean m, variance v and covariance C, then, with

\[
t=\frac{\ell-m(z)}{\sqrt{v(z)+s^2}},\quad p=\Phi(t),
\]

the derived one-step formula is

\[
A_n(z,\ell)=
\frac{\phi(t)^2}{[v(z)+s^2]\Phi(t)[1-\Phi(t)]}
\int C(z',z)^2\,d\nu(z').
\]

The derivation uses \(\operatorname{Cov}(\tau(z'),Y)=-C(z',z)\phi(t)/\sqrt{v(z)+s^2}\). For fixed z and unconstrained ell, the factor is maximized at ell=m(z), giving \((2/\pi)\int C^2/(v+s^2)\). Under a Gaussian approximation this separates **where along the boundary to learn** from **where to cross it**. Under a non-Gaussian posterior, the exact sample-based objective need not be maximized at its mean. Binary updates do not preserve Gaussianity; recursively using the closed form is an approximation requiring checks.

This derivation is a standard Bayesian-design specialization, not a novelty claim. Its value here is that it targets a physically interpretable estimand and explicitly includes cross-context covariance, unlike the rejected geometry-local PA-TVR proposal.

### A useful conditional resolution bound

Suppose the boundary is a graph, every inspected context has a reliable bracket of width at most w, and \(|\tau(z)-\tau(z')|\le L\|z-z'\|^\alpha\), with 0<α≤1. If the chosen contexts have fill distance r, nearest-context bracket midpoints satisfy

\[
\|\widehat\tau-\tau\|_\infty\le w/2+Lr^\alpha.
\]

This separates normal resolution from tangent coverage. Binary bisection shrinks an initial bracket W to w in \(\lceil\log_2(W/w)\rceil\) queries per context. A simple d-dimensional context cover therefore has cost of order

\[
\varepsilon^{-d/\alpha}\log(W/\varepsilon)
\]

for ε-level accuracy under these assumptions, compared with adding roughly another ε⁻¹ factor for a uniform normal grid. This is a constructive scaling argument, not an optimality theorem, and noisy signs change it. Smooth-boundary active learning and adaptive line-search reductions already have established theory. [Castro and Nowak][LCastro]; [Locatelli et al.][LLocatelli].

The bound also explains why omitting ST without evidence is dangerous: it changes the domain of the claimed surface. Fixing ST=350 K makes a legitimate lower-dimensional slice; it does not establish the full four-input boundary.

## 6. Three research directions worth a decisive test

### Direction 1 — Physics-coordinate threshold surface on the unseen finite pool

**Problem and model.** Estimate the label-defined graph τ(z), conditional on the configurations actually represented in the new pool, using Section 5's structured probit GP. This is a deliberately restricted challenger to M3. Sparse observations need not locate the continuous graph precisely; prediction and set recovery at held-out pool points are the primary observable tasks.

**Posterior.** A fixed-scale soft-probit model is the practical first challenger, with prior and kernel choices finalized on the old 405 simulations. Hard inequalities are a sensitivity only where their structural assumptions are supported. Benchmark approximate threshold quantiles against a sampled posterior on old-data prefixes before unblinding. Proper prior regularization matters more than adding a new slope GP. No new labels may set its noise scale, kernel or exception rules.

**Acquisition.** Restrict every maximization to the currently unrevealed new training-pool candidates. Use the expected threshold-variance reduction in Section 5, integrated over a fixed label-free context reference distribution defined from the new training-pool features. Its weights must stay fixed as candidates are queried. Compare against probability margin under the **same threshold model**, not just against M3 or Random. Threshold variance at unsupported contexts can be prior-driven; add no rescue heuristic after results.

**Why it could work.** The graph restriction removes a freely varying normal-direction residual and converts binary observations into information about a lower-dimensional threshold. Unlike hard monotonic propagation, every unqueried candidate remains eligible. It may improve inference and query allocation if the unseen pool supplies useful cross-threshold and contextual support.

**Why it could fail.** New points may have the same holes as the old pool, with few opportunities to bracket a threshold. The graph can be wrong because of configurations, exposure or local reversals. M3 may already capture almost everything learnable. A threshold model can win prediction yet have no acquisition advantage; the planned contrasts explicitly allow that outcome.

**Required data.** New input coordinates and configuration metadata are needed for label-free support/feasibility diagnostics; new labels are needed only after the protocol is locked. The already-run pool can test empirical predictive and acquisition generalization. It cannot establish continuous boundary-location error without naturally occurring validated brackets or denser independent truth.

**Minimal decisive experiment.** The single locked four-path external replay in Section 10, after old-data numerical validation. No new simulations or custom sweeps are required. If the feature-only audit shows very poor overlap/support, keep the study as external predictive validation rather than inventing missing queries.

**Cost.** Dense GP algebra is O(n³), and pool/reference scoring is finite. Truncated/soft posterior checks at n≤405 are practical as small-prefix audits, but full MCMC hypothetical refits at every candidate can be expensive. Use an approximation only after acquisition-ranking validation on old data. No simulator runtime is added; computational replay and manual labelling costs must be reported separately.

**Closest work and novelty.** Keeley 2023 is the mandatory model comparator; Li–Ghosal 2017 and probabilistic bisection supply related boundary/inference precedents. **Novelty: LOW for the model; MODERATE only for a rigorous contribution explaining when boundary structure helps finite-pool acquisition and when support limits prevent it.** A fresh external win is scientifically valuable even if it is an application contribution. [Keeley][LKeeley]; [Li and Ghosal][LBoundary]; [Rodriguez and Ludkovski][LBisection].

### Direction 2 — Coherent Bayesian physics-discrepancy random-set estimation

**Problem.** Estimate a possibly non-graph positive set S={x:f(x)>0} under a declared domain measure, preserving the ability to represent local reversals or disconnected regions.

**Model.** Use one joint posterior rather than the two-stage plug-in construction:

\[
f(x)=a+b\ell(x)+r(x),\quad
(a,b)\sim p(a,b),\quad r\sim GP(0,k),\quad
Y\mid f\sim\operatorname{Bernoulli}(\Phi(f/s)).
\]

Fix s to identify the latent scale; give b a proper, physically informed prior, optionally positive if justified. A joint Bayesian mean is not completely new to the project: Phase 1.7 already had Gaussian-prior trend coefficients. The untested combination is adequate ARD flexibility, propagated trend uncertainty, and an explicit latent-set decision objective, with calibrated inference. If decomposition interpretation is needed, a projected residual kernel can remove the intercept/ell span on a **fixed label-free reference measure**, but that projection itself changes the prior and is not necessary merely to predict S.

**Posterior and acquisition.** Probit augmentation/MCMC, or validated variational inference, integrating the trend parameters and enough hyperparameter uncertainty to check decision stability. Compute \(\pi_n(x)=\Pr(f(x)>0\mid D_n)\); use the fixed-domain Bayes set loss Rₙ from Section 3, or a predeclared asymmetric variant. Letham-style closed forms apply only where their Gaussian/probit assumptions are satisfied. Numerical integration of logistic models is an alternative, but not their closed-form algorithm.

**Why it could work.** It attacks two specific untested limitations together: omitted trend uncertainty and the label-versus-latent-set objective mismatch. It can accommodate graph violations without propagation or candidate removal. This is meaningfully different from rerunning the Phase 1.18B p(1−p) functional.

**Why it could fail.** The uncertainty correction may hardly change useful decisions; a larger joint model can be less stable at B16. General set learning gives up some of the dimensional reduction of Direction 1. Most importantly, a better objective still cannot create missing simulator points.

**Required data and minimal experiment.** First use 20 predeclared historical prefixes only to compare π, calibration and uncertainty in boundary location with a sampling reference. A subsequent development-only 2×2 model/objective replay should compare plug-in versus joint inference and margin versus set loss, with the same candidates. Require a consistent, materially different set posterior and stable numerical acquisition rankings before committing the unseen pool to this challenger. Current 405 data can falsify this mechanism, but cannot provide a fresh confirmatory win after extensive reuse. The independently generated, still-unseen new pool supplies the confirmation opportunity; no locations need be chosen.

**Cost.** More expensive inference than M3; binary lookahead requires two outcomes per candidate and reference predictions. Without a validated analytic update, an all-candidate MCMC-refit loop is unattractive. Use sample reweighting with effective-sample-size checks, and refit only when needed; do not label this exact if approximation error remains. For context, existing exact-fixed/refit M3 full trajectories took median 217/469 seconds, but those timings are not forecasts for a joint MCMC implementation. [Phase 1.18B][R18B].

**Closest work and novelty.** Letham 2022, physics-informed GPC work by Hardcastle et al. 2025, and random-set classifier work by Menz et al. are direct precedents. The latter's full publisher text was inaccessible in this review; repository citations are not a substitute for verifying any detailed equivalence claim. **Novelty: LOW as a model/acquisition combination; MODERATE as a rigorous diagnostic and calibrated simulator application.** This is the second-best fallback if the graph fails. [Letham][LLetham]; [Hardcastle et al.][LPhysics].

### Direction 3 — Boundary-local mixed observations with censoring

**Problem.** Estimate the same boundary while extracting extra information from the continuous and temporal output of each paid simulation. The auxiliary target is useful only insofar as it reduces uncertainty about that boundary.

**Model.** Let q=ell−τ(z) be latent severity relative to the boundary. One testable local model is

\[
Y\mid q\sim\operatorname{Bernoulli}(\Phi(q/s_y)),\qquad
\log D^*=g_c(z)+b_c q+\epsilon_c,\quad c=\mathbf1\{q>0\},
\]

with regularized context functions g₀,g₁ and potentially different slopes/variances. A shared boundary can permit a discontinuity in depth without requiring a globally smooth depth map. Its zero is anchored by the binary likelihood; depth has nuisance trends and need not have a universal threshold. Other outputs may share a small number of latent factors only after this one-output version passes.

If a reported depth is right-censored at verified cᵢ, its contribution is

\[
\Pr(D_i^*\ge c_i\mid q_i,z_i)
=1-\Phi\!\left(\frac{\log c_i-g_c(z_i)-b_cq_i}{s_c}\right),
\]

not a Gaussian density evaluated at the cap. A simulator floor can also alter the physical solution, not merely clip a measurement. In that case a Tobit likelihood alone is insufficient: a deeper-domain check or a domain-specific target is required. The empirical 294.18 µm pile separator is a diagnostic threshold, not a verified observation-specific censor limit.

**Posterior and acquisition.** Fit a mixed-likelihood posterior by variational inference or sampled latent variables. Query utility is expected reduction of threshold/set loss given the **joint observation** O=(Y,D,censor flag,…):

\[
a_n(x)=R_n-\mathbb E_{O\mid D_n,x}R_{n+1}.
\]

Do not multiply marginal label and depth likelihoods as independent evidence unless their conditional independence is justified. Both derive from the same evolving geometry; extra dependence may otherwise generate false precision. Acquisition integrates future auxiliary outcomes, never uses unrevealed outputs as candidate features.

**Why it could work.** Close to the transition, a depth value can convey local severity or inequality information even if global depth RMSE is poor. Censored extreme values can be downweighted correctly, and separate regime trends need not smooth through a jump.

**Why it could fail.** Conditional on the observed binary label, depth may convey almost no additional information about the boundary. Label and depth can disagree because they summarize different time intervals. Latent scale/trend confounding, floor dynamics and few local paired observations can dominate. This is a higher-risk option than Directions 1–2.

**Required data and minimal experiment.** The 405 cases suffice for a development-only binary-versus-joint model comparison using identical revealed prefixes, plus an auxiliary-permutation control within regime and context neighbourhoods. Continue only if held-out boundary-relevant log score or location error improves beyond binary-only, with credible coverage preserved; global depth R² is not the gate. Use whatever synchronized raw trajectories, label frames and censor metadata were actually retained in the already-run new pool. No missing output should be invented or presumed recoverable. Active efficiency still requires a locked query-revelation comparison.

**Cost.** Several latent processes and mixed likelihoods increase fit and lookahead cost, often by orders of magnitude relative to closed-form GPR. Sparse variational inference is available but incurs extra approximation checks. Do not budget a large full replay before a small-prefix information-gain check.

**Closest work and novelty.** Mixed likelihood variational GPs (Wu et al. 2025), multi-output censored GPs (Gammelli et al. 2022), and Jump GP models already cover the main components. **Novelty: MODERATE only if a physically justified coupling and a falsifiable account of when auxiliary information helps are established; LOW for merely combining likelihoods.** [Mixed likelihoods][LMixed]; [Censored multi-output GPs][LCensored]; [Jump GP][LJump].

## 7. Continuous outputs and nonstationarity: what deserves attention

### What the depth history really says

Max-Depth, a maximum over the observed trajectory, and a late-active typical depth are different targets. In the Week 7 extraction, maxima precede T0 in 246/350 successful extractions; 22/70 KH cases have no saved KH frame within T0. A model of late depth is therefore not necessarily modelling the event that defined the experiment-level ever-KH label. Historical depth errors were concentrated: five cases contributed 48.2% of squared error and ten contributed 67.8%. Error magnitude correlated with local depth heterogeneity (ρ=0.582) much more than nearest-neighbour distance (ρ=0.047). This motivates checking local regime structure and target timing, not merely collecting globally uniform neighbours. [Week 7 depth diagnostics][RDepth].

Physical **G3** is maximum sustained depth: compute rolling medians of \(\max(0,-z_{\min}(t))\) over 50 µm of scan travel, then take the maximum eligible median in the adaptive interior. Windows require five observations and at least 40 µm actual span; output is in µm, with no LS normalization. It is not the Week 9 arm called G3, which is a standalone ARD GPC. [Physical target extractor][RG3Code].

Observed Max-Depth's worst transfer balanced accuracy was about 0.944; physical G3's was about 0.813. Yet the Phase 6 Max-Depth regressor, despite global R²≈0.921 and RMSE≈21.7 µm, had q20 classification error 0.200 versus Binary's 0.176. Its q20 error-AULC was approximately 0.205 versus 0.186, although the paired difference was unresolved; its global balanced-accuracy AULC was better. These results are endpoint-dependent, not proof that continuous outputs are useless. **A formal direct DA-LSE-versus-M3 benchmark was not located; Week 7 predates M3.** That part of the supplied narrative remains unverified. [Week 7 proxy transfer][RTransfer]; [Phase 6 benchmark][R7].

The relevant information quantity is

\[
I(\tau;D_{\mathrm{new}}\mid Y_{\mathrm{new}},x,D_n),
\]

not the marginal association between depth and Y. A near-perfect observed separator can add almost nothing after Y is known. Conversely, a noisy local depth trend can add information about threshold distance even when its global prediction is poor.

| Proposed use of outputs | Mechanistic assessment |
|---|---|
| Joint binary/continuous latent severity | Best auxiliary candidate if conditional information remains after Y; requires identifiable scale and dependence checks. |
| Regime-conditioned or change-point depth | Useful if matched sweeps reveal an actual jump or distinct slopes. Predicting the regime at an unqueried point remains part of the problem. |
| Multi-output GP / auxiliary tasks | Can borrow shared context structure; flexible output-specific components are needed to avoid forcing every response to define the same boundary. |
| Censored likelihood | Appropriate for a verified observation limit. Does not repair changed physics caused by a shallow simulation domain. |
| Ranking rather than regression | Robust to monotone output transformations, but needs conditional monotonicity. It loses absolute threshold-distance information and can inherit censor ties. |
| Depth-derived inequalities | Defensible only after validating a relation between depth and the regime boundary; the empirical 110 µm separator is not a physical law. |
| Boundary-distance regression | Requires a calibrated distance/severity relation. Calling depth a distance does not create one. |
| Width, height, kinetic energy, temporal geometry | Retain them from every new call, but do not add all to a latent model without a conditional-utility test. Corrected transverse width has weak hard-decision evidence. |

The temporal branch shows why skepticism matters: transverse width dynamics alone have q20 balanced accuracy about 0.505, and h+width hard decisions worsen relative to h. Some probability/ranking and early-prefix effects are useful secondary signals, but no validated early-warning rule exists. Longitudinal ΔX and transverse ΔY must not be conflated. [Corrected temporal report][RTemporal].

If observation-window differences dominate the new-pool audit, a more faithful future object may be **first observed onset distance/time**, with right-censoring when no KH appears by the end. For a latent onset T*(x), observations contribute an event density for observed onset and survival \(\Pr(T^*>T_{\mathrm{end}})\) otherwise. Saved-frame spacing makes onset interval-censored, not exact. A mixture with probability of no onset may be needed. This could exploit partial trajectories, but it changes the estimand to an exposure-defined event boundary; it must be explicitly registered, and binary ever-KH labels must not be multiplied as independent evidence of the same event. It is a contingency within Direction 3, not the current primary recommendation.

### Is an ARD stationary residual wrong?

M3's shorter VX length scale and longer LS/ST scales are compatible with velocity-dependent corrections. They do not prove different physical exponents, a kink, or causality. Frequent bound hits further weaken such interpretation. External log-power/log-velocity exponents differed from the nominal −1/2, but those fits used different labels, fixed LS and penalty-sensitive separators. They are evidence against a universal exact scaling law, not direct evidence for a specific SPH change point. [Phase 1.13][R13]; [External closure diagnostics][RClosure].

| Representation | When justified here | Main risk |
|---|---|---|
| Stationary ARD residual | Baseline while local matched-sweep geometry is unknown | Smears abrupt local changes |
| Smoothly varying threshold τ(z) | Single crossing with smooth contextual shifts | Excludes islands/reversals |
| Warped coordinates or varying exponents | Residual trend has reproducible physical coordinate dependence | Reparameterization may only add flexibility; exponent interpretation can be non-identifiable |
| Local GP / Jump GP | Matched observations show local jumps in continuous output | Few neighbours; unstable local partitions |
| Treed GP | Distinct reproducible regimes separated by a few interpretable splits | Axis-aligned artifacts and poor cross-boundary borrowing |
| Mixture of experts | Several mechanistically different response laws have data support | Gating ambiguity, extra parameters, double use of labels |
| Nonstationary/deep GP | Smoothness varies substantially and simpler models fail held-out local tests | Large modelling burden relative to 73 KH observations |

A power-series boundary can be kinked in z while remaining a perfectly valid graph. Start with the graph and inspect local residuals; do not equate graph modelling with universal smoothness. If needed, compare one stationary τ GP with one prespecified varying-length or local alternative on whole held-out sweeps. Do not select the architecture on pointwise random splits that put neighbouring points from the same sweep in training and test. Park's Jump GP and later active piecewise-GP work already address discontinuities; Booth et al. address nonstationary failure contours with deep GPs. Complexity alone would be engineering, not a new contribution. [Jump GP][LJump]; [Active piecewise GP][LPiecewise]; [Nonstationary contours][LDeep].

## 8. Evaluation aligned with the thesis title

**Keep q20/q30 as historical secondary endpoints.** B1 is the nearest opposite-label distance in population-standardized four-input space:

\[
d_i^{B1}=\min_{j:y_j\ne y_i}\|S_{405}(x_i)-S_{405}(x_j)\|_2.
\]

Within an 81-point held-out fold, the 17 smallest B1 distances form q20 and 25 form q30. A single changed q20 prediction moves fold accuracy by 1/17≈5.88 percentage points. B1 uses the full reference labels to define evaluation membership; that is intentional outcome-dependent evaluation, not hidden-label acquisition. It describes a density- and metric-dependent empirical subset, not a sampled surface with known physical distances. [Frozen evaluation implementation][RB1].

| Metric | What it measures | Suitability |
|---|---|---|
| Held-out q20/q30 accuracy | Classification on empirical opposite-label-near cases | Retain for continuity, qualified physical interpretation |
| Global finite-pool accuracy / BA | Recovery of an archived population | Valid pool endpoint; queried truths in composite scores must be identified |
| Integrated threshold error | \(\int\lvert\hat\tau-\tau\rvert\,d\nu\), or squared error | Best primary physical location loss if a graph is validated |
| Excursion symmetric difference | \(\mu(\hat S\triangle S)\) | Best general-set alternative, requires declared input measure |
| False-safe / false-unsafe volume | Direction-specific errors under µ | Important when missing KH is costlier; define costs before results |
| Hausdorff distance | Worst geometric discrepancy between boundaries | Sensitive to outliers/islands; requires dense truth and physically scaled axes |
| Boundary coverage | How much of the true surface lies near estimates | Useful against missed components; unavailable from sparse labels alone |
| Credible-region width and coverage | Uncertainty sharpness and calibration | Report together; narrow width by itself can reward overconfidence |
| Conservative excursion loss | Errors under a posterior safety requirement | Model-dependent protection, not guaranteed simulator safety |
| Queries to ε quality | First sustained threshold attainment | Most direct sample-efficiency endpoint; retain censoring and non-attainment |

For graph boundaries and a product measure with uniform ell conditional on z over a common interval of width W,

\[
\mu(S_{\hat\tau}\triangle S_\tau)
=\frac1W\int|\hat\tau(z)-\tau(z)|\,d\nu(z),
\]

when both thresholds lie inside the interval. With z-dependent feasible width, replace 1/W by 1/W(z); with general density ρ, the exact loss is \(\int\int_{\min(\tau,\hat\tau)}^{\max(\tau,\hat\tau)}\rho(\ell,z)d\ell dz\). This links boundary-location loss to classical LSE instead of replacing q20 opportunistically.

For a future dataset with sufficiently dense power brackets, **integrated absolute log-power threshold error** would be the main physical endpoint, plus KH-miss volume and credible-band coverage. An error 0.05 in ell at fixed context corresponds to a multiplicative power factor exp(0.05)≈1.051. This is an interpretable tolerance, but 5% is a proposed engineering target, not a supervisor-validated tolerance.

Integrated posterior variance is a rational squared-error acquisition objective, not the observed physical error. If using it while evaluating absolute error, state that mismatch and retain squared error as a prespecified secondary metric; an absolute-loss Bayes-risk acquisition is an alternative to choose **before** confirmation. For a non-graph fallback, use symmetric-difference loss under the same measure. Conservative excursion design has existing formal treatments. [Azzimonti et al.][LConservative].

### Evidence required for a new contribution

Separate two comparisons:

* **Model:** same queried datasets, different predictors. This can establish improved estimation but not acquisition quality.
* **Acquisition:** same model, priors, initial observations, allowable controls and total simulator budget, different query policies. This isolates sample selection.

For a system-level claim against M3, include M3-margin on the same new finite pool as a predeclared comparator alongside the primary same-model policy comparison. A threshold model beating M3-margin could otherwise be entirely a model gain again. The clean final study is a crossed model×policy design when budget permits, not an uncontrolled replacement of every component.

Use an independently held evaluation set/sweep collection, no hidden evaluation output in acquisition, a fixed stopping rule, and predeclared primary contrast. For stochastic policy comparisons, independent randomization blocks are units of algorithmic inference; points along a learning curve are not. Repeated outer splits on the old 405 rows measure split sensitivity, not independent simulator populations. A 95% interval cannot neutralize years of model selection on the same outcomes.

## 9. Corrected design: an independently generated finite pool with unseen labels

### What this opportunity can and cannot establish

The simulations are complete and their locations are fixed. This is now an opportunity for **external, label-blinded finite-pool confirmation**, not continuous experimental design. An independent generation process protects against acquisition-selected locations; it does not guarantee a different distribution, adequate near-boundary density, identical configurations, or independent simulator physics.

The unseen labels are more valuable than another retrospective tuning cycle on the old 405 rows. Freeze all scientific choices before the supervisor's labels enter model development. The supervisor can finish labelling normally; there is no requirement to interrupt that work. Labels can arrive together into a separate oracle file and still support a blinded replay, provided neither development nor selection inspects them. This memo neither sends a message nor changes the supervisor's workflow.

Three cost regimes must be distinguished:

| Regime | Information available before a query | Permissible efficiency claim |
|---|---|---|
| Simulator-information replay — **primary** | Process inputs and permitted configuration metadata; historical development knowledge | Fewer revealed simulator records in an external offline replay; hypothetical prospective simulator saving, not realized cost saving |
| Active manual annotation | All existing simulator outputs are free, only manual KH label is costly | Reduced manual annotation burden if labelling can actually stop or be directed; not reduced simulation count |
| Full-batch external validation | All new labels are revealed after the protocol lock | Generalization of predictive models; no realized sequential saving |

For the primary replay, querying index i reveals its manual label and any permitted physical outputs together. Withholding already-computed outputs is an experimental information constraint that mimics a simulator call. If depth, geometry or video-derived features are freely available for every candidate, say explicitly that the task is manual annotation instead. If the supervisor labels everything anyway, even manual-label savings are counterfactual replay results.

### Immediate label-free audit

Request/access the following **existing** materials; do not request new locations or runs:

* An immutable simulation-ID list, P, VX, LS, ST with units and exact parameter conventions; dataset-generation date/design description and the relation to the old population.
* Material, domain/mesh/particle resolution, initial state, XI/XF/XL/TE/DT, termination reason and observation/recording-window metadata.
* A manifest of available physical/temporal outputs, their definitions and censoring/boundary-contact flags. For simulator-information replay, keep their values out of candidate selection until queried.
* Manual `has_keyhole` labels and any ambiguous-frame notes in a separately held label file, joined by exact ID only. Freeze the labelling definition; do not silently turn a depth threshold into ground truth.

If labels have already arrived by the time the workflow is set up, record whether anyone developing the method inspected them. A file being new is not proof of blinding. If inspected, call the analysis external validation or development as appropriate, and reserve a genuinely untouched partition before further decisions where possible.

Without labels, compare old/new input distributions, exact duplicate IDs and duplicate process-plus-configuration settings, configuration proportions, h coverage, distance to old support, ST ranges and feasible-context coverage. Use old-data-only M3 predictions and h-band annotations for diagnostics; they are permitted because the new labels are absent. Do not use predicted KH counts as if they were ground truth.

Specifically compute: number of new points in the historical h-overlap band; distribution of distances to old near-boundary observations; number and separation of nearly matched context neighbours on opposite sides of the **old model's** threshold; size of partial-order antichains; and the number of old-model-uncertain candidates. A “bracket” based on predicted classes is only a predicted bracket. Report support deficiencies rather than changing candidate coordinates.

If observation windows or configurations differ, define whether the new target is still comparable manual ever-observed KH. Preserve every label. An unseen pool with a different exposure tests transfer of an operational label, not a universal material phase boundary. Metadata restriction/grouping rules must be specified before labels; no outcome-driven removal of inconvenient configurations.

### Freeze two different scientific questions

**External prediction:** train the locked H, M3 and threshold models on the old population only, then evaluate the new pool once after unblinding. This tests transfer/generalization of the previously developed predictor. No new label is used for fitting this comparison. Report accuracy, balanced accuracy, KH recall, Brier/log loss and the predeclared empirical boundary subset. If target definitions differ, qualify the comparison accordingly.

**External acquisition — primary methodological question:** run a cold-start *within-new-pool* replay, conditional on the architecture/prior choices developed from the old data. Only revealed new labels enter fitting. Old labels do not enter its likelihood or query scores. This matches the logic of the old acquisition benchmark and avoids calling a model pretrained on 405 labels a 16-label method. Old data remain development data; this is not an assertion that the algorithm was designed without them.

A warm-transfer/adaptation replay with all 405 old labels available is a different and useful secondary task. It must count *additional* new labels and retain the historical training cost in its description. Do not mix its learning curve with the cold-start curve or choose between them after seeing which wins.

### Fixed partitions and budgets, with unknown new-pool size

The new pool size N is not yet established in this review, so no number of runs or statistical power is invented. Use exact duplicate/process-configuration groups as indivisible units. Pre-generate repeat seeds and label-independent group partitions; do not reject or redraw splits using hidden new labels.

Prefer the historical 20 repeat blocks with five folds when the new pool is large enough to give approximately 85 or more evaluation rows per fold. If N is smaller, choose the largest K in {2,3,4,5} for which each feature-only fold is expected to have at least 85 rows. Group-size constraints override exact equality. If even two folds are too small, retain q20 but classify the inferential result as a small external benchmark; do not rescue power by treating folds or budgets as independent experiments. This rule is fixed before labels, and its final K is recorded before unblinding.

For each outer run, reserve its evaluation fold from all model fitting and acquisition. Choose the same feature-only maximin 16-point initial design for every policy. If it contains one class, continue the same predetermined feature-only sequence across all arms until two classes appear, charging every query. During that common startup, use the same proper smoothed-prevalence prediction for evaluation. This prevents hidden-label rejection sampling and makes M3's two-class fit requirement explicit. Such startup extensions and their budgets must be reported; they cannot be silently dropped. Startup is capped at the frozen H: if no second class appears by H, retain the common fallback throughout, report no policy divergence, and neither extend H nor discard the run.

Use the historical horizon 80 when every training pool has at least 100 queryable rows. Otherwise set the common horizon H to the smaller of 80 and floor(0.8 times the smallest training-pool size), before labels, retaining at least 20% of each pool as unrevealed at the primary horizon. If H≤16, the proposed acquisition study is infeasible. These are feasibility rules, not evidence that H=80 will retain boundary opportunities. Report early/mid/late results and the empirical depletion curve as prespecified secondary diagnostics.

The primary metric remains **Fold-B1-q20 accuracy AULC**, normalized over the registered budget interval. Recreate the historical evaluation definition on the new population, with B1/q flags computed inside an isolated evaluator only after the policies and protocol are frozen. Those fields never enter model fitting, acquisition, partition selection or hyperparameter choice. q30, balanced accuracy, KH recall, calibration and full-held-out accuracy are secondary. q20 stays primary even if a different metric looks better. If a fold has too few or no KH cases, report the resulting uncertainty/undefined class-specific metric rather than pretending its class balance is adequate.

This B1 definition uses new labels to define an evaluation target; that is permissible in an isolated evaluator. It does not turn sparse opposite-label distances into a physical surface-distance ground truth. Also report an old-model-defined, label-free near-boundary subset as a secondary transfer diagnostic to show whether conclusions depend on the outcome-dependent B1 definition.

### One challenger, four query paths, explicit effect separation

After numerical validation on old data, freeze four paths:

| Path | Query policy | Role |
|---|---|---|
| A | Canonical M3 margin | Incumbent |
| B | Threshold-model probability margin | Same-model acquisition control |
| C | Threshold-model expected integrated threshold-variance reduction, restricted to pool | Single new acquisition challenger |
| D | Feature-independent matched Random continuation | Sampling baseline; fixed continuation seeds |

Fit/evaluate M3 and the threshold model on identical revealed prefixes where needed for the following registered contrasts. The **single primary acquisition contrast is threshold model on C minus threshold model on B**. This asks whether boundary-directed selection helps beyond its own probability margin. A threshold model on C beating M3 on A is a system comparison, not an isolated acquisition effect.

The key secondary model contrast is threshold versus M3 on path A. The secondary system contrast is threshold/C versus M3/A. Random comparisons quantify acquisition versus nonadaptive selection; they do not replace the more demanding primary B-versus-C control. Report all registered contrasts and adjust the secondary confirmatory family if inferential claims are made. Do not add a fifth tuned policy after seeing new labels.

For the variance criterion, define a fixed reference measure from **outer-training input contexts**, for example equal weights over those contexts, before any new labels. Keep queried contexts in that reference measure. Maximize only over currently unqueried candidates; do not remove candidates via provisional labels. Thus integration geometry stays fixed while the query set shrinks. The absence of ideal threshold-crossing candidates is a measured limitation, not a prompt to generate points that do not exist.

### Claims and stopping rules

Primary success: C−B q20 accuracy-AULC has a paired repeat-block 95% interval with lower bound above zero **and** a point estimate at least +0.01 (one percentage point). The effect threshold is a proposed minimum practical improvement, to be frozen before unblinding. Require that the secondary q20 KH-recall AULC contrast does not show a material deterioration: use a predeclared −0.02 non-inferiority margin and disclose the interval. If that safety/utility check is inconclusive or unestimable because of absent KH evaluation cases, qualify rather than promote the result. Do not drop such folds to manufacture a passing guard.

Model-only success is reported separately if the same-path threshold predictor improves but C−B does not. A primary interval crossing zero is unresolved, not equivalence. An upper bound below zero is evidence of harm. An upper bound below +0.01 can rule out the proposed practically meaningful gain under this benchmark even when tiny benefits remain possible. No secondary endpoint overturns a failed primary result.

For a query-saving secondary endpoint, retain historical thresholds such as q20 accuracy 0.80/0.82/0.84, with sustained attainment over three checkpoints, paired starts and explicit censoring. Report attainment fractions and restricted burden; do not average successful crossings alone. If the new distribution makes those thresholds unreachable or trivial, retain that finding rather than retune the target after unblinding.

Bootstrap repeat blocks while retaining their folds and Random continuations together. Interpret intervals as split/policy-randomness uncertainty **conditional on this new population**. The new independent generation strengthens external evidence; it is still one new pool, not 20 independent simulator campaigns. Report each pool separately before any pooled summary.

### What the frozen new pool enables instead of the earlier simulation request

It enables an unusually clean separation of (i) external prediction, (ii) external acquisition, (iii) model versus path effects, and (iv) performance before/after pool uncertainty collapses. It may contain enough new support to falsify the old saturation explanation. It cannot guarantee a gain, supply arbitrary normal probes, establish Hausdorff error, or recover the simulator cost already spent.

The useful request to the supervisor/data owner is therefore **metadata, exact ID alignment, label isolation and any already-retained outputs**, not 320 additional simulations or custom settings. If labelling is already underway, preserve the full resulting labels behind the oracle; no change to where or how the simulations were run is required.

## 10. Minimal next experiment: one locked external finite-pool confirmation

**Question:** does a directly represented threshold model produce useful, externally reproducible query choices, beyond its own margin policy, on the independently generated unseen pool?

**Before labels:** complete numerical and posterior checks on the old data; freeze the four paths, single primary contrast, partitions/budget rules, target definition, priors, reference weights, seeds and one-class startup handling. Audit new inputs/metadata only. The information boundary matters more than whether labels physically arrive in one file or sequentially.

**After labels are available to the oracle:** run the four registered paths without developer access to hidden outputs and without interim method changes. Keep test labels in a separate evaluator. Finish the registered runs, then unblind their results together. No new acquisitions are invented from the evaluation outcomes.

**Success/failure criterion:** C−B has lower 95% bound >0 and mean q20 AULC gain ≥0.01, with the registered KH-recall guard satisfied. Otherwise, do not claim a new acquisition gain. Report model-only success, unresolved acquisition, practical futility or harm according to the intervals. The small-data feasibility rules in Section 9 can make the study underpowered; underpower is not a reason to select a new endpoint.

**Diagnostic interpretation:** if the new pool has materially denser old-model transition coverage yet acquisition still fails before depletion, weaken finite-pool depletion as the dominant explanation. If candidate uncertainty collapses at a similar effective number of queried band points and later policy paths converge, strengthen the saturation interpretation. These comparisons are predeclared associations; independently generated pools do not randomize boundary density, configuration or observation exposure, so they are not a causal experiment isolating depletion.

**Practical limit:** the models have not been implemented or validated for this proposed challenger during this memo. If that cannot be completed before anyone inspects new labels, escrow the labels and complete it on old data first. If blinding has already been lost, do not label a retroactively written protocol preregistered. The user correction establishes that labels are presently unseen; access and withholding details remain to be verified.

## 11. Literature and novelty decision

The search covered threshold/implicit-boundary GPs, inequality/ordinal inference, Bernoulli LSE, excursion/failure sets, monotonicity, continuous query design, noisy and multi-output LSE, censored GPs, phase diagrams and additive manufacturing. Primary sources were preferred; older work was retained where it directly limits novelty. The most consequential findings were cross-checked against original equations or primary publication records.

| Nearest prior work | What is already established | What could remain for this thesis |
|---|---|---|
| Keeley et al., AAAI 2023 | Contextual GP threshold/intercept and slope with binary observations and threshold acquisition | SPH-specific structural validation, feasible-cost design and robust resolution claims; not the basic model |
| Li & Ghosal 2017; BayesBD | Direct GP boundary priors and uncertainty from inside/outside observations | Different graph geometry and active simulator protocol |
| Chu & Ghahramani 2005; Benavoli et al. 2020/21; Takeno et al. 2023 | GP threshold/inequality likelihoods, skew posteriors and approximation issues | Inference validation for this particular threshold graph, not new inequality inference |
| Rodriguez & Ludkovski 2020; Castro–Nowak; Locatelli et al. | Noisy root search and active smooth-boundary estimation | Feasible contextual simulator bracketing with tested failure modes |
| Gotovos et al. 2013; Bect et al. 2012 | GP-LSE confidence designs and Bayesian excursion/failure SUR | A new physical target/observation design, not generic straddle or SUR |
| Shekhar & Javidi 2019; Mason et al. 2022 | Multiscale LSE and structured sample-complexity theory | Carefully proved assumptions linking graph brackets, coverage and simulator loss |
| Zhao et al. 2021; Letham et al. 2022 | GPC error reduction, query synthesis, posterior Bernoulli-LSE lookahead | Mechanistic diagnosis of why a different predictive-probability SUR failed |
| Hardcastle et al. 2025 | Physics-informed classifier priors for material feasibility and active phase refinement | The audited M3 application and its model/acquisition decomposition |
| Masinelli et al. 2025 | Active GPC-based conduction/keyhole process-map generation with power-level speed sweeps | Different manual simulator target, four controls, direct boundary resolution and prospective accounting |
| Zhu et al. 2024; Fan et al. BALPI 2026 | GP active phase-diagram discovery; complementary classifier and fraction-LSE approaches | No broad “first GP active phase-boundary method” claim |
| Wu et al. 2025; Gammelli et al. 2022 | Mixed likelihoods and multi-output censored GP inference | A validated local physical coupling and evidence of conditional auxiliary utility |
| Park 2022; Park et al. 2026; Booth et al. 2025 | Jump/piecewise/nonstationary surrogate and contour learning | Evidence that the SPH boundary requires such structure and that it improves query efficiency |

Links: [Keeley][LKeeley], [Li–Ghosal][LBoundary], [BayesBD][LBayesBD], [ordinal GPs][LOrdinal], [skew GPs][LSkew], [Takeno][LTakeno], [bisection][LBisection], [Castro–Nowak][LCastro], [Locatelli][LLocatelli], [Gotovos][LGotovos], [Bect][LBect], [Shekhar][LShekhar], [Mason][LMason], [Zhao][LZhao], [Letham][LLetham], [Hardcastle][LPhysics], [Masinelli][LAM], [Zhu][LPhase], [BALPI][LBALPI], [mixed likelihoods][LMixed], [censoring][LCensored], [Jump GP][LJump], [piecewise AL][LPiecewise], [deep-GP contours][LDeep].

Additional relevant comparisons are soft monotonicity via virtual derivative observations, noisy-LSE observation-model robustness, safe multi-output design and manufacturing process-window estimation. They reinforce the conclusion that model structure, observation type, loss and allowable query set must be specified together. [Riihimäki and Vehtari][LMonotone]; [Lyu et al.][LNoisy]; [Li et al.][LMulti]; [Karandikar et al.][LProcess].

Two qualifications prevent overstating the recent literature. Masinelli's iterative study uses measured grids and power-level speed sweeps, not verified arbitrary joint four-control continuous SPH queries; its labels differ from manual ever-observed KH. BALPI combines two complementary formulations, not necessarily one jointly coupled binary/continuous latent model. Their relevance is substantial without pretending they solved this exact experiment.

The search stopped after the closest model-equivalence threat and the principal design/observation precedents were established, and further broad hits mostly repeated these families. This is a substantial targeted research review, not proof of absence of every possible prior paper. A future methodological novelty claim needs a precise theorem or algorithm first, followed by a renewed comparison against these nearest works. No defensible priority claim can be made for “GP on the boundary,” “continuous GP active learning,” or “mixed binary/depth likelihood” alone.

## 12. Final decision A–J

**A. Diagnosis.** The strongest actionable problem is limited boundary support in a static pool, compounded by a mismatch between predictive-label uncertainty and the set being estimated. Late opportunity collapse is measured in the old pool; early overconfidence, observation exposure and model structure remain competing explanations. The unseen new pool can test external reproducibility but does not automatically remove any of those limitations.

**B. Strongest established contribution.** Binary margin's qualified offline near-boundary advantage over matched Random, M3's supported same-path predictive improvement, and the controlled separation of model gains from query gains. Preserve the negative acquisition results as scientific evidence.

**C. One primary recommendation.** A **locked external finite-pool test of a physics-coordinate threshold-surface challenger**, with M3 retained as incumbent and threshold-variance selection versus threshold-margin as the single primary acquisition contrast. Develop and validate the challenger only on old data; use the new labels once for confirmation.

**D. One fallback.** **Coherent Bayesian physics-discrepancy random-set estimation on the finite pool**, with integrated trend uncertainty and fixed-reference latent-set loss, if old-data structural tests make the graph assumption untenable. Choose this fallback before unblinding, not after seeing which challenger wins on the new pool. If the new acquisition fails, the defensible thesis pivot is the established predictive contribution plus an external diagnosis of finite-pool acquisition saturation.

**E. Stop spending time on:** broad repulsion searches; correction-margin mixtures without independent information; rejected PA-TVR; unvalidated fast updates; hard monotonic candidate removal; proxy-based relabelling; assuming an observed depth separator supplies a useful acquisition; unrestricted new architecture searches on the old q20 benchmark; and continuous-query or custom-sweep proposals for simulations whose locations are already fixed.

**F. New-data request.** Request/access the **already-run pool's exact input/ID/configuration manifest, available-output inventory and separately held manual-label file**. Ask that labels remain unavailable to development until the protocol is locked. Do not request additional runs or altered locations. Allow the supervisor to finish labelling; use an isolated oracle for replay.

**G. Minimal next experiment.** The single locked four-path external replay in Section 10. Primary success requires threshold-variance versus threshold-margin q20 AULC mean gain ≥0.01 and lower paired 95% bound >0, plus the registered KH-recall guard. Failure to meet it does not invalidate a separately supported model gain.

**H. Potential thesis claim if successful.** “On an independently generated SPH simulation pool whose labels were withheld during method development, the registered boundary-directed policy improved empirical near-boundary accuracy AULC over probability margin under the same threshold model and matched revealed-record budgets. This is an external offline sample-efficiency result, conditional on the pool, protocol and evaluated budgets; it does not establish realized simulator-cost savings or continuous boundary-location accuracy.”

**I. Potential paper contribution.** A paper could explain when structured boundary posteriors change the value of finite-pool labels, and when support/depletion makes improved prediction fail to yield improved acquisition, using old/new independent pools and controlled model/path comparisons. That is more interesting than another one-pool heuristic win. The basic threshold GP, inequality inference and variance-reduction principle already exist; a strong methodological claim still needs a new, valid resolution/robustness result or a general mechanism with broader tests.

**J. Confidence, explicitly subjective.** For the revised finite-pool direction: technically feasible **90%**; likely to improve boundary-relevant prediction over M3 **45%**; likely to improve active sample efficiency over its own margin control **30%**; likely to support a methodological contribution beyond application/engineering **20%**. Plausible ranges are 80–95%, 25–60%, 15–45%, and 10–35%. These are planning judgments, not fitted probabilities. New-pool size, support, configuration compatibility and successful preservation of blinding could move them substantially. They are lower than for an ideal controllable continuous design because the new locations cannot be optimized.

## Scope and interpretation limits

This is a research strategy memo, not a newly executed experiment or a completed preregistration. New-pool files, count, feature ranges and output availability were not inspected because their locations were not supplied. The proposed challenger has not been fitted here. No model or acquisition was selected using new labels. The user correction supersedes all assumptions about controllable new simulations; the recommended next study uses only the fixed unseen pool. The mathematical continuous-domain discussion remains solely to clarify what finite-pool data cannot identify.

## Source register

Repository links below are pinned to the audited latest research commit, except the explicitly separate temporal branch. The primary-literature links identify the source publication or author manuscript. All were researched for this memo on 5 September 2026; the Menz publisher full text and current Hugging Face dataset page were inaccessible. The report's derivations, proposed designs, run allocations, gates and confidence estimates are original analysis here, not claims of previously measured results.

[R85]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week8_5_frozen_confirmation/final_results_narrative.md
[R7]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week7_06_real_data_boundary_active_level_set/results_summary.md
[R13]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_13_fixed_physics_ard_discrepancy/FINAL_PHASE1_13_REPORT.md
[R14]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_14_m3_margin_acquisition/FINAL_PHASE1_14_REPORT.md
[R15]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_15a_physics_residual_signal_audit/FINAL_PHASE1_15A_REPORT.md
[R16]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_16_m3_repulsion_scale_audit/FINAL_PHASE1_16_REPORT.md
[R17]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_17a_physics_contour_geometry_audit/FINAL_PHASE1_17A_REPORT.md
[R18A]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_18a_level_set_acquisition_compatibility_audit/FINAL_PHASE1_18A_REPORT.md
[R18B0]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_18b0_fast_gpc_sur_update_validation/FINAL_PHASE1_18B0_REPORT.md
[R18B]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark/FINAL_PHASE1_18B_REPORT.md
[R19A]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_19a_integrity_posterior_monotonicity_audit/FINAL_PHASE1_19A_REPORT.md
[R19B]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_19b_prospective_robust_monotone_pool_lse/FINAL_PHASE1_19B_REPORT.md
[RLetham]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_19a_integrity_posterior_monotonicity_audit/letham_2022_applicability_memo.md
[RSemantics]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_18a_level_set_acquisition_compatibility_audit/m3_posterior_semantics.md
[RStates]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_18a_level_set_acquisition_compatibility_audit/candidate_scores_pre_reveal.csv.gz
[RConfigTable]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_19a_integrity_posterior_monotonicity_audit/simulation_configuration_table.csv
[RDepth]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week7_04_new_data_feature_effects_depth_diagnostics/results_summary.md
[RTransfer]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week7_05_5_g3_robustness_transfer_analysis/results_summary.md
[RG3Code]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/src/week7_phase2_sph_v2_physical_target_extraction.py
[RTemporal]: https://github.com/iso0/active-level-set-week1-warmup/blob/da913797d14b171bec55d3708f96aa87f09a4f94/outputs/week9_phase2_temporal_width_dynamics/FINAL_PHASE2_REPORT.md
[RClosure]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/outputs/week9_phase1_10_closure_diagnostics/FINAL_PHASE1_10_CLOSURE_REPORT.md
[RB1]: https://github.com/iso0/active-level-set-week1-warmup/blob/bf4782881bc27fe1ec5256dc3ba0516478a1ed13/src/week8_5_frozen_sample_efficiency_confirmation.py
[LKeeley]: https://ojs.aaai.org/index.php/AAAI/article/view/25074
[LLetham]: https://proceedings.mlr.press/v151/letham22a.html
[LBoundary]: https://arxiv.org/abs/1508.05847
[LBayesBD]: https://journal.r-project.org/articles/RJ-2017-052/
[LBisection]: https://arxiv.org/abs/1807.00095
[LSkew]: https://arxiv.org/abs/2008.06677
[LTakeno]: https://proceedings.mlr.press/v202/takeno23b.html
[LOrdinal]: https://www.jmlr.org/beta/papers/v6/chu05a.html
[LMonotone]: https://proceedings.mlr.press/v9/riihimaki10a.html
[LZhao]: https://proceedings.neurips.cc/paper_files/paper/2021/file/50d2e70cdf7dd05be85e1b8df3f8ced4-Paper.pdf
[LShekhar]: https://proceedings.mlr.press/v89/shekhar19a.html
[LMason]: https://proceedings.mlr.press/v151/mason22a.html
[LBect]: https://doi.org/10.1007/s11222-011-9241-4
[LGotovos]: https://proceedings.mlr.press/v28/gotovos13.html
[LConservative]: https://arxiv.org/abs/1611.07256
[LCastro]: https://doi.org/10.1109/TIT.2008.920189
[LLocatelli]: https://arxiv.org/abs/1711.09294
[LPhysics]: https://pubs.rsc.org/en/content/articlehtml/2025/dd/d5dd00084j
[LMixed]: https://arxiv.org/abs/2503.04138
[LCensored]: https://orbit.dtu.dk/en/publications/generalized-multi-output-gaussian-process-censored-regression/
[LJump]: https://www.jmlr.org/papers/v23/21-1472.html
[LPiecewise]: https://doi.org/10.1080/00401706.2025.2561746
[LDeep]: https://doi.org/10.1214/24-AOAS1951
[LAM]: https://doi.org/10.1016/j.addma.2025.104677
[LPhase]: https://arxiv.org/abs/2409.07042
[LBALPI]: https://pubs.rsc.org/en/content/articlelanding/2026/dd/d5dd00459d
[LNoisy]: https://doi.org/10.1007/s11222-021-10014-w
[LMulti]: https://proceedings.mlr.press/v151/li22d.html
[LProcess]: https://doi.org/10.1016/j.mfglet.2022.09.001
