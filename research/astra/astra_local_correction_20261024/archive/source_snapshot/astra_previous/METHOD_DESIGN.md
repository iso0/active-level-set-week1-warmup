# Representation versus planning: prospective construction

Recorded 20 October 2026, before new numerical outcomes. The old 336-world TEST
is now exposed development evidence. Its completed files and clock are immutable.
This is a new, bounded synthetic investigation, not physical confirmation.

## Two mechanisms, one objective

At a public input x in [0,1]^4, one paid run returns the available monitor values.
The primary controlled observation is y=f(x)+epsilon, with conditional zero-mean
Gaussian noise in the working model. Heavy-tail, heteroskedastic and coherent-bias
worlds deliberately violate this assumption. Missing/invalid observations retain
their paid cost. The target is the sign of the *latent* f at threshold zero under
the uniform reference distribution Q. Decisions use the current model's
P(f(x)>0|D)>1/2, with ties assigned negative. Loss is integrated sign error:

    L(d,f)=integral 1[d(x) != 1[f(x)>0]] dQ(x).
    R(D)=integral min(p_D(x),1-p_D(x)) dQ(x).

This is not maximum-value search, rare-island recall, canonical Keyhole BA or a
physical identification guarantee. Island/boundary masks belong to evaluation.
Uniform error may rationally sacrifice a small region. Keeping regional harms
visible is necessary even when an overall error contrast improves.

The factorial hypotheses are (R) insufficient representation after a paid local
observation, and (H) an investment that pays off only after a second observation.
Neither is presumed correct. A finite-pool island absent from the candidate set
cannot be queried. Learning after a hit does not estimate first-hit search value.

## Coherent paid-anchor local representation

The background is the preserved structural finite GP mixture, including its
isotropic, multiscale and coordinate-short covariance alternatives and its two
noise scales. In the local model write f=g+delta with independent GP priors.
Delta has a spike at zero and a small, fixed bank of compact-support covariances:

    k_delta(x,z)=tau^2 (1-r)_+^5 (5r+1), r=||x-z||/R.

This Wendland covariance is positive definite in four dimensions. Support,
amplitude and spike weights are declared before numerical development. Posterior
component probabilities use one joint marginal likelihood of the paid values.
No observation that selected a location is entered a second time.

Conditional on a component, with C=K_g+K_delta+Sigma_noise,

    E[delta(x)|D]=k_delta(x,X_paid) C^-1 y,
    Cov(delta(x),delta(z)|D)=k_delta(x,z)-k_delta(x,X_paid) C^-1 k_delta(X_paid,z).

The paid inputs are the posterior representer anchors. Local support controls
which anchors affect x, and posterior shrinkage/mixture evidence controls their
strength. A null component can remain or regain weight. This construction uses
all paid startup observations without inventing a pre-start prediction.
It is an alternative to choosing a bump center after inspecting y and then
pretending that its data-dependent prior was fixed beforehand. It does not claim
one physical anomaly per anchor, and the kernel remains stationary within each
component; additive local support is not arbitrary nonstationary identification.

Adaptive paid locations do not require entering their selected responses twice:
the sequential design probabilities, conditional on the previously observed
history, carry no additional unknown-f factor in the likelihood. The common
shortlist uses a leave-one-out residual to propose two neighbors of a paid input.
That residual is a proposal heuristic, not a calibrated p-value or an honest
prequential forecast: later adaptively selected locations may themselves contain
information about a held-out value. Startup handling is justified by the fixed
additive prior above, not by claiming these residuals were available before startup.

A learned ARD Matérn GP is a strong separate control. Its lengthscales, amplitude
and noise are learned by marginal likelihood with deterministic multiple starts.
Finite optimizer convergence and plug-in hyperparameter uncertainty are reported.
Coordinate-short alternatives cannot certify rotated-anisotropy robustness.

## Paid two-step value

With a common protocol-defined shortlist S(D) and paid observation Y_i:

    V1(i,D)=R(D)-E[R(D+i,Y_i)].
    V2(i,D)=R(D)-E_Yi[min_{j in S(D)\{i}} E_Yj|Yi[R(D+i,Y_i+j,Y_j)]].

Equivalently V2=V1+E[max_j V1(j,D+i,Y_i)]. The second index is contingent on
the first result, but its observation is charged as a second query. Only the
first query is executed; the actual paid posterior is then updated and replanned.
At one remaining query the rule reduces to V1. When the next scheduled slot is
global random exploration, the second-stage action is that lawful scheduled
random choice, not an unconstrained fictitious optimum.

All horizon comparisons share the actual posterior, decision, loss, observations,
reference points, shortlist, global exploration and tie handling. The working
lookahead uses a Gaussian matched to full mixture means and covariance, including
within- and between-component uncertainty. Actual updates reweight the finite
mixture. Future Gaussian conditioning is a declared approximation to future
mixture reweighting, not exact Bayesian mixture planning. Independent small-mixture
quadrature measures this discrepancy separately from integration error.
The paid-data availability estimate is held fixed within hypothetical updates;
actual missingness counts update it after each paid run. Thus lookahead also
uses a plug-in missingness model, independent of x and latent values. Main
controlled fits use one scalar monitor; a richer joint-output posterior requires
an explicit compatible multi-output integration, not silently ignoring a new
channel while claiming its information was valued.

For reference f_r and future y_i under this working Gaussian, let
a_r=m_r/sqrt(v_r), rho_ri^2=c_ri^2/(v_r*(v_i+noise_i)).
One-step error reduction is

    Phi(-|a_r|)-2*T_Owen(|a_r|,sqrt((1-rho^2)/rho^2)).

It vanishes at zero information. Noise enters observation covariance exactly
once, while latent sign probabilities use latent covariance. Gaussian conditioning
updates all reference/candidate means and their covariances. Two-step integration
uses deterministic Gauss-Hermite refinement, bounded by a declared maximum order;
near-ties remain ties at a fixed tolerance. Convergence of quadrature establishes
only numerical convergence for this working posterior.

## Analytical distinction and limitation

In a calibrated finite posterior, extra information has nonnegative expected
Bayes value because ignoring it is always an available decision. A two-step
policy can nevertheless select a first action with smaller V1. Example: a latent
switch determines whether a local second measurement is informative; a switch
measurement alone changes no sign decision but changes the best second action.
An independent exhaustive small-state reference will compare contingent policies.

This inequality does not prove realized accuracy improvement under a misspecified
GP, a restricted shortlist, unknown noise, or expensive computation. A compact
component can fit structured monitor corruption as confidently as a real island.
If both induce the same law of paid observations, no selector can distinguish
them without an additional legitimate channel or identification assumption.

## Established methods and actual contribution

SUR for sign loss, additive GP covariance, finite Bayesian averaging, Wendland
compact support, learned ARD and bounded lookahead are established. The contribution
being tested is their controlled integration for paid-startup local structure and
the matched representation-by-horizon discriminator, including search and compute
cost. No novelty claim is made for combining local/global exploration or for
two-step planning itself. See LITERATURE.md for primary sources and code context.

The application adapter must accept public inputs and paid-only observations,
record pre-query posterior/hash, variance convention, quality and cost, and keep
all outputs of a run together. The later 541-run physical pool has no free archive
or OLD/NEW routing. A different downstream loss needs a separate validated adapter.
