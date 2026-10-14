**ASTRA joint model V2 — learn how much depth should be shared with classification**

13 October 2026 · independent controlled development  
Repository evidence: e2bcf97a55736cdd2933b6761678d8b695358205. V1 is preserved byte-for-byte.

**Independent judgment.** The strongest implementable revision is a **mixture over depth–label coupling that preserves the marginal classifier prior**, with expectation propagation (EP) inside each component. It can withdraw an inappropriate depth bridge without changing the binary model's prior capacity. The experiments support that mechanism, not general superiority: V2 avoids a strongly harmful bridge, loses some benefit when depth is informative, and **does not solve rare-negative generalization**. Its paired acquisition is implemented and checked, but wins BA-AULC in only 2 of 9 small sequential comparisons. Complete Opus's frozen V1 Stage M first; then test V2 as a separate matched-path model experiment. Do not replace V1's priors midway or launch real-data Stage A/C4 from these results.

The primary choice, generators, seeds, controls and budgets were frozen in [SELECTION_RECORD_V2.json][selection] before comparative runs. The original 290 comparative fit requests are retained. A separate, prospectively recorded [diagnostic amendment][amendment] investigated the original V1 sparse-negative case, leakage and fallback behavior. Total work was **307 controlled fit requests, 580 component solves**, within both 600 ceilings, plus separately counted quadrature references and four sampling chains. No SPH models, simulator jobs or temporal repairs were run.

**Updated evidence and ownership.** C3 is **spent**. Its locked NEW ACTIVE−G3 BA-AULC was +0.00714 [−0.03649,+0.05287], failing the +0.02 and positive-lower-bound criterion. ACTIVE−WHOLE was +0.044, with interval [+0.023,+0.067]. NEW ACTIVE−G3 q20 (+0.0693), AUC (+0.0954), Brier (−0.0237) and short-K sensitivity (+0.2789) favor ACTIVE, but specificity is −0.0182 [−0.0964,+0.0612]. OLD q20 is worse than G3: −0.0252 [−0.0408,−0.0035]. These are split-confirmation results on already inspected simulations, not fresh external data. Earlier “reserved” paragraphs in the evolving report are superseded by its C3 execution section and decision file. [C3 freeze][c3freeze], [decision][c3decision], [contrasts][c3contrasts]

Track 1 extension found a real reversed-slope failure in WHOLE's threshold rule; correcting its sign improved sensitivity but reduced specificity, leaving approximately +0.002 BA-AULC. Avoiding that trap therefore does not explain the whole target advantage or guarantee a useful classifier. Better AUC measures ranking; better Brier measures a proper probability score that combines several aspects of prediction. Their improvement without BA superiority does **not** isolate miscalibration as the sole remaining problem. The report's “no depth-based model separates” language about similar trajectories also does not imply impossibility for all four-input predictors. [Development report][development], [guard implementation][guard], [engine][engine]

Opus owns V1 Stage M on NEW/OLD/POOLED, mechanisms in that real benchmark, and temporal-model repair. This package neither reads his unfinished results for selection nor changes his checkout. Canonical Y remains any observed manually labelled Keyhole frame; P, VX, LS radius and ST remain the four deployment inputs. Preserve NEW-136, the 49 exclusions, ACTIVE's existing observation window and q20.

**Failure analysis before repair.**

| Quantity or distinction | What it controls; what it cannot establish |
|---|---|
| Global θ location / uncertainty | Moves the overall response–label relation. Many positive labels constrain a shared shift; one local negative may require moving many other cases. A proper prior prevents an undefined root but does not make the resulting decision useful. |
| Probit softness τ | Sets how severely a disagreeing label penalizes h and separates latent probability uncertainty from working-label variability. Changing τ changes the statistical model, not only numerical stability. |
| Response residual σz | Controls how strongly measured depth pins f. Small σz can make an incorrect bridge difficult to escape. It is neither known measurement noise nor a substitute for τ. |
| Discrepancy scale / length | Determines the cost and spatial extent of a departure from the bridge. A weak, smooth discrepancy may force a rare negative to follow depth; an unrestricted discrepancy can discard useful depth and lose identifiability. |
| Approximation versus posterior | A wrong class can be the correct implication of an unfavorable prior/likelihood. More accurate inference need not move its probability toward the observed label. |
| Probability versus BA decision | A calibrated class probability and the BA-optimal decision need not share cutoff 0.5. This does not make every BA loss a cutoff problem. |
| Paid composition versus population | Adaptively selected cases are not an unbiased prevalence sample. A one-negative paid prefix does not identify the population's negative frequency or its spatial extent. |
| Working likelihood versus physics | A Bernoulli likelihood expresses uncertainty about recorded labels. It does not prove fluctuating physical outcomes, annotation error, or that a credible minority observation is noise. |

