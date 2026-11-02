# Final prospective execution envelope

20 October 2026, before generating any independent TEST realization.
The bounded development allocation is exhausted: exactly 40 complete trajectories,
zero failed or pending DEV trajectories. The early 24 paths, the eight numerical
refinements and the eight additional-control paths retain their own manifests.
All remain development; none is relabelled TEST.

The revised two-step numerical rule produced 11 unaccepted refinements in 144
DEV decisions and 102 finite-resolution tie fallbacks. The mixture-aware control
accepted all 48 DEV decisions, with five tie fallbacks and one changed refinement
ranking. These are operating characteristics of four exposed worlds, not
guaranteed TEST acceptance or efficacy. No prior or scientific target was tuned.

## Count and finite reserves

336 independent worlds; 2,688 B32-to-B48 common-prefix trajectories and 1,408
B8-to-B48 end-to-end trajectories. Total 4,096 learned paths:
103,424 planned actual fits, and 115,712 four-fit reservations before
interruptions. The 1,088 already reserved DEV fits remain charged.
The 125,000 controlled-fit and 8,000,000 factorization ceilings are unchanged.
Each optimizer objective consumes a factorization, including failed starts.

The new component-learning control adds at most 11,805,696 scalar fantasy
states. The strict two-step maximum is 13,856,256. Before TEST, increase only
the fantasy-state ceiling from 15,000,000 to **30,000,000** to cover both declared
algorithms, existing development, block rounding and bounded numerical checks.
The old ceiling remains in Git and NUMERICAL_REFINEMENT_02.md. This is a finite
prospective arithmetic amendment, not an outcome-dependent rescue. Reference
ceilings remain 500 fits and 20,000 factorizations.

The 352 pure RANDOM/MAXIMIN search paths need no model fits. They still consume
the owned numerical allocation, report their paid-query costs and preserve all
first-hit/no-hit cases. They are not substitutes for classification comparators.

## Feasibility and priority

The measured DEV mean CPU at B8-to-B32 is 4.80 s existing/h1, 10.17 s local/h1,
20.53 s existing/h2, 23.96 s local/h2, and 4.23--4.63 s learned ARD. The B8-to-B16
mixture control costs 3.42 s existing and 7.83 s local. The forecast JSON uses
these timing observations, scales with the remaining query count, multiplies by
1.35 for larger paid sets/unseen worlds, and adds two seconds per worker launch.
For unpiloted straddle costs it conservatively uses the corresponding h1 cost.
This forecast is a scheduling calculation, not a confidence bound; interrupted
work, disk contention and other host activity can make it wrong.

The fixed deadline remains 21 October 11:58:58 UTC. Astra uses only two threads,
with BLAS/OpenMP one thread per worker. Opus's idle allocation remains unavailable.
Run complete world blocks, interleaving families at each replication index, so
initial failures or deadline censoring cannot silently omit a difficult family.
Do not extend the clock or cap in reaction to a scientific result.

Keep enough time for cached-result analysis, replay/integrity and final handoff.
If the deadline censors any path, retain it, disable a clean primary pass and
report incomplete coverage. Do not replace it with an easier seed.

The controller is stdlib-only and registers its exact PID/create time as a
zero-numerical-thread control job. Every numerical child independently claims
one real thread before importing numerical libraries. This clarifies metadata;
it does not change either owner's grant.
