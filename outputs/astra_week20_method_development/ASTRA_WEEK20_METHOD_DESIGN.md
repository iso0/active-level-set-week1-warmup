**ASTRA Week 20 — joint depth–label inference with threshold uncertainty and discrepancy**  
13 October 2026 · evidence pinned to `7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9`  
Status: independent method development; controlled numerical evidence, not SPH performance evidence.

**Decision and deliverable.** Develop direction A: a **joint depth–label GP**, with a proper uncertain global threshold and a centered, regularized input-dependent discrepancy. Both the canonical label and available depth from every paid simulation contribute likelihood terms. Select queries by the expected reduction in uncertainty about the canonical-label probability, integrating the next simulation’s *paired* label and depth. A standalone implementation and controlled checks are included. Direction B was researched before this choice; it remains a possible extension, not a discarded information source. The choice and initial defaults were recorded before comparative results in [SELECTION_RECORD.json][selection]. Numerical repairs are recorded in [CHANGE_LOG.md][changes].

**What the pinned evidence warrants.** The Week 19 shared-path B40 result supports ACTIVE over WHOLE for classification, with contributions from response predictions and fitted thresholds; superiority over G3 remains uncertain. The updated evidence now isolates the late negative’s changed response at B16/r2/f5 and B40/r1/f2. Replacing its 312.0 µm response by 110.8 µm raises the fitted threshold from 104.04→119.64 and 86.02→117.14 µm respectively; each comparison corrects two negative predictions and loses one positive prediction. This demonstrates algorithmic influence at those checkpoints. It does not establish the historical adaptive ≈309 µm mechanism or isolate that simulation in other checkpoints with multiple changed responses. The direction of influence is composition-dependent. [Pinned review and isolation evidence][review]

**Why this differs from prior attempts.** This is a new implementation proposal for this repository, not a claim to have invented Bayesian multitask modelling.

E1's overlapping-class rule estimates $r=\log u=-a/b$. Its first-order sensitivity is $dr=-da/b+(a/b^2)\,db$: a weak slope magnifies intercept/slope changes, even though fitting the logistic objective is convex. Adaptive acquisition changes the paid depth/class composition, so an extreme crossing can alter later straddle queries and reinforce the composition that produced it. This is a **falsifiable feedback hypothesis**, not established historical causation. A future logged trajectory must show the paid-composition change, weakening slope/root movement and consequent query-rank change in that order; stable slopes, stable roots or unchanged rankings would count against this mechanism. Feature-only paths break that acquisition feedback, but do not mathematically guarantee stable calibration.

| Existing method | Substantive difference here |
|---|---|
| E1 depth GP + plug-in crossing | E1’s response fit does not use labels; its logistic crossing is a ratio of estimated coefficients and is treated as fixed in prediction/acquisition. Here labels and continuous responses update a coupled posterior without dividing by a fitted slope. [Code][e1] |
| E2 Tobit / E3 MixGP | E2 censors positive depth; E3 uses Gaussian likelihood alone on rows with depth, with their labels contributing to a plug-in threshold. Here a paired row contributes **both** likelihood factors under an explicit conditional-independence assumption. Missing depth never removes its label. E3’s pooled failure remains relevant evidence against assuming auxiliary outputs help automatically. [Code][tobit], [ledger][ledger] |
| M3 / LT physics classifiers | M3 has a fitted physics trend and discrepancy; LT already integrates Gaussian-prior trend coefficients. An uncertain intercept is therefore insufficient as a distinction. Here a measured response anchors a separate latent process, whose posterior dependence with threshold/discrepancy is retained. [Models][models] |
| Uncertainty mixtures / previous SUR and PEER | This is not an arbitrary weighted sum of margin, threshold SD and discrepancy magnitude. It evaluates information from a joint future observation under one model. Probability-SUR and PEER have already failed to improve acquisition reliably; changing the model and observed information does not guarantee a different outcome. [SUR report][sur], [Week 17 report][week17] |

