# Independent synthetic TEST — prospective scientific protocol

This protocol is written before generating any new TEST realization. The final
JSON freeze supplies the timestamp, source hashes and exact unit list. The old
campaign and all 40 new DEV trajectories are exposed development. No test outcome
may change this protocol, the prior, numerical tolerance, shortlist or success rule.

## Population, observations, worlds and budget

The scientific target distribution is uniform on [0,1]^4, with latent monitor
threshold zero. The selector approximates its sign-error loss on the same fixed
1,024-point scrambled Sobol reference cloud; independent 2,048-point iid evaluator
clouds estimate outcome metrics. Candidate pools have 512 public feature vectors.
Each unique run costs one and returns its available scalar primary monitor.
Missing observations retain their cost. No island/family/noise/true function
information enters the policy. The noise model is intentionally wrong in several
families; these worlds stay in the results.

Eleven fixed families: smooth, coordinate anisotropy, rotated anisotropy, local
scale, small/large island, heteroskedastic, heavy tail, null, coherent monitor
corruption and missing primary output. Each seed draws a fresh function/noise/pool.
Island centers are drawn once independently of startup; no rejection to create a
free hit. Pool-island counts of zero remain in all unconditional summaries.
The structural baseline is the old 12-component scalar bank. The one new local
bank and the learned ARD baseline are fixed by the development protocol.

There are **336 distinct worlds**: 128 small-island, 64 large-island, and 16 per
other family. The extra island realizations improve precision of the sparse
post-hit diagnostic, without deciding whether to retain any world from its
outcomes. The first sixteen realizations in every family form the 176-world
end-to-end panel. All means over families use equal family weights; pooling all
336 rows without these weights would silently change the target population.

## Matched experiments and strong controls

1. **Common-prefix experiment:** a lawful feature-only maximin path buys B32 in
   every world. Start all four factorial policies from exactly these paid values;
   continue to B48. Arms are existing/h1, existing/h2, local/h1, local/h2, plus
   local/full-pool straddle, learned-ARD/full-pool straddle, and existing/local
   mixture-aware h1. There are 2,688
   trajectories. Startup and all preceding queries count toward B48. Evaluator
   measurements begin at B32; no earlier attainment is invented.
2. **End-to-end experiment:** the first sixteen worlds per family start at B8 and
   continue to B48. The eight arms are the four factorial arms, learned-ARD/h1,
   learned-ARD/straddle, existing/straddle and local/straddle.
   There are 1,408 trajectories. First-hit and no-hit results
   are reported separately from post-prefix refinement.

Total: **4,096 learned trajectories**, not 4,096 independent worlds. Reusing a world
across arms/panels does not increase its replication count. B32 predictions in
the common-prefix panel give a directly matched-path model comparison before any
acquisition divergence. Model effects at B48 may also involve changed paths.

Horizon comparisons share the posterior, decision, startup, paid output, six-point
shortlist and one-in-four random exploration schedule. The shortlist contains two
public random priorities, two full-pool straddle leaders and two nearest unpaid
neighbors of a paid residual anchor, filling duplicates deterministically.
Leave-one-out residuals are proposal heuristics, not calibrated surprise tests.
The forced future global slot is honored in hypothetical two-step choices.
Only the first planned run is actually bought, then the posterior is updated.

The full-pool straddle controls expose shortlist cost/artifacts and are complete
system comparisons. Separate feature-only RANDOM/MAXIMIN B8-to-B48 search paths
in the 176 end-to-end worlds expose first-hit opportunity (352 paths, no model
fits or learned classification metrics). They use the same B8 prefix and charge
every paid query. RANDOM uses independent per-budget public random priorities;
MAXIMIN continues the existing feature prefix. These are search controls, not
classification controls or additional independent worlds. They must not be
mistaken for isolated horizon effects. The ARD controls learn their hyperparameters
on paid values; no true rotation, lengthscale, island center or noise is supplied.

## Frozen numerical rule

Gaussian moment lookahead retains mixture within/between covariance, uses
independent observation noise exactly once, and approximates future mixture
reweighting. Actual paid updates reweight all components. Availability is a
paid-only plug-in estimate held fixed inside fantasies. Hyperparameters of the
ARD working model are also held fixed inside a one-step fantasy.

GH orders 9/17/33/65; two adjacent refinements below 5e-5 permit acceptance;
maximum order 65. Ordinary score ties use 2e-5. The uncertainty set uses twice the
larger of 5e-5 and the last two refinement changes, plus the tie tolerance.
Select the best one-step action within unresolved ties. Record unresolved
integration, changed rankings, near ties and fallbacks. These are numerical
diagnostics, not a proved error bound or an exact mixture posterior. Do not
escalate settings on a difficult TEST result. At the finite cap, an unaccepted
integral is flagged; action selection still uses the declared finite-resolution
set, taking moment-h1 within that set if it is not a singleton. Acceptance is
a refinement diagnostic, not a rigorous error bound. Report the fraction of
paths/actions affected, so a bounded approximation is not called exact planning.

The single additional mechanism is future component learning, justified in
COMPONENT_LEARNING_CONTROL.md before TEST. The existing/local mixture-aware
one-step controls condition and reweight components under each hypothetical
outcome. Importance GH orders 17/33/65/129, absolute tolerance 1e-4, mass tolerance
1e-4, omitted mass <=1e-8 and tie tolerance 2e-5 are fixed. Two successive score
refinements or stable-three-order rank resolution (gap > four times the last two
changes plus tie tolerance) can accept an action. Otherwise fall back to moment-h1.
Report absolute convergence separately from rank resolution, effective weighted
quadrature-node counts, mass errors and fallbacks. These counts are not iid
Monte Carlo ESS. Single-component integration uses the analytic one-step result.

