# Why a compact component may disappear — post hoc interpretation

POST-HOC EXPLORATORY INTERPRETATION — NOT A NEW CONFIRMATORY EXPERIMENT.
Written after frozen TEST inspection on 21 October 2026. No new model, prior,
selector or numerical experiment is introduced. The one additional tested
mechanism was already used by the mixture-aware h1 control.

The implemented local prior adds a stationary covariance with marginal variance
tau^2 everywhere. Its *correlation* has compact support. All paid locations,
including startup, are legitimate posterior representers; no selected response
is counted twice. This does not make the component a spatially gated variance
model. The prior must explain all paid data jointly before a high local posterior
mean can help a nearby decision. Model expressibility and posterior support at
the available budget are different properties.

Consider a restricted analytical example with known background, residual vector
e at n well-separated paid inputs, known observation variance sigma^2, and
K_delta=tau^2 I because these inputs lie beyond the compact support. Compare
M0: e~N(0,sigma^2 I) with M1: e~N(0,(sigma^2+tau^2)I), equal model prior odds.
Writing r=tau^2/sigma^2, direct Gaussian density division gives

    log BF10 = -n/2 log(1+r) + r/[2(1+r)] ||e||^2/sigma^2.

If one residual has mean a and the others mean zero, with independent variance
sigma^2 around those means, then

    E log BF10 = -n/2 log(1+r) + r/[2(1+r)] (n+a^2/sigma^2).

Thus positive expected log evidence requires

    a^2/sigma^2 > n [(1+r)/r log(1+r) - 1].

The bracket is positive for r>0. An isolated anomaly must overcome a complexity
cost that grows with the number of otherwise ordinary observations. A prior
whose *variance* is localized to one known location would pay the corresponding
one-location cost, but an unknown location entails its own legitimate selection/
prior cost. This is not permission to select the true island for free. Non-equal
model prior odds add their log odds to the expression.

This exact restricted calculation establishes possibility, not the historical
cause of every weight change: the actual fitted background is uncertain, paid
points are correlated, two noise scales compete, the prior mixes lengthscales,
and real anomalies need not be independent or Gaussian. A local component can
also absorb noisy or corrupted data without improving the latent boundary.

The completed evidence is consistent with, but does not prove, the mechanism:
local/h1 mean component weight on large islands is 0.003430 at B32 and 0.0000315
at B48; on small islands 0.002779 to 0.0000231. Most common-prefix local/existing
paths coincide. Rotated worlds retain mean local weight 0.217 at B48 but remain
near chance, showing that component activation is insufficient. These are
cached descriptive diagnostics in FINAL_REVIEW_FACTS.json. The old campaign's
inactive surprise gate and this campaign's posterior shrinkage are different
mechanisms and must not be described as the same failure.

There are two distinct alternatives to a representation explanation. First,
uniform integrated sign loss assigns little mass to a tiny island; a useful
local posterior may still have little global expected query value. Second, a
six-candidate bounded plan can miss useful actions, and moment matching can
misvalue those it includes. Mixture-aware h1 was the prospectively registered
test of a combined distributional-approximation mechanism. It did not yield
the general improvement; it is not a weight-only causal ablation. The many
h2 near ties and fallbacks limit statements about exact two-step planning.

The strongest next discriminator is a single prospectively specified localized-
variance representation against the current model, first on identical paid
prefix predictions, then with the same cheap one-step selector and uniform loss.
Use fresh worlds and lawful hits, retain unseen islands/noise/corruption controls,
and freeze predictive and regional metrics before seeing outcomes. A prediction
gain that does not translate into local acquisition gain favors the loss/
shortlist explanation; no prediction gain leaves representation unresolved.
This is a future proposal, not another run under the completed allowance.

In any calibrated posterior, extra observations cannot increase *expected*
optimal Bayes risk because ignoring them is an available action. This does not
guarantee realized accuracy under model error, nor make uniform risk a rare-
region safeguard. If a real island and monitor corruption induce the same paid
observation law, no acquisition over that channel can distinguish them without
additional legitimate information. None of these arguments is a new general
sample-complexity theorem. Additive GP inference and marginal-likelihood model
selection are established; see LITERATURE.md and the original primary sources.