The fixed units, proper θ prior, fixed link scale, absence of another free intercept and fixed-pool discrepancy centering are useful regularization. V1's coefficient of f fixed at one is additionally a strong sharing assumption. Simply enlarging discrepancy variance would change classifier capacity while also weakening that assumption. V2 separates these effects.

The later diagnostic makes the approximation distinction concrete. In **the original V1 one-negative case**, its Laplace probability is 0.67383; fixed-bridge EP gives 0.72110; independent elliptical-slice sampling gives **0.73237**, with batch Monte Carlo SE 0.00409 and maximum conventional split R-hat 1.0031. The target is the fixed V1 posterior; these are not population confidence intervals. Its unfavorable decision survives more accurate inference. V2 reduces the probability to **0.50831**, still on the wrong side of 0.5. No prior was changed after this result. [Supplemental diagnostics][supplement]

**Selected model and new assumptions.** For a fixed feature-only training candidate pool Q, let

$$
f,g\stackrel{\mathrm{ind}}{\sim}GP(0,k_f),\quad
\delta\sim GP(0,k_\delta^c),\quad
\theta\sim N(0,s_\theta^2),\quad
\rho\sim\operatorname{Categorical}\{(0,\tfrac13),(\tfrac12,\tfrac13),(1,\tfrac13)\},
$$
$$
h(x)=\rho f(x)+\sqrt{1-\rho^2}\,g(x)-\theta+\delta(x),
\qquad z_i=\log(A_i/111\,\mu\mathrm m),
$$
$$
z_i\mid f_i\sim N(f_i,\sigma_z^2),\qquad
Y_i\mid h_i\sim\operatorname{Bernoulli}\{\Phi(h_i/\tau)\}.
$$

The residual GP g is an independent statistical component, **not another observed physical output**. Conditional independence of the two likelihood channels is still assumed. Missing response removes its Gaussian factor only; its label and query cost remain. Ignoring the missingness mechanism is an assumption, especially if observation coverage and recorded morphology share unmodelled causes.

The core identity is

$$
\operatorname{Cov}(h,h\mid\rho)
=K_f+K_\delta^c+s_\theta^2\mathbf1\mathbf1^T
\quad\text{for every }\rho,\qquad
\operatorname{Cov}(f,h\mid\rho)=\rho K_f.
$$

Thus ρ controls **sharing**, not the marginal classifier covariance. It is not the total f–h correlation coefficient, since θ and δ also contribute variance. At ρ=1 the model reduces to V1; at ρ=0, depth and labels are independent under the model. Removing the continuous likelihood leaves the same binary GP for every ρ, so posterior masses remain their prior values. This is the capacity-matched Binary V2 control. It receives no depth-trained scales, kernels or component weights.

The discrete prior is a bounded integration rule over three declared models, not a grid from which the best held-out score is selected. It does not integrate every possible coupling or other hyperparameter. Global nonnegative sharing is a restriction: a locally contradictory region can coexist with useful depth elsewhere, and a negative global relation is handled by withdrawing depth rather than learning an inverse physical law.

Use the V1 fixed priors: f SD 0.60, δ SD 0.35, θ SD 0.35, σz 0.03 and τ 0.15. Matérn-3/2 lengthscale is 0.5 in the original one-dimensional fixtures and 1.5 in each generated four-dimensional coordinate. Real deployment uses lengthscale vector (1.5,1.5,1.5,1.5) on frozen standardized log(P,VX,LS,ST), as specified in the original V1 handoff. No test outcomes fit that transform.

