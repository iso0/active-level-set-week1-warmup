# Discrepancy-aware regional level-set learning — development version 1

18 October 2026. This choice precedes any new campaign numerical outcome.
Historical PHYS_AL/PHYS_DISCOVERY/TEMPORAL_STRUCT results are explicitly exposed
development context. The final 17 October prototype is a separate Opus-owned
reference, not a numerical success and not repeated here.

## Two mechanism hypotheses

H1 (allocation): after a reproducible local predictive discrepancy, choosing
locally by expected level-set error reduction is more useful than repeatedly
choosing the nearest neighbor. Compare the same model, global schedule and local
quota with local reaction disabled, surprise-gated, and ungated. Extra positive
collection alone is not success.

H2 (representation): a fixed smooth GP can assimilate an outsider in the wrong
way or dismiss a small island confidently. A predeclared multiscale/noise mixture
can retain competing explanations; the acquisition alone cannot repair a model
whose posterior excludes the relevant local variation. Compare models under the
SAME acquisition and use crossed controls. Neither hypothesis asserts universal
benefit; a useful model change may remove any need for local acquisition.

## Observation, target, action and cost

On a declared domain X=[0,1]^4, unknown primary latent f_0 defines
S={x:f_0(x)>h}, h=0. A paid simulation i reveals a vector
Y_ij=f_j(x_i)+epsilon_ij when channel j is available and passes declared quality
checks. All channels share one simulation cost, even if absent/invalid. A valid
reported channel may still have an undetected spatial bias; this is separately
tested, not assumed away. Canonical SPH labels are not redefined by this scalar
threshold. There is no real SPH classification experiment in this campaign.

The primary decision loss is the symmetric-difference mass
L(d,f)=integral 1[d(x) != 1(f_0(x)>0)] dQ(x), with Q uniform on the declared
feature domain. Its Bayes rule is d=1[p(f_0>0|D)>.5], risk integral min(p,1-p)dQ.
Finding high values instead maximizes a quantity such as sum 1[f(x_t)>h]; it can
spend every query inside an already-known positive region without reducing L.
An evaluator-only boundary-band error and minimum component recall guard prevent
claiming useful region recovery from a good average that misses small islands.
These guards are not selector inputs or a claim that uniform loss guarantees them.

Before each new observation save the complete paid-data/model hash, means,
latent and observation covariance conventions, component weights and the selected
point's predictive moments. Epistemic covariance describes f; noise covariance
describes conditional observation variation. A learned nugget is a working noise
model, not proof of physical randomness. Missing and QC events consume a query.

## Loss-reduction calculation

For a Gaussian working posterior at a reference point z, write a=m_z/s_z,
V_x=Var(Y(x)|D), c=Cov(f_0(z),Y(x)|D), and
rho^2=c V_x^{-1} c^T / s_z^2, clipped only for roundoff. This treats a paired
output as one vector observation. Let T be Owen's T function. Conditional on
fixed hyperparameters and Gaussian likelihood,

R_z=Phi(-|a|),
E[R_z after x]=2 T(|a|, sqrt(1-rho^2)/rho),
Delta_z=R_z-E[R_z after x].

The rho=0 limit is Delta=0; rho=1 gives Delta=R_z. The query criterion is the
average Delta over 128 label-free uniform reference points, divided by declared
simulation cost. No Monte Carlo future GP refits are needed. The Gaussian
identity is independently checked by scalar integration, not by another use of
Owen's T. We also compare its rankings with higher-resolution reference clouds
and record near ties. A finite reference cloud approximates Q; it is not exact
integration over the continuum.

For a finite Gaussian-process mixture, decisions use its mixture exceedance
probability. The inexpensive acquisition uses its joint moment-matched Gaussian
(including both within- and between-component covariance). This is explicitly a
SUR approximation; it does NOT perform exact future component reweighting.
Actual paid updates recompute all component likelihoods/weights. A separate
small-pool quadrature reference does reweight components and compares expected
loss and rankings. Any material approximation mismatch is reported and may lead
to a prospective development revision before sealed testing; numerical settings
are never chosen by held-out scientific score.

Availability is marginalized over observed paid availability patterns with a
Dirichlet prior favoring all channels present. No true unpaid availability or
quality flag is supplied. Report the primary-only and paired-output predicted
benefit separately; an independent auxiliary channel has zero theoretical
primary-level-set value in the Gaussian limit, even when it is itself uncertain.

## Limited analytical results, not a universal guarantee

For one Gaussian target with a=0, Delta=asin(rho)/pi. Hence, among equal-cost
queries, squared correlation with the unresolved boundary determines this local
gain; nearest distance or largest observation variance alone need not maximize
it. A noisy nearest point can be inferior to a farther but more informative one.
For |a|>0, differentiating the integral representation gives
d Delta / d rho = exp(-a^2/(2 rho^2))/(pi sqrt(1-rho^2)) >= 0.
This proves monotonicity in information under the stated Gaussian model, not
correctness when that model is confidently wrong. The integration measure and
correlations can favor a different point globally than locally.

Suppose the model is calibrated and a finite set of local candidates is a subset
of all candidates. An exactly evaluated one-step global risk maximizer weakly
dominates every local restriction for expected one-step global risk. Thus local
reaction needs a multi-step exploration benefit, approximation/computational
advantage, or misspecification correction; it is not automatically justified by
SUR. This is the strongest competing explanation to test, not an inconvenient
result to hide.

