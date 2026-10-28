# What the revised method learns, and what it cannot establish

This supplements the frozen v2 amendment; it does not change any selector or
endpoint. Continuous monitor level-set learning, canonical recorded-label
classification, and a physical morphology boundary remain different tasks.

For a uniform reference distribution Q on the four-dimensional input cube,
the scientific latent target is S={x:f0(x)>0}. Under symmetric difference loss,
R(d,f)=integral 1{d(x) differs from 1{f0(x)>0}} dQ(x), the posterior Bayes action
is d(x)=1{p(x)>1/2}, and its posterior risk is integral min(p,1-p) dQ. The binary
label in the SPH project is not redefined as this synthetic latent sign. An actual
monitor threshold, its observation window and noise model must be specified
before this interface has a physical interpretation.

## Why the query score targets a boundary

For a Gaussian conditional posterior, let a=m/s and
rho²=c V_Y^{-1} c^T/s², where V_Y contains latent uncertainty plus the available
outputs' observation-noise covariance. The expected sign-error reduction at a
reference point is

    g(a,rho) = Phi(-|a|) - 2 T(|a|, sqrt(1-rho²)/rho).

The endpoints are g(a,0)=0 and g(a,1)=Phi(-|a|). At a=0, g=asin(rho)/pi;
for 0<rho<1, dg/drho=exp[-a²/(2rho²)]/[pi sqrt(1-rho²)]. Thus covariance
reduction matters most near an uncertain threshold. Maximizing expected response
m(x), or even Var(f(x)), is a different objective. We average g over the fixed
public Sobol Q cloud and the paid-only missing-channel model. We do not weight
points by a hidden island, short-K, q20, or an evaluator's boundary membership.

The formula is exact for the stated Gaussian conditional model and finite
reference integration. Moment matching a non-Gaussian posterior mixture changes
the acquisition objective: it includes within/between component covariance but
does not simulate the observation-dependent future component reweighting. The
actual next fit does reweight components. Independent mixture quadrature measures
this approximation on a small fixture; convergence on that fixture cannot prove
accuracy on every scientific trajectory. Snapshot weights and near ties are
logged to make that limitation auditable.

For primary and auxiliary outputs, the additional variance reduction from paying
the auxiliary channel, conditional on the primary, is

    [c2 - c1 V11^{-1} V12]^2 / [V22 - V21 V11^{-1} V12].

It is nonnegative for a valid Gaussian covariance, and zero when the auxiliary
has no remaining conditional relation to the primary target. This distinguishes
auxiliary prediction improvement from primary-boundary information. In a
misspecified model a large predicted gain can still be wrong; the paired-versus-
primary valuation controls expose that. Availability frequencies assume missing
channels independent of x and latent values; that assumption holds in the frozen
missing-channel generator, but is not established for real monitor failures.

## A concrete reason to revise the surprise gate

Take prior f(x)~N(-.4,.09), independent noise variance .0036, and observed y=.2.
The standardized prediction residual is about 1.96: a 2.5-sigma value-surprise gate
does not react. Yet the prior positive probability is about .091 and the paid
posterior positive probability is above .99. This is a reversal of the level-set
decision, even though the continuous outcome is not an extreme predictive tail.
It motivates the fixed 0.75/0.90 probability gate, not a fitted optimal threshold.
Raising the noise variance to .5 removes the confident reversal. The precision-
matrix reference in `numerical_checks.py` independently checks both cases.

If p is a calibrated true posterior and the updated probability of a new sign
is at least .9, its conditional posterior error is at most .1. That is a
conditional Bayesian statement, NOT a repeated-testing false-discovery guarantee
or a calibration theorem for our moment approximation. Under a true Gaussian
model the law of total expectation also gives
Pr(p_after>=.9 | D) <= p_before/.9 for a previously negative point. A local episode
can therefore arise legitimately under a correct model; its occurrence alone
does not prove misspecification. We log the pre-query state and require a separate
paid corroboration, retain noise/corruption controls, and cap expenditure.

## Limited proposition: local response has an opportunity cost

For fixed current posterior, Q and one-step loss, let A be every unpaid candidate
and B subset A be the local neighbourhood. Then max_{x in B} G(x) <= max_{x in A}
G(x), simply by set inclusion. Under exact one-step Bayes evaluation, a mandatory
local restriction cannot improve the current globally optimized score. Likewise,
nearest-neighbour verification need not be the most informative boundary query.
A later empirical gain must involve horizon effects, model misspecification,
calibration or acquisition approximation, rather than overturning this inequality.
The two controlled mechanisms deliberately keep these interpretations separate.

An observation-noise counterexample makes this concrete. Two candidates have the
same target covariance but noise variances t_A > t_B. The more distant B can have
larger c²/(v+t) and hence higher g than the nearest A. Repeating a blind local
response around independent outliers spends budget with no shared latent signal.
Conversely, correlated residual structure plus an appropriate spatial kernel can
let the first paid correction change many nearby sign probabilities. Whether that
benefit outweighs displaced global queries is empirical here, not guaranteed.

## Discovery limits and the joint attainment guard

Uniform symmetric-difference loss can prefer ignoring a tiny region. A classifier
which misses an island of volume .01 but is perfect elsewhere has only .01 error
and zero island recall. Our unchanged joint attainment endpoint requires island
recall, both class recalls and boundary-band error, confirmed at two successive
budgets. It prevents calling such a solution successful discovery or query
savings. It does NOT secretly supply those evaluator-only subsets to acquisition,
nor make one-step global error minimization an exact optimizer of that joint
endpoint. This remaining objective mismatch must be reported if it matters.

Until a query enters a region B, two functions identical outside B generate the
same observations there. No gate can respond to a first hit it never obtained.
For iid uniform exploratory queries and region mass v, the first-hit probability
after n such queries is 1-(1-v)^n. Other adaptive queries may also hit B; the
random-floor formula is not their total probability or a universal lower bound
for geometry-conditioned worlds. Seen/unseen and size/distance controls measure
this bottleneck separately from learning a boundary after a hit.

Finally, if one world has physical function f+b and unbiased monitors, and another
has physical f with unflagged monitor bias b, their paid observations can have
identical distributions. By induction, every adaptive ask/tell history and query
distribution then agrees. The physical level sets may differ. No acquisition
rule can distinguish these worlds from that channel alone; independent quality
information or a justified additional measurement changes the information
contract. The corrupted-monitor family is retained precisely to expose this
limit. A monitor contour may still be learned accurately without identifying a
physical regime boundary.

SUR, Bayesian model averaging, anisotropic kernels and surprise/local/global
sampling are established ideas. The contribution under evaluation is their
explicit paid-output implementation, the decision-linked gate, controlled
separation of allocation and representation, and an auditable negative/positive
mechanism map. No general new convergence theorem or SPH superiority is claimed.
