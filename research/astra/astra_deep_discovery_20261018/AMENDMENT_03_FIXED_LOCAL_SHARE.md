# Additional matched control, registered before TEST exposure

18 October 2026. The v2 DEV worker has started, but no v2 scientific performance
table has been inspected and no TEST realization has run. This amendment adds a
necessary control; it does not revise the method, primary tests, loss or success
definition in the frozen v2 manifest.

The existing ungated-local comparator matches the *available local slots*, not
necessarily the realized number of local queries: an inactive surprise gate
spends fewer. Thus regional minus ungated-local alone cannot isolate the value
of choosing a region based on surprise at a fixed local allocation. We explicitly
retain this limitation and add two controls with EXACTLY the same realized share.

Both controls use the `structure` model, same startup, paid outputs, independent
policy RNG 713019, Q, decisions, budgets and all 14 frozen worlds. Steps 0 modulo
4 are global random; steps 2 modulo 4 are global SUR; all odd steps are local SUR.
The local candidate set is the 12 nearest UNPAID candidates to a paid anchor,
so every local slot is feasible (pool 512, budget at most 64). This changes the
neighbourhood convention for BOTH controls and is not called the main policy.
Every local query maximizes the same global SUR score restricted to that set.
No privileged evaluator group or other arm's observations enter either selector.

* `quota_no_surprise`: anchor is the most recent valid global paid point, or the
  last startup ID until such a point exists. No surprise episode controls queries.
* `quota_surprise`: use the same default anchor, except during an active v2
  boundary-contradiction episode, whose anchor/reference/corroboration and six-
  local-query cap are unchanged. The episode may select an older surprising
  anchor. Global slots and total local expenditure are still identical.

This isolates SURPRISE-INFORMED ANCHOR CHOICE at fixed allocation. It is not
an exact equal-cost causal decomposition of whether to launch an episode; that
counterfactual cannot be obtained simply by handing one arm another arm's future
trigger log under the same paid-information contract. Report realized counts:
16 of 32 adaptive DEV queries and 28 of 56 TEST queries are local, per arm.

Three existing DEV realizations per family give 84 extra trajectories. The same
24 independently generated TEST realizations per family give 672 extra trajectories.
They belong to the SAME synthetic test experiment, not a second independent
confirmation. Their protocol is frozen before those outcomes. There is no DEV
score gate or parameter selection. A separate worker executes these after the
main v2 queue completes, within Astra's original two slots and absolute deadline.

Extra numerical allocation: 41,076 top-level fits and 704,160 component solves.
Together with v1 retained work and v2, nominal controlled fits are 692,697 and
component solves 4,793,034 at registration (diagnostic overhead is additionally
charged). These remain INSIDE 700,000 requests / 6,000,000 components. Independent
reference budget remains 400 requests / 6,000 components. No deadline reset.

Analysis: a single descriptive equal-family paired mean difference in final
global error, its 10,000 stratified paired bootstrap interval (seed 20261018),
boundary/island recalls, proper scores, joint attainment and restricted query
burden. No new primary significance claim. Reuse the unchanged two-successive-
budget target and actual-horizon censor rule. Retain every failed/censored run.
An exact cost check must verify the 16/28 local counts and identical global slot
positions before interpreting the result. A query saving claim requires both
arms' attainment >=80% and a positive paired reduction interval as before.

The additional implementation and runner are separately hashed in
`FROZEN_QUOTA_CONTROL_V1.json`; root v2 source and manifest stay immutable.
`quota_policy.py` is the compact prototype; the worker injects its Policy factory
inside its own process only. Opus's code and running jobs are untouched.