Center δ on Q exactly as in V1. The fixed zero process means and proper priors remove unconstrained parameter drifts, but do **not** identify θ, g and δ separately from sparse labels. In particular, g can have a nonzero average on Q and trade off with θ; its prior mean zero is not a hard centering constraint. Once ρ<1, θ is best called a global label offset. It is a depth threshold only in the restrictive ρ=1, δ=0 limit. One or two negatives cannot identify a physical threshold, kernel scales, softness and coupling simultaneously.

**Posterior computation and paid information flow.** Condition f exactly on available paid z, obtaining $(m_f^z,C_f^z)$. For each ρ,

$$
m_\rho=\rho m_f^z-\theta_0\mathbf1,\qquad
K_\rho=\rho^2C_f^z+(1-\rho^2)K_f+K_\delta^c+s_\theta^2\mathbf1\mathbf1^T.
$$

Paid labels multiply this Gaussian prior by $\prod_i\Phi(s_i h_i/\tau)$, with $s_i=2Y_i-1$. EP replaces each factor by a Gaussian site and matches the exact first two moments of its one-dimensional tilted distribution. For cavity $N(m_i,v_i)$, with $t_i=s_i m_i/\sqrt{\tau^2+v_i}$ and $\lambda(t)=\phi(t)/\Phi(t)$,

$$
Z_i=\Phi(t_i),\quad
\widehat m_i=m_i+\frac{s_i v_i}{\sqrt{\tau^2+v_i}}\lambda(t_i),\quad
\widehat v_i=v_i-\frac{v_i^2}{\tau^2+v_i}\lambda(t_i)\{\lambda(t_i)+t_i\}.
$$

Update site precision and natural mean toward $\widehat v_i^{-1}-v_i^{-1}$ and $\widehat m_i/\widehat v_i-m_i/v_i$, using damping 0.5. Stop after three consecutive relative site changes below 1e-8, with at most 200 iterations. Nonpositive cavity/tilted variances, nonfinite quantities or failure to converge trigger a **whole-mixture Laplace fallback**, never deletion of an unfavorable component. Its fixed stationarity criterion is 2e-6; failure there stops the trajectory. Zero/one-class paid data use this same policy without reseeding or extending startup. No real experiment or main controlled fit needed fallback; an induced failure verified the policy.

For each component, EP yields Gaussian paid-latent moments $(\mu_\rho,\Sigma_\rho)$ and an approximate label evidence $\widetilde Z_\rho$. Gaussian conditional identities propagate them to any jointly modelled component a:

$$
E[a\mid D,\rho]\approx m_a^z+C^z_{a,h_P}K_{\rho,PP}^{-1}(\mu_\rho-m_{\rho,P}),
$$
$$
\operatorname{Cov}(a,b\mid D,\rho)\approx C^z_{ab}
-C^z_{a,h_P}\left(K_{\rho,PP}^{-1}
-K_{\rho,PP}^{-1}\Sigma_\rho K_{\rho,PP}^{-1}\right)C^z_{h_P,b}.
$$

Examples of pre-label cross-covariances are $C^z_{f,h}=\rho C_f^z$, $C^z_{g,h}=\sqrt{1-\rho^2}K_f$ and $C^z_{\theta,h}=-s_\theta^2\mathbf1^T$. They are retained. Component masses are

$$
w_\rho\approx\frac{p(\rho)\widetilde Z_\rho}{\sum_r p(r)\widetilde Z_r}.
$$

The response evidence cancels between components because their marginal response models are identical. This is integration over the declared coupling prior, **not empirical-Bayes selection of a best ρ**. Approximate evidence can nevertheless bias the masses; accurate predictive probabilities alone do not validate evidence estimates.

Four-input prediction is

$$
p_*(x)=\sum_\rho w_\rho\,
\Phi\!\left(\frac{\mu_{\rho,h}(x)}
{\sqrt{\tau^2+V_{\rho,h}(x)}}\right).
$$

Mixture covariance includes both within-component covariance and covariance of component means. Replacing this mixture by independent depth/threshold fits, or dropping between-component variance, is incorrect. One paid simulation appends its Y and available z once, refits all paid factors, and updates both component posteriors and their masses. Its label can modify f; its depth can modify h and θ through their conditional dependence. Selection based only on observed history and candidate features is compatible with this conditional likelihood; the adaptive selection policy factors cancel in the sequential posterior. This does not make the paid class fraction an unbiased population estimate.