**Direction B: useful training information, with a stricter information boundary.** Hernández-Lobato et al.’s GPC+ uses privileged training variables to modulate classification noise: $P(Y=1\mid f,g,z)=\Phi(f(x)e^{-g(z)/2})$. Its test predictor drops privileged variables and assumes homoscedastic test noise. That is a reliability assumption, not a general way to transmit systematic morphology information. It is risky to interpret credible rare negatives as noisy merely because depth disagrees. GPC+ also lacks a generative distribution for the auxiliary output of a future query. [Primary paper, §§2–3][gpcplus]

A stronger B extension would jointly model a small vector of paid coefficients $c_j(x)$, with observations $a_{ij}\mid c_j\sim N(c_j,\sigma_j^2)$, and a label latent $h=f-\theta+\delta+\sum_j\beta_j c_j$. Loadings need fixed normalization and strong regularization; freely learning many loadings from 12 negatives is a weakly identified problem. At an unqueried input, integrate the **joint posterior** of the coefficients and label latent. An observed test monitor is never an ordinary predictor input. A basis learned from data must use only the currently paid training traces; label-defined event times cannot set its alignment.

The repository provides melt bounding-box width and length as possible paid auxiliary channels. These are not vapor-cavity dimensions, and kinetic energy was examined in only 20 selected cases. Similar depth trajectories with opposite labels neither prove annotation error nor establish that auxiliary information is useless: other inputs, unmeasured morphology and observation coverage can differ. Conversely, more temporal resolution cannot recover a channel’s absent morphology information. A later B experiment should ask whether one prespecified channel improves held-out canonical-label prediction beyond the scalar joint model, not whether it reconstructs curves well. Its potential benefit is finite-sample learning from paid outputs; it does not change the four-input test interface. [Extraction code][series], [audit][audit]

A is the stronger first implementation because it directly addresses the known plug-in uncertainty omission and admits systematic exceptions while valuing both observations. It does not require inventing a new temporal signature or duplicating Opus’s temporal GP/rank-three benchmark. The failed relaxation descriptor remains rejected in its original form.

**Model and explicit assumptions.** Let $x=(P,VX,LS,ST)$, with LS the spot radius. Use feature-only scaling fixed on the candidate pool $Q$, and $z=\log(A/111\,\mu\mathrm m)$ when the existing ACTIVE response is positive and available. The 111 µm reference fixes units; it does not assert a universal threshold. Preserve canonical $Y=1$ iff at least one observed manually labelled Keyhole frame, NEW-136 and the 49 exclusions. Let $P$ be paid indices and $O\subseteq P$ those with available response:

$$
f\sim GP(0,k_f),\quad \theta\sim N(\theta_0,s_\theta^2),\quad
\delta\sim GP(0,k_\delta^c),\qquad h(x)=f(x)-\theta+\delta(x),
$$
$$
z_i\mid f_i\sim N(f_i,\sigma_z^2),\qquad
Y_i\mid h_i\sim\operatorname{Bernoulli}\{\Phi(h_i/\tau)\},\quad \tau>0,
$$
$$
p(f,\theta,\delta\mid\mathcal D)\propto p(f)p(\theta)p(\delta)
\prod_{i\in O}N(z_i;f_i,\sigma_z^2)
\prod_{i\in P}\Phi\!\left((2Y_i-1)\frac{f_i-\theta+\delta_i}{\tau}\right).
$$

The latent processes are independent **a priori**, not after observing labels. Conditional independence of the two likelihood channels is a new modelling assumption; common monitor/annotation residuals can violate it. The positive depth coefficient is fixed to one. Thus this method also replaces E1’s estimated logistic slope by a prescribed positive probit softness. It is not merely uncertainty added to an unchanged E1 model. The noise scales describe model residuals; neither is established sensor noise or evidence of erroneous annotations. The Bernoulli likelihood is a working model for recorded labels, not proof of repeat-trial stochastic physics. Omitting a missing response assumes its missingness is ignorable for this likelihood; no missingness model is implemented.

