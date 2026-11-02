# Independent model validation, frozen before generated outcomes

One candidate: joint_model.py exactly as DEV, fixed six-parameter shared-theta
empirical Bayes, same64 gates/null prior/.36 local variance/.5decision/tolerances/
starts/refresh cadence. All six DEV comparators retained. No model or selector
choice from TEST. DEV indicated concentrated benefit, not query saving.

144 independent4D worlds:12 families×12 realizations, seeds
20261028000+1000*family_index+replicate. No seed overlaps old DEV. Each world has
256public candidates/768uniform reference inputs, two dependent paths with the
same8maximin startup: feature-only maximin and original strong-GP margin.
Every observation is revealed only after its choice; every prequery posterior
is saved. All queries including startup and pre-hit exploration are charged.
The worlds/generator parameters/regions/noise truth never enter model functions.

Local families (equal family weight): radial_shift, radial_island, rotated_ridge,
compact_plateau, twin_islands, annular_shell. Controls: smooth, rare_negative,
heteroskedastic, heavy_tail, outliers, correlated_corruption. Random sign,
orientation, centers, amplitude and three prescribed size levels. First two
local families test transfer to new realizations of related shapes; remaining
four test deliberately outside the radial basis. Uniform negative/positive
island backgrounds do not supply a free positive. Shapes and numerical generator
formulae are frozen in test_worlds.py; no generator calibration against results.

Evaluation and budget B8,10,...24 unchanged. Two path deltas are averaged inside
world, then worlds within family, then families. Main effects are joint minus
strong_extra, fixed_extra and joint_trace in all six local families. For a
model-validation PASS require each mean>=.005 and each one-sided bootstrap
lower98.333% bound>0 (Bonferroni for these3 predeclared contrasts). Also require
regional-error reduction with upper95% bound<0; outside-basis four-family mean
BA differences versus strong_extra and fixed_extra>0; control mean and each
smooth/outliers/correlated_corruption mean BA difference>−.01, with overall
control one-sided lower95% bound>−.01. Other family/metric intervals are explicitly
pointwise descriptive. Bootstrap10000, seed726280, stratified whole worlds.
These are Monte Carlo inference on fixed synthetic families, not physical proof.

Keep every generated world. One-class reference BA is undefined, not resampled
or silently replaced; report denominators and all proper/global-error scores.
PASS additionally requires at least10/12 worlds with defined paired BA in EACH
family. Failed/incomplete units prevent automatic PASS; do not drop them.
Report both recalls, per-world outliers, regional and outside error, proper
scores, theta/evidence diagnostics, CPU and peak memory. DEV world's exceptional
gain is not a criterion for selecting TEST worlds.

Targets .90/.93/.95 require two consecutive evaluations of a single learner;
confirmation budget charged, no attainment afterB24 inferred. Restricted burden
25 for nonattainment is a penalized endpoint, not actual success time. Compare
attainment and burden with paired world uncertainty; model improvement alone
does not warrant a query-saving claim. Preserve geometric/latent/noisy hit times
and conditional post-hit summaries as evaluator diagnostics, not policy inputs.

If PASS, freeze a bounded own-margin experiment and any cheap one-step selector
before their outcomes. Match model, decision, startup, output contract and new
evaluation worlds. No two-step planner. If FAIL, preserve exact result and
diagnose limits; this TEST must not be retuned into success.

Finite separate TEST_V1 ledger ceilings:40000 model requests,6000000 optimizer
evaluations,400000000 rank-one updates,2000 independent reference solves. Covers
288paths, including original-strong path construction and matched six-model
replay; retains all reservations/failed attempts. Automatic cached analysis runs
only after every TEST unit is terminal. Same original deadline; no extra48h.
