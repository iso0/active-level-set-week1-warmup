# What the calculations establish, and what they do not

The gated covariance is positive semidefinite because D K D is PSD whenever K is.
Compact support of K(x,x') restricts correlation; multiplying by a(x)a(x') also
scales marginal variance. These are separate interventions. Unknown location must
be integrated or estimated with its selection cost; a truth-selected gate is not
a fair baseline. Our finite mixture includes that cost, conditional on fitted
background parameters.

For separated Gaussian residuals the constant-variance log Bayes factor has the
exact n-dependent determinant penalty in MODEL_DESIGN_V1.md. The numerical
examples independently verify it. They establish a possible mechanism, not the
cause of historical Opus/Astra trajectories. In the new pilot the stationary
compact component was suppressed, while gated components retained support.
Their simultaneous classification failure demonstrates that activating a local
component is insufficient for useful boundary recovery.

The v2 low-rank correction separates a more coherent mean response from the
same local prior variance. Its exact conditional updates use the covariance,
not a fabricated cross-covariance inferred from marginal uncertainty. The
512 independent dense replays reproduce odd-budget pre-query moments and every
margin choice; the maximum moment discrepancy is 1.82e-13. These numerical facts
do not calibrate the plug-in posterior under model misspecification.

## Two useful limitations

**Confounding with the background.** If the paid background covariance is
C0=B+kappa aa' for positive-definite B and kappa>0, then

    q = a' C0^-1 a = q0/(1+kappa q0),  q0=a' B^-1 a.

The Woodbury identity proves q<=1/kappa. Consequently the coefficient posterior
variance `(tau^-2+q)^-1` need not vanish even as observations increase. This is an
identifiability statement about decomposition into background and correction,
not proof that their sum is poorly predicted. An unconditional claim that a
wrong extra component must become harmless at rate n^-1/2 would be invalid.
Our pilot fixes theta from the strong null; it does not test joint estimation of
background and local covariance. That remains the strongest model-level rival
to a weak-correlation explanation.

**Observational ambiguity.** Compare world A: true f=g+delta with observations
z=f+epsilon, and world B: true f=g with monitor bias delta and observations
z=f+delta+epsilon. At every candidate the observation law is identical. By
induction any adaptive policy depending only on public inputs and paid z has the
same query/history law in both worlds. Their physical level sets can differ.
No learner using only this channel can consistently identify which physical
boundary is correct in both worlds. Independent quality information, another
legitimate output, or a structural assumption is necessary. The corruption
control illustrates the risk; it does not certify that real monitor data have
this defect.

## Objective and evidence limits

BA=(sensitivity + specificity)/2. Our shared cutoff 0.5 targets the latent zero
contour, not the BA-optimal surface for every imbalanced feature distribution.
Changing that cutoff from evaluator labels would invalidate the matched-model
test. A future loss study must estimate its target distribution legitimately and
separate decision calibration from representation and acquisition.

The results show proper-score improvements and small exploratory BA differences;
neither correction passed the predeclared practical screen. No final TEST, new
selector comparison or query-saving claim is justified. V2 reused inspected DEV
worlds. Pointwise bootstrap intervals are descriptive with only four independent
worlds per fixed family. There is no multiplicity-controlled confirmation,
physical simulator validation, canonical-label result or new general theorem.

The finishing receipt field `margin_argmax_roundoff_near_ties` counts literal
argmax disagreements tolerated by the numerical score check, not every close
first/second score pair. Its zero value establishes no disagreement in these
replays; it is not a universal separation-margin or numerical-conditioning claim.
