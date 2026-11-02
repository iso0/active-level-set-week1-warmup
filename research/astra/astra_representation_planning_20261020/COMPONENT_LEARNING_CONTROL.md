# One additional mechanism: future component learning

Prospective note, before any new TEST realization. This is the single extra
mechanism permitted by the owner, motivated by an independent numerical
counterexample rather than a scientific-score search.

In `SECONDARY_NUMERICAL_CHECKS.json`, exact Gaussian-component updates followed by
bounded quadrature rank the one-step candidates 1,2,0. The moment-Gaussian rule
ranks 2,1,0. Two-step chooses 1 under both calculations. Thus an apparent
two-step improvement can partly repair a one-step approximation error; it need
not demonstrate a genuine long-horizon investment under the original mixture.
The maximum one-step score discrepancy is 0.01424 and two-step discrepancy 0.02049.
The mixture reference's 33-to-65 refinement change is 0.000469, not zero; these
are numerical mixture references, not exact posterior integrals. This materially
limits attribution of the main Gaussian-moment horizon contrast.

Implement one additional **mixture-aware one-step control** using the unchanged
posterior, paid decisions, six-point shortlist, loss and exploration cadence.
For future scalar y at i, update weights

    w_c(y) proportional to w_c Normal(y; m_ci, v_ci + noise_ci),

and condition each Gaussian component using its own covariance. Evaluate the
posterior mixture sign probability, then its Bayes error, then integrate over y.
This is ordinary Bayesian mixture decision theory, not a novelty claim.

The implementation uses deterministic importance Gauss-Hermite quadrature under
the moment-matched predictive Gaussian, with exact predictive mixture density
ratios. Orders 17/33/65/129, score tolerance 1e-4, total-mass tolerance 1e-4,
two successive refinements and a finite cap. Report mass error, effective
quadrature nodes, maximum normalized weight, rank changes and fallbacks. Effective
quadrature-node count is not iid Monte Carlo ESS or a confidence guarantee.
An unaccepted integral falls back to the unchanged moment one-step selector.
An accepted numerical tie uses its moment score within the tied set.
For action selection, a stable winner across three consecutive orders with
gap greater than four times the last two refinement changes plus 2e-5 may also
be accepted; absolute score convergence is recorded separately. This is an
empirical rank-resolution criterion, not a mathematical quadrature bound.
The dense root-partitioned reference shows why the distinction matters:
order-129 maximum absolute error is 0.000142, while all four orders select the
correct mixture winner with a gap exceeding 0.003. Its dense reference estimated
errors are below 6.1e-11. A normalized weight sum alone would miss score error.

Components may be omitted only when their **total** posterior mass is <=1e-8.
For loss bounded in [0,1], replacing the joint mixture by its renormalized
retained mixture changes any expected loss by at most that mass (total variation);
taking the infimum over decisions preserves the inequality. Hence a
before-minus-after Bayes-risk reduction changes by at most twice that mass.
This bound controls component truncation, not quadrature or model misspecification.
All retained components reweight under the hypothetical outcome. Store the full
untruncated component snapshot before the real query.

Use at most eight additional DEV timing trajectories, keeping the total at 40.
The independent toy is checked against dense adaptive one-dimensional integration
and component-stratified quadrature before TEST. If affordable, include this
control prospectively in the common-prefix panel. No further alternative,
prior search or threshold sweep is opened by this note.

The anticipated common-prefix panel becomes eight arms (the six existing arms
plus existing/local mixture-aware h1); end-to-end retains the eight learned
policies. Feature-only RANDOM/MAXIMIN search paths can separately report paid
first-hit coverage without claiming learned classification metrics. Final counts
and a finite fantasy-state envelope are set in the TEST JSON freeze after
numerical/timing validation, before any TEST outcome. The clock and slots do
not change.