## Primary mechanism contrasts and uncertainty

For a loss E, define the paired world-level contrasts:

    Representation R = ((local_h1-existing_h1)+(local_h2-existing_h2))/2
    Horizon H = ((existing_h2-existing_h1)+(local_h2-local_h1))/2
    Interaction I = (local_h2-local_h1)-(existing_h2-existing_h1).

Primary endpoint is B48 in the common-prefix experiment. Evaluate these three
contrasts on two declared losses:

- uniform sign error across all eleven families;
- island error (=1-island recall) **conditional on at least one valid island
  observation in the common B32 prefix**, averaging small/large families equally.

That makes six prespecified primary estimates, not a post-hoc subgroup hunt.
The conditional result answers learning *after a lawful hit*; it does not estimate
cheap discovery. A latent island hit whose returned channel is missing does not
count as informative. Also report the unconditional island analysis, all no-hit
worlds and zero-candidate worlds. The learner receives none of these memberships.

Use 10,000 stratified whole-world paired bootstrap resamples, analysis seed
672020. Retain all arms/panels together within a resampled world. For the six
primary estimates use a joint max-standardized-bootstrap-deviation critical
value for approximate 95% simultaneous intervals. Degenerate zero-variance
coordinates get a zero-width descriptive interval and no inferential pass.
Conditional-hit denominators are recomputed per resample; empty replicates are
reported, not silently converted to zero. This relies on independent realizations
within the specified families and bootstrap approximation; it is not an exact
randomization test, distribution-free guarantee or inference to arbitrary
unseen families. No sign-flip p-value is treated as justified by zero mean alone.

Family results, budget curves, end-to-end contrasts and strong-control differences
get pointwise 95% paired intervals, labelled descriptive. No global replacement
claim follows from one favorable family or an unadjusted winning control.
The four prespecified mixture-control comparisons are, within each posterior,
mixture-h1 versus moment-h1 and h2 versus mixture-h1, on the same two loss
definitions. They are secondary diagnostics with pointwise intervals, not extra
primary promotion gates. A horizon contrast that disappears against mixture-h1
cannot be attributed uniquely to two paid steps. Even if it persists, the h2
working posterior remains a moment approximation; the exact-mixture horizon
mechanism would still require its own numerical and experimental validation.

A representation or horizon mechanism can be supported by a negative simultaneous
upper interval for one declared loss, accompanied by a simultaneous upper bound
below +0.01 global error and +0.05 conditional island error on the other loss.
Report any family harm even when this guard passes. An interaction is evidence of
effect modification, not by itself a benefit. Practical promotion additionally
requires comparison with the learned-ARD/cheap controls and measured computation;
synthetic evidence cannot authorize replacing Opus's physical posterior.

If the conditional group is too small or uncertainty too wide, the result is
inconclusive. Do not obtain a conveniently larger conditional sample by reseeding.
Any incomplete scientific unit disables a clean primary pass; report counts,
completion-conditional estimates and bounded missing-outcome sensitivity.

## Metrics, attainment and paid/computation cost

At budgets separated by four paid queries record global/boundary error, positive
and negative recall, BA, island recall, Brier/log loss, latent/reported RMSE,
moment-interval coverage, first/third island hit, all missing queries, mixture
weights and local component evidence. Near-boundary means evaluator-only |f|<=.10.
Undefined classes/bands are N/A and have explicit denominators.

The common joint target is unchanged: global error<=.08, boundary error<=.25,
both available class recalls>=.85, and island recall>=.70 where an evaluator
island exists. It must hold at two consecutive four-query readouts; charge the
second budget. Continue to B48 regardless. Attainment is an event, not a promise
of later persistence. A post-prefix run cannot claim target attainment before B36.

Report attained fractions, censored counts, event-time distribution and restricted
burden min(T,48). A lower restricted burden alone is not sample savings.
Query-saving language requires at least 80% attainment in each compared arm,
a favorable paired burden interval, and no lost regional guard. Otherwise show
the censored table without extrapolated savings. Never report fictitious physical
hours: no simulator duration was measured.

All readouts retain cumulative selection CPU, fit CPU and total CPU, plus final
wall time and per-process peak memory. Equal-decision-CPU comparisons use the
last observed readout within 0.25/1/5/20/60 CPU seconds and the common B48 cap.
Equal-total-CPU comparisons use 1/5/20/60/300 seconds. A path that has already
reached its query cap is capped, not extrapolated; a budget below initial fitting
cost has no available prediction and is explicitly unavailable. These are
descriptive compute-budget readouts, not physical time savings.

## Frozen follow-through and stopping

The finite envelope is recorded in TEST_EXECUTION_ENVELOPE.md and CAMPAIGN.json.
The controller is idempotent, records PID/create-time, and claims only Astra's
two slots before numerical imports. Every prospective fit/factorization/fantasy
is charged to the finite ledger. Deadlines never reset. No failed attempt or
reservation is deleted. Unit hashes and immutable pre-query states support replay.

At completion, or the fixed deadline, produce all per-world tables, mechanism
and cost summaries, full path integrity, selected numerical replays and reviewed
figures. The one allowed alternative has already been used for the prospective
component-learning control. There is no remaining alternative, prior, threshold
or selector sweep. Test outcomes cannot change this programme.