**Paired acquisition with posterior mixture learning.** Keep V1's target

$$
V(D)=\sum_{i\in T}v_i\,\operatorname{Var}\{\pi_i\mid D\},
\quad \pi_i=\Phi(h_i/\tau),\quad
a(j)=V(D)-E_{Z_j,Y_j\mid D}V(D,Z_j,Y_j),
$$

where T is the fixed feature-only candidate pool, uniformly weighted, including paid inputs. The utility concerns epistemic uncertainty in canonical-label probability, not label entropy or a depth maximum. It is not a BA objective.

For component k, future depth has density $d_k(z)=N(z;\mu_{k,f_j},V_{k,f_j}+\sigma_z^2)$. At each z, first update

$$
w_k(z)=\frac{w_k d_k(z)}{\sum_\ell w_\ell d_\ell(z)}.
$$

Condition its **joint** Gaussian on z using $C_{h_i,f_j}$ to obtain $m_{ki}(z),C_{kii'}(z)$. Define

$$
b_{ki}=\frac{m_{ki}(z)}{\sqrt{\tau^2+C_{kii}(z)}},\quad
p_{ki}(z)=\Phi(b_{ki}),\quad q_k(z)=p_{kj}(z),
$$
$$
J_{kij}(z)=\Phi_2\!\left(b_{ki},b_{kj};
\frac{C_{kij}(z)}{\sqrt{(\tau^2+C_{kii}(z))(\tau^2+C_{kjj}(z))}}\right).
$$

Mix the *moments* at that z:
$p_i(z)=\sum_kw_k(z)p_{ki}(z)$,
$q(z)=\sum_kw_k(z)q_k(z)$ and
$J_{ij}(z)=\sum_kw_k(z)J_{kij}(z)$.
Observing Y then reweights component k by $q_k(z)$ or $1-q_k(z)$. Consequently the expected variance reduction is

$$
\boxed{a(j)=\int\!\left[\sum_kw_kd_k(z)\right]
\sum_i v_i\left[
\{p_i(z)-p_i\}^2+
\frac{\{J_{ij}(z)-p_i(z)q(z)\}^2}{q(z)\{1-q(z)\}}
\right]\,dz.}
$$

This follows from total variance and the conditional means $J/q$ and $(p-J)/(1-q)$. Averaging the V1 utilities of separate components would omit learning the coupling and is not this acquisition. Gaussian quadrature integrates over every component's predictive z distribution. All operations are exact for the Gaussian mixture approximation up to numerical integration; they do not make EP or future re-EP fits exact.

~~~text
Given paid-only data, fit all declared components and their masses.
For every unpaid candidate:
    Integrate z over the mixture of predictive response distributions.
    Reweight components by their density of z.
    Condition each component jointly on z; compute p_i(z), q(z), J_ij(z).
    Sum response information and conditional-label information over the fixed pool.
Check score stability at higher quadrature orders; choose by the fixed tie rule.
Reveal Y and available z only for the chosen ID; charge one query and refit.
~~~

For K components, n paid cases, M integration points, C candidates, G response nodes and L bivariate-CDF nodes, dense component fitting is $O(KI n^3)$ for I EP iterations; principal covariance storage is $O(K(M+C)^2+n^2K)$. Mixture acquisition is approximately $O(CK M^2+CK^2GML)$ with this vectorized implementation; near-singular CDF integration can cost more. There are no fantasy model fits. Candidate masking and missing-output handling follow V1. Unpaid response availability is not inspected.

**Numerical validation and failure discrimination.** Seventeen deterministic correctness checks passed, plus the supplemental leakage and fallback checks. They verify the V1 endpoint, binary limit, mixture and component covariances, missing-response retention, single-factor EP moments/evidence, and acquisition identities/bounds on the exercised cases. Delivery validation additionally checks prediction-batch invariance. The original V1 source copy is byte-identical. These are finite tests, not uniform guarantees. [Correctness/reference runner][referencecode], [numerical record][references]

| Independent reference | Observed approximation error |
|---|---|
| Scalar θ posterior, five positive / one negative | Exact p=0.800461. Laplace error 0.017007; EP error **0.000583**. θ variance error falls from 0.000558 to 0.000196. |
| Two-paid-label tensor quadrature | EP-mixture maximum probability error **0.00338**, joint f/h covariance error **0.000579**, component-mass error **0.000210**. The two quadrature resolutions differ in p by 0.0000191. |
| One-paid-label paired-acquisition reference | Maximum probability error 0.00258; score error **0.000474**. Independent response/latent quadrature resolutions differ by 0.00000682. Both select candidate 1 of three; the two-label label-only check also preserves the ranking. |
| Original V1 sparse-negative posterior, four ESS chains | EP is closer to the sampling reference than Laplace, but the reference probability is **more positive**, approximately 0.732. Maximum paid-latent covariance discrepancy for EP is 0.00813. Sampling precision does not erase approximation error. |

The last result is decisive against “fixing Laplace will by itself preserve that negative.” V2's global sharing revision addresses a different restriction. The sampled reference is for fixed V1, not a claim that V2's sparse mixture is exactly inferred. The acquisition-ranking checks cover two tractable examples; near ties elsewhere can still change under posterior approximation even when quadrature has converged.

**Controlled mechanism results.** Ten prespecified four-dimensional worlds include informative, redundant, locally contradictory and anti-aligned depth; shifted threshold; zero/one/two paid negatives; missing responses; and one model-generated family. Other worlds are analytic laws, deliberately outside the selected GP family. Static comparisons use the same paid maximin prefixes at B8/B16, two seeds, 40 candidates and 96 evaluation inputs per world/seed. Rare-composition prefixes are engineered stress tests; their counts are not population estimates. All held-out outcomes and latent probability truths are available only to the evaluator.

| B16 mean across two frozen seeds | V2 BA | V1 BA | Fixed-ρ=1 EP BA | Binary EP BA | Interpretation |
|---|---:|---:|---:|---:|---|
| Informative depth | 0.880 | 0.916 | 0.887 | 0.815 | Depth helps relative to binary; V2 still loses to V1. |
| Harmful bridge | 0.854 | 0.627 | 0.684 | 0.854 | Withdrawal of sharing, beyond inference improvement, removes much of the imposed harm. |
| Local contradiction | 0.728 | 0.738 | 0.741 | 0.710 | Global sharing is not a complete local-mismatch remedy; specificity versus binary falls 0.008. |
| One paid negative | 0.500 | 0.500 | 0.500 | 0.516 | V2 correctly classifies its paid negatives but misses all held-out negatives at 0.5. |
| Two paid negatives | 0.531 | 0.531 | 0.500 | 0.531 | No BA advantage over binary; held-out specificity remains only 0.0625. |

In the harmful world, average posterior mass at ρ=0 is 0.968; in the informative world mass at ρ=1 is 0.919. This supports learning global compatibility in those worlds. One-negative mass remains diffuse, approximately (0.276,0.429,0.295); preserving the observed negative locally does not identify the unseen negative region. Its paid-negative probabilities improve from V1's 0.514/0.521 to V2's 0.381/0.352, while held-out specificity stays zero. Binary EP has specificity 0.0313. This is evidence **against claiming the scientific question solved**.

Brier improves over Binary EP in informative, local-contradiction, shifted-threshold and missing-response worlds, but worsens in the redundant and sparse cases. The full record includes BA, specificity, sensitivity, Brier, log loss, probability MSE, 90% probability coverage/width, paid-negative probabilities and weights for **every** arm, budget and seed. Coverage concerns the known synthetic $\pi(x)$, not whether a binary event falls in an interval. Intervals are often very broad: informative coverage 1.000 with mean width 0.764, harmful coverage 1.000 with width 0.900. Two seeds and correlated input predictions do not certify uncertainty calibration. [Complete controlled summaries][summary], [full inputs/results][results]

**Sequential experiment.** On three worlds × three seeds, paired acquisition and margin use the **same V2 model**, all paid outputs, the same feature-only B6 startup, and four subsequent queries. Future outcomes stay behind the paid interface. All 18 trajectories completed; all nine paired comparisons diverged at B7 or B8. Paired-minus-margin BA-AULC over B6–B10 averaged **+0.00416**, with range **−0.05059 to +0.09325**, and was positive in **2/9** pairs. The positive average is dominated by one harmful-bridge case. All three informative-depth pairs lost BA. Proper-score and specificity changes were mixed; the nine individual contrasts are retained in the summary. These different worlds are not draws from a defined SPH population, so pooling them is descriptive. There is no demonstrated acquisition superiority or sample-saving result.

![V2 controlled mechanisms](C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/V2_MECHANISMS.png)

**One additional idea: distinguish the BA loss from probability calibration.** This idea was frozen separately and tested by exact finite-pool enumeration, not by rescoring Opus's predictions. For population probability $\eta(x)$ and prevalence $\pi=E_X\eta(X)$,

$$
\operatorname{BA}(d)=\tfrac12\left\{
\frac{E_X[\eta(X)d(X)]}{\pi}
\frac{E_X[(1-\eta(X))(1-d(X))]}{1-\pi}\right\}.
$$

With known η and π, choose positive iff $\eta(x)\ge\pi$. Under posterior uncertainty, the population Bayes action compares $E[\eta(x)/\pi\mid D]$ against $E[(1-\eta(x))/(1-\pi)\mid D]$; replacing this by a ratio of posterior means is an approximation. A feature-only reference distribution plus joint posterior function draws can estimate those integrals from paid data, but only under the model and a justified target feature distribution. Neither the adaptive paid fraction nor the already inspected NEW count 124/136 is a free label-blind learner input.

For a finite evaluation pool with random class totals, the exact action instead compares
$E[Y_i/N_1\mid D]$ and $E[(1-Y_i)/N_0\mid D]$, conditional on both classes being present. Known paid labels would be fixed in these expectations; unobserved labels and totals would be integrated. This is not generally a single prevalence plug-in cutoff.

The six-input counterexample uses **exact**, calibrated probabilities (0.10,0.65,0.75,0.85,0.90,0.95). Conditional on both classes, expected BA is 0.79024 at 0.5 versus 0.79859 under the exact finite-pool action. Thus a decision mismatch can exist without miscalibration. Its separately illustrated paid fraction of 1.0 comes from high-probability inputs; it is not conditioning data for that enumeration. This modest example neither identifies C3's cause nor licenses a held-out cutoff search. The primary V2 experiments kept cutoff 0.5. The declared stopping point is reached: no real-data threshold selection or additional decision-rule sweep.

**Prior work and scope of contribution.** Covariance sharing across outputs is established GP coregionalization, not a novel model family. The useful construction here is the fixed marginal classifier prior across sharing strengths, paired output updating, and explicit no-auxiliary control. [Álvarez, Rosasco & Lawrence][vector] EP's suitability for predictive distributions and evidence has substantial prior study; those papers also distinguish evidence quality from prediction quality. They do not guarantee accuracy in our sparse mixture. [Kuss & Rasmussen][kuss], [Nickisch & Rasmussen][nickisch] Elliptical slice sampling supplies an independent latent-Gaussian posterior check, with finite-chain diagnostics rather than an exactness claim. [Murray et al.][ess]

Relative to repository attempts, this is not Tobit censoring, MixGP's replacement of one likelihood channel, a physics-mean classifier with an arbitrary uncertainty-weighted selector, or a scalar threshold-root guard. It retains both paired likelihoods, learned coupling masses and their posterior cross-covariances. Previous SUR/PEER failures make the negative sequential result credible evidence to retain, not a reason to rename the score and rerun. Gotovos's scalar-GP/fixed-threshold assumptions and Letham's Gaussian/probit conditioning machinery do not provide a sample-complexity or boundary-recovery theorem for this mixed-output model. [V1 prior-attempt review][v1design], [Gotovos et al.][gotovos], [Letham et al.][letham]

**What should happen next.** Finish V1 Stage M unchanged. Then execute the separately versioned NEW matched-path V2 model/ablation study in [OPUS_V2_IMPLEMENTATION_REQUEST.md][handoff]. Fixed-ρ=1 EP distinguishes inference effects from V1; V2 versus that arm isolates uncertain sharing; V2 versus Binary EP tests the continuous likelihood's incremental value. The decisive evidence is preserved negative specificity and proper scores on held-out simulations, not a less extreme probability at the already paid negative. A +0.01 BA change is a practical effect threshold, not a forecast, significance test or test of whether auxiliary information exists.

My preferred explanation is that **forced global sharing and limited negative coverage can coexist**. Evidence against V2 is its failure on rare held-out negatives, broad intervals and inconsistent acquisition gains. If better inference helps but allowing weaker sharing does not, approximation was the more relevant defect. If coupling mass withdraws but specificity remains poor, local coverage, the remaining discrepancy prior or a decision-loss mismatch is more plausible than a single global bridge problem. The frozen controlled results already rule out “inference alone fixes the original V1 negative”; the proposed real-data controls distinguish the remaining explanations without tuning on held-out BA.

C4 repeats 21–24 may be drafted only after verifying they are unused, as another split-stability check on these same simulations. This package does not verify their current availability, run them or use them for selection. Repeated/nested evaluation can estimate specified procedures conditional on this inspected dataset and split design; it cannot undo model-family selection from its labels. Prospective transfer, rare-region validity and physical morphology claims need genuinely new simulations and independently specified annotation/observation evidence. There is no research-closing date.

**Türkçe açıklama.** V2'nin yeni fikri, derinliğin etikete ne kadar bağlanacağını öğrenmek; derinlik yanıltıcıysa aynı kapasiteli ikili modele yaklaşmak. Bağımsız hesap, V1'in tek negatifteki sorununun yalnızca Laplace hatası olmadığını gösterdi: daha doğru posterior da negatife yüksek Keyhole olasılığı veriyor. V2 bu baskıyı azalttı ama seyrek negatifleri genelleme sorununu çözmedi; aktif örnek seçimi de tutarlı üstünlük göstermedi. Bu yüzden V1 deneyi değişmeden tamamlanmalı, ardından V2 ve aynı kapasiteli ikili model yeni bir manifestoda karşılaştırılmalı.

[selection]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/SELECTION_RECORD_V2.json>
[amendment]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/AMENDMENT_01_DIAGNOSTICS.md>
[supplement]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/SUPPLEMENTAL_DIAGNOSTICS.json>
[references]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/NUMERICAL_REFERENCES.json>
[referencecode]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/reference_checks.py>
[summary]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/CONTROLLED_SUMMARY.md>
[results]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/CONTROLLED_RESULTS.json>
[handoff]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/OPUS_V2_IMPLEMENTATION_REQUEST.md>
[v1design]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week20_method_development/ASTRA_WEEK20_METHOD_DESIGN.md>
[c3freeze]: https://github.com/iso0/active-level-set-week1-warmup/blob/e2bcf97a55736cdd2933b6761678d8b695358205/outputs/week20_active_temporal_development/c3/freeze_c3.json
[c3decision]: https://github.com/iso0/active-level-set-week1-warmup/blob/e2bcf97a55736cdd2933b6761678d8b695358205/outputs/week20_active_temporal_development/c3/decision_c3.json
[c3contrasts]: https://github.com/iso0/active-level-set-week1-warmup/blob/e2bcf97a55736cdd2933b6761678d8b695358205/outputs/week20_active_temporal_development/c3/contrasts.csv
[development]: https://github.com/iso0/active-level-set-week1-warmup/blob/e2bcf97a55736cdd2933b6761678d8b695358205/outputs/week20_active_temporal_development/DEVELOPMENT_REPORT.md
[guard]: https://github.com/iso0/active-level-set-week1-warmup/blob/e2bcf97a55736cdd2933b6761678d8b695358205/src/week20_track1_ext.py
[engine]: https://github.com/iso0/active-level-set-week1-warmup/blob/e2bcf97a55736cdd2933b6761678d8b695358205/src/week18_engine.py
[vector]: https://arxiv.org/abs/1106.6251
[kuss]: https://jmlr.csail.mit.edu/papers/volume6/kuss05a/kuss05a.pdf
[nickisch]: https://www.jmlr.org/papers/volume9/nickisch08a/nickisch08a.pdf
[ess]: https://proceedings.mlr.press/v9/murray10a.html
[gotovos]: https://people.csail.mit.edu/alkisg/files/gotovos13active.pdf
[letham]: https://proceedings.mlr.press/v151/letham22a.html
