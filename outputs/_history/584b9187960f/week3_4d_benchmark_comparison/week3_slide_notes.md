# Week 3 Slide Notes

## Why move from 2D Branin to 4D

The Week 1 and Week 2 Branin experiments were useful because they made the
active-learning loop visible and testable in two dimensions. The real
laser-metal process-parameter space is four-dimensional, so Week 3 adds a first
4D synthetic benchmark before using the real melt-pool data.

## Selected benchmark

The benchmark is a controlled synthetic 4D boundary function on `[0, 1]^4`.
It is deterministic and continuous. We label a point +1 when the function value
is above a fixed median threshold and -1 otherwise.

I chose this over Ackley for the first Week 3 run because the boundary can be
designed for level-set estimation directly. Ackley is still a good named
benchmark to try later, but it is primarily an optimization test function.

## How the comparison is kept fair

For each seed, all five acquisition rules use the same threshold, same pool,
same test set, same initial labelled points, same GP-regression stand-in, and
same budget. Only the rule for choosing the next pool point changes.

The five rules are the same as Week 2: random, smallest |mu|, straddle,
randomized straddle, and expected feasibility.

## What the results show

The y-axis is test-label misclassification error against exact threshold labels.
Lower is better. In this run the best mean final method is `straddle`, with
mean final error `0.113` at budget 80.

Using a fixed 12% test-error tolerance as a lightweight
progress check:

- random: did not reach 12% mean test error.
- smallest_abs_mu: did not reach 12% mean test error.
- straddle: reached 12% mean test error at n=69.
- randomized_straddle: reached 12% mean test error at n=69.
- expected_feasibility: did not reach 12% mean test error.

## Caveats

This is a first 4D synthetic benchmark. The GP regressor is still a stand-in,
not the final GP classifier. The metric is test-label misclassification error,
not a geometric boundary-distance metric. The result is preliminary and should
be discussed with Ioan before treating it as a final thesis direction.

## Suggested next step for Ioan

Ask Ioan whether this controlled 4D boundary is a good first Week 3 bridge, or
whether he would prefer the next run to use thresholded 4D Ackley as a named
benchmark. Also ask whether the next metric should include a boundary-distance
or contour-quality measure in addition to test misclassification error.