Center discrepancy using the fixed, label-blind reference pool:

$$
k_\delta^c(x,x')=k_\delta(x,x')-\overline{k_\delta(x,Q)}
-\overline{k_\delta(Q,x')}+\overline{k_\delta(Q,Q)}.
$$

Consequently $\sum_{x\in Q}\delta(x)=0$ almost surely. Keep the response mean fixed, omit a second free label intercept, use a proper threshold prior, and fix the response/link scales. These restrictions remove the constant-direction and scale ambiguities. They **do not physically identify** threshold and discrepancy from sparse data: a globally centered discrepancy can resemble a constant on the paid subset, and nonconstant response/discrepancy structure can trade off. This is why prior sensitivity is part of the numerical evidence. Recentring on each test batch would change the model and is prohibited.

**Approximate posterior and information flow.** First condition $f$ exactly on the available Gaussian observations to obtain $m_f^z,C_f^z$. Then

$$
h\mid z\sim N(m,K),\qquad m=m_f^z-\theta_0\mathbf1,
\quad K=C_f^z+K_\delta^c+s_\theta^2\mathbf1\mathbf1^T.
$$

On paid labels, minimize

$$
\tfrac12(h_P-m_P)^TK_{PP}^{-1}(h_P-m_P)
-\sum_{i\in P}\log\Phi\{s_i h_i/\tau\},\qquad s_i=2Y_i-1.
$$

For fixed hyperparameters the posterior density is log-concave on the prior support. The whitened negative-log-posterior Hessian is positive definite, giving a unique fixed-hyperparameter mode without forming an ill-conditioned coefficient ratio. E1's logistic objective is also convex; its root instability is not multimodality. With $t_i=s_i\hat h_i/\tau$, $\lambda(t)=\phi(t)/\Phi(t)$, set

$$
W_{ii}=\lambda(t_i)[\lambda(t_i)+t_i]/\tau^2,\quad
\alpha=K_{PP}^{-1}(\hat h_P-m_P),\quad
R=W^{1/2}(I+W^{1/2}K_{PP}W^{1/2})^{-1}W^{1/2}.
$$

For any components $a,b\in\{f,\theta,\delta,h\}$, the joint Gaussian approximation uses

$$
\mu_a=m_a^z+C^z_{a,h_P}\alpha,\qquad
C_{ab}=C^z_{ab}-C^z_{a,h_P}R C^z_{h_P,b}.
$$

In particular, before label conditioning, $C^z_{f,h}=C_f^z$, $C^z_{\theta,h}=-s_\theta^2\mathbf1^T$, and $C^z_{\delta,h}=K_\delta^c$. These terms propagate label information to all three components. This is a standard Laplace construction applied to the proposed joint model; it is not exact posterior inference. [GPML, chapter 3][gpml]

Pre-query prediction needs only $x$:

$$
P(Y_*=1\mid x_*,\mathcal D)\approx
\Phi\!\left(\frac{\mu_{h_*}}{\sqrt{\tau^2+V_{h_*}}}\right),
$$
$$
V_h=V_f+V_\theta+V_\delta-2C_{f,\theta}+2C_{f,\delta}-2C_{\theta,\delta}.
$$

The covariance terms are essential. Observing a new depth informs the response and, through the accumulated label likelihood, threshold/discrepancy; its label simultaneously constrains their relationship. Refit using each paid likelihood factor once, rather than treating an approximate posterior as a fresh prior and multiplying all old data again. A missing depth leaves the binary factor and paid-query count intact.

**One concrete acquisition.** Define the latent canonical-label probability $\pi_i=\Phi(h_i/\tau)$, and its posterior mean $p_i=E[\pi_i\mid\mathcal D]$. On fixed feature-only integration points $T$ with uniform weights $w_i$, target

$$
V(\mathcal D)=\sum_{i\in T}w_i\operatorname{Var}(\pi_i\mid\mathcal D),\qquad
a(j)=V(\mathcal D)-E_{Z_j,Y_j\mid\mathcal D}V(\mathcal D\cup\{Z_j,Y_j\}).
$$

This targets epistemic uncertainty in the canonical probability map. It is distinct from Bernoulli entropy and from $P(h>0\mid\mathcal D)$, the posterior membership of a latent probability level set. A known $\pi=0.5$ has zero value under this acquisition despite maximal label entropy. The objective is a surrogate for useful classification learning; it does not optimize BA/q20 directly or guarantee physical-boundary recovery.

Under the current joint Gaussian approximation, $Z_j\sim N(\mu_{f_j},s_j^2)$, $s_j^2=V_{f_j}+\sigma_z^2$. Let $c_i=C_{h_i,f_j}$. After a fantasy $z$,

$$
m_i(z)=\mu_{h_i}+c_i(z-\mu_{f_j})/s_j^2,\qquad
C_{ik}(z)=C_{h_i,h_k}-c_i c_k/s_j^2.
$$

Set $a_i(z)=m_i(z)/\sqrt{\tau^2+C_{ii}(z)}$, $p_i(z)=\Phi(a_i(z))$, $q(z)=p_j(z)$, and

$$
J_{ij}(z)=\Phi_2\!\left(a_i(z),a_j(z);
\frac{C_{ij}(z)}{\sqrt{[\tau^2+C_{ii}(z)][\tau^2+C_{jj}(z)]}}\right).
$$

Conditioning on the binary outcome gives posterior means $J_{ij}/q$ and $(p_i(z)-J_{ij})/(1-q)$. The law of total variance therefore yields the implementable, nonnegative score

$$
\boxed{a(j)=E_{Z_j}\sum_iw_i\left[
(p_i(Z_j)-p_i)^2+
\frac{\{J_{ij}(Z_j)-p_i(Z_j)q(Z_j)\}^2}{q(Z_j)[1-q(Z_j)]}
\right].}
$$

The first term values the response; the second values the label conditional on that response. They are not independent fantasy rewards. One-dimensional Gauss–Hermite quadrature and a deterministic bivariate-normal CDF evaluate the score without fantasy refits. This is exact conditioning of the Gaussian surrogate, up to numerical integration; it need not equal a newly refitted Laplace posterior. The implementation logs an upper bound when an extreme-probability label term is omitted.

```text
Fix candidate pool, input transform, integration weights and simulation-ID order.
For the current paid set, condition on available responses and fit joint label posterior.
For each unpaid candidate j:
    Integrate possible response Z_j using fixed Gaussian quadrature.
    Condition h jointly on each Z_j, including Cov(h, f_j).
    Integrate Y_j=0/1 with the bivariate-probit formula above.
    Sum response information + conditional label information over T.
Choose maximal score; break numerical ties by fixed simulation ID.
Pay once; append canonical Y and available response; record missing outputs.
Refit from all paid observations once and continue to the fixed budget.
```

The reference assumes a queried response will be available. Do not inspect unqueried monitor validity to decide which candidates receive paired utility. If response availability is not legitimate pre-query information, retain this explicit approximation and log any missing response when it is revealed.

**Cost and numerical safeguards.** Let $n$ be paid cases, $M$ integration points, $C$ candidates, $S=M+C$, $G$ response-quadrature nodes and $L$ CDF integration nodes. Fixed-kernel dense fitting costs $O(n^3)$ per Newton factorization; full joint covariance construction costs $O(S^2n+Sn^2)$. The current reference uses $O(CM^2+CGML)$ acquisition work and $O(S^2+n^2)$ principal storage. Near-singular CDF correlations use adaptive integration, so their cost is data-dependent. There is no hidden $CG$ sequence of model fits. Log-CDF evaluation, negative-tail Mills expansions, whitening, a gradient acceptance threshold and covariance checks avoid the identified numerical failures. The code is a dense fixed-hyperparameter reference, not a production-scale sparse GP.

**What the primary papers do and do not supply.** Gotovos et al. study a scalar function drawn from a stipulated GP, Gaussian observation noise and a given threshold; their implicit-threshold extension uses a fraction of the unknown maximum. Estimated morphology calibration and discrepancy are different assumptions, so its sample-complexity guarantee does not transfer. [Gotovos et al., 2013][gotovos] Letham et al. derive analytic Bernoulli look-ahead set-membership probabilities conditional on a multivariate-normal latent posterior and a probit link. That supports the conditioning machinery, but does not make the posterior exact or value a paired continuous response automatically. The acquisition above changes both the target functional and the query outcome space. [Letham et al., 2022][letham]

**Controlled numerical results.** The final suite passes **26 checks across 26 model-fit calls**, using fixed cases and no SPH observations. Python 3.14.4, NumPy 2.4.6 and SciPy 1.17.1 were used. Four solver status flags report unsuccessful termination, but meet the explicitly enforced gradient criterion; the largest logged infinity norm is $2.50\times10^{-7}$, below $2\times10^{-6}$. They are not silently reported as successful optimizer statuses. Numerical records, inputs, diagnostics and source hashes are in [prototype_results.json][results].

| Controlled question | Result and boundary of inference |
|---|---|
| Known fixed threshold | Discrepancy=0, threshold variance=0, labels disabled and $\tau\to0$ reproduce the matched response-GP plug-in probability to $4.62\times10^{-11}$. This checks an identity, not repository ML-II parity. |
| Uncertain threshold / posterior dependence | Threshold SD falls 0.350→0.177 after labels in the chosen case. Dropping component covariances changes probabilities by up to 0.0621. Covariance reconstruction error is below $7\times10^{-17}$; Gaussian Monte Carlo prediction agrees within 0.00091. |
| Approximation error | For a scalar uncertain-threshold posterior with five positives and one negative, exact quadrature gives $p=0.80046$; Laplace gives 0.78345. The 0.01701 error is a limitation, not a failed exactness claim. |
| Equal depth, different input regions | Held-out BA is 0.9375 for both the joint and binary-only models, versus 0.500 without discrepancy. This establishes representational ability, not a joint-model advantage over classification. |
| Sparse paid negatives | With one paid negative, the primary model still assigns it $p=0.674$. Prespecified prior sensitivities give 0.496–0.996. Properness does not imply correct rare-class prediction. The all-positive fit remains finite. |
| Adverse depth–label relation | Joint and binary-only BA tie at 0.9583, while joint Brier is worse: 0.0559 versus 0.0468. The depth bridge can hurt calibration. |
| Paired acquisition | Scores obey the variance bound and contain at least the information of either channel alone in the checked case. Joint and label-only scores choose the **same** query, $x=0.7$. One real toy update reduces integrated variance 0.044635→0.044424; its realized reduction is not the expected score. No query-saving result follows. |
| Leakage and structural limits | Corrupting every unpaid response/label changes neither prediction nor acquisition. Missing response retains its label. Identical input vectors receive identical probabilities; this constructed limit says nothing about real cases that merely have similar depth traces. |

The acquisition also matches an independent analytic threshold-only identity, returns exactly zero for known π=0.5, and passes tail/near-singular numerical checks. [Reference implementation][code], [check runner][checks]

![Controlled prototype mechanisms](C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week20_method_development/prototype_mechanisms.png)

**Limiting comparisons.** A fixed threshold with zero discrepancy still differs from E1 if labels are allowed to update the response process. Exact predictive reduction additionally disables that binary likelihood and takes the hard-threshold limit under matched response-GP conventions. Conversely, removing all continuous likelihood terms yields a binary probit GP with effective prior covariance $K_f+K_\delta^c+s_\theta^2\mathbf1\mathbf1^T$. This is the capacity-matched binary-only control; it is not automatically historical G3, whose mean/kernel/hyperparameter rules differ. If discrepancy dominates or the imposed positive depth effect damages calibration, retaining a binary classifier is a substantive outcome rather than an implementation failure.

**Recommended next experiment.** Run the bounded NEW-only, matched-path model/ablation study in [OPUS_METHOD_IMPLEMENTATION_REQUEST.md][request], followed by its separately gated same-model acquisition comparison. The immediate scientific question is whether paid ACTIVE depth contributes canonical-label information beyond the matched binary prior without suppressing negatives. This development can proceed before the morphology meeting. The meeting can refine the interpretation of any discrepancy; it is not a prerequisite for this implementable experiment. Leave C3 reserved. No real-data model fits, Opus checkout changes, push, external message or paid job were performed here.

**Türkçe açıklama.** Yeni fikir, derinlik tahminini, belirsiz eşiği ve derinlikle açıklanamayan girdi etkisini birlikte öğrenmek. Böylece ücretli bir simülasyonun hem derinliği hem etiketi aynı modele bilgi veriyor; sonraki örnek de bu iki bilginin beklenen katkısına göre seçiliyor. Prototip hesapların tutarlı olduğunu gösterdi, fakat seyrek negatiflerde öncüllere duyarlılığı da ortaya çıkardı. Şimdi gerçek NEW simülasyonlarında önce modelin katkısı, sonra örnek seçiminin katkısı ayrı ölçülmeli; henüz örnek tasarrufu veya daha iyi sınır bulma sonucu yok.

[selection]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week20_method_development/SELECTION_RECORD.json>
[changes]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week20_method_development/CHANGE_LOG.md>
[results]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week20_method_development/prototype_results.json>
[code]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week20_method_development/joint_depth_label_gp.py>
[checks]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week20_method_development/run_checks.py>
[request]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/week20_method_development/OPUS_METHOD_IMPLEMENTATION_REQUEST.md>
[review]: https://github.com/iso0/active-level-set-week1-warmup/blob/7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9/outputs/week19_temporal_regime_dev_pilot/review/REVIEW.md
[e1]: https://github.com/iso0/active-level-set-week1-warmup/blob/7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9/src/week18_engine.py#L45
[tobit]: https://github.com/iso0/active-level-set-week1-warmup/blob/7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9/src/week18_tobit.py#L147
[ledger]: https://github.com/iso0/active-level-set-week1-warmup/blob/7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9/outputs/week18_independent_research/ATTEMPT_LEDGER.md
[models]: https://github.com/iso0/active-level-set-week1-warmup/blob/7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9/src/week17_models.py
[sur]: https://github.com/iso0/active-level-set-week1-warmup/blob/7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9/outputs/week9_phase1_18b_prospective_global_gpc_sur_benchmark/FINAL_PHASE1_18B_REPORT.md
[week17]: https://github.com/iso0/active-level-set-week1-warmup/blob/7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9/outputs/week17_model_and_acquisition/WEEK17_REPORT.md
[series]: https://github.com/iso0/active-level-set-week1-warmup/blob/7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9/src/week19_series.py
[audit]: https://github.com/iso0/active-level-set-week1-warmup/blob/7707d7f43f1c36a1d4cce3c18edaf563e75a1fe9/outputs/week19_temporal_regime_audit/REPORT.md
[gotovos]: https://people.csail.mit.edu/alkisg/files/gotovos13active.pdf
[letham]: https://proceedings.mlr.press/v151/letham22a.html
[gpcplus]: https://proceedings.neurips.cc/paper_files/paper/2014/file/a60f5f0f9348059cabc17bcb0e7686db-Paper.pdf
[gpml]: https://gaussianprocess.org/gpml/chapters/RW3.pdf