If two latent worlds (physical island vs no island plus an unflagged monitor bias)
induce the same joint distribution of all paid observations and QA, every policy
has the same distribution of paths in both. No observation-only discovery rule
can certify which physical world holds. Multi-output channels help only if they
provide an identifying assumption/information absent from that equivalence.

## Working model and regional policy

Simple model: zero-mean Matérn-3/2, amplitude 1, length .45, noise SD .06.
Alternative: finite prior over this covariance and an additive covariance
.8 k_.45 + .2 k_.12, crossed with noise SD .06 or .25. Equal discrete prior;
Gaussian marginal likelihood weights, no held-out hyperparameter search. All
within/between-component uncertainty is retained. For two outputs, also average
over correlation 0, +.7 and -.7, with equal discrete prior. This is a bounded
working family, not a claim of robustness to arbitrary nonstationarity or tails.

Regional acquisition keeps one global feature-random query per four post-startup
queries and one global SUR query; two remaining slots may investigate a region.
Without an episode these slots are global SUR. A paid, quality-valid pre-query
standardized residual beyond 2.5 initiates an episode. A robust scale from the
last eight global residuals (minimum four) qualifies the trigger; a scale above
2 warns of broad miscalibration and inhibits episodes, without deleting data.
The initial local radius is the distance to the 12th nearest feature neighbor,
clipped to [.15,.45]; no latent island parameter is used. The first local query
is a nearest-neighbor verification. Subsequent local slots maximize the SAME
global loss-reduction score within the region, for at most six local queries.
Require a same-sign discrepancy >=1.5 against the frozen BEFORE-anchor posterior
within two local checks; otherwise stop. Expire after twelve total choices.
No local re-seeding. Every valid paid value updates the same model as its controls.

Ungated-local control starts identical episodes on every eligible global query
without inspecting its residual; same schedule, neighborhood, maximum local quota
and loss score. Report realized local spending, since a trigger necessarily
changes realized use. A separate blind-neighbor control uses surprise gating but
nearest neighbors throughout. Their difference tests objective-aware spending.

## Closest references and scope

TruVaR (Bogunovic et al., NeurIPS 2016) supplies a strong finite-domain reference:
truncated posterior variance reduction over unresolved points, unit cost here.
Use beta^.5=3 and our frozen eta_1=1, r=.5, delta=.1; permit reopening as its
supplement recommends under mismatch. Finite-pool/no-requery restriction is named.
The theorem assumes a known correct GP/noise; no guarantee is transferred here.
[Reference (PENDING_ARCHIVE)](../../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-f6f0532e24beaa18)

Multiscale GP-LSE (Shekhar/Javidi, AISTATS 2019) refines spatial partitions when
uncertainty is below within-cell variation. It addresses continuous query access
with regularity/confidence assumptions. Our fixed pool cannot query arbitrary cell
centers or replicate them. Include a labelled finite-pool tree adaptation and
document its departures; do not present it as their exact theoretical algorithm.
[Reference (PENDING_ARCHIVE)](../../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-bcdea8c276695e12)

CA-SMART (Raihan et al., 27 March 2025 preprint) already combines surprise, local
verification and global coverage. Its 95% predictive-interval rule motivates an
explicit nearest/global adaptation, not a novelty claim for that combination.
Its flat-prior CAS normalization is not silently treated as a unique proper KL.
[Reference (PENDING_ARCHIVE)](../../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-c64a0b446eb98572)

Hübotter et al. (NeurIPS 2024), Transductive Active Learning, studies information
and variance reduction at a target set. Its VTL criterion is an integrated
variance comparator, distinct from maximizing single-point variance. We include
VTL with the same quarter-global-random schedule and paired-channel contract as
SUR under both models. Its GP/noise or RKHS/sub-Gaussian assumptions do not cover
arbitrary unflagged monitor bias. The author's repository is
[Reference (PENDING_ARCHIVE)](../../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-7261d3bb59c7aa8f) and the primary paper is
[Reference (PENDING_ARCHIVE)](../../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-16038a7ac5cccc54) . Our implementation uses the Gaussian variance
identity; it does not import the author's JAX safe-BO experiment.

Lyu/Binois/Ludkovski's noisy level-set comparison (2018 preprint, 2021 journal)
directly studies robust metamodels and SUR under non-Gaussian noise. This is closer
to our objective than maximizing a BO function. [Reference (PENDING_ARCHIVE)](../../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-6321c9c50cd3c8e4)
Ngo/Nguyen/Gupta (ACML 2024) adapt a transferred prior locally; we have no source
task and do not assume their transfer guarantees. [Reference (PENDING_ARCHIVE)](../../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-0e346db97912b891)
The warped multi-output time-series model (Kaiser et al., 2017/2018) is context for
Opus, not a duplicated fit: [Reference (PENDING_ARCHIVE)](../../../../../../../docs/research/ARCHIVE_MANIFEST.md#pending-b6994fe6c88f6b83)

Contribution under test: a reproducible decomposition of local response, a
loss-aware query criterion and model-family adequacy under a strict paid contract.
The component theories are established. Any claim of a new useful combination
requires the independent tests and prior-art comparison, not its name.

Pre-freeze implementation note: the conditional island-center proposal spans
[.05,.95] in nuisance coordinates and [.60,.95] in coordinate 0, permitting
maximin startup points near the domain edge to belong to a small island.
The radius is unchanged. Domain-truncated island volumes are retained/evaluated;
seen versus unseen is a controlled generator condition, not a selector input.
Narrower center support was corrected before any numerical campaign outcome.
