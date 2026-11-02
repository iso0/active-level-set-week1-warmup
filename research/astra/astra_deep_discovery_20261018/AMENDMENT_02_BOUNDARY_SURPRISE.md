# Prospective second version: boundary surprise and structural representation

Registered after inspecting all 807 v1.1 DEV trajectories on 18 October 2026,
before any TEST function/noise realization was generated. The original failed
quadrature attempt, v1.1 source, manifests, completed outcomes and null effects
remain intact. This is a single mechanism-led development revision, not a
threshold/prior search. The 48-hour clock and all physical-data restrictions stay.

## Evidence and competing explanations

V1.1 mixture regional versus global SUR has exactly zero error difference on 42
DEV worlds: its gate never acts. This does not test the benefit of an active local
response. Unconditionally local acquisition is worse by 0.00446 global error
on average (descriptive interval [0.00071,0.00824]). Most families have approximately
99–100% coverage by nominal 90% latent intervals; the anisotropic family is an
exception, with about 75% coverage and 50% sign error. Broad prior uncertainty can
hide meaningful sign contradictions without a 2.5-standard-deviation residual.
Separately, short isotropic kernels cannot efficiently share information along
irrelevant directions. These are distinct allocation and representation failures.

## One decision-linked gate, fixed before its outcomes

Keep the global schedule, radius, six-query cap and two-verification limit.
At a valid global paid observation, retain its pre-query posterior. A boundary
episode is eligible only when the old sign has probability at least 0.75 and the
Gaussian moment update using the new observation gives the opposite sign probability
at least 0.90. These are declared operational odds (3:1 before, 9:1 after), not
estimates of a universal significance threshold. No gate threshold will be tuned.
The updated local latent moments are

    m+ = m + v/(v+t) (y-m),  v+ = vt/(v+t),

where v is latent variance and t is observation-noise variance. Unlike raw value
surprise, the gate requires a change of the relevant level-set decision. For a
mixture this moment update is an approximation; actual posterior fitting still
reweights all components. A local corroboration is the same direction of sign
contradiction against the FROZEN pre-anchor posterior, with 0.60 prior opposition
and 0.80 updated confidence. No hidden island membership is used. Calibration
scale >2 inhibits the gate as in v1. Invalid/missing primary outputs end episodes.

On subsequent eligible local slots choose the maximum of the SAME global SUR
score inside the radius; the first local query verifies by nearest neighbour.
Retain blind-neighbour and ungated controls with the same slot schedule. The
legacy z-trigger remains a labelled control, not silently replaced in its files.
This gate cannot find an unobserved island, distinguish coherent monitor corruption
from physics, or guarantee that local restriction beats globally maximal one-step
SUR. The experiment tests when model repair/verification compensates for that cost.

## One representation extension, no optimizer or kernel sweep

Add model `structure`: the two existing isotropic kernels plus one Matérn-3/2
kernel per coordinate with length 0.08 in that coordinate and 1.2 in all others.
Assign half the kernel prior mass to the two isotropic kernels and half equally
to the four coordinate alternatives. Keep both noise levels and all existing
output-correlation alternatives, equally weighted within each kernel. Therefore
there are 12 scalar or 36 paired components. All have amplitude 1, no fitted
hyperparameter optimizer, and exact component conditioning/evidence updates.
All coordinates receive the same prior; generator identity, seed, island centre,
hidden outcomes and evaluation groups are absent from the model/selector API.
This bank is not a nonparametric nonstationary GP and cannot represent arbitrary
rotated or spatially varying anisotropy. Results on the already seen DEV family
motivate this capacity change; only fresh realizations support later test claims.

## Numerical and protocol repairs decided without scientific-score tuning

The predeclared numerical fixture selected 1024 Sobol reference points: across
four scrambles max score discrepancy versus 8192 is 0.000254, below the fixed
0.0005 limit. N=512 failed that criterion. This is a finite reference comparison,
not a proof for all future posteriors. Consume the original 128 random-reference
draws to preserve all function/noise realizations, then use one public Sobol
cloud with seed 251018. Use an independent constant policy RNG stream (713019),
never pass the generator seed. Add matched RANDOM/MAXIMIN model comparisons.

Retain all 14 families, DEV seeds, unopened 24 TEST realizations per family,
budgets, metrics and the joint two-readout attainment target. New DEV is development
even if a revised method wins. No new scientific score will select another gate
or kernel. Retain the two legacy primary contrasts and add two revised primary
contrasts: structure/boundary_regional minus structure/sur_global; and
structure/boundary_regional minus simple/boundary_regional. Holm adjustment covers
all FOUR final-error primary tests. Other controls/metrics remain descriptive.

The new arms are simple's original 13 plus boundary_regional; mixture's original
six plus random, maximin, boundary_regional; and structure with random, maximin,
straddle, sur_global, boundary_regional, boundary_blind, ungated_local. Add
sur_primary for BOTH multi-output mixtures in multi-output families. This retains
the historical contrasts and isolates gate, model, and paired-output valuation.

## Finite computation amendment, before new fits

Retain at most 700,000 total controlled requests, expand the total component
envelope from 2,000,000 to **6,000,000**, and independent references from 200/2000
requests/components to **400/6000**. All are CAMPAIGN totals, including v1 failures,
DEV, numerical references, diagnostics and replay. The final manifest will compute
exact nominal counts before enqueue. No new task may start after the original
20 October 08:40:14 UTC deadline. Two registered Astra threads only. Preserve
all failures and censor incomplete paths; do not shorten the target or omit hard
families to claim success. A larger allocation is not paid compute or a reset.

## Expected directions and stopping condition

Boundary surprise should create some real local verification, unlike the inactive
v1 gate, but may hurt under noise and corrupt monitors. Structural sharing should
help coordinate anisotropy and can hurt when that prior is wrong. Small unseen
islands remain limited by first-hit probability; no universal win is predicted.
Do not give a numeric effect prediction from three DEV realizations. After this
revision, run the frozen independent test and report both mechanisms, including
failure. Any later development requires a new, explicitly separate protocol and
cannot reuse these test outcomes as untouched evidence.

## Durable technical release and implementation equivalence

The detached controller may release v2 TEST automatically only after its independent
numerical checks pass and ALL v2 DEV trajectories finish with unique paid IDs,
matching world/startup identities and preserved pre-query hashes. There is no
DEV scientific-effect gate: the revision and test analysis are already fixed.
Any failed numerical or trajectory check blocks release for a documented repair.
This replaces the earlier manual-release workflow prospectively and prevents
chat inactivity from consuming the remaining experiment window. It does not
authorize an automatic model revision or an outcome-selected test subset.

Spatial kernel arrays shared by mixture components are cached by exact array
identity and kernel parameters; retained references prevent identity reuse.
No components are pruned. Candidate-only baselines compute a one-reference
snapshot because reference integration cannot enter those selection rules.
These reduce computation without changing their decision mathematics.
