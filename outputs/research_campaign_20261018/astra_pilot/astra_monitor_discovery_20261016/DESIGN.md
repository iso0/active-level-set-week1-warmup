# Bounded surprise episodes for local discovery

**Directive 2026-10-16; final prospective specification 2026-10-17.** The selector
and generator choices were recorded in `METHOD_CHOICE_RECORD.json` before reading
the newer October 17 protocols. A subsequent commit-metadata read incidentally
exposed their aggregate result descriptions. No method, generator, threshold,
prior or budget was selected or revised using those results. Two runner wiring
repairs and variance-contract checks followed; the selection rule is unchanged.
See `CONTEXT_AND_VARIANCE_AUDIT.md` for this exposure and the exact scope of the
repairs. No new V2 benchmark result is a selection criterion. This package follows
the changed research direction; incomplete ASTRA_AL P2 is not a negative result.

## Question, relation to prior work and claim boundary

Can a *newly paid* observation contradicting a model provide a useful location for
a short local investigation, while continued global sampling prevents indefinite
concentration there? The task is discovery followed by region/boundary learning,
not simply collecting positives or maximizing aggregate BA.

This is an **adaptation of established ideas**, not a claim to invent surprise
sampling. Response-dependent neighborhood sampling predates GP active learning
([Thompson, 1990](https://doi.org/10.1080/01621459.1990.10474975)). Straddle measures
proximity to a specified scalar level and predictive uncertainty; its relation to
LSE confidence bounds is explicit in [Gotovos et al., 2013, §3](https://www.ijcai.org/Proceedings/13/Papers/202.pdf).
That paper also distinguishes boundary learning from active search for positives.

Very close work exists in manufacturing: [Raihan et al., 2024](https://arxiv.org/html/2401.05579v1)
use surprise-guided sequential learning for melt-pool geometry. [CA-SMART, 2025
preprint, §3.5](https://arxiv.org/html/2503.21095v1) already combines posterior-based
surprise, local verification and global coverage. Its [2026 journal version](https://www.sciencedirect.com/science/article/pii/S1568494626009117)
is indexed; the publisher full text was inaccessible here. The accessible preprint
is the basis of this comparison. Our changes are engineering/research choices:
fixed local quotas, retained observations, a calibration warning, a fixed global
quota, separate first-hit versus boundary endpoints, and a strict paid interface.
They are not an established novel algorithm or a theorem transferring those
papers' results to SPH.

## Selected construction, frozen before comparison

Let four features be scaled using declared design-domain bounds into [0,1]^4.
At a selected location i, before seeing its scalar response q_i, save
mu_i, latent SD s_i, and predictive observation-noise SD eta_i. Define

\[
 z_i=\frac{q_i-\mu_i}{\max(\sqrt{s_i^2+\eta_i^2},10^{-8})}.
\]

For previous **global** query residuals only, keep the last eight |z| values. With
at least four, set c=max(1, median(|z|)/0.67449); otherwise c=1. The new residual is
not used in its own calibration. c>2 raises a calibration alert, blocks new episodes
and closes an existing episode on that global update. This is a robust heuristic
on selected observations, **not a calibrated p-value or a conformal guarantee**.
It can miss local miscalibration, particularly early, and can suppress a real shift.
The prototype deliberately does not silently rescale the underlying fitted GP.

A finite, quality-approved newly paid global observation with |z|/c >=2.5 starts
an episode if none is open. Freeze the **whole posterior before that observation**
as the episode reference. All candidates within Euclidean distance 0.25 of the
anchor are eligible for local checks. This radius is a small feature-space
neighborhood (roughly ten neighbors in an interior 512-point uniform 4D pool), not
the constructed island radius, a learned physical length, or a NEW subgroup rule.
No scan-speed cutoff is used.

The four-step repeating schedule is **global random, local, global straddle,
local**. Without an episode, local slots use global straddle. The global random
choice is the first unpaid point of a seeded random permutation. At least one
quarter of post-startup queries therefore maintain global exploration; local
episodes can occupy at most half. This does not guarantee discovery of a tiny
island at a finite budget.

The first local candidate is the nearest unpaid neighbor. A same-sign residual
>=1.5 against the frozen before-anchor reference corroborates a **local model
discrepancy**. It need not still surprise the newly fitted model, which has already
seen the anchor. If neither of the first two local checks corroborates, close the
episode. After corroboration, local slots maximize
1.96 s(x)-|mu(x)-h|, h=0, within the neighborhood. End after at most four local
queries, eight total subsequent choices, no remaining neighbor, or a quality
alert. Local queries cannot create replacement anchors and restart the quota.
All valid observations enter the same GP as the controls; failed local verification
does not delete the original observation.

The selector is O(Nd) per local neighborhood scan plus O(N) scoring/hash work and
O(N) stored reference moments, d=4. There are no hypothetical posterior updates,
quadratures, fantasies, or selector fits. Model prediction costs remain; in the
toy runner, ordinary conditioning costs O(n^3+N n^2), n<=24. The scalar threshold
is a declared **synthetic** target; it is not E1's learned depth-to-morphology rule.

## Falsifiable hypothesis and competing explanations

**H:** If a quality-approved surprise is caused by a locally persistent deviation
of the physical scalar surface, the bounded local episode will improve subsequent
island recall/boundary error, or the censored time to the frozen joint target,
relative to *the same global schedule with local episodes disabled*.

The principal competitor is that additional global coverage explains any gain.
`straddle_global` isolates that explanation. The other competitors are diffuse
uncertainty miscalibration, corrupted monitors, and an insufficiently flexible GP.
A local increase in discovered points without better predictions would favor the
last explanation over an acquisition-only success. First discovery can occur
before any trigger: no benefit from a reaction is possible until an informative
observation has been paid. An island already in startup is reported at its startup
query number, not credited to the selector.

**Unavoidable limitation:** two worlds with identical reported observations and
QA flags—one a physical local shift, another a spatially correlated measurement
bias—produce identical choices. The executed counterexample test demonstrates
this. A local repeat is evidence of persistence in this observation channel;
independent physical/monitor checks are needed to name its cause. A diffuse
calibration warning is not proof of a broken simulator either.

## Prospective synthetic comparison

The evaluator draws 512 candidate features and a separate fixed 2,048-point
evaluation cloud uniformly on [0,1]^4, seeds **61016, 61017**. Truth is never passed
to the selector. Shared feature-only maximin startup B8, all budgets B8...B24,
same fixed Matérn-3/2 GP, noise SD .08 and paired outcomes. No hyperparameter
optimization, reseeding, or tuning after trajectories. The hand-built surfaces
are not draws from the fitted GP and contain a non-smooth joining surface.

| World | Definition | What it tests |
|---|---|---|
| island | f(x)=3 max(0.18-x1, 0.30-||x-(.72,.65,.35,.65)||); q=f+N(0,.08²) | A positive 4D island detached from the main positive slab |
| null_bad_scale | f(x)=3(0.18-x1), no island; supplied predictive SDs ×.15 in every arm | A confidence defect can masquerade as discovery; guard behavior and cost |
| island_bad_monitor | Island world; pool IDs divisible by 37 return nonfinite primary monitors with an explicit quality failure | Invalid primary observations cost a query, cannot trigger, and retain their label |

Five core arms: `surprise`, `straddle_global` (episode ablation), `straddle`,
`margin`, `random`. Margin is |Phi(mu/s)-.5| on **this same regression posterior**;
it is not an implementation or superiority test of G3. Every arm retains the
same startup, prior, level decision, candidate pool, available outputs and cost.

Endpoints at every budget: first valid island query (startup included); queries
until three distinct paid island members; island recall; error in the evaluator's
0.04-wide spherical boundary band; global error, BA and both recalls; Brier/log
loss; scalar MAE/RMSE; latent/observation 90% coverage; feature coverage at radius
.20; invalid-query counts; triggers, corroborations and wall time. Null-world
island endpoints are unavailable, not zero or success. Seed outcomes are paired
and all retained; with two seeds report values/ranges, not persuasive significance.

For **equal-performance query savings**, freeze the joint target now: global
error <=.10, island recall >=.75, island-boundary error <=.20 at two consecutive
readouts. Charge the second readout. Not reached by B24 is right-censored at 24;
never substitute a fictional B25 hit. Report target-attainment counts and raw
censored endpoints; a path change alone is not savings. No target feasibility or
positive effect size is predicted.

## Cheap physical-channel uncertainty extension

In the clean island world only, also pay g(x)+N(0,.08²), with
g=.8 sin(2 pi x2)+.6(x3-.5)+.3 cos(2 pi x4). Both extension controls fit the same
two independent fixed GPs (primary length .28, auxiliary .45; output scales 1).
Compare primary variance against .5 v_primary+.5 v_aux. There is no future
integration and no supplied true unpaid channel. This is a standard multi-output
uncertainty heuristic, not integrated risk reduction. Identical normalized
variance maps would make it redundant. Report each output's MAE/RMSE separately;
the joint regression target is both RMSEs <=.30, confirmed twice. A gain in g need
not improve the level set or canonical Keyhole prediction.

The complete envelope is **30 core + 4 auxiliary trajectories**, 578 controlled
fit requests, 646 controlled GP solves, four separate reference fits, 650 total
solves, one thread and at most 20 cumulative minutes (checked between bounded
steps; a current tiny solve may finish). Failure/cap/expired reservation stops
execution and preserves checkpoints. Incomplete results are not a final negative
finding. None of these experiments authorizes C4, Stage A or SPH superiority claims.
