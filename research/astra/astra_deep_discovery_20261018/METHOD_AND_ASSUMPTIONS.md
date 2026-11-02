# Final implemented method and its limits

This is the authoritative short description of the **frozen v2** implementation.
The historical DESIGN_V1.md remains unchanged. Amendment 02 changes its
reference cloud from 128 IID points to 1,024 fixed scrambled Sobol points and adds
the boundary gate and structural model; Amendment 03 adds equal-share controls.
All parameters were fixed before v2 TEST. Results did not select this definition.

On \(X=[0,1]^4\), let \(S=\{x:f_0(x)>0\}\). The target distribution \(Q\) is
uniform feature-space volume, approximated by the public reference cloud; the
independent evaluator uses 2,048 uniform points. The candidate pool has 512
public feature vectors. Startup is eight feature-only maximin IDs. One purchase
reveals all available outputs at one new ID; no repeats. A missing or invalid
channel remains paid. The evaluator's island, boundary band, function identity,
seed, future quality and hidden values are unavailable to the selector.

The working observation model is \(Y_j(x)=f_j(x)+\epsilon_j(x)\), with conditionally
independent Gaussian observation errors within each fixed component. The true
controlled worlds also include heteroskedastic noise, heavy tails, spatially
varying scales, conflicting output relationships and unflagged monitor bias.
The latter is a channel-definition failure, not independent measurement noise.
No general robustness theorem is assumed for these departures.

For symmetric sign loss,
\[
L(d,f)=\int 1\{d(z)\ne1[f_0(z)>0]\}\,Q(dz),\qquad
R_t=\int\min(p_t(z),1-p_t(z))\,Q(dz),
\]
the Bayes action is \(d_t(z)=1\{p_t(z)>1/2\}\). Mixture exceedance probabilities
are computed by averaging component probabilities, not thresholding a mean
depth or using the fraction of paid positives. This is a continuous latent-monitor
experiment. A canonical Keyhole label, a loss-optimal decision contour, and a
physical morphology boundary remain different targets.

The one-step ideal value for an available output pattern \(M\) is
\[
\Delta_t(x)=R_t-\mathbb E_{M,Y_M(x)\mid D_t}[R_{t+1}].
\]
For a single joint Gaussian posterior define
\(a=m_z/s_z\), \(V=\operatorname{Var}(Y_M(x)\mid D_t)\),
\(c=\operatorname{Cov}(f_0(z),Y_M(x)\mid D_t)\), and
\(\rho^2=cV^{-1}c^\top/s_z^2\). Then
\[
\Delta_t(z,x)=\Phi(-|a|)
-2T\!\left(|a|,\frac{\sqrt{1-\rho^2}}{\rho}\right).
\]
Here \(T\) is Owen's T function; the limits are zero at \(\rho=0\) and current
Bayes risk at \(\rho=1\). At \(a=0\), gain is \(\arcsin(\rho)/\pi\).
The derivative is
\[
\frac{\partial\Delta}{\partial\rho}
=\frac{\exp[-a^2/(2\rho^2)]}{\pi\sqrt{1-\rho^2}}\ge0.
\]
These are conditional Gaussian identities, not misspecification guarantees.
Maximizing the number of positive paid observations is a different objective:
it can spend every query in a known positive region and leave this loss unchanged.

For two scalar outputs, additional explained target variance from output 2 given
output 1 is
\[
\frac{(c_2-c_1V_{11}^{-1}V_{12})^2}
{V_{22}-V_{21}V_{11}^{-1}V_{12}}\ge0.
\]
An uncertain auxiliary channel has no primary-boundary value when this
conditional covariance is zero. All channels cost one simulation. The reference
implementation learns availability-pattern probabilities from paid observations
with a fixed Dirichlet prior (2 for all-present, .25 for each other pattern).
This assumes availability is unrelated to location/value; it is not valid for
arbitrary informative missingness.

The simple model has one zero-mean, unit-amplitude Matérn-3/2 component
(length .45, noise SD .06). The mixture crosses long versus additive short/long
covariance with noise SD .06/.25 and, for paired outputs, correlations 0/±.7.
The structural bank adds four coordinate-anisotropic alternatives
(length .08 in one coordinate, 1.2 in the others); half of the kernel prior mass
stays on the original alternatives. It has 12 scalar or 36 paired components.
No hyperparameter optimization or pruning occurs.

Actual conditioning and marginal-likelihood component reweighting are exact
within this finite working model, subject to floating-point stabilization.
The acquisition instead moment-matches the joint mixture, retaining within-
and between-component covariance, and applies the Gaussian identity. Thus it
omits part of future component reweighting and is not exact mixture SUR.
The separate scalar quadrature audit reweights future components and bounds
integration error on its screened states; it cannot certify model truth.
Reported nominal .90 coverage uses moment-normal latent intervals, not exact
mixture quantiles. WhiteKernel predictive variance must not have its noise
added twice; the saved independent reference verifies this convention.

The boundary gate requires an old sign probability ≥.75 and an opposite sign
probability ≥.90 after an approximate local Gaussian update with the new paid
value. The same-direction corroboration thresholds are .60/.80 against the
**frozen pre-anchor posterior**. Broad standardized-residual inflation inhibits
episodes; it does not delete observations. Regions use a public 12-neighbor
radius clipped to [.15,.45]; episodes have at most six local queries and expire
after 12 choices. The first local purchase is a nearest verification, later
ones maximize the same global SUR score inside the region. If no episode is
active, those slots revert to global SUR. Startup observations do not create
retrospective surprise episodes.

For a correctly specified posterior and exact one-step global objective,
\(\max_{x\in A_{\rm local}}\Delta_t(x)\le
\max_{x\in A_{\rm all}}\Delta_t(x)\). A local restriction therefore needs
multi-step value, computational advantage or correction of model error.
The [exact rational example](LOCAL_VALUE_ANALYTIC_CHECK.md) shows both benefit
and harm: with \(q=.01,w=.5,\eta=.05,g=.003\), greedy two-global-query risk is
.005, but adaptive local-first risk is .0033135. Raising noise to .30 or reducing
region mass to .01 favors global queries. One case has tied optimal first
actions; the original uniqueness error and corrected reference are retained.
This is established finite Bayesian decision theory, not a new universal result.

If “physical island” and “no island plus coherent monitor bias” induce identical
distributions of all available observations and QA, every adaptive policy has
identical history distributions in both. No selector identifies which world is
physical without additional justified information. Likewise a trigger cannot
react before a first observation. The familiar \(1-(1-v)^n\) discovery probability
only describes IID uniform draws, not an arbitrary adaptive policy.

The frozen evaluation target is sign error ≤.08, boundary-band error ≤.25,
island recall ≥.70 where defined, and both class recalls ≥.85 where defined,
at **two consecutive four-query readouts**. Charge the second readout and
censor nonattainment at B64. These evaluator-only requirements diagnose failures
of uniform-loss learning; the acquisition does not know their hidden masks or
guarantee them. All policies continue to B64 after confirmation. This is an
evaluation hitting time, not a deployable oracle-informed stopping rule.

The main acquisition/decision entry is `acquisition.sur_scores(Snapshot)`;
the controller is `policy.Policy.ask/tell`. All component techniques are
established; the implementation, strict contract and controlled separation of
allocation/representation are the contribution evaluated here. See the
[primary-source comparison (RESTRICTED)](../../../docs/research/ARCHIVE_MANIFEST.md#rec-pkg-0223) before making
novelty or state-of-the-art claims.
