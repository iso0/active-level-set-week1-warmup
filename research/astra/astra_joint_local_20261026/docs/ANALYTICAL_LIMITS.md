# What the joint-learning result identifies

The working observation is y=f(x)+epsilon with Gaussian independent noise and
latent target1{f>=0}. Several test worlds deliberately violate that likelihood.
The 0.5 decision threshold is common across arms and minimizes model-based
equal-cost sign error; it is not generally the BA-optimal threshold under
imbalance. That limitation is held constant to isolate model learning. Region
error measures sign classification, not geometric/Hausdorff boundary recovery.

Let C_j(theta)=C_0(theta)+tau² a_j a_j', with C_0=K(theta)+sigma²I,
fixed tau²=.36, prior mass .5 on null and .5/64 on each alternative. At most one
rank-one local component is active. The marginal predictor is a Gaussian mixture,
not generally a GP. Define L(theta)=log sum_j pi_j exp ell_j(theta).

\[
\nabla L(\theta)=\sum_j w_j(\theta)\nabla\ell_j(\theta),\qquad
\log(p_j/p_0)=\tfrac12\left[\frac{\tau^2 b_j^2}{1+\tau^2q_j}
-\log(1+\tau^2q_j)\right],
\]

where q_j=a_j'C_0^{-1}a_j and b_j=a_j'C_0^{-1}y. At a null optimum only
the null score must vanish; the alternative scores generally do not. Joint
optimization changes the whitening, evidence penalty and component weights.
This explains how fits can differ, not why held-out predictions must improve.
The model integrates coefficients and locations conditional on estimated theta;
it does not integrate hyperparameter uncertainty. Nonconvex numerical optimization
can miss optima, and higher training evidence is not a predictive guarantee.

Fixed-parameter Gaussian conditioning already permits background reattribution:
E[g|y]=K C_0^{-1}(y-a E[beta|y]). It is not merely adding a residual to an
unchangeable posterior mean. The previous coherent model had this property;
the new intervention is learning theta under the mixture objective. Thus “the
old model could not update its background at all” would be an incorrect account.

Ba–Joseph's Theorem1 explicitly equates single-stage and sequential predictor
forms **at the same parameters**, then distinguishes simultaneous parameter
estimation. This paper is Ba & Joseph(2012), arXiv posted2013, not a new principle
introduced by this campaign. Davis–Hans–Santner uses a richer heteroscedastic
composite GP with posterior parameter integration and smoothness/weighting
assumptions. Our single coherent basis and empirical Bayes are much narrower.
[Ba–Joseph §3.2/§4 (PENDING_ARCHIVE)](../../../../docs/research/ARCHIVE_MANIFEST.md#pending-49a6e0d0fd18893a);
[Davis–Hans–Santner §§2–3 (PENDING_ARCHIVE)](../../../../docs/research/ARCHIVE_MANIFEST.md#pending-b3d8571d6751d60f).

## Observed diagnostic pattern, not a causal proof

The extra-null optimizer reproduces approximately the original strong fit and
does not account for the gain. The spatial joint model exceeds the trace-matched
joint control. This supports a constrained model-learning/spatial-structure
effect on these paths. It does not isolate noise from length-scale reattribution.
See results/completion/FAMILY_DIAGNOSTICS_B24.csv: compared with fixed_extra,
mean log-noise change is+.408 for plateau,+.015 for radial islands,+.065 for shell,
but−.197 for twin islands. Noise does not uniformly fall. Length changes and
null weights also move; conditional local-weight entropy remains2.17–2.76 nats
for these island families (maximum log64≈4.159). Location is not simply known.

Information is sparse. At B24 geometric hits occur in20/24 radial-island paths,
but15/24 paths have at most one observation inside the geometric region with
the planted target sign. Shell:16/24 geometric-hit paths,15/24 have at most one
signed-target observation; plateau17/24 and11/24; twins19/24 and13/24. These are
dependent-path counts, not independent-world success probabilities. Geometric
membership, latent-positive sign and a noisy positive measurement are different.
For negative islands the scientifically relevant local sign is negative, hence
the extra signed-target diagnostic. For controls it has no planted-regime meaning.
All queries before first hit remain charged. Post-hit means are selected-prefix
descriptions and do not estimate the causal benefit of a local-query policy.

Sparse local observations and the one-basis model restriction coexist. A hit is
not enough to identify a boundary. Conversely poor error after a hit does not
alone prove representation failure. Even with a known basis, if
C_0=B+kappa aa', Sherman–Morrison gives
q=q_0/(1+kappa q_0)<=1/kappa. Background/local decomposition can remain uncertain
while their sum predicts well. This is a conditional identifiability example,
not a universal lower bound on achievable classification.

Monitor bias is stronger: observation z=f+b+epsilon is identical in distribution
under (f,b)=(g+delta,0) and (g,delta). An adaptive learner sees the same history
distribution and cannot distinguish physical change from bias with this channel
alone. A prior chooses an attribution; it adds no identifying observation.

## One discriminating next experiment, not executed here

Before any further acquisition expansion, freeze a small factorial diagnostic
crossing **available local information** (the existing sparse paid set versus a
predefined additional observation ladder, every extra observation counted) with
**representation** (current unknown-location bank versus an evaluator-only true
shape/known-location control). Use both genuine local change and matched monitor
bias worlds; the oracle control is never a deployable selector or a savings claim.
If the true-shape control fails on sparse data but both models improve with more
information, inadequate evidence is supported. If the bank remains poor after
the true-shape control works with the same observations, representation/location
restriction is implicated. Both may matter. An independent calibrated output
would be required to distinguish the observationally equivalent bias worlds.
Register the diagnostic and subsequent independent evidence before outcomes;
these inspected TEST worlds can only be development. This is a proposal, not
use of the campaign's optional continuation or permission to reopen old queues.
