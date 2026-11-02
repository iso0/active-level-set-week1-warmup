# Prospective controlled program v1

Registered before generating or fitting any campaign world. Model and acquisition
are specified in DESIGN_V1.md and frozen source hashes. This protocol is development
version 1; final evaluation cannot start until a separate test-release record.

Domain: [0,1]^4, uniform target Q. Each realization has 512 candidates, 2048
independent evaluator features and 128 independent public reference features.
Features and reference weights are label-blind. Startup is a shared 8-point
feature-maximin path. For the seen/unseen island conditions the GENERATOR conditions
its random island center on this path; this is a controlled starting condition,
not a claim that a natural feature-only design guarantees either. Every initial
query counts. Pool density and rare-component counts are retained, including zero
pool hits. No seed is replaced because a world is difficult or a target is missed.

Fourteen families: smooth boundary; small/large islands with seen/unseen starts;
anisotropy; local change of scale; heteroscedastic noise; heavy-tailed noise; null
without an island; spatially correlated unflagged monitor bias; shared auxiliary,
locally conflicting auxiliary and missing-channel worlds. Random orientations,
phases, centers and observation noise vary by realization. These are analytic
functions, not samples from the fitted GP. No family name, seed, center, radius,
noise realization, mask, latent values or evaluator metrics enters a selector.

DEV: 3 independent realizations per family, seed bases 810000, 810001, 810002
with family offset 1000*k. B8..B40, evaluation every 4 queries (and final).
TEST: 24 new independent realizations per family, seed bases 920000..920023
with family offset 1000*k. B8..B64, same readout rule. Test outcomes are not
generated/read for development; TEST_RELEASE.json requires a model/protocol/code
freeze and a recorded development judgment. A model revision keeps the same
unopened final realization list unless a bug requires a declared fresh test set.

Core arms, all with identical world/startup/cost:

| Model | Selectors |
|---|---|
| Simple fixed GP | random, maximin, maxvar, straddle, posterior margin, TruVaR reopening adaptation, multiscale tree finite-pool adaptation, CA-SMART nearest/global adaptation, global SUR with 1/4 random schedule, regional SUR, ungated local SUR, surprise-blind-neighbor, VTL with the same 1/4 random schedule |
| Multiscale/noise mixture | straddle, scheduled global SUR, regional SUR, ungated local SUR, surprise-blind-neighbor, scheduled VTL |
| Mixture, multi-output families only | primary-only SUR as control for paired-output SUR; SAME two-output fitted model |

The regional/global contrast holds the model, decision, output contract and global
schedule fixed. Ungated local uses the same 1/2 local-slot allocation, neighborhood
and six-query ceiling without a surprise condition; realized use is reported and
is not falsely called exactly matched after gating. The blind-neighbor control
tests spending locally by distance instead of the loss criterion. Pure baseline
arms have their native schedules; those contrasts are whole-policy comparisons.

The finite-pool tree and CA-SMART adaptations are transparently approximate
references, not asserted replicas of unavailable author code. TruVaR implements
the published truncation/epoch formula, with the supplement's reopening variant.
No author's theorem is claimed under a wrong kernel or no-repeat candidate pool.

Primary fixed-budget loss: uniform symmetric-difference error at final B64.
Secondary: its AULC B8..64; boundary-band error on |f|<=.10; both recalls/BA;
component/island recall and spatial coverage; Brier/log loss; primary and auxiliary
MAE/RMSE and 90% coverage; first valid island query and later third-island query;
positive count; quality/missing cost; triggers/local spending; model weights;
query-selection and fit/evaluation seconds, CPU seconds and process peak RSS.
Prediction is from the paid model only; evaluator outcomes never affect stopping
of a trajectory. Even after target attainment the full frozen budget is run.

ONE joint target: global error <=.08, boundary-band error <=.25, island recall
>=.70 when present, and each existing class recall >=.85. Empty conditional
subsets are reported N/A, never used to remove a world. Confirmation requires
two consecutive readouts; charge the SECOND budget. First hit at startup counts.
Unreached targets are right-censored at the actual horizon, with separate event
flags; never invent a B68 success. Report restricted query burden min(T,64),
attainment probability, and paired restricted-burden differences. Claim query
savings only with at least 80% attainment in both compared arms plus a positive
paired 95% lower bound on reduction; fixed-budget quality remains visible if this
condition fails. No measured physical runtimes means no claimed simulator-hours
saved. Compute overhead is reported separately from simulation query count.

Primary confirmatory comparisons (two hypotheses): mixture regional vs mixture
scheduled global; mixture regional vs simple regional. Pair within function/noise
realization. Stratify bootstrap by family, equal family weight; resample whole
realizations (not readouts or folds), 10000 draws seed 20261018. Use Holm adjustment
for the two primary randomization tests; family/other-arm intervals are descriptive
and labelled. Report all per-family effects and failures. Missing failed units
prevent a full-suite superiority verdict; no successful-case-only average.
Two function realizations are not enough; test uses 24 per family. This supports
claims about the declared synthetic generator distribution, not universal or SPH
superiority. Any final test exposed during repair becomes development evidence.

Numerical acceptance precedes comparisons: Gaussian error-reduction identity vs
independent quadrature; GP moments vs dense conditioning; additive WhiteKernel
variance convention; paired covariance/value identity; exact-mixture quadrature
versus moment approximation; reproducible paths and resume. Numerical tolerances
are absolute 1e-8 for exact identities, 1e-6 for scalar adaptive integration;
record the moment approximation discrepancy rather than passing it as exact.
Reference-cloud sensitivity uses the same analytical fixture at 128/512/2048
points; do not choose a setting using the scientific held-out score.

Finite initial envelope: 700000 top-level controlled model requests, 2000000
component solves, plus 200 independent numerical-reference requests/2000 solves,
all within the SAME absolute 48-hour deadline and two Astra slots. Request and
component costs are reserved before each fit. DEV v1 has 807 trajectories; final
v1 design has 6456. Nominally 394623 controlled requests and 1023966 component
solves, leaving explicit room for references and prospective development revisions.
These are upper bounds, not pressure to use the full budget.
Additional versions require a prospective amendment with its counts, motivation,
development exposure and remaining budget. The old 650-solve reference is neither
charged here nor repeated by Astra. No unrecorded rescue ladder or resampling.

Crashes, numerical failures, censored targets and QA failures remain in per-unit
records. Atomic per-query checkpoints preserve paid paths. Automatic continuation
after a verified dead worker uses the same seed, code and paid prefix and records
the new attempt. A scientific/numerical failure requires a documented code/version
repair, not silent deletion. At the deadline no new fit/selection starts.
