**Prepared V2 handoff — separate manifest after frozen V1 Stage M**

13 October 2026 · prepared locally, **not sent and not executed on SPH**

**Ownership and order.** First complete the already frozen V1 Stage M on NEW, OLD and POOLED, DEV 1–2, B16/B40. Preserve all six V1 arms, priors, paid paths and reporting rules even if the results disappoint. Do not substitute V2 into that run, repair its priors retrospectively, or label a changed result “V1.” V2 requires a new manifest, implementation module and output directory. Temporal numerical repair remains a separate Opus task.

C3 is spent and failed the locked ACTIVE−G3 NEW BA superiority criterion. Stage A and C4 are **design-only** in this handoff. C4 21–24 may be proposed only after checking that it remains unused; it is another split check on inspected simulations, not independent data.

**Candidate and rationale.** Implement the covariance-preserving uncertain-coupling model from [the design][design] and [reference code][code]:

$$
h=\rho f+\sqrt{1-\rho^2}g-\theta+\delta,\qquad
f,g\stackrel{\rm ind}{\sim}GP(0,k_f),\quad
\rho\in\{0,0.5,1\},\quad p(\rho)=1/3.
$$

The marginal h prior is identical across ρ. Integrate approximate component evidences; do not pick a best ρ or average component acquisition scores. This is a bounded model study, not permission to search discrepancy scales or decision thresholds.

The original V1 sparse-negative probability is 0.674, while its independently sampled posterior gives approximately 0.732. More accurate inference therefore does not itself fix the bridge. V2 reduces this particular probability to 0.508 but still misses the negative at cutoff 0.5. Controlled V2 acquisition wins BA-AULC in only 2/9 paired experiments. These limitations are part of the handoff, not defects to hide.

**Exact integration contract.**

| Item | Required implementation |
|---|---|
| Deployment inputs | P, VX, LS radius, ST only. Use log of all four positive inputs and the same frozen training-pool feature scaler as the new manifest's V1 comparison. No monitor/label enters preprocessing. |
| Canonical outcome | Existing any-observed-manual-Keyhole Y. Preserve eligibility, all 49 Bug-withheld exclusions and full simulation IDs; H suffixes are not unique. |
| Continuous channel | Existing ACTIVE A with startup retained and the existing 90%-of-derived-exit convention. z=log(A/111 µm); unavailable/nonpositive A is missing, never a fabricated zero log-depth. |
| Paid interface | The learner gets a table containing only already paid X/Y/z. One simulation reveals both channels if available, costs one query and contributes each likelihood once. |
| Missing response | Retain Y and query count. No candidate masking, model choice or acquisition reward based on unpaid monitor availability. The model assumes ignorable missingness; report that assumption. |
| Reference pool | Fixed fold training candidates, feature-only. Center δ there and use it for uniform acquisition integration. Never recenter on the paid subset or prediction batch. Test rows never become candidates. |
| Prior | Matérn-3/2: f and g SD 0.60, lengthscales (1.5,1.5,1.5,1.5); δ SD 0.35, same lengthscales, pool-centered; θ mean 0/SD 0.35; σz=0.03; τ=0.15; jitter=1e-10. Zero process means; no extra intercept or class weights. |
| Hyperprior / fitting | The three ρ masses are integrated from paid observations. All other parameters are fixed. No ML-II, held-out calibration or hyperparameter grid selection for V2 or its matched binary control. |
| Prediction | Mixture of component probit probabilities, retaining covariance and between-component uncertainty. Four inputs only. h's component means/variances may be logged, but θ is not a universal physical threshold when ρ<1. |
| Decision | p≥0.5 for the primary comparison. The BA decision-theory counterexample in the design is separate; do not set a cutoff from test BA/q20 or from 124/136. |

**Train-only policy and numerical fallback.** At each paid prefix, initialize all EP sites at zero. Use parallel site updates, damping 0.5, relative natural-parameter tolerance 1e-8 for three consecutive updates, maximum 200 iterations. Compute tilted moments using stable log-CDF/Mills formulas. Evaluate component evidences including site constants; verify these against the reference rather than substituting the mode likelihood.

