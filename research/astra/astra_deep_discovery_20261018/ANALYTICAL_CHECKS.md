# Analytical checks and falsifiable limits

These statements concern the declared loss and observation experiment. They are
not claims of a new general theorem, calibrated SPH probabilities or physical
Keyhole identification. The calculation is independently integrated in
`results/NUMERICAL_CHECKS.json`.

For one reference point, standardize the joint Gaussian latent and future data.
Sufficiently summarize the vector observation by Z~N(0,1) and let
F/s = a + rho Z + sqrt(1-rho^2) U, with U independent standard normal. The
posterior decision is sign(a+rho Z). Its expected misclassification probability is

`r(a,rho) = integral phi(z) Phi(-|a+rho z|/sqrt(1-rho^2)) dz`.

Splitting at -a/rho yields `r=2 T(|a|,sqrt(1-rho^2)/rho)`. Equivalently, the
gain from observing Z is the one-dimensional integral

`Delta(a,rho) = integral_0^rho exp(-a^2/(2 t^2))/(pi sqrt(1-t^2)) dt`.

At a=0 this is asin(rho)/pi. The derivative is nonnegative. For vector Y,
rho^2=c Var(Y)^(-1)c^T/s^2 follows by Gaussian conditioning. This directly
separates reducible latent uncertainty from observation noise. A large observation
variance due only to noise can make rho smaller and the query less valuable.

**Nearest-neighbor counterexample.** Consider two unresolved independent latent
boundary cells, with the same unit loss weight. Query A is geographically nearest
but has correlation .1 with one cell, and no information about the other. Query B
has correlation .8 with that cell, also no information about the other. At equal
cost the gains are asin(.1)/pi and asin(.8)/pi. Distance does not order these
values without a suitable calibrated covariance/quality assumption. A policy can
therefore improve on blind neighbors while still losing to unrestricted SUR.

**Why local restriction is not a theorem of improvement.** If A_local is a subset
of A_all and the one-step criterion is exactly the same global expected loss,
max over A_all is at least max over A_local. This is a set-inclusion argument,
not a GP-specific convergence theorem. A gain from surprise-based restriction
must arise from a longer horizon, misspecification, or approximation/computational
effects. H1 compares regional to global under the same model; H2 compares the
representation under the same selector. If H2 helps but H1 does not, the evidence
favors changing the model while retaining global loss-aware allocation.

**A quantitative discovery bottleneck.** Suppose a wrong posterior assigns zero
gain throughout an unseen island, so only g independent uniform exploration
queries can hit it. Its continuous hit probability is 1-(1-v)^g for volume v.
On a finite pool with M unseen island candidates out of N, the exact no-hit
probability is the product over k=0..g-1 of (N-M-k)/(N-k). For an interior 4D
ball of radius .2, v=(pi^2/2)*.2^4, and g=14 gives only about 10.5% chance.
Domain clipping lowers it. This is a limiting counterexample, not an estimate of
the actual policy's hit probability: its global SUR queries can also hit the
island. No local reaction can exploit a surprise that is never observed. A good
global error can coexist with failure of the frozen island-recall guard.

**Identifiability of monitor corruption.** Let world A have physical latent f+b
and unbiased observation f+b+epsilon; let world B have physical latent f with an
unflagged monitor bias b and observation f+b+epsilon. Give identical feature,
noise, quality, missingness and cost distributions. Any adaptive policy that
depends only on paid observations has identical path distributions in A and B:
induct on the paid history; the next-query rule and conditional next-observation
law are identical. Their physical level sets can nevertheless differ. Therefore
no such policy can consistently certify both physical answers. An independent
measurement channel or verified numerical-quality assumption could break this
equivalence; extra querying of the same corrupted channel alone cannot.

**Mixture approximation is a separate issue.** Exact mixture decisions minimize
the current mixture risk, but the moment-Gaussian lookahead optimizes a surrogate
future risk. Its reference fixture has maximum absolute score error 4.64e-5 and
the same best candidate; this is one numerical fixture, not a uniform bound.
The 128/512/2048 reference-cloud fixture changed the best candidate from 2 to 3
and back to 2. Thus no converged ranking is asserted. The campaign records this
source of approximation and actual near ties; prospective numerical refinement
must use quadrature stability, not a favorable held-out scientific score.

**Same selector does not imply the same query path.** The H2 contrast changes
the model under a fixed adaptive selection formula. Its total effect can include
different predictions AND model-induced path changes. It is not a pure matched-
path prediction effect. Before TEST, add mixture RANDOM and MAXIMIN controls
with identical feature-only paths to the simple model; their prediction contrasts
are secondary diagnostics of model value. Preserve the two original primary
contrasts and the original target instead of changing success after a result.

**Adaptive acquisition does not by itself invalidate a conditional GP likelihood.**
If x_t is chosen using only the recorded past and external randomization, the
policy's conditional probability for that x_t is the same factor under every
latent-function hypothesis consistent with that history. Those design factors
cancel in Bayes' rule; likelihood conditioning on paid x remains legitimate under
the stated observation model. This does not make the paid class fraction an
unbiased estimate of a target population, or make a misspecified likelihood
calibrated. Here Q and h are fixed prospectively; no paid-prevalence threshold is
used. Applying the interface to a new physical target requires specifying its
reference distribution and decision loss again, not inheriting uniform volume
or equating a scalar-monitor contour with the canonical recorded morphology label.