If any component's EP inference fails, refit **every** component using the declared Laplace routine. Keep the same hyperprior, data and kernels. Accept Laplace only at gradient infinity norm ≤2e-6 with finite objective; record solver-reported status separately. If fallback fails, stop that trajectory, retain its partial data and mark later endpoints missing. Do not drop one component, widen τ, enlarge δ, change numerical tolerances or seed a second attempt after seeing its performance. Significant negative posterior variances/nonfinite predictions outside inference are numerical stops.

Sparse or one-class paid data follow precisely this policy. No class-balancing duplication, forced negative discovery, bootstrap replacement or startup extension is permitted in this model study. A posterior mixture can remain prior-sensitive; uncertainty is not a reason to choose a favorite component.

The Binary V2 control removes the continuous likelihood altogether. Since every ρ then induces exactly the same h law and evidence, one EP solve can be reused and the masses must stay at their prior values. This is an algebraic saving, not less tuning effort: both arms have zero kernel search and the same hyperprior conventions. It must not inherit anything learned from depth. Historical G3 and ACTIVE E1 retain their frozen fitting rules and serve as full-model comparators, not capacity-matched controls.

If later development proposes a different τ, kernel or prior, it needs a new manifest and a paid-training-only rule first. One or two negatives cannot support simultaneous fitting of threshold location, softness, response residual, discrepancy geometry and coupling. Do not estimate them from test outcomes or from the future paid prefix.

**Numerical acceptance before real fits.**

- Reproduce the deterministic reference checks, including the exact V1 endpoint, rho=0 binary limit, unchanged binary masses, all within/between-component covariance terms, missing-response retention and Gaussian-mixture acquisition identity. Match saved errors within normal numerical tolerance; do not require an approximate method to match a non-Gaussian posterior exactly.
- Preserve the scalar posterior result: EP error about 0.000583 versus Laplace 0.017007. On the tractable two-label reference, maximum probability/covariance/mass discrepancies are about 0.00338/0.000579/0.000210. Use these as reproduction records, not universal error guarantees.
- The independent paired-acquisition reference gives a maximum score discrepancy about 0.000474 and the same selected candidate. A converged quadrature rule does not certify posterior accuracy or rankings in every real prefix.
- Corrupt all unpaid/test outputs before paid extraction: probabilities and acquisition must be unchanged. Test prediction batches against one combined batch; the reference pool must stay fixed.
- Inject one EP exception and verify the whole-mixture fallback with all component masses retained. Do not count this intentional fault as an observed scientific failure.
- Check one four-dimensional paid prefix against the standalone implementation, with identical transformed inputs, reference pool, priors, likelihood rows and precision. No undocumented changes to get parity.

**Bounded real-data DEV experiment — model contribution first.** After V1 Stage M is complete, create a new NEW-only manifest for DEV repeats 1–2, five folds, B16/B40, on **the exact saved Week 19 feature-only maximin paths**. Reuse V1 predictions only after verifying full path, split, response, scaler, prior, target, missingness and implementation hashes. Do not substitute the adaptive Track 1 trajectories. This request does not duplicate the full OLD/POOLED benchmark.

| Arm | Attribution |
|---|---|
| V2 EP mixture | Primary new candidate. |
| Fixed-ρ=1 EP | Same model as V1 with EP; separates inference from coupling. This is also a V2 component and may be reused exactly. |
| Binary V2 EP | Primary no-continuous-likelihood control with identical marginal h prior. |
| Immutable V1 Laplace | Original construction and declared priors. |
| Binary V1 Laplace | Separates binary EP effects from continuous information. |
| ACTIVE E1 | Frozen plug-in response-threshold comparator. |
| G3 | Frozen canonical binary comparator. |

This is at most **140 top-level checkpoint requests / 180 component solves** if nothing is reused. Exact reuse of prior V1 arms or the fixed-ρ=1 component reduces that count; it does not authorize additional repeats/arms. Reserve at most 20 further component attempts for declared numerical fallback, for a hard 200-component cap. Count failures and stop when the cap is exhausted. At most two local workers, one BLAS thread each; no paid compute.

Freeze feature-only path/scaler/reference-pool hashes and this configuration before the first V2 comparison. If the completed V1 manifest differs from the stated prior/scaler conventions, document the mismatch; do not quietly change either experiment. The V2-versus-Binary-V2 contrast must still share an identical marginal prior and transform.

Primary endpoint: NEW B40 paired BA difference V2−Binary V2. Also report V2−fixed-ρ=1 EP and fixed-ρ=1 EP−V1, which distinguish sharing from inference. Report B16 results, unchanged q20, specificity, sensitivity, Brier, log loss and short-K sensitivity using the existing 0<K/(F+C+K)<0.10 diagnostic subgroup. Keep the ten short-K simulations as ten unique cases across repeated predictions. Two checkpoints do not support fine-grained acquisition or query-saving conclusions.

A +0.01 mean BA difference is a **practical threshold**, not an expected effect, p-value or proof about the existence of depth information. Consider the candidate promising for further model work only if the same-path mean improvement is at least this size, negative specificity is not lower than Binary V2 and log loss is not worse. Report intervals and case counts regardless of this screen; do not call it confirmation. Failure of the screen records the result for this frozen model, not the end of research.

Use the frozen pooled-per-repeat aggregation, paired by split/budget, and retain simulation-level predictions. With only two repeats, do not present a fine bootstrap interval as external uncertainty. A class-stratified simulation-cluster resample retaining both repeats can describe uncertainty conditional on stored fits; it does not account for fitting/selection variability. Do not substitute a favorable q20 or AUC outcome for a failed BA criterion.

**Mechanism logs that distinguish the explanations.**

- Record component log evidences/masses, θ moments, f/h moments, component f–h/θ/discrepancy cross-covariances, mixture between-component variance, EP convergence and fallback status.
- For every paid negative, retain model probability and uncertainty; separately retain held-out negative predictions. A correct paid negative with poor held-out specificity is not successful minority-class generalization.
- Compare V1→fixed-ρ=1 EP first, then fixed-ρ=1 EP→V2. An inference improvement without a sharing improvement implicates approximation more than forced coupling. Withdrawal toward rho=0 with unchanged poor specificity implicates other limitations, including negative-region coverage or the fixed residual geometry.
- Evaluate proper scores without describing their difference as a pure calibration decomposition. Reliability diagnostics may be descriptive; they cannot select a held-out decision cutoff.
- Retain missing-response cases and costs. Use complete simulation IDs and hash all input/response joins. No q20/subgroup/morphology metadata may enter fitting or scoring.

**Stage A draft only.** The supplied mixture acquisition is ready for implementation, but its synthetic results do not justify automatic real-data execution. If a later authorized manifest evaluates it, compare the same fixed V2 model under paired utility versus probability margin, giving both arms the same paid label/response information. Use identical feature-only B16 startup, all five folds of DEV 3–4 and sequential B17–B40 as a possible bounded design: 500 top-level fits / 1,500 component solves before explicit fallback allowance. Do not run that draft now.

Use uniform fixed-pool probability-variance reduction; no label-entropy surrogate, depth-max objective or weighted sum of separate component utilities. Compare response/CDF quadrature at 15/48 and 31/64 nodes, ranking with the higher-order scores. The top gap exceeding twice the maximum score difference plus the omitted-tail bound is a **stability screen**, not a certified error bound. If unresolved, use the predeclared 63/96 check; accept a numerical tie only at 1e-8 with stable scores and the fixed ID rule, otherwise stop. Log scores and state before any selected outcome is revealed.

Record complete query paths, first divergence, overlap, class discoveries, proper-score curves and class errors. Primary acquisition comparison should be declared separately (for example BA-AULC B16–B40 with unchanged q20 alongside it). Do not infer savings from a larger information score or one successful query. A later sample-saving analysis needs its own fixed performance target and censoring rules.

**C4 and claim boundaries.** Do not execute or tune on C4. If unused repeats 21–24 are later frozen, they can assess new-split stability of a locked procedure on the existing inspected simulations. They cannot make ACTIVE target selection or model-family development independent of those labels. Robust prospective claims need genuinely new simulation and annotation/coverage evidence. Improvements in held-out canonical-label prediction, adaptive acquisition, query efficiency and physical boundary recovery are separate claims.

**Requested next action:** finish the frozen V1 Stage M, then prepare and execute only the separate bounded V2 model comparison above under a new manifest. Keep real Stage A/C4 as drafts. Retain Binary V2 and G3 as serious alternatives if the continuous channel remains harmful or fails to improve negative generalization.

[design]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/ASTRA_JOINT_MODEL_V2_DESIGN.md>
[code]: <C:/Users/ozgur/Documents/Codex/2026-10-10/files-pasted-by-the-user-you/outputs/astra_joint_model_v2/joint_model_v2.py>
